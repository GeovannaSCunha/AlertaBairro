"""Monta a base de conhecimento do assistente.

Dois tipos de trecho, todos com fonte:
  - "dados": gerados a partir das tabelas Ouro (via FonteDados), um fato por trecho;
  - "documento": arquivos Markdown em `base_conhecimento/`, um trecho por seção "## ".
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from app.assistente.busca import Trecho

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _mm(valor: float | None) -> str:
    return "sem dado" if valor is None else f"{valor:.1f}".replace(".", ",")


def data_br(iso: str | None) -> str:
    if not iso:
        return "data não informada"
    d = date.fromisoformat(iso[:10])
    return d.strftime("%d/%m/%Y")


def mes_br(iso_ano_mes: str | None) -> str:
    if not iso_ano_mes:
        return "período não informado"
    ano, mes = int(iso_ano_mes[:4]), int(iso_ano_mes[5:7])
    return f"{MESES[mes - 1]} de {ano}"


def periodo_meses_br(inicio: str | None, fim: str | None) -> str:
    if inicio and fim and inicio[:4] == fim[:4]:
        return f"de {MESES[int(inicio[5:7]) - 1]} a {mes_br(fim)}"
    return f"de {mes_br(inicio)} a {mes_br(fim)}"


def _rotulo_fonte(tabela: str, meta: dict[str, Any]) -> str:
    origem = meta.get("origem", "snapshot")
    if origem == "snapshot":
        return f"{tabela} (snapshot validado em {data_br(meta.get('snapshot_validado_em'))})"
    return f"{tabela} (Databricks, consultado em {meta.get('consultado_em')})"


def trechos_de_dados(
    kpis: dict[str, Any],
    meta_kpis: dict[str, Any],
    subprefeituras: dict[str, Any],
    meta_sub: dict[str, Any],
    mensal: list[dict[str, Any]],
    meta_mensal: dict[str, Any],
    clima: list[dict[str, Any]],
    meta_clima: dict[str, Any],
    indice: dict[str, Any] | None = None,
) -> list[Trecho]:
    trechos: list[Trecho] = []
    ala = kpis["alagamentos"]
    cl = kpis["clima"]

    trechos.append(
        Trecho(
            id="kpi:resumo",
            titulo="Resumo da base histórica de alagamentos",
            texto=(
                f"A base histórica do AlertaBairro tem {ala['total']} ocorrências únicas de alagamento, "
                f"registradas {periodo_meses_br(ala['periodo_inicio'], ala['periodo_fim'])}, distribuídas em "
                f"{kpis['subprefeituras_com_registros']} subprefeituras com registros. "
                "Os dados vêm do GeoSampa/Defesa Civil e são históricos, não em tempo real."
            ),
            fonte=_rotulo_fonte(meta_kpis.get("tabela", "ouro"), meta_kpis),
        )
    )
    trechos.append(
        Trecho(
            id="clima:resumo",
            titulo="Resumo da chuva histórica",
            texto=(
                f"Entre {data_br(cl['periodo_inicio'])} e {data_br(cl['periodo_fim'])} choveu "
                f"{_mm(cl['chuva_acumulada_mm'])} mm no total no ponto de referência (latitude -23,55, "
                f"longitude -46,63, região central de São Paulo). O maior volume em um dia foi "
                f"{_mm(cl['maior_chuva_diaria_mm'])} mm, em {data_br(cl.get('data_maior_chuva'))}. "
                "A fonte é o Open-Meteo, e o valor vale para esse ponto, não para a cidade toda. "
                "O período da chuva não coincide com o dos alagamentos, então não é possível afirmar correlação."
            ),
            fonte=_rotulo_fonte(meta_clima.get("tabela", "ouro_clima_diario"), meta_clima),
        )
    )

    itens = subprefeituras.get("itens", [])
    total_grupos = kpis.get("subprefeituras_com_registros") or len(itens)
    for posicao, item in enumerate(itens, start=1):
        periodo = ""
        if item.get("primeira_ocorrencia") and item.get("ultima_ocorrencia"):
            periodo = (
                f" O primeiro registro é de {data_br(item['primeira_ocorrencia'])} e o último, "
                f"de {data_br(item['ultima_ocorrencia'])}."
            )
        trechos.append(
            Trecho(
                id=f"sub:{item.get('chave') or posicao}",
                titulo=f"Alagamentos na subprefeitura {item['subprefeitura']}",
                texto=(
                    f"Segundo a base histórica, a subprefeitura {item['subprefeitura']} tem "
                    f"{item['total_ocorrencias']} registros de alagamento, ocupando a posição {posicao} "
                    f"entre {total_grupos} subprefeituras com registros.{periodo} "
                    "O ranking mostra a distribuição dos registros na base, não um índice de risco, "
                    "e não considera população nem área."
                ),
                fonte=_rotulo_fonte(meta_sub.get("tabela", "ouro_alagamentos_subprefeitura"), meta_sub),
            )
        )
    demais = subprefeituras.get("demais")
    if demais:
        trechos.append(
            Trecho(
                id="sub:demais",
                titulo="Demais subprefeituras do ranking",
                texto=(
                    f"Além das {len(itens)} subprefeituras com mais registros, outras {demais['grupos']} "
                    f"subprefeituras somam {demais['total_ocorrencias']} registros. Os nomes delas não "
                    "constam do snapshot validado."
                ),
                fonte=_rotulo_fonte(meta_sub.get("tabela", "ouro_alagamentos_subprefeitura"), meta_sub),
            )
        )

    presentes = {}
    for linha in mensal:
        d = date.fromisoformat(linha["mes"][:10])
        presentes[(d.year, d.month)] = linha["total_ocorrencias"]
        trechos.append(
            Trecho(
                id=f"mes:{d.year}-{d.month:02d}",
                titulo=f"Alagamentos em {MESES[d.month - 1]} de {d.year}",
                texto=(
                    f"Em {MESES[d.month - 1]} de {d.year}, a base histórica tem "
                    f"{linha['total_ocorrencias']} registros de alagamento."
                ),
                fonte=_rotulo_fonte(meta_mensal.get("tabela", "ouro_alagamentos_mensal"), meta_mensal),
            )
        )
    if presentes:
        inicio, fim = min(presentes), max(presentes)
        ano, mes = inicio
        while (ano, mes) <= fim:
            if (ano, mes) not in presentes:
                trechos.append(
                    Trecho(
                        id=f"mes:{ano}-{mes:02d}",
                        titulo=f"Alagamentos em {MESES[mes - 1]} de {ano}",
                        texto=(
                            f"{MESES[mes - 1].capitalize()} de {ano} não tem linha na tabela mensal. "
                            "Isso é uma lacuna da base e não comprova que não houve alagamentos nesse mês."
                        ),
                        fonte=_rotulo_fonte(meta_mensal.get("tabela", "ouro_alagamentos_mensal"), meta_mensal),
                    )
                )
            mes += 1
            if mes > 12:
                ano, mes = ano + 1, 1

    for linha in clima:
        trechos.append(
            Trecho(
                id=f"chuva:{linha['data']}",
                titulo=f"Chuva em {data_br(linha['data'])}",
                texto=(
                    f"Em {data_br(linha['data'])} choveu {_mm(linha['precipitacao_mm'])} mm no ponto de "
                    f"referência da região central de São Paulo. O acumulado desde o início da série era "
                    f"{_mm(linha.get('precipitacao_acumulada_mm'))} mm."
                ),
                fonte=_rotulo_fonte(meta_clima.get("tabela", "ouro_clima_diario"), meta_clima),
            )
        )

    if indice:
        for regiao in indice.get("regioes", []):
            trechos.append(
                Trecho(
                    id=f"indice:{regiao.get('chave')}",
                    titulo=f"Índice experimental de atenção para {regiao['subprefeitura']}",
                    texto=(
                        f"No índice experimental do AlertaBairro (regras documentadas, ilustrativo), "
                        f"{regiao['subprefeitura']} aparece com {regiao['rotulo'].lower()}: {regiao['explicacao']} "
                        "O índice não é previsão nem substitui a Defesa Civil."
                    ),
                    fonte=f"Índice experimental AlertaBairro (data de referência {data_br(indice.get('data_referencia'))})",
                )
            )
    return trechos


def _trecho_de_secao(arquivo: Path, numero: int, titulo: str | None, linhas: list[str], fonte: str) -> Trecho | None:
    texto = " ".join(l.strip() for l in linhas if l.strip())
    if not titulo or not texto:
        return None
    return Trecho(id=f"doc:{arquivo.stem}#{numero}", titulo=titulo, texto=texto, fonte=fonte, tipo="documento")


def trechos_de_documentos(pasta: str | Path) -> list[Trecho]:
    """Um trecho por seção "## " de cada arquivo Markdown; a linha "Fonte:" vale para o arquivo todo."""
    trechos: list[Trecho] = []
    base = Path(pasta)
    if not base.exists():
        return trechos
    for arquivo in sorted(base.glob("*.md")):
        titulo_doc = arquivo.stem
        fonte = f"Documento {arquivo.name}"
        secoes: list[tuple[str, list[str]]] = []
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if linha.startswith("# "):
                titulo_doc = linha[2:].strip()
            elif linha.lower().startswith("fonte:"):
                fonte = f"{titulo_doc} — {linha.split(':', 1)[1].strip()}"
            elif linha.startswith("## "):
                secoes.append((linha[3:].strip(), []))
            elif secoes:
                secoes[-1][1].append(linha)
        numero = 0
        for titulo, linhas in secoes:
            trecho = _trecho_de_secao(arquivo, numero + 1, titulo, linhas, fonte)
            if trecho:
                numero += 1
                trechos.append(trecho)
    return trechos
