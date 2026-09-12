# Ejecucion reproducible en Google Colab

## Estado de verificacion

Los cinco notebooks nuevos se ejecutaron localmente mediante nbclient y entorno uv. No se ha iniciado una sesion remota de Colab en esta ejecucion; no se afirma validacion remota ni ausencia de warnings en un runtime no probado. La ultima version original Third_Man_Analytics_Ingesta_de_Datos.ipynb permanece intacta, ignorada por Git.

## Flujo recomendado: entorno uv aislado

1. Abrir un runtime CPU de Colab y clonar la revision de codigo que se va a evaluar (no una rama cambiante). Los commits locales deben haberse publicado o cargarse como un archivo de codigo sin datos ni secretos.
2. Instalar uv en el runtime con `%pip install uv`. Reinicio solo si Colab lo solicita.
3. Desde el directorio raiz del checkout ejecutar:

```text
uv sync --locked --all-extras
uv run cornerscout ingest
uv run python -m analytics.audit
uv run cornerscout build
uv run --extra ml cornerscout train
uv run --all-extras pytest
uv run --all-extras python scripts/notebooks.py --execute --through 5
```

En una celda Colab se pueden ejecutar comandos con `!uv ...` y establecer el directorio mediante `%cd` al checkout. El entorno aislado evita depender de las versiones preinstaladas en el kernel de Colab. No ocultar warnings con filtros globales: registrar y corregir cada aviso observado.

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

## Entregables que comprobar

- quality.json passed=true, 380 partidos, 20 equipos; revisar exclusiones de secuencias y mapas.
- raw.json con hashes de archivos; conservarlo junto a la revision de codigo usada.
- Cinco notebooks ejecutados en data/processed/executed_notebooks.
- model-evaluation.json, calibration.png y artefactos locales.
- Pruebas completas sin errores; registrar warnings exactos del runtime.

Para entrega academica descargar notebooks ejecutados como evidencia privada. No incluir tablas raw, credenciales ni rutas de usuario en los notebooks versionados. La prueba E2E de navegador se realiza en el entorno local con Node/Chromium; no es requisito ejecutar Angular dentro de Colab.
