from datetime import date

from app import indice
from app.dados import snapshot


def _subs():
    return [
        {"subprefeitura": "São Miguel Paulista", "chave": "SAOMIGUELPAULISTA", "total_ocorrencias": 113},
        {"subprefeitura": "Campo Limpo", "chave": "CAMPOLIMPO", "total_ocorrencias": 24},
        {"subprefeitura": "Butantã", "chave": "BUTANTA", "total_ocorrencias": 11},
        {"subprefeitura": "Perus", "chave": "PERUS", "total_ocorrencias": 2},
    ]


def test_faixas_historico():
    assert [indice.pontos_historico(n) for n in (0, 4, 5, 14, 15, 49, 50, 113)] == [0, 0, 1, 1, 2, 2, 3, 3]


def test_faixas_chuva():
    assert [indice.pontos_chuva(v) for v in (0, 9.9, 10, 29.9, 30, 80)] == [0, 0, 1, 1, 2, 2]


def test_chuva_vencida_nao_entra_no_calculo():
    r = indice.calcular(_subs(), snapshot.CLIMA_DIARIO, date(2026, 11, 13))
    assert r["chuva"]["considerada"] is False
    assert "06/11/2026" in r["chuva"]["motivo"]
    smp = r["regioes"][0]
    assert smp["subprefeitura"] == "São Miguel Paulista"
    assert (smp["componente_historico"], smp["componente_chuva"], smp["nivel"]) == (3, 0, "moderada")
    assert "C = 0" in smp["explicacao"]


def test_chuva_recente_soma_tres_dias():
    # Referência 01/11: soma 30/10 (5,2) + 31/10 (1,7) + 01/11 (17,8) = 24,7 mm → C = 1
    r = indice.calcular(_subs(), snapshot.CLIMA_DIARIO, date(2026, 11, 1))
    assert r["chuva"]["considerada"] is True
    assert r["chuva"]["mm_72h"] == 24.7
    assert r["chuva"]["pontos"] == 1
    niveis = {x["chave"]: x["nivel"] for x in r["regioes"]}
    assert niveis == {"SAOMIGUELPAULISTA": "elevada", "CAMPOLIMPO": "moderada", "BUTANTA": "moderada", "PERUS": "baixa"}
    assert "24,7 mm" in r["regioes"][0]["explicacao"]


def test_referencia_antes_da_serie():
    r = indice.calcular(_subs(), snapshot.CLIMA_DIARIO, date(2026, 1, 1))
    assert r["chuva"]["considerada"] is False


def test_sem_clima():
    r = indice.calcular(_subs(), [], date(2026, 11, 13))
    assert r["chuva"]["considerada"] is False
    assert r["aviso"].startswith("Índice experimental")
