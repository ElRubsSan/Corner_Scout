# CornerScout - Guia de trabajo

## Producto

- El nombre visible del producto es **CornerScout**.
- Se conservan temporalmente la carpeta local `Corner_Scope` y el remoto `Corner_Scout`.
- Es un MVP academico de analisis prepartido de corners ofensivos.
- El caso de estudio es LaLiga 2015/16 de StatsBomb Open Data (`competition_id=11`, `season_id=27`).
- Los resultados historicos nunca deben presentarse como informacion actual.

## Fase actual

La fase 1 documental esta aprobada. El usuario autoriza ejecucion integral, pruebas, commits por fases y push a origin/main de fases validadas. No desplegar externamente hasta validar localmente y preparar configuraciones. Implementaciones autorizadas:

- Pipelines analiticos ejecutables.
- FastAPI o bases de datos.
- Angular standalone.
- La interfaz final es exclusivamente Angular standalone; nunca Streamlit, Gradio, Tableau o Power BI.
- Docker o despliegues.
- Modelos supervisados o no supervisados.
- Integracion Gemini exclusivamente desde FastAPI, Structured Outputs/Pydantic y fallback determinista.

Angular standalone, FastAPI/OpenAPI, frontend en Vercel y LLM son obligatorios. No usar interfaces alternativas. Modelos: baseline, regresion logistica, Random Forest y K-Means; modelado solo despues de validar datos. El notebook original aportado por el usuario se conserva intacto y no se incluye en commits hasta sanitizarlo; los notebooks nuevos son independientes.

## Prioridades del MVP

1. Restaurar y auditar los datos generados en Colab.
2. Validar la seleccion de los ocho partidos inmediatamente anteriores del rival.
3. Implementar y auditar SCR-15.
4. Construir el reporte prepartido descriptivo y trazable.
5. Incorporar patrones descriptivos.
6. Evaluar modelos supervisados solo despues de validar SCR-15.

## Reglas de datos

- La capa `data/raw` es inmutable.
- Los archivos raw, interim, processed y los artefactos pesados no se versionan en Git.
- Google Drive conserva la copia canonica actual en `/content/drive/MyDrive/Corner_Scout/data/raw`.
- Los nombres raw actuales son `competitions.csv`, `matches_laliga_2015_16.csv`, `metadata_ingesta.json`, `registro_ingesta.csv` y `events/<match_id>.jsonl.gz`; no se renombran sin una migracion explicita.
- El repositorio solo versiona codigo, notebooks sanitizados, documentacion, contratos y manifiestos sin datos sensibles.
- Nunca incluir credenciales, tokens, URLs privadas de Drive, rutas personales ni archivos `.env`.
- Cada transformacion futura debe conservar proveedor, competicion, temporada, `match_id`, `event_id` cuando aplique, fecha de procesamiento, version del pipeline y trazabilidad al archivo fuente.
- No sustituir datos ausentes con datos sinteticos sin una etiqueta visible de demo.

## Regla provisional SCR-15

- La secuencia comienza en un evento `Pass` cuyo `pass_type` es `Corner`.
- La secuencia termina por el primer limite aplicable: 15 segundos, cuando `possession_team` deja de ser el equipo ejecutor o al finalizar el periodo.
- Un cambio de `possession` con el mismo `possession_team` se registra para auditoria, pero no cierra automaticamente la secuencia.
- Un tiro exactamente a los 15 segundos se considera dentro de la ventana, sujeto a que no haya ocurrido antes otro criterio de cierre.
- No cerrar automaticamente por saque de banda, saque de meta, tiro libre u otra reanudacion en esta fase.
- Esas reanudaciones deben registrarse para auditoria antes de decidir si forman parte de la regla definitiva.
- Nunca atribuir un tiro de una posesion posterior al corner.
- En la regla actual, posesion posterior significa que el equipo en posesion cambio; un nuevo ID con el mismo equipo es solo auditoria. Seis secuencias temporalmente ambiguas se excluyen del denominador evaluable y se muestran como desconocidas.

La especificacion completa se mantiene en `docs/scr15-methodology.md`.

## Arquitectura y limites

- Los notebooks son exploratorios; la futura logica productiva debe vivir en modulos Python probados.
- El procesamiento pesado sera offline sobre raw e interim.
- El backend futuro consultara artefactos procesados; no descargara StatsBomb ni entrenara modelos por solicitud.
- DuckDB solo ejecutara consultas controladas y parametrizadas. Un LLM nunca generara SQL libre.
- Angular consumira un contrato OpenAPI generado por FastAPI cuando ambas capas existan.
- Los calculos, selecciones, clusters y probabilidades se producen en Python, nunca en un LLM.

## Convenciones futuras

- Python y TypeScript deben tener tipado explicito en limites publicos.
- Los contratos externos se validan antes de procesarse.
- Las fechas se expresan en ISO 8601.
- Los identificadores de StatsBomb se conservan sin reasignarlos.
- Las tablas se nombran en `snake_case`; los componentes Angular seguiran la convencion oficial vigente cuando se cree el frontend.
- Toda regla no obvia debe estar documentada y cubierta por una prueba.
- No fijar versiones de herramientas sin consultar primero su documentacion oficial vigente.

## Git y seguridad

- No hacer commits, pushes, despliegues ni cambios irreversibles sin autorizacion explicita.
- No borrar ni sobrescribir datos raw.
- No versionar `.env`, credenciales, bases locales, Parquet, JSONL comprimido ni modelos entrenados.
- Mantener los cambios de cada fase pequenos y verificables.

## Comandos disponibles

### Fase 2 validada localmente

Usar uv de preferencia: `uv sync --extra dev`, `uv run cornerscout ingest`, `uv run cornerscout build`, `uv run --extra dev pytest`, `uv run --extra dev python scripts/notebooks.py --execute --through 3`.

Cobertura real: 380 partidos, 20 equipos, 1,295,354 eventos, 3,841 corners. Seis secuencias no evaluables por reloj regresivo y un corner excluido de visualizacion espacial. Ver docs/data-audit.md. Seis pruebas de limites SCR-15 pasan. Tres notebooks nuevos ejecutados localmente; validacion remota en Google Colab pendiente. Jupyter local emite avisos de transporte TCP/Windows, no se afirma ejecucion sin warnings en Colab. No entrenar sin quality.passed=true.

### Fase 3

`uv sync --extra dev --extra ml`; `uv run --extra ml cornerscout train`. Entrenados baseline, LR, RF y K-Means mensual. Baseline seleccionado: LR/RF no mejoran consistentemente validacion. Metricas reales: docs/model-evaluation.json, docs/model-card.md. Ocho partidos previos estrictos; no promocionar un modelo con entrenamiento/evaluacion posterior al corte.

Validacion fase 3: ocho pruebas pasan y cinco notebooks nuevos ejecutados localmente con nbclient. No se ha ejecutado Google Colab remoto. Artefactos y Parquet ignorados por Git.

Verificaciones Git no destructivas:

### Fase 4 validada

FastAPI implementado. `uv run --extra api uvicorn backend.main:app --host 127.0.0.1 --port 8000`. OpenAPI: `uv run --extra api python scripts/export_openapi.py`. API usa nombre exacto del rival como clave de seleccion y match_id del proveedor; no inventa IDs de equipo. Corte por fecha exclusivo (partido objetivo usa su fecha). Diez pruebas locales pasan, incluyendo flujo real de ocho partidos, errores y reproducibilidad. DuckDB hace SELECT de Parquet con conexiones por consulta. Runs persistidos en processed/runs. Reporte determinista y endpoint de plan previo. Advertencias de dependencias TestClient registradas; Colab remoto pendiente.

### Fase 5 validada con mocks

Gemini SDK oficial google-genai 2.23.0, Structured Outputs/Pydantic, timeout HTTP y fallback por clave ausente, cuota, fallo o salida invalida. Diez pruebas de API/Gemini pasan. Sin llamada real al proveedor: requiere GEMINI_API_KEY en backend; ver docs/gemini.md. `uv sync --all-extras` y `uv run --all-extras pytest`. Validar IDs/cifras no garantiza toda la semantica del texto; limitacion documentada.

### Fase 6 validada localmente

Angular standalone 22.1.6 y CLI/build 22.1.8, Node 24.19.0, TS 6.0.3. `npm ci` completo corrigio @angular/common y common/http sin external. `npm run build` pasa (247 kB iniciales); `npm run typecheck` pasa; `npm run e2e` pasa 2 recorridos Chromium con FastAPI y datos reales (dashboard, mapa, patrones, reporte fallback, calidad, corte por fecha y partido). Ejecutar npm dentro de frontend. Playwright inicia y detiene ambos servidores; no usa claves reales.

OpenAPI generado en contracts/openapi.json y frontend/src/app/core/api.generated.ts. Codegen aislado en tools/codegen por peer TS5. Vercel configurado, backend Docker preparado, despliegues externos no realizados. Docker requiere validacion con motor disponible. Ver docs/deployment.md.

### Fase 7 — cierre local

Documentados README de instalacion uv/npm, guia Colab, demo de cinco minutos, guion de video, estructura academica y fuentes oficiales. Rubrica concreta no recibida: la matriz academica es provisional. Build produccion Angular, typecheck y dos E2E pasan; suite Python completa: 18 pruebas pasan, dos warnings de dependencias TestClient. Cinco notebooks ejecutados localmente; no afirmar prueba remota en Colab ni ausencia de warnings de Jupyter.

Pendientes manuales: validar en Colab, instalar Docker y probar contenedor, configurar clave Gemini en backend y hacer prueba real, elegir backend HTTPS/volumen y configurar apiBaseUrl antes de Vercel; incorporar logo oficial StatsBomb para publicacion. No se desplego externamente. Estado detallado y siguiente accion en RESUMEN_DE_CONTINUIDAD.md.

```powershell
git status --short
git diff --check
git ls-files
```

Los comandos de instalacion, pruebas, procesamiento y ejecucion se agregaran cuando existan sus respectivas capas.

## Cierre de fase

Al terminar cada fase se debe informar:

- Archivos modificados.
- Decisiones tomadas.
- Validaciones realizadas.
- Riesgos y datos pendientes.
- Siguiente fase recomendada.
