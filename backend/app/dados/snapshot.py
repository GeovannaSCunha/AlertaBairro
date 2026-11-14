"""Snapshot com os valores validados no relatório técnico do Databricks (13/11/2026).

Usado quando o Databricks não está configurado ou não responde. Assim a URL pública
continua funcionando durante a correção, e a tela sempre indica "snapshot".

Os pontos do mapa não fazem parte do relatório. Para exibi-los sem conexão ao Databricks,
exporte a tabela `prata_alagamentos` como CSV (veja `data/snapshot/README.md`).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("alertabairro.snapshot")

VALIDADO_EM = "2026-11-13"
FONTE_RELATORIO = "Relatório técnico AlertaBairro — Databricks (v1.0, 13/11/2026)"

KPIS: dict[str, Any] = {
    "total_alagamentos": 292,
    "subprefeituras_com_registros": 30,
    "mes_inicio": "2026-01-01",
    "mes_fim": "2026-09-01",
    "chuva_acumulada_mm": 67.1,
    "maior_chuva_diaria_mm": 20.2,
    "data_maior_chuva": "2026-10-29",
    "periodo_inicio": "2026-10-28",
    "periodo_fim": "2026-11-06",
}

# Top 10 publicado no relatório (seção 05). Os demais 20 grupos somam 63 registros,
# mas os nomes não constam do relatório; por isso não são inventados aqui.
SUBPREFEITURAS: list[dict[str, Any]] = [
    {"codigo_subprefeitura": None, "subprefeitura": "São Miguel Paulista", "total_ocorrencias": 113},
    {"codigo_subprefeitura": None, "subprefeitura": "Campo Limpo", "total_ocorrencias": 24},
    {"codigo_subprefeitura": None, "subprefeitura": "Aricanduva/Vila Formosa", "total_ocorrencias": 16},
    {"codigo_subprefeitura": None, "subprefeitura": "M'Boi Mirim", "total_ocorrencias": 16},
    {"codigo_subprefeitura": None, "subprefeitura": "Vila Prudente", "total_ocorrencias": 15},
    {"codigo_subprefeitura": None, "subprefeitura": "Butantã", "total_ocorrencias": 11},
    {"codigo_subprefeitura": None, "subprefeitura": "Capela do Socorro", "total_ocorrencias": 9},
    {"codigo_subprefeitura": None, "subprefeitura": "Ipiranga", "total_ocorrencias": 9},
    {"codigo_subprefeitura": None, "subprefeitura": "Itaim Paulista", "total_ocorrencias": 9},
    {"codigo_subprefeitura": None, "subprefeitura": "Pirituba/Jaraguá", "total_ocorrencias": 7},
]
for _item in SUBPREFEITURAS:
    _item.setdefault("primeira_ocorrencia", None)
    _item.setdefault("ultima_ocorrencia", None)

DEMAIS_SUBPREFEITURAS = {"grupos": 20, "total_ocorrencias": 63}

# Julho não tem linha na tabela mensal (lacuna, não zero).
MENSAL: list[dict[str, Any]] = [
    {"mes": "2026-01-01", "total_ocorrencias": 94},
    {"mes": "2026-02-01", "total_ocorrencias": 34},
    {"mes": "2026-03-01", "total_ocorrencias": 48},
    {"mes": "2026-04-01", "total_ocorrencias": 5},
    {"mes": "2026-05-01", "total_ocorrencias": 1},
    {"mes": "2026-06-01", "total_ocorrencias": 10},
    {"mes": "2026-08-01", "total_ocorrencias": 5},
    {"mes": "2026-09-01", "total_ocorrencias": 95},
]

_CHUVA = [
    ("2026-10-28", 1.6),
    ("2026-10-29", 20.2),
    ("2026-10-30", 5.2),
    ("2026-10-31", 1.7),
    ("2026-11-01", 17.8),
    ("2026-11-02", 6.9),
    ("2026-11-03", 0.0),
    ("2026-11-04", 2.3),
    ("2026-11-05", 3.1),
    ("2026-11-06", 8.3),
]


def _clima_com_acumulado() -> list[dict[str, Any]]:
    acumulado = 0.0
    linhas = []
    for data, mm in _CHUVA:
        acumulado = round(acumulado + mm, 1)
        linhas.append({"data": data, "precipitacao_mm": mm, "precipitacao_acumulada_mm": acumulado})
    return linhas


CLIMA_DIARIO = _clima_com_acumulado()

COLUNAS_PONTOS = ("id", "data", "tipo", "subprefeitura", "latitude", "longitude")


def carregar_pontos(snapshot_dir: str | Path) -> list[dict[str, Any]]:
    """Lê `prata_alagamentos.csv` exportado do Databricks, se existir."""
    caminho = Path(snapshot_dir) / "prata_alagamentos.csv"
    if not caminho.exists():
        return []
    pontos: list[dict[str, Any]] = []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        faltando = set(COLUNAS_PONTOS) - set(leitor.fieldnames or [])
        if faltando:
            logger.warning("CSV de pontos ignorado; colunas ausentes: %s", sorted(faltando))
            return []
        for linha in leitor:
            try:
                lat = float(linha["latitude"])
                lon = float(linha["longitude"])
            except (TypeError, ValueError):
                continue
            pontos.append(
                {
                    "id": str(linha["id"]),
                    "data": (linha["data"] or "")[:10] or None,
                    "tipo": linha["tipo"] or None,
                    "subprefeitura": linha["subprefeitura"] or None,
                    "latitude": lat,
                    "longitude": lon,
                }
            )
    pontos.sort(key=lambda p: p["data"] or "", reverse=True)
    return pontos
