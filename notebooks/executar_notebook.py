"""Executa um notebook .ipynb célula a célula e grava as saídas (texto e figuras) no próprio arquivo.

Existe porque o ambiente da equipe nem sempre tem Jupyter instalado. Para notebooks que só leem os
arquivos do repositório (01 e 03), basta Python 3 e matplotlib:

    python3 notebooks/executar_notebook.py notebooks/01_busca_recall.ipynb

O notebook do LoRA (02) precisa de GPU e roda no Google Colab.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import sys
import traceback
from pathlib import Path


def executar(caminho: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nb = json.loads(caminho.read_text(encoding="utf-8"))
    os.chdir(caminho.parent)
    ambiente: dict = {"__name__": "__main__"}
    contador = 0
    for celula in nb["cells"]:
        if celula["cell_type"] != "code":
            continue
        contador += 1
        codigo = "".join(celula["source"])
        saida = io.StringIO()
        saidas: list[dict] = []
        try:
            with contextlib.redirect_stdout(saida):
                exec(compile(codigo, f"<célula {contador}>", "exec"), ambiente)  # noqa: S102  # nosec B102 nosemgrep - executa o próprio notebook do repositório
        except Exception:  # noqa: BLE001
            texto = saida.getvalue()
            if texto:
                saidas.append({"output_type": "stream", "name": "stdout", "text": texto.splitlines(True)})
            saidas.append({"output_type": "error", "ename": "Erro", "evalue": "", "traceback": traceback.format_exc().splitlines()})
            celula["outputs"], celula["execution_count"] = saidas, contador
            caminho.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
            raise
        texto = saida.getvalue()
        if texto:
            saidas.append({"output_type": "stream", "name": "stdout", "text": texto.splitlines(True)})
        for numero in plt.get_fignums():
            buffer = io.BytesIO()
            plt.figure(numero).savefig(buffer, format="png", dpi=110, bbox_inches="tight")
            saidas.append({"output_type": "display_data", "metadata": {},
                           "data": {"image/png": base64.b64encode(buffer.getvalue()).decode("ascii"),
                                    "text/plain": ["<Figure>"]}})
        plt.close("all")
        celula["outputs"], celula["execution_count"] = saidas, contador
    caminho.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{caminho.name}: {contador} células executadas")


if __name__ == "__main__":
    for caminho in [Path(a).resolve() for a in sys.argv[1:]]:
        executar(caminho)
