# Datos locales

Esta carpeta representa las capas de datos de CornerScout.

```text
data/
|-- raw/        Copia local inmutable restaurada desde Google Drive
|-- interim/    Salidas auditadas, contratos y secuencias
|-- processed/  Futuros KPIs y agregados de producto
`-- manifests/  Inventarios pequenos y versionables
```

`raw`, `interim` y `processed` estan excluidas de Git salvo sus archivos `.gitkeep`. La copia canonica actual de raw esta en `/content/drive/MyDrive/Corner_Scout/data/raw`. Los directorios `interim/01_ingestion`, `02_clean` y `03_scr15` contienen la ejecucion local auditada de fase B. Los ZIP locales son evidencia anterior aportada por el usuario; permanecen ignorados y no se extraen ni promueven automaticamente. No coloque credenciales ni enlaces privados en ningun manifiesto.

`manual_labels/short_corner_review.csv` contiene 40 etiquetas humanas que deben preservarse sin reconstruirlas desde el proxy. Sus notas y metodologia se auditaran antes de presentar concordancia como validacion independiente.

Consulte `../docs/data-restoration.md` antes de copiar archivos.
