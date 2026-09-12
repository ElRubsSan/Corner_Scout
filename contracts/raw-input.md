# Contrato de entrada raw

Version provisional: `raw-input-v0.1`.

Este contrato refleja el formato descrito para la exportacion de Colab. Debe verificarse contra archivos reales antes de crear codigo analitico.

## Conjunto de entrada

La ubicacion canonica actual en Google Drive es:

```text
/content/drive/MyDrive/Corner_Scout/data/raw/
|-- competitions.csv
|-- matches_laliga_2015_16.csv
|-- metadata_ingesta.json
|-- registro_ingesta.csv
`-- events/<match_id>.jsonl.gz
```

La copia local conserva exactamente los mismos nombres bajo `data/raw/`. No existe `matches.jsonl.gz` y no se normalizaran nombres o formatos dentro de la capa raw.

## Competiciones

Ruta local:

```text
data/raw/competitions.csv
```

Finalidad: conservar el catalogo de competiciones y temporadas usado para seleccionar `competition_id=11` y `season_id=27`.

El encabezado y los tipos reales se documentaran despues de inspeccionar el archivo. No se presume todavia un mapeo de columnas.

## Partidos

Ruta local:

```text
data/raw/matches_laliga_2015_16.csv
```

Granularidad esperada: una fila por partido, con 380 filas para la temporada.

Campos logicos que el futuro adaptador debe poder obtener, sin asumir aun sus nombres fisicos:

| Campo logico | Regla |
|---|---|
| `match_id` | Entero, unico, no nulo |
| `match_date` | Fecha ISO, no nula |
| `kick_off` | Hora nullable |
| `competition_id` | Debe ser 11 |
| `competition_name` | Texto |
| `season_id` | Debe ser 27 |
| `season_name` | Texto |
| `home_team_id` | Entero, no nulo |
| `home_team_name` | Texto, no nulo |
| `away_team_id` | Entero, no nulo |
| `away_team_name` | Texto, no nulo |
| `home_score` | Entero nullable |
| `away_score` | Entero nullable |

El mapeo entre estos campos logicos y las columnas fisicas se fijara solo despues de auditar el encabezado real.

## Metadatos de ingesta

Rutas locales:

```text
data/raw/metadata_ingesta.json
data/raw/registro_ingesta.csv
```

`metadata_ingesta.json` describe la ejecucion general de Colab. `registro_ingesta.csv` conserva el registro por archivo o partido. Ambos forman parte de raw y se mantienen sin transformaciones.

Sus campos, granularidad y relacion exacta con los 380 partidos deben auditarse antes de convertirlos en un contrato de columnas estricto.

## Eventos

Ruta canonica:

```text
data/raw/events/<match_id>.jsonl.gz
```

Granularidad: un objeto JSON por evento y por linea. El `match_id` se deriva inicialmente del nombre del archivo y se incorpora como campo explicito en interim.

Campos comunes minimos esperados:

| Campo logico | Ruta fuente esperada | Regla |
|---|---|---|
| `event_id` | `id` | UUID o texto unico dentro del partido |
| `index` | `index` | Entero para orden original |
| `period` | `period` | Entero, no nulo |
| `timestamp` | `timestamp` | Tiempo dentro del periodo |
| `minute` | `minute` | Entero |
| `second` | `second` | Entero |
| `type_id` | `type.id` | Entero |
| `type_name` | `type.name` | Texto |
| `possession` | `possession` | Entero nullable sujeto a auditoria |
| `possession_team_id` | `possession_team.id` | Entero nullable |
| `team_id` | `team.id` | Entero nullable segun tipo de evento |
| `player_id` | `player.id` | Entero nullable |
| `location` | `location` | Arreglo `[x, y]` nullable |

Campos minimos para pases y corners:

| Campo logico | Ruta fuente esperada | Regla |
|---|---|---|
| `pass_type_id` | `pass.type.id` | Nullable fuera de pases |
| `pass_type_name` | `pass.type.name` | `Corner` para inicio SCR-15 |
| `pass_end_location` | `pass.end_location` | Arreglo `[x, y]` nullable sujeto a calidad |
| `pass_length` | `pass.length` | Numero nullable |
| `pass_angle` | `pass.angle` | Numero nullable |
| `pass_height_id` | `pass.height.id` | Entero nullable |
| `pass_height_name` | `pass.height.name` | Texto nullable |
| `pass_outcome_id` | `pass.outcome.id` | Entero nullable; ausencia puede representar exito |

Campos minimos para tiros:

| Campo logico | Ruta fuente esperada | Regla |
|---|---|---|
| `shot_statsbomb_xg` | `shot.statsbomb_xg` | Numero nullable fuera de tiros |
| `shot_outcome_id` | `shot.outcome.id` | Entero nullable |
| `shot_outcome_name` | `shot.outcome.name` | Texto nullable |
| `shot_end_location` | `shot.end_location` | Arreglo de dos o tres valores nullable |

## Reglas de preservacion

- Raw se valida pero nunca se reescribe.
- No se eliminan propiedades desconocidas del archivo fuente.
- Los nulos se conservan; no se imputan en raw.
- Los IDs se conservan con su representacion original.
- El archivo y numero de linea se registraran en interim para trazabilidad.
- Una variacion del esquema se registra en calidad y no se corrige silenciosamente.

## Validaciones de cobertura

- 380 partidos esperados.
- 380 archivos de eventos esperados.
- 20 equipos distintos esperados.
- Cada archivo de eventos corresponde a un `match_id` de `matches_laliga_2015_16.csv`.
- Los cuatro archivos de metadatos requeridos estan presentes y no estan vacios.
- `metadata_ingesta.json` y `registro_ingesta.csv` son coherentes con los archivos de eventos presentes.
- Todos los eventos tienen `id`, `index`, `period`, `timestamp` y `type` salvo excepciones documentadas.
- La orientacion y rango real de coordenadas se auditan antes de clasificar lados o zonas.

## Pendientes de confirmar con datos reales

- Encabezados, tipos y codificacion de los cuatro archivos de metadatos.
- Estructura exacta de `metadata_ingesta.json`.
- Granularidad y estados registrados en `registro_ingesta.csv`.
- Si cada linea JSONL contiene directamente el evento o un envoltorio adicional.
- Tipo concreto de `event_id` y precision del timestamp.
- Completitud de `possession` y `possession_team`.
- Uso real de IDs o nombres para detectar `Corner`.
- Campos disponibles para tecnicas, altura y resultados de pase.
