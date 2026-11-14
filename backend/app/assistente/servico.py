"""Orquestra o assistente: guardrails → base de conhecimento → busca → geração → validação."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import date
from typing import Any, Callable

from app import indice as indice_mod
from app.assistente import regras
from app.assistente.base_conhecimento import trechos_de_dados, trechos_de_documentos
from app.assistente.busca import IndiceBM25, Trecho
from app.assistente.guardrails import verificar
from app.assistente.llm import ClienteLLM, ErroLLM
from app.dados.fonte import FonteDados

logger = logging.getLogger("alertabairro.assistente")

TAMANHO_MAXIMO_PERGUNTA = 500
K_TRECHOS = 5


class ServicoAssistente:
    def __init__(
        self,
        fonte: FonteDados,
        pasta_documentos: str,
        llm: ClienteLLM | None = None,
        hoje: Callable[[], date] = date.today,
        ttl_indice_s: int = 300,
    ) -> None:
        self._fonte = fonte
        self._documentos = trechos_de_documentos(pasta_documentos)
        self._llm = llm
        self._hoje = hoje
        self._ttl = ttl_indice_s
        self._cache: tuple[float, dict[str, Any], IndiceBM25, dict[str, Trecho]] | None = None

    @property
    def modo(self) -> str:
        return "llm" if self._llm else "regras"

    def _contexto(self) -> tuple[dict[str, Any], IndiceBM25, dict[str, Trecho]]:
        agora = time.monotonic()
        if self._cache and self._cache[0] > agora:
            return self._cache[1], self._cache[2], self._cache[3]

        kpis = self._fonte.kpis()
        subs = self._fonte.subprefeituras()
        mensal = self._fonte.mensal()
        clima = self._fonte.clima_diario()
        ind = indice_mod.calcular(subs.dados["itens"], clima.dados, self._hoje())
        ctx = {
            "kpis": kpis.dados,
            "subprefeituras": subs.dados,
            "mensal": mensal.dados,
            "clima": clima.dados,
            "indice": ind,
        }
        trechos = trechos_de_dados(
            kpis.dados, kpis.meta, subs.dados, subs.meta, mensal.dados, mensal.meta, clima.dados, clima.meta, ind
        ) + self._documentos
        busca = IndiceBM25(trechos)
        por_id = {t.id: t for t in trechos}
        self._cache = (agora + self._ttl, ctx, busca, por_id)
        return ctx, busca, por_id

    def base(self) -> list[dict[str, Any]]:
        """Exporta a base de conhecimento (útil para os notebooks de avaliação da disciplina de IA)."""
        _, _, por_id = self._contexto()
        return [asdict(t) for t in por_id.values()]

    def responder(self, pergunta: str) -> dict[str, Any]:
        pergunta = " ".join((pergunta or "").split())[:TAMANHO_MAXIMO_PERGUNTA]
        verificacao = verificar(pergunta)
        if verificacao.categoria != "ok":
            return asdict(
                regras.Resposta(
                    resposta=verificacao.mensagem or "",
                    recusou=verificacao.categoria != "emergencia",
                    motivo_recusa=None if verificacao.categoria == "emergencia" else verificacao.categoria,
                    modo="guardrail",
                    fontes=[{"id": "doc:chuva_e_seguranca#2", "titulo": "Telefones de emergência",
                             "fonte": "Orientações gerais de Defesa Civil"}]
                    if verificacao.categoria == "emergencia"
                    else [],
                )
            ) | {"categoria": verificacao.categoria}

        ctx, busca, por_id = self._contexto()
        achados = busca.buscar(pergunta, k=K_TRECHOS)

        if self._llm is not None:
            try:
                saida = self._llm.gerar(pergunta, achados)
                fontes = [
                    {"id": por_id[f].id, "titulo": por_id[f].titulo, "fonte": por_id[f].fonte}
                    for f in saida["fontes"]
                    if f in por_id
                ]
                return asdict(
                    regras.Resposta(
                        resposta=saida["resposta"],
                        fontes=fontes,
                        recusou=saida["recusou"],
                        motivo_recusa="nao_consta" if saida["recusou"] else None,
                        modo=f"llm:{self._llm.modelo}",
                        ferramentas=["buscar_base"],
                    )
                ) | {"categoria": "ok"}
            except ErroLLM as exc:
                logger.warning("LLM falhou, usando modo regras: %s", exc)

        resposta = regras.responder(pergunta, ctx, achados, por_id)
        return asdict(resposta) | {"categoria": "ok"}
