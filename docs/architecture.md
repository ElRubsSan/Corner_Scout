# Arquitectura inicial

## Estado de la decision

Este documento describe la arquitectura aprobada para CornerScout. En la fase 1 solo existen la estructura y sus contratos; los componentes ejecutables se implementaran en fases posteriores.

## Principios

- El reporte descriptivo de ocho partidos es el primer producto util.
- SCR-15 debe ser determinista, probado y trazable antes de modelar.
- Los datos raw son inmutables y se conservan fuera de Git.
- Las transformaciones se ejecutan offline y producen Parquet consultable.
- Una consulta web no descarga datos ni entrena modelos.
- Toda cifra visible se puede rastrear a partidos, eventos y versiones de reglas.
- El LLM, si se agrega, solo redacta evidencia estructurada calculada previamente.

## Componentes previstos

```text
StatsBomb Open Data
        |
        v
Google Drive: /content/drive/MyDrive/Corner_Scout/data/raw
        |
        v
data/raw: restauracion local inmutable
        |
        v
analytics: validacion, secuencias, variables y KPIs
        |
        +--> data/interim
        |
        +--> data/processed + artifacts + manifiestos
        |
        v
backend: FastAPI y consultas DuckDB controladas
        |
        v
frontend: Angular y visualizaciones
```

## Responsabilidades

### Notebooks

Exploracion, auditoria visual y explicacion academica. No deben convertirse en la unica implementacion de una regla productiva. Los notebooks versionados deben estar sin credenciales, rutas personales ni salidas pesadas.

### Analytics

Futura libreria Python para validar contratos, normalizar eventos, seleccionar ventanas temporales, construir secuencias, calcular KPIs y producir artefactos reproducibles.

### Backend

Futura API FastAPI. Leera artefactos procesados mediante consultas fijas y parametros validados. No accedera a Google Drive en cada solicitud ni procesara los 380 JSONL en tiempo de respuesta.

### Frontend

Futura aplicacion Angular standalone. Consumira un cliente generado desde OpenAPI y dibujara la cancha desde coordenadas StatsBomb de 120 por 80.

### Reporting

La primera implementacion sera una plantilla determinista. Una integracion LLM posterior recibira exclusivamente objetos estructurados y debera conservar las referencias de evidencia.

## Capas de datos

### Raw

Archivos recibidos de Colab sin modificaciones. La restauracion debe comprobar checksum antes de procesarlos.

### Interim

Eventos normalizados, auditorias, corners extraidos y secuencias. Debe conservar campos fuente y banderas de calidad.

### Processed

Ventanas de ocho partidos, KPIs, agregados para vistas, patrones y, en fases posteriores, predicciones y reportes.

## Reproducibilidad

Todo dataset derivado debera registrar como minimo:

- `provider`.
- `competition_id` y `season_id`.
- `source_manifest_sha256`.
- `pipeline_version`.
- `schema_version`.
- `processed_at` en UTC.
- Reglas de inclusion y exclusion.

Una futura ejecucion de scouting debera quedar identificada por el rival, fecha de corte o partido objetivo, ocho `match_id` ordenados, version de datos y version de reglas.

## Orden aprobado

1. Restauracion y auditoria de datos.
2. Seleccion temporal de ocho partidos.
3. Extraccion de corners y validacion de SCR-15.
4. KPIs y reporte descriptivo.
5. Patrones recurrentes.
6. API y frontend.
7. Prediccion supervisada.
8. Integracion LLM opcional.
