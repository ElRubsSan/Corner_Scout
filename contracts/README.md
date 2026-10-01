# Contratos implementados

CornerScout utiliza dos fronteras tipadas:

- **Pipeline:** `analytics/contracts.py` define `StageContract` y `Artifact`.
  Cada etapa publica `contract.json` junto a sus archivos locales.
- **HTTP:** `backend/schemas.py` define solicitudes y respuestas; FastAPI
  genera `contracts/openapi.json`, que alimenta el cliente TypeScript.

## Versiones del pipeline

| Etapa | Versión | Directorio bajo la raíz de datos |
|---|---|---|
| Ingesta | `01-ingestion-v1` | `interim/01_ingestion` |
| Limpieza | `02-clean-v2` | `interim/02_clean` |
| Secuencias | `03-scr15-v2` | `interim/03_scr15` |
| Variables | `04-features-v2` | `processed/04_features` |
| Modelado | `05-modeling-v3-objectives` | `processed/05_modeling` |

Un contrato declara etapa, versión, run, artefactos, SHA-256 y metadatos de
conteos y linaje. Las rutas de artefactos son relativas y no pueden escapar
del directorio de etapa. La publicación se realiza después de completar los
archivos. FastAPI rechaza archivos faltantes, versiones o hashes incompatibles
y relaciones de origen inconsistentes.

## Documentos

- [Entrada raw](raw-input.md): archivos inmutables y campos del proveedor.
- [Entidades](processed-entities.md): unidades, tablas y trazabilidad vigentes.
- [Arquitectura](../docs/architecture.md): consumidores de cada frontera.

## Regenerar el contrato HTTP y el cliente

Desde la raíz, después de instalar Python y Node como indica el README:

```powershell
uv run --extra api python scripts/export_openapi.py
npm --prefix tools/codegen ci
npm --prefix tools/codegen run generate
npm --prefix frontend run typecheck
```

Los dos archivos generados se versionan: `contracts/openapi.json` y
`frontend/src/app/core/api.generated.ts`. Revisa su diff cuando cambie una
solicitud o respuesta. El build de Angular consume el cliente ya generado;
no necesita ejecutar Python.

Un cambio científico de esquema requiere documentar versión anterior, motivo,
campos afectados y reconstrucción o migración. La limpieza documental no altera
los contratos científicos.
