# Restauracion de datos desde Google Drive

## Objetivo

La copia canonica actual de los datos exportados por Colab permanece en Google Drive, en `/content/drive/MyDrive/Corner_Scout/data/raw`. La restauracion local se realiza en `data/raw/`, que esta excluido de Git.

Alternativa implementada y autorizada: `uv run cornerscout ingest` descarga explicitamente archivos faltantes desde la revision publica fijada de StatsBomb. No usa credenciales ni sustituye raw existente. La copia nueva usa eventos anidados; el adaptador tambien admite la exportacion aplanada del notebook original. `CORNERSCOUT_DATA_DIR` permite apuntar al padre de raw/ en Drive o en una restauracion local.

## Archivos que deben permanecer en Google Drive

La estructura canonica actual es:

```text
/content/drive/MyDrive/Corner_Scout/data/raw/
|-- competitions.csv
|-- matches_laliga_2015_16.csv
|-- metadata_ingesta.json
|-- registro_ingesta.csv
`-- events/
    |-- <match_id_1>.jsonl.gz
    |-- <match_id_2>.jsonl.gz
    `-- ... 380 archivos en total
```

Archivos obligatorios:

- `competitions.csv`: catalogo de competiciones y temporadas usado durante la ingesta.
- `matches_laliga_2015_16.csv`: metadatos de los 380 partidos de LaLiga 2015/16.
- `metadata_ingesta.json`: metadatos generales de la ejecucion de ingesta.
- `registro_ingesta.csv`: registro producido por Colab para auditar la ingesta por archivo o partido.
- `events/<match_id>.jsonl.gz`: un objeto de evento por linea y un archivo por partido, 380 archivos esperados.

No existe `matches.jsonl.gz`. Los cinco nombres y formatos actuales deben conservarse sin migrarlos, renombrarlos ni sobrescribirlos. Cualquier cambio futuro requerira una decision de migracion explicita y trazable.

No son obligatorios para el MVP inicial los archivos de video, tracking, 360, alineaciones separadas o datos actuales. Si Colab genero alguno, debe mantenerse fuera del conjunto de entrada hasta documentar su necesidad.

## Archivos derivados que pueden llevarse a Git

Los archivos raw anteriores permanecen en Google Drive y en la copia local ignorada. Solo los manifiestos derivados, sin filas de eventos ni informacion privada, podran incorporarse posteriormente al repositorio:

- `data/manifests/statsbomb_laliga_2015_16.csv`: inventario sin datos de eventos, generado a partir de `raw_manifest.template.csv`.
- `data/manifests/statsbomb_laliga_2015_16_summary.json`: resumen agregado de cobertura, cuando se defina su contrato final.

El notebook actual se llama `Third_Man_Analytics_Ingesta_de_Datos.ipynb` y debe permanecer fuera del repositorio hasta confirmar su incorporacion. Mas adelante se evaluara una copia sanitizada y el nombre consistente `01_ingesta_statsbomb.ipynb`.

Antes de una eventual incorporacion del notebook se deben eliminar:

- Tokens, cookies, IDs privados de Drive y credenciales.
- Rutas como `C:\Users\...` o rutas privadas de Google Drive.
- Outputs que contengan eventos completos o grandes tablas.
- Archivos incrustados y datos descargados dentro del notebook.

La eventual copia sanitizada debe conservar las versiones de dependencias usadas, la URL publica de StatsBomb Open Data, los identificadores 11 y 27 y una explicacion del formato exportado.

## Archivos que no deben llevarse a Git

- Los 380 archivos de eventos.
- `competitions.csv`, `matches_laliga_2015_16.csv`, `metadata_ingesta.json` y `registro_ingesta.csv`.
- El notebook `Third_Man_Analytics_Ingesta_de_Datos.ipynb` mientras no se apruebe su incorporacion.
- Parquet interim o processed.
- Bases DuckDB locales.
- Modelos entrenados.
- Credenciales o archivos `.env`.
- Enlaces privados de Google Drive.

## Destino local esperado

Una vez copiados desde Drive, los archivos deben quedar asi:

```text
data/raw/competitions.csv
data/raw/matches_laliga_2015_16.csv
data/raw/metadata_ingesta.json
data/raw/registro_ingesta.csv
data/raw/events/<match_id>.jsonl.gz
```

No se debe editar, recomprimir ni renombrar un archivo despues de calcular su checksum. Cualquier normalizacion posterior se escribe en `data/interim/`.

## Manifiesto requerido

El manifiesto versionable debe incluir una fila para cada uno de los cuatro archivos de metadatos y una por archivo de eventos. Sus columnas se definen en `data/manifests/README.md`.

El manifiesto no debe incluir rutas absolutas. `relative_path` siempre parte desde `data/raw/`.

## Verificaciones previas al procesamiento

Estas verificaciones se ejecutan mediante analytics/pipeline.py; sus resultados reales y excepciones auditadas estan en docs/data-audit.md. El manifiesto efectivo es data/manifests/raw.json (ruta relativa, bytes y SHA-256); quality-summary.json contiene conteos agregados. Las plantillas CSV/JSON de fase 1 son referencias documentales y no sustituyen estos manifiestos generados.

- Existen exactamente 380 archivos en `events/`.
- Los nombres de archivo son `match_id` validos y unicos.
- Cada `match_id` de eventos existe en `matches_laliga_2015_16.csv`.
- Cada archivo puede descomprimirse y cada linea contiene JSON valido.
- Los checksums coinciden con el manifiesto.
- La competicion y temporada corresponden a 11 y 27.
- Hay 380 partidos y 20 equipos distintos.
- No hay archivos vacios ni partidos sin eventos.
- `metadata_ingesta.json` y `registro_ingesta.csv` son coherentes con los archivos presentes.

## Datos derivados de Colab que no se reutilizaran automaticamente

Si Colab contiene CSV, Parquet, clusters, variables o KPIs adicionales, deben quedarse en Drive hasta documentar:

- Codigo y version que los produjo.
- Fuente raw exacta.
- Esquema y granularidad.
- Reglas de limpieza.
- Presencia o ausencia de fuga temporal.

No se usaran como fuente productiva solo por existir. Podran compararse con el nuevo pipeline durante la auditoria.
