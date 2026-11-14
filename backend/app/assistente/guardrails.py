"""Regras de segurança aplicadas ANTES de qualquer geração.

O relatório técnico define que a IA explica dados históricos e nunca promete previsão.
Exemplo aceito: "Segundo a base histórica, São Miguel Paulista possui 113 registros".
Exemplo proibido: "Hoje haverá alagamento em São Miguel Paulista".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.texto import sem_acentos

_EMERGENCIA = re.compile(
    r"\b(socorro|emergencia|ilhad[oa]s?|presos?\b.*\bagua|arrastad[oa]|afogando|desabou|desabamento|"
    r"agua (entrando|subindo) (em casa|na casa|no quarto)|estou preso|estamos presos)",
)
_PREVISAO = re.compile(
    r"(\b(vai|vao|ira|irao|pode|podera|deve|devera)\s+(alagar|chover|encher|transbordar|inundar)"
    r"|\bprevis(ao|oes)\b|\bprever\b|\bamanha\b|\bproxim[oa]s? (hora|horas|dia|dias|semana)\b"
    r"|\b(esta|ta|estao)\s+(alagando|chovendo|alagad[oa]|inundad[oa])\b"
    r"|\b(agora|neste momento|nesse momento|em tempo real|ao vivo)\b"
    r"|\bposso (sair|passar|ir)\b|\bdevo (sair|passar|ir|evitar)\b|\bseguro (sair|passar|ir)\b)",
)

MSG_EMERGENCIA = (
    "Se você ou alguém está em perigo agora, ligue imediatamente para os Bombeiros (193) "
    "ou para a Defesa Civil (199). Não atravesse áreas alagadas, nem a pé nem de carro, "
    "e procure um lugar alto e seguro. O AlertaBairro mostra apenas dados históricos e não aciona socorro."
)
MSG_PREVISAO = (
    "Não consigo responder isso. O AlertaBairro trabalha com dados históricos (alagamentos de "
    "janeiro a setembro de 2026 e chuva de 28/10 a 06/11/2026) e não faz previsão nem "
    "monitoramento em tempo real. Para a situação de agora, consulte o CGE da Prefeitura e a "
    "Defesa Civil (199). Posso contar o que a base histórica mostra sobre uma região, se quiser."
)


@dataclass(frozen=True)
class Verificacao:
    categoria: str  # "ok" | "emergencia" | "previsao" | "invalida"
    mensagem: str | None = None


def normalizar(pergunta: str) -> str:
    return " ".join(sem_acentos(pergunta.lower()).split())


def verificar(pergunta: str) -> Verificacao:
    texto = normalizar(pergunta)
    if len(texto) < 3:
        return Verificacao("invalida", "Escreva uma pergunta sobre os dados de alagamento ou de chuva.")
    if _EMERGENCIA.search(texto):
        return Verificacao("emergencia", MSG_EMERGENCIA)
    if _PREVISAO.search(texto):
        return Verificacao("previsao", MSG_PREVISAO)
    return Verificacao("ok")
