# Analytics

Pipeline offline canonico, sin ejecucion de notebooks. Cada frontera carga un
`contract.json` con Pydantic, exige la etapa y version esperadas y verifica el
SHA-256 de todos sus artefactos antes de consumirlos. El contrato se publica de
forma atomica y siempre despues de completar los artefactos. `data/raw` solo se
crea durante la ingesta y nunca se reescribe.

Comandos:

```powershell
uv run cornerscout ingest
uv run --extra ml cornerscout build
uv run --extra ml cornerscout clean
uv run --extra ml cornerscout scr15
uv run --extra ml cornerscout features
uv run --extra ml cornerscout train
```

`build` produce y valida `02_clean` -> `03_scr15` -> `04_features` usando
`cleaning`, `context`, `scr15`, `features` y `modeling`. Los comandos de etapa
requieren que el contrato anterior ya exista y sea valido; no saltan controles.

`train` consume `04_features` solo despues de validar todos sus hashes y publica
`05-modeling-v3-objectives` con modelos, esquemas, predicciones, tuning,
metricas, bootstrap por partido, gates y contrato. Usa LR regularizada para
objetivos categoricos y Poisson para conteo; Random Forest y K-Means no son
predictores. Las decisiones usan exclusivamente las tres ventanas de desarrollo.
El periodo final puede evaluarse, pero permanece como confirmacion y no altera
gates, hiperparametros globales ni ganadores.

Para validar sin sustituir una publicacion existente se puede llamar
`analytics.pipeline.train(Path("data"), output=directorio_temporal)`; la fuente
04 se verifica en su ubicacion canonica y toda la salida 05 se aisla en el
directorio indicado.
