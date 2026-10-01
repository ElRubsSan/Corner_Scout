# Metodología vigente de SCR-15

Regla implementada: `scr15-research-v1.2-first-limit` en `analytics/scr15.py`.
Contrato de salida: `03-scr15-v2`. El indicador describe córners ofensivos del
caso histórico LaLiga 2015/16; mide tiro, no gol ni eficacia causal.

```text
SCR-15 = córners evaluables con al menos un tiro válido en la secuencia
         ------------------------------------------------------------
                       total de córners evaluables
```

Cada córner contribuye una sola vez al numerador aunque origine varios tiros.
Los desconocidos se muestran por separado y no son negativos.

## Inicio y orden

La secuencia comienza en un evento `Pass` con `pass_type=Corner` normalizado.
Requiere tiempo finito, equipo conocido y equipo en posesión coincidente con
el ejecutor. Los eventos conservan el orden original por periodo e índice
StatsBomb; el tiempo mide la duración, no sustituye ese orden.

## Primer cierre

Se recorre la secuencia hasta el primero de estos límites:

1. Un evento posterior a los 15 segundos desde el córner.
2. Cambio de `possession_team` respecto del ejecutor.
3. Fin de periodo o evento `Half End`.
4. Un nuevo pase de córner.

Un tiro exactamente a los **15 segundos** entra si no hubo otro cierre antes.
Después de una pérdida de posesión la secuencia no se reabre, aunque el equipo
recupere el balón. Un cambio de ID `possession` con el mismo equipo se audita
y no cierra.

Un saque de banda, meta, libre u otra reanudación distinta de un nuevo córner
se registra para auditoría; no agrega un cierre automático. Este comportamiento
es parte de la regla versionada, no un supuesto pendiente de implementación.

## Reloj ambiguo y campos ausentes

El recorrido verifica la ambigüedad dentro de la ventana activa. Una regresión
que aparece después del primer cierre no invalida retrospectivamente la
secuencia. Un tiempo no finito, retroceso dentro de ventana o posesión
desconocida puede producir un resultado no evaluable; no se repara con datos
inventados. Si no se observa un cierre válido, el caso también es desconocido.

La geometría inválida limita el análisis espacial, pero por sí sola no elimina
una secuencia del denominador temporal.

## Tiro válido y xG

Un tiro atribuido es un evento `Shot` del equipo ejecutor, posterior al córner
según el índice original, entre cero y 15 segundos y anterior a cualquier otro
cierre. Ningún tiro puede atribuirse a dos córners.

La existencia de tiro no depende de tener xG. `xg_complete` exige una secuencia
válida y xG finito entre cero y uno para todos sus tiros. En secuencias válidas
sin tiros la suma es cero. El indicador descriptivo de xG utiliza solo los
córners evaluables con xG completo y muestra su cobertura:

```text
xG por córner = suma del xG de secuencias evaluables con xG completo
                -------------------------------------------------
                 córners evaluables con xG completo
```

El xG posterior nunca es predictor prepartido del córner que se evalúa.

## Trazabilidad y resultados del corpus

Cada fila conserva partido, evento e índice de córner, periodo, tiempo,
equipo, cierre y evento terminal, IDs de tiros y reinicios, tiempos de tiros,
etiqueta, completitud xG y versión de regla. Las exportaciones completas y
hashes se declaran en `data/interim/03_scr15/contract.json`.

| Comprobación | Resultado canónico |
|---|---:|
| Partidos | 380 |
| Eventos | 1.295.354 |
| Córners | 3.841 |
| Evaluables | 3.835 |
| Desconocidos por reloj ambiguo | 6 |
| Evaluables con tiro | 1.245 |
| Tiros compartidos | 0 |
| Cierres por nuevo córner | 29 |
| Reinicios auditados | 105 |

La tasa del corpus es aproximadamente **32,46 %**. Las cinco exclusiones
adicionales de una versión anterior se debían a retrocesos posteriores al
cierre: dejaron de ser falsos desconocidos al aplicar el primer límite.
La copia ejecutada de Colab se entrega por separado; el producto usa módulos
Python y no requiere notebooks.

## Reproducir y verificar

Desde la raíz, con dependencias y raw preparado:

```powershell
uv run --all-extras cornerscout clean
uv run --all-extras cornerscout scr15
uv run --all-extras pytest tests/test_sequences.py tests/test_full_regression.py
```

`clean` exige el contrato previo de ingesta. Las pruebas cubren la frontera
inclusiva, pérdida sin reapertura, mismo equipo con nuevo ID, nuevo córner y
regresiones antes/después del cierre. La regresión completa requiere los datos
locales correspondientes; ver el resultado de validación registrado.

Cambiar una regla científica requiere una solicitud explícita, versión nueva,
auditoría de diferencias y reconstrucción de las etapas dependientes.
