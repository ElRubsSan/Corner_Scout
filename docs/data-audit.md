# Calidad y auditoría de datos

La revisión fija de StatsBomb y el raw inmutable permiten rastrear cada evento.
El adaptador admite eventos anidados y exportaciones aplanadas. No se editan
relojes ni se imputan posiciones para forzar una secuencia válida.

## Conteos del corpus canónico

| Comprobación | Resultado |
|---|---:|
| Partidos / equipos | 380 / 20 |
| Eventos | 1.295.354 |
| Córners | 3.841 |
| Regresiones de reloj auditadas | 126 |
| Coordenadas fuera de rango auditadas | 25 |
| Secuencias evaluables / desconocidas | 3.835 / 6 |
| Córners evaluables con tiro | 1.245 |
| Tiros compartidos | 0 |

Son resultados del conjunto canónico, no de cada ventana de ocho partidos.
Las posiciones inválidas limitan mapas y clusters, pero no excluyen por sí
solas del KPI temporal. Solo las anomalías de la ventana activa invalidan la
secuencia; un retroceso después del cierre no cambia su resultado.

## Reconstrucción del contexto

La limpieza concilia los 380 marcadores y conserva auditorías de autogoles,
sustituciones y expulsiones. La corrida académica registró 29 autogoles,
2.190 sustituciones y 109 registros de expulsión: 106 en campo y tres fuera.
Una roja a un suplente no reduce los jugadores en campo. El contexto se
calcula antes de cada evento; no incorpora el gol o tarjeta del propio evento
como información previa.

## Dónde revisar la evidencia

- `interim/02_clean`: `data_quality`, `match_state_quality`, auditorías de
  autogoles, expulsiones y sustituciones, y particiones de eventos.
- `interim/03_scr15`: `scr15_quality_report`, `restart_audit`,
  `shared_shots_audit` y secuencias.
- `processed/04_features`: auditoría de las 40 etiquetas, comprobaciones de
  histórico y perturbación, alcance temporal y decisiones descriptivas.
- `processed/05_modeling`: métricas por ventana, gates y ganadores por objetivo.

Los nombres de archivo exactos, hashes y conteos están en `contract.json` de
cada etapa. En la app, Calidad muestra cobertura y límites de la sesión.
El inspector antiguo `analytics/audit.py` se retiró: dependía de una
representación anterior y no tenía consumidores vigentes.

## Ejecutar y comprobar

Desde la raíz, con dependencias instaladas como indica el README:

```powershell
uv run --extra pipeline cornerscout ingest
uv run --all-extras cornerscout build
uv run --all-extras cornerscout train
```

La publicación de una etapa exige coherencia con su entrada; una respuesta
503 de ready no se resuelve sustituyendo hashes. Restaurar el conjunto coherente
o reconstruir según [la guía de datos](data-restoration.md).
Las pruebas ejecutadas y sus omisiones están en [validación](validation.md).

Las 40 etiquetas de corto son exploratorias y asistidas, no validación humana
independiente. Los resultados históricos no prueban comportamiento actual ni
utilidad táctica universal. Para reglas específicas, consultar
[SCR-15](scr15-methodology.md) y [model card](model-card.md).
