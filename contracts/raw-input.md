# Entrada raw implementada

La ingesta usa StatsBomb Open Data, competición 11 y temporada 27, revisión
`4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. La implementación está en
`analytics/ingestion.py` y `analytics/io.py`; la normalización está en
`analytics/cleaning.py` y `analytics/pipeline.py`.

```text
data/raw/
  competitions.csv
  matches_laliga_2015_16.csv
  metadata_ingesta.json
  registro_ingesta.csv
  events/<match_id>.jsonl.gz
```

Cada línea descomprimida contiene un evento JSON. El partido se identifica
también por el nombre del archivo. Se esperan 380 partidos y archivos de
eventos y 20 equipos. Raw se crea o valida; nunca se reescribe.

## Partidos

La limpieza requiere `match_id`, `match_date`, `kick_off`, `home_team`,
`away_team`, `home_score` y `away_score`. Acepta también las columnas
`home_team_home_team_name` y `away_team_away_team_name` de la exportación
aplanada y las adapta en la capa derivada. No renombra el CSV fuente.
La selección histórica usa cortes exclusivos por fecha.

## Eventos nested y flat

El adaptador reconoce los valores anidados del proveedor y sus equivalentes
aplanados. Entre los campos consumidos se encuentran:

| Finalidad | Campos del proveedor |
|---|---|
| Identidad y orden | `id`, `index`, `period`, `timestamp`, `minute`, `second` |
| Tipo y equipos | `type`, `team`, `possession`, `possession_team` |
| Ejecutante | `player`, `location` |
| Pase de córner | `pass.type`, `pass.end_location`, `pass.length`, `pass.height` |
| Pase y destinatario | `pass.recipient`, resultado y propiedades disponibles |
| Tiro | `shot.statsbomb_xg`, tipo y resultado disponibles |
| Contexto | Alineaciones, sustituciones, tarjetas y goles/autogoles |

Los objetos con `id`/`name` y las columnas aplanadas se normalizan conservando
ausencias. El contexto se reconstruye **antes** del evento. El esquema
normalizado completo se consulta en `analytics/cleaning.py`.

## Validación y preservación

- Se inspeccionan archivos comprimidos, JSON, conteos y pertenencia de partidos.
- El contrato `01-ingestion-v1` registra las huellas de raw.
- `02_clean` verifica los archivos que consume contra ese contrato.
- La normalización conserva referencia al archivo y línea raw.
- Los relojes ambiguos y coordenadas inválidas se auditan; no se imputan para
  convertir una secuencia en válida.
- Las propiedades fuente permanecen en raw aunque no se consuman en el MVP.

No se requieren tracking, vídeo ni StatsBomb 360 para ejecutar este pipeline.
Los procedimientos de copia y recuperación están en
[restauración de datos](../docs/data-restoration.md).
