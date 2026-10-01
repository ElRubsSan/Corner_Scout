# Entrega académica separada

La lógica ejecutable vive en `analytics/` y `backend/`. Los notebooks se
entregan aparte al profesor: se retiraron del repositorio de producto después
de preservar y verificar `artifacts/entrega-academica.zip` local, fuera de Git.
Ese ZIP no se descarga al clonar ni se necesita para instalar la aplicación.

## Contenido

- `notebooks/CornerScout_integrado_ejecutado.ipynb`: documento principal con
  salidas de las siete etapas y comentarios basados en sus resultados.
- `notebooks/CornerScout_integrado.ipynb`: fuente integrada sin las salidas de
  la corrida entregada.
- Fuentes individuales `01`–`07` y scripts de preparación académica.
- `README.md`: instrucciones de lectura y repetición en Colab.
- `verification.json`: hashes original/final y comprobación de conservación.
- `historical/`: registros y evaluación antiguos, identificados como históricos.
- `InverAI_Pre_deploy.ipynb`: referencia externa, no ejecución de CornerScout.

## Conservación de la corrida

Se añadieron **14 celdas Markdown** con lecturas de limpieza, secuencias,
variables, modelos y agente. Se comprobó igualdad completa de las **104 celdas
de código**: fuente, salidas, metadatos y contadores de ejecución intactos.
La celda final de código está vacía; las otras 103 tienen ejecución registrada.
No hay salidas de tipo error guardadas. La edición no volvió a ejecutar el
notebook ni hizo llamadas al proveedor.

La corrida registró dos reportes reales aprobados, catorce pruebas mock del
agente y tres consultas reales dentro de alcance. La solicitud fuera de alcance
se bloqueó sin llamar al proveedor. El modelo registrado pertenece al entorno
de esa corrida y no garantiza acceso futuro.

Para el método vigente consultar [SCR-15](scr15-methodology.md),
[modelos](model-card.md) y [arquitectura](architecture.md). Para repetir la
entrega, seguir [Colab](colab.md). La validación local del producto es
independiente y está en [validation.md](validation.md).
