# Publicar o MVP

O critério de aceite pede uma **URL pública** que o avaliador use sem explicação. Os dois serviços são containers independentes:

| Serviço | Pasta | Porta | Variáveis |
| --- | --- | --- | --- |
| API | `backend/` | 8000 | `ADMIN_TOKEN`, `DATABRICKS_*` (opcional), `LLM_*` (opcional), `CORS_ORIGENS` (só se o navegador chamar a API direto) |
| Web | `frontend/` | 3000 | `API_URL` = endereço da API |

## Caminho rápido (qualquer plataforma que rode Dockerfile)

1. Crie um serviço web a partir de `backend/Dockerfile`. Configure as variáveis e anote a URL gerada (ex.: `https://alertabairro-api.exemplo.com`).
2. Teste `https://.../api/v1/health` e `https://.../api/v1/status`.
3. Crie outro serviço a partir de `frontend/Dockerfile`, com `API_URL` igual à URL da API.
4. Abra a URL do frontend e siga os 5 passos da página inicial.
5. Se a plataforma oferecer disco persistente, monte-o em `/app/var` para não perder relatos e fotos a cada deploy.

## Checklist antes de entregar

- [ ] URL pública abrindo em janela anônima, no celular e no computador
- [ ] `/api/v1/status` mostrando `databricks` (ou o snapshot, se o warehouse estiver desligado)
- [ ] `ADMIN_TOKEN` forte configurado e um relato de teste aprovado, para o mapa não ficar vazio
- [ ] CSV da Prata exportado em `backend/data/snapshot/` (garante os pontos do mapa mesmo sem Databricks)
- [ ] Pipeline do GitHub Actions verde
- [ ] README com integrantes, RM e URL preenchidos

Para a disciplina de Secure DevOps, este repositório já tem os Dockerfiles não root, o `docker-compose`, o workflow com Gitleaks, Semgrep e Trivy e a observabilidade. Faltam o Terraform da nuvem escolhida e o deploy automático no workflow.
