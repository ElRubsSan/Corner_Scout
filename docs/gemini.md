# Reporte Gemini

Integracion obligatoria implementada exclusivamente en FastAPI. SDK oficial google-genai (<3), generate_content y response_json_schema construido desde Narrative.model_json_schema(). Entrada ReportInput y salida Narrative validadas por Pydantic. Modelo configurable con GEMINI_MODEL; valor inicial gemini-2.5-flash documentado en SDK oficial. Verificar disponibilidad en la cuenta antes de demo.

Instalar `uv sync --extra api --extra llm`. Establecer GEMINI_API_KEY en el entorno del proceso backend, nunca en Angular. `.env.example` es una plantilla; el servidor no carga .env automaticamente. La clave no se necesita para usar el fallback ni para pruebas con mocks tipados.

El LLM recibe rival, corte, ocho partidos, SCR-15, xG por corner evaluable, patrones, probabilidad baseline claramente etiquetada, evidencia y limitaciones. No recibe raw, SQL ni credenciales dentro del prompt. No tiene herramientas de calculo, busqueda o entrenamiento.

Timeout HTTP 20 segundos; falta de clave, fallo de proveedor/cuota, JSON invalido, referencias inexistentes o cifras no respaldadas devuelven plantilla determinista. No se filtran mensajes SDK al cliente. El modo y motivo de fallback se muestran explicitamente.

Validacion de evidencia comprueba referencias y cifras literales. No equivale a una prueba automatica de veracidad semantica de todo texto libre: revisar recomendaciones antes de uso profesional. Las limitaciones originales se adjuntan siempre sin depender de la redaccion del LLM.

Validado con mocks tipados (respuesta correcta, clave ausente, cuota, timeout, JSON invalido, cifras y referencias inventadas). Llamada real y cuota dependen de configuracion manual de una clave; no se afirma prueba real de Gemini.

Fuente oficial consultada: https://github.com/googleapis/python-genai (README, JSON Response Schema y HttpOptions). ai.google.dev no fue accesible desde la herramienta en esta sesion.
