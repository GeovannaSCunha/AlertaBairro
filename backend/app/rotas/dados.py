"""Rotas somente-leitura sobre o lakehouse (contrato da seção 12 do relatório técnico)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app import __version__, indice
from app.dados import snapshot
from app.rotas import servicos
from app.texto import chave, nome_exibicao

router = APIRouter(prefix="/api/v1", tags=["dados"])

_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("/health", summary="Processo da API está vivo (não testa o Databricks)")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status", summary="Origem dos dados e estado das integrações")
def status(request: Request) -> dict[str, Any]:
    s = servicos(request)
    return {
        "versao": __version__,
        "dados": {
            "modo": s.fonte.modo,
            "databricks_configurado": s.config.databricks_configurado,
            "ultima_consulta_ok": s.fonte.estado.ultima_consulta_ok,
            "ultima_falha": s.fonte.estado.ultima_falha,
            "falhas_consecutivas": s.fonte.estado.falhas_consecutivas,
            "snapshot_validado_em": snapshot.VALIDADO_EM,
            "catalogo": f"{s.config.databricks_catalog}.{s.config.databricks_schema}",
        },
        "assistente": {"modo": s.assistente.modo},
        "moderacao_habilitada": s.config.moderacao_habilitada,
    }


@router.get("/kpis", summary="4 indicadores e períodos")
def kpis(request: Request) -> dict[str, Any]:
    r = servicos(request).fonte.kpis()
    return {"dados": r.dados, "meta": r.meta}


@router.get("/alagamentos/subprefeituras", summary="Ranking de registros por subprefeitura")
def subprefeituras(request: Request, limit: int = Query(10, ge=1, le=50)) -> dict[str, Any]:
    r = servicos(request).fonte.subprefeituras()
    itens = r.dados["itens"]
    base = r.dados.get("demais") or {"grupos": 0, "total_ocorrencias": 0}
    resto = itens[limit:]
    demais = {
        "grupos": base["grupos"] + len(resto),
        "total_ocorrencias": base["total_ocorrencias"] + sum(i["total_ocorrencias"] for i in resto),
    }
    return {
        "dados": {"itens": itens[:limit], "demais": demais if demais["grupos"] else None},
        "meta": r.meta,
    }


def _lacunas(serie: list[dict[str, Any]]) -> list[str]:
    if not serie:
        return []
    presentes = {l["mes"][:7] for l in serie}
    inicio, fim = min(presentes), max(presentes)
    ano, mes = int(inicio[:4]), int(inicio[5:7])
    lacunas = []
    while f"{ano:04d}-{mes:02d}" <= fim:
        atual = f"{ano:04d}-{mes:02d}"
        if atual not in presentes:
            lacunas.append(atual)
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1
    return lacunas


@router.get("/alagamentos/mensal", summary="Série mensal histórica, com meses sem linha indicados")
def mensal(request: Request) -> dict[str, Any]:
    r = servicos(request).fonte.mensal()
    return {"dados": {"serie": r.dados, "lacunas": _lacunas(r.dados)}, "meta": r.meta}


@router.get("/clima/diario", summary="Precipitação diária e acumulada no ponto de referência")
def clima(request: Request) -> dict[str, Any]:
    r = servicos(request).fonte.clima_diario()
    return {
        "dados": {
            "serie": r.dados,
            "ponto_referencia": {"latitude": -23.55, "longitude": -46.63, "descricao": "Região central de São Paulo"},
            "fonte_original": "Open-Meteo (API de arquivo histórico)",
        },
        "meta": r.meta,
    }


@router.get("/alagamentos/mapa", summary="Pontos de ocorrência (camada Prata) com filtros")
def mapa(
    request: Request,
    limit: int = Query(500, ge=1, le=2000),
    subprefeitura: str | None = Query(None, max_length=80),
    mes: str | None = Query(None, description="AAAA-MM"),
) -> dict[str, Any]:
    if mes and not _MES.match(mes):
        raise HTTPException(422, "Parâmetro 'mes' deve estar no formato AAAA-MM")
    r = servicos(request).fonte.pontos()
    todos = r.dados
    filtrados = todos
    if subprefeitura:
        alvo = chave(subprefeitura)
        filtrados = [p for p in filtrados if chave(p.get("subprefeitura")) == alvo]
    if mes:
        filtrados = [p for p in filtrados if (p.get("data") or "").startswith(mes)]
    opcoes_sub = sorted({nome_exibicao(p.get("subprefeitura")) for p in todos if p.get("subprefeitura")})
    opcoes_mes = sorted({(p.get("data") or "")[:7] for p in todos if p.get("data")})
    pontos = [p | {"subprefeitura_exibicao": nome_exibicao(p.get("subprefeitura"))} for p in filtrados[:limit]]
    return {
        "dados": {
            "pontos": pontos,
            "total_filtrado": len(filtrados),
            "total": len(todos),
            "filtros": {"subprefeituras": opcoes_sub, "meses": opcoes_mes},
        },
        "meta": r.meta | {"pontos_disponiveis": bool(todos)},
    }


@router.get("/indice", summary="Índice experimental de atenção (regras documentadas)")
def obter_indice(request: Request, data_referencia: date | None = None) -> dict[str, Any]:
    s = servicos(request)
    hoje = date.today()
    clima_r = s.fonte.clima_diario()
    subs_r = s.fonte.subprefeituras()
    simulacao = data_referencia is not None and data_referencia != hoje
    if data_referencia is not None:
        datas = [date.fromisoformat(l["data"][:10]) for l in clima_r.dados]
        if datas and not (min(datas) <= data_referencia <= hoje):
            raise HTTPException(
                422,
                f"Escolha uma data entre {min(datas).strftime('%d/%m/%Y')} e hoje para simular o índice.",
            )
    resultado = indice.calcular(subs_r.dados["itens"], clima_r.dados, data_referencia or hoje)
    return {
        "dados": resultado | {"demais": subs_r.dados.get("demais")},
        "meta": subs_r.meta | {"tabela_clima": clima_r.meta["tabela"], "simulacao": simulacao},
    }


@router.get("/indicadores", summary="Indicadores de impacto: cobertura, qualidade e uso")
def indicadores(request: Request) -> dict[str, Any]:
    s = servicos(request)
    k = s.fonte.kpis()
    return {
        "dados": {
            "cobertura": {
                "ocorrencias_mapeadas": k.dados["alagamentos"]["total"],
                "subprefeituras_com_registros": k.dados["subprefeituras_com_registros"],
                "total_subprefeituras_sp": 32,
            },
            "qualidade": {
                "origem_dados": k.meta["origem"],
                "consultado_em": k.meta["consultado_em"],
                "snapshot_validado_em": k.meta["snapshot_validado_em"],
            },
            "participacao": s.relatos.indicadores(),
        },
        "meta": k.meta,
    }
