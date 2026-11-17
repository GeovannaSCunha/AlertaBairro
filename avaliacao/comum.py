"""Utilitários compartilhados pela avaliação do assistente (disciplina de IA Generativa).

Usa o MESMO código do produto (backend/app/assistente) para que o que é medido aqui seja
exatamente o que roda no site: tokenização, BM25, guardrails, prompt e validação do JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

from app.assistente.busca import IndiceBM25, Trecho  # noqa: E402

BASE = RAIZ / "base" / "trechos.json"
CASOS = RAIZ / "avaliacao" / "casos_teste.jsonl"
RESULTADOS = RAIZ / "avaliacao" / "resultados"


def carregar_trechos(caminho: Path = BASE) -> list[Trecho]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))["dados"]
    return [Trecho(**t) for t in dados]


def carregar_casos(caminho: Path = CASOS) -> list[dict]:
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]


def indice(trechos: list[Trecho] | None = None) -> IndiceBM25:
    return IndiceBM25(trechos if trechos is not None else carregar_trechos())


def salvar_json(nome: str, obj: object) -> Path:
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    caminho = RESULTADOS / nome
    caminho.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho
