"""SQL fixo (somente leitura) usado pela API.

Nenhum texto vindo do usuário, do app ou da IA é concatenado aqui: catálogo e schema
são validados como identificadores em `config.py`, e limites numéricos passam por `int()`.
Os filtros do mapa (subprefeitura, mês) são aplicados em Python sobre o resultado em cache.
"""

from __future__ import annotations

from dataclasses import dataclass

LIMITE_MAXIMO_PONTOS = 2000


@dataclass(frozen=True)
class Consultas:
    catalog: str
    schema: str

    def tabela(self, nome: str) -> str:
        return f"{self.catalog}.{self.schema}.{nome}"

    @property
    def kpis(self) -> str:
        sub = self.tabela("ouro_alagamentos_subprefeitura")
        mensal = self.tabela("ouro_alagamentos_mensal")
        clima = self.tabela("ouro_clima_diario")
        return f"""
SELECT a.total_alagamentos,
       a.subprefeituras_com_registros,
       CAST(m.mes_inicio AS STRING) AS mes_inicio,
       CAST(m.mes_fim AS STRING) AS mes_fim,
       c.chuva_acumulada_mm,
       c.maior_chuva_diaria_mm,
       CAST(c.data_maior_chuva AS STRING) AS data_maior_chuva,
       CAST(c.periodo_inicio AS STRING) AS periodo_inicio,
       CAST(c.periodo_fim AS STRING) AS periodo_fim
FROM (
  SELECT SUM(total_ocorrencias) AS total_alagamentos,
         COUNT(*) AS subprefeituras_com_registros
  FROM {sub}
) a
CROSS JOIN (
  SELECT MIN(mes) AS mes_inicio, MAX(mes) AS mes_fim FROM {mensal}
) m
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
        return f"""
SELECT codigo_subprefeitura,
       subprefeitura,
       total_ocorrencias,
       CAST(primeira_ocorrencia AS STRING) AS primeira_ocorrencia,
       CAST(ultima_ocorrencia AS STRING) AS ultima_ocorrencia
FROM {self.tabela("ouro_alagamentos_subprefeitura")}
ORDER BY total_ocorrencias DESC, subprefeitura
""".strip()

    @property
    def mensal(self) -> str:
        return f"""
SELECT CAST(mes AS STRING) AS mes, total_ocorrencias
FROM {self.tabela("ouro_alagamentos_mensal")}
ORDER BY mes
""".strip()

    @property
    def clima_diario(self) -> str:
        return f"""
SELECT CAST(data AS STRING) AS data, precipitacao_mm, precipitacao_acumulada_mm
FROM {self.tabela("ouro_clima_diario")}
ORDER BY data
""".strip()

    def mapa(self, limite: int = 1000) -> str:
        limite = max(1, min(int(limite), LIMITE_MAXIMO_PONTOS))
        return f"""
SELECT CAST(id_ocorrencia AS STRING) AS id,
       CAST(data_ocorrencia AS STRING) AS data,
       tipo_ocorrencia AS tipo,
       subprefeitura,
       CAST(latitude AS DOUBLE) AS latitude,
       CAST(longitude AS DOUBLE) AS longitude
FROM {self.tabela("prata_alagamentos")}
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY data_ocorrencia DESC
LIMIT {limite}
""".strip()
