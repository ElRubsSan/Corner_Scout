# Datos para Vercel

Esta carpeta aloja `vercel-canonical-data.zip`, el paquete de datos canónicos
utilizado para desplegar CornerScout. El ZIP permanece fuera de Git.

## Generar el paquete

Desde la raíz, con las etapas `02`–`05` disponibles:

```powershell
uv run --extra api python scripts/vercel_data.py package
```

El comando verifica contratos, hashes y linaje, genera el ZIP y muestra su
SHA-256. El archivo se publica como asset inmutable de una release y se configura
en Vercel mediante `CORNERSCOUT_DATA_ARCHIVE_URL` y
`CORNERSCOUT_DATA_ARCHIVE_SHA256`.

Consulta [Despliegue en Vercel](../docs/vercel.md).
