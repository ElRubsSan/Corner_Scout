# Demo en vivo — cinco minutos

## Preparacion

Ejecutar pipeline y modelos antes de la demo. Levantar FastAPI con uv y Angular con npm start. Abrir http://127.0.0.1:4200. No descargar ni entrenar durante la presentacion. Confirmar que GEMINI_API_KEY, si se usa, solo esta en el backend; la demo tambien funciona sin clave mediante fallback visible.

## Recorrido

| Tiempo | Accion | Mensaje |
|---|---|---|
| 0:00–0:30 | Landing | CornerScout prepara defensa de corners ofensivos. Caso historico, no datos actuales. |
| 0:30–1:10 | Rival Barcelona, corte 2016-03-01 | Mostrar los ocho partidos reales y explicar corte exclusivo. Confirmar. |
| 1:10–2:00 | Dashboard | Leer valores en pantalla sin anticipar cifras. SCR-15: corners con tiro en 15 segundos bajo regla de posesion/periodo. Explicar denominador evaluable. |
| 2:00–2:40 | Mapa y filtro corto | Destino del pase, no ubicacion de remate; relacion con cobrador y lado. |
| 2:40–3:20 | Patrones | K-Means identifica agrupaciones recurrentes; no confirma jugadas ensayadas. Mostrar un evento de evidencia. |
| 3:20–4:10 | Reporte | Mostrar plan, generar, identificar Gemini o fallback. Cada observacion cita evidencia calculada. |
| 4:10–5:00 | Calidad y modelos | LR/RF no superaron consistentemente baseline. Mostrar limitaciones, fecha, hashes y atribucion StatsBomb. |

Si falta historial, mostrar el mensaje de datos insuficientes y elegir una fecha posterior. Si falla Gemini, explicar el respaldo sin inventar una respuesta del proveedor. Si la API no esta disponible, detener la demo y restaurar el servicio; no sustituir datos reales con mocks de producto.
