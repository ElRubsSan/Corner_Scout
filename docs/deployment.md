# Configuracion de despliegue

Docker se validó localmente con un motor real y artefactos canónicos verificados.
El primer build de Vercel falló por tamaño (470,03 MB, límite aplicado 225 MB).
El runtime ligero y ZIP canónico empaquetado ya se comprobaron localmente;
queda pendiente aprobar el nuevo build y la validación pública.

## Frontend Vercel

**Ruta preferida gratuita:** frontend y backend juntos mediante el
`vercel.json` de la raíz. Seguir [Vercel Services](vercel.md), con raíz `./`,
sesiones firmadas y `CORNERSCOUT_SAME_ORIGIN=1`. Los pasos siguientes de raíz
`frontend` y URL externa corresponden a la alternativa de frontend separado.

Configurar Root Directory `frontend`, instalar con `npm ci` y compilar con `npm run build`. `frontend/vercel.json` publica `dist/cornerscout/browser` y enruta la SPA.

Definir en las variables de entorno de **build de Vercel** `CORNERSCOUT_API_BASE_URL=https://<origen-publico-del-backend>` (sin `/api/v1`). `npm run build` genera `public/config.json` con ese origen; rechaza una build de Vercel sin esta variable. La URL es pública y no contiene claves. En local, sin la variable, `apiBaseUrl` queda vacío y se usa el proxy de desarrollo. En backend, `CORNERSCOUT_ORIGINS` debe contener los orígenes Vercel autorizados, separados por comas; añadir tanto el dominio final como los dominios de preview que vayan a probarse. No añadir barras ni rutas a los orígenes.

Nunca configurar `OPENAI_API_KEY`, `OPENAI_MODEL` ni prompts como variables del frontend. OpenAI se invoca exclusivamente desde FastAPI.

## Backend Docker

Primero instala Docker Desktop, inicia su motor y prepara los datos con el
README o la guía de restauración. Desde la raíz puedes comprobar herramientas:

```powershell
docker version
docker compose version
```

La imagen ejecuta FastAPI con `CORNERSCOUT_DATA_DIR=/data`. El servicio debe montar exactamente las capas canonicas que consume la API. `docker-compose.yml` usa raíz del contenedor de solo lectura y `/tmp` efímero:

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

Configurar en el backend `OPENAI_API_KEY` y `OPENAI_MODEL` solo si se desea generación real. Sin clave, reporte y agente conservan el fallback determinista. Docker Compose lee variables del entorno y de `.env` local si existe; comprobar la configuración antes de probar el modo sin clave. Nunca exponer secretos en el frontend o en Git.

El puerto de Compose se publica solo en `127.0.0.1:8000`; esta configuración
es local, no un endpoint público. No arranques al mismo tiempo Uvicorn local
en ese puerto. No publiques la salida completa de `docker compose config`,
que puede resolver secretos; `--quiet` valida sin mostrarlos.

## Verificación reproducible

Desde la raíz, con los artefactos canónicos ya restaurados en `data/`:

```powershell
docker compose config --quiet
docker compose build backend
docker compose up -d --no-build backend
uv run --extra api python scripts/smoke_deployment.py --base-url http://127.0.0.1:8000 --origin http://localhost:4200
docker compose down
```

El script espera a `/api/v1/ready`, que comprueba contratos, hashes, linajes y lectura de `matches_clean`; crea un análisis histórico de ocho partidos y recorre los endpoints de las seis secciones. Escribe solo el run determinista en `data/processed/runs`. Opcionalmente, `--assistant-mode deterministic` exige fallback sin clave y `--assistant-mode openai` hace llamadas **reales** al proveedor: escoger explícitamente antes de ejecutar. El argumento `--origin` prueba CORS para un origen concreto.

Si el servicio no está listo, consulta `docker compose logs backend`. Para
volver a arrancar después de cambios del código, reconstruye la imagen.
`docker compose down` detiene el servicio sin borrar los datos montados.

**Registro local 2026-09-29:** Docker Engine 29.7.2, build y smoke de backend aprobados, raíz `read_only=true`, cuatro montajes canónicos con `RW=false` y solo `/data/processed/runs` con `RW=true`; preflight CORS local aprobado. Con clave configurada en Compose, reporte y agente devolvieron `openai` sin fallback; una consulta del agente consumió 1789 tokens de entrada y 167 de salida (1956 en total). En contenedor aparte sin clave, reporte y agente devolvieron `deterministic` con `missing_api_key` y 0 tokens. El agente limita cada sesión a cuatro tools, cuatro turnos reales, 45 segundos y 12000 tokens; el reporte limita la salida a 2500 tokens y usa timeout de 20 segundos por solicitud. **El coste facturado no se obtiene de estas respuestas**: consultarlo en el panel del proveedor para el modelo configurado. No se ha probado Vercel ni CORS/HTTPS contra un dominio público.

Tras publicar ambos servicios, repetir el smoke con `--base-url https://<origen-backend> --origin https://<origen-vercel>` y los recorridos de interfaz contra la URL Vercel. Mantener la indicación visible de que el caso es histórico (LaLiga 2015/16).

**Nueva comprobación local 2026-09-30:** imagen reconstruida con el lockfile
depurado y smoke aprobado en un contenedor temporal, puerto 8002, clave vacía
y origen `http://127.0.0.1:4200` explícito. Reporte y agente devolvieron
`deterministic`, `missing_api_key` y cero tokens del agente. El contenedor de
prueba se eliminó sin detener el servicio existente en 8000. Ver
[registro completo](validation.md).

## Reproducibilidad del cliente

Regenerar OpenAPI desde la raiz con `uv run --extra api python scripts/export_openapi.py`, `npm --prefix tools/codegen ci` y `npm --prefix tools/codegen run generate`. La salida tipada se versiona; Vercel no necesita Python ni codegen.

## Fase pública pendiente: orden de trabajo

1. Elegir un proveedor de backend que admita contenedores y datos persistentes.
   Dimensionar almacenamiento a partir de las cuatro etapas completas y la
   política de conservación de runs; no copiar solo la tabla de la interfaz.
2. Cargar artefactos y configurar los cinco montajes, variables backend,
   permisos y backups. Publicar FastAPI detrás de HTTPS.
3. Comprobar `/api/v1/health`, `/api/v1/ready` y smoke sobre ese dominio.
4. Importar el repositorio en Vercel con raíz `frontend`, `npm ci`,
   `npm run build` y salida `dist/cornerscout/browser`. Definir
   `CORNERSCOUT_API_BASE_URL` con el origen HTTPS real del backend.
5. Añadir el origen final del frontend a CORS backend y reiniciar el servicio.
   Para previews, autorizar solo los orígenes que se vayan a comprobar.
6. Verificar navegación directa de la SPA, imágenes, análisis, reporte,
   asistente y errores desde el dominio público. Ejecutar smoke con `--origin`.
7. Registrar URLs y resultados públicos, actualizar README y decidir la
   política operativa de conservación/limpieza de runs.

Estos pasos son preparación, no despliegues realizados. El registro local
actual está en [validation.md](validation.md); los pendientes de la fase están
en [predeploy.md](predeploy.md).
