import io
from datetime import datetime, timedelta, timezone

import pytest

from app import relatos as r

AGORA = datetime(2026, 11, 13, 20, 0, tzinfo=timezone.utc)


def _valido(**extra):
    base = dict(
        tipo="alagamento",
        descricao="Rua totalmente alagada perto da escola, água acima da calçada.",
        ocorrido_em="2026-11-13T15:30",
        latitude="-23.4987654",
        longitude="-46.4012345",
        aceite_termos="true",
        agora=AGORA,
    )
    base.update(extra)
    return base


def test_validacao_ok_arredonda_coordenada():
    novo = r.validar(**_valido())
    assert novo.latitude == -23.499 and novo.longitude == -46.401
    assert novo.ocorrido_em == datetime(2026, 11, 13, 18, 30, tzinfo=timezone.utc)  # 15:30 em Brasília


@pytest.mark.parametrize(
    "campo,valor,chave_erro",
    [
        ("tipo", "incendio", "tipo"),
        ("descricao", "curto", "descricao"),
        ("descricao", "Me liga no (11) 98765-4321 para detalhes da rua", "descricao"),
        ("descricao", "Meu email é fulano@exemplo.com, rua alagada", "descricao"),
        ("descricao", "CPF 123.456.789-09 rua alagada na esquina", "descricao"),
        ("ocorrido_em", "2026-11-20T10:00", "ocorrido_em"),
        ("ocorrido_em", "2026-10-01T10:00", "ocorrido_em"),
        ("ocorrido_em", "ontem", "ocorrido_em"),
        ("latitude", "-22.9", "localizacao"),
        ("longitude", "abc", "localizacao"),
        ("aceite_termos", "false", "aceite_termos"),
    ],
)
def test_validacao_erros(campo, valor, chave_erro):
    with pytest.raises(r.ErroValidacao) as exc:
        r.validar(**_valido(**{campo: valor}))
    assert chave_erro in exc.value.erros


def test_descricao_com_numero_de_rua_nao_e_telefone():
    r.validar(**_valido(descricao="Alagamento na Rua das Flores, 120, perto do CEP 08010-100."))


def _imagem_com_exif() -> bytes:
    from PIL import Image

    img = Image.new("RGB", (40, 30), (120, 140, 160))
    exif = Image.Exif()
    exif[0x010F] = "CameraTeste"  # Make
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_processar_foto_remove_exif():
    from PIL import Image

    original = _imagem_com_exif()
    assert Image.open(io.BytesIO(original)).getexif()
    limpa = r.processar_foto(original)
    assert not Image.open(io.BytesIO(limpa)).getexif()


def test_processar_foto_rejeita_nao_imagem():
    with pytest.raises(r.ErroValidacao):
        r.processar_foto(b"%PDF-1.4 nao sou imagem")
    with pytest.raises(r.ErroValidacao):
        r.processar_foto(b"\xff\xd8\xff" + b"0" * (r.FOTO_MAX_BYTES + 1))


@pytest.fixture
def repo(tmp_path):
    return r.RepositorioRelatos(tmp_path / "db.sqlite", tmp_path / "up", retencao_fotos_dias=90)


def test_fluxo_criar_moderar_listar(repo):
    criado = repo.criar(r.validar(**_valido()), foto_jpeg=b"jpeg", agora=AGORA)
    assert criado["status"] == "pendente" and criado["protocolo"].startswith("AB-")
    assert repo.listar_aprovados() == []
    assert repo.caminho_foto(criado["id"]) is None  # pendente não expõe foto

    pend = repo.listar_para_moderacao()
    assert len(pend) == 1 and pend[0]["protocolo"] == criado["protocolo"]

    repo.moderar(criado["id"], "aprovar", agora=AGORA)
    publicos = repo.listar_aprovados()
    assert len(publicos) == 1 and "protocolo" not in publicos[0]
    assert publicos[0]["tem_foto"] is True
    assert repo.caminho_foto(criado["id"]) is not None
    assert repo.consultar_protocolo(criado["protocolo"].lower())["status"] == "aprovado"
    ind = repo.indicadores()
    assert ind["aprovado"] == 1 and ind["taxa_aprovacao"] == 1.0


def test_rejeitar_apaga_foto(repo, tmp_path):
    criado = repo.criar(r.validar(**_valido()), foto_jpeg=b"jpeg", agora=AGORA)
    repo.moderar(criado["id"], "rejeitar", motivo="Local incoerente", agora=AGORA)
    assert not any((tmp_path / "up").iterdir())
    assert repo.listar_para_moderacao("rejeitado")[0]["motivo_moderacao"] == "Local incoerente"


def test_moderar_inexistente_e_acao_invalida(repo):
    assert repo.moderar("nao-existe", "aprovar") is None
    with pytest.raises(r.ErroValidacao):
        repo.moderar("x", "apagar")


def test_retencao_de_fotos(repo, tmp_path):
    antigo = repo.criar(r.validar(**_valido()), foto_jpeg=b"jpeg", agora=AGORA - timedelta(days=91))
    recente = repo.criar(r.validar(**_valido()), foto_jpeg=b"jpeg", agora=AGORA)
    assert repo.aplicar_retencao(agora=AGORA) == 1
    repo.moderar(antigo["id"], "aprovar")
    repo.moderar(recente["id"], "aprovar")
    assert repo.caminho_foto(antigo["id"]) is None
    assert repo.caminho_foto(recente["id"]) is not None
