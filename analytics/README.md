# Analytics · pipeline offline

La lógica científica se ejecuta en módulos Python. Las etapas
publican contratos Pydantic, SHA-256, conteos y linaje antes de que la siguiente
pueda consumir sus archivos. Raw no se sobrescribe.

## Preparación

Desde la raíz, después de instalar Python y uv:

```powershell
uv sync --locked --all-extras
uv run --extra pipeline cornerscout ingest
uv run --all-extras cornerscout build
uv run --all-extras cornerscout train
```

`build` encadena `clean`, `scr15` y `features`. No incluye ingesta ni modelado.
Cada comando de etapa también puede ejecutarse individualmente:

```powershell
uv run --all-extras cornerscout clean
uv run --all-extras cornerscout scr15
uv run --all-extras cornerscout features
```

Estos comandos requieren el contrato previo completo. Las etapas derivadas se
republican al ejecutarlas; las salidas existentes no son una copia de seguridad.
Para otra raíz de datos, configura `CORNERSCOUT_DATA_DIR` en la terminal;
el CLI no carga `.env` automáticamente. Ver [datos](../docs/data-restoration.md).

## Módulos y resultados

| Etapa | Módulos principales | Resultado |
|---|---|---|
| 01 | `ingestion`, `io` | Fuente inmutable e inventario verificado. |
| 02 | `cleaning`, `context`, `pipeline` | Eventos normalizados y contexto anterior. |
| 03 | `scr15`, `pipeline` | Secuencias evaluables y auditoría de primer cierre. |
| 04 | `features`, `modeling`, `pipeline` | Historiales de ocho partidos y K-Means descriptivo. |
| 05 | `modeling`, `pipeline` | Ventanas, métricas, gates, modelos y ganadores. |
| 06–07 | `tactical_report`, `agent_tools`, backend | Evidencia tipada y consultas de sesión. |

La versión de modelado es `05-modeling-v3-objectives`. Compara referencias
ligueras e históricas con regresión logística regularizada o Poisson según
objetivo. No hay Random Forest vigente. K-Means solo describe destinos y nunca
es predictor. Las tres ventanas de desarrollo deciden; el periodo final confirma.
Ver [model card](../docs/model-card.md).

Para evaluar 05 sin sustituir una publicación existente, la función
`analytics.pipeline.train(Path("data"), output=directorio_temporal)` permite
una salida aislada; ese directorio debe elegirse explícitamente.

## Verificación

```powershell
uv run --all-extras pytest
```

Las pruebas pequeñas usan fixtures identificadas; las regresiones completas
usan datos locales cuando están disponibles. No se rellenan datos productivos
ausentes con fixtures. Los resultados recientes están en
[validación](../docs/validation.md).
