"""Serviço de dados: Databricks (quando configurado) com cache e fallback para snapshot.

Toda resposta carrega um bloco `meta` com origem, tabela, natureza e horário da consulta,
para que a interface mostre de onde vem cada número (critério de aceite da proposta).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import Config
from app.dados import snapshot
from app.dados.consultas import CLIMA, DIM_SUBPREFEITURA, DIM_TEMPO, FATO, Consultas
from app.dados.databricks import ClienteDatabricks, DatabricksErro
from app.texto import chave, nome_exibicao

logger = logging.getLogger("alertabairro.dados")

Observador = Callable[[str, str], None]  # (origem, status)

AVISO_SNAPSHOT = (
    "Exibindo o snapshot validado em 13/11/2026 (relatório técnico). "
    "A conexão ao Databricks não está configurada neste ambiente."
)
AVISO_FALLBACK = (
    "O Databricks não respondeu agora; exibindo o snapshot validado em 13/11/2026."
)


@dataclass
class Resultado:
    dados: Any
    meta: dict[str, Any]


@dataclass
class _ItemCache:
    expira_em: float
    valor: Any


@dataclass
class EstadoFonte:
    ultima_consulta_ok: str | None = None
    ultima_falha: str | None = None
    falhas_consecutivas: int = 0
    historico: list[str] = field(default_factory=list)


def _agora_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class FonteDados:
    def __init__(
        self,
        config: Config,
        cliente: ClienteDatabricks | None = None,
        observador: Observador | None = None,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._consultas = Consultas(config.databricks_catalog, config.databricks_schema)
        if cliente is None and config.databricks_configurado:
            cliente = ClienteDatabricks(
                host=config.databricks_host or "",
                token=config.databricks_token or "",
                warehouse_id=config.databricks_warehouse_id or "",
                catalog=config.databricks_catalog,
                schema=config.databricks_schema,
                timeout_s=config.databricks_timeout_s,
            )
        self._cliente = cliente
        self._observador = observador or (lambda origem, status: None)
        self._relogio = relogio
        self._cache: dict[str, _ItemCache] = {}
        self._trava = threading.Lock()
        self._pontos_snapshot: list[dict[str, Any]] | None = None
        self.estado = EstadoFonte()

    # ------------------------------------------------------------------ infraestrutura
    @property
    def modo(self) -> str:
        return "databricks" if self._cliente is not None else "snapshot"

    def tabela(self, nome: str) -> str:
        return self._consultas.tabela(nome)

    def _meta(self, origem: str, tabela: str, consultado_em: str | None, aviso: str | None) -> dict[str, Any]:
        return {
            "origem": origem,
            "tabela": tabela,
            "natureza": "historico",
            "consultado_em": consultado_em,
            "snapshot_validado_em": snapshot.VALIDADO_EM if origem == "snapshot" else None,
            "aviso": aviso,
        }

    def _consultar(
        self,
        chave_cache: str,
        sql: str,
        tabelas: tuple[str, ...],
        transformar: Callable[[list[dict[str, Any]]], Any],
        fallback: Callable[[], Any],
    ) -> Resultado:
        tabela_completa = ", ".join(self.tabela(t) for t in tabelas)
        if self._cliente is None:
            self._observador("snapshot", "sem_configuracao")
            return Resultado(fallback(), self._meta("snapshot", tabela_completa, None, AVISO_SNAPSHOT))

        agora = self._relogio()
        with self._trava:
            item = self._cache.get(chave_cache)
            if item and item.expira_em > agora:
                self._observador("databricks", "cache")
                return item.valor

        try:
            linhas = self._cliente.executar(sql)
            resultado = Resultado(transformar(linhas), self._meta("databricks", tabela_completa, _agora_iso(), None))
        except DatabricksErro as exc:
            logger.warning("Falha ao consultar %s no Databricks: %s", tabela_completa, exc)
            self.estado.ultima_falha = _agora_iso()
            self.estado.falhas_consecutivas += 1
            self._observador("databricks", "erro")
            return Resultado(fallback(), self._meta("snapshot", tabela_completa, None, AVISO_FALLBACK))

        self.estado.ultima_consulta_ok = resultado.meta["consultado_em"]
        self.estado.falhas_consecutivas = 0
        self._observador("databricks", "ok")
        with self._trava:
            self._cache[chave_cache] = _ItemCache(agora + self._config.cache_ttl_s, resultado)
        return resultado

    def limpar_cache(self) -> None:
        with self._trava:
            self._cache.clear()

    # ------------------------------------------------------------------ consultas públicas
    def kpis(self) -> Resultado:
        def transformar(linhas: list[dict[str, Any]]) -> dict[str, Any]:
            if not linhas:
                raise DatabricksErro("Consulta de KPIs não retornou linhas")
            return _formatar_kpis(linhas[0])

        return self._consultar(
            "kpis",
            self._consultas.kpis,
            (FATO, DIM_TEMPO, CLIMA),
            transformar,
            lambda: _formatar_kpis(snapshot.KPIS),
        )

    def subprefeituras(self) -> Resultado:
        def transformar(linhas: list[dict[str, Any]]) -> dict[str, Any]:
            return {"itens": [_formatar_sub(l) for l in linhas], "demais": None}

        def fallback() -> dict[str, Any]:
            return {
                "itens": [_formatar_sub(l) for l in snapshot.SUBPREFEITURAS],
                "demais": dict(snapshot.DEMAIS_SUBPREFEITURAS),
            }

        return self._consultar(
            "subprefeituras",
            self._consultas.subprefeituras,
            (FATO, DIM_SUBPREFEITURA),
            transformar,
            fallback,
        )

    def mensal(self) -> Resultado:
        def transformar(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                {"mes": str(l["mes"])[:10], "total_ocorrencias": int(l["total_ocorrencias"] or 0)} for l in linhas
            ]

        return self._consultar(
            "mensal",
            self._consultas.mensal,
            (FATO, DIM_TEMPO),
            transformar,
            lambda: [dict(l) for l in snapshot.MENSAL],
        )

    def clima_diario(self) -> Resultado:
        def transformar(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                {
                    "data": str(l["data"])[:10],
                    "precipitacao_mm": _arred(l.get("precipitacao_mm")),
                    "precipitacao_acumulada_mm": _arred(l.get("precipitacao_acumulada_mm")),
                }
                for l in linhas
            ]

        return self._consultar(
            "clima",
            self._consultas.clima_diario,
            (CLIMA,),
            transformar,
            lambda: [dict(l) for l in snapshot.CLIMA_DIARIO],
        )

    def pontos(self) -> Resultado:
        def transformar(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
            pontos = []
            for l in linhas:
                if l.get("latitude") is None or l.get("longitude") is None:
                    continue
                pontos.append(
                    {
                        "id": str(l["id"]),
                        "data": (str(l["data"])[:10] if l.get("data") else None),
                        "tipo": l.get("tipo"),
                        "subprefeitura": l.get("subprefeitura"),
                        "latitude": float(l["latitude"]),
                        "longitude": float(l["longitude"]),
                    }
                )
            return pontos

        def fallback() -> list[dict[str, Any]]:
            if self._pontos_snapshot is None:
                self._pontos_snapshot = snapshot.carregar_pontos(self._config.snapshot_dir)
            return [dict(p) for p in self._pontos_snapshot]

        return self._consultar(
            "mapa",
            self._consultas.mapa(),
            (FATO, DIM_SUBPREFEITURA),
            transformar,
            fallback,
        )


# ---------------------------------------------------------------------- formatadores
def _arred(valor: Any) -> float | None:
    if valor is None:
        return None
    return round(float(valor), 1)


def _formatar_kpis(l: dict[str, Any]) -> dict[str, Any]:
    mes_inicio = str(l.get("mes_inicio") or "")[:7] or None
    mes_fim = str(l.get("mes_fim") or "")[:7] or None
    return {
        "alagamentos": {
            "total": int(l.get("total_alagamentos") or 0),
            "periodo_inicio": mes_inicio,
            "periodo_fim": mes_fim,
        },
        "subprefeituras_com_registros": int(l.get("subprefeituras_com_registros") or 0),
        "clima": {
            "chuva_acumulada_mm": _arred(l.get("chuva_acumulada_mm")),
            "maior_chuva_diaria_mm": _arred(l.get("maior_chuva_diaria_mm")),
            "data_maior_chuva": (str(l["data_maior_chuva"])[:10] if l.get("data_maior_chuva") else None),
            "periodo_inicio": (str(l["periodo_inicio"])[:10] if l.get("periodo_inicio") else None),
            "periodo_fim": (str(l["periodo_fim"])[:10] if l.get("periodo_fim") else None),
            "ponto_referencia": {"latitude": -23.55, "longitude": -46.63, "descricao": "Região central de São Paulo"},
        },
    }


def _formatar_sub(l: dict[str, Any]) -> dict[str, Any]:
    return {
        "codigo": l.get("codigo_subprefeitura"),
        "subprefeitura": nome_exibicao(l.get("subprefeitura")),
        "chave": chave(l.get("subprefeitura")),
        "total_ocorrencias": int(l.get("total_ocorrencias") or 0),
        "primeira_ocorrencia": (str(l["primeira_ocorrencia"])[:10] if l.get("primeira_ocorrencia") else None),
        "ultima_ocorrencia": (str(l["ultima_ocorrencia"])[:10] if l.get("ultima_ocorrencia") else None),
    }
