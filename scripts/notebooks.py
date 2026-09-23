"""Validate or execute the canonical scientific notebooks without rewriting them."""
import argparse
import asyncio
import sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from analytics.io import ROOT, data_dir, digest, write_json

NOTEBOOKS = [
    "01_ingesta_statsbomb",
    "02_limpieza_eda",
    "03_secuencias_scr15",
    "04_ingenieria_variables",
    "05_modelos_evaluacion",
    "06_reporte_tactico_llm",
    "07_herramientas_agente",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--through", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.start <= args.through <= len(NOTEBOOKS):
        parser.error("Require 1 <= --start <= --through <= 5")
    logs = []
    for name in NOTEBOOKS[args.start - 1:args.through]:
        path = ROOT / "notebooks" / f"{name}.ipynb"
        book = nbformat.read(path, as_version=4)
        nbformat.validate(book)
        status = "validated"
        if args.execute:
            manager = AsyncKernelManager(kernel_name="python3")
            manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
            client = NotebookClient(book, km=manager, timeout=600, resources={"metadata": {"path": str(ROOT)}})
            try:
                # Use the active environment instead of an unrelated global kernel.
                client.execute()
            finally:
                asyncio.run(manager.shutdown_kernel(now=True))
            target = data_dir() / "processed" / "executed_notebooks"
            target.mkdir(parents=True, exist_ok=True)
            executed_path = target / path.name
            nbformat.write(book, executed_path)
            status = "executed"
        record = {"notebook": path.name, "status": status, "source_sha256": digest(path)}
        if args.execute:
            record["executed_copy"] = executed_path.relative_to(data_dir()).as_posix()
            record["executed_sha256"] = digest(executed_path)
        logs.append(record)
    write_json(data_dir() / "manifests" / "notebook-execution.json", logs)


if __name__ == "__main__":
    main()
