"""Testes de ponta a ponta da API (executados no CI, onde o FastAPI está instalado)."""

import io
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import criar_app  # noqa: E402

TOKEN = "token-de-teste-com-mais-de-16"


@pytest.fixture
def cliente(config_snapshot):
    with TestClient(criar_app(config_snapshot)) as c:
        yield c


def _form(**extra):
    agora_brt = datetime.now(timezone(timedelta(hours=-3))) - timedelta(hours=1)
    dados = {
        "tipo": "alagamento",
        "descricao": "Água cobrindo a calçada na esquina da praça, carros desviando.",
        "ocorrido_em": agora_brt.strftime("%Y-%m-%dT%H:%M"),
        "latitude": "-23.4987",
        "longitude": "-46.4012",
        "aceite_termos": "true",
    }
    dados.update(extra)
    return dados


def test_health_e_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_status_indica_snapshot(cliente):
    corpo = cliente.get("/api/v1/status").json()
    assert corpo["dados"]["modo"] == "snapshot"
    assert corpo["dados"]["databricks_configurado"] is False
    assert corpo["moderacao_habilitada"] is True


def test_kpis_contrato(cliente):
    corpo = cliente.get("/api/v1/kpis").json()
    assert corpo["dados"]["alagamentos"]["total"] == 292
    assert corpo["dados"]["clima"]["chuva_acumulada_mm"] == 67.1
    assert corpo["meta"]["origem"] == "snapshot"
    assert corpo["meta"]["tabela"] == "workspace.alertabairro.ouro_alagamentos_subprefeitura"
    assert corpo["meta"]["natureza"] == "historico"


def test_ranking_com_limite_agrega_demais(cliente):
    corpo = cliente.get("/api/v1/alagamentos/subprefeituras?limit=3").json()
    assert [i["total_ocorrencias"] for i in corpo["dados"]["itens"]] == [113, 24, 16]
    assert corpo["dados"]["demais"] == {"grupos": 27, "total_ocorrencias": 292 - 153}
    assert cliente.get("/api/v1/alagamentos/subprefeituras?limit=0").status_code == 422


def test_mensal_indica_lacuna_de_julho(cliente):
    corpo = cliente.get("/api/v1/alagamentos/mensal").json()
    assert corpo["dados"]["lacunas"] == ["2026-07"]
    assert sum(m["total_ocorrencias"] for m in corpo["dados"]["serie"]) == 292


def test_clima(cliente):
    serie = cliente.get("/api/v1/clima/diario").json()["dados"]["serie"]
    assert len(serie) == 10 and serie[-1]["precipitacao_acumulada_mm"] == 67.1


def test_mapa_sem_csv_retorna_vazio_e_filtro_invalido(cliente):
    corpo = cliente.get("/api/v1/alagamentos/mapa").json()
    assert corpo["dados"]["pontos"] == [] and corpo["meta"]["pontos_disponiveis"] is False
    assert cliente.get("/api/v1/alagamentos/mapa?mes=2026-13").status_code == 422


def test_mapa_com_csv_e_filtros(config_snapshot, tmp_path):
    from pathlib import Path

    pasta = Path(config_snapshot.snapshot_dir)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "prata_alagamentos.csv").write_text(
        "id,data,tipo,subprefeitura,latitude,longitude\n"
        "1,2026-09-02,ALAGAMENTO,SAO MIGUEL PAULISTA,-23.49,-46.44\n"
        "2,2026-01-15,ALAGAMENTO,Campo Limpo,-23.64,-46.76\n",
        encoding="utf-8",
    )
    with TestClient(criar_app(config_snapshot)) as c:
        tudo = c.get("/api/v1/alagamentos/mapa").json()["dados"]
        assert tudo["total"] == 2
        assert "São Miguel Paulista" in tudo["filtros"]["subprefeituras"]
        filtrado = c.get("/api/v1/alagamentos/mapa", params={"subprefeitura": "São Miguel Paulista"}).json()["dados"]
        assert [p["id"] for p in filtrado["pontos"]] == ["1"]
        por_mes = c.get("/api/v1/alagamentos/mapa", params={"mes": "2026-01"}).json()["dados"]
        assert [p["id"] for p in por_mes["pontos"]] == ["2"]


def test_indice_e_simulacao(cliente):
    atual = cliente.get("/api/v1/indice").json()
    assert atual["dados"]["chuva"]["considerada"] is False and atual["meta"]["simulacao"] is False
    sim = cliente.get("/api/v1/indice?data_referencia=2026-11-01").json()
    assert sim["dados"]["chuva"]["mm_72h"] == 24.7 and sim["meta"]["simulacao"] is True
    assert cliente.get("/api/v1/indice?data_referencia=2025-01-01").status_code == 422


def test_relato_fluxo_completo_com_moderacao(cliente):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (90, 120, 150)).save(buf, format="PNG")
    r = cliente.post("/api/v1/relatos", data=_form(), files={"foto": ("foto.png", buf.getvalue(), "image/png")})
    assert r.status_code == 201, r.text
    criado = r.json()
    assert criado["status"] == "pendente"

    assert cliente.get("/api/v1/relatos").json()["dados"] == []
    assert cliente.get(f"/api/v1/relatos/{criado['id']}/foto").status_code == 404
    assert cliente.get(f"/api/v1/relatos/protocolo/{criado['protocolo']}").json()["status"] == "pendente"

    assert cliente.get("/api/v1/moderacao/relatos").status_code == 401
    assert cliente.get("/api/v1/moderacao/relatos", headers={"Authorization": "Bearer errado-errado-errado"}).status_code == 401
    cab = {"Authorization": f"Bearer {TOKEN}"}
    fila = cliente.get("/api/v1/moderacao/relatos", headers=cab)
    assert fila.status_code == 200 and fila.headers["cache-control"] == "no-store"
    assert fila.json()["dados"][0]["id"] == criado["id"]

    d = cliente.post(f"/api/v1/moderacao/relatos/{criado['id']}", json={"acao": "aprovar"}, headers=cab)
    assert d.status_code == 200 and d.json()["status"] == "aprovado"

    publicos = cliente.get("/api/v1/relatos").json()["dados"]
    assert len(publicos) == 1 and publicos[0]["latitude"] == -23.499 and "protocolo" not in publicos[0]
    foto = cliente.get(f"/api/v1/relatos/{criado['id']}/foto")
    assert foto.status_code == 200 and foto.headers["content-type"] == "image/jpeg"

    ind = cliente.get("/api/v1/indicadores").json()["dados"]
    assert ind["participacao"]["aprovado"] == 1


def test_relato_invalido_devolve_campos(cliente):
    r = cliente.post("/api/v1/relatos", data=_form(descricao="ligue 11 98765-4321 agora mesmo ok", latitude="-10"))
    assert r.status_code == 422
    assert set(r.json()["campos"]) >= {"descricao", "localizacao"}


def test_relato_foto_invalida(cliente):
    r = cliente.post("/api/v1/relatos", data=_form(), files={"foto": ("x.png", b"nao e imagem", "image/png")})
    assert r.status_code == 422 and "foto" in r.json()["campos"]


def test_limite_de_taxa(config_snapshot):
    from dataclasses import replace

    with TestClient(criar_app(replace(config_snapshot, limite_assistente_por_minuto=2))) as c:
        for _ in range(2):
            assert c.post("/api/v1/assistente", json={"pergunta": "Quantos alagamentos no total?"}).status_code == 200
        r = c.post("/api/v1/assistente", json={"pergunta": "Quantos alagamentos no total?"})
        assert r.status_code == 429 and "retry-after" in r.headers


def test_assistente(cliente):
    r = cliente.post("/api/v1/assistente", json={"pergunta": "Quantos alagamentos tem em Campo Limpo?"}).json()
    assert "24" in r["resposta"] and r["fontes"]
    prev = cliente.post("/api/v1/assistente", json={"pergunta": "Vai alagar amanhã no Butantã?"}).json()
    assert prev["recusou"] is True
    assert cliente.post("/api/v1/assistente", json={"pergunta": ""}).status_code == 422
    assert cliente.get("/api/v1/assistente/base").json()["total"] > 20


def test_metricas_prometheus(cliente):
    cliente.get("/api/v1/kpis")
    cliente.get("/api/v1/relatos/00000000-0000-0000-0000-000000000000/foto")
    texto = cliente.get("/metrics").text
    linhas = [l for l in texto.splitlines() if l.startswith("http_requests_total{")]

    def tem(*rotulos: str) -> bool:
        return any(all(r in l for r in rotulos) for l in linhas)

    assert tem('metodo="GET"', 'rota="/api/v1/kpis"', 'status="200"'), linhas
    assert tem('rota="/api/v1/relatos/{relato_id}/foto"', 'status="404"'), linhas
    assert "alertabairro_consultas_dados_total" in texto
    assert "http_requests_em_andamento" in texto


def test_moderacao_desabilitada_sem_token(config_snapshot):
    from dataclasses import replace

    with TestClient(criar_app(replace(config_snapshot, admin_token=None))) as c:
        assert c.get("/api/v1/moderacao/relatos").status_code == 503
