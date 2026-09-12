# Backend

FastAPI con contratos Pydantic/OpenAPI, consultas DuckDB a Parquet, runs persistidos y reporte Gemini con fallback. Inicio desde la raiz: `uv run --extra api --extra llm uvicorn backend.main:app --host 127.0.0.1 --port 8000`.

Swagger: /docs. Requiere datos procesados por ingest/build/train. No lee raw ni llama al proveedor de datos por solicitud. Claves Gemini solo en variables de entorno del backend.
