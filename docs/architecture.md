# Arquitectura inicial

## Estado de la decision

Este documento describe la arquitectura implementada localmente para CornerScout. Las fases de datos, modelos, backend, Gemini y Angular cuentan con codigo y pruebas. Vercel y contenedor backend estan configurados, sin despliegue externo.

## Principios

- El reporte descriptivo de ocho partidos es el primer producto util.
- SCR-15 debe ser determinista, probado y trazable antes de modelar.
- Los datos raw son inmutables y se conservan fuera de Git.
- Las transformaciones se ejecutan offline y producen Parquet consultable.
- Una consulta web no descarga datos ni entrena modelos.
- Toda cifra visible se puede rastrear a partidos, eventos y versiones de reglas.
- El LLM es obligatorio como modulo backend; solo redacta evidencia estructurada validada. Gemini usa Structured Outputs/Pydantic con plantilla de respaldo automatica.

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
frontend: Angular standalone y visualizaciones (Vercel)
```

## Responsabilidades

### Notebooks

Exploracion, auditoria visual y explicacion academica. No deben convertirse en la unica implementacion de una regla productiva. Los notebooks versionados deben estar sin credenciales, rutas personales ni salidas pesadas.

### Analytics

Futura libreria Python para validar contratos, normalizar eventos, seleccionar ventanas temporales, construir secuencias, calcular KPIs y producir artefactos reproducibles.

### Backend

FastAPI expone contratos OpenAPI consumidos mediante openapi-fetch y tipos generados. Consulta Parquet con DuckDB y parametros validados, sin Google Drive en solicitudes. El nombre exacto del rival es clave de seleccion; match_id conserva el ID del proveedor. Runs reproducibles se guardan en processed/runs. Las claves Gemini solo existen en backend.

### Frontend

Angular standalone obligatorio, desplegable exclusivamente en Vercel. Dibuja cancha SVG desde coordenadas StatsBomb 120 por 80. Tailwind y CSS para layout. Streamlit, Gradio, Tableau y Power BI no son interfaces finales permitidas. tools/codegen aisla el generador TS5 de Angular TS6.

### Reporting

La plantilla determinista es respaldo, no reemplazo de la integracion obligatoria. FastAPI recibe la solicitud de Angular, muestra el plan mediante endpoint previo, recopila ReportInput validado (rival, partidos, KPIs, clusters, probabilidad baseline, evidencia y limitaciones) y llama Gemini. Structured Outputs se valida con Pydantic; errores, cuota, timeout o clave ausente activan plantilla. La UI muestra modo y motivo. Ninguna llamada Gemini sale de Angular.

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
8. Integracion Gemini obligatoria con fallback probado.
9. Build Angular, comprobacion de tipos y E2E con datos reales.
10. Documentacion academica y configuracion de Vercel/contenedor.

Los resultados observados y las exclusiones se documentan en data-audit.md. Los candidatos supervisados no superaron consistentemente baseline; model-card.md documenta la decision de no promocionarlos. El reporte descriptivo sigue siendo el centro del producto.
