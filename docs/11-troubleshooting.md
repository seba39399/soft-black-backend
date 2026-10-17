# 11 — Troubleshooting

> Problemas frecuentes, en el orden en que suelen aparecer. Si resuelves uno nuevo, agrégalo aquí.

---

## Instalación y verify

### `uv sync` falla o usa otra versión de Python

`pyproject.toml` exige `>=3.13,<3.14`. `uv` descarga Python 3.13 si no lo tienes. Si tu red lo bloquea, instálalo (`winget install Python.Python.3.13`) y repite.

### `poe verify` falla en `requirements` o el diff muestra `src/requirements.txt` cambiado

Cambiaste dependencias en `pyproject.toml`. `poe verify` regenera el archivo; commitéalo junto con `pyproject.toml` y `uv.lock`.

### `mypy`: "Skipping analyzing boto3: missing library stubs"

Faltan los stubs de desarrollo: `uv sync` (incluye `boto3-stubs[dynamodb]`). Si usas otro servicio (S3, Secrets Manager), agrega su extra: `boto3-stubs[dynamodb,s3,secretsmanager]`.

### `SyntaxError` al importar `adapters.in…`

`in` es palabra reservada en Python. Las carpetas son `adapters/inbound/` y `adapters/outbound/` ([02 §1](./02-arquitectura.md#1-las-capas)).

### El test de arquitectura falla

Un módulo importa algo prohibido para su capa (por ejemplo `boto3` en `domain/`). Mueve ese código al adaptador correspondiente ([02 §3](./02-arquitectura.md#3-reglas-por-capa)).

### El test de contrato falla

| Mensaje | Causa |
|---|---|
| `test_mismas_rutas` | Hay una ruta en el código que no está en `openapi.yaml`, o al revés |
| `test_misma_forma` con `None == {...}` | El handler devuelve `dict`: devuelve un modelo `ApiModel` |
| `test_misma_forma` con campos distintos | Nombres de campos o query params distintos entre el código y el YAML (revisa camelCase) |

---

## Build y despliegue

### `sam build`: "Binary validation failed for python, searched for python3.13"

SAM necesita Python 3.13 instalado y en el PATH para compilar sin contenedor. Instálalo o usa `sam build --use-container` (requiere Docker).

### La Lambda falla con `No module named 'pydantic_core._pydantic_core'`

Se subió el binario de otra plataforma (por ejemplo, un `pip install` manual en Windows). Despliega **siempre** con `sam build` (que baja los wheels `aarch64`) o con `--use-container`. Nunca copies `site-packages` de tu máquina.

### `sam deploy` despliega en la cuenta equivocada

Verifica el perfil: `aws sts get-caller-identity --profile soft-black-frontend-prod`. El perfil sale de `samconfig.toml` según `--config-env`. Nunca despliegues sin `--config-env`.

---

## Autenticación

### Todo responde 401 `{"message":"Unauthorized"}`

Es el authorizer de API Gateway (la Lambda no llegó a ejecutarse):

- ¿El header es `Authorization: Bearer <token>`, con "Bearer"?
- ¿Es el **access token** (no el id token)?
- ¿El token es del User Pool **de este entorno**? Un token de `dev` no sirve en `prod`.
- ¿El `client_id` del token está en `CognitoClientIds` de `samconfig.toml`?
- ¿El token expiró? Dura 1 h por defecto; el frontend lo renueva solo.

### 403 `FORBIDDEN` con un usuario que debería tener acceso

- ¿El recurso está en `RESOURCE_GROUPS` con el grupo correcto?
- ¿El grupo existe con **exactamente** ese nombre en el User Pool de **este** entorno?
- ¿El usuario volvió a iniciar sesión después de que lo agregaran al grupo? Los grupos viajan en el token.
- Revisa qué grupos ve el backend: `GET /v1/me/permissions`.

### Los grupos llegan raros (`["[admin", "ventas]"]`)

Alguien parseó `cognito:groups` sin `parse_groups`. En HTTP API llegan como texto `"[admin ventas]"` ([03 §3](./03-autenticacion-autorizacion.md#3-identidad-y-grupos)).

---

## CORS y frontend

### Error de CORS en el navegador

- ¿El origen exacto del frontend (protocolo, dominio y puerto, sin barra final) está en `AllowedOrigins` de ese entorno?
- ¿Redesplegaste después de cambiarlo?
- Un 401 del authorizer **también** puede verse como error de CORS si el origen no está permitido: arregla el origen primero.

### El frontend recibe 404 en una ruta que existe en el código

Falta el `Event` de esa ruta en la función del dominio en `template.yaml` ([05 §4](./05-infraestructura-sam.md#4-agregar-la-función-de-un-dominio)).

### El frontend dice "No se pudo conectar con el servidor" pero la Lambda terminó bien

La Lambda tardó más de 15 s (el corte del frontend). Baja el tiempo (índices, menos datos, más memoria) o pasa el proceso a asíncrono ([05 §6](./05-infraestructura-sam.md#6-timeouts-y-memoria)).
