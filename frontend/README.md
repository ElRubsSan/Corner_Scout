# Frontend

Angular standalone 22 con Tailwind, cancha SVG interactiva y cliente tipado desde OpenAPI. Inicio: `npm ci`, `npm start`. Validacion: `npm run build`, `npm run typecheck`, `npm run e2e` (requiere datos reales y Playwright Chromium).

Vercel obligatorio, configurado sin desplegar. apiBaseUrl publico en public/config.json; nunca incluir claves Gemini. Generacion OpenAPI aislada en tools/codegen por diferencia TypeScript 5/6. Ver docs/deployment.md.
