# Snapshot dos dados

Quando a API não está conectada ao Databricks, ela usa os valores validados no relatório técnico
(13/11/2026), definidos em `app/dados/snapshot.py`. Esses valores cobrem os KPIs, o ranking (top 10),
a série mensal e a chuva diária.

Os **pontos do mapa** não constam do relatório. Para mostrá-los sem conexão ao Databricks, exporte a
camada Prata como CSV e salve aqui com o nome `prata_alagamentos.csv`:

1. No Databricks, abra o SQL Editor e execute:

   ```sql
   SELECT CAST(id_ocorrencia AS STRING) AS id,
          CAST(data_ocorrencia AS STRING) AS data,
          tipo_ocorrencia AS tipo,
          subprefeitura,
          CAST(latitude AS DOUBLE) AS latitude,
          CAST(longitude AS DOUBLE) AS longitude
   FROM workspace.alertabairro.prata_alagamentos
   WHERE latitude IS NOT NULL AND longitude IS NOT NULL
   ORDER BY data_ocorrencia DESC
   ```

2. Baixe o resultado em CSV (botão de download da grade de resultados).
3. Salve como `backend/data/snapshot/prata_alagamentos.csv`, com cabeçalho
   `id,data,tipo,subprefeitura,latitude,longitude`.
4. Faça commit do arquivo. São dados públicos do GeoSampa, sem informação pessoal.

A tela do mapa continua indicando "Snapshot" e a data de validação.
