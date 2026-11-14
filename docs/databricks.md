# Conectar a API ao Databricks

A API consulta o catálogo `workspace.alertabairro` pela **SQL Statement Execution API 2.0**, seguindo o relatório técnico (seções 07 a 11). Sem conexão, ela usa o snapshot validado.

## 1. Pegar os dados de conexão

1. No Databricks, abra **SQL Warehouses**, escolha o warehouse e vá em **Connection details**.
2. Copie o **Server hostname**. Ele vira `DATABRICKS_HOST=https://<hostname>`.
3. Copie o **Warehouse ID**, que aparece no fim do HTTP path (`/sql/1.0/warehouses/<id>`). Ele vira `DATABRICKS_WAREHOUSE_ID`.
4. Gere um token em **Settings → Developer → Access tokens**. Ele vira `DATABRICKS_TOKEN`. Para produção, prefira OAuth de service principal, quando o plano permitir.

## 2. Conferir permissões

A identidade do token precisa de `CAN USE` no warehouse e de `SELECT` nas tabelas:

```sql
GRANT USE CATALOG ON CATALOG workspace TO `seu-usuario-ou-sp`;
GRANT USE SCHEMA ON SCHEMA workspace.alertabairro TO `seu-usuario-ou-sp`;
GRANT SELECT ON TABLE workspace.alertabairro.prata_alagamentos TO `seu-usuario-ou-sp`;
GRANT SELECT ON TABLE workspace.alertabairro.ouro_alagamentos_subprefeitura TO `seu-usuario-ou-sp`;
GRANT SELECT ON TABLE workspace.alertabairro.ouro_alagamentos_mensal TO `seu-usuario-ou-sp`;
GRANT SELECT ON TABLE workspace.alertabairro.ouro_clima_diario TO `seu-usuario-ou-sp`;
```

## 3. Testar fora do app

```bash
curl -s -X POST "$DATABRICKS_HOST/api/2.0/sql/statements" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" -H "Content-Type: application/json" \
  -d "{\"warehouse_id\":\"$DATABRICKS_WAREHOUSE_ID\",\"statement\":\"SELECT mes, total_ocorrencias FROM workspace.alertabairro.ouro_alagamentos_mensal ORDER BY mes\",\"wait_timeout\":\"30s\"}" \
  | python -m json.tool | head -40
```

Espere `"state": "SUCCEEDED"` e 8 linhas. Na Free Edition, o warehouse pode estar desligado; a primeira consulta pode demorar enquanto ele liga.

## 4. Ligar na API

Preencha o `.env` e reinicie (`docker compose up -d --build api`). Depois confira:

```bash
curl -s http://localhost:8000/api/v1/status | python -m json.tool
```

`"modo": "databricks"` confirma a conexão. Cada tela passa a mostrar o selo **Databricks** e o horário da consulta.

## Consultas usadas pela API

Todas ficam em `backend/app/dados/consultas.py`, são somente leitura e não recebem texto do usuário.

| Rota | Tabela | Observação |
| --- | --- | --- |
| `/kpis` | Ouro (3 tabelas) | Reproduz o dataset `kpis_alertabairro` do dashboard, que não é tabela física |
| `/alagamentos/subprefeituras` | `ouro_alagamentos_subprefeitura` | Nomes normalizados viram nomes com acento para exibição |
| `/alagamentos/mensal` | `ouro_alagamentos_mensal` | A API calcula as lacunas (ex.: julho) |
| `/clima/diario` | `ouro_clima_diario` | |
| `/alagamentos/mapa` | `prata_alagamentos` | Até 2.000 pontos, com filtros aplicados em memória |

## Problemas comuns

| Sintoma | Causa provável |
| --- | --- |
| `HTTP 401/403` nos logs | Token inválido ou sem permissão no warehouse |
| `TABLE_OR_VIEW_NOT_FOUND` | Catálogo/schema diferente: ajuste `DATABRICKS_CATALOG` e `DATABRICKS_SCHEMA` |
| `Consulta SQL não terminou no prazo` | Warehouse ligando; tente de novo em 1–2 minutos |
| Tela mostra "Snapshot" com aviso de falha | A API caiu no plano B; veja `/api/v1/status` e o painel do Grafana |
