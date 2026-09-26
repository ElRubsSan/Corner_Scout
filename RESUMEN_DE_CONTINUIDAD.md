# CornerScout - resumen de continuidad

## Estado real

El pipeline modular canonico `01`-`07`, FastAPI/OpenAPI y Angular standalone estan implementados. La logica cientifica ya fue extraida de los notebooks a modulos Python probados; los notebooks siguen siendo evidencia canonica. No se ha desplegado, probado Docker con motor real ni ejecutado una llamada real a OpenAI.

El producto usa exclusivamente datos historicos de LaLiga 2015/16. No presentar resultados como actuales.

## Etapas

| Etapa | Responsabilidad | Ubicacion |
|---|---|---|
| `01_ingestion` | ingesta inmutable, conteos y hashes | `analytics.ingestion`, `analytics.io` |
| `02_clean` | normalizacion y contexto previo | `analytics.cleaning`, `analytics.context` |
| `03_scr15` | secuencias y auditoria | `analytics.scr15` |
| `04_features` | variables prepartido y K-Means descriptivo | `analytics.features` |
| `05_modeling` | evaluacion temporal y decisiones | `analytics.modeling` |
| `06_reporte_tactico_llm` | contrato de evidencia, OpenAI y fallback | `analytics.tactical_report`, `backend.openai` |
| `07_herramientas_agente` | tres tools read-only y agente acotado | `analytics.agent_tools`, `backend.agent` |

## Resultados canonicos

- 380 partidos y 1,295,354 eventos.
- 3,841 corners; 3,835 evaluables, 6 excluidos y 1,245 con tiro.
- SCR-15 cierra por el primer limite entre 15 segundos, cambio de `possession_team`, fin de periodo y nuevo corner.
- No hubo atribucion compartida de tiros; cambios de ID con el mismo equipo y otras reanudaciones se auditan.
- K-Means se fijo con datos predesarrollo, describe destinos y no entra en ningun predictor.

Decisiones `05_modeling`:

| Objetivo | Decision |
|---|---|
| `scr15` | `league_reference` |
| `short_direct` | `candidate` |
| `delivery_zone` | `not_modelled` |
| `corner_count` | `candidate` |

## Backend

FastAPI carga contratos `02-clean-v2`, `03-scr15-v2`, `04-features-v2` y `05-modeling-v3-objectives`. Verifica runs, hashes y linaje antes de abrir artefactos canonicos. DuckDB solo consulta tablas conocidas con parametros validados. Los scouting runs fijan la identidad de datos y se escriben en `data/processed/runs`.

OpenAI se usa exclusivamente desde FastAPI mediante Responses API y Structured Outputs/Pydantic. `OPENAI_API_KEY` y `OPENAI_MODEL` son backend-only. Falta de clave, proveedor no disponible o salida invalida activa fallback determinista visible. No se ha hecho una llamada real.

El agente registra exactamente `obtener_historial`, `obtener_perfil_corners` y `consultar_evidencia`. Son tools tipadas, de solo lectura, bloqueadas por sesion y sin SQL libre, web, archivos, raw o entrenamiento.

## Verificacion registrada

| Comando | Resultado registrado |
|---|---|
| `uv run --all-extras pytest` | `77 passed, 1 skipped` |
| `npm --prefix frontend run typecheck` | pasa |
| `npm --prefix frontend run build` | pasa |
| `npm --prefix frontend run e2e` | 2 E2E pasan |

Estas son afirmaciones historicas de la verificacion disponible; repetir las pruebas despues de cambios funcionales. No hay validacion equivalente de Docker, Vercel ni OpenAI real.

## Operacion local

```powershell
uv sync --locked --all-extras
uv run cornerscout ingest
uv run cornerscout clean
uv run cornerscout scr15
uv run cornerscout features
uv run --extra ml cornerscout train
uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend start
```

`uv run cornerscout build` sustituye los comandos `clean`, `scr15` y `features` cuando se desea ejecutarlos en secuencia. `uv run --all-extras python scripts/notebooks.py --through 7` valida los siete notebooks sin reescribirlos.

## Despliegue pendiente

Docker debe preservar bajo `/data` los montajes `interim/02_clean`, `interim/03_scr15`, `processed/04_features`, `processed/05_modeling` y `processed/runs`; solo `runs` necesita escritura. No montar artefactos demo antiguos. Despues deben probarse contratos, health, creacion de runs, CORS/HTTPS y Vercel con recursos reales.

## Riesgos y siguientes pasos

1. Ejecutar una prueba controlada de OpenAI con secreto solo en backend y registrar modelo, resultado y fallback sin exponer la clave.
2. Validar la topologia Docker con los cinco montajes canonicos; la configuracion no equivale a una prueba.
3. Desplegar FastAPI con HTTPS y despues configurar `apiBaseUrl`/CORS para Vercel.
4. Mantener visibles las limitaciones cientificas: temporada unica, proxy corto/directo, ausencia de video/tracking y no causalidad de clusters o candidatos.
