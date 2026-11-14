"""Busca lexical BM25 sobre os trechos da base de conhecimento (sem dependências externas)."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from app.texto import sem_acentos

STOPWORDS = set(
    """a o as os um uma uns umas de do da dos das no na nos nas em por para pra com sem sobre
    e ou que qual quais quem quanto quantos quanta quantas como onde quando porque se nao sim
    eu voce voces ele ela eles elas meu minha seu sua nosso nossa isso isto esse essa este esta
    ao aos foi ser e ha tem ter teve mais menos muito muita me te lhe nos vos ja tambem
    pode posso algum alguma sobre dia dias mes meses""".split()
)


@dataclass(frozen=True)
class Trecho:
    id: str
    titulo: str
    texto: str
    fonte: str
    tipo: str = "dados"  # "dados" (gerado do lakehouse) ou "documento" (base estática)


@dataclass(frozen=True)
class Achado:
    trecho: Trecho
    score: float
    termos_casados: int = 0
    termos_consulta: int = 0

    @property
    def cobertura(self) -> float:
        return self.termos_casados / self.termos_consulta if self.termos_consulta else 0.0


_SUFIXOS = ("amento", "imento", "mente", "acao", "icao", "ando", "endo", "indo", "aram", "eram",
            "ada", "ado", "ida", "ido", "ar", "er", "ir", "ou", "eu", "iu")


def radical(t: str) -> str:
    """Radical leve para português: "alagamentos", "alagada" e "alagar" viram "alag"."""
    if len(t) > 4 and t.endswith("s"):
        t = t[:-1]
    for sufixo in _SUFIXOS:
        if t.endswith(sufixo) and len(t) - len(sufixo) >= 4:
            return t[: -len(sufixo)]
    return t


def tokenizar(texto: str) -> list[str]:
    texto = sem_acentos(texto.lower())
    tokens = re.findall(r"[a-z0-9]+", texto)
    return [radical(t) for t in tokens if t not in STOPWORDS and len(t) >= 2]


class IndiceBM25:
    def __init__(self, trechos: Sequence[Trecho], k1: float = 1.5, b: float = 0.75) -> None:
        self.trechos = list(trechos)
        self.k1 = k1
        self.b = b
        self._docs = [Counter(tokenizar(f"{t.titulo} {t.texto}")) for t in self.trechos]
        self._tamanhos = [sum(d.values()) for d in self._docs]
        self._media = (sum(self._tamanhos) / len(self._tamanhos)) if self._tamanhos else 0.0
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(d.keys())
        n = len(self._docs)
        self._idf = {termo: math.log(1 + (n - f + 0.5) / (f + 0.5)) for termo, f in df.items()}

    def buscar(self, consulta: str, k: int = 5) -> list[Achado]:
        termos = list(dict.fromkeys(tokenizar(consulta)))
        if not termos or not self.trechos:
            return []
        resultados = []
        for i, doc in enumerate(self._docs):
            score = 0.0
            casados = 0
            for termo in termos:
                f = doc.get(termo, 0)
                if not f:
                    continue
                casados += 1
                idf = self._idf.get(termo, 0.0)
                denom = f + self.k1 * (1 - self.b + self.b * self._tamanhos[i] / (self._media or 1))
                score += idf * f * (self.k1 + 1) / denom
            if score > 0:
                resultados.append(Achado(self.trechos[i], round(score, 4), casados, len(termos)))
        resultados.sort(key=lambda a: a.score, reverse=True)
        return resultados[:k]
