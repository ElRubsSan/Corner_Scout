# Configuracion de despliegue (sin despliegue externo)

## Frontend obligatorio: Vercel

Proyecto Angular standalone 22.1.6; CLI/build 22.1.8; TypeScript 6.0.3; Node 24.19.0 verificados localmente. Configurar Root Directory `frontend`, instalar con `npm ci`, compilar con `npm run build`. `frontend/vercel.json` publica `dist/cornerscout/browser` y enruta la SPA. El build no necesita acceso a raw ni claves.

Antes de publicar, configurar `frontend/public/config.json` con `apiBaseUrl` igual al origen HTTPS real de FastAPI (sin /api/v1 al final). Es configuracion publica, nunca un secreto. Con valor vacio se usa mismo origen; en desarrollo Angular proxy reenvia /api al backend local. No existe aun URL de backend de produccion. La regla de Vercel excluye /api para evitar devolver index.html como si fuera JSON de API.

En el backend configurar CORNERSCOUT_ORIGINS con los origenes exactos de Vercel autorizados. Nunca agregar GEMINI_API_KEY al frontend ni a las variables publicas de Vercel.

## Backend compatible

Dockerfile proporciona FastAPI con uv.lock y Python 3.13. Es apto para un servicio de contenedores con volumen persistente y HTTPS, por ejemplo un servicio Docker en Render. Seleccion y aprovisionamiento del proveedor quedan manuales; no se ha creado ningun recurso externo.

Montar en `/data/processed` los archivos `matches.parquet`, `corners.parquet`, `clusters.parquet`, `quality.json` y `model-evaluation.json`. Permitir escritura en `processed/runs` para persistencia de analisis. El servidor no necesita raw, features.parquet ni modelos joblib; sirve el baseline aprobado y asignaciones de clusters precomputadas. No generar datos durante cada solicitud ni descargar al arrancar la API.

Prueba de contenedor local (requiere Docker instalado): `docker compose config --quiet`, `docker compose build`, `docker compose up`. Angular se inicia por separado con `npm start` dentro de frontend. El contenedor no incluye datasets ni secretos en la imagen.

## Reproducibilidad de frontend

`tools/codegen` aisla openapi-typescript 7 (peer TypeScript 5) de Angular 22 (TypeScript 6). Regenerar desde la raiz con `uv run --extra api python scripts/export_openapi.py`; despues `npm --prefix tools/codegen ci` y `npm --prefix tools/codegen run generate`. Se versiona la salida api.generated.ts, por lo que Vercel no necesita Python ni codegen.

## Fuentes oficiales consultadas

- https://angular.dev/reference/versions
- https://vercel.com/docs/project-configuration
- https://openapi-ts.dev/introduction
- https://openapi-ts.dev/openapi-fetch/
- https://tailwindcss.com/docs/installation/framework-guides/angular
- https://docs.astral.sh/uv/guides/integration/docker/

La verificacion local de Angular y navegador no equivale a una validacion del contenedor ni de Vercel. Registrar estos resultados por separado.
