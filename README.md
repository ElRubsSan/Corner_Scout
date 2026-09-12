# CornerScout

CornerScout es un MVP academico para preparar defensivamente un partido mediante el analisis de los corners ofensivos del proximo rival.

El caso de estudio utiliza StatsBomb Open Data para LaLiga 2015/16 (`competition_id=11`, `season_id=27`). Toda salida debe identificarse como analisis historico y no como informacion actual de los equipos.

## Estado

El proyecto se encuentra en la fase 1: estructura, documentacion y contratos. Aun no contiene pipelines ejecutables, API, frontend, modelos ni despliegue.

## Objetivo inicial

Para un rival y una fecha de corte, CornerScout debe seleccionar sus ocho partidos inmediatamente anteriores y describir:

- Cantidad de corners ofensivos.
- Lado y tipo de ejecucion.
- Zonas de destino.
- Principales cobradores.
- Patrones recurrentes.
- SCR-15 y xG descriptivo por corner.
- Evidencia, cobertura y limitaciones.

La prediccion supervisada se abordara despues de implementar y validar el calculo de SCR-15.

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

El notebook actual `Third_Man_Analytics_Ingesta_de_Datos.ipynb` permanece fuera del repositorio hasta confirmar su incorporacion y futuro cambio de nombre a `01_ingesta_statsbomb.ipynb`.

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
- `docs/data-restoration.md`: archivos de Colab y restauracion desde Drive.
- `docs/scr15-methodology.md`: regla provisional y auditorias pendientes.
- `contracts/raw-input.md`: contrato de los archivos de entrada.
- `contracts/processed-entities.md`: entidades logicas previstas.
- `data/manifests/README.md`: contrato de manifiestos.

## Fuente

StatsBomb Open Data. La atribucion y las condiciones de uso se verificaran y mostraran en el producto antes de publicar cualquier demo.
