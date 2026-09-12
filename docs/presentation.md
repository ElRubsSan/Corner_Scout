# Guion de presentacion y video (maximo cinco minutos)

**0:00–0:35 — Problema.** «Un cuerpo tecnico necesita entender los corners ofensivos de su proximo rival. CornerScout organiza evidencia de sus ocho partidos anteriores. Usamos LaLiga 2015/16 como caso academico historico.»

**0:35–1:15 — Datos.** «StatsBomb Open Data aporta 380 partidos. Auditamos cobertura, IDs, reloj y coordenadas. Las secuencias ambiguas se identifican y no se tratan como fracasos de corner.» Mostrar manifiesto y calidad, no raw completo.

**1:15–2:00 — Metodologia.** «SCR-15 mide si hay un tiro en los 15 segundos siguientes, antes de perder el equipo en posesion o acabar el periodo. Los cambios de ID con el mismo equipo y las reanudaciones se auditan.» Mostrar seleccion y KPIs reales en pantalla.

**2:00–2:50 — Patrones.** Mostrar mapa y K-Means. «Los destinos representan pases. Un cluster es recurrente, no demuestra una jugada ensayada. Cada ejemplo conserva identificador.»

**2:50–3:35 — Modelos.** «Evaluamos tasa base, regresion logistica y Random Forest con bloques temporales completos por partido. No hubo mejora consistente sobre baseline; por eso no desplegamos un modelo mas complejo sin evidencia.» Mostrar Brier y calibracion.

**3:35–4:20 — Reporte.** Mostrar plan y generar. «Gemini solo recibe resultados estructurados validados. Si falla o falta cuota, una plantilla mantiene la evidencia disponible. La clave nunca llega a Angular.» Si se muestra fallback, decirlo explicitamente.

**4:20–5:00 — Arquitectura y cierre.** «Angular standalone consume OpenAPI de FastAPI. Python calcula; el LLM redacta. Hay pruebas de secuencias, API y navegador con datos reales. Vercel esta preparado y quedan validaciones externas, sin presentar datos historicos como actuales.» Cerrar con credito StatsBomb y limitaciones.

Usar cinco diapositivas: problema, datos/regla, demo, modelos, arquitectura/limites. No leer numeros inventados; tomar valores de la ejecucion visible. No grabar terminales con variables secretas. Incorporar logo oficial StatsBomb del media pack antes de publicar el video.
