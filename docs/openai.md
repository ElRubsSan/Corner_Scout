# Reporte y agente

Solo FastAPI lee `OPENAI_API_KEY` y `OPENAI_MODEL`. Crear `.env` desde
`.env.example` y arrancar con `--env-file .env` como indica el README. Docker
Compose carga `.env` automáticamente. El navegador solo llama a nuestra API.

`backend/openai.py` construye una salida Pydantic de reporte, verifica citas y
cifras y usa fallback ante clave ausente, salida inválida o proveedor caído.
El modelo configurado debe aceptar Responses API y salida estructurada.

## Comportamiento del reporte

```mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Angular
    participant B as FastAPI
    participant P as Evidencia Python
    participant O as OpenAI
    U->>F: Solicita reporte
    F->>B: POST /report + sesión firmada
    B->>P: Calcula indicadores y citas permitidas
    P-->>B: ReportInput tipado
    B->>O: Structured Output
    O-->>B: Reporte estructurado
    B->>B: Verifica cifras, evidencia y lenguaje
    B-->>F: Reporte OpenAI o fallback identificado
```

OpenAI redacta; no calcula ventanas, porcentajes, clusters o probabilidades. El
reporte solo acepta evidencias incluidas en `ReportInput`. Números no respaldados,
citas desconocidas o afirmaciones prohibidas invalidan la salida y activan el
respaldo determinista.

## Comportamiento del agente

| Herramienta | Alcance |
|---|---|
| `obtener_historial` | IDs y cantidad de los ocho partidos estrictamente anteriores. |
| `obtener_perfil_corners` | Indicadores y referencias calculados por Python. |
| `consultar_evidencia` | Detalle de uno a doce IDs existentes. |

El modelo propone llamadas; FastAPI valida nombre, argumentos, presupuesto y
coincidencia con rival y corte antes de ejecutar. Las tools son de solo lectura
y no tienen acceso a web, SQL libre, archivos arbitrarios ni otras sesiones.

## Configurar y comprobar

Desde la raíz, instala `uv sync --locked --all-extras`. Crea `.env` con:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
CORNERSCOUT_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

Para empezar sin proveedor, deja la clave vacía. Para usarlo, introduce tu
clave en ese archivo local y escoge un modelo disponible en tu cuenta.
Arranca FastAPI con el comando del README y reinícialo después de editar `.env`.
Uvicorn sin `--env-file .env` solo recibe las variables de la terminal.

En Angular, crea un análisis y solicita Reporte o Asistente. La respuesta
identifica el modo utilizado. Un error de modelo, credenciales o verificación
puede activar fallback aunque exista una clave; consulta el motivo de la
respuesta HTTP en Swagger o la pestaña Network del navegador.

`backend/agent.py` registra tres herramientas: `obtener_historial`,
`obtener_perfil_corners`, `consultar_evidencia`. La sesión fija rival y corte.
Las cifras provienen de Python. Hay una única reparación final sin nuevas
tools; un segundo fallo activa fallback. Límites por sesión: cuatro tools,
cuatro turnos, 45 segundos y 12.000 tokens. No hay apuestas, web, SQL libre,
entrenamiento ni cambios de datos por el agente.

El proveedor recibe evidencia ya calculada. En el agente, Python inserta las
cifras y la lectura cronológica después de verificar el borrador; una respuesta
directa sin herramientas no sustituye la consulta requerida. El reporte
verifica las cifras contra las evidencias citadas. Ninguna de esas rutas
descarga datos ni permite al modelo producir SQL.

El reporte limita la salida a 2.500 tokens y usa timeout de 20 segundos por
solicitud al proveedor. El SDK admite un reintento: ese timeout no equivale a
un límite absoluto de duración de todo el endpoint.

La aplicación pública se ha comprobado con OpenAI. Los costes facturados se
consultan en el panel del proveedor; repetir llamadas reales puede generar
cargos. El modo visible en cada respuesta permite distinguir proveedor y
fallback sin inferirlo a partir del texto.

## Pruebas reproducibles sin cargos

Desde la raíz:

```powershell
uv run --all-extras pytest tests/test_openai.py tests/test_agent.py tests/test_agent_tools.py
```

Las pruebas usan proveedores simulados para verificar modos, alcance, citas,
cifras y reparación final. Para un smoke HTTP sin proveedor, arranca el backend
con clave vacía y ejecuta:

```powershell
uv run --extra api python scripts/smoke_deployment.py --base-url http://127.0.0.1:8000 --assistant-mode deterministic
```

`--assistant-mode openai` hace llamadas reales y exige ese modo. No se ejecuta
automáticamente como parte de la validación ordinaria. El modo por defecto
`skip` del smoke no llama al reporte ni al agente.
