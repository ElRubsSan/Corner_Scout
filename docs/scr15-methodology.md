# Metodologia provisional de SCR-15

## Definicion

```text
SCR-15 = corners ofensivos que generan al menos un tiro valido en 15 segundos
         ------------------------------------------------------------------
                         total de corners ofensivos
```

La unidad de observacion es un corner ofensivo. El resultado `shot_within_15s` es booleano y cada corner contribuye una sola vez al numerador, aunque su secuencia contenga mas de un tiro valido.

Implementacion actual `scr15-v0.2-team-inclusive`: si el reloj hace indeterminada una secuencia, target/xG son nulos, no falsos. SCR-15 y xG por corner se publican sobre corners evaluables, mostrando tambien totales y excluidos. En el dataset auditado son seis secuencias; la geometria invalida no excluye del KPI temporal, solo del mapa/clustering. Ver data-audit.md.

## Inicio

Una secuencia comienza en un evento StatsBomb que cumpla simultaneamente:

- El tipo de evento es `Pass`.
- `pass.type.name` es `Corner`, o su identificador equivalente confirmado por el contrato fuente.
- El equipo ejecutor es conocido.
- El periodo y el tiempo del evento se pueden ordenar.

Los corners que no cumplan los campos minimos no se reparan silenciosamente. Se excluyen o se conservan con una bandera de calidad segun el resultado de la auditoria.

## Orden de eventos

Se conservara el `index` original de StatsBomb. La ordenacion provisional dentro de un partido sera:

```text
period, index
```

El timestamp se usara para calcular tiempo transcurrido, no como unico criterio de orden. Los timestamps duplicados, regresivos o invalidos se registraran en calidad de datos.

## Cierre provisional

La observacion termina en el primer limite aplicable:

1. Han transcurrido mas de 15 segundos desde el corner.
2. `possession_team` deja de ser el equipo ejecutor.
3. Finaliza el periodo.

Un tiro a exactamente 15.000 segundos se incluye si ocurre antes de que `possession_team` deje de ser el equipo ejecutor o finalice el periodo.

Un cambio del identificador `possession` con el mismo `possession_team` se registra para auditoria, pero no cierra automaticamente la secuencia. Si falta `possession_team`, el caso se marca como problema de calidad; el identificador `possession` no se usa por si solo para inferir el cierre.

## Tiro valido

Un evento cuenta como tiro asociado cuando:

- Su tipo StatsBomb es `Shot`.
- Ocurre despues del evento de corner segun el orden original.
- Su tiempo transcurrido es mayor o igual que cero y menor o igual que 15 segundos.
- No se ha alcanzado antes ningun criterio de cierre.

Si `possession_team` cambia a otro equipo, la secuencia queda cerrada y no se reincorpora aunque el equipo ejecutor recupere rapidamente el balon.

## Reanudaciones a auditar

En esta fase, un saque de banda, saque de meta, tiro libre u otra reanudacion no cierra por si solo la secuencia. Se deben registrar, cuando aparezcan dentro de la ventana:

- Tipo de reanudacion.
- `event_id` e `index`.
- Segundos transcurridos desde el corner.
- Equipo del evento y equipo en posesion.
- Resultado SCR-15 que se obtendria con y sin ese cierre adicional.

La regla definitiva solo cambiara despues de revisar su frecuencia, coherencia con las posesiones StatsBomb y efecto sobre el KPI.

## Campos de trazabilidad

Cada secuencia futura debe conservar como minimo:

- `match_id`.
- `corner_event_id`.
- `corner_index`.
- `team_id`.
- `period`.
- Tiempo de inicio y fin.
- `sequence_end_reason`.
- `shot_within_15s`.
- Identificadores de tiros validos.
- xG de tiros validos.
- Reanudaciones observadas.
- Banderas de calidad.
- Version de esta regla.

## KPIs relacionados

El xG por corner es descriptivo:

```text
xG por corner = suma del StatsBomb xG de tiros validos atribuidos
                -------------------------------------------------
                          total de corners ofensivos
```

El xG posterior nunca sera una variable predictora prepartido.

## Auditorias obligatorias

- Comparar el tiempo derivado del timestamp con `minute` y `second`.
- Contar corners sin posesion, equipo, periodo o timestamp valido.
- Revisar cambios de posesion con el mismo equipo y cambios de equipo sin nuevo identificador.
- Cuantificar cambios de `possession` que conservan el mismo `possession_team` sin usarlos como cierre.
- Revisar manualmente una muestra positiva y una negativa de cada causa de cierre.
- Cuantificar reanudaciones dentro de 15 segundos.
- Probar corners cercanos al final de cada periodo.
- Verificar que ningun tiro atribuido pertenece a una posesion posterior.

## Estado

Contrato metodologico provisional `scr15-v0.1`. No debe presentarse como regla definitiva hasta ejecutar las auditorias anteriores sobre los datos restaurados.
