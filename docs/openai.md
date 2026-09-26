# OpenAI en FastAPI

## Alcance

OpenAI esta integrado exclusivamente en FastAPI mediante el SDK oficial, Responses API, Structured Outputs y modelos Pydantic. Se usa para redactar el reporte tactico y responder mediante un agente acotado; Python conserva todos los calculos, selecciones, referencias y decisiones.

Configurar `OPENAI_API_KEY` y, opcionalmente, `OPENAI_MODEL` solo en el entorno del backend. El modelo predeterminado implementado es `gpt-4.1-mini`. `.env.example` es una plantilla y no debe contener secretos. Angular y Vercel frontend nunca reciben la clave.

```powershell
uv sync --extra api --extra llm
$env:OPENAI_API_KEY="..."
$env:OPENAI_MODEL="gpt-4.1-mini"
uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

No se ha ejecutado una llamada real con una clave OpenAI; la cobertura actual usa mocks y fallback.

## Reporte

FastAPI construye una entrada validada con rival, corte, ocho partidos, SCR-15, xG descriptivo, patrones, evidencia y limitaciones. OpenAI solo redacta sobre esa entrada. La salida estructurada se valida con Pydantic y se rechazan referencias desconocidas, cifras no respaldadas y lenguaje determinista no sustentado.

La falta de clave produce `missing_api_key`; una salida invalida produce `invalid_output`; un fallo del proveedor produce `provider_unavailable`. En todos esos casos se entrega una plantilla determinista y el modo de fallback queda visible. El timeout del cliente es de 20 segundos y no se filtran errores internos al frontend.

## Agente y tools

El agente dispone exactamente de tres tools registradas, estrictamente tipadas y de solo lectura:

- `obtener_historial`: devuelve los ocho `match_id` previos de la sesion.
- `obtener_perfil_corners`: devuelve indicadores, limitaciones y resultados de modelos promovidos.
- `consultar_evidencia`: devuelve el detalle de `evidence_ids` existentes.

Rival y fecha de corte quedan bloqueados a la sesion. No hay tool de SQL, escritura, archivos, web, raw, entrenamiento ni calculo libre. Se validan argumentos, citas y cifras; se aplican presupuestos de llamadas, tiempo, tokens y turnos. Preguntas fuera de alcance y fallos del proveedor usan respuesta determinista.

## Limites

Validar IDs y cifras no demuestra la correccion semantica completa de texto libre. Las recomendaciones requieren revision humana y siempre conservan las limitaciones: datos historicos de LaLiga 2015/16, ocho partidos, sin video, tracking ni datos actuales.

Fuentes oficiales: https://platform.openai.com/docs/guides/structured-outputs, https://platform.openai.com/docs/guides/function-calling y https://github.com/openai/openai-python.
