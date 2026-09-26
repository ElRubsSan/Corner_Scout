# CornerScout - Guia de trabajo

## Producto y estado

- El producto visible es **CornerScout**; se conservan temporalmente la carpeta `Corner_Scope` y el remoto `Corner_Scout`.
- Es un MVP academico prepartido sobre StatsBomb Open Data, LaLiga 2015/16 (`competition_id=11`, `season_id=27`). Nunca presentar resultados historicos como actuales.
- Estan implementados el pipeline modular canonico `01`-`07`, FastAPI/OpenAPI, Angular standalone, evaluacion temporal y OpenAI exclusivamente desde FastAPI con fallback determinista.
- No se ha realizado despliegue externo, prueba de Docker con motor real ni llamada real a OpenAI.
- La interfaz final es Angular standalone. No usar Streamlit, Gradio, Tableau ni Power BI.

## Pipeline canonico

1. `01_ingestion`: ingesta inmutable y contrato de hashes.
2. `02_clean`: normalizacion y contexto previo al evento.
3. `03_scr15`: secuencias y auditoria SCR-15.
4. `04_features`: variables prepartido y K-Means descriptivo predesarrollo.
5. `05_modeling`: evaluacion temporal y seleccion por objetivo.
6. `06_reporte_tactico_llm`: evidencia, reporte tipado, OpenAI y fallback.
7. `07_herramientas_agente`: tres tools de solo lectura y agente acotado.

Los notebooks `01`-`07` son la evidencia cientifica canonica y la logica ejecutable ya esta extraida a modulos Python probados. Los originales se conservan en `notebooks/prueba/`; no modificar notebooks o contratos sin una solicitud explicita.

## Datos

- `data/raw` es inmutable y no se versiona. La copia de Drive esta en `/content/drive/MyDrive/Corner_Scout/data/raw`.
- Los nombres raw son `competitions.csv`, `matches_laliga_2015_16.csv`, `metadata_ingesta.json`, `registro_ingesta.csv` y `events/<match_id>.jsonl.gz`.
- Raw, interim, processed, Parquet, JSONL comprimido y modelos entrenados permanecen fuera de Git.
- Cada etapa publica un contrato con version, run, hashes, conteos y linaje. FastAPI rechaza contratos, hashes o linajes canonicos invalidos.
- Resultados canonicos: 380 partidos, 1,295,354 eventos, 3,841 corners, 3,835 evaluables, 6 excluidos y 1,245 con tiro.
- No sustituir datos ausentes por datos sinteticos salvo fixtures de prueba claramente identificados.

## SCR-15

- Inicia en un evento `Pass` con `pass_type=Corner`.
- Termina en el primero de cuatro cierres: limite de 15 segundos, cambio de `possession_team`, fin de periodo o nuevo corner.
- Un tiro exactamente a los 15 segundos se incluye si no ocurrio antes otro cierre.
- Un cambio de ID de `possession` con el mismo equipo no cierra; se audita.
- Saques de banda, meta, libres y otras reanudaciones distintas de un nuevo corner se auditan, pero no cierran automaticamente.
- Nunca atribuir un tiro de una posesion posterior. Las seis secuencias con reloj ambiguo son desconocidas y se excluyen del denominador evaluable.
- La especificacion completa esta en `docs/scr15-methodology.md`.

## Modelado

- Las ventanas usan los ocho partidos estrictamente anteriores y cortes exclusivos.
- Decisiones `05`: `scr15=league_reference`, `short_direct=candidate`, `delivery_zone=not_modelled`, `corner_count=candidate`.
- K-Means esta fijado con datos predesarrollo, solo describe destinos y nunca entra como predictor.
- No presentar clusters como jugadas ensayadas ni modelos candidatos como garantia causal.
- FastAPI sirve decisiones y artefactos canonicos; no entrena por solicitud.

## Backend y OpenAI

- FastAPI consume contratos y artefactos verificados de `data/interim/02_clean`, `data/interim/03_scr15`, `data/processed/04_features` y `data/processed/05_modeling`.
- DuckDB solo ejecuta consultas controladas y parametrizadas. Un LLM nunca genera SQL libre.
- OpenAI se invoca solo desde FastAPI mediante Structured Outputs/Pydantic. `OPENAI_API_KEY` y `OPENAI_MODEL` son backend-only.
- Falta de clave, proveedor no disponible o salida invalida activa fallback determinista visible. No afirmar una llamada real hasta ejecutarla y registrarla.
- El agente solo registra `obtener_historial`, `obtener_perfil_corners` y `consultar_evidencia`; son tools tipadas de solo lectura y bloqueadas a la sesion.
- Una respuesta final invalida puede repararse una sola vez, sin nuevas tools ni cambios de evidencia; un segundo fallo activa el fallback determinista.
- Los calculos, ventanas, clusters, probabilidades y evidencia se producen en Python, nunca en el LLM.

## Frontend y despliegue

- Angular consume el contrato OpenAPI generado por FastAPI. Las claves y prompts nunca llegan al navegador.
- Vercel esta configurado, pero no desplegado.
- El backend Docker debe montar, conservando esas rutas bajo `/data`: `interim/02_clean`, `interim/03_scr15`, `processed/04_features`, `processed/05_modeling` y `processed/runs` con escritura solo para `runs`.
- No montar ni servir los artefactos demo antiguos. No afirmar que Docker esta probado.

## Comandos

```powershell
uv sync --locked --all-extras
uv run cornerscout ingest
uv run cornerscout clean
uv run cornerscout scr15
uv run cornerscout features
uv run cornerscout build
uv run --extra ml cornerscout train
uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000
uv run --all-extras pytest
uv run --all-extras python scripts/notebooks.py --through 7
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run e2e
```

Verificacion registrada: Python `77 passed, 1 skipped`; Angular typecheck/build; 2 E2E. Solo repetir estas afirmaciones como historicas hasta ejecutar una nueva validacion.

## Seguridad y Git

- Nunca versionar `.env`, claves, tokens, URLs privadas, rutas personales o credenciales.
- No borrar ni sobrescribir raw ni revertir cambios ajenos.
- No hacer commits, push, despliegues ni cambios irreversibles sin autorizacion explicita.
- Mantener cambios pequenos y verificables; usar tipado explicito en limites publicos e ISO 8601 para fechas.

## Cierre de fase

Informar archivos modificados, decisiones, validaciones, riesgos/datos pendientes y siguiente fase recomendada.
