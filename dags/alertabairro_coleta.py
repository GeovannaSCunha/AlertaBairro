# airflow DAG - AlertaBairro
#
# Configuração e credenciais ficam em Airflow Variables (Admin > Variables), nunca no código.
# Todas têm valor padrão, então o DAG roda sem cadastrar nada:
#   alertabairro_pasta_chegada   pasta de pouso dos arquivos (padrão /opt/airflow/chegada)
#   alertabairro_latitude        latitude do ponto de chuva (padrão -23.55)
#   alertabairro_longitude       longitude do ponto de chuva (padrão -46.63)
#   alertabairro_webhook_alerta  URL de webhook (Teams/Slack/Discord) para avisar falhas (opcional)
# As fontes atuais (Open-Meteo e GeoSampa) não exigem chave. Se uma fonte nova exigir,
# a chave entra como Variable (ex.: alertabairro_token_sptrans) e é lida com Variable.get().
import json
import logging
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pendulum
from airflow.sdk import Variable, dag, task

FUSO = "America/Sao_Paulo"
log = logging.getLogger(__name__)


def config(nome, padrao):
    """Lê uma Airflow Variable; usa o padrão quando ela não foi cadastrada."""
    return Variable.get(nome, default=padrao)


def notificar_falha(context):
    """Notificação de falha: registra no log e, se houver webhook cadastrado, envia a mensagem."""
    ti = context.get("task_instance")
    mensagem = (
        f"AlertaBairro: falha na tarefa {getattr(ti, 'task_id', '?')} "
        f"do DAG {getattr(ti, 'dag_id', '?')} (execução {context.get('run_id', '?')})."
    )
    log.error(mensagem)
    webhook = config("alertabairro_webhook_alerta", "")
    if webhook:
        try:
            requisicao = Request(
                webhook,
                data=json.dumps({"text": mensagem}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(requisicao, timeout=15).close()
        except Exception as erro:  # a notificação nunca derruba o DAG
            log.warning("Não foi possível enviar a notificação: %s", erro)


def consultar_api(url, parametros):
    url_completa = f"{url}?{urlencode(parametros)}"
    requisicao = Request(
        url_completa,
        headers={"User-Agent": "AlertaBairro-FIAP/1.0"}
    )

    with urlopen(requisicao, timeout=90) as resposta:
        return json.load(resposta)


def salvar_json(dados, nome_arquivo):
    pasta_chegada = Path(config("alertabairro_pasta_chegada", "/opt/airflow/chegada"))
    pasta_chegada.mkdir(parents=True, exist_ok=True)
    destino = pasta_chegada / nome_arquivo
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
    default_args={"on_failure_callback": notificar_falha},
    tags=["alertabairro", "citizentech", "bigdata"]
)
def pipeline_alertabairro():

    @task(retries=2, retry_delay=timedelta(minutes=2))
    def coletar_clima():
        hoje = pendulum.now(FUSO).date()

        parametros = {
            "latitude": float(config("alertabairro_latitude", "-23.55")),
            "longitude": float(config("alertabairro_longitude", "-46.63")),
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
