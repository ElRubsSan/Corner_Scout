# Modelado canónico por objetivo

La versión vigente es `05-modeling-v3-objectives`, implementada en
`analytics/modeling.py` y orquestada por `analytics/pipeline.py`.

| Objetivo | Candidato | Decisión canónica |
|---|---|---|
| Tiro en SCR-15 | Regresión logística regularizada | Tasa histórica de liga |
| Corto/directo | Regresión logística regularizada | Candidato seleccionado |
| Volumen por equipo-partido | Regresión de Poisson regularizada | Candidato seleccionado |
| Zona del pase | Gate de soporte y persistencia | Sin predicción |

Las variables resumen ocho partidos estrictamente anteriores. Preprocesamiento
y ajuste se realizan dentro del entrenamiento temporal; el destino del córner
objetivo y K-Means no son predictores. Tres ventanas de desarrollo seleccionan;
el periodo final confirma y no modifica ganadores. No es un holdout completamente
intacto: hubo verificación global de calidad y conteos, documentada en el contrato.

### Alcance de cada objetivo

SCR-15 y volumen son objetivos prepartido. **Corto/directo es secundario de
escenario pre-cobro**, cuando se conocen minuto, marcador, diferencia numérica
y lado del córner concedido; no se presenta como predicción estrictamente
prepartido. El target corto es el proxy geométrico versionado, no una etiqueta
humana independiente. Zona no superó el gate de persistencia y no se predice.

### Ventanas canónicas

Los límites son exclusivos por la derecha:

| Ventana | Inicio | Fin exclusivo | Uso |
|---|---|---|---|
| Desarrollo 1 | 2016-01-25 | 2016-02-21 | Selección |
| Desarrollo 2 | 2016-02-21 | 2016-03-15 | Selección |
| Desarrollo 3 | 2016-03-18 | 2016-04-18 | Selección |
| Final | 2016-04-19 | 2016-05-16 | Confirmación |

SCR-15 pasó cero de tres ventanas y conserva la referencia liguera.
Corto/directo pasó dos. El candidato de conteo fue seleccionado con familia
Poisson. Las ventanas y métricas de una publicación concreta se leen de sus
artefactos canónicos.

Se comparan referencia liguera e histórico suavizado. Para binarios se examinan
Brier, log loss, AP y calibración; para volumen MAE y deviance Poisson. Se
remuestrean partidos completos para comparar incertidumbre. Las métricas y
ventanas exactas están en `data/processed/05_modeling/` con hashes y contrato.

La promoción binaria exige mejoras en Brier, log loss y AP sin degradar
calibración en al menos dos ventanas de desarrollo. La evaluación no necesita
un umbral clasificatorio de 0,5. Los artefactos retrospectivos se ajustan antes
del periodo final; los `refit_full` usan la temporada completa y no se presentan
como reevaluados fuera de muestra.

K-Means se fija antes de desarrollo y solo describe destinos de pases directos.
No descubre por sí mismo jugadas ensayadas ni garantiza tiros. El proxy de corto
usa 18 unidades StatsBomb; la auditoría de 40 eventos fue asistida por la
clasificación, no independiente. Registró 28 TP, 10 TN, 0 FP y 2 FN. No se
extrapola el 95 % de acuerdo a toda la temporada.

El ajuste descriptivo de K-Means usa destinos anteriores a `2016-01-01`, con
cuatro grupos fijados por la decisión exploratoria documentada. No se escoge
otra cantidad por cada consulta ni se promociona una probabilidad de tiro a
partir del cluster.

Reproducir: `uv run --all-extras cornerscout train`, después de `ingest` y
`build`. FastAPI sirve artefactos verificados y no entrena por solicitud.

Para interpretar una sesión, revisar Calidad en la app y mantener separados
los indicadores observados de la ventana, la referencia liguera y la decisión
del modelo. Otras temporadas y revisión de vídeo son líneas futuras; no hay
validación de comportamiento actual de equipos.
