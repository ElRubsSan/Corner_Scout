# Frontend · Angular standalone

CornerScout presenta seis secciones: Resumen, Mapa, Patrones, Reporte, Calidad
y Asistente. Usa Tailwind, cancha SVG y cliente tipado OpenAPI. Los datos
corresponden a LaLiga 2015/16; las fotos pueden ser de otros años.

## Requisitos y arranque

Instala Node **24.15 o superior, dentro de la versión 24**, que incluye npm.
La guía completa de instalación y preparación de backend está en el
[README principal](../README.md).

Desde la raíz del repositorio:

```powershell
npm --prefix frontend ci
npm --prefix frontend start
```

`ci` instala el lockfile. `start` publica http://127.0.0.1:4200. Mantén FastAPI
activo en el puerto 8000 en otra terminal; el proxy local reenvía `/api`.
Detén Angular con Ctrl+C.

## Configuración pública

`public/config.json` contiene únicamente `apiBaseUrl`. Vacío significa usar
rutas relativas: en desarrollo las resuelve el proxy y en Vercel las rewrites
del dominio compartido.
`npm run build` genera ese archivo mediante `scripts/build-config.mjs`.
Para un backend remoto, desde la raíz:

```powershell
$env:CORNERSCOUT_API_BASE_URL = "https://backend.example.org"
npm --prefix frontend run build
```

Sustituye el dominio de ejemplo por el origen real, sin `/api/v1`, credenciales,
query ni fragmentos. Las URLs remotas requieren HTTPS. El backend debe permitir
el origen del frontend en `CORNERSCOUT_ORIGINS`. Esta configuración corresponde
a un frontend separado. Publicar una build local sin URL ni proxy requiere un servidor que
resuelva `/api` hacia FastAPI.

`OPENAI_API_KEY`, `OPENAI_MODEL` y prompts no pertenecen al navegador. Los
cálculos científicos, el proveedor y las herramientas viven en Python.

## Comprobar el frontend

```powershell
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend exec playwright install chromium
npm --prefix frontend run e2e
```

El build genera `frontend/dist/cornerscout/browser`. Los E2E necesitan las
dependencias Python y datos canónicos; arrancan FastAPI en 8001 y Angular en
4201. Usan Chromium y deshabilitan la clave OpenAI en el backend de prueba.
No hace falta arrancar esos dos servicios manualmente.
Las cifras verificadas se registran en [validación](../docs/validation.md).

Después de los E2E, puedes publicar las dos capturas del README desde la raíz:

```powershell
node frontend/scripts/publish-doc-screenshots.mjs
```

Este comando copia las capturas del análisis histórico de prueba a
`docs/images`; no consulta al proveedor ni crea datos sintéticos de producto.

## Cliente y recursos

Para regenerar el cliente HTTP desde la raíz:

```powershell
uv run --extra api python scripts/export_openapi.py
npm --prefix tools/codegen ci
npm --prefix frontend run generate:api
```

`core/api.generated.ts` se genera; las adaptaciones de UI están en los otros
archivos de `core/`. `tools/codegen` aísla TypeScript del generador.

Los 20 escudos y 202 retratos ya están en `public/media`: no se descargan
durante el build. Ver [imágenes y fuentes](../docs/visual-assets.md). La página
de Créditos muestra sus atribuciones. El tema claro/oscuro usa `localStorage`.

La cancha representa coordenadas StatsBomb 120 × 80. Izquierda/derecha se leen
desde el atacante mirando a portería. Un destino es llegada del pase, no
posición de remate. Estas etiquetas no modifican el contrato HTTP.

La vista «Mapa de calor» suaviza visualmente los conteos por cuadrícula con
manchas lima–amarillo–naranja–rojo. La escala es relativa al máximo de los
filtros actuales: no representa una nueva estimación de densidad. Al señalar
una cuadrícula ocupada se consulta su conteo exacto. Las líneas se dibujan
encima del calor y este queda recortado al campo. Las cuadrículas sin pases
no generan manchas.

Debajo del mapa, el total y la escala se separan de los destinos con barras
ordenadas por frecuencia. Las barras usan como denominador los envíos
representados; las exclusiones se muestran en otro bloque y la explicación
de colores es desplegable. Las etiquetas principales de tiro usan lenguaje
natural; «¿Cómo se cuenta el tiro tras el córner?» conserva la definición
completa y el nombre metodológico SCR-15. El reporte propone revisar en vídeo
la zona observada en lugar de una pregunta genérica de preparación.

## Vercel

Para frontend y backend juntos, usar [la guía Services](../docs/vercel.md)
y raíz del proyecto `./`. `CORNERSCOUT_SAME_ORIGIN=1` permite rutas relativas
en build. La sesión firmada se conserva en la pestaña sin exponer secretos;
los demás navegadores necesitan crear su propio análisis.

La aplicación está publicada en
[cornerscout-ten.vercel.app](https://cornerscout-ten.vercel.app/). Para frontend
separado se usa Root Directory `frontend`; la configuración recomendada y la
ruta Docker están en [la guía de despliegue](../docs/deployment.md).
