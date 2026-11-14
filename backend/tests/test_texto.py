from app.texto import chave, nome_exibicao


def test_nomes_da_prata_com_sigla_viram_nome_de_exibicao():
    assert nome_exibicao("MP - SAO MIGUEL PAULISTA") == "São Miguel Paulista"
    assert nome_exibicao("Pj - Pirituba/Jaragua") == "Pirituba/Jaraguá"
    assert nome_exibicao("CL - CAMPO LIMPO") == "Campo Limpo"
    assert nome_exibicao("SAO MIGUEL PAULISTA") == "São Miguel Paulista"
    assert nome_exibicao("XY - BAIRRO NOVO") == "Bairro Novo"


def test_chave_igual_entre_prata_ouro_e_tela():
    assert chave("MP - SAO MIGUEL PAULISTA") == chave("São Miguel Paulista") == chave("SAO MIGUEL PAULISTA")


def test_chave_nao_corta_nomes_sem_sigla():
    assert chave("Sé") == "SE"
    assert chave("M'Boi Mirim") == "MBOIMIRIM"
    assert chave("Vila Maria/Vila Guilherme") == "VILAMARIAVILAGUILHERME"
