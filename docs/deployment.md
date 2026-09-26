# Configuracion de despliegue

No se ha desplegado CornerScout ni validado Docker con un motor real. Esta guia describe la topologia requerida, no una validacion completada.

## Frontend Vercel

Configurar Root Directory `frontend`, instalar con `npm ci` y compilar con `npm run build`. `frontend/vercel.json` publica `dist/cornerscout/browser` y enruta la SPA.

Definir `frontend/public/config.json` con `apiBaseUrl` igual al origen HTTPS de FastAPI, sin `/api/v1`. Es configuracion publica, no un secreto. En backend, `CORNERSCOUT_ORIGINS` debe contener solo los origenes Vercel autorizados.

Nunca configurar `OPENAI_API_KEY`, `OPENAI_MODEL` ni prompts como variables del frontend. OpenAI se invoca exclusivamente desde FastAPI.

## Backend Docker

La imagen ejecuta FastAPI con `CORNERSCOUT_DATA_DIR=/data`. El servicio debe montar exactamente las capas canonicas que consume la API:

| Host | Contenedor | Acceso |
|---|---|---|
| `data/interim/02_clean` | `/data/interim/02_clean` | solo lectura |
| `data/interim/03_scr15` | `/data/interim/03_scr15` | solo lectura |
| `data/processed/04_features` | `/data/processed/04_features` | solo lectura |
| `data/processed/05_modeling` | `/data/processed/05_modeling` | solo lectura |
| `data/processed/runs` | `/data/processed/runs` | lectura/escritura |

No montar `data/raw`, artefactos demo antiguos ni un directorio `processed` ambiguo. FastAPI necesita los contratos y todos los artefactos declarados con sus hashes; no genera datos ni entrena al arrancar.

Ejemplo de opciones de volumen para adaptar al proveedor:

```text
--mount type=bind,src=<repo>/data/interim/02_clean,dst=/data/interim/02_clean,readonly
--mount type=bind,src=<repo>/data/interim/03_scr15,dst=/data/interim/03_scr15,readonly
--mount type=bind,src=<repo>/data/processed/04_features,dst=/data/processed/04_features,readonly
--mount type=bind,src=<repo>/data/processed/05_modeling,dst=/data/processed/05_modeling,readonly
--mount type=bind,src=<repo>/data/processed/runs,dst=/data/processed/runs
```

Configurar en el backend `OPENAI_API_KEY` y `OPENAI_MODEL` solo si se hara una prueba real. Sin clave, reporte y agente conservan el fallback determinista. No registrar secretos en imagenes, logs o archivos versionados.

## Validacion pendiente

Cuando exista motor Docker, comprobar configuracion, build, health, lectura de contratos `02`-`05`, creacion de un run y escritura exclusiva en `runs`. Despues validar CORS y HTTPS contra el dominio Vercel. No afirmar que Docker, OpenAI real o Vercel funcionan hasta registrar esas pruebas.

## Reproducibilidad del cliente

Regenerar OpenAPI desde la raiz con `uv run --extra api python scripts/export_openapi.py`, `npm --prefix tools/codegen ci` y `npm --prefix tools/codegen run generate`. La salida tipada se versiona; Vercel no necesita Python ni codegen.
