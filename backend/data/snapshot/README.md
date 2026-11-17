# Snapshot dos dados

Quando a API não está conectada ao Databricks, ela usa os valores validados no relatório técnico
(13/11/2026), definidos em `app/dados/snapshot.py`. Esses valores cobrem os KPIs, o ranking (top 10),
a série mensal e a chuva diária.

Os **pontos do mapa** não constam do relatório. Para mostrá-los sem conexão ao Databricks, exporte
os pontos da Ouro pública como CSV e salve aqui com o nome `pontos_mapa.csv`:

1. No Databricks, abra o SQL Editor e execute:

   ```sql
   SELECT f.id_ocorrencia_hash AS id,
          CAST(f.id_data AS STRING) AS data,
          f.tipo_ocorrencia AS tipo,
          s.nome_subprefeitura AS subprefeitura,
          f.latitude_aprox AS latitude,
          f.longitude_aprox AS longitude
   FROM workspace.alertabairro.ouro_fato_alagamentos_publica f
   JOIN workspace.alertabairro.ouro_dim_subprefeitura s ON f.id_subprefeitura = s.id_subprefeitura
   ORDER BY f.id_data DESC
   ```

2. Baixe o resultado em CSV (botão de download da grade de resultados).
3. Salve como `backend/data/snapshot/pontos_mapa.csv`, com cabeçalho
   `id,data,tipo,subprefeitura,latitude,longitude`.
4. Faça commit do arquivo. São dados públicos do GeoSampa, com id em hash e coordenadas arredondadas.

A tela do mapa continua indicando "Snapshot" e a data de validação.
