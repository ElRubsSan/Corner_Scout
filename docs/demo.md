# Demo en vivo - cinco minutos

## Preparacion

Instalar dependencias y generar o restaurar previamente las etapas canónicas
`01`–`05` siguiendo el [README](../README.md). Desde la raíz, en dos terminales:

```powershell
uv run --all-extras uvicorn backend.main:app --env-file .env --host 127.0.0.1 --port 8000
```

```powershell
npm --prefix frontend start
```

Si no hay `.env`, omitir `--env-file .env`. Comprobar
http://127.0.0.1:8000/api/v1/ready y abrir http://127.0.0.1:4200.
No descargar ni entrenar durante la presentación.

`OPENAI_API_KEY` y `OPENAI_MODEL`, si se usan, solo existen en FastAPI.
Las llamadas reales locales sí se validaron; ver [registro](deployment.md).
La demo también funciona sin clave mediante fallback determinista visible.
Identificar el modo realmente mostrado y no atribuir al proveedor una plantilla.

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

Al terminar, detener ambos procesos con Ctrl+C. La demostración local no es un
despliegue público; Vercel sigue pendiente.
