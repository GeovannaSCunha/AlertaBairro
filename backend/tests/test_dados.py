from dataclasses import replace

import pytest

from app.dados import snapshot
from app.dados.consultas import Consultas
from app.dados.databricks import ClienteDatabricks, DatabricksErro, converter_valor, linhas_do_resultado
from app.dados.fonte import FonteDados


# ----------------------------------------------------------------------------- snapshot
def test_snapshot_bate_com_relatorio():
    assert snapshot.KPIS["total_alagamentos"] == 292
    assert sum(m["total_ocorrencias"] for m in snapshot.MENSAL) == 292
    assert len(snapshot.MENSAL) == 8  # 8 meses com registros; julho ausente
    assert all(not m["mes"].startswith("2026-07") for m in snapshot.MENSAL)
    top = sum(s["total_ocorrencias"] for s in snapshot.SUBPREFEITURAS)
    assert top + snapshot.DEMAIS_SUBPREFEITURAS["total_ocorrencias"] == 292
    assert len(snapshot.SUBPREFEITURAS) + snapshot.DEMAIS_SUBPREFEITURAS["grupos"] == 30
    assert snapshot.CLIMA_DIARIO[-1]["precipitacao_acumulada_mm"] == pytest.approx(67.1)
    assert max(c["precipitacao_mm"] for c in snapshot.CLIMA_DIARIO) == pytest.approx(20.2)


def test_carregar_pontos_csv(tmp_path):
    (tmp_path / "prata_alagamentos.csv").write_text(
        "id,data,tipo,subprefeitura,latitude,longitude\n"
        "1,2026-04-01,ALAGAMENTO,MOOCA,-23.6062,-46.5368\n"
        "2,2026-09-02,ALAGAMENTO,SE,invalido,-46.6\n"
        "3,2026-09-10,ALAGAMENTO,SE,-23.55,-46.63\n",
        encoding="utf-8",
    )
    pontos = snapshot.carregar_pontos(tmp_path)
    assert [p["id"] for p in pontos] == ["3", "1"]  # inválido ignorado, ordenado por data desc


def test_carregar_pontos_sem_arquivo(tmp_path):
    assert snapshot.carregar_pontos(tmp_path) == []


# ----------------------------------------------------------------------------- consultas
def test_consultas_usam_tabelas_qualificadas_e_limite_inteiro():
    c = Consultas("workspace", "alertabairro")
    assert "workspace.alertabairro.ouro_dim_tempo" in c.mensal
    assert "LIMIT 2000" in c.mapa(999999)
    assert "LIMIT 1" in c.mapa(-5)
    for sql in (c.kpis, c.subprefeituras, c.mensal, c.clima_diario, c.mapa()):
        assert sql.lstrip().upper().startswith("SELECT")


# ----------------------------------------------------------------------------- cliente
def _resposta_ok(colunas, linhas):
    return {
        "statement_id": "abc",
        "status": {"state": "SUCCEEDED"},
        "manifest": {"schema": {"columns": [{"name": n, "type_name": t} for n, t in colunas]}},
        "result": {"data_array": linhas},
    }


def test_converter_valor():
    assert converter_valor("94", "LONG") == 94
    assert converter_valor("20.2", "DOUBLE") == 20.2
    assert converter_valor("12.50", "DECIMAL(10,2)") == 12.5
    assert converter_valor(None, "LONG") is None
    assert converter_valor("2026-01-01", "DATE") == "2026-01-01"


def test_linhas_do_resultado_rejeita_paginacao():
    obj = _resposta_ok([("mes", "DATE")], [["2026-01-01"]])
    obj["result"]["next_chunk_internal_link"] = "/x"
    with pytest.raises(DatabricksErro):
        linhas_do_resultado(obj)


def test_cliente_faz_polling_ate_sucesso():
    chamadas = []

    def transporte(metodo, caminho, corpo):
        chamadas.append((metodo, caminho, corpo))
        if metodo == "POST":
            assert corpo["format"] == "JSON_ARRAY" and corpo["disposition"] == "INLINE"
            return {"statement_id": "s1", "status": {"state": "PENDING"}}
        return _resposta_ok([("mes", "STRING"), ("total_ocorrencias", "LONG")], [["2026-01-01", "94"]])

    cliente = ClienteDatabricks("https://exemplo.cloud.databricks.com", "dapi-secreto", "wh", transporte=transporte,
                                dormir=lambda s: None)
    assert cliente.executar("SELECT 1") == [{"mes": "2026-01-01", "total_ocorrencias": 94}]
    assert chamadas[1] == ("GET", "/api/2.0/sql/statements/s1", None)
    assert "dapi-secreto" not in repr(cliente)


def test_cliente_erro_de_consulta():
    def transporte(metodo, caminho, corpo):
        return {"statement_id": "s1", "status": {"state": "FAILED", "error": {"error_code": "TABLE_NOT_FOUND"}}}

    cliente = ClienteDatabricks("https://x.cloud.databricks.com", "t", "wh", transporte=transporte, dormir=lambda s: None)
    with pytest.raises(DatabricksErro, match="TABLE_NOT_FOUND"):
        cliente.executar("SELECT 1")


def test_cliente_exige_https():
    with pytest.raises(ValueError):
        ClienteDatabricks("http://inseguro", "t", "wh")


# ----------------------------------------------------------------------------- fonte de dados
def test_fonte_sem_configuracao_usa_snapshot(config_snapshot):
    fonte = FonteDados(config_snapshot)
    r = fonte.kpis()
    assert fonte.modo == "snapshot"
    assert r.meta["origem"] == "snapshot"
    assert r.meta["snapshot_validado_em"] == "2026-11-13"
    assert r.dados["alagamentos"]["total"] == 292
    assert r.dados["alagamentos"]["periodo_inicio"] == "2026-01"
    assert r.dados["clima"]["data_maior_chuva"] == "2026-10-29"
    subs = fonte.subprefeituras().dados
    assert subs["itens"][0]["subprefeitura"] == "São Miguel Paulista"
    assert subs["itens"][0]["chave"] == "SAOMIGUELPAULISTA"
    assert subs["demais"] == {"grupos": 20, "total_ocorrencias": 63}


class _ClienteFalso:
    def __init__(self, respostas=None, erro=False):
        self.respostas = respostas or {}
        self.erro = erro
        self.chamadas = 0

    def executar(self, sql, row_limit=1000):
        self.chamadas += 1
        if self.erro:
            raise DatabricksErro("HTTP 503")
        for trecho, linhas in self.respostas.items():
            if trecho in sql:
                return linhas
        return []


def test_fonte_databricks_com_cache(config_snapshot):
    cliente = _ClienteFalso({"ouro_dim_tempo": [{"mes": "2026-01-01", "total_ocorrencias": 94}]})
    relogio = [0.0]
    fonte = FonteDados(replace(config_snapshot, cache_ttl_s=60), cliente=cliente, relogio=lambda: relogio[0])
    r1 = fonte.mensal()
    r2 = fonte.mensal()
    assert r1.meta["origem"] == "databricks" and r1.dados == [{"mes": "2026-01-01", "total_ocorrencias": 94}]
    assert r2 is r1 and cliente.chamadas == 1
    relogio[0] = 61
    fonte.mensal()
    assert cliente.chamadas == 2


def test_fonte_databricks_falha_cai_para_snapshot(config_snapshot):
    eventos = []
    fonte = FonteDados(config_snapshot, cliente=_ClienteFalso(erro=True), observador=lambda o, s: eventos.append((o, s)))
    r = fonte.clima_diario()
    assert r.meta["origem"] == "snapshot"
    assert "não respondeu" in r.meta["aviso"]
    assert len(r.dados) == 10
    assert ("databricks", "erro") in eventos
    assert fonte.estado.falhas_consecutivas == 1


def test_fonte_databricks_normaliza_nomes(config_snapshot):
    cliente = _ClienteFalso(
        {
            "ouro_dim_subprefeitura": [
                {"codigo_subprefeitura": "MP", "subprefeitura": "MP - SAO MIGUEL PAULISTA", "total_ocorrencias": 113,
                 "primeira_ocorrencia": "2026-01-03", "ultima_ocorrencia": "2026-09-28"},
            ]
        }
    )
    fonte = FonteDados(config_snapshot, cliente=cliente)
    item = fonte.subprefeituras().dados["itens"][0]
    assert item["subprefeitura"] == "São Miguel Paulista"
    assert item["codigo"] == "MP"


def test_mvp_consome_somente_a_camada_ouro():
    """Requisito 08 da disciplina de Big Data: o MVP lê a Ouro (fato pública + dimensões), nunca a Prata."""
    c = Consultas("workspace", "alertabairro")
    for sql in (c.kpis, c.subprefeituras, c.mensal, c.clima_diario, c.mapa()):
        assert "prata_" not in sql and "bronze_" not in sql
        assert "ouro_" in sql
    for sql in (c.kpis, c.subprefeituras, c.mensal, c.mapa()):
        assert "ouro_fato_alagamentos_publica" in sql
    assert "id_ocorrencia_hash" in c.mapa() and "latitude_aprox" in c.mapa()
    assert "id_ocorrencia " not in c.mapa().replace("id_ocorrencia_hash", "")


def test_meta_lista_as_tabelas_da_consulta(config_snapshot):
    meta = FonteDados(config_snapshot).subprefeituras().meta
    assert meta["tabela"] == (
        "workspace.alertabairro.ouro_fato_alagamentos_publica, workspace.alertabairro.ouro_dim_subprefeitura"
    )
