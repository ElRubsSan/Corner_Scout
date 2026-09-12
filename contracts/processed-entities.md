# Contrato de entidades logicas

Version provisional: `processed-entities-v0.1`.

Estas entidades describen el modelo logico. No implican todavia una base de datos ni archivos creados.

## Campos transversales

Cuando apliquen, las entidades deben conservar:

- `provider` con valor `statsbomb_open_data`.
- `competition_id` con valor 11.
- `season_id` con valor 27.
- `match_id`.
- `event_id` o evento fuente.
- `processed_at` en UTC.
- `pipeline_version`.
- `schema_version`.
- `source_manifest_sha256`.
- `quality_flags`.

## `matches`

Granularidad: una fila por partido.

Clave: `match_id`.

Contenido minimo: fecha, hora disponible, local, visitante, marcador, competicion y temporada.

Reglas:

- La seleccion temporal usa fecha y hora confirmadas; si solo existe fecha, se aplica una politica explicita de corte.
- El partido objetivo nunca forma parte de su propia ventana historica.

## `events`

Granularidad: una fila por evento normalizado.

Clave: `match_id`, `event_id`.

Contenido minimo: indice original, periodo, timestamp, tipo, posesion, equipos, jugador, ubicacion y subconjuntos de pase o tiro requeridos.

Reglas:

- Conserva referencia al archivo y linea raw.
- No pretende aplanar desde el inicio todos los campos de StatsBomb.

## `corners`

Granularidad: una fila por pase de corner ofensivo.

Clave: `match_id`, `corner_event_id`.

Contenido minimo:

- Equipo y jugador ejecutor.
- Fecha y contexto de partido.
- Periodo, indice y timestamp.
- Origen y destino StatsBomb.
- Longitud, angulo y altura disponibles.
- Lado y tipo derivados, con version de regla.
- Zona de destino, con version de zonificacion.

Las etiquetas corto, envio, lado y zona permanecen pendientes hasta auditar coordenadas y distribuciones reales.

## `corner_sequences`

Granularidad: una fila por corner.

Clave: `match_id`, `corner_event_id`.

Contenido minimo:

- Inicio y fin de secuencia.
- Posesion y equipo inicial.
- Causa de cierre.
- `shot_within_15s`.
- Cantidad e IDs de tiros validos.
- xG total valido.
- Reanudaciones observadas.
- Version de SCR-15.

La regla provisional esta definida en `docs/scr15-methodology.md`.

## `team_form_windows`

Granularidad: una fila por partido incluido en una ventana de scouting.

Clave: `window_id`, `window_position`.

Contenido minimo:

- Rival.
- Fecha de corte o partido objetivo.
- `match_id` incluido.
- Posicion de 1 a 8, ordenada de mas reciente a mas antiguo.
- Condicion local o visitante.
- Version de seleccion temporal.

Reglas:

- Debe contener exactamente ocho partidos para una ejecucion valida.
- Todos los partidos deben ser estrictamente anteriores al corte.
- La seleccion es automatica y el usuario solo confirma la lista; no sustituye partidos arbitrariamente.

## `corner_clusters`

Estado: diferido hasta despues de SCR-15 descriptivo.

Granularidad prevista: una fila por corner y version de clustering.

Contenido previsto: cluster, distancia al centroide, variables usadas, fecha maxima de entrenamiento y descripcion no determinista del patron.

Un cluster se denomina patron recurrente, no jugada ensayada.

## `corner_predictions`

Estado: diferido hasta validar SCR-15.

Granularidad prevista: una fila por prediccion reproducible.

Contenido previsto: corte temporal, variables prepartido, probabilidad, version de modelo y fecha maxima de entrenamiento.

No puede contener destino real del pase, tiro posterior, xG posterior, rematador ni informacion futura.

## `scouting_reports`

Granularidad: una fila por version de reporte.

Contenido minimo futuro: rival, corte, ocho partidos, KPIs, patrones, recomendaciones, limitaciones, fuentes y referencias de evidencia.

La primera version sera determinista y no dependera de un LLM.

## `data_quality_logs`

Granularidad: una fila por comprobacion, entidad o registro afectado.

Contenido minimo:

- Regla de calidad.
- Severidad.
- Resultado y conteo.
- Identificadores afectados cuando sea viable.
- Version de datos y pipeline.
- Fecha de ejecucion.

Los errores que cambien la atribucion de SCR-15 deben poder bloquear la publicacion del artefacto.
