# Estructura del documento academico final

La rubrica especifica no se ha proporcionado. Esta estructura cubre criterios habituales; el alineamiento exacto y ponderaciones deben completarse con la rubrica real, sin afirmar cumplimiento no comprobado.

1. **Resumen y problema:** preparacion prepartido ante corners ofensivos del rival; usuario analista/entrenador; alcance historico.
2. **Objetivos y preguntas:** ocho partidos previos, SCR-15, destinos y amenaza descriptiva; separacion entre observacion y prediccion.
3. **Datos y atribucion:** StatsBomb, competicion 11/temporada 27, revision, 380 partidos/20 equipos, exportacion Colab y raw inmutable.
4. **Auditoria:** calidad de IDs, cobertura, tiempos, coordenadas; 126 regresiones, seis secuencias no evaluables y un corner espacialmente invalido. Referir docs/data-audit.md y manifiestos.
5. **Metodologia SCR-15:** inicio, cierres, frontera inclusiva, reanudaciones y posesiones auditadas, denominador evaluable; ejemplos reales y pruebas de limites.
6. **EDA y variables:** cobradores, envios, zonas, historia previa; dependencia de corners de un mismo partido; limite espacial de eventos.
7. **Modelos:** baseline, LR, RF, K-Means, Gemini. Variables prohibidas y prevencion de fuga; funciones de cada familia.
8. **Evaluacion:** dos bloques temporales de validacion y holdout; AP, ROC-AUC, Brier, precision/recall/F1, calibracion, tamanos de muestra. Incluir model-evaluation.json y calibration.png. Justificar conservar baseline.
9. **Arquitectura full-stack:** Python/Parquet/DuckDB, FastAPI/Pydantic/OpenAPI, Angular standalone, Vercel preparado; Gemini exclusivamente backend.
10. **Producto y trazabilidad:** capturas de seleccion, dashboard, mapa, patrones, reporte y calidad; describir demo y estados de fallo.
11. **Pruebas y reproducibilidad:** comandos uv/npm, lockfiles, fixtures solo para pruebas de reglas, E2E con datos reales, hashes de artefactos.
12. **Limitaciones:** temporada unica, muestra pequena, ausencia de video/tracking, no inferir movimientos, semantica LLM no completamente verificable, Colab remoto y Docker pendientes.
13. **Conclusiones:** utilidad descriptiva comprobable sin exagerar prediccion. El fracaso de promocion de LR/RF es un resultado cientifico, no se oculta.
14. **Trabajo futuro:** validacion con otras temporadas autorizadas, revision de reglas de reanudacion, calibracion y explicabilidad, evaluacion con analistas, exportacion PDF.
15. **Referencias y anexos:** StatsBomb, documentacion oficial, notebooks, OpenAPI, model card, decisiones y evidencia de pruebas.

## Matriz para completar con la rubrica

| Criterio probable | Evidencia disponible | Pendiente |
|---|---|---|
| Ciencia de datos | analytics/, notebooks/, model-card.md | Sesion Colab documentada |
| Evaluacion de modelos | model-evaluation.json, calibration.png | Interpretacion academica final por autor |
| Full-stack | backend/, frontend/, contracts/openapi.json | Capturas finales elegidas |
| Generativa | backend/gemini.py, tests/test_gemini.py | Prueba real con clave propia |
| Despliegue | frontend/vercel.json, Dockerfile | Validacion Docker y recursos externos |
| Comunicacion | demo.md, presentation.md | Grabar video y adaptar a rubrica |
