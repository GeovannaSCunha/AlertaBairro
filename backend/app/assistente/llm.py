"""Cliente de LLM via API compatível com OpenAI (/v1/chat/completions).

Funciona com um modelo LOCAL servido pelo Ollama (ex.: LLM_BASE_URL=http://localhost:11434/v1,
LLM_MODEL=qwen2.5:3b-instruct), com vLLM, com o LM Studio ou com o seu modelo afinado (LoRA)
publicado por um desses servidores. Não exige chave quando o servidor é local.

A geração é FUNDAMENTADA: o modelo recebe apenas os trechos recuperados e deve devolver
JSON {"resposta", "fontes", "recusou"}; o JSON é validado antes de chegar ao usuário.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Callable, Sequence

from app.assistente.busca import Achado

logger = logging.getLogger("alertabairro.llm")

PROMPT_SISTEMA = """Você é o assistente do AlertaBairro, uma plataforma cidadã sobre alagamentos em São Paulo.
Regras obrigatórias:
1. Responda SOMENTE com base nos TRECHOS fornecidos. Não use conhecimento externo.
2. Os dados são HISTÓRICOS. Nunca faça previsão, nunca diga que vai ou não alagar, nunca fale de "agora".
3. Se os trechos não respondem à pergunta, recuse: "recusou": true e diga que não consta na base.
4. Cite os IDs dos trechos usados em "fontes" (ex.: ["sub:SAOMIGUELPAULISTA"]).
5. Português do Brasil, linguagem simples, no máximo 4 frases. Números exatamente como nos trechos.
6. Em perigo, oriente ligar 193 (Bombeiros) ou 199 (Defesa Civil).
Responda APENAS com JSON válido no formato:
{"resposta": "texto", "fontes": ["id1", "id2"], "recusou": false}"""

Transporte = Callable[[str, dict[str, Any], dict[str, str], int], dict[str, Any]]


class ErroLLM(RuntimeError):
    pass


def montar_mensagens(pergunta: str, achados: Sequence[Achado]) -> list[dict[str, str]]:
    blocos = [f"[{a.trecho.id}] {a.trecho.titulo}: {a.trecho.texto} (fonte: {a.trecho.fonte})" for a in achados]
    contexto = "\n".join(blocos) if blocos else "(nenhum trecho relevante encontrado)"
    return [
        {"role": "system", "content": PROMPT_SISTEMA},
        {"role": "user", "content": f"TRECHOS:\n{contexto}\n\nPERGUNTA: {pergunta}"},
    ]


def validar_saida(conteudo: str, ids_permitidos: set[str]) -> dict[str, Any]:
    """Valida o JSON do modelo. Lança ErroLLM se o formato ou as citações forem inválidos."""
    texto = conteudo.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        texto = texto[texto.find("{"):]
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ErroLLM("Saída sem objeto JSON")
    try:
        obj = json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError as exc:
        raise ErroLLM(f"JSON inválido: {exc.msg}") from None
    resposta = obj.get("resposta")
    fontes = obj.get("fontes", [])
    recusou = obj.get("recusou", False)
    if not isinstance(resposta, str) or not resposta.strip():
        raise ErroLLM("Campo 'resposta' ausente ou vazio")
    if not isinstance(fontes, list) or not all(isinstance(f, str) for f in fontes):
        raise ErroLLM("Campo 'fontes' deve ser lista de strings")
    if not isinstance(recusou, bool):
        raise ErroLLM("Campo 'recusou' deve ser booleano")
    invalidas = [f for f in fontes if f not in ids_permitidos]
    if invalidas:
        raise ErroLLM(f"Citações fora do contexto: {invalidas}")
    if not recusou and not fontes:
        raise ErroLLM("Resposta afirmativa sem citação de fonte")
    return {"resposta": resposta.strip()[:1200], "fontes": fontes, "recusou": recusou}


class ClienteLLM:
    def __init__(
        self,
        base_url: str,
        modelo: str,
        api_key: str | None = None,
        timeout_s: int = 60,
        transporte: Transporte | None = None,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._modelo = modelo
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._transporte = transporte or self._http

    @property
    def modelo(self) -> str:
        return self._modelo

    def _http(self, url: str, corpo: dict[str, Any], cabecalhos: dict[str, str], timeout: int) -> dict[str, Any]:
        req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"), method="POST", headers=cabecalhos)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 nosemgrep - URL vem da configuração
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ErroLLM(f"HTTP {exc.code} do servidor de LLM") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ErroLLM(f"Servidor de LLM indisponível: {type(exc).__name__}") from None
        except json.JSONDecodeError:
            raise ErroLLM("Servidor de LLM respondeu algo que não é JSON") from None

    def gerar(self, pergunta: str, achados: Sequence[Achado]) -> dict[str, Any]:
        cabecalhos = {"Content-Type": "application/json"}
        if self._api_key:
            cabecalhos["Authorization"] = f"Bearer {self._api_key}"
        corpo = {
            "model": self._modelo,
            "messages": montar_mensagens(pergunta, achados),
            "temperature": 0.1,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }
        obj = self._transporte(self._url, corpo, cabecalhos, self._timeout_s)
        try:
            conteudo = obj["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ErroLLM("Resposta do servidor de LLM fora do formato esperado") from None
        return validar_saida(conteudo, {a.trecho.id for a in achados})
