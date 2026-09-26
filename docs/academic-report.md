# Estructura del documento academico final

La rubrica especifica no se ha proporcionado. Esta estructura cubre evidencia disponible sin afirmar cumplimiento no comprobado.

1. **Resumen y problema:** preparacion prepartido ante corners ofensivos; usuario analista/entrenador; caso historico LaLiga 2015/16.
2. **Objetivos:** ocho partidos estrictamente anteriores, SCR-15, destinos, amenaza descriptiva y separacion entre observacion y prediccion.
3. **Datos:** StatsBomb competicion 11/temporada 27, revision fijada, raw inmutable y contratos de hashes.
4. **Resultados de datos:** 380 partidos, 1,295,354 eventos, 3,841 corners, 3,835 evaluables, 6 excluidos y 1,245 con tiro.
5. **SCR-15:** inicio en corner y primer cierre entre limite de 15 segundos, cambio de `possession_team`, fin de periodo y nuevo corner; frontera inclusiva, auditoria de reanudaciones y desconocidos.
6. **Pipeline reproducible:** etapas `01_ingestion` a `07_herramientas_agente`; notebooks como evidencia y logica extraida a modulos Python.
7. **Variables y EDA:** ocho partidos previos, cortes exclusivos, contexto preevento, geometria y dependencia intrapartido.
8. **K-Means:** ajuste fijo con datos predesarrollo, uso descriptivo de destinos y exclusion total de predictores.
9. **Evaluacion temporal:** ventanas de desarrollo y confirmacion; bootstrap por partido; metricas probabilisticas y de conteo sin fuga temporal.
10. **Decisiones `05`:** `scr15=league_reference`, `short_direct=candidate`, `delivery_zone=not_modelled`, `corner_count=candidate`.
11. **Arquitectura:** contratos/Parquet/DuckDB, FastAPI/Pydantic/OpenAPI y Angular standalone; API solo sobre artefactos canonicos `02`-`05`.
12. **OpenAI:** llamada solo desde FastAPI, Structured Outputs, evidencia validada y fallback determinista; `OPENAI_API_KEY`/`OPENAI_MODEL` backend-only.
13. **Agente:** `obtener_historial`, `obtener_perfil_corners` y `consultar_evidencia`, todas read-only, tipadas y limitadas a la sesion.
14. **Pruebas:** Python `77 passed, 1 skipped`, Angular typecheck/build y 2 E2E como validacion registrada.
15. **Limitaciones:** temporada unica, muestra de ocho partidos, sin video/tracking/360, etiqueta corto/directo proxy, sin llamada real OpenAI, Docker o despliegue comprobados.
16. **Conclusiones:** utilidad descriptiva trazable sin exagerar prediccion ni actualidad.

## Matriz de evidencia

| Area | Evidencia | Pendiente |
|---|---|---|
| Datos y SCR-15 | notebooks `01`-`03`, contratos, `docs/data-audit.md` | Interpretacion academica final |
| Variables/modelos | notebooks `04`-`05`, contrato `05`, model card | Discusion de validez externa |
| Reporte | notebook `06`, `analytics/tactical_report.py`, `backend/openai.py` | Llamada real OpenAI, si se autoriza |
| Agente | notebook `07`, `analytics/agent_tools.py`, `backend/agent.py` | Evaluacion humana de respuestas |
| Full-stack | FastAPI, OpenAPI, Angular, E2E | Capturas finales |
| Despliegue | Dockerfile, configuracion Vercel, `docs/deployment.md` | Docker y recursos externos reales |
| Comunicacion | `docs/demo.md`, `docs/presentation.md` | Video, rubrica y logo StatsBomb |
