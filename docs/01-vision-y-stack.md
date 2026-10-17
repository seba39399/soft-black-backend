# 01 — Visión y stack

> Qué hace el backend, con qué está hecho y qué deja fuera a propósito.

---

## 1. Qué hace

Una **API HTTP serverless** que alimenta los dashboards del frontend:

- **Autentica** cada request con el token de Cognito del entorno. Lo hace API Gateway antes de invocar la Lambda.
- **Autoriza** por grupo de Cognito: cada usuario solo ve los recursos (dashboards) que su grupo tiene permitidos. Es la **última línea de defensa**: el frontend oculta menús, pero la seguridad de los datos está aquí.
- **Informa los permisos** al frontend con `GET /v1/me/permissions`, para que el menú se arme desde una sola fuente.
- **Lee y escribe datos** de varias fuentes (DynamoDB, bases SQL, S3…) sin que el dominio sepa cuál es.
- **Cumple un contrato** (`contrato/openapi.yaml`) que el frontend consume y que un test verifica.

---

## 2. Stack

| Capa | Tecnología | Versión | Notas |
|---|---|---|---|
| Lenguaje | **Python** | 3.13 | Tipado estricto (`mypy --strict`) |
| Infraestructura | **AWS SAM** | CLI ≥ 1.166 | `template.yaml` + `samconfig.toml` |
| Cómputo | **AWS Lambda** | `python3.13`, `arm64` | Una función por dominio |
| API | **API Gateway HTTP API** | — | Authorizer JWT de Cognito nativo |
| Toolkit Lambda | **Powertools for AWS Lambda (Python)** | 3.35.0 | Router, validación, logging, OpenAPI |
| Validación | **pydantic** | 2.13.5 | Modelos de entrada y salida |
| Datos | DynamoDB, SQL (RDS/Aurora vía RDS Proxy), S3, Athena | — | Cada uno como adaptador ([06](./06-fuentes-de-datos.md)) |
| Dependencias | **uv** | — | `pyproject.toml` + `uv.lock` |
| Calidad | `ruff`, `mypy`, `pytest`, `moto`, `poethepoet` | fijadas en `pyproject.toml` | `uv run poe verify` |

### Qué es Powertools y qué usamos

Librería **open source de AWS** con las utilidades que todo backend en Lambda termina escribiendo a mano. Se usa **solo en `adapters/inbound/`**:

| Pieza | Uso aquí |
|---|---|
| `APIGatewayHttpResolver` (Event Handler) | Router tipo FastAPI: una Lambda atiende todas las rutas de un dominio |
| `enable_validation=True` | Valida query, path y body con los tipos de la función y genera el OpenAPI de las rutas |
| `Logger` | Logs JSON con `request_id`, cold start y función |
| `Parameters` | Lee y cachea secretos de SSM o Secrets Manager (credenciales SQL) |
| `Tracer` | *Opcional.* Trazas detalladas de X-Ray. Agrega `aws-xray-sdk` y `botocore` al paquete, que queda bastante más pesado. `Tracing: Active` en el template ya da la traza básica sin él |

### Reglas sobre dependencias

- Las de **runtime** (van a Lambda) están en `[project.dependencies]` con versión exacta. `boto3` **no** va: lo trae el runtime de Lambda.
- Las de **desarrollo** están en `[dependency-groups].dev`.
- `src/requirements.txt` **se genera** (`uv run poe requirements`); nunca se edita a mano. `sam build` lo usa.
- Cada dependencia nueva de runtime se justifica en el PR: aumenta el tamaño del paquete y el arranque en frío.

---

## 3. Principios

1. **Contrato primero** ([04](./04-contrato-api.md)).
2. **Seguro por defecto:** todas las rutas tienen authorizer; la excepción se declara ([03](./03-autenticacion-autorizacion.md)).
3. **Hexagonal:** el dominio no conoce AWS; las fuentes de datos se enchufan como adaptadores ([02](./02-arquitectura.md)).
4. **Mínimo privilegio:** IAM por función, solo lo que usa ([05](./05-infraestructura-sam.md)).
5. **Entornos aislados:** `dev` y `prod` en cuentas y User Pools distintos ([08](./08-entorno-y-despliegue.md)).
6. **Sin estado entre requests:** nada de caches de decisiones de autorización en memoria.

---

## 4. Fuera de alcance

- Emitir tokens o gestionar usuarios: lo hace Cognito, desde la consola.
- Renderizar UI.
- Procesos largos dentro de un request HTTP: todo endpoint responde en segundos. Lo largo va asíncrono ([05 §6](./05-infraestructura-sam.md#6-timeouts-y-memoria)).
