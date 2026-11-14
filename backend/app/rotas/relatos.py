"""Relatos da comunidade (público) e moderação (restrita por token)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import relatos as rel
from app.rotas import limitar, servicos
from app.seguranca import token_admin_valido

router = APIRouter(prefix="/api/v1", tags=["relatos"])

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_PROTOCOLO = re.compile(r"^AB-[A-Z0-9]{6}$")


def _validar_id(relato_id: str) -> str:
    if not _UUID.match(relato_id):
        raise HTTPException(404, "Relato não encontrado")
    return relato_id


@router.get("/relatos/tipos", summary="Tipos de ocorrência aceitos")
def tipos() -> dict[str, Any]:
    return {"dados": [{"codigo": k, "rotulo": v} for k, v in rel.TIPOS.items()]}


@router.post("/relatos", status_code=201, summary="Registrar um relato (fica pendente de moderação)")
async def criar_relato(
    request: Request,
    tipo: str = Form(...),
    descricao: str = Form(...),
    ocorrido_em: str = Form(...),
    latitude: str = Form(...),
    longitude: str = Form(...),
    aceite_termos: str = Form("false"),
    subprefeitura: str | None = Form(None),
    foto: UploadFile | None = File(None),
) -> dict[str, Any]:
    s = servicos(request)
    limitar(request, "relatos", s.config.limite_relatos_por_hora, 3600)

    try:
        novo = rel.validar(
            tipo=tipo,
            descricao=descricao,
            ocorrido_em=ocorrido_em,
            latitude=latitude,
            longitude=longitude,
            aceite_termos=aceite_termos,
            subprefeitura=subprefeitura,
        )
        foto_jpeg = None
        if foto is not None and foto.filename:
            conteudo = await foto.read(rel.FOTO_MAX_BYTES + 1)
            foto_jpeg = rel.processar_foto(conteudo)
    except rel.ErroValidacao:
        s.metricas.relatos.labels(resultado="invalido").inc()
        raise

    criado = s.relatos.criar(novo, foto_jpeg)
    s.relatos.aplicar_retencao()
    s.metricas.relatos.labels(resultado="recebido").inc()
    return criado | {
        "mensagem": "Recebemos seu relato. Ele aparece no mapa depois da moderação. Guarde o protocolo para acompanhar."
    }


@router.get("/relatos", summary="Relatos aprovados (públicos)")
def listar_relatos(request: Request, limit: int = Query(200, ge=1, le=500)) -> dict[str, Any]:
    itens = servicos(request).relatos.listar_aprovados(limit)
    return {"dados": itens, "meta": {"origem": "comunidade", "tabela": "relatos (SQLite da API)", "moderado": True}}


@router.get("/relatos/protocolo/{protocolo}", summary="Acompanhar um relato pelo protocolo")
def acompanhar(request: Request, protocolo: str) -> dict[str, Any]:
    protocolo = protocolo.strip().upper()
    if not _PROTOCOLO.match(protocolo):
        raise HTTPException(404, "Protocolo não encontrado")
    limitar(request, "protocolo", 30, 60)
    achado = servicos(request).relatos.consultar_protocolo(protocolo)
    if not achado:
        raise HTTPException(404, "Protocolo não encontrado")
    return achado


@router.get("/relatos/{relato_id}/foto", summary="Foto de um relato aprovado")
def foto_publica(request: Request, relato_id: str) -> FileResponse:
    caminho = servicos(request).relatos.caminho_foto(_validar_id(relato_id), somente_aprovado=True)
    if not caminho:
        raise HTTPException(404, "Foto não encontrada")
    return FileResponse(caminho, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})


# ----------------------------------------------------------------------------- moderação
class Decisao(BaseModel):
    acao: str = Field(pattern="^(aprovar|rejeitar)$")
    motivo: str | None = Field(default=None, max_length=200)


def _exigir_admin(request: Request, authorization: str | None) -> None:
    s = servicos(request)
    if not s.config.moderacao_habilitada:
        raise HTTPException(503, "Moderação desabilitada: defina ADMIN_TOKEN (16+ caracteres) no servidor")
    limitar(request, "moderacao", 60, 60)
    if not token_admin_valido(s.config, authorization):
        raise HTTPException(401, "Token de moderação inválido", headers={"WWW-Authenticate": "Bearer"})


@router.get("/moderacao/relatos", tags=["moderação"], summary="Fila de moderação")
def fila(
    request: Request,
    status: str = Query("pendente", pattern="^(pendente|aprovado|rejeitado)$"),
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    _exigir_admin(request, authorization)
    return {"dados": servicos(request).relatos.listar_para_moderacao(status)}


@router.post("/moderacao/relatos/{relato_id}", tags=["moderação"], summary="Aprovar ou rejeitar um relato")
def decidir(request: Request, relato_id: str, decisao: Decisao, authorization: str | None = Header(None)) -> dict[str, Any]:
    _exigir_admin(request, authorization)
    s = servicos(request)
    resultado = s.relatos.moderar(_validar_id(relato_id), decisao.acao, decisao.motivo)
    if resultado is None:
        raise HTTPException(404, "Relato não encontrado")
    s.metricas.moderacoes.labels(acao=decisao.acao).inc()
    return resultado


@router.get("/moderacao/relatos/{relato_id}/foto", tags=["moderação"], summary="Foto de qualquer relato (moderador)")
def foto_moderacao(request: Request, relato_id: str, authorization: str | None = Header(None)) -> FileResponse:
    _exigir_admin(request, authorization)
    caminho = servicos(request).relatos.caminho_foto(_validar_id(relato_id), somente_aprovado=False)
    if not caminho:
        raise HTTPException(404, "Foto não encontrada")
    return FileResponse(caminho, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
