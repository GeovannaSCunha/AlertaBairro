# Segurança e LGPD - AlertaBairro

## Contexto

Os dados públicos de alagamento do GeoSampa não identificam pessoas: cada registro é uma ocorrência com data, tipo, subprefeitura e coordenada. Mesmo assim, aplicamos proteção na camada Ouro, porque a coordenada exata e o identificador da fonte não são necessários ao produto (princípio da necessidade, art. 6º, III, da LGPD).

## O que a Ouro entrega ao MVP

A tabela `workspace.alertabairro.ouro_fato_alagamentos_publica` (notebook `databricks/alertabairro_ouro_contrato_mvp.py`) é a única fato lida pelo site:

| Coluna | Proteção |
| --- | --- |
| `id_ocorrencia_hash` | SHA-256 do identificador original (pseudonimização) |
| `latitude_aprox`, `longitude_aprox` | Coordenadas arredondadas para 3 casas decimais (~110 m) |
| `id_data`, `id_subprefeitura`, `tipo_ocorrencia`, `quantidade_ocorrencias` | Sem dado pessoal |

A tabela de detalhe `ouro_fato_alagamentos` (com o id original e a coordenada exata) fica restrita ao pipeline. A API lê somente a fato pública e as dimensões `ouro_dim_subprefeitura` e `ouro_dim_tempo`, além de `ouro_clima_diario` (teste automatizado `test_mvp_consome_somente_a_camada_ouro`).

O hash SHA-256 é **pseudonimização**, não anonimização: como o identificador da fonte é público, quem tiver a base original pode refazer o hash. Um próximo passo é usar um *salt* guardado em segredo (Databricks Secrets) no cálculo do hash.

## Dados que o produto coleta

Os relatos de moradores ficam no banco da API, fora do lakehouse: não pedem nome nem contato; a descrição é recusada se contiver e-mail, CPF ou telefone; a coordenada é arredondada; a foto perde os metadados (EXIF/GPS) e é apagada depois de 90 dias.

## Cuidados na publicação

1. Tokens do Databricks somente em variáveis de ambiente do servidor (`.env`, fora do Git).
2. Configuração do DAG em Airflow Variables; nenhuma fonte atual exige chave.
3. Prints revisados: o endereço do workspace e o e-mail da conta foram desfocados.
4. Gitleaks, Semgrep e Trivy rodam a cada push no GitHub Actions.

## Evidências

- `../evidencias/ouro/09_anonimizacao_hash_292.png`
- `../evidencias/ouro/10_esquema_ouro_publica.png`
- `../evidencias/mvp/01_mvp_tela_inicial_kpis.png`
