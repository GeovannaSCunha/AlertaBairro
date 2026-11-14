"""Configuração lida exclusivamente de variáveis de ambiente.

Nenhuma credencial fica no código. Veja `.env.example` na raiz do repositório.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _env(nome: str, padrao: str | None = None) -> str | None:
    valor = os.getenv(nome)
    if valor is None or valor.strip() == "":
        return padrao
    return valor.strip()


def _env_int(nome: str, padrao: int) -> int:
    valor = _env(nome)
    if valor is None:
        return padrao
    try:
        return int(valor)
    except ValueError as exc:  # configuração inválida deve falhar cedo
        raise ValueError(f"Variável {nome} deve ser um número inteiro") from exc


def _env_bool(nome: str, padrao: bool) -> bool:
    valor = _env(nome)
    if valor is None:
        return padrao
    return valor.lower() in {"1", "true", "sim", "yes", "on"}


def _identificador(nome: str, valor: str) -> str:
    """Catálogo e schema entram no SQL; por isso só aceitamos identificadores simples."""
    if not _IDENTIFICADOR.match(valor):
        raise ValueError(f"{nome} contém caracteres não permitidos: {valor!r}")
    return valor


@dataclass(frozen=True)
class Config:
    # Databricks (SQL Statement Execution API 2.0)
    databricks_host: str | None = None
    databricks_token: str | None = None
    databricks_warehouse_id: str | None = None
    databricks_catalog: str = "workspace"
    databricks_schema: str = "alertabairro"
    databricks_timeout_s: int = 35
    cache_ttl_s: int = 600

    # Persistência local (relatos da comunidade)
    db_path: str = "data/alertabairro.db"
    uploads_dir: str = "data/uploads"
    snapshot_dir: str = "data/snapshot"
    base_conhecimento_dir: str = "base_conhecimento"
    retencao_fotos_dias: int = 90

    # Segurança
    admin_token: str | None = None
    cors_origens: tuple[str, ...] = field(default_factory=tuple)
    confiar_proxy: bool = True
    limite_relatos_por_hora: int = 5
    limite_assistente_por_minuto: int = 20

    # Assistente de IA (endpoint compatível com OpenAI, ex.: Ollama local)
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_timeout_s: int = 60

    @property
    def databricks_configurado(self) -> bool:
        return bool(self.databricks_host and self.databricks_token and self.databricks_warehouse_id)

    @property
    def llm_configurado(self) -> bool:
        return bool(self.llm_base_url and self.llm_model)

    @property
    def moderacao_habilitada(self) -> bool:
        return bool(self.admin_token) and len(self.admin_token or "") >= 16


def carregar_config() -> Config:
    origens = _env("CORS_ORIGENS", "") or ""
    return Config(
        databricks_host=(_env("DATABRICKS_HOST") or "").rstrip("/") or None,
        databricks_token=_env("DATABRICKS_TOKEN"),
        databricks_warehouse_id=_env("DATABRICKS_WAREHOUSE_ID"),
        databricks_catalog=_identificador("DATABRICKS_CATALOG", _env("DATABRICKS_CATALOG", "workspace") or "workspace"),
        databricks_schema=_identificador("DATABRICKS_SCHEMA", _env("DATABRICKS_SCHEMA", "alertabairro") or "alertabairro"),
        databricks_timeout_s=_env_int("DATABRICKS_TIMEOUT_S", 35),
        cache_ttl_s=_env_int("CACHE_TTL_S", 600),
        db_path=_env("DB_PATH", "data/alertabairro.db") or "data/alertabairro.db",
        uploads_dir=_env("UPLOADS_DIR", "data/uploads") or "data/uploads",
        snapshot_dir=_env("SNAPSHOT_DIR", "data/snapshot") or "data/snapshot",
        base_conhecimento_dir=_env("BASE_CONHECIMENTO_DIR", "base_conhecimento") or "base_conhecimento",
        retencao_fotos_dias=_env_int("RETENCAO_FOTOS_DIAS", 90),
        admin_token=_env("ADMIN_TOKEN"),
        cors_origens=tuple(o.strip() for o in origens.split(",") if o.strip()),
        confiar_proxy=_env_bool("CONFIAR_PROXY", True),
        limite_relatos_por_hora=_env_int("LIMITE_RELATOS_POR_HORA", 5),
        limite_assistente_por_minuto=_env_int("LIMITE_ASSISTENTE_POR_MINUTO", 20),
        llm_base_url=(_env("LLM_BASE_URL") or "").rstrip("/") or None,
        llm_model=_env("LLM_MODEL"),
        llm_api_key=_env("LLM_API_KEY"),
        llm_timeout_s=_env_int("LLM_TIMEOUT_S", 60),
    )
