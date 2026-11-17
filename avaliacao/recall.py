"""Mede a busca (item 03): recall@1, recall@3 e a escolha do limiar de relevância.

Uso (na raiz do repositório):  python3 avaliacao/recall.py
Saída: tabela no terminal e avaliacao/resultados/recall.json
"""

from __future__ import annotations

from comum import carregar_casos, carregar_trechos, indice, salvar_json

from app.assistente.guardrails import verificar
from app.assistente.regras import COBERTURA_MINIMA, LIMIAR_RELEVANCIA, relevante

LIMIARES = [0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]


def avaliar() -> dict:
    trechos = carregar_trechos()
    busca = indice(trechos)
    casos = carregar_casos()

    linhas = []
    for caso in casos:
        guarda = verificar(caso["pergunta"]).categoria
        achados = busca.buscar(caso["pergunta"], k=5)
        top = achados[0] if achados else None
        ids = [a.trecho.id for a in achados]
        ouro = set(caso["trechos_ouro"])
        linhas.append({
            "id": caso["id"],
            "categoria": caso["categoria"],
            "guardrail": guarda,
            "respondivel": bool(ouro),
            "top3": ids[:3],
            "acerto_1": bool(ouro) and bool(set(ids[:1]) & ouro),
            "acerto_3": bool(ouro) and bool(set(ids[:3]) & ouro),
            "score_top1": top.score if top else 0.0,
            "cobertura_top1": round(top.cobertura, 2) if top else 0.0,
            "relevante": relevante(top),
        })

    # Recall: só perguntas com trecho-ouro que passam pelo guardrail (as demais nem chegam à busca).
    respondiveis = [r for r in linhas if r["respondivel"] and r["guardrail"] == "ok"]
    nao_consta = [r for r in linhas if r["categoria"] == "nao_consta" and r["guardrail"] == "ok"]
    n = len(respondiveis)
    recall_1 = sum(r["acerto_1"] for r in respondiveis) / n
    recall_3 = sum(r["acerto_3"] for r in respondiveis) / n

    # Curva do limiar: quanto das respondíveis seguem aceitas x quantas "não consta" passariam.
    curva = []
    for limiar in LIMIARES:
        def passa(r: dict, lim: float = limiar) -> bool:
            return r["score_top1"] >= lim and r["cobertura_top1"] >= COBERTURA_MINIMA
        curva.append({
            "limiar": limiar,
            "respondiveis_aceitas": round(sum(passa(r) for r in respondiveis) / n, 3),
            "respondiveis_corretas_aceitas": round(sum(passa(r) and r["acerto_3"] for r in respondiveis) / n, 3),
            "nao_consta_aceitas": round(sum(passa(r) for r in nao_consta) / len(nao_consta), 3),
        })

    return {
        "total_casos": len(casos),
        "avaliados_na_busca": n,
        "nao_consta_na_busca": len(nao_consta),
        "barrados_pelo_guardrail": [r["id"] for r in linhas if r["guardrail"] != "ok"],
        "recall_1": round(recall_1, 3),
        "recall_3": round(recall_3, 3),
        "limiar_produto": {"score": LIMIAR_RELEVANCIA, "cobertura": COBERTURA_MINIMA},
        "regra_produto_aceita": {
            "respondiveis": round(sum(r["relevante"] for r in respondiveis) / n, 3),
            "nao_consta": round(sum(r["relevante"] for r in nao_consta) / len(nao_consta), 3),
        },
        "curva_limiar": curva,
        "erros_top3": [r for r in respondiveis if not r["acerto_3"]],
        "erros_top1": [r for r in respondiveis if r["acerto_3"] and not r["acerto_1"]],
        "nao_consta_detalhe": nao_consta,
        "linhas": linhas,
    }


def imprimir(res: dict) -> None:
    print(f"Casos: {res['total_casos']} | avaliados na busca: {res['avaliados_na_busca']} | "
          f"'não consta' na busca: {res['nao_consta_na_busca']}")
    print(f"Barrados antes da busca (guardrail): {', '.join(res['barrados_pelo_guardrail'])}")
    print(f"recall@1 = {res['recall_1']:.1%}   recall@3 = {res['recall_3']:.1%}")
    print("\nlimiar | respondíveis aceitas | corretas aceitas | 'não consta' aceitas (falso aceite)")
    for c in res["curva_limiar"]:
        print(f"{c['limiar']:>6} | {c['respondiveis_aceitas']:>20.1%} | {c['respondiveis_corretas_aceitas']:>16.1%} | "
              f"{c['nao_consta_aceitas']:>10.1%}")
    rp = res["regra_produto_aceita"]
    print(f"\nRegra do produto (score >= {res['limiar_produto']['score']} e cobertura/termos): "
          f"aceita {rp['respondiveis']:.1%} das respondíveis e {rp['nao_consta']:.1%} das 'não consta'")
    if res["erros_top3"]:
        print("\nFora do top-3:")
        for r in res["erros_top3"]:
            print(f"  {r['id']} ({r['categoria']}): top3 = {r['top3']}")
    if res["erros_top1"]:
        print("\nCerto no top-3, errado no top-1:")
        for r in res["erros_top1"]:
            print(f"  {r['id']} ({r['categoria']}): top3 = {r['top3']}")
    print("\n'Não consta' (melhor trecho encontrado):")
    for r in res["nao_consta_detalhe"]:
        print(f"  {r['id']}: score={r['score_top1']:.2f} cobertura={r['cobertura_top1']:.2f} "
              f"aceita_pelo_produto={r['relevante']} top1={r['top3'][:1]}")


if __name__ == "__main__":
    resultado = avaliar()
    imprimir(resultado)
    print(f"\nSalvo em {salvar_json('recall.json', resultado)}")
