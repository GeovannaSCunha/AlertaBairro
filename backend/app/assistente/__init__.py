"""Assistente analítico do AlertaBairro.

Arquitetura pensada para a disciplina Generative AI for Engineering:
  base de conhecimento (trechos com fonte) → busca (BM25 + limiar) → geração fundamentada
  (JSON com citação e recusa) → validação → resposta.

Dois modos:
  - "regras": sem LLM, determinístico; garante que o MVP funcione sem modelo.
  - "llm": qualquer endpoint compatível com a API do OpenAI, como o Ollama rodando localmente.
"""
