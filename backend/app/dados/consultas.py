"""SQL fixo (somente leitura) usado pela API.

Nenhum texto vindo do usuário, do app ou da IA é concatenado aqui: catálogo e schema
são validados como identificadores em `config.py`, e limites numéricos passam por `int()`.
Os filtros do mapa (subprefeitura, mês) são aplicados em Python sobre o resultado em cache.
O MVP consome somente a camada Ouro: fato pública + dimensões de subprefeitura e tempo + clima diário.
"""

from __future__ import annotations

from dataclasses import dataclass

LIMITE_MAXIMO_PONTOS = 2000


# Modelo estrela da camada Ouro (notebooks alertabairro_ouro e alertabairro_ouro_contrato_mvp).
# O MVP lê apenas a fato PÚBLICA (id em SHA-256 e coordenadas arredondadas) e as dimensões.
FATO = "ouro_fato_alagamentos_publica"
DIM_SUBPREFEITURA = "ouro_dim_subprefeitura"
DIM_TEMPO = "ouro_dim_tempo"
CLIMA = "ouro_clima_diario"


@dataclass(frozen=True)
class Consultas:
    catalog: str
    schema: str

    def tabela(self, nome: str) -> str:
        return f"{self.catalog}.{self.schema}.{nome}"

    @property
    def kpis(self) -> str:
        fato, tempo, clima = self.tabela(FATO), self.tabela(DIM_TEMPO), self.tabela(CLIMA)
        return f"""
SELECT a.total_alagamentos,
       a.subprefeituras_com_registros,
       CAST(a.mes_inicio AS STRING) AS mes_inicio,
       CAST(a.mes_fim AS STRING) AS mes_fim,
       c.chuva_acumulada_mm,
       c.maior_chuva_diaria_mm,
       CAST(c.data_maior_chuva AS STRING) AS data_maior_chuva,
       CAST(c.periodo_inicio AS STRING) AS periodo_inicio,
       CAST(c.periodo_fim AS STRING) AS periodo_fim
FROM (
  SELECT SUM(f.quantidade_ocorrencias) AS total_alagamentos,
         COUNT(DISTINCT f.id_subprefeitura) AS subprefeituras_com_registros,
         CAST(DATE_TRUNC('MONTH', MIN(t.id_data)) AS DATE) AS mes_inicio,
         CAST(DATE_TRUNC('MONTH', MAX(t.id_data)) AS DATE) AS mes_fim
  FROM {fato} f
  JOIN {tempo} t ON f.id_data = t.id_data
) a
CROSS JOIN (
  SELECT ROUND(SUM(precipitacao_mm), 1) AS chuva_acumulada_mm,
         MAX(precipitacao_mm) AS maior_chuva_diaria_mm,
         MAX_BY(data, precipitacao_mm) AS data_maior_chuva,
         MIN(data) AS periodo_inicio,
         MAX(data) AS periodo_fim
  FROM {clima}
) c
""".strip()

    @property
    def subprefeituras(self) -> str:
        fato, dim = self.tabela(FATO), self.tabela(DIM_SUBPREFEITURA)
        return f"""
SELECT NULLIF(REGEXP_EXTRACT(s.id_subprefeitura, '^([A-Z]{{1,3}}) *-', 1), '') AS codigo_subprefeitura,
       s.nome_subprefeitura AS subprefeitura,
       SUM(f.quantidade_ocorrencias) AS total_ocorrencias,
       CAST(MIN(f.id_data) AS STRING) AS primeira_ocorrencia,
       CAST(MAX(f.id_data) AS STRING) AS ultima_ocorrencia
FROM {fato} f
JOIN {dim} s ON f.id_subprefeitura = s.id_subprefeitura
GROUP BY s.id_subprefeitura, s.nome_subprefeitura
ORDER BY total_ocorrencias DESC, subprefeitura
""".strip()

    @property
    def mensal(self) -> str:
        fato, tempo = self.tabela(FATO), self.tabela(DIM_TEMPO)
        return f"""
SELECT CONCAT(t.ano_mes, '-01') AS mes,
       SUM(f.quantidade_ocorrencias) AS total_ocorrencias
FROM {fato} f
JOIN {tempo} t ON f.id_data = t.id_data
GROUP BY t.ano_mes
ORDER BY t.ano_mes
""".strip()

    @property
    def clima_diario(self) -> str:
        return f"""
SELECT CAST(data AS STRING) AS data, precipitacao_mm, precipitacao_acumulada_mm
FROM {self.tabela(CLIMA)}
ORDER BY data
""".strip()

    def mapa(self, limite: int = 1000) -> str:
        limite = max(1, min(int(limite), LIMITE_MAXIMO_PONTOS))
        fato, dim = self.tabela(FATO), self.tabela(DIM_SUBPREFEITURA)
        return f"""
SELECT f.id_ocorrencia_hash AS id,
       CAST(f.id_data AS STRING) AS data,
       f.tipo_ocorrencia AS tipo,
       s.nome_subprefeitura AS subprefeitura,
       CAST(f.latitude_aprox AS DOUBLE) AS latitude,
       CAST(f.longitude_aprox AS DOUBLE) AS longitude
FROM {fato} f
JOIN {dim} s ON f.id_subprefeitura = s.id_subprefeitura
WHERE f.latitude_aprox IS NOT NULL AND f.longitude_aprox IS NOT NULL
ORDER BY f.id_data DESC
LIMIT {limite}
""".strip()
