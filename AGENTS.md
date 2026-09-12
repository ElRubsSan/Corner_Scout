# CornerScout - Guia de trabajo

## Producto

- El nombre visible del producto es **CornerScout**.
- Se conservan temporalmente la carpeta local `Corner_Scope` y el remoto `Corner_Scout`.
- Es un MVP academico de analisis prepartido de corners ofensivos.
- El caso de estudio es LaLiga 2015/16 de StatsBomb Open Data (`competition_id=11`, `season_id=27`).
- Los resultados historicos nunca deben presentarse como informacion actual.

## Fase actual

La fase 1 solo permite estructura del monorepo, documentacion, contratos de datos y manifiestos. No se deben construir todavia:

- Pipelines analiticos ejecutables.
- FastAPI o bases de datos.
- Angular u otra interfaz.
- Docker o despliegues.
- Modelos supervisados o no supervisados.
- Integraciones con LLM o agentes.

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

Todavia no hay aplicaciones ni dependencias instaladas. En fase 1 solo son aplicables verificaciones no destructivas:

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
