# Validación local

Las verificaciones de esta fase se ejecutan sobre el producto depurado y los
artefactos locales existentes. No se reentrena ni se vuelve a ejecutar el
notebook. No se hacen llamadas reales a OpenAI durante la limpieza.

## Registro anterior

El registro previo documentó 124 pruebas Python aprobadas y dos omitidas,
Angular typecheck/build y cuatro E2E. Docker y llamadas reales locales están
registrados en [deployment.md](deployment.md). Son antecedentes separados
del nuevo registro de esta fase.

## Verificación de entrega académica

Se validó el formato notebook, la integridad ZIP y la igualdad de las 104
celdas de código antes/después de añadir 14 celdas Markdown. La copia final
está dentro de `artifacts/entrega-academica.zip`; su `verification.json`
registra hashes y conservación. No hay outputs de tipo error guardados.

## Comandos del producto

Desde la raíz:

```powershell
uv sync --locked --all-extras
uv run --all-extras pytest -q -rs
uv run --extra api python scripts/check_visual_coverage.py --require-complete
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend exec playwright install chromium
npm --prefix frontend run e2e
node frontend/scripts/publish-doc-screenshots.mjs
uv run python scripts/check_documentation.py
docker compose config --quiet
```

Los E2E arrancan sus servicios en 8001/4201 y deshabilitan OpenAI. El smoke
HTTP opcional crea solo un scouting run en `processed/runs`.

## Resultado de esta fase · 2026-09-30

| Verificación ejecutada | Resultado |
|---|---|
| `uv lock` y `uv sync --locked --all-extras` | Lock actualizado sin dependencias Jupyter; instalación correcta. |
| `uv run --all-extras pytest -q -rs` | **124 passed, 2 skipped**, 2 avisos de dependencias. |
| Cobertura visual `--require-complete` | **20/20 escudos, 202/202 cobradores**, 539 identidades. |
| Angular typecheck | Aprobado, también después de regenerar el cliente. |
| Angular build | Aprobado; salida `frontend/dist/cornerscout/browser`. |
| Instalación Chromium y E2E | **4 passed**: recorrido táctico, historial insuficiente, móvil/tema/errores y recursos. |
| Capturas del README | Resumen y mapa generados a partir del E2E real histórico. |
| OpenAPI | Igualdad del JSON versionado con `app.openapi()`; cliente regenerado. |
| Codegen `npm ci`, audit y generación | Instalación/generación correctas; corregido `brace-expansion` 2.1.4 → 2.1.7; audit final sin vulnerabilidades en ese paquete de herramientas. |
| Enlaces Markdown locales | Comprobación automática aprobada; incluye imágenes y enlaces entre guías. |
| `git diff --check` | Sin errores de whitespace. |
| `docker compose config --quiet` y build backend | Aprobados con Docker Engine 29.7.2. |
| Smoke de imagen nueva | Ready, run, seis secciones, fallback y CORS aprobados en puerto 8002. |

### Omisiones justificadas

- `tests/test_full_regression.py`: exige `CORNERSCOUT_RUN_FULL_PIPELINE=1`
  y vuelve a ejecutar raw → 05. No se regeneraron etapas canónicas para esta
  limpieza documental y de empaquetado.
- `tests/test_modeling.py`: exige `CORNERSCOUT_RUN_LOCAL_MODELING=1` para la
  integración local de etapa 04/modelado. No hubo cambios científicos que
  requirieran ese reentrenamiento.
- No se volvió a ejecutar el notebook ni se hicieron llamadas reales OpenAI.
  La nueva prueba HTTP usó clave vacía, fallback `missing_api_key` y cero tokens.
- Vercel, dominio público, HTTPS y CORS público no se ejecutaron.

### Incidencias resueltas y avisos conservados

La primera invocación directa de pytest no encontraba el paquete `scripts`;
se añadió `pythonpath = ["."]` a su configuración y la suite completa pasó.
Dos avisos de Starlette permanecen: deprecación de httpx en TestClient y del
alias `anyio.abc.BlockingPortal`. No se ocultaron ni se modificó la selección
de dependencias runtime para resolverlos en esta fase.

Los primeros intentos E2E y build Docker excedieron el timeout de la herramienta;
se repitieron con límites suficientes y terminaron correctamente. El primer
preflight de smoke rechazó el origen de prueba heredando la configuración
local; se repitió con `CORNERSCOUT_ORIGINS=http://127.0.0.1:4200` explícito.
La prueba final valida ese origen configurado, no todos los orígenes posibles.

El contenedor temporal `cornerscout-predeploy-check` usó los montajes canónicos
de Compose, puerto 8002 y variables explícitas sin proveedor. Se eliminó al
terminar. El backend ya activo en 8000 se conservó. El smoke y E2E pueden
crear sus runs en `processed/runs`; raw y las etapas `01`–`05` no se rehicieron.

Esta verificación usa la instalación y los datos locales existentes: no se
presenta como una prueba de clonación limpia ni de despliegue externo.

## Cambio visual: mapa de calor · 2026-09-30

Se sustituyeron los bloques por manchas SVG suavizadas, recortadas al campo,
con escala lima–amarillo–naranja–rojo y líneas por encima. La interfaz utiliza
«Mapa de calor» y una leyenda relativa a los filtros. Las cuadrículas
transparentes conservan el conteo exacto; no cambia el cálculo del backend.

- `npm run typecheck`: aprobado.
- `npm run build`: aprobado.
- `npm run e2e`: **4 passed**. Se añadieron comprobaciones de correspondencia
  entre celdas y conteos, orden de las líneas, leyenda y ausencia de manchas
  en muestra vacía. El recorrido móvil conserva errores/reintento y tema oscuro.
- `node scripts/publish-doc-screenshots.mjs`: capturas de README actualizadas.

La primera compilación detectó accesos a colores posiblemente ausentes bajo
tipado estricto; se corrigió la interpolación con tuplas y valores de respaldo.
Los E2E detectaron selectores de texto ambiguos por los nuevos títulos SVG;
se acotaron a la leyenda y la corrida final pasó. No se repitieron Python ni
Docker: este cambio solo afecta representación Angular, estilos y pruebas UI.

## Claridad del mapa y del indicador de tiro · 2026-09-30

Se separaron total/escala, destinos con barras, exclusiones y explicación
desplegable. Los destinos se ordenan por conteo y sus barras usan los envíos
representados, no el máximo por cuadrícula. «Posición inválida» corresponde
a córners filtrados, no exclusivamente a envíos directos. El reporte propone
revisión en vídeo solo cuando hay una zona identificada.

Las etiquetas principales explican tiro tras el córner; un componente común
mantiene la definición completa de SCR-15 en desplegables. La presentación
traduce la sigla en respuestas de reporte/agente sin alterar contratos.
El respaldo del agente admite «tiro» y «tiros» además del término técnico,
seleccionando la misma evidencia `E_SCR15`.

Verificación: typecheck/build aprobados, cuatro E2E aprobados y 45 pruebas de
agente/herramientas aprobadas. Los E2E comprueban orden y denominador de barras,
exclusiones, ayuda metodológica y respuesta a la pregunta sin siglas. Capturas
del README actualizadas. No se modificaron cálculos ni se reentrenó.

## Ayuda visual de tiro tras el córner · 2026-09-30

El desplegable compartido presenta tres pasos con iconos, cierres y detalles
en tarjetas y una nota técnica SCR-15. Mantiene ventana inclusiva, primer
cierre y exclusión de desconocidos. Se adapta a móvil y ambos temas.
Typecheck y build aprobados; **4 E2E aprobados**, incluyendo apertura/cierre
con Enter y comprobación móvil en tema oscuro sin desbordamiento horizontal.
No hay cambios de cálculo ni de backend.
