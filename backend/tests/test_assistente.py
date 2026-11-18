import json
from datetime import date

import pytest

from app.assistente.busca import IndiceBM25, Trecho, tokenizar
from app.assistente.guardrails import verificar
from app.assistente.llm import ClienteLLM, ErroLLM, validar_saida
from app.assistente.servico import ServicoAssistente
from app.dados.fonte import FonteDados


@pytest.fixture
def servico(config_snapshot):
    return ServicoAssistente(FonteDados(config_snapshot), config_snapshot.base_conhecimento_dir,
                             hoje=lambda: date(2026, 11, 13))


# ----------------------------------------------------------------------------- guardrails
@pytest.mark.parametrize(
    "pergunta",
    [
        "Vai alagar em São Miguel amanhã?",
        "Está alagando no Campo Limpo agora?",
        "Qual a previsão de chuva para a semana?",
        "Posso sair de carro pela Vila Prudente?",
    ],
)
def test_guardrail_previsao(pergunta):
    assert verificar(pergunta).categoria == "previsao"


def test_guardrail_emergencia():
    v = verificar("Socorro, estou ilhado com água entrando em casa")
    assert v.categoria == "emergencia" and "193" in (v.mensagem or "")


@pytest.mark.parametrize("pergunta", ["Quantos alagamentos tem em Itaim Paulista?", "Quanto choveu em outubro?"])
def test_guardrail_libera_perguntas_historicas(pergunta):
    assert verificar(pergunta).categoria == "ok"


# ----------------------------------------------------------------------------- busca
def test_tokenizar_remove_acentos_e_aproxima_radicais():
    assert tokenizar("Alagamentos em São Miguel") == ["alag", "sao", "miguel"]
    assert tokenizar("alagar")[0] == tokenizar("ruas alagadas")[1] == "alag"


def test_bm25_ranqueia_trecho_certo():
    trechos = [
        Trecho("a", "Chuva", "Em 29/10 choveu 20,2 mm", "f"),
        Trecho("b", "Ranking", "São Miguel Paulista tem 113 registros de alagamento", "f"),
    ]
    achados = IndiceBM25(trechos).buscar("registros em são miguel")
    assert achados[0].trecho.id == "b"


# ----------------------------------------------------------------------------- modo regras
def test_responde_subprefeitura_com_fonte(servico):
    r = servico.responder("Quantos alagamentos tem em São Miguel Paulista?")
    assert "113" in r["resposta"] and r["recusou"] is False
    assert r["fontes"][0]["id"] == "sub:SAOMIGUELPAULISTA"
    assert "snapshot" in r["fontes"][0]["fonte"]


def test_responde_mes_com_lacuna(servico):
    r = servico.responder("Quantos alagamentos houve em julho?")
    assert "não comprova" in r["resposta"]
    r2 = servico.responder("E quantos registros em setembro?")
    assert "95" in r2["resposta"]


def test_responde_chuva(servico):
    r = servico.responder("Quanto choveu no período?")
    assert "67,1" in r["resposta"] and "20,2" in r["resposta"]


def test_responde_indice(servico):
    r = servico.responder("Qual o nível de atenção de Campo Limpo no índice?")
    assert "atenção moderada" in r["resposta"] and r["fontes"][0]["id"] == "indice:CAMPOLIMPO"


def test_responde_documento(servico):
    r = servico.responder("O que significa um milímetro de chuva?")
    assert "1 litro" in r["resposta"]


def test_recusa_fora_da_base(servico):
    r = servico.responder("Quem ganhou a copa do mundo de 2002?")
    assert r["recusou"] is True and r["motivo_recusa"] == "nao_consta"


def test_recusa_previsao(servico):
    r = servico.responder("Vai alagar no Butantã amanhã?")
    assert r["recusou"] is True and r["modo"] == "guardrail"


def test_base_exportavel(servico):
    base = servico.base()
    assert any(t["id"] == "kpi:resumo" for t in base)
    assert any(t["tipo"] == "documento" for t in base)


# ----------------------------------------------------------------------------- modo LLM
def test_validar_saida_llm():
    ok = validar_saida('{"resposta": "113 registros", "fontes": ["sub:X"], "recusou": false}', {"sub:X"})
    assert ok["fontes"] == ["sub:X"]
    with pytest.raises(ErroLLM):
        validar_saida('{"resposta": "x", "fontes": ["inventada"], "recusou": false}', {"sub:X"})
    with pytest.raises(ErroLLM):
        validar_saida('{"resposta": "x", "fontes": [], "recusou": false}', {"sub:X"})
    with pytest.raises(ErroLLM):
        validar_saida("não é json", {"sub:X"})
    assert validar_saida('```json\n{"resposta": "Não consta.", "fontes": [], "recusou": true}\n```', set())["recusou"]


def test_servico_usa_llm_e_cai_para_regras(config_snapshot):
    def transporte_ok(url, corpo, cab, timeout):
        assert url.endswith("/chat/completions") and corpo["response_format"] == {"type": "json_object"}
        ids = [linha.split("]")[0][1:] for linha in corpo["messages"][1]["content"].splitlines() if linha.startswith("[")]
        return {"choices": [{"message": {"content": json.dumps(
            {"resposta": "Segundo a base histórica, são 113 registros.", "fontes": ids[:1], "recusou": False})}}]}

    def transporte_ruim(url, corpo, cab, timeout):
        return {"choices": [{"message": {"content": "texto livre sem json"}}]}

    fonte = FonteDados(config_snapshot)
    ok = ServicoAssistente(fonte, config_snapshot.base_conhecimento_dir,
                           llm=ClienteLLM("http://localhost:11434/v1", "modelo-teste", transporte=transporte_ok))
    r = ok.responder("Quantos alagamentos em São Miguel Paulista?")
    assert r["modo"] == "llm:modelo-teste" and len(r["fontes"]) == 1

    ruim = ServicoAssistente(fonte, config_snapshot.base_conhecimento_dir,
                             llm=ClienteLLM("http://localhost:11434/v1", "modelo-teste", transporte=transporte_ruim))
    r2 = ruim.responder("Quantos alagamentos em São Miguel Paulista?")
    assert r2["modo"] == "regras" and "113" in r2["resposta"]


def test_subprefeitura_fora_do_top10_e_palavra_inteira(servico):
    r = servico.responder("E na Mooca?")
    assert "Mooca" in r["resposta"] and r["fontes"][0]["id"] == "sub:demais"
    r2 = servico.responder("Estou empenhado em entender os dados de chuva")
    assert "Penha" not in r2["resposta"]


def test_chuva_em_data_especifica(servico):
    assert "17,8" in servico.responder("Quanto choveu no dia 01/11?")["resposta"]
    assert servico.responder("Choveu em 15/12?")["recusou"] is True


def test_limiar_recusa_sem_chamar_llm(config_snapshot):
    chamadas = []

    def transporte(url, corpo, cab, timeout):
        chamadas.append(corpo)
        return {"choices": [{"message": {"content": json.dumps({"resposta": "inventado", "fontes": [], "recusou": False})}}]}

    servico = ServicoAssistente(FonteDados(config_snapshot), config_snapshot.base_conhecimento_dir,
                                llm=ClienteLLM("http://localhost:11434/v1", "modelo-teste", transporte=transporte))
    r = servico.responder("Qual é o nível do rio Tietê?")
    assert r["recusou"] and r["modo"] == "limiar" and r["motivo_recusa"] == "nao_consta"
    assert chamadas == []
