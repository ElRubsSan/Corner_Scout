# Notebooks cientificos

Los notebooks canonicos se adoptaron de las versiones desarrolladas por el usuario en Google Colab/Drive el 2026-09-19. Sus originales exactos se conservan localmente en `notebooks/prueba/` y `source-manifest.json` registra su origen. Los canonicos `01` a `03` fueron corregidos y validados localmente en la fase B; `04` y `05` conservan todavia la linea historica de Colab.

La metodologia se validara primero en notebooks ejecutables y explicativos. Cuando una etapa quede aprobada, su logica se extraera a modulos Python y se comprobara la equivalencia entre las salidas del notebook y del modulo antes de integrarla con FastAPI. La implementacion actual de `analytics/` y los artefactos de la demo permanecen como referencia y no se promueven ni sustituyen automaticamente.

## Responsabilidades

1. `01_ingesta_statsbomb.ipynb`: ingesta y trazabilidad del raw.
2. `02_limpieza_eda.ipynb`: normalizacion, calidad y EDA estructural.
3. `03_secuencias_scr15.ipynb`: construccion y auditoria de SCR-15.
4. `04_ingenieria_variables.ipynb`: ingenieria, EDA tactico e historicos prepartido.
5. `05_modelos_evaluacion.ipynb`: validacion temporal, seleccion y evaluacion.
6. `06_reporte_tactico_llm.ipynb`: pendiente; evidencia y reporte tactico con LLM.
7. `07_herramientas_agente.ipynb`: pendiente; herramientas de lectura y agente acotado.

## Estado de la evidencia

- Los notebooks `01` a `03` se ejecutaron en orden localmente sobre 380 partidos y conservan sus copias ejecutadas bajo `data/processed/executed_notebooks/`.
- Sus contratos encadenados quedan bajo `data/interim/01_ingestion`, `02_clean` y `03_scr15`; estas rutas estan fuera de Git.
- Los notebooks `04` y `05` y sus salidas guardadas siguen siendo evidencia historica de Colab, pendiente de adaptacion a los contratos corregidos.
- Todavia no se ha verificado una ejecucion ordenada `01` a `05` desde un runtime limpio de Colab.
- Los ZIP locales de `data/interim/` y `data/processed/` conservan los derivados de la misma linea de investigacion; no se han promovido a la demo.
- `data/manual_labels/short_corner_review.csv` conserva las 40 etiquetas humanas del proxy de corner corto.

## Validacion y ejecucion

`scripts/notebooks.py` ya no crea ni sobrescribe notebooks. Sin `--execute` valida el formato y registra los hashes:

```powershell
uv run --all-extras python scripts/notebooks.py --through 5
```

La ejecucion local corregida de fase B es:

```powershell
uv run --all-extras python scripts/notebooks.py --execute --through 3
```

El script no sobrescribe los fuentes: guarda evidencia ejecutada en la capa procesada ignorada. La ejecucion integral `01` a `05` permanece destinada a Colab despues de adaptar `04` y `05`. Ver `docs/colab.md`.
