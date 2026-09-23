# CornerScout — resumen de continuidad

## Estado real

Fases 2–6 implementadas y verificadas localmente. Fase 7: documentacion academica y demo preparadas; build y pruebas integrales locales pasan. No se han realizado despliegues externos, usado secretos reales ni hecho push de estos hitos.

La validacion externa de Colab/Docker/Gemini/Vercel sigue pendiente; no confundirla con la validacion local completada.

El 2026-09-19 se autorizo un enfoque notebook-first. Los originales del usuario permanecen en `notebooks/prueba/` y `notebooks/source-manifest.json` registra sus hashes. La fase B corrigio y ejecuto localmente los canonicos `01` a `03`; `04` y `05` conservan la linea historica de Colab. La demo y `analytics/` permanecen como referencia hasta probar equivalencia; no se promovieron ZIP ni modelos aportados.

## Hitos locales

- `a54e6f0`: ingesta inmutable, adaptador eventos anidados/aplanados, gate y SCR-15.
- `b5519b9`: evaluacion temporal LR/RF/baseline y snapshots K-Means.
- `75c08e0`: FastAPI, OpenAPI, runs y reporte determinista.
- `477735c`: Gemini Structured Outputs con fallback y mocks tipados.
- `56da46d`: Angular standalone, lockfile limpio, tipos y flujo E2E.
- Cierre documental posterior: README, guias academicas/Colab, arquitectura actual y estado de cero partidos.

## Archivos principales creados o modificados

- `pyproject.toml`, `uv.lock`: dependencias Python gestionadas con uv.
- `analytics/{io,pipeline,audit,models,cli}.py`: pipeline y modelos.
- `backend/{main,schemas,service,reporting,gemini}.py`: API/reportes.
- `contracts/openapi.json`, `frontend/src/app/core/api.generated.ts`: contrato generado.
- `frontend/src/app/features/`: inicio, seleccion, dashboard, mapa, patrones, reporte y calidad.
- `frontend/package.json`, `frontend/package-lock.json`, `tools/codegen/`: Angular TS6 y generador TS5 aislados.
- `frontend/e2e/scouting.spec.ts`, `tests/`: pruebas de navegador, API, Gemini, secuencias y temporalidad.
- `notebooks/01_*.ipynb` a `05_*.ipynb`: copias canonicas de los notebooks cientificos del usuario. `scripts/notebooks.py` los valida o ejecuta, pero ya no los genera ni sobrescribe.
- `data/manifests/raw.json`, `quality-summary.json`, `notebook-execution.json`: evidencia versionable.
- `docs/model-card.md`, `model-evaluation.json`, `calibration.png`, `data-audit.md`: resultados reales.
- `docs/{colab,demo,academic-report,presentation,official-sources,deployment}.md`: entrega y operaciones.
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `frontend/vercel.json`: configuraciones sin desplegar.
- `README.md`, `AGENTS.md`: instrucciones y estado actualizado.

Raw, Parquet, joblib y datos pesados permanecen ignorados por Git. Los originales aportados se conservan en `notebooks/prueba/`; las copias canonicas incluyen las salidas cientificas guardadas. Los ZIP de interim/processed permanecen locales e ignorados.

## Resultados de verificacion

| Comando | Directorio | Resultado |
|---|---|---|
| `uv sync --all-extras` | raiz | Dependencias instaladas con uv 0.12.13 |
| `uv run cornerscout ingest` | raiz | 380 partidos reales, revision StatsBomb fijada |
| `uv run python -m analytics.audit` | raiz | Anomalias conservadas para inspeccion |
| `uv run cornerscout build` | raiz | Gate aprobado; 380 partidos, 20 equipos, 1,295,354 eventos, 3,841 corners |
| `uv run --extra ml cornerscout train` | raiz | 3,039 observaciones con ocho partidos previos; baseline seleccionado |
| `uv run --all-extras python scripts/notebooks.py --execute --through 3` | raiz | Fase B ejecutada: 3,841 corners, 3,835 evaluables, 6 excluidos, 0 tiros compartidos |
| `uv run --all-extras pytest` | raiz | 18 pruebas pasan; dos warnings de dependencias TestClient |
| `npm ci --prefer-offline --no-audit --loglevel info` | frontend | Instalacion limpia completada; descarga @angular/common fue lenta |
| `npm ls @angular/core @angular/common @angular/forms @angular/router @angular/compiler @angular/platform-browser @angular/build @angular/cli` | frontend | Framework 22.1.6 coherente; CLI/build 22.1.8 |
| `npm run build` | frontend | Build de produccion pasa, 247.06 kB iniciales |
| `npm run typecheck` | frontend | Pasa |
| `npm run e2e` | frontend | 2 pruebas Chromium pasan con backend y datos reales |
| `docker --version` | raiz | Docker no instalado; no se valido contenedor |

## Error Angular resuelto

@angular/common y @angular/common/http fallaban por una instalacion incompleta tras timeouts de descarga. Se hizo npm ci completo y se verifico el arbol de dependencias y build. Ningun modulo se marco external. No usar --force ni --legacy-peer-deps para resolverlo. El generador OpenAPI se mantiene separado porque declara peer TS5 y Angular requiere TS6.

## Errores/limitaciones abiertos

1. `01` a `03` pasaron en orden localmente, pero falta repetirlos en un runtime limpio de Colab y adaptar/ejecutar `04` y `05`; no afirmar reproducibilidad integral o remota hasta completar ese flujo.
2. Docker no disponible; configuracion preparada, no probada con motor real.
3. Gemini no probado con una clave real. Mocks cubren respuesta valida, clave ausente, timeout, cuota, JSON invalido, cifras/referencias inventadas. La comprobacion semantica completa de texto libre no esta automatizada.
4. LR/RF no superan consistentemente baseline; no se sirve una prediccion supervisada promocionada. Se muestra tasa liguera anterior al corte, explicitamente etiquetada.
5. SCR-15 quedo conciliado por evento: seis regresiones dentro de ventana permanecen desconocidas y cinco exclusiones antiguas eran falsos positivos posteriores al primer cierre. Falta probar equivalencia entre notebook y modulo productivo. El proxy corto de investigacion usa 18 unidades y conserva 40 etiquetas humanas.
6. Falta rubrica academica concreta para ajustar ponderaciones y estructura final; falta grabacion del video y logo oficial StatsBomb antes de publicacion externa.
7. API de demo selecciona rival por nombre exacto y corte exclusivo por fecha. No hay autenticacion. La persistencia de runs requiere directorio escribible. No afirmar preparacion operativa multiusuario de produccion.

## Siguiente accion exacta

Para levantar la demo validada: desde la raiz ejecutar `uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000`; desde frontend ejecutar `npm start`. Abrir http://127.0.0.1:4200 y seguir docs/demo.md.

La siguiente fase cientifica es adaptar `04` al contrato `03-scr15-v2`, auditar las 40 etiquetas humanas y reconstruir historicos prepartido antes de reejecutar `05`. En paralelo debe comprobarse la equivalencia del motor SCR-15 del notebook con el modulo productivo. Docker, Gemini real y despliegue quedan separados.
