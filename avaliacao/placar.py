"""Placar das configurações do assistente (itens 04, 05 e 06 da disciplina de IA Generativa).

Roda os 50 casos de avaliacao/casos_teste.jsonl contra um modelo servido pelo Ollama (API compatível
com OpenAI) em uma de três configurações:

  sem_contexto  o modelo responde sozinho, sem base e sem guardrails (linha de base)
  rag           pipeline do site: guardrails -> BM25 -> limiar -> modelo com os trechos -> validação do JSON
  lora_rag      o mesmo pipeline, com o modelo afinado por LoRA (passe --modelo com o nome dele)

Uso (na raiz do repositório, com o Ollama rodando):
  python3 avaliacao/placar.py --config sem_contexto --modelo qwen2.5:3b-instruct
  python3 avaliacao/placar.py --config rag --modelo qwen2.5:3b-instruct
  python3 avaliacao/placar.py --config lora_rag --modelo alertabairro-lora
  python3 avaliacao/placar.py --resumo        # junta as configurações já rodadas em resultados/placar.md

Cada execução grava avaliacao/resultados/placar_<config>.jsonl (uma linha por caso, com a resposta bruta).
Só usa a biblioteca padrão do Python, além do código do próprio backend.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request

from comum import RESULTADOS, carregar_casos, carregar_trechos, indice

from app.assistente.guardrails import verificar
from app.assistente.llm import ClienteLLM, ErroLLM
from app.assistente.regras import relevante
from app.texto import sem_acentos

CONFIGS = ("sem_contexto", "rag", "lora_rag")
K_TRECHOS = 5  # o mesmo do site (servico.K_TRECHOS)

PROMPT_SEM_CONTEXTO = """Você é um assistente que responde perguntas de cidadãos sobre chuva e alagamentos em São Paulo.
Responda em português do Brasil, em no máximo 4 frases.
Se não souber a resposta, diga que não sabe e marque "recusou": true.
Responda APENAS com JSON válido no formato:
{"resposta": "texto", "recusou": false}"""


# ----------------------------------------------------------------------------- chamadas ao modelo

def _post(url: str, corpo: dict, timeout: int) -> dict:
    if not url.startswith(("http://", "https://")):
        raise ValueError("A URL do modelo precisa começar com http:// ou https://")
    req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"), method="POST",  # noqa: S310
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  # nosec B310 nosemgrep - URL local do Ollama
        return json.loads(resp.read().decode("utf-8"))


def responder_sem_contexto(pergunta: str, url: str, modelo: str, timeout: int) -> dict:
    corpo = {
        "model": modelo,
        "messages": [{"role": "system", "content": PROMPT_SEM_CONTEXTO}, {"role": "user", "content": pergunta}],
        "temperature": 0.1,
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }
    bruto = _post(f"{url.rstrip('/')}/chat/completions", corpo, timeout)["choices"][0]["message"]["content"]
    try:
        obj = json.loads(bruto[bruto.find("{"): bruto.rfind("}") + 1])
        resposta, recusou = obj.get("resposta"), obj.get("recusou", False)
        if not isinstance(resposta, str) or not isinstance(recusou, bool):
            raise ValueError
        return {"resposta": resposta, "recusou": recusou, "fontes": [], "etapa": "modelo", "json_valido": True, "bruto": bruto}
    except ValueError:
        return {"resposta": bruto, "recusou": False, "fontes": [], "etapa": "modelo", "json_valido": False, "bruto": bruto}


def responder_rag(pergunta: str, busca, cliente: ClienteLLM) -> dict:
    """Mesmo caminho do site (ServicoAssistente.responder), sem o fallback para o modo regras."""
    verificacao = verificar(pergunta)
    if verificacao.categoria != "ok":
        return {"resposta": verificacao.mensagem, "recusou": verificacao.categoria != "emergencia",
                "fontes": [], "etapa": f"guardrail:{verificacao.categoria}", "json_valido": None, "bruto": None}
    achados = busca.buscar(pergunta, k=K_TRECHOS)
    if not relevante(achados[0] if achados else None):
        return {"resposta": "Não consta na base do AlertaBairro.", "recusou": True, "fontes": [],
                "etapa": "limiar", "json_valido": None, "bruto": None, "contexto": []}
    contexto = [a.trecho.id for a in achados]
    try:
        saida = cliente.gerar(pergunta, achados)
        return {**saida, "etapa": "modelo", "json_valido": True, "bruto": None, "contexto": contexto}
    except ErroLLM as exc:
        # No site, este caso cai para o modo "regras". Aqui contamos como falha do modelo.
        return {"resposta": str(exc), "recusou": False, "fontes": [], "etapa": "modelo", "json_valido": False,
                "bruto": None, "erro": str(exc), "contexto": contexto}


# ----------------------------------------------------------------------------- correção automática

def _norm(texto: str) -> str:
    return " " + " ".join(re.sub(r"[^a-z0-9,./']+", " ", sem_acentos((texto or "").lower())).split()) + " "


def _contem(resposta: str, fato: str) -> bool:
    r, f = _norm(resposta), _norm(fato).strip()
    variantes = {f, f.replace(",", ".")}
    if re.fullmatch(r"[0-9]+", f):  # número inteiro: casa como número isolado ("9" não casa com "19")
        return re.search(rf"(?<![0-9]){f}(?![0-9,.][0-9])", r) is not None
    return any(v in r for v in variantes)


def corrigir(caso: dict, saida: dict) -> dict:
    recusou = bool(saida["recusou"])
    fatos_ok = all(_contem(saida["resposta"], f) for f in caso["fatos"])
    if caso["deve_recusar"]:
        correto = recusou
        alucinou = not recusou  # afirmou algo que a base não sustenta
        recusa_indevida = False
    else:
        correto = (not recusou) and fatos_ok
        alucinou = (not recusou) and not fatos_ok  # respondeu, mas com o fato errado ou ausente
        recusa_indevida = recusou
    if saida["etapa"] != "modelo":
        alucinou = False  # erro de guardrail ou de limiar é erro do pipeline, não texto inventado pelo modelo
    ouro = set(caso["trechos_ouro"])
    citou_ouro = bool(ouro & set(saida.get("fontes") or [])) if ouro and not recusou else None
    return {"correto": correto, "alucinou": alucinou, "recusa_indevida": recusa_indevida, "citou_ouro": citou_ouro}


# ----------------------------------------------------------------------------- execução e resumo

def rodar(config: str, modelo: str, url: str, timeout: int) -> None:
    casos = carregar_casos()
    busca = indice(carregar_trechos())
    cliente = ClienteLLM(url, modelo, timeout_s=timeout)
    saida_arquivo = RESULTADOS / f"placar_{config}.jsonl"
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    linhas = []
    for i, caso in enumerate(casos, 1):
        inicio = time.perf_counter()
        if config == "sem_contexto":
            saida = responder_sem_contexto(caso["pergunta"], url, modelo, timeout)
        else:
            saida = responder_rag(caso["pergunta"], busca, cliente)
        latencia = round(time.perf_counter() - inicio, 2)
        nota = corrigir(caso, saida)
        linha = {"id": caso["id"], "categoria": caso["categoria"], "pergunta": caso["pergunta"], "config": config,
                 "modelo": modelo, "latencia_s": latencia, **saida, **nota}
        linhas.append(linha)
        marca = "OK " if nota["correto"] else ("ALU" if nota["alucinou"] else "ERR")
        print(f"[{i:02d}/{len(casos)}] {marca} {caso['id']} {saida['etapa']:<20} {latencia:>5.1f}s  {saida['resposta'][:70]!r}")
    saida_arquivo.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in linhas) + "\n", encoding="utf-8")
    print()
    imprimir_resumo({config: resumir(linhas)})
    print(f"\nSalvo em {saida_arquivo}")


def resumir(linhas: list[dict]) -> dict:
    n = len(linhas)
    resp = [l for l in linhas if l["categoria"] not in ("nao_consta", "previsao")]
    recusar = [l for l in linhas if l["categoria"] in ("nao_consta", "previsao")]
    modelo = [l for l in linhas if l["etapa"] == "modelo"]
    citaveis = [l for l in linhas if l["citou_ouro"] is not None]
    return {
        "modelo": linhas[0]["modelo"],
        "casos": n,
        "acerto_geral": sum(l["correto"] for l in linhas) / n,
        "acerto_respondiveis": sum(l["correto"] for l in resp) / len(resp),
        "recusa_correta": sum(l["correto"] for l in recusar) / len(recusar),
        "alucinacao": sum(l["alucinou"] for l in linhas) / n,
        "recusa_indevida": sum(l["recusa_indevida"] for l in linhas) / n,
        "json_valido": (sum(bool(l["json_valido"]) for l in modelo) / len(modelo)) if modelo else None,
        "citacao_correta": (sum(l["citou_ouro"] for l in citaveis) / len(citaveis)) if citaveis else None,
        "chamadas_ao_modelo": len(modelo),
        "latencia_media_s": sum(l["latencia_s"] for l in linhas) / n,
    }


ROTULOS = [
    ("acerto_geral", "Acerto geral (50 casos)"),
    ("acerto_respondiveis", "Acerto nas perguntas com resposta"),
    ("recusa_correta", "Recusa correta ('não consta' e previsão)"),
    ("alucinacao", "Alucinação (afirmou o que a base não sustenta)"),
    ("recusa_indevida", "Recusa indevida"),
    ("json_valido", "JSON válido (chamadas ao modelo)"),
    ("citacao_correta", "Citou o trecho correto"),
    ("chamadas_ao_modelo", "Chamadas ao modelo"),
    ("latencia_media_s", "Latência média (s)"),
]


def _fmt(chave: str, valor) -> str:
    if valor is None:
        return "—"
    if chave == "chamadas_ao_modelo":
        return str(valor)
    if chave == "latencia_media_s":
        return f"{valor:.1f}".replace(".", ",")
    return f"{valor:.1%}".replace(".", ",")


def tabela_markdown(resumos: dict[str, dict]) -> str:
    cab = "| Métrica | " + " | ".join(f"{c} ({r['modelo']})" for c, r in resumos.items()) + " |"
    sep = "|---|" + "---|" * len(resumos)
    corpo = [f"| {rotulo} | " + " | ".join(_fmt(ch, r[ch]) for r in resumos.values()) + " |" for ch, rotulo in ROTULOS]
    return "\n".join([cab, sep, *corpo])


def imprimir_resumo(resumos: dict[str, dict]) -> None:
    print(tabela_markdown(resumos))


def resumo_geral() -> None:
    resumos = {}
    for config in CONFIGS:
        arq = RESULTADOS / f"placar_{config}.jsonl"
        if arq.exists():
            linhas = [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]
            resumos[config] = resumir(linhas)
    if not resumos:
        raise SystemExit("Nenhum placar_<config>.jsonl em avaliacao/resultados/. Rode uma configuração antes.")
    texto = tabela_markdown(resumos)
    (RESULTADOS / "placar.md").write_text(texto + "\n", encoding="utf-8")
    (RESULTADOS / "placar_resumo.json").write_text(json.dumps(resumos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(texto)
    print(f"\nSalvo em {RESULTADOS / 'placar.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", choices=CONFIGS)
    ap.add_argument("--modelo", default="qwen2.5:3b-instruct")
    ap.add_argument("--url", default="http://localhost:11434/v1")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--resumo", action="store_true", help="junta os resultados já gerados em resultados/placar.md")
    args = ap.parse_args()
    if args.resumo:
        resumo_geral()
    elif args.config:
        rodar(args.config, args.modelo, args.url, args.timeout)
    else:
        ap.error("informe --config ou --resumo")
