# Databricks notebook source
# MAGIC %md
# MAGIC # AlertaBairro | Auditoria da Bronze (requisito 05)
# MAGIC
# MAGIC Mostra, a partir do histórico Delta, quantos documentos e registros a Bronze tinha
# MAGIC **depois do 1º lote**, **depois do 2º lote** e **depois de uma nova execução do COPY INTO**.
# MAGIC
# MAGIC Como importar: *Workspace → Import → arquivo .py*. Rode as duas células e tire um print de cada saída.

# COMMAND ----------

# Etapa 1: contagem da Bronze em cada versão da tabela (time travel do Delta)

from pyspark.sql import functions as F

TABELAS = {
    "workspace.alertabairro.bronze_clima": "size(daily.time)",
    "workspace.alertabairro.bronze_alagamentos": "size(features)",
}

linhas = []
for tabela, expressao_registros in TABELAS.items():
    historico = (
        spark.sql(f"DESCRIBE HISTORY {tabela}")
        .select("version", "timestamp", "operation", "operationMetrics")
        .orderBy("version")
        .collect()
    )
    for versao in historico:
        try:
            contagem = spark.sql(
                f"""
                SELECT COUNT(*) AS documentos,
                       COALESCE(SUM({expressao_registros}), 0) AS registros
                FROM {tabela} VERSION AS OF {versao['version']}
                """
            ).first()
            documentos, registros = contagem["documentos"], contagem["registros"]
        except Exception:
            # Versão 0 da tabela ainda sem colunas (criada vazia antes do 1º COPY INTO)
            documentos, registros = 0, 0
        metricas = versao["operationMetrics"] or {}
        linhas.append(
            (
                tabela.split(".")[-1],
                int(versao["version"]),
                str(versao["timestamp"])[:19],
                versao["operation"],
                metricas.get("numOutputRows", "-"),
                int(documentos),
                int(registros),
            )
        )

auditoria = spark.createDataFrame(
    linhas,
    "tabela string, versao int, quando string, operacao string, "
    "linhas_inseridas string, documentos_na_tabela long, registros_na_tabela long",
)

print("=== BRONZE: CONTAGEM EM CADA VERSAO ===")
auditoria.orderBy("tabela", "versao").show(truncate=False)

# COMMAND ----------

# Etapa 2: nova execução do COPY INTO (2ª execução) - não pode inserir nada

antes = {
    t: spark.table(t).count() for t in TABELAS
}

resultado_clima = spark.sql("""
    COPY INTO workspace.alertabairro.bronze_clima
    FROM '/Volumes/workspace/alertabairro/chegada/'
    FILEFORMAT = JSON
    PATTERN = 'clima_*.json'
    FORMAT_OPTIONS ('multiLine' = 'true', 'mergeSchema' = 'true')
    COPY_OPTIONS ('mergeSchema' = 'true')
""").first()

resultado_alagamentos = spark.sql("""
    COPY INTO workspace.alertabairro.bronze_alagamentos
    FROM '/Volumes/workspace/alertabairro/chegada/'
    FILEFORMAT = JSON
    PATTERN = 'alagamentos_*.geojson'
    FORMAT_OPTIONS ('multiLine' = 'true', 'mergeSchema' = 'true')
    COPY_OPTIONS ('mergeSchema' = 'true')
""").first()

depois = {
    t: spark.table(t).count() for t in TABELAS
}

print("=== 2a EXECUCAO DO COPY INTO ===")
for tabela, resultado in [
    ("workspace.alertabairro.bronze_clima", resultado_clima),
    ("workspace.alertabairro.bronze_alagamentos", resultado_alagamentos),
]:
    inseridas = resultado["num_inserted_rows"] if resultado is not None else 0
    print(
        f"{tabela.split('.')[-1]}: documentos antes = {antes[tabela]}, "
        f"inseridos agora = {inseridas}, documentos depois = {depois[tabela]}"
    )
    assert antes[tabela] == depois[tabela], "A reexecução duplicou dados!"

print("Reexecução sem duplicação: OK")
