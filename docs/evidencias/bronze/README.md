# Bronze - ingestão incremental

Esta pasta reúne capturas reais fornecidas durante o desenvolvimento do AlertaBairro. Use os prints em tamanho original nas evidências do relatório.

### 01. Volume Databricks chegada/ com arquivos enviados

![Volume Databricks chegada/ com arquivos enviados](01_volume_arquivos_carregados.png)

*Arquivo:* `01_volume_arquivos_carregados.png` | *Critérios:* R04.

### 02. Listagem dos arquivos de entrada usados no notebook Bronze

![Listagem dos arquivos de entrada usados no notebook Bronze](02_listagem_arquivos_bronze.png)

*Arquivo:* `02_listagem_arquivos_bronze.png` | *Critérios:* R04, R05.

### 03. Bronze - tabelas brutas disponíveis no catálogo

![Bronze - tabelas brutas disponíveis no catálogo](03_tabelas_bronze_criadas.png)

*Arquivo:* `03_tabelas_bronze_criadas.png` | *Critérios:* R05.

### 04. COPY INTO clima - métricas de execução/reexecução

![COPY INTO clima - métricas de execução/reexecução](04_copy_into_clima_reexecucao.png)

*Arquivo:* `04_copy_into_clima_reexecucao.png` | *Critérios:* R05.

### 05. COPY INTO alagamentos - métricas de execução/reexecução

![COPY INTO alagamentos - métricas de execução/reexecução](05_copy_into_alagamentos_reexecucao.png)

*Arquivo:* `05_copy_into_alagamentos_reexecucao.png` | *Critérios:* R05.

### 06. Contagem da Bronze por versão Delta: 1º lote (1 documento, 292 / 8) e 2º lote (2 documentos, 584 / 16)

![Contagem da Bronze por versão Delta: 1º lote (1 documento, 292 / 8) e 2º lote (2 documentos, 584 / 16)](06_auditoria_contagens_por_versao.png)

*Arquivo:* `06_auditoria_contagens_por_versao.png` | *Critérios:* R05.

### 07. 2ª execução do COPY INTO: 0 linhas inseridas, documentos antes = depois

![2ª execução do COPY INTO: 0 linhas inseridas, documentos antes = depois](07_auditoria_reexecucao_sem_duplicar.png)

*Arquivo:* `07_auditoria_reexecucao_sem_duplicar.png` | *Critérios:* R05.
