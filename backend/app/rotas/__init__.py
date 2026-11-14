"""Rotas HTTP da API v1."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from app.assistente.servico import ServicoAssistente
from app.config import Config
from app.dados.fonte import FonteDados
from app.observabilidade import Metricas
from app.relatos import RepositorioRelatos
from app.seguranca import LimitadorTaxa, ip_cliente


@dataclass
class Servicos:
    config: Config
    fonte: FonteDados
    relatos: RepositorioRelatos
    assistente: ServicoAssistente
    metricas: Metricas
    limitador: LimitadorTaxa


def servicos(request: Request) -> Servicos:
    return request.app.state.servicos


def limitar(request: Request, recurso: str, limite: int, janela_s: float) -> None:
    s = servicos(request)
    ip = ip_cliente(request.headers, request.client.host if request.client else None, s.config.confiar_proxy)
    if not s.limitador.permitir(f"{recurso}:{ip}", limite, janela_s):
        s.metricas.limite_excedido.labels(recurso=recurso).inc()
        raise HTTPException(
            status_code=429,
            detail="Muitas solicitações em pouco tempo. Aguarde alguns minutos e tente de novo.",
            headers={"Retry-After": str(int(janela_s))},
        )
