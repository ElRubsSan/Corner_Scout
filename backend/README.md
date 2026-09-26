# Backend

FastAPI con contratos Pydantic/OpenAPI, consultas DuckDB de solo lectura, runs persistidos y OpenAI con Structured Outputs y fallback determinista. Inicio desde la raiz: `uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000`.

Swagger: `/docs`. Requiere los contratos canonicos `02-clean-v2`, `03-scr15-v2`, `04-features-v2` y `05-modeling-v3-objectives` y sus artefactos con hashes validos. La API solo consume `matches_clean`, `corners_engineered`, `cluster_assignments`, `objective_winners` y `temporal_metrics`; no lee raw ni entrena.

`OPENAI_API_KEY` y opcionalmente `OPENAI_MODEL` existen solo en el backend. Sin clave, por fallo de proveedor o por salida invalida, reporte y agente usan fallback determinista. El agente expone exactamente las tres herramientas de solo lectura registradas en `analytics.agent_tools`, bloquea solicitudes fuera de alcance antes del proveedor y aplica presupuestos de llamadas, tiempo y tokens.
