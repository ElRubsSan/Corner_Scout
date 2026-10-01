# Fuentes tecnicas oficiales

Las versiones instaladas se consultan en `uv.lock` y `frontend/package-lock.json`; no deben inferirse de memoria.

- StatsBomb Open Data: https://github.com/statsbomb/open-data
- OpenAI Python SDK: https://github.com/openai/openai-python
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- OpenAI function calling: https://platform.openai.com/docs/guides/function-calling
- Pydantic: https://docs.pydantic.dev/latest/concepts/models/
- FastAPI response models: https://fastapi.tiangolo.com/tutorial/response-model/
- DuckDB Python: https://duckdb.org/docs/current/clients/python/overview.html
- pandas Parquet: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_parquet.html
- scikit-learn model selection: https://scikit-learn.org/stable/modules/cross_validation.html
- uv y Docker: https://docs.astral.sh/uv/guides/projects/ y https://docs.astral.sh/uv/guides/integration/docker/
- nbclient (solo entrega académica): https://nbclient.readthedocs.io/en/latest/client.html
- Angular: https://angular.dev/reference/versions
- Tailwind para Angular: https://tailwindcss.com/docs/installation/framework-guides/angular
- OpenAPI TypeScript y openapi-fetch: https://openapi-ts.dev/introduction y https://openapi-ts.dev/openapi-fetch/
- Vercel: https://vercel.com/docs/project-configuration
- Playwright web server: https://playwright.dev/docs/test-webserver

Docker y las llamadas reales de reporte/agente se validaron localmente; los
registros están en [despliegue](deployment.md). La nueva verificación del producto
se registra en [validación](validation.md). Backend público, Vercel y pruebas
HTTPS/CORS contra dominios públicos siguen pendientes.

Referencia de organización del README:
[Inver-AI del profesor](https://github.com/FernandoBRdgz/inverai-claude).
Su configuración de servicios no se adopta automáticamente: CornerScout
necesita servir artefactos locales verificados y persistir runs.
