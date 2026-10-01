# Entidades y granularidad vigentes

Este documento describe las entidades implementadas; los esquemas ejecutables
están en `analytics/contracts.py`, los módulos de etapa y `backend/schemas.py`.
La lista completa de archivos de cada corrida está en su `contract.json`.

| Entidad | Unidad | Origen y finalidad |
|---|---|---|
| `matches_clean` | Un partido (`match_id`) | `02_clean`: fechas, participantes y marcador conciliado. |
| Eventos normalizados | Un evento por partido | `02_clean`: orden original, campos nested/flat y contexto previo. |
| Secuencias SCR-15 | Un córner | `03_scr15`: primer cierre, tiros atribuidos y evaluabilidad. |
| `corners_engineered` | Un córner | `04_features`: geometría, proxy corto, contexto y referencias históricas. |
| Perspectivas equipo-partido | Dos por partido | `04_features`: conteos observados, incluidos partidos sin córners. |
| Tablas por objetivo | Córner o equipo-partido | `04_features`: targets y predictores elegibles según objetivo. |
| `cluster_assignments` | Un destino asignado | `04_features`: K-Means descriptivo fijo predesarrollo. |
| `objective_winners` | Un objetivo | `05_modeling`: decisión temporal y justificación. |
| `temporal_metrics` | Objetivo, ventana y modelo | `05_modeling`: evaluación y denominadores. |
| Scouting run | Rival, corte y ocho partidos | `processed/runs`: sesión persistida de la aplicación. |
| Reporte y respuesta del agente | Una solicitud | Backend: evidencia citada, modo OpenAI o determinista y consumo. |

## Temporalidad

Las ventanas usan exactamente ocho partidos con `match_date < cutoff`.
El usuario confirma la selección automática; no sustituye partidos arbitrarios.
La presentación del historial es cronológica. Las primeras perspectivas sin
ocho partidos previos no se rellenan con datos inventados.

SCR-15 prepartido no usa destino, rematador, tiro o xG posterior del córner
objetivo. El modelo secundario corto/directo es un **escenario pre-cobro**:
puede incorporar contexto ya conocido cuando se concede el córner; no se
presenta como predicción estrictamente prepartido.

## Secuencia y espacio

`shot_within_15s` es nulo cuando no se puede evaluar el reloj o la secuencia.
Los nulos no son negativos. La falta de geometría no excluye por sí sola del
KPI temporal, pero sí limita mapas y clusters. Los destinos del pase no son
lugares de remate. Los clusters no son jugadas ensayadas ni predictores.

## Trazabilidad

Los eventos conservan partido, evento, índice y origen raw. Los contratos
conservan run, hashes y linaje. Cada scouting run fija la ventana y el
fingerprint del conjunto canónico: al cambiar la versión de datos, los runs
incompatibles se rechazan y se crea un análisis nuevo.

No existe una base de datos de entrenamiento creada por solicitud web.
DuckDB consulta Parquet verificado mediante consultas controladas y parámetros.
El esquema HTTP exacto puede explorarse en `/docs` con FastAPI activo.
