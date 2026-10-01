# Preparar o restaurar los datos

CornerScout analiza **LaLiga 2015/16** (`competition_id=11`, `season_id=27`).
Los eventos, Parquet y modelos no están en Git. Una clonación del código necesita
preparar datos antes de que `/api/v1/ready` pueda responder `ready`.

Todos los comandos de esta guía se ejecutan desde la raíz del repositorio,
después de `uv sync --locked --all-extras`.

## Ruta A: construir desde la fuente pública

```powershell
uv run --extra pipeline cornerscout ingest
uv run --all-extras cornerscout build
uv run --all-extras cornerscout train
```

1. `ingest` descarga los archivos faltantes de una revisión fija de StatsBomb.
   Necesita Internet. No sobrescribe raw existente; un archivo incompatible
   debe investigarse, no editarse para que pase un hash.
2. `build` ejecuta limpieza, SCR-15 y variables en ese orden.
3. `train` evalúa los objetivos y publica la etapa `05_modeling`.

Son procesos offline; pueden tardar y requieren espacio para raw y derivados.
No existe una duración universal. Las etapas derivadas se vuelven a publicar al
reconstruirlas: si ya tienes un conjunto útil, conserva su copia antes de hacerlo.

## Ruta B: restaurar raw y reconstruir

Descarga la carpeta raw de tu copia de Drive y extráela conservando esta forma:

```text
data/raw/
  competitions.csv
  matches_laliga_2015_16.csv
  metadata_ingesta.json
  registro_ingesta.csv
  events/
    <match_id>.jsonl.gz          380 archivos
```

La ubicación académica habitual es `/content/drive/MyDrive/Corner_Scout/data/raw`.
No se necesita un enlace privado para instalar desde StatsBomb. No existe un
archivo de entrada llamado `matches.jsonl.gz`.

Ejecuta los tres comandos de la ruta A: `ingest` valida la copia existente y
publica su contrato; `build` y `train` producen los derivados. No renombres,
recomprimas ni normalices archivos dentro de raw. El adaptador acepta eventos
anidados y exportaciones aplanadas compatibles.

## Ruta C: restaurar artefactos ya preparados para servir

Necesitas una copia **completa y coherente de una misma cadena de etapas**.
No hay un enlace público de descarga de estos artefactos en el repositorio.
Si no dispones de esa copia, usa la ruta A.

1. Detén el backend y conserva cualquier conjunto local que quieras recuperar.
2. Extrae la copia en un directorio vacío, conservando las rutas siguientes.
3. Incluye cada `contract.json` y **todos** los archivos que declara, incluso
   particiones o artefactos que la interfaz no consulta directamente.
4. Usa el directorio restaurado como raíz de datos y arranca el backend.
5. Comprueba `/api/v1/ready`. Una respuesta 503 requiere revisar el error del
   backend y restaurar el conjunto coherente; no modificar los hashes.

```text
<raíz de datos>/
  interim/02_clean/contract.json
  interim/02_clean/...          todos sus archivos declarados
  interim/03_scr15/contract.json
  interim/03_scr15/...
  processed/04_features/contract.json
  processed/04_features/...
  processed/05_modeling/contract.json
  processed/05_modeling/...
  processed/runs/               escritura para análisis creados en la app
```

Para esta ruta de servicio no hace falta montar raw ni `01_ingestion`. Sí hacen
falta las cuatro capas `02`–`05`: FastAPI verifica versiones, hashes y linaje.
Restaurar solo `corners_engineered.parquet` no es suficiente.

## Elegir otra raíz de datos

En PowerShell, en cada terminal que vaya a usar esos datos:

```powershell
$env:CORNERSCOUT_DATA_DIR = "D:\CornerScout-data"
uv run --all-extras uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

La variable apunta al **padre** de `raw`, `interim` y `processed`, no a raw.
También puede definirse en `.env`; Uvicorn lo carga cuando se añade
`--env-file .env`. Los comandos del pipeline no cargan `.env` automáticamente:
para ellos configura la variable en la terminal. Reinicia el backend si cambias
la raíz o los artefactos.

Docker Compose usa los montajes de `./data` declarados en su archivo. Cambiar
esta variable en el host no cambia sus rutas de volumen; adapta esos montajes
si restauraste en otro lugar. Ver [despliegue](deployment.md).

## Comprobar el resultado

Con el backend activo, abre http://127.0.0.1:8000/api/v1/ready o ejecuta:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
```

Debe devolver `status: ready`. Después crea Barcelona con corte `2016-03-01`
desde Angular. Los conteos del corpus son 380 partidos, 1.295.354 eventos,
3.841 córners, 3.835 evaluables, seis excluidos y 1.245 con tiro; los de una
ventana de ocho partidos son menores y no deben confundirse con ellos.

## Qué se conserva fuera de Git

Raw, interim, processed, modelos, bases locales, runs y ZIP académicos. Las
40 etiquetas de `data/manual_labels/short_corner_review.csv` sí se preservan
como fuente exploratoria versionada; no se regeneran desde el proxy.
Los contratos efectivos están junto a sus etapas, no en plantillas antiguas.
