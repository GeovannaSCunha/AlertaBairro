# syntax=docker/dockerfile:1.7
# API FastAPI: imagem slim, dependências em camada separada, usuário não root, sem segredos na imagem.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_PATH=/app/var/alertabairro.db \
    UPLOADS_DIR=/app/var/uploads
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN groupadd --system app && useradd --system --gid app --home /app app
COPY --chown=app:app app ./app
COPY --chown=app:app base_conhecimento ./base_conhecimento
COPY --chown=app:app data/snapshot ./data/snapshot
# Única pasta gravável: banco de relatos e fotos (montar um volume aqui)
RUN mkdir -p /app/var/uploads && chown -R app:app /app/var

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
