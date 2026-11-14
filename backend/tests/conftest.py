import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from app.config import Config  # noqa: E402


@pytest.fixture
def config_snapshot(tmp_path) -> Config:
    return Config(
        db_path=str(tmp_path / "teste.db"),
        uploads_dir=str(tmp_path / "uploads"),
        snapshot_dir=str(tmp_path / "snapshot"),
        base_conhecimento_dir=str(RAIZ / "base_conhecimento"),
        admin_token="token-de-teste-com-mais-de-16",
        limite_relatos_por_hora=100,
        limite_assistente_por_minuto=100,
    )
