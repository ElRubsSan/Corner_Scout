# Demo en vivo - cinco minutos

## Preparacion

Generar previamente las etapas canonicas `01`-`05`. Levantar FastAPI con `uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000` y Angular con `npm --prefix frontend start`. Abrir http://127.0.0.1:4200. No descargar ni entrenar durante la presentacion.

`OPENAI_API_KEY` y `OPENAI_MODEL`, si se usan, solo pueden existir en FastAPI. La demo funciona sin clave mediante fallback determinista visible. Como no se ha realizado una llamada real a OpenAI, no presentar el modo OpenAI como validado.

## Recorrido

| Tiempo | Accion | Mensaje |
|---|---|---|
| 0:00-0:30 | Landing | CornerScout prepara defensa de corners ofensivos con datos historicos de LaLiga 2015/16, no datos actuales. |
| 0:30-1:10 | Barcelona, corte `2016-03-01` | Mostrar los ocho partidos estrictamente anteriores y confirmar la ventana. |
| 1:10-2:00 | Dashboard | Explicar 3,841 corners totales, 3,835 evaluables, 6 excluidos y 1,245 con tiro en el corpus; distinguirlos de la ventana elegida. |
| 2:00-2:40 | Mapa | El punto es destino del pase, no ubicacion de remate. Filtrar lado, cobrador y envio. |
| 2:40-3:20 | Patrones | K-Means fue fijado con datos predesarrollo y solo describe destinos; un cluster no prueba una jugada ensayada. |
| 3:20-4:10 | Reporte y agente | Mostrar plan, generar reporte e identificar OpenAI o fallback. Consultar una de las tres tools read-only y revisar sus `evidence_ids`. |
| 4:10-5:00 | Modelos y calidad | Mostrar decisiones: SCR `league_reference`, corto/directo y conteo `candidate`, zona `not_modelled`; cerrar con contratos, hashes y limites. |

SCR-15 termina por el primer cierre entre 15 segundos, cambio de `possession_team`, fin de periodo y nuevo corner. Un tiro exactamente en 15 segundos entra si no hubo cierre anterior; las reanudaciones distintas de un nuevo corner se auditan.

Si falta historial, elegir una fecha posterior. Si OpenAI no esta disponible, explicar el fallback sin atribuir una llamada al proveedor. Si falla la API o faltan contratos canonicos `02`-`05`, detener la demo; no sustituir datos reales con artefactos demo ni mocks de producto.
