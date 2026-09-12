# Manifiestos de datos

Los manifiestos permiten verificar la copia local sin versionar los datos crudos.

## Manifiesto raw

Archivo previsto:

```text
statsbomb_laliga_2015_16.csv
```

Debe generarse a partir de `raw_manifest.template.csv` y contener una fila por archivo raw: los cuatro archivos de metadatos y los 380 archivos de eventos.

Columnas:

| Columna | Descripcion |
|---|---|
| `relative_path` | Ruta relativa desde `data/raw/`, sin ruta personal |
| `layer` | Siempre `raw` para este manifiesto |
| `provider` | `statsbomb_open_data` |
| `competition_id` | 11 |
| `season_id` | 27 |
| `match_id` | ID para eventos; vacio para el archivo agregado de partidos |
| `media_type` | Por ejemplo `application/x-ndjson` |
| `compression` | `gzip` |
| `byte_size` | Tamano exacto del archivo |
| `sha256` | Checksum hexadecimal |
| `record_count` | Cantidad de lineas JSON validas |
| `exported_at` | Fecha UTC de exportacion desde Colab |
| `schema_version` | `raw-input-v0.1` mientras aplique |

## Restricciones

- No incluir rutas absolutas.
- No incluir IDs privados de Google Drive.
- No incluir tokens, correos o credenciales.
- No modificar checksums para ocultar diferencias.
- Un cambio en cualquier archivo raw produce una nueva version del manifiesto.

El manifiesto real se creara despues de recibir los archivos de Colab y no debe rellenarse con valores estimados.

## Resumen de cobertura

`dataset_summary.template.json` define el resumen agregado que debe completarse como `statsbomb_laliga_2015_16_summary.json`. Los campos `observed` se calculan desde los archivos restaurados; no se rellenan manualmente con los valores esperados.
