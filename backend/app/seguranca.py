"""Controles de segurança da API: limite de taxa, identificação do cliente e acesso de moderação."""

from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque
from typing import Callable

from app.config import Config


class LimitadorTaxa:
    """Janela deslizante em memória (suficiente para uma instância do MVP)."""

    def __init__(self, relogio: Callable[[], float] = time.monotonic) -> None:
        self._eventos: dict[str, deque[float]] = defaultdict(deque)
        self._trava = threading.Lock()
        self._relogio = relogio

    def permitir(self, chave: str, limite: int, janela_s: float) -> bool:
        agora = self._relogio()
        with self._trava:
            fila = self._eventos[chave]
            while fila and fila[0] <= agora - janela_s:
                fila.popleft()
            if len(fila) >= limite:
                return False
            fila.append(agora)
            if len(self._eventos) > 10_000:  # evita crescimento ilimitado
                for k in [k for k, v in self._eventos.items() if not v]:
                    del self._eventos[k]
            return True


def ip_cliente(cabecalhos: dict[str, str] | object, host: str | None, confiar_proxy: bool) -> str:
    """Usa o primeiro IP de X-Forwarded-For quando a API está atrás do proxy do frontend."""
    if confiar_proxy:
        encaminhado = getattr(cabecalhos, "get", lambda _k, _d=None: None)("x-forwarded-for")
        if encaminhado:
            return encaminhado.split(",")[0].strip()[:64]
    return host or "desconhecido"


def token_admin_valido(config: Config, autorizacao: str | None) -> bool:
    if not config.moderacao_habilitada or not autorizacao:
        return False
    esquema, _, token = autorizacao.partition(" ")
    if esquema.lower() != "bearer" or not token:
        return False
    return hmac.compare_digest(token.strip().encode(), (config.admin_token or "").encode())
