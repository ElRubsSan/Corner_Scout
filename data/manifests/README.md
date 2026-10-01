# Inventarios auxiliares

`raw.json` conserva un inventario de rutas relativas, bytes y SHA-256;
`quality-summary.json` conserva conteos agregados de una ejecución.
Son registros auxiliares de procedencia, no reemplazos de `contract.json`.
Sus cifras describen su propia corrida; no se actualizan manualmente para
simular una verificación nueva.

Los contratos efectivos se publican bajo `interim/01_ingestion`, `02_clean`,
`03_scr15`, `processed/04_features` y `05_modeling`. El pipeline y FastAPI
verifican esos contratos y sus archivos, no las plantillas de la fase inicial.
Las plantillas sin consumidores se retiraron del repositorio.

Un inventario versionado no debe contener eventos completos, secretos, enlaces
privados ni rutas personales. Los hashes se calculan desde los archivos:
no se modifican para ocultar diferencias. Ver
[contratos](../../contracts/README.md) y
[restauración](../../docs/data-restoration.md).
