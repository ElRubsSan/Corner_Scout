# Datos locales de CornerScout

```text
data/
  raw/                         fuente inmutable
  interim/01_ingestion/        contrato de ingesta
  interim/02_clean/            eventos y contexto previo
  interim/03_scr15/            secuencias y auditorías
  processed/04_features/       históricos, geometría y clusters descriptivos
  processed/05_modeling/       modelos, métricas y decisiones
  processed/runs/              análisis creados por la aplicación
  manifests/                  inventarios auxiliares
  manual_labels/              40 etiquetas exploratorias preservadas
```

Raw, interim y processed están fuera de Git salvo sus `.gitkeep`. La app
necesita las cuatro etapas `02`–`05` completas y permiso de escritura para
`processed/runs`. No descarga ni entrena al arrancar.

Desde la raíz del repositorio, después de instalar dependencias:

```powershell
uv run cornerscout ingest
uv run --all-extras cornerscout build
uv run --all-extras cornerscout train
```

Para restaurar una copia o elegir otra raíz, seguir
[la guía de datos](../docs/data-restoration.md). No mezclar una etapa nueva con
una etapa anterior incompatible. Reiniciar FastAPI después de sustituir datos.

`manual_labels/short_corner_review.csv` no se regenera desde el proxy: conserva
las 40 etiquetas originales. Su revisión fue asistida y no independiente.
La nota sobre sus límites está en [modelado](../docs/model-card.md).

Los ZIP y artefactos antiguos que puedan existir en una instalación local no
se promueven automáticamente. Los contratos de etapa son la autoridad vigente.
