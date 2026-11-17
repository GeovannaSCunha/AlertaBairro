-- ============================================================================
-- AlertaBairro | Global Solution FIAP 2026.2
-- Big Data Architecture & Data Integration | Camada Ouro (Gold)
-- Arquivo: databricks/consultas_sql/consultas_analiticas.sql
-- Dialeto: Databricks SQL / Spark SQL
-- ============================================================================
-- Modelo dimensional:
--   workspace.alertabairro.ouro_fato_alagamentos
--   workspace.alertabairro.ouro_dim_subprefeitura
--   workspace.alertabairro.ouro_dim_tempo
--
-- As consultas abaixo correspondem às cinco análises do notebook
-- alertabairro_ouro. Executar cada instrução separadamente no Databricks SQL.
-- As contagens refletem os registros disponíveis na fonte, não constituem
-- uma estimativa de risco real ou de todos os alagamentos da cidade.
-- ============================================================================

-- 1. RANKING: quais subprefeituras concentram mais registros de alagamento?
-- Evidência esperada no lote analisado: São Miguel Paulista lidera com 113.
SELECT
    s.nome_subprefeitura,
    SUM(f.quantidade_ocorrencias) AS total_alagamentos
FROM workspace.alertabairro.ouro_fato_alagamentos AS f
INNER JOIN workspace.alertabairro.ouro_dim_subprefeitura AS s
    ON f.id_subprefeitura = s.id_subprefeitura
GROUP BY
    s.nome_subprefeitura
ORDER BY
    total_alagamentos DESC,
    s.nome_subprefeitura
LIMIT 10;


-- 2. EVOLUÇÃO MENSAL: quantos alagamentos foram registrados por mês?
-- Permite identificar meses com maior concentração de ocorrências.
SELECT
    t.ano,
    t.mes,
    t.ano_mes,
    SUM(f.quantidade_ocorrencias) AS total_alagamentos
FROM workspace.alertabairro.ouro_fato_alagamentos AS f
INNER JOIN workspace.alertabairro.ouro_dim_tempo AS t
    ON f.id_data = t.id_data
GROUP BY
    t.ano,
    t.mes,
    t.ano_mes
ORDER BY
    t.ano,
    t.mes;


-- 3. TIPOS DE OCORRÊNCIA: distribuição e participação percentual.
-- No lote analisado, os 292 registros são classificados como ALAGAMENTO.
WITH contagem AS (
    SELECT
        COALESCE(NULLIF(TRIM(tipo_ocorrencia), ''), 'Não informado') AS tipo_ocorrencia,
        COUNT(1) AS total
    FROM workspace.alertabairro.ouro_fato_alagamentos
    GROUP BY
        COALESCE(NULLIF(TRIM(tipo_ocorrencia), ''), 'Não informado')
)
SELECT
    tipo_ocorrencia,
    total AS total_ocorrencias,
    ROUND(100.0 * total / SUM(total) OVER (), 2) AS percentual_total
FROM contagem
ORDER BY
    total_ocorrencias DESC,
    tipo_ocorrencia;


-- 4. DIA DA SEMANA: em quais dias há mais registros?
-- DAYOFWEEK no Spark SQL: 1=domingo, 2=segunda, ..., 7=sábado.
SELECT
    t.dia_semana AS numero_dia_semana,
    CASE t.dia_semana
        WHEN 1 THEN 'Domingo'
        WHEN 2 THEN 'Segunda-feira'
        WHEN 3 THEN 'Terça-feira'
        WHEN 4 THEN 'Quarta-feira'
        WHEN 5 THEN 'Quinta-feira'
        WHEN 6 THEN 'Sexta-feira'
        WHEN 7 THEN 'Sábado'
        ELSE 'Não informado'
    END AS dia_semana,
    COUNT(1) AS total_ocorrencias
FROM workspace.alertabairro.ouro_fato_alagamentos AS f
INNER JOIN workspace.alertabairro.ouro_dim_tempo AS t
    ON f.id_data = t.id_data
GROUP BY
    t.dia_semana
ORDER BY
    total_ocorrencias DESC,
    numero_dia_semana;


-- 5. ANÁLISE DE IMPACTO REGIONAL (PROXY): concentração e recorrência.
-- Número de registros, meses distintos com ocorrência e participação no total.
-- IMPORTANTE: "impacto" aqui significa concentração de registros na fonte;
-- não mede vítimas, perdas econômicas, gravidade ou probabilidade de enchente.
WITH analise_regional AS (
    SELECT
        s.nome_subprefeitura,
        SUM(f.quantidade_ocorrencias) AS total_ocorrencias,
        COUNT(DISTINCT t.ano_mes) AS meses_com_registros
    FROM workspace.alertabairro.ouro_fato_alagamentos AS f
    INNER JOIN workspace.alertabairro.ouro_dim_subprefeitura AS s
        ON f.id_subprefeitura = s.id_subprefeitura
    INNER JOIN workspace.alertabairro.ouro_dim_tempo AS t
        ON f.id_data = t.id_data
    GROUP BY
        s.nome_subprefeitura
)
SELECT
    nome_subprefeitura,
    total_ocorrencias,
    meses_com_registros,
    ROUND(
        100.0 * total_ocorrencias / SUM(total_ocorrencias) OVER (),
        2
    ) AS percentual_total
FROM analise_regional
ORDER BY
    total_ocorrencias DESC,
    meses_com_registros DESC,
    nome_subprefeitura
LIMIT 10;
