# Auditoria real de datos — fase 2

Descarga explicita de StatsBomb Open Data fijada a revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Los nombres de archivos raw aprobados se conservan. `CORNERSCOUT_DATA_DIR` permite restaurar o montar una copia de Drive sin rutas personales.

El notebook original exporta con statsbombpy `flatten_attrs=True`. El adaptador admite ese formato y el JSON anidado del proveedor; no sobrescribe originales. La descarga nueva usa JSON anidado y registra su formato en metadata_ingesta.json.

Resultado: 380 partidos, 20 equipos, 1,295,354 eventos, 3,841 corners. Sin IDs duplicados ni archivos faltantes. Se auditan 126 regresiones de timestamp y 25 eventos con coordenadas fuera del terreno. Evidencia local: `data/interim/anomalies.json`.

Politica conservadora: conservar orden por periodo/index. No imputar timestamps. Seis secuencias con reloj regresivo dentro de la ventana tienen target/xG nulos y quedan excluidas del denominador evaluable (nunca tratadas como negativas). Mostrar siempre corners totales, evaluables y excluidos. Un corner fuera de limites se conserva para SCR-15 pero se excluye de mapas y clustering. Otros eventos fuera de limites no alteran la atribucion temporal. Raw permanece intacto.

SCR-15 provisional: [0,15] segundos, cierre por equipo en posesion o periodo; cambios de ID de posesion y reanudaciones solo se auditan. No se reabre despues de perder posesion. Las zonas son destinos de pase, no remates. Corto: distancia euclidiana <=15 unidades; umbral descriptivo provisional. Lado: y_bajo/y_alto evita etiquetar izquierda/derecha sin perspectiva explicita.

Ejecutar: `uv sync --extra dev`, `uv run cornerscout ingest`, `uv run python -m analytics.audit`, `uv run cornerscout build`, `uv run --extra dev pytest`. Los manifiestos contienen hashes reales y los Parquet permanecen fuera de Git.
