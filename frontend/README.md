# Frontend

Angular standalone con Tailwind, cancha SVG interactiva y cliente tipado desde OpenAPI. Solo presenta resultados historicos de LaLiga 2015/16.

```powershell
npm --prefix frontend ci
npm --prefix frontend start
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run e2e
```

La verificacion registrada incluye typecheck/build y 2 E2E. Vercel esta configurado, pero no desplegado.

`public/config.json` contiene un `apiBaseUrl` publico; nunca debe contener `OPENAI_API_KEY`, `OPENAI_MODEL`, prompts o credenciales. OpenAI, el fallback determinista y las tres tools read-only (`obtener_historial`, `obtener_perfil_corners`, `consultar_evidencia`) pertenecen exclusivamente a FastAPI. Angular no llama al proveedor ni calcula SCR-15, clusters o probabilidades.

FastAPI sirve solo contratos y artefactos canonicos `02`-`05`. La generacion OpenAPI se mantiene en `tools/codegen`; ver `docs/architecture.md` y `docs/deployment.md`.
