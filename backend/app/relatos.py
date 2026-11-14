"""Relatos da comunidade: validação, armazenamento (SQLite) e moderação.

LGPD by design:
- não coletamos nome, e-mail, telefone ou qualquer identificador do morador;
- a descrição é recusada se contiver e-mail, CPF ou telefone;
- a coordenada é arredondada para 3 casas (~110 m) antes de ser gravada;
- a foto é reprocessada no servidor (remove EXIF/GPS) e apagada após `retencao_fotos_dias`;
- relatos só ficam públicos depois de aprovados por um moderador.
"""

from __future__ import annotations

import io
import re
import secrets
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

TIPOS = {
    "alagamento": "Alagamento",
    "via_intransitavel": "Via intransitável",
    "boca_de_lobo": "Boca de lobo entupida",
    "corrego_transbordando": "Córrego transbordando",
    "outro": "Outro",
}
STATUS = ("pendente", "aprovado", "rejeitado")

# Limites aproximados do município de São Paulo (bounding box)
LAT_MIN, LAT_MAX = -24.01, -23.35
LON_MIN, LON_MAX = -46.83, -46.36
CASAS_COORDENADA = 3
DESCRICAO_MIN, DESCRICAO_MAX = 15, 500
MAX_DIAS_PASSADO = 7
TOLERANCIA_FUTURO = timedelta(minutes=10)
FOTO_MAX_BYTES = 3 * 1024 * 1024
FOTO_LADO_MAX = 1600

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_TELEFONE = re.compile(r"(?:\(?\b\d{2}\)?[\s.-]?)?\b9?\d{4}[\s.-]?\d{4}\b")


class ErroValidacao(ValueError):
    def __init__(self, erros: dict[str, str]) -> None:
        super().__init__("; ".join(f"{k}: {v}" for k, v in erros.items()))
        self.erros = erros


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def contem_dado_pessoal(texto: str) -> str | None:
    if _EMAIL.search(texto):
        return "e-mail"
    if _CPF.search(texto):
        return "CPF"
    if _TELEFONE.search(texto):
        return "telefone"
    return None


def _parse_datahora(valor: str) -> datetime:
    texto = valor.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(texto)
    if dt.tzinfo is None:
        # Horário sem fuso vindo do formulário é interpretado como horário de Brasília (UTC-3)
        dt = dt.replace(tzinfo=timezone(timedelta(hours=-3)))
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class NovoRelato:
    tipo: str
    descricao: str
    ocorrido_em: datetime
    latitude: float
    longitude: float
    subprefeitura: str | None


def validar(
    *,
    tipo: str | None,
    descricao: str | None,
    ocorrido_em: str | None,
    latitude: Any,
    longitude: Any,
    aceite_termos: Any,
    subprefeitura: str | None = None,
    agora: datetime | None = None,
) -> NovoRelato:
    agora = agora or _agora()
    erros: dict[str, str] = {}

    tipo = (tipo or "").strip()
    if tipo not in TIPOS:
        erros["tipo"] = "Escolha um tipo de ocorrência da lista."

    texto = " ".join((descricao or "").split())
    if len(texto) < DESCRICAO_MIN:
        erros["descricao"] = f"Descreva a ocorrência com pelo menos {DESCRICAO_MIN} caracteres."
    elif len(texto) > DESCRICAO_MAX:
        erros["descricao"] = f"A descrição pode ter no máximo {DESCRICAO_MAX} caracteres."
    else:
        achado = contem_dado_pessoal(texto)
        if achado:
            erros["descricao"] = f"Remova dados pessoais da descrição (encontramos algo parecido com {achado})."

    quando: datetime | None = None
    try:
        quando = _parse_datahora(ocorrido_em or "")
        if quando > agora + TOLERANCIA_FUTURO:
            erros["ocorrido_em"] = "A data e a hora não podem estar no futuro."
        elif quando < agora - timedelta(days=MAX_DIAS_PASSADO):
            erros["ocorrido_em"] = f"Relatos devem ser de no máximo {MAX_DIAS_PASSADO} dias atrás."
    except ValueError:
        erros["ocorrido_em"] = "Informe a data e a hora da ocorrência."

    lat = lon = None
    try:
        lat = float(latitude)
        lon = float(longitude)
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            erros["localizacao"] = "O ponto escolhido está fora do município de São Paulo."
    except (TypeError, ValueError):
        erros["localizacao"] = "Marque o local da ocorrência no mapa."

    if str(aceite_termos).lower() not in {"true", "1", "sim", "on"}:
        erros["aceite_termos"] = "É preciso concordar com o uso das informações para publicar o relato."

    sub = (subprefeitura or "").strip() or None
    if sub and len(sub) > 80:
        erros["subprefeitura"] = "Nome de subprefeitura inválido."

    if erros:
        raise ErroValidacao(erros)

    assert quando is not None and lat is not None and lon is not None
    return NovoRelato(
        tipo=tipo,
        descricao=texto,
        ocorrido_em=quando,
        latitude=round(lat, CASAS_COORDENADA),
        longitude=round(lon, CASAS_COORDENADA),
        subprefeitura=sub,
    )


def processar_foto(conteudo: bytes) -> bytes:
    """Valida e regrava a imagem como JPEG sem metadados (EXIF/GPS removidos)."""
    if len(conteudo) > FOTO_MAX_BYTES:
        raise ErroValidacao({"foto": "A foto deve ter no máximo 3 MB."})
    assinaturas = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")
    if not conteudo.startswith(assinaturas):
        raise ErroValidacao({"foto": "Envie uma imagem JPEG, PNG ou WebP."})
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(conteudo)) as img:
            img.verify()
        with Image.open(io.BytesIO(conteudo)) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((FOTO_LADO_MAX, FOTO_LADO_MAX))
            saida = io.BytesIO()
            img.save(saida, format="JPEG", quality=82, optimize=True)  # sem exif=
            return saida.getvalue()
    except ErroValidacao:
        raise
    except Exception:  # noqa: BLE001 - qualquer falha do decodificador = arquivo inválido
        raise ErroValidacao({"foto": "Não foi possível ler a imagem enviada."}) from None


_ESQUEMA = """
CREATE TABLE IF NOT EXISTS relatos (
    id TEXT PRIMARY KEY,
    protocolo TEXT UNIQUE NOT NULL,
    criado_em TEXT NOT NULL,
    ocorrido_em TEXT NOT NULL,
    tipo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    subprefeitura TEXT,
    status TEXT NOT NULL DEFAULT 'pendente',
    motivo_moderacao TEXT,
    moderado_em TEXT,
    foto_arquivo TEXT,
    foto_removida_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_relatos_status ON relatos(status);
CREATE INDEX IF NOT EXISTS idx_relatos_criado ON relatos(criado_em);
"""


def _gerar_protocolo() -> str:
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O/1/I para facilitar a leitura
    return "AB-" + "".join(secrets.choice(alfabeto) for _ in range(6))


class RepositorioRelatos:
    def __init__(self, db_path: str | Path, uploads_dir: str | Path, retencao_fotos_dias: int = 90) -> None:
        self._db_path = str(db_path)
        self._uploads = Path(uploads_dir)
        self._retencao = timedelta(days=retencao_fotos_dias)
        self._trava = threading.Lock()
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._uploads.mkdir(parents=True, exist_ok=True)
        self._memoria: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._memoria = sqlite3.connect(":memory:", check_same_thread=False)
            self._memoria.row_factory = sqlite3.Row
        with self._conexao() as con:
            con.executescript(_ESQUEMA)

    @contextmanager
    def _conexao(self) -> Iterator[sqlite3.Connection]:
        with self._trava:
            if self._memoria is not None:
                yield self._memoria
                self._memoria.commit()
                return
            con = sqlite3.connect(self._db_path, timeout=10)
            con.row_factory = sqlite3.Row
            try:
                yield con
                con.commit()
            finally:
                con.close()

    # ---------------------------------------------------------------- escrita
    def criar(self, relato: NovoRelato, foto_jpeg: bytes | None = None, agora: datetime | None = None) -> dict[str, Any]:
        agora = agora or _agora()
        relato_id = str(uuid.uuid4())
        foto_arquivo = None
        if foto_jpeg:
            foto_arquivo = f"{relato_id}.jpg"
            (self._uploads / foto_arquivo).write_bytes(foto_jpeg)
        for _ in range(5):
            protocolo = _gerar_protocolo()
            try:
                with self._conexao() as con:
                    con.execute(
                        """INSERT INTO relatos (id, protocolo, criado_em, ocorrido_em, tipo, descricao,
                               latitude, longitude, subprefeitura, status, foto_arquivo)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?)""",
                        (
                            relato_id,
                            protocolo,
                            agora.isoformat(timespec="seconds"),
                            relato.ocorrido_em.isoformat(timespec="seconds"),
                            relato.tipo,
                            relato.descricao,
                            relato.latitude,
                            relato.longitude,
                            relato.subprefeitura,
                            foto_arquivo,
                        ),
                    )
                break
            except sqlite3.IntegrityError:
                continue
        else:  # pragma: no cover - colisão de protocolo 5 vezes seguidas
            raise RuntimeError("Não foi possível gerar um protocolo único")
        return {"id": relato_id, "protocolo": protocolo, "status": "pendente"}

    def moderar(self, relato_id: str, acao: str, motivo: str | None = None, agora: datetime | None = None) -> dict[str, Any] | None:
        if acao not in {"aprovar", "rejeitar"}:
            raise ErroValidacao({"acao": "Use 'aprovar' ou 'rejeitar'."})
        novo_status = "aprovado" if acao == "aprovar" else "rejeitado"
        agora = agora or _agora()
        motivo_limpo = " ".join((motivo or "").split())[:200] or None
        with self._conexao() as con:
            cur = con.execute(
                "UPDATE relatos SET status = ?, motivo_moderacao = ?, moderado_em = ? WHERE id = ?",
                (novo_status, motivo_limpo, agora.isoformat(timespec="seconds"), relato_id),
            )
            if cur.rowcount == 0:
                return None
            linha = con.execute("SELECT * FROM relatos WHERE id = ?", (relato_id,)).fetchone()
        if novo_status == "rejeitado" and linha["foto_arquivo"]:
            self._apagar_foto(relato_id, linha["foto_arquivo"], agora)
        return self._publico(linha) | {"status": novo_status}

    def _apagar_foto(self, relato_id: str, arquivo: str, agora: datetime) -> None:
        caminho = self._uploads / Path(arquivo).name
        caminho.unlink(missing_ok=True)
        with self._conexao() as con:
            con.execute(
                "UPDATE relatos SET foto_arquivo = NULL, foto_removida_em = ? WHERE id = ?",
                (agora.isoformat(timespec="seconds"), relato_id),
            )

    def aplicar_retencao(self, agora: datetime | None = None) -> int:
        """Apaga fotos mais antigas que o prazo de retenção. Retorna quantas foram removidas."""
        agora = agora or _agora()
        limite = (agora - self._retencao).isoformat(timespec="seconds")
        with self._conexao() as con:
            linhas = con.execute(
                "SELECT id, foto_arquivo FROM relatos WHERE foto_arquivo IS NOT NULL AND criado_em < ?",
                (limite,),
            ).fetchall()
        for linha in linhas:
            self._apagar_foto(linha["id"], linha["foto_arquivo"], agora)
        return len(linhas)

    # ---------------------------------------------------------------- leitura
    @staticmethod
    def _publico(linha: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": linha["id"],
            "tipo": linha["tipo"],
            "tipo_rotulo": TIPOS.get(linha["tipo"], linha["tipo"]),
            "descricao": linha["descricao"],
            "ocorrido_em": linha["ocorrido_em"],
            "latitude": linha["latitude"],
            "longitude": linha["longitude"],
            "subprefeitura": linha["subprefeitura"],
            "tem_foto": bool(linha["foto_arquivo"]),
        }

    def listar_aprovados(self, limite: int = 200) -> list[dict[str, Any]]:
        with self._conexao() as con:
            linhas = con.execute(
                "SELECT * FROM relatos WHERE status = 'aprovado' ORDER BY ocorrido_em DESC LIMIT ?",
                (max(1, min(int(limite), 500)),),
            ).fetchall()
        return [self._publico(l) for l in linhas]

    def listar_para_moderacao(self, status: str = "pendente", limite: int = 100) -> list[dict[str, Any]]:
        if status not in STATUS:
            raise ErroValidacao({"status": "Status inválido."})
        with self._conexao() as con:
            linhas = con.execute(
                "SELECT * FROM relatos WHERE status = ? ORDER BY criado_em ASC LIMIT ?",
                (status, max(1, min(int(limite), 500))),
            ).fetchall()
        return [
            self._publico(l)
            | {
                "protocolo": l["protocolo"],
                "status": l["status"],
                "criado_em": l["criado_em"],
                "motivo_moderacao": l["motivo_moderacao"],
            }
            for l in linhas
        ]

    def consultar_protocolo(self, protocolo: str) -> dict[str, Any] | None:
        with self._conexao() as con:
            linha = con.execute(
                "SELECT status, criado_em, motivo_moderacao FROM relatos WHERE protocolo = ?",
                (protocolo.strip().upper(),),
            ).fetchone()
        if not linha:
            return None
        return {"protocolo": protocolo.strip().upper(), "status": linha["status"], "criado_em": linha["criado_em"],
                "motivo_moderacao": linha["motivo_moderacao"]}

    def caminho_foto(self, relato_id: str, somente_aprovado: bool = True) -> Path | None:
        sql = "SELECT foto_arquivo, status FROM relatos WHERE id = ?"
        with self._conexao() as con:
            linha = con.execute(sql, (relato_id,)).fetchone()
        if not linha or not linha["foto_arquivo"]:
            return None
        if somente_aprovado and linha["status"] != "aprovado":
            return None
        caminho = self._uploads / Path(linha["foto_arquivo"]).name
        return caminho if caminho.exists() else None

    def indicadores(self) -> dict[str, Any]:
        with self._conexao() as con:
            linhas = con.execute("SELECT status, COUNT(*) AS n FROM relatos GROUP BY status").fetchall()
            ultimo = con.execute("SELECT MAX(criado_em) AS m FROM relatos").fetchone()["m"]
        contagem = {s: 0 for s in STATUS}
        for l in linhas:
            contagem[l["status"]] = l["n"]
        total = sum(contagem.values())
        moderados = contagem["aprovado"] + contagem["rejeitado"]
        return {
            "total": total,
            **contagem,
            "taxa_aprovacao": round(contagem["aprovado"] / moderados, 3) if moderados else None,
            "ultimo_relato_em": ultimo,
        }
