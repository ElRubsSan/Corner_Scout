# Contratos de datos

Los contratos de esta carpeta describen entradas y entidades logicas antes de implementar Pydantic, Parquet o SQL.

## Documentos

- `raw-input.md`: estructura y campos minimos recibidos desde Colab.
- `processed-entities.md`: granularidad, claves y trazabilidad de las entidades previstas.

## Versionado

Los contratos comienzan en `v0.1` y pueden cambiar despues de auditar los archivos reales. Todo cambio futuro debe registrar:

- Version anterior y nueva.
- Motivo del cambio.
- Campos afectados.
- Compatibilidad con artefactos existentes.
- Migracion o reconstruccion requerida.

Los contratos ejecutables con Pydantic se agregaran junto con la capa analitica, no durante la fase 1.
