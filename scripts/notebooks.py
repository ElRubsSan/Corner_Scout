"""Create reviewed teaching notebooks; execute without storing raw outputs in Git."""
import argparse
import asyncio
import sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from analytics.io import ROOT, data_dir, write_json

CELLS = {
    "01_ingesta_statsbomb": ("Ingesta inmutable", "from analytics.io import ingest\ningest()"),
    "02_limpieza_eda": ("Auditoria y EDA", "from analytics.audit import audit_anomalies\nfrom analytics.pipeline import build\naudit_anomalies()\nbuild()"),
    "03_secuencias_scr15": ("Corners y SCR-15", "import pandas as pd\nfrom analytics.io import data_dir\nc = pd.read_parquet(data_dir() / 'processed/corners.parquet')\nprint(c.groupby('end_reason').size())\nprint('Secuencias validas:', c.valid_sequence.sum())\nprint('SCR-15 evaluable:', c.loc[c.valid_sequence, 'shot_within_15s'].mean())"),
    "04_ingenieria_variables": ("Variables historicas sin fuga", "from analytics.models import features\nfrom analytics.io import data_dir\nimport pandas as pd\nm = pd.read_parquet(data_dir() / 'processed/matches.parquet')\nc = pd.read_parquet(data_dir() / 'processed/corners.parquet')\nf = features(m, c)\nprint(f.describe().to_string())"),
    "05_modelos_evaluacion": ("Evaluacion temporal", "from analytics.models import train\ntrain()"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--through", type=int, default=5)
    args = parser.parse_args()
    logs = []
    for name, (title, code) in list(CELLS.items())[:args.through]:
        path = ROOT / "notebooks" / f"{name}.ipynb"
        book = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell(f"# CornerScout: {title}\nStatsBomb Open Data, LaLiga 2015/16. Ver docs/colab.md para instalar con uv. Datos reales; no ejecutar modelos hasta pasar el gate. Este notebook nuevo no modifica el original de Colab."),
            nbformat.v4.new_code_cell("import os, sys\nfrom pathlib import Path\nroot = Path.cwd() if (Path.cwd() / 'pyproject.toml').exists() else Path.cwd().parent\nsys.path.insert(0, str(root))"),
            nbformat.v4.new_code_cell(code)], metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
        nbformat.write(book, path)
        if args.execute:
            manager = AsyncKernelManager(kernel_name="python3")
            manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
            client = NotebookClient(book, km=manager, timeout=600, resources={"metadata": {"path": str(ROOT)}})
            # Use the active uv environment instead of an unrelated global kernel.
            client.execute()
            asyncio.run(manager.shutdown_kernel(now=True))
            target = data_dir() / "processed" / "executed_notebooks"
            target.mkdir(parents=True, exist_ok=True)
            nbformat.write(book, target / path.name)
            logs.append({"notebook": path.name, "status": "executed"})
    write_json(data_dir() / "manifests" / "notebook-execution.json", logs)


if __name__ == "__main__":
    main()
