# CornerScout

CornerScout es un MVP academico para preparar defensivamente un partido mediante el analisis de los corners ofensivos del proximo rival.

El caso de estudio utiliza StatsBomb Open Data para LaLiga 2015/16 (`competition_id=11`, `season_id=27`). Toda salida debe identificarse como analisis historico y no como informacion actual de los equipos.

## Estado

Aplicacion local implementada: pipeline auditable, modelos temporales evaluados, FastAPI/OpenAPI, Angular standalone y reportes Gemini con fallback. El frontend esta configurado para Vercel; no se han realizado despliegues externos ni llamadas con secretos reales. Ver `RESUMEN_DE_CONTINUIDAD.md` para el estado verificado y pendientes.

## Instalacion y ejecucion local

Requisitos: uv, Python >=3.11 (probado 3.13.2), Node 24.15+ (probado 24.19.0), npm. Ejecutar desde la raiz:

```powershell
uv sync --locked --all-extras
uv run cornerscout ingest
uv run python -m analytics.audit
uv run cornerscout build
uv run --extra ml cornerscout train
uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

La ingesta es explicita y reanudable; no se ejecuta en cada consulta. Si ya dispone de una copia de Drive, restaurar sus cuatro metadatos y events/ bajo data/raw o definir CORNERSCOUT_DATA_DIR hacia el directorio que contiene raw/. No sobrescribir archivos existentes.

En otra terminal, desde `frontend/`:

```powershell
npm ci
npm start
```

Abrir http://127.0.0.1:4200. API y Swagger: http://127.0.0.1:8000/docs. Rival de ejemplo: Barcelona; corte 2016-03-01. Confirmar ocho partidos antes de analizar. Para Gemini, configurar GEMINI_API_KEY solamente en el proceso backend; sin clave se muestra explicitamente el reporte determinista.

## Verificaciones

Desde la raiz: `uv run --all-extras pytest`.

Desde frontend: `npm run build`, `npm run typecheck`, `npx playwright install chromium`, `npm run e2e`. E2E inicia ambos servidores locales y los detiene al finalizar; requiere puertos 8000 y 4200 libres y datos procesados reales.

Notebooks: `uv run --all-extras python scripts/notebooks.py --through 5` valida estructura y hashes sin modificar celdas. `uv run --all-extras python scripts/notebooks.py --execute --through 3` ejecuta la fase B corregida y guarda copias bajo la capa procesada ignorada. `01` a `03` ya pasaron localmente; la ejecucion integral `01` a `05` en Colab sigue pendiente. Guia remota: docs/colab.md.

Contratos: `uv run --extra api python scripts/export_openapi.py`, `npm --prefix tools/codegen ci`, `npm --prefix tools/codegen run generate`. Codegen usa TS5 aislado; Angular usa TS6. Los lockfiles evitan forzar peers incompatibles.

## Resultados reales y limites

- 380 partidos, 20 equipos, 1,295,354 eventos y 3,841 corners.
- Seis secuencias no evaluables por reloj regresivo; un corner fuera de limites espaciales. Se muestran denominadores evaluables y exclusiones.
- Baseline, regresion logistica y Random Forest entrenados y evaluados en bloques temporales. LR/RF no mejoraron consistentemente la validacion: se sirve baseline liguero anterior al corte.
- K-Means usa snapshots mensuales anteriores al corte; describe destinos de pase, no jugadas ensayadas.
- Gemini probado con mocks tipados, no con una clave real. Validacion semantica humana sigue siendo necesaria.
- La ejecucion local ordenada de `01` a `03` concilio las once exclusiones historicas en seis secuencias desconocidas y cinco falsos positivos posteriores al cierre; no hubo tiros compartidos. La ejecucion integral en Colab, Docker y proveedores externos permanece pendiente. Docker no esta instalado localmente.

## Objetivo inicial

Para un rival y una fecha de corte, CornerScout debe seleccionar sus ocho partidos inmediatamente anteriores y describir:

- Cantidad de corners ofensivos.
- Lado y tipo de ejecucion.
- Zonas de destino.
- Principales cobradores.
- Patrones recurrentes.
- SCR-15 y xG descriptivo por corner.
- Evidencia, cobertura y limitaciones.

La prediccion supervisada fue evaluada despues de validar SCR-15; los candidatos no se promocionaron al no superar consistentemente el baseline.

## Alcance excluido

- Datos actuales o en vivo.
- Video, tracking y datos 360.
- Prediccion de goles como objetivo principal.
- Apuestas, fichajes o predicciones de marcador.
- Autenticacion real.
- Metricas calculadas por un LLM.

## Estructura

```text
Corner_Scope/
|-- AGENTS.md
|-- README.md
|-- contracts/       Contratos logicos de entrada y entidades
|-- data/            Capas locales ignoradas y manifiestos versionables
|-- docs/            Arquitectura, metodologia y restauracion
|-- notebooks/       Notebooks sanitizados de Colab
|-- analytics/       Futura libreria de procesamiento y ciencia de datos
|-- backend/         Futura aplicacion FastAPI
|-- frontend/        Futura aplicacion Angular
`-- artifacts/       Futuros modelos y metadatos generados
```

## Datos

Los datos crudos no forman parte de Git. Su copia canonica actual esta en `/content/drive/MyDrive/Corner_Scout/data/raw` y debe restaurarse localmente bajo `data/raw/` siguiendo `docs/data-restoration.md`.

Antes de escribir procesamiento analitico se requieren:

- 380 archivos `<match_id>.jsonl.gz`, uno por partido.
- `competitions.csv`, `matches_laliga_2015_16.csv`, `metadata_ingesta.json` y `registro_ingesta.csv`.
- Un manifiesto con checksums y conteos, sin rutas privadas ni credenciales.

Los notebooks cientificos aportados por el usuario ya son las versiones canonicas `01` a `05`. Sus originales permanecen localmente en `notebooks/prueba/` y sus hashes estan en `notebooks/source-manifest.json`. Los artefactos de investigacion no sustituyen automaticamente los de la demo.

Los formatos y campos esperados estan definidos en `contracts/raw-input.md`.

## Flujo previsto

```text
Google Drive
    |
    v
data/raw (inmutable, fuera de Git)
    |
    v
data/interim (auditado y secuencias)
    |
    v
data/processed (KPIs, patrones y reportes)
    |
    v
FastAPI + DuckDB -> Angular
```

## Documentacion

- `docs/architecture.md`: arquitectura y responsabilidades.
- `docs/demo.md`: demo en cinco minutos.
- `docs/academic-report.md`: estructura academica y evidencias.
- `docs/presentation.md`: guion de presentacion y video.
- `docs/model-card.md`: modelos, criterio de seleccion y limitaciones.
- `docs/deployment.md`: configuracion Vercel/backend sin desplegar.
- `docs/data-restoration.md`: archivos de Colab y restauracion desde Drive.
- `docs/scr15-methodology.md`: regla SCR-15, auditoria local y pendientes remotos.
- `notebooks/source-manifest.json`: procedencia y hashes de los notebooks cientificos y evidencia local.
- `contracts/raw-input.md`: contrato de los archivos de entrada.
- `contracts/processed-entities.md`: entidades logicas previstas.
- `data/manifests/README.md`: contrato de manifiestos.

## Fuente

Fuente: [StatsBomb Open Data](https://github.com/statsbomb/open-data), revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Credito incluido en la interfaz y reportes. El README oficial solicita atribucion y logo del media pack al publicar; incorporar el recurso oficial de marca antes de publicacion externa. Datos historicos para investigacion academica; no se redistribuye raw en este repositorio.
