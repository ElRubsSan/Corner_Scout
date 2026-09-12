# Model card — CornerScout v0.3

Target: shot_within_15s de secuencias evaluables, no goles. 3,039 corners con ocho partidos previos disponibles. Variables de cada corner: SCR historico evaluable, corners por partido, proporcion de cortos y proporcion de envios altos de los ocho encuentros anteriores. No destino real ni outcome del corner objetivo. Todos los corners de un partido comparten variables prepartido; no confundir con prediccion en vivo.

Entrenamiento expansivo: validacion enero–14 febrero, validacion 15 febrero–marzo; holdout abril–mayo. Partidos y dias completos no se dividen entre entrenamiento y prueba. Preprocesamiento se ajusta en cada entrenamiento. No se ajustan hiperparametros con holdout. Umbral 0.5 fijo ilustrativo (F1 nulo por probabilidades inferiores; no demuestra inutilidad absoluta, evaluar Brier/calibracion).

Modelos: tasa base en entrenamiento, StandardScaler + LogisticRegression(C=1), RandomForest(200 arboles, profundidad 4, hoja minima 30). Semilla 42. Promocion exige Brier menor y AP mayor que baseline en ambos bloques de validacion, y confirmacion Brier en holdout. Resultado: **baseline**. Las mejoras pequenas en holdout no revierten el fallo en validacion. No se promocionan LR/RF. Su evaluacion completa esta en model-evaluation.json y calibration.png.

K-Means: k=2..6, estandarizacion, n_init=10, silhouette y minimo 20 observaciones por grupo. Variables: destino x/y; baseline espacial interpretable. Snapshots mensuales entrenados solo con historia anterior. No predice tiros ni identifica jugadas ensayadas. La UI usa el ultimo snapshot disponible anterior/al corte, excluyendo geometria invalida. IDs de cluster solo comparables dentro del mismo snapshot.

Los resultados de evaluacion global de temporada se muestran como evaluacion retrospectiva del sistema, no evidencia disponible a un entrenador en el corte historico. Probabilidad operativa anterior a junio: baseline historico usando exclusivamente partidos anteriores al corte. No se usa el modelo entrenado con datos futuros.

Artefactos locales: artifacts/v0.3 (modelos y hashes), data/processed/features.parquet, clusters.parquet y model-evaluation.json. Regenerar con `uv run --extra ml cornerscout train` tras pasar el gate de calidad.
