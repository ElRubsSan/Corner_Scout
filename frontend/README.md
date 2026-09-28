# Frontend

Angular standalone con Tailwind, cancha SVG interactiva y cliente tipado desde OpenAPI. Solo presenta resultados historicos de LaLiga 2015/16.

La interfaz ofrece modo claro/oscuro guardado en `localStorage`, navegacion por secciones y etiquetas futbolisticas para lados, tipos de ejecucion y zonas de destino. Estas etiquetas no cambian los valores del contrato OpenAPI ni los identificadores de evidencia. Izquierda/derecha se expresan desde la perspectiva del equipo atacante mirando hacia la porteria rival. Las zonas describen destinos del pase, no lugares de remate.

```powershell
npm --prefix frontend ci
npm --prefix frontend start
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run e2e
```

La verificacion registrada incluye typecheck/build y 3 E2E. Vercel esta configurado, pero no desplegado.

Los E2E levantan un backend aislado en `127.0.0.1:8001` y Angular en `127.0.0.1:4201` mediante `proxy.e2e.conf.json`; el desarrollo habitual conserva Docker en `8000` y Angular en `4200`.

`public/config.json` contiene un `apiBaseUrl` publico; nunca debe contener `OPENAI_API_KEY`, `OPENAI_MODEL`, prompts o credenciales. OpenAI, el fallback determinista y las tres tools read-only (`obtener_historial`, `obtener_perfil_corners`, `consultar_evidencia`) pertenecen exclusivamente a FastAPI. Angular no llama al proveedor ni calcula SCR-15, clusters o probabilidades.

Antes de la demostracion en Vercel, configurar el `apiBaseUrl` publico en el artefacto `config.json` desplegado, confirmar que el backend permite el origen publico del frontend y comprobar el recorrido completo desde ese origen. El valor vacio actual usa el proxy local de Angular y no conecta con un backend remoto por si solo. No incorporar claves ni rutas privadas a la configuracion publica.

FastAPI sirve solo contratos y artefactos canonicos `02`-`05`. La generacion OpenAPI se mantiene en `tools/codegen`; ver `docs/architecture.md` y `docs/deployment.md`.
