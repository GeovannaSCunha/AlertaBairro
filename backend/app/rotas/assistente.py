"""Assistente analítico: perguntas em linguagem natural sobre os dados históricos."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.assistente import regras
from app.rotas import limitar, servicos

router = APIRouter(prefix="/api/v1/assistente", tags=["assistente"])


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)


@router.post("", summary="Perguntar ao assistente (resposta em JSON com fontes e recusa)")
def perguntar(request: Request, corpo: Pergunta) -> dict[str, Any]:
    s = servicos(request)
    limitar(request, "assistente", s.config.limite_assistente_por_minuto, 60)
    resposta = s.assistente.responder(corpo.pergunta)
    modo = resposta["modo"].split(":")[0]
    s.metricas.respostas_assistente.labels(modo=modo, recusou=str(resposta["recusou"]).lower()).inc()
    return resposta


@router.get("/info", summary="Modo de operação do assistente")
def info(request: Request) -> dict[str, Any]:
    s = servicos(request)
    return {
        "modo": s.assistente.modo,
        "modelo": s.config.llm_model if s.config.llm_configurado else None,
        "limiar_relevancia": regras.LIMIAR_RELEVANCIA,
        "cobertura_minima": regras.COBERTURA_MINIMA,
        "exemplos": [
            "Quantos alagamentos tem em São Miguel Paulista?",
            "Em qual mês houve mais registros?",
            "Quanto choveu no dia 29/10?",
            "Como funciona o índice experimental?",
            "O que fazer se a rua alagar?",
        ],
    }


@router.get("/base", summary="Exporta a base de conhecimento (trechos com fonte)")
def base(request: Request) -> dict[str, Any]:
    trechos = servicos(request).assistente.base()
    return {"dados": trechos, "total": len(trechos)}
