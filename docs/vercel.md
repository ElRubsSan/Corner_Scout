# Vercel gratuito: Angular y FastAPI en el mismo dominio

Configuración preparada en `vercel.json` de la raíz, siguiendo Services del
proyecto del profesor. **No se ha realizado un despliegue público**. Services
está en beta; comprobar que está disponible en la cuenta Hobby antes de importar.

## 1. Preparar los datos fuera de Git

Desde la raíz con las cuatro etapas canónicas locales:

```powershell
uv run --extra api python scripts/vercel_data.py package
```

Produce `artifacts/vercel-canonical-data.zip` ignorado por Git, con todos los
artefactos declarados y contratos `02`–`05`. No incluye raw ni runs. El comando
verifica los hashes y linaje y muestra SHA-256 para la configuración de build.

Para almacenamiento gratuito, crear una release de datos en GitHub y adjuntar
este ZIP como **asset de release**, no como archivo de código Git. Es una
publicación separada que debes efectuar desde GitHub; los artefactos serán
descargables públicamente. Usar un tag de datos fijo y no sustituir el asset
de una versión ya publicada. No subir el ZIP académico, `.env` ni raw.

Copiar la URL de descarga HTTPS del asset (`/releases/download/<tag>/...zip`).
Durante build, `scripts/vercel_data.py restore` descarga el ZIP, verifica su
SHA-256, restringe las rutas y vuelve a validar los contratos completos.
Runtime consulta la copia empaquetada: no descarga datos ni entrena por petición.

## 2. Secreto de sesiones

Genera un secreto nuevo localmente:

```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copia el resultado exclusivamente al dashboard. El backend firma el contexto
de cada análisis, y Angular lo guarda en `sessionStorage` y lo envía mediante
`X-CornerScout-Run`. Cada instancia reconstruye y verifica la ventana, ID y
fingerprint. No hay escritura de runs en modo serverless.

La sesión dura la pestaña del navegador. Abrir el enlace en otro navegador sin
ese contexto requiere crear otro análisis. Cambiar el secreto invalida las
sesiones anteriores; cambiar los artefactos incompatibles exige un análisis
nuevo. Los usuarios no aportan claves ni configuran servicios.

## 3. Importar desde Vercel

Primero guardar estos cambios en GitHub mediante revisión/commit/push.
En Vercel, Import Project → repositorio CornerScout → rama `main`:

- Plan **Hobby**, uso académico personal.
- **Root Directory: raíz (`./`)**, no `frontend`.
- Mantener overrides globales de build/install/output desactivados; cada
  servicio declara sus propios comandos.
- El backend usa raíz `.` para incluir el paquete `analytics`; su entrypoint
  es `backend.main:app`. El frontend usa raíz `frontend`.

Variables para el entorno Production (y Preview si deseas probarlo):

| Variable | Valor |
|---|---|
| `CORNERSCOUT_SAME_ORIGIN` | `1` |
| `CORNERSCOUT_STATELESS_RUNS` | `1` |
| `CORNERSCOUT_SESSION_SECRET` | Secreto generado, al menos 32 caracteres. |
| `CORNERSCOUT_DATA_ARCHIVE_URL` | URL HTTPS del asset de release. |
| `CORNERSCOUT_DATA_ARCHIVE_SHA256` | SHA-256 mostrado por el script. |
| `OPENAI_API_KEY` | Tu clave, configurada como sensitive y nunca en Git. |
| `OPENAI_MODEL` | Modelo disponible, por ejemplo `gpt-4.1-mini`. |

Dejar `CORNERSCOUT_API_BASE_URL` y `CORNERSCOUT_DATA_DIR` sin definir en esta
ruta. Angular usa `/api/v1` del mismo dominio, enrutado al backend; los datos
están en `data` dentro del paquete. No necesita CORS externo para esas llamadas.
El código frontend no utiliza las variables OpenAI ni las inserta en config.

El plan de alojamiento es gratuito dentro de cuotas; **OpenAI se factura en tu
cuenta**. La clave permite usar el proveedor sin pedir nada al profesor. Si falta
o falla, la interfaz identifica el respaldo determinista.

## 4. Validación pública pendiente

Después del deploy abrir `/api/v1/health`, `/api/v1/ready` y la aplicación.
Crear Barcelona con corte `2016-03-01`, recargar la pestaña y recorrer las seis
secciones. Solicitar reporte/agente y comprobar el modo real; no basta con que
el chat muestre una respuesta. Las llamadas reales consumen tokens.

Smoke desde la raíz:

```powershell
uv run --extra api python scripts/smoke_deployment.py --base-url https://<proyecto>.vercel.app
```

Agregar `--assistant-mode openai` solo al decidir probar el proveedor real.
El smoke admite el contexto firmado entre solicitudes. Verificar también una
URL directa Angular y los archivos de imágenes.

## Límites a comprobar en el build real

Medición local Linux de la imagen de servicio: dependencias instaladas ~317,72
MiB; datos completos ~146,63 MiB. La suma ~464,35 MiB es cercana al límite
estándar documentado de 500 MB para Python, antes de diferencias de empaquetado.
**No es una medición de bundle Vercel**: el build debe confirmar el tamaño final.
Se excluyen pruebas, documentación, frontend y raw del paquete Python; no se
eliminan archivos científicos para forzar el tamaño. Si se excede, detener y
revisar empaquetado/dependencias antes de contratar o activar opciones de pago.

La configuración actual permite 120 segundos por función. Las llamadas del
proveedor siguen sus presupuestos; las cuotas Hobby y OpenAI son independientes.
No hay garantía de disponibilidad permanente ni de reproducibilidad del build
hasta comprobar el despliegue real.
