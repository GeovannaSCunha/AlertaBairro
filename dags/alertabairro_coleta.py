# airflow DAG - AlertaBairro
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pendulum
from airflow.sdk import dag, task


PASTA_CHEGADA = Path("/opt/airflow/chegada")
FUSO = "America/Sao_Paulo"


def consultar_api(url, parametros):
    url_completa = f"{url}?{urlencode(parametros)}"
    requisicao = Request(
        url_completa,
        headers={"User-Agent": "AlertaBairro-FIAP/1.0"}
    )

    with urlopen(requisicao, timeout=90) as resposta:
        return json.load(resposta)


def salvar_json(dados, nome_arquivo):
    PASTA_CHEGADA.mkdir(parents=True, exist_ok=True)
    destino = PASTA_CHEGADA / nome_arquivo
    temporario = destino.with_suffix(destino.suffix + ".tmp")

    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporario.replace(destino)

    return str(destino)


@dag(
    dag_id="alertabairro_coleta",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 11, 1, tz=FUSO),
    catchup=False,
    tags=["alertabairro", "citizentech", "bigdata"]
)
def pipeline_alertabairro():

    @task(retries=2, retry_delay=timedelta(minutes=2))
    def coletar_clima():
        hoje = pendulum.now(FUSO).date()

        parametros = {
            "latitude": -23.55,
            "longitude": -46.63,
            "start_date": str(hoje - timedelta(days=14)),
            "end_date": str(hoje - timedelta(days=7)),
            "daily": "precipitation_sum",
            "timezone": FUSO
        }

        dados = consultar_api(
            "https://archive-api.open-meteo.com/v1/archive",
            parametros
        )

        if not dados.get("daily", {}).get("time"):
            raise ValueError("Open-Meteo retornou dados vazios")

        nome = f"clima_{hoje:%Y%m%d}.json"
        caminho = salvar_json(dados, nome)
        print(f"Clima salvo em: {caminho}")
        return caminho

    @task(retries=2, retry_delay=timedelta(minutes=2))
    def coletar_alagamentos():
        hoje = pendulum.now(FUSO).date()

        parametros = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": "geoportal:risco_ocorrencia_alagamento",
            "maxFeatures": 1000,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326"
        }

        dados = consultar_api(
            "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
            parametros
        )

        if not dados.get("features"):
            raise ValueError("GeoSampa retornou dados vazios")

        nome = f"alagamentos_{hoje:%Y%m%d}.geojson"
        caminho = salvar_json(dados, nome)
        print(f"Alagamentos salvos em: {caminho}")
        return caminho

    @task
    def conferir_chegada(arquivo_clima, arquivo_alagamentos):
        for arquivo in [arquivo_clima, arquivo_alagamentos]:
            caminho = Path(arquivo)

            if not caminho.is_file() or caminho.stat().st_size == 0:
                raise RuntimeError(f"Arquivo ausente ou vazio: {arquivo}")

            print(f"Arquivo verificado: {caminho.name}")

        print("Coleta do AlertaBairro concluida com sucesso!")

    clima = coletar_clima()
    alagamentos = coletar_alagamentos()

    conferir_chegada(clima, alagamentos)


pipeline_alertabairro()
