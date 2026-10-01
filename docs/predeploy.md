# Cierre previo al despliegue

## Decisiones de limpieza

- Los notebooks y sus cinco scripts auxiliares se trasladaron a la entrega
  académica local. El ejecutado recibió 14 comentarios de resultados; sus
  104 celdas de código completas se conservaron sin cambios.
- Se retiraron el manifiesto de ejecución de notebooks y las plantillas de
  manifiestos de la fase inicial. Los contratos de etapa son la autoridad.
- Se retiró `docs/model-evaluation.json` de `v0.3`; tiene copia histórica en
  la entrega. La gráfica de calibración anterior se retiró del seguimiento
  Git y del directorio de documentos después de archivarla en el ZIP.
- Se retiró `analytics.zip` después de preservar su copia histórica en el ZIP.
  `artifacts/v0.3/` permanece como histórico local ignorado; no se sirve ni monta
  como artefacto del producto.
- Se retiró `analytics/audit.py`, sin consumidores y dependiente de la
  representación antigua de eventos. La auditoría canónica vive en pipeline.
- Se eliminaron dependencias Jupyter del extra `dev` del producto y se
  actualizó `uv.lock`. La entrega mantiene su instalación autocontenida.
- Se corrigió la importación de scripts en pytest con `pythonpath = ["."]`.
  Codegen actualizó únicamente la dependencia transitiva `brace-expansion`
  de 2.1.4 a 2.1.7 tras el aviso real de npm; se regeneró y verificó el cliente.
- Se conservaron los cambios de producto existentes. No se alteraron reglas
  SCR-15, selección temporal, modelos ni etiquetas humanas.

## Qué se conserva

Pipeline Python, FastAPI, Angular, contrato OpenAPI y cliente generado, tests,
lockfiles, imágenes y fuentes, inventario visual, codegen y smoke Docker.
Raw y las cuatro etapas canónicas locales no se borraron ni regeneraron.
Los scripts de inventario siguen disponibles para mantenimiento, aunque no
se ejecutan durante build.

## Documentación

Las instrucciones parten de herramientas e instalación, distinguen construir
datos de restaurar una copia coherente, explican `.env` y configuración pública,
puertos, arranque, pruebas y diagnósticos. Las guías de métodos reflejan la
implementación vigente. Los resultados probados están en [validación](validation.md).

La nueva corrida aprobó 124 pruebas Python (dos integraciones pesadas omitidas),
cuatro E2E, typecheck/build, cobertura visual, OpenAPI y smoke de la imagen Docker
nueva sin proveedor. No hay despliegue público validado.

## Datos y operación pendientes

- No hay distribución pública de los artefactos preparados; una clonación
  nueva debe construirlos o recibir una copia completa.
- No hay backend ni frontend público validado. Vercel está configurado.
- Se debe elegir alojamiento, almacenamiento, backups y conservación de runs
  antes de publicar.
- La calidad táctica requiere lectura humana y vídeo; una temporada histórica
  no valida predicciones actuales ni comportamiento causal.

## Siguiente fase

Seguir [despliegue](deployment.md): backend HTTPS y datos persistentes primero,
frontend Vercel después, CORS y recorridos públicos al final. No se hicieron
commits, push ni despliegues durante este cierre.
