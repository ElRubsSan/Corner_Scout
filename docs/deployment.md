# Operación y despliegue

La ruta pública principal es Vercel Services y está descrita en
[Despliegue en Vercel](vercel.md). Docker reproduce el backend localmente para
desarrollo, validación y diagnóstico con los mismos contratos canónicos.

## Servicio público

- Aplicación: https://cornerscout-ten.vercel.app/
- Salud: https://cornerscout-ten.vercel.app/api/v1/health
- Datos listos: https://cornerscout-ten.vercel.app/api/v1/ready

`health` confirma el proceso. `ready` además abre el repositorio, verifica
contratos, hashes y linaje, y lee `matches_clean`. Para considerar disponible el
producto deben responder la aplicación y `ready`.

## Backend Docker local

La imagen ejecuta FastAPI con `CORNERSCOUT_DATA_DIR=/data`. Compose monta:

| Host | Contenedor | Acceso |
|---|---|---|
| `data/interim/02_clean` | `/data/interim/02_clean` | Solo lectura |
| `data/interim/03_scr15` | `/data/interim/03_scr15` | Solo lectura |
| `data/processed/04_features` | `/data/processed/04_features` | Solo lectura |
| `data/processed/05_modeling` | `/data/processed/05_modeling` | Solo lectura |
| `data/processed/runs` | `/data/processed/runs` | Lectura y escritura |

No monta raw ni artefactos históricos. La raíz del contenedor es de solo lectura
y `/tmp` es efímero.

```powershell
docker compose config --quiet
docker compose build backend
docker compose up -d --no-build backend
uv run --extra api python scripts/smoke_deployment.py --base-url http://127.0.0.1:8000 --origin http://localhost:4200
docker compose down
```

No arranques Uvicorn local y Docker simultáneamente en el puerto 8000. Para
diagnosticar un contenedor usa `docker compose logs backend`. Reconstruye la
imagen después de cambiar código o dependencias.

## Modos del reporte y agente

| Condición | Modo visible | Comportamiento |
|---|---|---|
| Clave y modelo disponibles; salida válida | `openai` | Redacción estructurada, verificada contra evidencia Python. |
| Clave ausente | `deterministic` | Respuesta reproducible con `missing_api_key`. |
| Error, timeout o salida inválida | `deterministic` | Fallback identificado; nunca presenta texto no validado como evidencia. |

El reporte limita la salida a 2.500 tokens y usa timeout de 20 segundos por
solicitud. El agente limita cada sesión a cuatro tools, cuatro turnos reales,
45 segundos y 12.000 tokens. Los costes se consultan en el panel de OpenAI.

## Lista operativa

Después de modificar el producto:

1. Ejecutar pruebas Python y typecheck/build Angular.
2. Verificar documentación y contrato OpenAPI si cambió una ruta pública.
3. Construir y ejecutar el smoke local si cambió backend, datos o dependencias.
4. Desplegar el commit en Vercel.
5. Comprobar aplicación, health, ready, sesión, seis secciones y modo del asistente.
6. Publicar datos con una versión nueva si cambió un artefacto canónico.

No publiques `.env`, claves, URLs privadas, raw ni ZIP locales fuera del asset
canónico versionado para Vercel.
