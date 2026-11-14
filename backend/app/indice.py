"""Índice experimental de atenção — Etapa 1 da proposta (regras explicáveis, sem ML).

O índice é ILUSTRATIVO. Ele não é probabilidade, não mede gravidade e não substitui
alertas ou orientações da Defesa Civil. Cada nível vem acompanhado da explicação de
como foi calculado, e as regras abaixo são exibidas na tela /indice.

Componentes:
  H — histórico: quantidade de registros da subprefeitura na base (camada Ouro).
  C — chuva recente: soma dos últimos 3 dias no ponto de referência (Open-Meteo).
      Só entra no cálculo se o dado climático tiver no máximo `VALIDADE_CHUVA_DIAS` dias.
      Com dado vencido, C = 0 e a tela informa o motivo.
Pontuação = H + C  →  0–1 atenção baixa · 2–3 atenção moderada · 4–5 atenção elevada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

# (limite mínimo, pontos) — avaliados do maior para o menor
FAIXAS_HISTORICO: list[tuple[int, int]] = [(50, 3), (15, 2), (5, 1), (0, 0)]
FAIXAS_CHUVA_72H_MM: list[tuple[float, int]] = [(30.0, 2), (10.0, 1), (0.0, 0)]
JANELA_CHUVA_DIAS = 3
VALIDADE_CHUVA_DIAS = 3
NIVEIS: list[tuple[int, str, str]] = [
    (4, "elevada", "Atenção elevada"),
    (2, "moderada", "Atenção moderada"),
    (0, "baixa", "Atenção baixa"),
]

AVISO = (
    "Índice experimental e ilustrativo, calculado por regras documentadas. "
    "Não é previsão, não mede gravidade e não substitui a Defesa Civil (199) ou os Bombeiros (193)."
)

REGRAS_TEXTO = [
    "Histórico (H): 0 a 4 registros = 0 ponto; 5 a 14 = 1; 15 a 49 = 2; 50 ou mais = 3.",
    "Chuva recente (C): soma dos últimos 3 dias no ponto de referência; abaixo de 10 mm = 0; 10 a 29,9 mm = 1; 30 mm ou mais = 2.",
    "A chuva só conta se o dado climático mais recente tiver no máximo 3 dias em relação à data de referência.",
    "Pontuação = H + C. De 0 a 1: atenção baixa. De 2 a 3: atenção moderada. De 4 a 5: atenção elevada.",
    "A chuva vem de um único ponto (região central). Ela é aplicada igualmente a todas as regiões, o que é uma simplificação.",
]


def pontos_historico(total: int) -> int:
    for minimo, pontos in FAIXAS_HISTORICO:
        if total >= minimo:
            return pontos
    return 0


def pontos_chuva(mm_72h: float) -> int:
    for minimo, pontos in FAIXAS_CHUVA_72H_MM:
        if mm_72h >= minimo:
            return pontos
    return 0


def nivel(pontuacao: int) -> tuple[str, str]:
    for minimo, codigo, rotulo in NIVEIS:
        if pontuacao >= minimo:
            return codigo, rotulo
    return "baixa", "Atenção baixa"


@dataclass(frozen=True)
class ContextoChuva:
    considerada: bool
    mm_72h: float | None
    janela_inicio: str | None
    janela_fim: str | None
    motivo: str


def contexto_chuva(clima: list[dict[str, Any]], referencia: date) -> ContextoChuva:
    """Soma a chuva dos 3 dias que terminam na data de referência (inclusive)."""
    if not clima:
        return ContextoChuva(False, None, None, None, "Sem dados climáticos disponíveis.")

    por_data = {date.fromisoformat(l["data"][:10]): float(l.get("precipitacao_mm") or 0.0) for l in clima}
    ultima = max(por_data)
    if referencia < min(por_data):
        return ContextoChuva(False, None, None, None, "A data de referência é anterior ao início da série climática.")

    fim = min(referencia, ultima)
    defasagem = (referencia - ultima).days
    if defasagem > VALIDADE_CHUVA_DIAS:
        return ContextoChuva(
            False,
            None,
            None,
            ultima.isoformat(),
            f"O dado de chuva mais recente é de {ultima.strftime('%d/%m/%Y')} "
            f"({defasagem} dias antes da referência). Acima de {VALIDADE_CHUVA_DIAS} dias, a chuva não entra no cálculo.",
        )

    inicio = fim - timedelta(days=JANELA_CHUVA_DIAS - 1)
    soma = round(sum(mm for d, mm in por_data.items() if inicio <= d <= fim), 1)
    return ContextoChuva(
        True,
        soma,
        inicio.isoformat(),
        fim.isoformat(),
        f"Chuva de {inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')} no ponto de referência: "
        f"{_mm(soma)} mm.",
    )


def _mm(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def calcular(
    subprefeituras: list[dict[str, Any]],
    clima: list[dict[str, Any]],
    referencia: date,
) -> dict[str, Any]:
    chuva = contexto_chuva(clima, referencia)
    c = pontos_chuva(chuva.mm_72h) if chuva.considerada and chuva.mm_72h is not None else 0

    regioes = []
    for item in subprefeituras:
        total = int(item.get("total_ocorrencias") or 0)
        h = pontos_historico(total)
        pontuacao = h + c
        codigo, rotulo = nivel(pontuacao)
        partes = [f"{total} registro{'s' if total != 1 else ''} na base histórica → H = {h}"]
        if chuva.considerada:
            partes.append(f"{_mm(chuva.mm_72h or 0.0)} mm em 3 dias → C = {c}")
        else:
            partes.append("chuva recente sem dado válido → C = 0")
        regioes.append(
            {
                "subprefeitura": item.get("subprefeitura"),
                "chave": item.get("chave"),
                "total_ocorrencias": total,
                "componente_historico": h,
                "componente_chuva": c,
                "pontuacao": pontuacao,
                "nivel": codigo,
                "rotulo": rotulo,
                "explicacao": "; ".join(partes) + f". Total = {pontuacao}.",
            }
        )

    regioes.sort(key=lambda r: (-r["pontuacao"], -r["total_ocorrencias"], r["subprefeitura"] or ""))
    return {
        "data_referencia": referencia.isoformat(),
        "chuva": {
            "considerada": chuva.considerada,
            "mm_72h": chuva.mm_72h,
            "janela_inicio": chuva.janela_inicio,
            "janela_fim": chuva.janela_fim,
            "motivo": chuva.motivo,
            "pontos": c,
        },
        "regioes": regioes,
        "regras": REGRAS_TEXTO,
        "aviso": AVISO,
    }
