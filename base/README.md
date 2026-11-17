# Base de conhecimento do assistente

`trechos.json` é a base que o assistente do AlertaBairro usa para responder. Ela foi exportada da API em
execução (`GET /api/v1/assistente/base`) em 17/11/2026, com os dados vindos do Databricks (camada Ouro,
tabela pública pseudonimizada `ouro_fato_alagamentos_publica`).

Cada trecho tem:
- `id`: identificador estável, citado pelo modelo em `fontes`;
- `titulo` e `texto`: o conteúdo;
- `fonte`: a tabela ou o documento de origem, com a data da consulta;
- `tipo`: `dados` (gerado do lakehouse) ou `documento` (texto escrito pela equipe).

Os trechos são frases completas em português, e não linhas de tabela. Assim, o modelo recebe o número
junto com o contexto ("base histórica", "não é índice de risco"), e a busca encontra o trecho pelas
mesmas palavras que o cidadão usa.

## Composição

| Grupo (prefixo do id) | Origem | Formato de origem | Licença / termos | Nº de trechos |
|---|---|---|---|---|
| `kpi:` resumo da base | `workspace.alertabairro.ouro_fato_alagamentos_publica` + `ouro_dim_tempo` (GeoSampa / Defesa Civil, via Databricks) | Tabela Delta (Ouro) | Dados abertos do GeoSampa, Prefeitura de São Paulo ([licença de uso](https://prefeitura.sp.gov.br/web/licenciamento/w/desenvolvimento_urbano/dados_estatisticos/legislacao_sig-1)) | 1 |
| `sub:` alagamentos por subprefeitura | `ouro_fato_alagamentos_publica` + `ouro_dim_subprefeitura` | Tabela Delta (Ouro) | idem | 30 |
| `mes:` alagamentos por mês (inclui a lacuna de julho) | `ouro_fato_alagamentos_publica` + `ouro_dim_tempo` | Tabela Delta (Ouro) | idem | 9 |
| `indice:` índice experimental por subprefeitura | Calculado pela API a partir das tabelas Ouro (regras em `backend/app/indice.py`) | Regras documentadas | Derivado; mesmos termos das fontes | 30 |
| `clima:` resumo da chuva | `ouro_clima_diario` (Open-Meteo, via Databricks) | Tabela Delta (Ouro) | [CC BY 4.0](https://open-meteo.com/en/license) | 1 |
| `chuva:` chuva por dia | `ouro_clima_diario` | Tabela Delta (Ouro) | CC BY 4.0 | 10 |
| `doc:chuva_e_seguranca` | `backend/base_conhecimento/chuva_e_seguranca.md` | Markdown | Texto da equipe, baseado em orientações gerais de Defesa Civil | 4 |
| `doc:limites_dos_dados` | `backend/base_conhecimento/limites_dos_dados.md` | Markdown | Texto da equipe (relatório técnico Databricks) | 6 |
| `doc:sobre_o_app` | `backend/base_conhecimento/sobre_o_app.md` | Markdown | Texto da equipe (proposta do projeto) | 6 |
| **Total** | | | | **97** |

## Privacidade (LGPD)

A base não tem dados pessoais. Os trechos de dados são agregados (contagens por subprefeitura, por mês
e por dia). Os pontos individuais de alagamento não entram na base, e os relatos dos cidadãos também
não: eles ficam na moderação e nunca são enviados ao modelo.

## Como regenerar

Com o site rodando (`docker compose up -d`):

```bash
curl -s http://localhost:8000/api/v1/assistente/base -o base/trechos.json
```

Sem credenciais do Databricks, a API usa o snapshot validado em `backend/data/snapshot/`. Os números
são os mesmos, mas a `fonte` de cada trecho indica "snapshot".
