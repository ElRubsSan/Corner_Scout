# Imágenes de CornerScout

La aplicación incluye sus recursos visuales en `frontend/public/media/`; una
copia del repositorio puede compilar Angular sin ejecutar descargadores ni
extraer archivos adicionales.

## Cobertura de la muestra histórica

- **20/20 escudos** en `media/clubs/<team_id>.png`.
- **202/202 cobradores de córner** con retrato en
  `media/players/<player_id>.webp` (256 × 256 píxeles).
- El inventario conserva las **539 identidades de jugadores** de LaLiga
  2015/16, pero los retratos se limitan a quienes cobraron al menos un córner.
  No se utilizan fotografías de los demás jugadores en la interfaz.

La asociación entre un archivo y un jugador se realiza por `player_id` y nombre
de StatsBomb, nunca por semejanza de nombres ni por una URL recibida del
navegador. Los 202 IDs se cotejan con `corners_engineered` verificado mediante
`scripts/check_visual_coverage.py --require-complete` y
`tests/test_visual_inventory.py`.

## Registro de los archivos

- `docs/player-photo-sources.json`: 119 fotografías con fuente individual.
- `docs/manual-player-photo-sources.json`: seis fotografías identificadas
  manualmente con fuente individual.
- `docs/user-taker-photo-sources.json`: 75 fotografías aportadas al proyecto,
  con ID, nombre, dimensiones y SHA-256 del JPEG original; no se atribuye una
  fuente externa que no se registró.
- Los otros dos cobradores, Beñat Etxebarria y Roberto Trashorras, conservan
  sus fotografías y créditos individuales en esta documentación y en la
  página de créditos.
- `docs/club-badge-sources.json`: URLs de origen de los 20 escudos.

| StatsBomb ID | Jugador | Archivo de origen y autor | Archivo local |
|---|---|---|---|
| 6396 | Beñat Etxebarria Urkiaga | [Beñat Etxebarria, 2012](https://commons.wikimedia.org/wiki/File:Benat_Etxebarria.jpg), Memorino | `media/players/6396.webp` |
| 26848 | Roberto Trashorras Gayoso | [Roberto Trashorras, 2009](https://commons.wikimedia.org/wiki/File:Roberto_Trashorras.jpg), Adrián Estévez (Estevoaei) | `media/players/26848.webp` |

Las fotos identifican a las personas; pueden ser de un año diferente de
2015/16. La identidad visual no altera datos, contratos ni modelos. Para
comprobar qué se distribuye:

```powershell
uv run --extra api python scripts/check_visual_coverage.py --require-complete
```

Ejecutar desde la raíz con dependencias instaladas y las etapas canónicas
disponibles. El script comprueba los IDs contra los artefactos verificados;
no descarga fotos. El build solo utiliza archivos que ya están en el proyecto.

Para actualizar el inventario después de un cambio deliberado de recursos:

```powershell
uv run --extra api python scripts/build_visual_inventory.py
```

Revisar el diff de `docs/visual-inventory.json` y los archivos generados de
frontend, y conservar las fuentes individuales. Las capturas del README se
generan desde el recorrido E2E; no forman parte del inventario de identidades.
