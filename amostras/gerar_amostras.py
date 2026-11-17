"""Gera amostras pequenas de cada fonte a partir da pasta chegada/ do Airflow.

Uso (no WSL, na raiz do repositório):
    python3 amostras/gerar_amostras.py ~/alertabairro/chegada

Saída (nesta pasta):
    clima_AAAAMMDD.json                 arquivo do Open-Meteo completo (é pequeno)
    alagamentos_AAAAMMDD_amostra.geojson  10 primeiras ocorrências do GeoSampa
São dados públicos, sem informação pessoal. Usa só a biblioteca padrão do Python.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PASTA_AMOSTRAS = Path(__file__).resolve().parent
QTD_OCORRENCIAS = 10


def ultimo(pasta: Path, padrao: str) -> Path:
    arquivos = sorted(pasta.glob(padrao))
    if not arquivos:
        sys.exit(f"Nenhum arquivo {padrao} em {pasta}")
    return arquivos[-1]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    chegada = Path(sys.argv[1]).expanduser()

    clima = ultimo(chegada, "clima_*.json")
    destino_clima = PASTA_AMOSTRAS / clima.name
    destino_clima.write_text(
        json.dumps(json.loads(clima.read_text(encoding="utf-8")), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    alagamentos = ultimo(chegada, "alagamentos_*.geojson")
    dados = json.loads(alagamentos.read_text(encoding="utf-8"))
    total = len(dados.get("features", []))
    dados["features"] = dados.get("features", [])[:QTD_OCORRENCIAS]
    dados["_amostra"] = (
        f"{QTD_OCORRENCIAS} de {total} ocorrências do arquivo {alagamentos.name} "
        "(GeoSampa, camada geoportal:risco_ocorrencia_alagamento)"
    )
    destino_alag = PASTA_AMOSTRAS / f"{alagamentos.stem}_amostra.geojson"
    destino_alag.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Gerado: {destino_clima.name}")
    print(f"Gerado: {destino_alag.name} ({QTD_OCORRENCIAS} de {total} ocorrências)")


if __name__ == "__main__":
    main()
