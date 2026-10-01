# Backend · FastAPI

La API sirve evidencia histórica de LaLiga 2015/16 con consultas DuckDB
controladas, contratos Pydantic y OpenAI opcional. No descarga StatsBomb ni
entrena por solicitud. La instalación completa comienza en el
[README principal](../README.md).

## Instalar y arrancar

Desde la raíz del repositorio, con Python y uv instalados:

```powershell
uv sync --locked --all-extras
```

Prepara o restaura las cuatro etapas `02`–`05` según
[la guía de datos](../docs/data-restoration.md). Copia `.env.example` a `.env`
desde el editor. La clave puede quedar vacía para usar respaldo determinista.

```powershell
uv run --all-extras uvicorn backend.main:app --env-file .env --host 127.0.0.1 --port 8000
```

Si no creaste `.env`, omite `--env-file .env`. Detén el servicio con Ctrl+C.
Reinícialo tras cambiar variables o artefactos. Para desarrollo con recarga,
añade `--reload --reload-dir backend --reload-dir analytics`; así no vigila
los datos ni el entorno virtual.

## Comprobar que está disponible

- http://127.0.0.1:8000/api/v1/health: proceso activo (`status: ok`).
- http://127.0.0.1:8000/api/v1/ready: contratos, hashes y lectura canónica
  disponibles (`status: ready`).
- http://127.0.0.1:8000/docs: Swagger, esquemas y pruebas HTTP interactivas.
- http://127.0.0.1:8000/openapi.json: contrato HTTP generado por FastAPI.

Un health correcto no garantiza que los datos estén listos. Si ready devuelve
503, consulta el error de la terminal y restaura o construye el conjunto entero.

## Recorrido HTTP

Todas las rutas de producto empiezan por `/api/v1`:

| Ruta | Finalidad |
|---|---|
| `GET /teams`, `GET /matches` | Selección de rival y partidos históricos. |
| `POST /scouting-runs` | Crear una sesión con exactamente ocho partidos previos. |
| `GET /scouting-runs/{run_id}` | Recuperar una sesión compatible. |
| `GET .../matches-profile`, `.../summary`, `.../habits` | Historial y perfil descriptivo. |
| `GET .../corners`, `.../destination-heatmap`, `.../patterns` | Pases, mapas y grupos de destinos. |
| `GET .../quality`, `.../model` | Calidad y decisiones temporales. |
| `GET .../report-plan`, `POST .../report` | Plan y reporte con evidencia. |
| `POST .../agent` | Pregunta de seguimiento dentro de la sesión. |

Usa Swagger para el cuerpo exacto y las respuestas de cada endpoint. Los runs
se escriben en `processed/runs`; un cambio del fingerprint canónico invalida
los análisis incompatibles.

## Configuración

| Variable | Uso |
|---|---|
| `CORNERSCOUT_DATA_DIR` | Padre de `raw`, `interim` y `processed`; por defecto `data`. |
| `CORNERSCOUT_ORIGINS` | Orígenes CORS separados por comas, sin rutas. |
| `OPENAI_API_KEY` | Clave opcional, exclusivamente backend. |
| `OPENAI_MODEL` | Modelo disponible con salida estructurada; ejemplo `gpt-4.1-mini`. |

El reporte y agente identifican OpenAI o fallback. El agente registra solo
`obtener_historial`, `obtener_perfil_corners` y `consultar_evidencia`, con rival
y corte bloqueados. Ver [OpenAI](../docs/openai.md).

## Verificar y mantener

```powershell
uv run --all-extras pytest
uv run --extra api python scripts/export_openapi.py
```

Para completar la regeneración del cliente, seguir
[contratos](../contracts/README.md). Docker y los montajes se explican en
[despliegue](../docs/deployment.md). La publicación externa sigue pendiente.
