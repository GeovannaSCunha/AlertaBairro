"""Cliente mínimo da Databricks SQL Statement Execution API 2.0.

Segue o padrão descrito no relatório técnico do projeto (seção 08/11):
POST /api/2.0/sql/statements -> polling em GET /api/2.0/sql/statements/{id}.

Regras de uso:
- somente o servidor executa SQL; o app, o usuário e a IA nunca enviam texto SQL;
- o token fica em variável de ambiente e nunca aparece em logs ou mensagens de erro.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Callable

logger = logging.getLogger("alertabairro.databricks")

Transporte = Callable[[str, str, dict[str, Any] | None], dict[str, Any]]

_TIPOS_INTEIROS = {"INT", "INTEGER", "LONG", "BIGINT", "SHORT", "SMALLINT", "TINYINT", "BYTE"}
_TIPOS_DECIMAIS = {"DOUBLE", "FLOAT", "DECIMAL", "REAL"}
_ESTADOS_FINAIS_ERRO = {"FAILED", "CANCELED", "CLOSED"}


class DatabricksErro(RuntimeError):
    """Falha ao consultar o Databricks. A mensagem nunca contém o token."""


def converter_valor(valor: Any, tipo: str | None) -> Any:
    """A API devolve números como strings em JSON_ARRAY; convertemos pelo tipo do manifesto."""
    if valor is None:
        return None
    tipo_base = (tipo or "").upper().split("(")[0]
    try:
        if tipo_base in _TIPOS_INTEIROS:
            return int(valor)
        if tipo_base in _TIPOS_DECIMAIS:
            return float(valor)
        if tipo_base == "BOOLEAN":
            return str(valor).lower() == "true"
    except (TypeError, ValueError):
        return valor
    return valor


def linhas_do_resultado(obj: dict[str, Any]) -> list[dict[str, Any]]:
    manifesto = obj.get("manifest") or {}
    if manifesto.get("truncated"):
        raise DatabricksErro("Resultado truncado; reduza o LIMIT ou implemente paginação")
    resultado = obj.get("result") or {}
    if resultado.get("next_chunk_internal_link"):
        raise DatabricksErro("Resultado com mais de um bloco; implemente paginação")
    colunas = (manifesto.get("schema") or {}).get("columns") or []
    nomes = [c.get("name") for c in colunas]
    tipos = [c.get("type_name") for c in colunas]
    linhas = resultado.get("data_array") or []
    return [
        {nome: converter_valor(valor, tipo) for nome, valor, tipo in zip(nomes, linha, tipos, strict=False)}
        for linha in linhas
    ]


class ClienteDatabricks:
    def __init__(
        self,
        host: str,
        token: str,
        warehouse_id: str,
        catalog: str = "workspace",
        schema: str = "alertabairro",
        timeout_s: int = 35,
        max_polls: int = 12,
        intervalo_s: float = 2.0,
        transporte: Transporte | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if not host.startswith("https://"):
            raise ValueError("DATABRICKS_HOST deve começar com https://")
        self._host = host.rstrip("/")
        self._token = token
        self._warehouse_id = warehouse_id
        self._catalog = catalog
        self._schema = schema
        self._timeout_s = timeout_s
        self._max_polls = max_polls
        self._intervalo_s = intervalo_s
        self._transporte = transporte or self._http
        self._dormir = dormir

    def __repr__(self) -> str:  # nunca expor o token
        return f"ClienteDatabricks(host={self._host!r}, warehouse_id={self._warehouse_id!r})"

    def _http(self, metodo: str, caminho: str, corpo: dict[str, Any] | None) -> dict[str, Any]:
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(
            f"{self._host}{caminho}",
            data=dados,
            method=metodo,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "AlertaBairro-API/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:  # nosec B310 nosemgrep - host https validado
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise DatabricksErro(f"HTTP {exc.code} ao chamar a Statement Execution API") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise DatabricksErro(f"Falha de rede ao chamar o Databricks: {type(exc).__name__}") from None
        except json.JSONDecodeError:
            raise DatabricksErro("Resposta do Databricks não é JSON válido") from None

    def executar(self, sql: str, row_limit: int = 1000) -> list[dict[str, Any]]:
        corpo = {
            "warehouse_id": self._warehouse_id,
            "catalog": self._catalog,
            "schema": self._schema,
            "statement": sql,
            "format": "JSON_ARRAY",
            "disposition": "INLINE",
            "wait_timeout": "10s",
            "on_wait_timeout": "CONTINUE",
            "row_limit": row_limit,
        }
        obj = self._transporte("POST", "/api/2.0/sql/statements", corpo)

        for _ in range(self._max_polls):
            estado = (obj.get("status") or {}).get("state")
            if estado == "SUCCEEDED":
                return linhas_do_resultado(obj)
            if estado in _ESTADOS_FINAIS_ERRO:
                erro = ((obj.get("status") or {}).get("error") or {}).get("error_code", "desconhecido")
                raise DatabricksErro(f"Consulta terminou em {estado} ({erro})")
            statement_id = obj.get("statement_id")
            if not statement_id:
                raise DatabricksErro("Resposta sem statement_id para acompanhar a consulta")
            self._dormir(self._intervalo_s)
            obj = self._transporte("GET", f"/api/2.0/sql/statements/{statement_id}", None)

        raise DatabricksErro("Consulta SQL não terminou no prazo")
