# ruff: noqa: S311, E501  (random só para amostragem reprodutível; linhas longas são textos de exemplo)
"""Gera o conjunto de treino do LoRA (item 05) a partir da base de conhecimento.

Objetivo do ajuste: ensinar o modelo a seguir o CONTRATO do assistente, e não a decorar números.
  1. responder só com o que está nos trechos, com o número exato;
  2. citar em "fontes" o id do trecho COPIADO do contexto (o erro mais comum na RAG simples foi inventar
     ids como "sub:mes2026-05" ou "doc:limites_dados#5");
  3. recusar ("recusou": true, "fontes": []) quando os trechos não respondem, mesmo que pareçam parecidos;
  4. devolver sempre JSON válido no formato {"resposta", "fontes", "recusou"}.

O prompt e o formato da mensagem são os MESMOS do site (app.assistente.llm.montar_mensagens), e o contexto
de cada exemplo vem da MESMA busca BM25, com os mesmos distratores que o modelo verá em produção.

Separação treino x teste: nenhuma pergunta de avaliacao/casos_teste.jsonl entra aqui. O script calcula a
similaridade (Jaccard de termos) de cada pergunta de treino com todas as de teste e descarta as parecidas.

Uso (na raiz do repositório):  python3 treino/gerar_dados_treino.py
Saída: treino/dados_treino.jsonl, treino/dados_validacao.jsonl e treino/estatisticas.json
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
sys.path.insert(0, str(RAIZ / "avaliacao"))

from comum import carregar_casos, carregar_trechos  # noqa: E402

from app.assistente.busca import Achado, IndiceBM25, tokenizar  # noqa: E402
from app.assistente.llm import montar_mensagens  # noqa: E402
from app.assistente.regras import relevante  # noqa: E402

SEMENTE = 42
LIMITE_SIMILARIDADE = 0.6  # Jaccard de termos acima disso com alguma pergunta de teste => descartada
FRACAO_VALIDACAO = 0.1
SAIDA = RAIZ / "treino"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]

RECUSA = ("Não consta na base do AlertaBairro. A base tem alagamentos por subprefeitura e por mês "
          "(janeiro a setembro de 2026) e a chuva de 28/10 a 06/11/2026.")


def resposta(texto: str, fontes: list[str]) -> str:
    return json.dumps({"resposta": texto, "fontes": fontes, "recusou": False}, ensure_ascii=False)


def recusa(motivo: str | None = None) -> str:
    texto = RECUSA if not motivo else f"{motivo} {RECUSA}"
    return json.dumps({"resposta": texto, "fontes": [], "recusou": True}, ensure_ascii=False)


# ----------------------------------------------------------------------------- exemplos com resposta

def exemplos_respondiveis(por_id: dict) -> list[tuple[str, str, str]]:
    """(pergunta, id do trecho-ouro, resposta JSON)."""
    rnd = random.Random(SEMENTE)
    ex: list[tuple[str, str, str]] = []
    rx_sub = re.compile(r"subprefeitura (.+?) tem (\d+) registros? .*?posição (\d+) entre (\d+) .*?"
                        r"primeiro registro é de (\S+) e o último, de (\S+)\.")
    for tid, t in por_id.items():
        if tid.startswith("sub:"):
            m = rx_sub.search(t.texto)
            nome, total, pos, n, prim, ult = m.groups()
            reg = "registro" if total == "1" else "registros"
            ex += rnd.sample([
                (f"Me diga o total de alagamentos registrados em {nome}.", tid,
                 resposta(f"Segundo a base histórica, {nome} tem {total} {reg} de alagamento.", [tid])),
                (f"{nome} aparece com quantas ocorrências de alagamento?", tid,
                 resposta(f"{nome} aparece com {total} {reg} de alagamento na base histórica.", [tid])),
                (f"Em que data aconteceu o primeiro alagamento registrado em {nome}?", tid,
                 resposta(f"O primeiro registro de alagamento em {nome} é de {prim}.", [tid])),
                (f"Qual a data do registro mais recente de alagamento em {nome}?", tid,
                 resposta(f"O último registro de alagamento em {nome} é de {ult}.", [tid])),
                (f"Em que lugar do ranking de alagamentos fica {nome}?", tid,
                 resposta(f"{nome} ocupa a posição {pos} entre {n} subprefeituras com registros. "
                          "O ranking mostra a distribuição dos registros, não um índice de risco.", [tid])),
            ], 3)
        elif tid.startswith("indice:"):
            m = re.search(r"\), (.+?) aparece com atenção (\w+): (.+?)\. O índice", t.texto)
            nome, nivel, conta = m.groups()
            ex += [
                (f"Como está {nome} no índice experimental de atenção?", tid,
                 resposta(f"No índice experimental, {nome} aparece com atenção {nivel} ({conta}). "
                          "O índice é ilustrativo e não é previsão.", [tid])),
            ]
        elif tid.startswith("mes:"):
            ano, mes = tid[4:].split("-")
            nome_mes = MESES[int(mes) - 1]
            if "lacuna" in t.texto:
                ex += [
                    (f"Teve alagamento em {nome_mes} de {ano}?", tid,
                     resposta(f"{nome_mes.capitalize()} de {ano} não tem linha na tabela mensal. É uma lacuna da base, "
                              "e isso não comprova que não houve alagamentos.", [tid])),
                    (f"Quantos registros de alagamento a base tem para {nome_mes}?", tid,
                     resposta(f"A base não tem dados de {nome_mes} de {ano}: é uma lacuna, e não significa zero alagamentos.", [tid])),
                ]
            else:
                total = re.search(r"tem (\d+) registros?", t.texto).group(1)
                reg = "registro" if total == "1" else "registros"
                ex += [
                    (f"No mês de {nome_mes}, quantos alagamentos entraram na base?", tid,
                     resposta(f"Em {nome_mes} de {ano}, a base histórica tem {total} {reg} de alagamento.", [tid])),
                    (f"Me fale o número de alagamentos registrados em {nome_mes} de {ano}.", tid,
                     resposta(f"A base histórica tem {total} {reg} de alagamento em {nome_mes} de {ano}.", [tid])),
                    (f"Qual o total mensal de alagamentos de {nome_mes}?", tid,
                     resposta(f"O total de {nome_mes} de {ano} na base histórica é {total} {reg} de alagamento.", [tid])),
                ]
        elif tid.startswith("chuva:"):
            m = re.search(r"Em (\S+) choveu (\S+) mm.*?acumulado desde o início da série era (\S+) mm", t.texto)
            data, mm, acum = m.groups()
            ex += [
                (f"Qual foi a chuva registrada em {data}?", tid,
                 resposta(f"Em {data} choveu {mm} mm no ponto de referência da região central de São Paulo.", [tid])),
                (f"Até {data}, quanto de chuva tinha acumulado na série?", tid,
                 resposta(f"Até {data}, o acumulado da série era {acum} mm no ponto de referência.", [tid])),
            ]
    k, c = "kpi:resumo", "clima:resumo"
    ex += [
        ("Quantos alagamentos a base do AlertaBairro tem no total?", k,
         resposta("A base histórica tem 292 ocorrências únicas de alagamento, de janeiro a setembro de 2026.", [k])),
        ("A base de alagamentos é atualizada em tempo real?", k,
         resposta("Não. Os dados vêm do GeoSampa/Defesa Civil e são históricos, de janeiro a setembro de 2026.", [k])),
        ("Em quantas subprefeituras houve alagamento registrado na base?", k,
         resposta("A base tem registros de alagamento em 30 subprefeituras.", [k])),
        ("Qual foi o maior volume de chuva em um único dia da série?", c,
         resposta("O maior volume em um dia foi 20,2 mm, em 29/10/2026, no ponto de referência.", [c])),
        ("Quanto choveu ao todo entre 28/10 e 06/11/2026?", c,
         resposta("Entre 28/10/2026 e 06/11/2026 choveu 67,1 mm no total no ponto de referência.", [c])),
        ("Dá para afirmar que a chuva causou os alagamentos da base?", c,
         resposta("Não. O período da chuva (28/10 a 06/11/2026) não coincide com o dos alagamentos "
                  "(janeiro a setembro de 2026), então não é possível afirmar correlação.", [c])),
    ]
    docs = {
        "doc:chuva_e_seguranca#1": [("Quantos litros de água representam 20 mm de chuva?",
                                     "20 mm de chuva equivalem a cerca de 20 litros de água por metro quadrado.")],
        "doc:chuva_e_seguranca#2": [("Para qual número eu ligo se estiver em perigo numa enchente?",
                                     "Ligue para os Bombeiros (193) ou para a Defesa Civil (199). O SAMU atende pelo 192."),
                                    ("O AlertaBairro chama o socorro para mim?",
                                     "Não. O AlertaBairro não aciona socorro: em perigo, ligue 193 (Bombeiros) ou 199 (Defesa Civil).")],
        "doc:chuva_e_seguranca#3": [("Posso atravessar uma rua alagada a pé?",
                                     "Não atravesse ruas alagadas, nem a pé nem de carro: a correnteza e buracos escondidos podem arrastar pessoas."),
                                    ("O que fazer se a água da enchente entrar em casa?",
                                     "Desligue a energia elétrica, se puder fazer isso com segurança, e vá para um lugar alto.")],
        "doc:chuva_e_seguranca#4": [("Onde vejo a situação de alagamento em tempo real?",
                                     "Consulte os canais oficiais, como o CGE da Prefeitura de São Paulo e a Defesa Civil.")],
        "doc:limites_dos_dados#1": [("A chuva e os alagamentos da base são do mesmo período?",
                                     "Não. Os alagamentos cobrem janeiro a setembro de 2026 e a chuva, 28/10 a 06/11/2026.")],
        "doc:limites_dos_dados#2": [("O ranking diz qual região é mais perigosa?",
                                     "Não. O ranking só mostra quantos registros cada região tem; não mede gravidade nem probabilidade.")],
        "doc:limites_dos_dados#3": [("Quantos pontos o histórico vale no índice experimental?",
                                     "O histórico (H) vale de 0 a 3 pontos conforme a quantidade de registros da subprefeitura."),
                                    ("Quando a atenção do índice é considerada elevada?",
                                     "A atenção é elevada quando o índice soma de 4 a 5 pontos.")],
        "doc:limites_dos_dados#4": [("A falta de dados em julho quer dizer que não alagou?",
                                     "Não. Julho de 2026 é uma lacuna da base e não comprova que não houve alagamentos.")],
        "doc:limites_dos_dados#5": [("Onde fica o ponto em que a chuva é medida?",
                                     "Numa coordenada de referência na região central de São Paulo (latitude -23,55 e longitude -46,63)."),
                                    ("A chuva do AlertaBairro mostra quanto choveu no meu bairro?",
                                     "Não. É a chuva de um único ponto na região central e não representa cada bairro.")],
        "doc:limites_dos_dados#6": [("Como os dados chegam ao Databricks?",
                                     "Um DAG do Airflow coleta os lotes, que passam pelas camadas Bronze, Prata e Ouro; o envio ao Databricks é manual.")],
        "doc:sobre_o_app#1": [("O AlertaBairro é um sistema oficial de alerta?",
                               "Não. É uma plataforma web cidadã com dados públicos de chuva e alagamento, não um sistema oficial de alerta.")],
        "doc:sobre_o_app#2": [("Posso relatar um alagamento que aconteceu há duas semanas?",
                               "Não. Relatos são aceitos para ocorrências de até 7 dias atrás.")],
        "doc:sobre_o_app#3": [("Um relato aparece no mapa assim que eu envio?",
                               "Não. Todo relato passa por moderação antes de aparecer no mapa.")],
        "doc:sobre_o_app#4": [("A foto do relato guarda a localização do meu celular?",
                               "Não. Os metadados da foto, como as coordenadas GPS, são removidos no servidor.")],
        "doc:sobre_o_app#5": [("Quanto custa usar o AlertaBairro?",
                               "O acesso é gratuito para os cidadãos.")],
        "doc:sobre_o_app#6": [("Qual ODS ligado ao clima o AlertaBairro atende?",
                               "O ODS 13 (Ação contra a mudança global do clima).")],
    }
    for tid, pares in docs.items():
        ex += [(p, tid, resposta(r, [tid])) for p, r in pares]
    return ex


# ----------------------------------------------------------------------------- exemplos de recusa

def perguntas_de_recusa(nomes_sub: list[str]) -> list[tuple[str, str | None]]:
    """Perguntas parecidas com as da base, mas que a base NÃO responde. (pergunta, motivo opcional)."""
    rnd = random.Random(SEMENTE)
    p: list[tuple[str, str | None]] = []
    for nome in rnd.sample(nomes_sub, 10):
        ano = rnd.choice([2019, 2020, 2021, 2022, 2023])
        p.append((f"Quantos alagamentos {nome} teve em {ano}?", f"A base só cobre 2026, não {ano}."))
    for nome in rnd.sample(nomes_sub, 6):
        p.append((f"Quantas pessoas ficaram desabrigadas em {nome}?", "A base não tem dados de desabrigados."))
    for nome in rnd.sample(nomes_sub, 4):
        p.append((f"Em qual rua de {nome} alaga mais?", "A base agrega por subprefeitura, não por rua."))
    for cidade in ["Osasco", "Santo André", "Campinas", "Rio de Janeiro", "São Bernardo do Campo", "Barueri"]:
        p.append((f"Quantos alagamentos foram registrados em {cidade}?", f"{cidade} não faz parte da base, que é só da cidade de São Paulo."))
    for mes in ["outubro", "novembro"]:
        p.append((f"Quantos alagamentos a base registrou em {mes} de 2026?", f"A base de alagamentos não tem {mes} de 2026."))
    for mes, ano in [("março", 2025), ("janeiro", 2024), ("setembro", 2023), ("fevereiro", 2022), ("junho", 2025)]:
        p.append((f"Quantos alagamentos houve em {mes} de {ano}?", f"A base só cobre 2026, não {ano}."))
    for nome in rnd.sample(nomes_sub, 5):
        p.append((f"Quantas pessoas ficaram feridas em alagamentos em {nome}?", "A base não tem dados de feridos."))
    for data in ["20/10/2026", "25/10/2026", "08/11/2026", "12/11/2026", "01/10/2026", "27/10/2026",
                 "10/11/2026", "05/10/2026"]:
        p.append((f"Qual foi a chuva registrada em {data}?", f"A série de chuva não tem o dia {data}."))
    p += [
        ("Qual a temperatura média registrada no período da base?", "A base não tem temperatura."),
        ("Quantos carros foram arrastados pela enchente?", None),
        ("Qual o horário em que mais alaga em São Paulo?", "A base não tem horário das ocorrências."),
        ("Qual é o nível do rio Pinheiros?", None),
        ("Quem é o governador de São Paulo?", None),
        ("Quanto custa o aluguel em Pinheiros?", None),
        ("Qual a umidade do ar no dia mais chuvoso?", "A base não tem umidade do ar."),
        ("Quantos alagamentos a cidade teve no ano passado inteiro?", "A base só cobre janeiro a setembro de 2026."),
        ("Quantos relatos de cidadãos foram aprovados até hoje?", None),
        ("Qual subprefeitura recebeu mais investimento em drenagem?", None),
        ("Quantos alagamentos teve o bairro de Moema?", "A base agrega por subprefeitura, não por bairro."),
        ("Quantos milímetros choveu em todo o mês de outubro?", "A série de chuva só cobre 28/10 a 06/11/2026."),
        ("Qual foi a velocidade do vento no dia 29/10/2026?", "A base não tem dados de vento."),
        ("Quantas árvores caíram na chuva de 01/11/2026?", None),
    ]
    return p


# ----------------------------------------------------------------------------- montagem

def jaccard(a: str, b: str) -> float:
    ta, tb = set(tokenizar(a)), set(tokenizar(b))
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


def contexto_com_ouro(busca: IndiceBM25, pergunta: str, ouro, rnd: random.Random) -> list[Achado]:
    achados = busca.buscar(pergunta, k=5)
    if not any(a.trecho.id == ouro.id for a in achados):
        # A busca não trouxe o trecho-ouro: troca um distrator por ele, em posição aleatória,
        # para o modelo aprender a achar o trecho certo e não "o primeiro da lista".
        achados = achados[:4]
        achados.insert(rnd.randrange(len(achados) + 1), Achado(ouro, 0.0, 0, 0))
    return achados


def gerar() -> dict:
    rnd = random.Random(SEMENTE)
    trechos = carregar_trechos()
    por_id = {t.id: t for t in trechos}
    busca = IndiceBM25(trechos)
    testes = [c["pergunta"] for c in carregar_casos()]

    exemplos, descartadas, max_sim = [], [], 0.0

    def similar(p: str) -> float:
        return max(jaccard(p, t) for t in testes)

    for pergunta, tid, alvo in exemplos_respondiveis(por_id):
        s = similar(pergunta)
        if s > LIMITE_SIMILARIDADE:
            descartadas.append({"pergunta": pergunta, "similaridade": round(s, 2)})
            continue
        max_sim = max(max_sim, s)
        achados = contexto_com_ouro(busca, pergunta, por_id[tid], rnd)
        exemplos.append({"tipo": "resposta", "ouro": tid, "messages": montar_mensagens(pergunta, achados)
                         + [{"role": "assistant", "content": alvo}]})

    nomes = [t.titulo.removeprefix("Alagamentos na subprefeitura ") for t in trechos if t.id.startswith("sub:")]
    sem_contexto = 0
    for pergunta, motivo in perguntas_de_recusa(nomes):
        s = similar(pergunta)
        if s > LIMITE_SIMILARIDADE:
            descartadas.append({"pergunta": pergunta, "similaridade": round(s, 2)})
            continue
        max_sim = max(max_sim, s)
        achados = busca.buscar(pergunta, k=5)
        if not relevante(achados[0] if achados else None):
            sem_contexto += 1  # no site, o limiar recusa antes do modelo; mantemos poucos desses
            if sem_contexto > 5:
                continue
        exemplos.append({"tipo": "recusa", "ouro": None, "messages": montar_mensagens(pergunta, achados)
                         + [{"role": "assistant", "content": recusa(motivo)}]})

    rnd.shuffle(exemplos)
    n_val = max(1, int(len(exemplos) * FRACAO_VALIDACAO))
    validacao, treino = exemplos[:n_val], exemplos[n_val:]
    SAIDA.mkdir(exist_ok=True)
    for nome, dados in (("dados_treino.jsonl", treino), ("dados_validacao.jsonl", validacao)):
        (SAIDA / nome).write_text("\n".join(json.dumps({"messages": e["messages"]}, ensure_ascii=False) for e in dados) + "\n",
                                  encoding="utf-8")
    est = {
        "semente": SEMENTE,
        "total": len(exemplos),
        "treino": len(treino),
        "validacao": len(validacao),
        "respostas": sum(e["tipo"] == "resposta" for e in exemplos),
        "recusas": sum(e["tipo"] == "recusa" for e in exemplos),
        "por_grupo": {g: sum(1 for e in exemplos if (e["ouro"] or "recusa").split(":")[0] == g)
                      for g in ("sub", "indice", "mes", "chuva", "kpi", "clima", "doc", "recusa")},
        "limite_similaridade_com_teste": LIMITE_SIMILARIDADE,
        "maior_similaridade_mantida": round(max_sim, 2),
        "descartadas_por_parecer_teste": descartadas,
        "perguntas_de_teste_no_treino": 0,
    }
    (SAIDA / "estatisticas.json").write_text(json.dumps(est, ensure_ascii=False, indent=2), encoding="utf-8")
    return est


if __name__ == "__main__":
    e = gerar()
    print(json.dumps({k: v for k, v in e.items() if k != "descartadas_por_parecer_teste"}, ensure_ascii=False, indent=2))
    print(f"Descartadas por parecer pergunta de teste: {len(e['descartadas_por_parecer_teste'])}")
    for d in e["descartadas_por_parecer_teste"]:
        print(f"  {d['similaridade']:.2f}  {d['pergunta']}")
