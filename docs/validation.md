# Validación del producto

Esta guía distingue comprobaciones reproducibles, servicio público y pruebas que
pueden consumir OpenAI. Los resultados históricos del dominio no sustituyen una
nueva ejecución de los comandos.

## Estado público

Aplicación: [cornerscout-ten.vercel.app](https://cornerscout-ten.vercel.app/)

Se comprobó directamente que la aplicación responde, `/api/v1/health` devuelve
`status: ok` y `/api/v1/ready` devuelve `status: ready`. El propietario comprobó
en navegador el recorrido completo, persistencia de sesión y funcionamiento del
reporte y agente con OpenAI.

## Verificación local reproducible

Desde la raíz, con datos canónicos restaurados:

```powershell
uv sync --locked --all-extras
uv run --all-extras pytest -q -rs
uv run --extra api python scripts/check_visual_coverage.py --require-complete
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend exec playwright install chromium
npm --prefix frontend run e2e
uv run python scripts/check_documentation.py
docker compose config --quiet
```

Los E2E arrancan FastAPI en 8001 y Angular en 4201, usan Chromium y deshabilitan
OpenAI. Las integraciones pesadas del pipeline requieren sus variables explícitas
y regeneran datos; no forman parte de una comprobación ordinaria del producto.

## Cobertura verificada

- Contratos, hashes, linaje y rechazo de artefactos alterados.
- Regla SCR-15 y sus cierres, incluido el límite exacto de 15 segundos.
- Ventanas de ocho partidos estrictamente anteriores.
- API, sesiones persistidas y sesiones firmadas stateless.
- Resumen, mapa, calor, patrones, calidad, reporte y agente.
- Fallback determinista, Structured Outputs, citas, cifras y reparación final.
- Equivalencia de evidencia sin pandas en runtime para Barcelona, Real Madrid y
  Atlético Madrid en dos fechas históricas.
- Inventario de 20 escudos y 202 retratos de cobradores.
- Typecheck, build Angular, navegación móvil, tema y recursos estáticos.

## Smoke HTTP

Local determinista:

```powershell
uv run --extra api python scripts/smoke_deployment.py --base-url http://127.0.0.1:8000 --assistant-mode deterministic
```

Público sin invocar el proveedor:

```powershell
uv run --extra api python scripts/smoke_deployment.py --base-url https://cornerscout-ten.vercel.app
```

Añadir `--assistant-mode openai` exige respuestas reales del proveedor y consume
tokens. Debe ejecutarse solo de forma deliberada. El smoke transporta el contexto
firmado entre solicitudes cuando el backend usa sesiones stateless.
