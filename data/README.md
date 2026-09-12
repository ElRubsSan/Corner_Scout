# Datos locales

Esta carpeta representa las capas de datos de CornerScout.

```text
data/
|-- raw/        Copia local inmutable restaurada desde Google Drive
|-- interim/    Futuras salidas auditadas y secuencias
|-- processed/  Futuros KPIs y agregados de producto
`-- manifests/  Inventarios pequenos y versionables
```

`raw`, `interim` y `processed` estan excluidas de Git salvo sus archivos `.gitkeep`. La copia canonica actual de raw esta en `/content/drive/MyDrive/Corner_Scout/data/raw`. No coloque credenciales ni enlaces privados en ningun manifiesto.

Consulte `../docs/data-restoration.md` antes de copiar archivos.
