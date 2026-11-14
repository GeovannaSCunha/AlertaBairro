"""Utilidades de texto: normalização de nomes e exibição de subprefeituras."""

from __future__ import annotations

import re
import unicodedata

# As 32 subprefeituras de São Paulo, com grafia de exibição.
# A camada Ouro guarda nomes normalizados em maiúsculas; usamos esta lista apenas para exibir acentos.
SUBPREFEITURAS_SP = [
    "Aricanduva/Formosa/Carrão",
    "Butantã",
    "Campo Limpo",
    "Capela do Socorro",
    "Casa Verde/Cachoeirinha",
    "Cidade Ademar",
    "Cidade Tiradentes",
    "Ermelino Matarazzo",
    "Freguesia/Brasilândia",
    "Guaianases",
    "Ipiranga",
    "Itaim Paulista",
    "Itaquera",
    "Jabaquara",
    "Jaçanã/Tremembé",
    "Lapa",
    "M'Boi Mirim",
    "Mooca",
    "Parelheiros",
    "Penha",
    "Perus",
    "Pinheiros",
    "Pirituba/Jaraguá",
    "Santana/Tucuruvi",
    "Santo Amaro",
    "São Mateus",
    "São Miguel Paulista",
    "Sapopemba",
    "Sé",
    "Vila Maria/Vila Guilherme",
    "Vila Mariana",
    "Vila Prudente",
]


def sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


# A Prata do GeoSampa traz a sigla antes do nome ("MP - SAO MIGUEL PAULISTA"); a Ouro não.
_PREFIXO_SIGLA = re.compile(r"^\s*[A-Za-z]{1,3}\s*[-–]\s+")


def sem_sigla(texto: str) -> str:
    return _PREFIXO_SIGLA.sub("", texto)


def chave(texto: str | None) -> str:
    """Chave de comparação: sem sigla inicial, sem acento, maiúscula, apenas letras e números."""
    if not texto:
        return ""
    return re.sub(r"[^A-Z0-9]", "", sem_acentos(sem_sigla(texto)).upper())


_EXIBICAO = {chave(nome): nome for nome in SUBPREFEITURAS_SP}
# Variações observadas nas bases públicas
_EXIBICAO[chave("Aricanduva/Vila Formosa")] = "Aricanduva/Vila Formosa"
_EXIBICAO[chave("Aricanduva")] = "Aricanduva/Formosa/Carrão"
_EXIBICAO[chave("MBoi Mirim")] = "M'Boi Mirim"


def nome_exibicao(nome: str | None) -> str:
    if not nome:
        return "Não informada"
    conhecido = _EXIBICAO.get(chave(nome))
    if conhecido:
        return conhecido
    nome = sem_sigla(nome)
    if nome.isupper():
        return nome.title()
    return nome


def mesmo_lugar(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b) and chave(a) == chave(b)
