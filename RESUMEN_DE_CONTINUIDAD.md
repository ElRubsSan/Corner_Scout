# Continuidad de CornerScout

El producto usa FastAPI, Angular y el pipeline Python canónico. Para instalar
herramientas, dependencias, datos, `.env` y ambos servicios, seguir `README.md`.
Las guías están indexadas en `docs/README.md`.

## Cierre previo al despliegue

La entrega está en `artifacts/entrega-academica.zip` local, fuera de Git. Contiene
el ejecutado con 14 comentarios nuevos y las 104 celdas de código intactas,
fuentes y scripts. Los notebooks se retiraron del repositorio de producto.
Se retiraron también plantillas antiguas, evaluación `v0.3` y el inspector de
eventos obsoleto; las dependencias Jupyter ya no pertenecen al extra de producto.
El detalle de decisiones está en `docs/predeploy.md`.

Los cambios de UI, backend, contrato y recursos visuales de la sesión previa
se conservaron. Los resultados de comprobaciones de esta fase se registran en
`docs/validation.md`, incluidos los motivos de pruebas omitidas. No hay commits
ni publicación pública de esta fase.

Nueva corrida 2026-09-30: 124 pruebas Python aprobadas, dos integraciones
pesadas omitidas, cuatro E2E, typecheck/build, cobertura visual completa,
OpenAPI y smoke Docker de la imagen nueva sin proveedor aprobados. Dos avisos
de deprecación de Starlette se conservan y están documentados.

## Datos y límites

380 partidos, 1.295.354 eventos, 3.841 córners, 3.835 evaluables, seis excluidos,
1.245 con tiro. Imágenes: 20 escudos y 202 cobradores. No son datos actuales.
Decisiones y límites en `docs/model-card.md`; SCR-15 en
`docs/scr15-methodology.md`. Raw y las etapas locales no se regeneraron para
esta limpieza. Las 40 etiquetas humanas se preservan.

## Próxima fase

Elegir alojamiento backend con artefactos persistentes, publicar HTTPS y luego
conectar Vercel, CORS y recorridos públicos; seguir `docs/deployment.md`.
Docker y llamadas reales de OpenAI se validaron localmente en el registro previo.
No publicar secretos, raw, modelos ni ZIP pesados. No hacer commit, push o
despliegue sin autorización explícita.
