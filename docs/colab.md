# Leer y repetir la entrega en Colab

La copia académica se distribuye como `artifacts/entrega-academica.zip` fuera
de Git. La aplicación se instala con el README principal, sin notebooks.

## Leer los resultados sin ejecutar

1. Extrae el ZIP en una carpeta local.
2. Abre `notebooks/CornerScout_integrado_ejecutado.ipynb` en Jupyter o súbelo
   desde «Archivo → Subir notebook» en Google Colab.
3. Recorre las siete etapas y sus salidas. No necesitas montar Drive, instalar
   paquetes ni configurar una clave para leer el documento guardado.
4. Conserva la copia ejecutada de entrega antes de repetir el cálculo.

## Ejecutar una copia nueva

1. Sube `notebooks/CornerScout_integrado.ipynb` a Google Colab.
2. Lee la preparación inicial y ejecuta las celdas en orden.
3. Autoriza el montaje de tu Drive. La raíz habitual es
   `/content/drive/MyDrive/Corner_Scout/data`; conserva `raw`, `interim` y
   `processed` bajo ella. Si ya contiene una corrida, conserva su copia o elige
   una raíz nueva antes de regenerar derivados.
4. La primera preparación instala dependencias en el kernel. La ingesta obtiene
   una revisión fija de StatsBomb y conserva raw que ya esté completo.
5. Para repetir sin proveedor, deshabilita `ENABLE_LIVE_PROVIDER` antes de
   las etapas 06–07. No hace falta una clave para el respaldo determinista.
6. Para llamadas reales, configura `OPENAI_API_KEY` en los secretos de Colab,
   autoriza su acceso y escoge un modelo disponible compatible. No pegues la
   clave en código ni outputs. Las llamadas pueden generar cargos.
7. Al terminar, comprueba las conclusiones y contratos y descarga tu copia
   ejecutada para conservar la evidencia.

El notebook es autocontenido: no requiere clonar CornerScout ni importar sus
paquetes. Internet, espacio en Drive y disponibilidad del proveedor condicionan
una ejecución nueva; la salida guardada no demuestra que toda cuenta o runtime
pueda repetirla sin ajustes.

En la corrida entregada se aprobaron dos reportes reales y las pruebas del
agente. Ver [evidencia académica](academic-report.md) para las comprobaciones de
edición y conservación. Esto no prueba publicación de FastAPI ni Vercel.
