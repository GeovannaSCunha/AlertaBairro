# Databricks notebook source
# MAGIC %md
# MAGIC # AlertaBairro | Ouro pública e contrato com o MVP (requisitos 07 e 08)
# MAGIC
# MAGIC Rode **depois** do notebook `alertabairro_ouro` (que cria a fato e as dimensões).
# MAGIC
# MAGIC 1. Recria `ouro_fato_alagamentos_publica` com proteção LGPD:
# MAGIC    hash SHA-256 do identificador e coordenadas arredondadas (~110 m).
# MAGIC 2. Valida a tabela pública.
# MAGIC 3. Executa exatamente as consultas que a API do MVP faz (contrato de dados).
# MAGIC
# MAGIC Como importar: *Workspace → Import → arquivo .py*. Tire um print das saídas das etapas 2 e 3.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Etapa 1: Ouro pública consumida pelo MVP (LGPD: pseudonimização + generalização)
# MAGIC CREATE OR REPLACE TABLE workspace.alertabairro.ouro_fato_alagamentos_publica
# MAGIC COMMENT 'Fato de alagamentos para o MVP: id em SHA-256 e coordenadas arredondadas (3 casas, ~110 m).'
# MAGIC AS
# MAGIC SELECT
# MAGIC     SHA2(CAST(id_ocorrencia AS STRING), 256) AS id_ocorrencia_hash,
# MAGIC     id_data,
# MAGIC     id_subprefeitura,
# MAGIC     tipo_ocorrencia,
# MAGIC     ROUND(latitude, 3)  AS latitude_aprox,
# MAGIC     ROUND(longitude, 3) AS longitude_aprox,
# MAGIC     quantidade_ocorrencias
# MAGIC FROM workspace.alertabairro.ouro_fato_alagamentos;
# MAGIC
# MAGIC ALTER TABLE workspace.alertabairro.ouro_fato_alagamentos_publica
# MAGIC     ALTER COLUMN id_ocorrencia_hash COMMENT 'SHA-256 do id da fonte (pseudonimização)';
# MAGIC ALTER TABLE workspace.alertabairro.ouro_fato_alagamentos_publica
# MAGIC     ALTER COLUMN latitude_aprox COMMENT 'Latitude arredondada para 3 casas (~110 m)';
# MAGIC ALTER TABLE workspace.alertabairro.ouro_fato_alagamentos_publica
# MAGIC     ALTER COLUMN longitude_aprox COMMENT 'Longitude arredondada para 3 casas (~110 m)';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Etapa 2: validação da tabela pública
# MAGIC SELECT
# MAGIC     COUNT(*)                                   AS total_registros,
# MAGIC     COUNT(DISTINCT id_ocorrencia_hash)         AS hashes_unicos,
# MAGIC     COUNT_IF(id_ocorrencia_hash IS NULL)       AS hashes_nulos,
# MAGIC     COUNT_IF(LENGTH(id_ocorrencia_hash) <> 64) AS hashes_fora_do_padrao,
# MAGIC     SUM(quantidade_ocorrencias)                AS total_ocorrencias,
# MAGIC     COUNT_IF(latitude_aprox <> ROUND(latitude_aprox, 3)
# MAGIC           OR longitude_aprox <> ROUND(longitude_aprox, 3)) AS coordenadas_com_mais_de_3_casas
# MAGIC FROM workspace.alertabairro.ouro_fato_alagamentos_publica;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Etapa 3a: contrato do MVP | KPIs da página inicial (GET /api/v1/kpis)
# MAGIC SELECT
# MAGIC     SUM(f.quantidade_ocorrencias)                        AS total_alagamentos,
# MAGIC     COUNT(DISTINCT f.id_subprefeitura)                   AS subprefeituras_com_registros,
# MAGIC     CAST(DATE_TRUNC('MONTH', MIN(t.id_data)) AS DATE)    AS mes_inicio,
# MAGIC     CAST(DATE_TRUNC('MONTH', MAX(t.id_data)) AS DATE)    AS mes_fim
# MAGIC FROM workspace.alertabairro.ouro_fato_alagamentos_publica f
# MAGIC JOIN workspace.alertabairro.ouro_dim_tempo t ON f.id_data = t.id_data;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Etapa 3b: contrato do MVP | ranking da tela Regiões (GET /api/v1/alagamentos/subprefeituras)
# MAGIC SELECT
# MAGIC     s.nome_subprefeitura,
# MAGIC     SUM(f.quantidade_ocorrencias) AS total_ocorrencias,
# MAGIC     MIN(f.id_data)                AS primeira_ocorrencia,
# MAGIC     MAX(f.id_data)                AS ultima_ocorrencia
# MAGIC FROM workspace.alertabairro.ouro_fato_alagamentos_publica f
# MAGIC JOIN workspace.alertabairro.ouro_dim_subprefeitura s ON f.id_subprefeitura = s.id_subprefeitura
# MAGIC GROUP BY s.id_subprefeitura, s.nome_subprefeitura
# MAGIC ORDER BY total_ocorrencias DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Etapa 3c: contrato do MVP | pontos da tela Mapa (GET /api/v1/alagamentos/mapa)
# MAGIC SELECT
# MAGIC     LEFT(f.id_ocorrencia_hash, 12) AS id_hash_inicio,
# MAGIC     f.id_data,
# MAGIC     s.nome_subprefeitura,
# MAGIC     f.latitude_aprox,
# MAGIC     f.longitude_aprox
# MAGIC FROM workspace.alertabairro.ouro_fato_alagamentos_publica f
# MAGIC JOIN workspace.alertabairro.ouro_dim_subprefeitura s ON f.id_subprefeitura = s.id_subprefeitura
# MAGIC ORDER BY f.id_data DESC
# MAGIC LIMIT 10;
