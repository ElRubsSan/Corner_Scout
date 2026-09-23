# Ejecucion reproducible en Google Colab

## Estado de verificacion

Los cinco notebooks se adoptaron del trabajo del usuario en Google Colab/Drive el 2026-09-19. Sus originales exactos permanecen en `notebooks/prueba/`. Los canonicos `01` a `03` fueron corregidos y ejecutados en orden localmente sobre datos reales; `04` y `05` conservan todavia la linea historica. No se ha verificado una ejecucion integral desde un runtime limpio de Colab. Ver `notebooks/source-manifest.json`.

La implementacion y los artefactos actuales de la demo se mantienen separados hasta comprobar la equivalencia con la metodologia cientifica. Los ZIP de evidencia no se promueven automaticamente.

## Fase actual: fase B validada localmente

Desde la raiz, el comando siguiente valida el formato de los notebooks y registra sus hashes. No ejecuta ni reescribe celdas:

```text
uv run --all-extras python scripts/notebooks.py --through 5
```

La validacion local corregida se ejecuta con `uv run --all-extras python scripts/notebooks.py --execute --through 3`. Guarda copias ejecutadas fuera de Git y registra hashes de fuente y resultado. Reporta 380 partidos, 1,295,354 eventos, 3,841 corners, 3,835 evaluables y seis excluidos. No sustituye la prueba remota integral.

## Flujo objetivo en Colab

1. Abrir un runtime CPU de Colab y clonar la revision de codigo que se va a evaluar (no una rama cambiante). Los commits locales deben haberse publicado o cargarse como un archivo de codigo sin datos ni secretos.
2. Instalar uv en el runtime con `%pip install uv`. Reinicio solo si Colab lo solicita.
3. Montar Drive y definir o confirmar `CORNERSCOUT_DATA_DIR`. Los notebooks cientificos gestionan sus dependencias y contratos de etapa; no deben recibir artefactos de la demo como sustitutos silenciosos.
4. Ejecutar `01` a `05` en orden desde un runtime limpio cuando terminen las correcciones cientificas de cada etapa.
5. Registrar warnings, contratos, hashes y resultados exactos. No ocultar warnings globalmente.

El flujo productivo separado continua disponible para reproducir la demo existente:

```text
uv sync --locked --all-extras
uv run cornerscout ingest
uv run python -m analytics.audit
uv run cornerscout build
uv run --extra ml cornerscout train
uv run --all-extras pytest
```

## Restauracion desde Drive en vez de descargar

Montar Drive manualmente mediante la interfaz de Colab o `google.colab.drive.mount`. Establecer `CORNERSCOUT_DATA_DIR` en `/content/drive/MyDrive/Corner_Scout/data` (el directorio padre de raw). Debe contener:

```text
raw/competitions.csv
raw/matches_laliga_2015_16.csv
raw/metadata_ingesta.json
raw/registro_ingesta.csv
raw/events/<match_id>.jsonl.gz
```

Omitir ingest cuando la copia este completa. El adaptador reconoce eventos aplanados de statsbombpy y objetos anidados del proveedor. No mezclar exportaciones sin recalcular y revisar el manifiesto. No ejecutar el notebook original dentro del pipeline nuevo ni sobrescribirlo.

## Entregables cientificos que comprobar

- quality.json passed=true, 380 partidos, 20 equipos; revisar exclusiones de secuencias y mapas.
- raw.json con hashes de archivos; conservarlo junto a la revision de codigo usada.
- Contratos y hashes encadenados entre `02_clean`, `03_scr15`, `04_features` y `05_modeling`.
- Notebooks ejecutados en orden con contadores, outputs y conclusiones coherentes.
- Etiquetas humanas de corto preservadas y metodologia de revision documentada.
- Metricas y artefactos de modelacion distinguiendo desarrollo, evaluacion retrospectiva y reajuste final.
- Pruebas completas sin errores; warnings exactos del runtime registrados.

Para entrega academica, los notebooks ejecutados son la evidencia cientifica principal. No incluir datos raw, credenciales ni rutas personales. La prueba E2E de navegador se realiza aparte; Angular no sustituye la validacion cientifica ni necesita ejecutarse dentro de Colab.
