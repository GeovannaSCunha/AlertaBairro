# Amostras das fontes

Um pouco de cada fonte, no formato exato em que o Airflow grava na pasta `chegada/`.

| Fonte | Arquivo | Formato | Coleta |
| --- | --- | --- | --- |
| Open-Meteo (API de arquivo histórico) | `clima_AAAAMMDD.json` | JSON (`daily.time`, `daily.precipitation_sum`) | Diária (`@daily`), janela de 8 dias terminando 7 dias antes da coleta |
| GeoSampa / Prefeitura de SP (WFS `geoportal:risco_ocorrencia_alagamento`) | `alagamentos_AAAAMMDD_amostra.geojson` | GeoJSON (`features[].properties`, `geometry.coordinates`) | Diária (`@daily`), até 1.000 ocorrências |

Para gerar a partir da sua pasta de coleta:

```bash
python3 amostras/gerar_amostras.py ~/alertabairro/chegada
```

São dados públicos, sem informação pessoal.
