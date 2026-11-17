# Ouro - modelo dimensional, SQL e LGPD

Esta pasta reúne capturas reais fornecidas durante o desenvolvimento do AlertaBairro. Use os prints em tamanho original nas evidências do relatório.

### 01. Ouro - tabela fato com 292 ocorrências e IDs únicos

![Ouro - tabela fato com 292 ocorrências e IDs únicos](01_validacao_fato_292.png)

*Arquivo:* `01_validacao_fato_292.png` | *Critérios:* R07.

### 02. Ouro - dimensão tempo com 71 datas únicas

![Ouro - dimensão tempo com 71 datas únicas](02_validacao_dim_tempo_71.png)

*Arquivo:* `02_validacao_dim_tempo_71.png` | *Critérios:* R07.

### 03. Ouro - junções válidas para tempo e subprefeitura

![Ouro - junções válidas para tempo e subprefeitura](03_integridade_fato_dimensoes.png)

*Arquivo:* `03_integridade_fato_dimensoes.png` | *Critérios:* R07.

### 04. SQL 1 - ranking de alagamentos por subprefeitura

![SQL 1 - ranking de alagamentos por subprefeitura](04_consulta_1_ranking_regioes.png)

*Arquivo:* `04_consulta_1_ranking_regioes.png` | *Critérios:* R07.

### 05. SQL 2 - evolução mensal das ocorrências

![SQL 2 - evolução mensal das ocorrências](05_consulta_2_serie_mensal.png)

*Arquivo:* `05_consulta_2_serie_mensal.png` | *Critérios:* R07.

### 06. SQL 3 - proporção por tipo de ocorrência

![SQL 3 - proporção por tipo de ocorrência](06_consulta_3_tipo_ocorrencia.png)

*Arquivo:* `06_consulta_3_tipo_ocorrencia.png` | *Critérios:* R07.

### 07. SQL 4 - distribuição por dia da semana

![SQL 4 - distribuição por dia da semana](07_consulta_4_dia_da_semana.png)

*Arquivo:* `07_consulta_4_dia_da_semana.png` | *Critérios:* R07.

### 08. SQL 5 - concentração/recorrência regional (proxy de impacto)

![SQL 5 - concentração/recorrência regional (proxy de impacto)](08_consulta_5_impacto_regional.png)

*Arquivo:* `08_consulta_5_impacto_regional.png` | *Critérios:* R07.

### 09. Ouro - tabela pública com 292 hashes únicos, nenhum nulo

![Ouro - tabela pública com 292 hashes únicos, nenhum nulo](09_anonimizacao_hash_292.png)

*Arquivo:* `09_anonimizacao_hash_292.png` | *Critérios:* R08.

### 10. Ouro - esquema da tabela pública sem coordenadas exatas

![Ouro - esquema da tabela pública sem coordenadas exatas](10_esquema_ouro_publica.png)

*Arquivo:* `10_esquema_ouro_publica.png` | *Critérios:* R08.

### 11. Fato pública: 292 hashes únicos de 64 caracteres, nenhum nulo, coordenadas com até 3 casas

![Fato pública: 292 hashes únicos de 64 caracteres, nenhum nulo, coordenadas com até 3 casas](11_validacao_ouro_publica.png)

*Arquivo:* `11_validacao_ouro_publica.png` | *Critérios:* R08.

### 12. Contrato do MVP: KPIs da página inicial lidos da fato pública e da dim_tempo

![Contrato do MVP: KPIs da página inicial lidos da fato pública e da dim_tempo](12_contrato_mvp_kpis.png)

*Arquivo:* `12_contrato_mvp_kpis.png` | *Critérios:* R08.

### 13. Contrato do MVP: ranking da tela Regiões (fato pública + dim_subprefeitura)

![Contrato do MVP: ranking da tela Regiões (fato pública + dim_subprefeitura)](13_contrato_mvp_ranking.png)

*Arquivo:* `13_contrato_mvp_ranking.png` | *Critérios:* R08.

### 14. Contrato do MVP: pontos do mapa com hash e coordenadas aproximadas

![Contrato do MVP: pontos do mapa com hash e coordenadas aproximadas](14_contrato_mvp_mapa.png)

*Arquivo:* `14_contrato_mvp_mapa.png` | *Critérios:* R08.
