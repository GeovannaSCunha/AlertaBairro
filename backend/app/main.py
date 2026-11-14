"""Aplicação FastAPI do AlertaBairro.

Execução local:  uvicorn app.main:app --reload --port 8000
Documentação:    http://localhost:8000/api/docs
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.routing import Match

from app import __version__
from app.assistente.llm import ClienteLLM
from app.assistente.servico import ServicoAssistente
from app.config import Config, carregar_config
from app.dados.fonte import FonteDados
from app.observabilidade import Metricas, configurar_logs
from app.relatos import ErroValidacao, RepositorioRelatos
from app.rotas import Servicos
from app.rotas import assistente as rotas_assistente
from app.rotas import dados as rotas_dados
from app.rotas import relatos as rotas_relatos
from app.seguranca import LimitadorTaxa

logger = logging.getLogger("alertabairro.api")

CABECALHOS_SEGURANCA = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cross-Origin-Resource-Policy": "same-site",
}


def criar_app(config: Config | None = None) -> FastAPI:
    config = config or carregar_config()
    configurar_logs()
    metricas = Metricas()
    fonte = FonteDados(config, observador=metricas.observar_fonte)
    llm = (
        ClienteLLM(config.llm_base_url or "", config.llm_model or "", config.llm_api_key, config.llm_timeout_s)
        if config.llm_configurado
        else None
    )
    servicos = Servicos(
        config=config,
        fonte=fonte,
        relatos=RepositorioRelatos(config.db_path, config.uploads_dir, config.retencao_fotos_dias),
        assistente=ServicoAssistente(fonte, config.base_conhecimento_dir, llm=llm),
        metricas=metricas,
        limitador=LimitadorTaxa(),
    )

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
        removidas = servicos.relatos.aplicar_retencao()
        logger.info(
            "API iniciada (dados=%s, assistente=%s, moderacao=%s, fotos_removidas=%d)",
            fonte.modo,
            servicos.assistente.modo,
            "sim" if config.moderacao_habilitada else "nao",
            removidas,
        )
        yield

    app = FastAPI(
        title="AlertaBairro API",
        version=__version__,
        description=(
            "API do MVP AlertaBairro (Global Solution FIAP 2026.2 — CitizenTech). "
            "Dados históricos de alagamentos e chuva em São Paulo, relatos da comunidade e assistente analítico. "
            "Não é um serviço oficial de alerta."
        ),
        lifespan=ciclo_de_vida,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.servicos = servicos

    if config.cors_origens:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origens),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
        )

    def rota_template(request: Request) -> str:
        """Caminho da rota com parâmetros ({relato_id}), para não explodir a cardinalidade das métricas."""
        for rota in app.router.routes:
            correspondencia, _ = rota.matches(request.scope)
            if correspondencia == Match.FULL:
                return getattr(rota, "path", "nao_mapeada")
        return "nao_mapeada"

    def registrar(request: Request, status: int, inicio: float) -> None:
        rota = rota_template(request)
        if rota == "/metrics":
            return
        duracao = time.perf_counter() - inicio
        metricas.requisicoes.labels(metodo=request.method, rota=rota, status=str(status)).inc()
        metricas.latencia.labels(metodo=request.method, rota=rota).observe(duracao)
        logger.info(
            "requisicao",
            extra={"metodo": request.method, "rota": rota, "status": status, "duracao_ms": round(duracao * 1000, 1)},
        )

    @app.middleware("http")
    async def observar(request: Request, call_next):  # type: ignore[no-untyped-def]
        inicio = time.perf_counter()
        metricas.em_andamento.inc()
        try:
            resposta = await call_next(request)
        except Exception:
            registrar(request, 500, inicio)
            raise
        finally:
            metricas.em_andamento.dec()
        registrar(request, resposta.status_code, inicio)
        for nome, valor in CABECALHOS_SEGURANCA.items():
            resposta.headers.setdefault(nome, valor)
        if request.url.path.startswith("/api/v1/moderacao"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.exception_handler(ErroValidacao)
    async def erro_validacao(_request: Request, exc: ErroValidacao) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "Revise os campos destacados.", "campos": exc.erros})

    @app.exception_handler(RequestValidationError)
    async def erro_requisicao(_request: Request, exc: RequestValidationError) -> JSONResponse:
        campos = {}
        for erro in exc.errors():
            local = [str(p) for p in erro.get("loc", []) if p not in ("body", "query", "path", "header")]
            campos[".".join(local) or "requisicao"] = "Valor ausente ou inválido."
        return JSONResponse(status_code=422, content={"detail": "Requisição inválida.", "campos": campos})

    @app.exception_handler(Exception)
    async def erro_inesperado(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Erro interno. Tente novamente em instantes."})

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(metricas.registro), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", include_in_schema=False)
    def raiz() -> dict[str, str]:
        return {"servico": "AlertaBairro API", "versao": __version__, "documentacao": "/api/docs"}

    app.include_router(rotas_dados.router)
    app.include_router(rotas_relatos.router)
    app.include_router(rotas_assistente.router)
    return app


app = criar_app()
