# Índice de evidências - AlertaBairro

Capturas fornecidas ao longo da construção do projeto, selecionadas e renomeadas para facilitar a correção da **Global Solution CitizenTech 2026.2 - Big Data Architecture & Data Integration**.

**Como consultar:** abra cada imagem em tamanho original no GitHub/VS Code; as miniaturas do Markdown podem reduzir a legibilidade. Os prints são os originais, com uma única edição: o endereço do workspace Databricks (barra do navegador) e o e-mail da conta foram desfocados antes da publicação.

**Atenção:** as evidências são registros de execução, não garantia de que a execução ainda esteja ativa. Os dois períodos são diferentes: ocorrências de jan-set/2026 e clima de 28/out a 06/nov/2026.

## Airflow - orquestração da coleta

- **[01_graph_primeira_execucao.png](airflow/01_graph_primeira_execucao.png)** - Visão Graph - coleta paralela e validação dos arquivos, execução concluída. Requisitos: R02, R03.
- **[02_graph_segunda_execucao.png](airflow/02_graph_segunda_execucao.png)** - Visão Graph - outra execução, três tarefas concluídas. Requisitos: R02, R03, R04.
- **[03_dag_registrada_interface.png](airflow/03_dag_registrada_interface.png)** - DAG alertabairro_coleta localizada no Airflow. Requisitos: R02, R09.
- **[04_chegada_arquivos_dois_lotes.png](airflow/04_chegada_arquivos_dois_lotes.png)** - Pasta chegada/ com arquivos datados das duas fontes de coleta. Requisitos: R02, R04.

## Bronze - ingestão incremental

- **[01_volume_arquivos_carregados.png](bronze/01_volume_arquivos_carregados.png)** - Volume Databricks chegada/ com arquivos enviados. Requisitos: R04.
- **[02_listagem_arquivos_bronze.png](bronze/02_listagem_arquivos_bronze.png)** - Listagem dos arquivos de entrada usados no notebook Bronze. Requisitos: R04, R05.
- **[03_tabelas_bronze_criadas.png](bronze/03_tabelas_bronze_criadas.png)** - Bronze - tabelas brutas disponíveis no catálogo. Requisitos: R05.
- **[04_copy_into_clima_reexecucao.png](bronze/04_copy_into_clima_reexecucao.png)** - COPY INTO clima - métricas de execução/reexecução. Requisitos: R05.
- **[05_copy_into_alagamentos_reexecucao.png](bronze/05_copy_into_alagamentos_reexecucao.png)** - COPY INTO alagamentos - métricas de execução/reexecução. Requisitos: R05.

## Prata - qualidade e MERGE

- **[01_amostras_dados_tratados.png](prata/01_amostras_dados_tratados.png)** - Prata - amostras dos registros e transformação dos campos. Requisitos: R06.
- **[02_regras_qualidade_origem.png](prata/02_regras_qualidade_origem.png)** - Prata - inspeção de nulos, campos e duplicidades na origem. Requisitos: R06.
- **[03_validacao_584_registros.png](prata/03_validacao_584_registros.png)** - Prata - 584 recebidos, 584 válidos, nenhum barrado. Requisitos: R06.
- **[04_deduplicacao_584_para_292.png](prata/04_deduplicacao_584_para_292.png)** - Prata - alagamentos 584 para 292; clima 16 para 10. Requisitos: R06.
- **[05_merge_alagamentos_292_unicos.png](prata/05_merge_alagamentos_292_unicos.png)** - Prata - MERGE concluído e 292 IDs únicos. Requisitos: R06.
- **[06_auditoria_merge_idempotencia.png](prata/06_auditoria_merge_idempotencia.png)** - Prata - duas execuções MERGE sem inserts, updates ou deletes. Requisitos: R06.
- **[07_contagens_regras_individuais.png](prata/07_contagens_regras_individuais.png)** - Consulta de auditoria de dados inválidos na origem. Requisitos: R06.

## Ouro - modelo dimensional, SQL e LGPD

- **[01_validacao_fato_292.png](ouro/01_validacao_fato_292.png)** - Ouro - tabela fato com 292 ocorrências e IDs únicos. Requisitos: R07.
- **[02_validacao_dim_tempo_71.png](ouro/02_validacao_dim_tempo_71.png)** - Ouro - dimensão tempo com 71 datas únicas. Requisitos: R07.
- **[03_integridade_fato_dimensoes.png](ouro/03_integridade_fato_dimensoes.png)** - Ouro - junções válidas para tempo e subprefeitura. Requisitos: R07.
- **[04_consulta_1_ranking_regioes.png](ouro/04_consulta_1_ranking_regioes.png)** - SQL 1 - ranking de alagamentos por subprefeitura. Requisitos: R07.
- **[05_consulta_2_serie_mensal.png](ouro/05_consulta_2_serie_mensal.png)** - SQL 2 - evolução mensal das ocorrências. Requisitos: R07.
- **[06_consulta_3_tipo_ocorrencia.png](ouro/06_consulta_3_tipo_ocorrencia.png)** - SQL 3 - proporção por tipo de ocorrência. Requisitos: R07.
- **[07_consulta_4_dia_da_semana.png](ouro/07_consulta_4_dia_da_semana.png)** - SQL 4 - distribuição por dia da semana. Requisitos: R07.
- **[08_consulta_5_impacto_regional.png](ouro/08_consulta_5_impacto_regional.png)** - SQL 5 - concentração/recorrência regional (proxy de impacto). Requisitos: R07.
- **[09_anonimizacao_hash_292.png](ouro/09_anonimizacao_hash_292.png)** - Ouro - tabela pública com 292 hashes únicos, nenhum nulo. Requisitos: R08.
- **[10_esquema_ouro_publica.png](ouro/10_esquema_ouro_publica.png)** - Ouro - esquema da tabela pública sem coordenadas exatas. Requisitos: R08.

## MVP - evidência de consumo dos dados

- **[01_mvp_tela_inicial_kpis.png](mvp/01_mvp_tela_inicial_kpis.png)** - Aplicação AlertaBairro exibindo 292 registros, 30 subprefeituras e indicadores climáticos. Requisitos: R08.

