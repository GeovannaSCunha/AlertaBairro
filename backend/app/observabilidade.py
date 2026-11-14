"""Logs estruturados (JSON) e métricas Prometheus com os 4 sinais de ouro.

  Latência   → http_request_duration_seconds (histograma por rota)
  Tráfego    → http_requests_total
  Erros      → http_requests_total{status=~"5.."} e alertabairro_consultas_dados_total{status="erro"}
  Saturação  → http_requests_em_andamento
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class FormatoJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for campo in ("metodo", "rota", "status", "duracao_ms"):
            if hasattr(record, campo):
                evento[campo] = getattr(record, campo)
        if record.exc_info:
            evento["erro"] = self.formatException(record.exc_info)
        return json.dumps(evento, ensure_ascii=False)


def configurar_logs(nivel: str = "INFO") -> None:
    raiz = logging.getLogger()
    if any(isinstance(h.formatter, FormatoJson) for h in raiz.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatoJson())
    raiz.handlers = [handler]
    raiz.setLevel(nivel)


class Metricas:
    def __init__(self) -> None:
        self.registro = CollectorRegistry()
        self.requisicoes = Counter(
            "http_requests_total", "Requisições HTTP", ["metodo", "rota", "status"], registry=self.registro
        )
        self.latencia = Histogram(
            "http_request_duration_seconds",
            "Duração das requisições HTTP",
            ["metodo", "rota"],
            buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
            registry=self.registro,
        )
        self.em_andamento = Gauge("http_requests_em_andamento", "Requisições em andamento", registry=self.registro)
        self.consultas_dados = Counter(
            "alertabairro_consultas_dados_total", "Consultas à fonte de dados", ["origem", "status"],
            registry=self.registro,
        )
        self.relatos = Counter(
            "alertabairro_relatos_total", "Relatos recebidos", ["resultado"], registry=self.registro
        )
        self.moderacoes = Counter(
            "alertabairro_moderacoes_total", "Decisões de moderação", ["acao"], registry=self.registro
        )
        self.respostas_assistente = Counter(
            "alertabairro_assistente_respostas_total", "Respostas do assistente", ["modo", "recusou"],
            registry=self.registro,
        )
        self.limite_excedido = Counter(
            "alertabairro_limite_excedido_total", "Requisições bloqueadas por limite de taxa", ["recurso"],
            registry=self.registro,
        )

    def observar_fonte(self, origem: str, status: str) -> None:
        self.consultas_dados.labels(origem=origem, status=status).inc()
