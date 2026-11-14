"""Modo "regras": responde sem LLM, chamando ferramentas fixas sobre os dados.

As ferramentas espelham as rotas da API (obter_kpis, listar_subprefeituras, obter_mensal,
obter_clima, obter_indice) e nunca executam SQL livre.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.assistente.base_conhecimento import MESES, data_br, periodo_meses_br
from app.assistente.busca import Achado
from app.assistente.guardrails import normalizar
from app.texto import SUBPREFEITURAS_SP, sem_acentos

LIMIAR_RELEVANCIA = 2.0  # score BM25 mínimo do melhor trecho para responder pelo modo de busca
COBERTURA_MINIMA = 0.5  # fração dos termos da pergunta que precisam aparecer no trecho
_DEFINICAO = re.compile(r"\b(o que (e|significa|quer dizer)|significa|como funciona|por que|para que serve|o que fazer)\b")


def relevante(achado: Achado | None) -> bool:
    """Limiar de resposta da busca: score mínimo E cobertura mínima (evita casar uma palavra solta)."""
    if achado is None:
        return False
    return achado.score >= LIMIAR_RELEVANCIA and (achado.termos_casados >= 2 or achado.cobertura >= COBERTURA_MINIMA)


@dataclass
class Resposta:
    resposta: str
    fontes: list[dict[str, str]] = field(default_factory=list)
    recusou: bool = False
    motivo_recusa: str | None = None
    modo: str = "regras"
    ferramentas: list[str] = field(default_factory=list)


def _fonte(achado_id: str, titulo: str, fonte: str) -> dict[str, str]:
    return {"id": achado_id, "titulo": titulo, "fonte": fonte}


def _num(v: float | None) -> str:
    return "sem dado" if v is None else f"{v:.1f}".replace(".", ",")


def _palavras(texto: str) -> str:
    """Texto normalizado com espaços nas bordas, para casar nomes por palavra inteira."""
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acentos(texto.lower())).split()) + " "


def _candidatos(nome: str) -> list[str]:
    partes = [nome] + [p for p in nome.split("/") if p.strip()]
    saida = []
    for parte in partes:
        c = _palavras(parte)
        if len(c.strip()) >= 4 and c not in saida:
            saida.append(c)
    return saida


def _achar_subprefeitura(pergunta: str, itens: list[dict[str, Any]]) -> dict[str, Any] | None:
    texto = _palavras(pergunta)
    melhor = None
    for item in itens:
        for c in _candidatos(item.get("subprefeitura") or ""):
            if c in texto and (melhor is None or len(c) > melhor[0]):
                melhor = (len(c), item)
    return melhor[1] if melhor else None


def _achar_nome_sp(pergunta: str) -> str | None:
    """Encontra qualquer subprefeitura de SP citada, mesmo que não esteja no ranking carregado."""
    texto = _palavras(pergunta)
    for nome in SUBPREFEITURAS_SP:
        if any(c in texto for c in _candidatos(nome)):
            return nome
    return None


def _achar_data(pergunta_norm: str, ano_padrao: int) -> str | None:
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", pergunta_norm)
    if not m:
        return None
    dia, mes = int(m.group(1)), int(m.group(2))
    ano = int(m.group(3)) if m.group(3) else ano_padrao
    if not (1 <= dia <= 31 and 1 <= mes <= 12):
        return None
    return f"{ano:04d}-{mes:02d}-{dia:02d}"


def _achar_mes(pergunta_norm: str) -> int | None:
    for i, nome in enumerate(MESES, start=1):
        if re.search(rf"\b{sem_acentos(nome)}\b", pergunta_norm):
            return i
    return None


def responder(pergunta: str, ctx: dict[str, Any], achados: list[Achado], fontes_por_id: dict[str, Any]) -> Resposta:
    p = normalizar(pergunta)
    kpis = ctx["kpis"]
    subs = ctx["subprefeituras"]["itens"]
    mensal = ctx["mensal"]
    clima = ctx["clima"]
    indice = ctx.get("indice")

    def fonte_de(tid: str) -> list[dict[str, str]]:
        t = fontes_por_id.get(tid)
        return [_fonte(t.id, t.titulo, t.fonte)] if t else []

    # 1) Como relatar
    if re.search(r"\b(relatar|registrar|reportar|denunciar|enviar (um )?relato|cadastrar)\b", p):
        return Resposta(
            "Para registrar uma ocorrência, abra a página “Relatar”, marque o ponto no mapa, informe "
            "data, hora e uma descrição sem dados pessoais. A foto é opcional. O relato fica pendente até "
            "a moderação e você recebe um protocolo para acompanhar.",
            fontes=fonte_de("doc:sobre_o_app#2") or [],
            ferramentas=[],
        )

    # 2) Perguntas de definição vão direto à base de documentos
    if _DEFINICAO.search(p) and achados and relevante(achados[0]):
        melhor = achados[0].trecho
        return Resposta(melhor.texto, fontes=[_fonte(melhor.id, melhor.titulo, melhor.fonte)], ferramentas=["buscar_base"])

    # 3) Índice experimental
    sub = _achar_subprefeitura(pergunta, subs)
    if re.search(r"\b(indice|nivel|atencao|pontuacao)\b", p) and indice:
        if sub:
            reg = next((r for r in indice["regioes"] if r.get("chave") == sub.get("chave")), None)
            if reg:
                return Resposta(
                    f"No índice experimental, {reg['subprefeitura']} aparece com {reg['rotulo'].lower()}. "
                    f"Cálculo: {reg['explicacao']} O índice é ilustrativo, baseado em regras documentadas, "
                    "e não é previsão.",
                    fontes=fonte_de(f"indice:{reg.get('chave')}"),
                    ferramentas=["obter_indice"],
                )
        return Resposta(
            "O índice experimental soma dois componentes: o histórico de registros da subprefeitura (0 a 3 "
            "pontos) e a chuva dos últimos 3 dias no ponto de referência (0 a 2 pontos, só quando o dado "
            f"climático é recente). {indice['chuva']['motivo']} Ele é ilustrativo e não substitui a Defesa Civil.",
            fontes=fonte_de("doc:limites_dos_dados#3"),
            ferramentas=["obter_indice"],
        )

    # 4) Subprefeitura específica
    if sub:
        return Resposta(
            fontes_por_id[f"sub:{sub.get('chave')}"].texto
            if f"sub:{sub.get('chave')}" in fontes_por_id
            else f"Segundo a base histórica, {sub['subprefeitura']} tem {sub['total_ocorrencias']} registros.",
            fontes=fonte_de(f"sub:{sub.get('chave')}"),
            ferramentas=["listar_subprefeituras"],
        )

    nome_sp = _achar_nome_sp(pergunta)
    if nome_sp:
        demais = ctx["subprefeituras"].get("demais")
        if demais:
            return Resposta(
                f"{nome_sp} não está entre as {len(subs)} subprefeituras com mais registros no snapshot validado. "
                f"As outras {demais['grupos']} subprefeituras somam {demais['total_ocorrencias']} registros, mas "
                "o snapshot não traz o número de cada uma. Com a conexão ao Databricks ativa, o valor aparece aqui.",
                fontes=fonte_de("sub:demais"),
                ferramentas=["listar_subprefeituras"],
            )
        return Resposta(
            f"{nome_sp} não aparece com registros de alagamento na base histórica "
            f"({periodo_meses_br(kpis['alagamentos']['periodo_inicio'], kpis['alagamentos']['periodo_fim'])}). "
            "Isso não garante que não houve alagamentos, apenas que não há registros nesta base.",
            fontes=fonte_de("kpi:resumo"),
            ferramentas=["listar_subprefeituras"],
        )

    # 5) Mês específico
    mes = _achar_mes(p)
    if mes and re.search(r"\b(alag|ocorrenc|registr|caso)", p):
        ano = int((mensal[0]["mes"] if mensal else "2026-01-01")[:4])
        tid = f"mes:{ano}-{mes:02d}"
        if tid in fontes_por_id:
            return Resposta(fontes_por_id[tid].texto, fontes=fonte_de(tid), ferramentas=["obter_mensal"])
        return Resposta(
            f"A base histórica não tem dados de {MESES[mes - 1]} de {ano}. Ela cobre "
            f"{periodo_meses_br(kpis['alagamentos']['periodo_inicio'], kpis['alagamentos']['periodo_fim'])}.",
            recusou=True,
            motivo_recusa="fora_do_periodo",
            ferramentas=["obter_mensal"],
        )

    # 6) Ranking
    if re.search(r"\b(ranking|mais (alagamentos|registros|ocorrencias)|maior(es)? (numero|quantidade)|top|lider|onde mais)\b", p):
        top = subs[:5]
        lista = "; ".join(f"{i}. {s['subprefeitura']} ({s['total_ocorrencias']})" for i, s in enumerate(top, 1))
        return Resposta(
            f"As subprefeituras com mais registros na base histórica são: {lista}. O ranking mostra "
            "onde estão os registros da base, não um índice de risco, e não considera população nem área.",
            fontes=[f for s in top for f in fonte_de(f"sub:{s.get('chave')}")],
            ferramentas=["listar_subprefeituras"],
        )

    # 7) Chuva
    if re.search(r"\b(chuva|choveu|chover|precipitac|mm|milimetro|pluviometr)", p):
        cl = kpis["clima"]
        ano = int((cl.get("periodo_inicio") or "2026")[:4])
        dia = _achar_data(p, ano)
        if dia:
            tid = f"chuva:{dia}"
            if tid in fontes_por_id:
                return Resposta(fontes_por_id[tid].texto, fontes=fonte_de(tid), ferramentas=["obter_clima"])
            return Resposta(
                f"Não há dado de chuva para {data_br(dia)}. A série vai de {data_br(cl['periodo_inicio'])} "
                f"a {data_br(cl['periodo_fim'])}.",
                recusou=True,
                motivo_recusa="fora_do_periodo",
                ferramentas=["obter_clima"],
            )
        return Resposta(
            f"No ponto de referência da região central, choveu {_num(cl['chuva_acumulada_mm'])} mm no total "
            f"entre {data_br(cl['periodo_inicio'])} e {data_br(cl['periodo_fim'])}. O dia mais chuvoso foi "
            f"{data_br(cl.get('data_maior_chuva'))}, "
            f"com {_num(cl['maior_chuva_diaria_mm'])} mm. Esse período não coincide com o dos alagamentos, "
            "então não dá para relacionar uma coisa com a outra.",
            fontes=fonte_de("clima:resumo"),
            ferramentas=["obter_clima"],
        )

    # 8) Resumo / totais
    if re.search(r"\b(quantos|quantas|total|resumo|numeros|dados|base)\b", p) and re.search(r"\b(alag|ocorrenc|registr|base|dados)", p):
        ala = kpis["alagamentos"]
        return Resposta(
            f"A base histórica tem {ala['total']} ocorrências únicas de alagamento, "
            f"{periodo_meses_br(ala['periodo_inicio'], ala['periodo_fim'])}, em "
            f"{kpis['subprefeituras_com_registros']} subprefeituras com registros.",
            fontes=fonte_de("kpi:resumo"),
            ferramentas=["obter_kpis"],
        )

    # 9) Busca na base de conhecimento (documentos e dados)
    if achados and relevante(achados[0]):
        melhor = achados[0].trecho
        return Resposta(melhor.texto, fontes=[_fonte(melhor.id, melhor.titulo, melhor.fonte)], ferramentas=["buscar_base"])

    return Resposta(
        "Não consta na base do AlertaBairro. Posso responder sobre alagamentos registrados por "
        "subprefeitura e por mês (jan–set/2026), sobre a chuva histórica (28/10 a 06/11/2026), sobre o "
        "índice experimental e sobre como enviar um relato.",
        recusou=True,
        motivo_recusa="nao_consta",
        ferramentas=["buscar_base"],
    )
