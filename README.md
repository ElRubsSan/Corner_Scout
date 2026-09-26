# CornerScout

CornerScout es un MVP academico de analisis prepartido de corners ofensivos. El caso de estudio usa StatsBomb Open Data de LaLiga 2015/16 (`competition_id=11`, `season_id=27`): todos los resultados son historicos y no describen el estado actual de los equipos.

## Estado

La aplicacion local incluye pipeline modular canonico `01`-`07`, evaluacion temporal, FastAPI/OpenAPI, Angular standalone y generacion OpenAI exclusivamente desde FastAPI con fallback determinista. No se ha realizado una llamada real a OpenAI, validado Docker con un motor real ni desplegado el sistema.

Resultados canonicos: 380 partidos, 1,295,354 eventos, 3,841 corners, 3,835 secuencias SCR-15 evaluables, 6 excluidas por ambiguedad temporal y 1,245 secuencias con tiro.

## Pipeline canonico

| Etapa | Implementacion | Salida principal |
|---|---|---|
| `01_ingestion` | `analytics.ingestion`, `analytics.io` | contrato de ingesta y raw verificado |
| `02_clean` | `analytics.cleaning`, `analytics.context` | eventos normalizados y contexto previo |
| `03_scr15` | `analytics.scr15` | secuencias SCR-15 auditables |
| `04_features` | `analytics.features` | variables prepartido y K-Means descriptivo |
| `05_modeling` | `analytics.modeling` | evaluacion temporal y decisiones por objetivo |
| `06_reporte_tactico_llm` | `analytics.tactical_report`, `backend.openai` | evidencia y reporte validado con fallback |
| `07_herramientas_agente` | `analytics.agent_tools`, `backend.agent` | agente acotado a tres tools de solo lectura |

Los notebooks `01`-`07` conservan la explicacion y evidencia cientifica; la logica ejecutable canonica ya esta extraida a modulos Python probados. Los originales aportados permanecen en `notebooks/prueba/` y sus hashes en `notebooks/source-manifest.json`.

## Instalacion y ejecucion

Requisitos: uv, Python >=3.11, Node y npm. Desde la raiz:

```powershell
uv sync --locked --all-extras
uv run cornerscout ingest
uv run cornerscout clean
uv run cornerscout scr15
uv run cornerscout features
uv run --extra ml cornerscout train
uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

`uv run cornerscout build` ejecuta `02_clean`, `03_scr15` y `04_features` en orden. La ingesta es explicita y reanudable; no se descarga ni entrena durante una solicitud web. Para restaurar la copia de Drive, seguir `docs/data-restoration.md` y no sobrescribir `data/raw`.

En otra terminal:

```powershell
npm --prefix frontend ci
npm --prefix frontend start
```

Abrir http://127.0.0.1:4200; Swagger queda en http://127.0.0.1:8000/docs. Ejemplo historico: rival Barcelona y corte exclusivo `2016-03-01`.

## OpenAI y agente

`OPENAI_API_KEY` y `OPENAI_MODEL` son variables exclusivas del backend. Sin clave, ante indisponibilidad o si la salida estructurada no supera las validaciones, FastAPI devuelve un fallback determinista identificado como tal. Angular nunca recibe claves, prompts ni acceso directo al proveedor. No se afirma una llamada real con una clave.

El agente solo puede invocar `obtener_historial`, `obtener_perfil_corners` y `consultar_evidencia`. Las tres tools son de solo lectura, operan sobre la sesion bloqueada por rival y fecha de corte, no aceptan SQL libre y no calculan ni entrenan modelos. Ver `docs/openai.md`.

## Metodo y decisiones

SCR-15 comienza en un `Pass` de tipo `Corner` y termina por el primer cierre aplicable: 15 segundos, cambio de `possession_team`, fin de periodo o nuevo corner. Un tiro exactamente a los 15 segundos cuenta si no ocurrio antes otro cierre. Un cambio de ID de posesion con el mismo equipo y otras reanudaciones solo se auditan.

Decisiones canonicas de `05_modeling`:

- `scr15`: `league_reference`.
- `short_direct`: `candidate`.
- `delivery_zone`: `not_modelled`.
- `corner_count`: `candidate`.
- K-Means queda fijo con datos predesarrollo, es descriptivo y no entra como predictor.

FastAPI consume exclusivamente contratos y artefactos canonicos verificados de `02_clean`, `03_scr15`, `04_features` y `05_modeling`. DuckDB ejecuta consultas controladas; la API no consulta los artefactos demo antiguos.

## Verificacion registrada

- Python: `uv run --all-extras pytest` dio `77 passed, 1 skipped`.
- Angular: `npm --prefix frontend run typecheck` y `npm --prefix frontend run build` pasaron.
- Navegador: `npm --prefix frontend run e2e` paso 2 recorridos.
- No se ha probado Docker, Vercel ni una llamada real a OpenAI.

Para validar notebooks sin reescribirlos: `uv run --all-extras python scripts/notebooks.py --through 7`. Para contratos: `uv run --extra api python scripts/export_openapi.py`, `npm --prefix tools/codegen ci` y `npm --prefix tools/codegen run generate`.

## Datos y arquitectura

Los datos crudos y artefactos pesados no forman parte de Git. La copia canonica raw esta en `/content/drive/MyDrive/Corner_Scout/data/raw`; localmente se usa `data/raw/` o `CORNERSCOUT_DATA_DIR`.

```text
StatsBomb raw (inmutable)
  -> 01 ingestion
  -> 02 clean
  -> 03 SCR-15
  -> 04 features + K-Means descriptivo
  -> 05 modeling
  -> FastAPI/DuckDB -> 06 reporte + 07 agente -> Angular
```

Documentacion principal: `docs/architecture.md`, `docs/scr15-methodology.md`, `docs/model-card.md`, `docs/openai.md`, `docs/deployment.md`, `docs/demo.md` y `RESUMEN_DE_CONTINUIDAD.md`.

Fuente: [StatsBomb Open Data](https://github.com/statsbomb/open-data), revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Incorporar el logo oficial del media pack antes de una publicacion externa; este repositorio no redistribuye raw.
