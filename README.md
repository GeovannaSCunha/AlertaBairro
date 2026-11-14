# AlertaBairro

**Histórico de alagamentos e chuva em São Paulo num mapa simples e colaborativo.**
Projeto CitizenTech da Global Solution FIAP 2026.2 (Engenharia de Software, 4º ano).

> O AlertaBairro mostra dados **históricos** e relatos da comunidade. Não é um serviço oficial de alerta nem faz previsão.
> Em perigo, ligue **193** (Bombeiros) ou **199** (Defesa Civil).

## Integrantes

| Nome completo | RM |
| --- | --- |
| Geovanna Silva Cunha | _RM a preencher_ |
| _Integrante_ | _RM_ |

## Ficha Técnica do MVP

| Item | Descrição |
| --- | --- |
| **Produto** | AlertaBairro |
| **Cidadão e território** | Moradores, trabalhadores e comerciantes de São Paulo, especialmente em subprefeituras com histórico de alagamento (São Miguel Paulista concentra 113 dos 292 registros da base). |
| **Problema** | Em dias de chuva, as informações sobre alagamentos estão dispersas em fontes diferentes e são difíceis de consultar por bairro. |
| **Proposta de valor** | Reunir num só lugar o histórico público de alagamentos, a chuva e os relatos dos moradores, com linguagem simples e a origem de cada número visível. |
| **Arquitetura** | Airflow → Databricks (Bronze/Prata/Ouro) → API FastAPI → frontend Next.js. Relatos em SQLite na API. Detalhes em [docs/arquitetura.md](docs/arquitetura.md). |
| **Fontes de dados** | GeoSampa/Defesa Civil (alagamentos), Open-Meteo (chuva) e relatos moderados da comunidade. |
| **Modelos de IA** | Índice experimental por regras explicáveis; assistente com busca BM25 + geração fundamentada (LLM local via Ollama, opcional) com citação de fonte e recusa. Veja [docs/assistente-ia.md](docs/assistente-ia.md). |
| **URL do MVP e repositório** | _URL pública a preencher após o deploy_ · https://github.com/GeovannaSCunha/AlertaBairro |
| **Indicadores de impacto** | Cobertura (ocorrências e subprefeituras mapeadas), qualidade (origem e data dos dados) e uso (relatos recebidos, taxa de aprovação, perguntas respondidas). Rota `GET /api/v1/indicadores`. |
| **ODS conectados** | ODS 11 (Cidades e comunidades sustentáveis) e ODS 13 (Ação contra a mudança global do clima). |

### As seis perguntas do briefing

1. **Quem é o cidadão?** Quem mora, trabalha ou tem comércio em regiões de São Paulo sujeitas a alagamento.
2. **Qual problema?** Falta de um lugar único, local e compreensível para consultar o histórico de alagamentos e registrar o que acontece na rua.
3. **Como funciona?** O morador escolhe a região, vê o histórico no mapa e nos gráficos, entende a chuva, envia relatos (moderados) e pode perguntar ao assistente.
4. **Quais tecnologias?** Airflow, Databricks (Delta/Unity Catalog), FastAPI, Next.js, Leaflet, Docker, GitHub Actions, Prometheus/Grafana e LLM local.
5. **Quem participa do ecossistema?** Moradores (relatos), equipe de moderação, fontes públicas (Prefeitura/Defesa Civil, Open-Meteo) e, no modelo de negócio, associações e instituições que usam painéis.
6. **Como medir e ampliar o impacto?** Indicadores de cobertura, qualidade e uso; expansão para outras cidades com o mesmo pipeline.

## O que o MVP faz

| Tela | Rota | O que mostra | Dados (tabela) |
| --- | --- | --- | --- |
| Início | `/` | Seletor de região com o histórico, fatos da base e participação | `ouro_alagamentos_subprefeitura`, `ouro_clima_diario` |
| Mapa | `/mapa` | Pontos históricos e relatos aprovados, com filtros por subprefeitura e mês | `prata_alagamentos` + relatos |
| Regiões | `/regioes` | Ranking por subprefeitura e série mensal (julho indicado como lacuna) | `ouro_alagamentos_subprefeitura`, `ouro_alagamentos_mensal` |
| Chuva | `/chuva` | Chuva diária e acumulada e explicação do que significam os milímetros | `ouro_clima_diario` |
| Índice | `/indice` | Índice experimental de atenção com regras abertas e simulação por data | Ouro + regras em `backend/app/indice.py` |
| Assistente | `/assistente` | Perguntas em linguagem natural, respostas com fonte e recusa de previsões | Base de conhecimento do assistente |
| Relatar | `/relatar` | Formulário com mapa, foto opcional e protocolo de acompanhamento | Banco da API |
| Moderação | `/moderacao` | Fila para aprovar ou rejeitar relatos (protegida por token) | Banco da API |
| Sobre | `/sobre` | Fontes, pipeline, limites, LGPD e situação das integrações | — |

Cada bloco de dados mostra a **tabela de origem**, se o valor veio do **Databricks** ou do **snapshot** e a data de validação.

## Como rodar

### Com Docker (recomendado)

```bash
cp .env.example .env          # preencha ADMIN_TOKEN e, se tiver, as variáveis do Databricks
docker compose up --build
```

- Web: http://localhost:3000
- API e documentação interativa: http://localhost:8000/api/docs
- Com observabilidade: `docker compose --profile observabilidade up --build` (Prometheus em :9090, Grafana em :3001)

### Sem Docker

```bash
# API (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export ADMIN_TOKEN=um-token-com-16-ou-mais-caracteres
uvicorn app.main:app --reload --port 8000

# Web (Node 20.9+), em outro terminal
cd frontend
npm install
API_URL=http://localhost:8000 npm run dev
```

Sem as variáveis do Databricks, a API usa o **snapshot validado em 13/11/2026** (valores do relatório técnico) e tudo funciona, exceto os pontos históricos do mapa. Para eles, conecte o Databricks ([docs/databricks.md](docs/databricks.md)) ou exporte a Prata em CSV ([backend/data/snapshot/README.md](backend/data/snapshot/README.md)).

## Testes

```bash
cd backend && pytest --cov=app        # unidade + API (FastAPI TestClient)
cd frontend && npm run typecheck && npm run build
```

Os testes cobrem: contrato do snapshot com o relatório (292 = soma mensal = ranking + demais), cliente do Databricks (polling, conversão de tipos, erro, paginação), fallback e cache, índice (faixas, chuva vencida, simulação), relatos (validação, dados pessoais, EXIF removido, moderação, retenção de fotos), assistente (guardrails, busca, recusa, validação do JSON do LLM) e API (rotas, limites de taxa, autenticação da moderação, métricas).

## API

| Método e rota | Descrição |
| --- | --- |
| `GET /api/v1/health` | Processo vivo (não testa o Databricks) |
| `GET /api/v1/status` | Origem dos dados (databricks/snapshot), falhas e modo do assistente |
| `GET /api/v1/kpis` | 4 indicadores e períodos |
| `GET /api/v1/alagamentos/subprefeituras?limit=10` | Ranking e soma das demais |
| `GET /api/v1/alagamentos/mensal` | Série mensal e meses sem linha |
| `GET /api/v1/clima/diario` | Chuva diária e acumulada |
| `GET /api/v1/alagamentos/mapa?subprefeitura=&mes=AAAA-MM` | Pontos da Prata com filtros |
| `GET /api/v1/indice?data_referencia=AAAA-MM-DD` | Índice experimental (opcionalmente simulado) |
| `GET /api/v1/indicadores` | Cobertura, qualidade e participação |
| `POST /api/v1/relatos` | Novo relato (multipart; fica pendente) |
| `GET /api/v1/relatos` | Relatos aprovados |
| `GET /api/v1/relatos/protocolo/{AB-XXXXXX}` | Situação de um relato |
| `GET/POST /api/v1/moderacao/relatos[/{id}]` | Fila e decisões (Bearer `ADMIN_TOKEN`) |
| `POST /api/v1/assistente` | Pergunta → `{resposta, fontes, recusou, modo}` |
| `GET /api/v1/assistente/base` | Exporta a base de conhecimento (para avaliação da IA) |
| `GET /metrics` | Métricas Prometheus |

Toda resposta de dados segue o envelope `{"dados": ..., "meta": {"origem", "tabela", "natureza", "consultado_em", "snapshot_validado_em", "aviso"}}`.

## Segurança e LGPD

- **Credenciais fora do código:** Databricks, `ADMIN_TOKEN` e LLM só por variáveis de ambiente; `.env` no `.gitignore`. O navegador fala apenas com o próprio frontend, que encaminha para a API; o token do Databricks nunca sai do servidor.
- **SQL fixo e somente leitura:** catálogo e schema validados como identificadores; nenhum texto do usuário ou da IA vira SQL.
- **Dados pessoais minimizados:** relatos sem nome, e-mail ou telefone; descrição recusada se contiver e-mail, CPF ou telefone; coordenadas arredondadas (~110 m); fotos regravadas sem EXIF/GPS no navegador e no servidor; fotos de relatos rejeitados apagadas na hora e as demais após 90 dias.
- **Controles:** limite de taxa por IP (relatos, assistente, protocolo e moderação), moderação com token comparado em tempo constante, CSP e cabeçalhos de segurança, containers não root com sistema de arquivos somente leitura.
- **Pipeline:** GitHub Actions com testes, Gitleaks, Semgrep e Trivy (dependências e imagens).

## Observabilidade

`/metrics` expõe os quatro sinais de ouro: latência (`http_request_duration_seconds`), tráfego (`http_requests_total`), erros (status 5xx) e saturação (`http_requests_em_andamento`). Também expõe métricas de produto, como a origem dos dados, os relatos e as respostas do assistente. O perfil `observabilidade` sobe o Prometheus com quatro alertas (`observabilidade/alertas.yml`) e o Grafana com um painel já provisionado. Os logs saem em JSON, sem segredos.

## Limites conhecidos

- Os dados são históricos: alagamentos de jan–set/2026 e chuva de 28/10–06/11/2026, sem sobreposição; por isso o app não afirma correlação.
- Julho de 2026 não tem linha na tabela mensal (lacuna, não zero).
- A chuva vem de um único ponto de referência.
- O envio dos lotes do Airflow ao Databricks ainda é manual.
- Os relatos ficam em SQLite (uma instância). Para escalar: PostgreSQL/PostGIS.

## Estrutura

```
backend/            API FastAPI (dados, índice, relatos, assistente), testes e Dockerfile
  app/dados/        cliente Databricks, SQL fixo, snapshot e fallback
  app/assistente/   base de conhecimento, BM25, guardrails, modo regras e cliente LLM
  base_conhecimento/ documentos com fonte usados pelo assistente
frontend/           Next.js (App Router), tema "Céu nublado", mapa Leaflet e gráficos SVG
observabilidade/    Prometheus, alertas e painel Grafana
docs/               arquitetura, Databricks, assistente de IA e deploy
```
