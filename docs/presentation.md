# Guion de presentacion y video

**0:00-0:35 - Problema.** «CornerScout organiza evidencia de los ocho partidos previos para preparar la defensa de corners. El caso es LaLiga 2015/16 y no representa informacion actual.»

**0:35-1:15 - Datos.** «StatsBomb Open Data aporta 380 partidos, 1,295,354 eventos y 3,841 corners. Hay 3,835 secuencias evaluables, 6 ambiguas excluidas y 1,245 con tiro.» Mostrar contratos y calidad, no raw.

**1:15-2:00 - SCR-15.** «La secuencia cierra por el primero de cuatro limites: 15 segundos, cambio del equipo en posesion, fin de periodo o nuevo corner. Los cambios de ID con el mismo equipo y otras reanudaciones se auditan.» Aclarar la frontera inclusiva de 15 segundos.

**2:00-2:40 - Pipeline y patrones.** «La logica de los notebooks `01`-`07` ya esta extraida a modulos Python. K-Means se fijo con datos predesarrollo, describe destinos y nunca entra como predictor.» No llamar jugada ensayada a un cluster.

**2:40-3:25 - Modelos.** «La evaluacion temporal decidio `scr15=league_reference`, `short_direct=candidate`, `delivery_zone=not_modelled` y `corner_count=candidate`. El periodo final no decide ganadores.» Mostrar evidencia, no garantias causales.

**3:25-4:15 - Reporte y agente.** «OpenAI se invoca exclusivamente desde FastAPI con salidas estructuradas. La clave nunca llega a Angular; falta de clave, fallo o salida invalida activa fallback determinista. El agente solo tiene tres tools de lectura.» No afirmar una llamada real a OpenAI; identificar el fallback si es lo mostrado.

**4:15-5:00 - Arquitectura y cierre.** «FastAPI verifica contratos, hashes y linaje `02`-`05`; DuckDB hace consultas controladas y Angular consume OpenAPI. Python calculo toda la evidencia.» Cerrar con credito StatsBomb y decir que Vercel y Docker no se han validado externamente.

Usar cinco diapositivas: problema, datos/SCR-15, pipeline/patrones, modelos, arquitectura/limites. No grabar secretos. Incorporar el logo oficial StatsBomb antes de publicar.
