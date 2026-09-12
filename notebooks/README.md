# Notebooks

Esta carpeta contiene cinco notebooks nuevos, sin outputs raw versionados, generados desde scripts/notebooks.py. Cubren ingesta, auditoria/EDA, secuencias SCR-15, variables historicas y modelos. Las salidas ejecutadas se guardan localmente en data/processed/executed_notebooks.

El notebook actual de Colab es `Third_Man_Analytics_Ingesta_de_Datos.ipynb` y permanece fuera del repositorio hasta confirmar su incorporacion. Mas adelante se evaluara una copia sanitizada y su cambio de nombre consistente a `01_ingesta_statsbomb.ipynb`.

La logica productiva vive en analytics/ y tiene pruebas. Ejecutar `uv run --all-extras python scripts/notebooks.py --execute --through 5`. Ver docs/colab.md para el runtime remoto, cuya validacion queda pendiente.
