# 02 — Arquitectura

> Arquitectura **hexagonal** (puertos y adaptadores) en Python. El dominio no conoce AWS: la infraestructura entra por los bordes.

---

## 1. Las capas

```
   ENTRA (HTTP + Cognito)                               SALE (datos)
┌───────────────────────────┐                ┌──────────────────────────────┐
│ adapters/inbound/          │                │ adapters/outbound/            │
│  http/  (Powertools)       │                │  dynamodb/  sql/  s3/  athena/ │
│  auth/  (claims → identidad)│               │  (implementan los puertos)    │
└─────────────┬─────────────┘                └──────────────▲───────────────┘
              │ llama                                        │ implementa
              ▼                                              │
┌──────────────────────────────────────────────────────────────────────────┐
│ application/   use_cases/ (orquestan)   ports/ (Protocol: qué necesitan)  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ domain/   entidades y reglas puras · errores de negocio · SIN AWS/HTTP    │
└──────────────────────────────────────────────────────────────────────────┘
          shared/  → authz, paginación, modelo base de respuesta (sin dependencias de capas)
```

**Las dependencias apuntan hacia adentro.** El dominio no sabe que existe DynamoDB. El caso de uso pide un `IndicadorRepository` (puerto) y no sabe si detrás hay DynamoDB, Postgres o un CSV en S3.

> **Por qué `inbound` / `outbound` y no `in` / `out`:** `in` es palabra reservada en Python. `from adapters.in.http import x` es un `SyntaxError`.

---

## 2. Estructura

```
backend/
├── template.yaml                 # Infraestructura (SAM) — doc 05
├── samconfig.toml                # Parámetros por entorno — doc 08
├── pyproject.toml / uv.lock      # Dependencias y tareas (poe) — doc 07
├── docs/
│   └── contrato/openapi.yaml     # FUENTE DE VERDAD del contrato — doc 04
├── src/                          # = CodeUri de todas las funciones
│   ├── requirements.txt          # GENERADO por `poe requirements` (no editar)
│   ├── domain/
│   │   ├── errors.py             # DomainError, NotFoundError, ValidationError
│   │   └── <dominio>.py          # Entidades (dataclasses)
│   ├── application/
│   │   ├── ports/<dominio>.py    # Protocol: lo que el caso de uso necesita
│   │   └── use_cases/<caso>.py   # Un caso de uso por operación
│   ├── adapters/
│   │   ├── inbound/
│   │   │   ├── http/
│   │   │   │   ├── errors.py             # Excepciones → {"error","code"} + status
│   │   │   │   ├── platform_api.py       # /v1/health, /v1/me/permissions
│   │   │   │   └── <dominio>_api.py      # Una Lambda por dominio (router)
│   │   │   └── auth/identity.py          # claims verificados → Identity
│   │   └── outbound/
│   │       ├── dynamodb/                 # client.py + <dominio>_repository.py
│   │       ├── sql/                      # (cuando llegue la primera fuente SQL)
│   │       └── s3/                       # (ídem)
│   └── shared/
│       ├── authz.py              # RESOURCE_GROUPS: recurso → grupos (única fuente)
│       ├── api_model.py          # Base de respuestas: snake_case → JSON camelCase
│       └── pagination.py         # CursorPage, encode/decode_cursor, clamp_limit
└── tests/
    ├── conftest.py               # http_event(), tabla moto, contexto Lambda
    ├── unit/                     # dominio, casos de uso, shared, reglas de capas (sin AWS)
    ├── integration/              # handlers + adaptadores (moto)
    └── contract/                 # código vs contrato/openapi.yaml
```

---

## 3. Reglas por capa

| Capa | Puede importar | **No** puede importar |
|---|---|---|
| `domain/` | stdlib | `boto3`, `os`, Powertools, pydantic, `application`, `adapters`, `shared` |
| `application/` | `domain`, `shared.authz`, stdlib | `boto3`, `os`, Powertools, `adapters` |
| `adapters/outbound/` | `domain`, `boto3`, drivers | `adapters/inbound`, Powertools Event Handler |
| `adapters/inbound/` | todo lo anterior, Powertools, pydantic | — |
| `shared/` | stdlib, pydantic | `boto3`, Powertools, `domain`, `application`, `adapters` |

- **Casos de uso:** reciben sus puertos por constructor (inyección de dependencias). Nunca crean clientes de AWS.
- **Handlers:** identidad → autorización → validación → caso de uso → modelo de respuesta. Ni reglas de negocio ni SQL/DynamoDB.
- **Claves de datos** (`PK`/`SK`, tablas, rutas de S3): solo en su adaptador `outbound`.
- **Las reglas de esta tabla las verifica `tests/unit/test_architecture.py`:** un import prohibido rompe `poe verify`.
- **Composition root:** cada `<dominio>_api.py` arma sus casos de uso con los adaptadores concretos (función `build_use_case()`). Es el único lugar que conoce ambos lados.

---

## 4. Una Lambda por dominio

Cada dashboard (o dominio de negocio) tiene **un** archivo `adapters/inbound/http/<dominio>_api.py` con **un** `APIGatewayHttpResolver` y **una** función en `template.yaml`, que atiende todas sus rutas.

- **Ventajas:** menos arranques en frío, menos YAML, IAM por dominio (un dashboard de solo lectura no puede escribir) y los despliegues de un dominio no tocan a los demás.
- **Regla:** el nombre del dominio es el **recurso de autorización** y coincide con el feature y la ruta del frontend: `ventas` ↔ `/v1/ventas/...` ↔ `RESOURCE_GROUPS["ventas"]` ↔ `src/features/ventas` en el frontend.

---

## 5. Piezas compartidas (ya definidas)

**Identidad y autorización** (`adapters/inbound/auth/identity.py`):

```python
def parse_groups(raw: Any) -> tuple[str, ...]:
    """Normaliza `cognito:groups`.

    En HTTP API llega como string "[admin ventas]"; en tests o en otros
    orígenes puede llegar como lista. Los nombres de grupo no llevan espacios.
    """
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(str(g) for g in raw if str(g))
    if isinstance(raw, str):
        return tuple(g for g in raw.strip("[]").replace(",", " ").split() if g)
    return ()


def require_resource(app: APIGatewayHttpResolver, resource: str) -> Identity:
    """Devuelve la identidad o lanza ForbiddenError (→ 403)."""
    identity = current_identity(app)
    if not is_authorized(identity.groups, resource):
        raise ForbiddenError()
    return identity
```

**Paginación** (`shared/pagination.py`):

```python
class CursorPage[T](ApiModel):
    """Forma única de toda respuesta paginada: {"items": [...], "nextCursor": ...}."""

    items: list[T]
    next_cursor: str | None = None


def encode_cursor(position: dict[str, Any] | None) -> str | None:
    if not position:
        return None
    raw = json.dumps(position, separators=(",", ":"), default=str).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidCursorError() from exc
    if not isinstance(value, dict):
        raise InvalidCursorError()
    return value
```

**Respuestas en camelCase** (`shared/api_model.py`): los modelos se escriben en snake_case y el JSON sale en camelCase.

```python
"""Base de los modelos de respuesta: atributos en snake_case en Python,
JSON en camelCase (regla del contrato)."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
```

---

## 6. Agregar un endpoint (paso a paso)

> **Única copia de este procedimiento.** La skill `/nuevo-endpoint` enlaza aquí.

Ejemplo real del esqueleto: `GET /v1/dashboard_1/indicadores`, paginado, desde DynamoDB, solo para el grupo `admin`.

### Paso 1 — Contrato

Agrega la ruta y sus esquemas en `docs/contrato/openapi.yaml`, con `x-recurso: dashboard_1` ([04 §5](./04-contrato-api.md#5-cómo-se-escribe-un-endpoint-en-el-contrato)). Hasta que el contrato no esté acordado con el frontend, no se escribe código.

### Paso 2 — Permiso

En `src/shared/authz.py`:

```python
RESOURCE_GROUPS: dict[str, frozenset[str]] = {
    "dashboard_1": frozenset({"admin"}),
}
```

### Paso 3 — Dominio

```python
"""Entidades del dominio `dashboard_1` (ejemplo). Sin AWS, sin HTTP."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Indicador:
    id: str
    nombre: str
    valor: float
    actualizado_en: datetime
```

### Paso 4 — Puerto

```python
"""Puerto: lo que el caso de uso necesita de "algún" almacenamiento.

La implementación puede ser DynamoDB, SQL o S3: el caso de uso no lo sabe.
"""

from typing import Any, Protocol

from domain.indicadores import Indicador


class IndicadorRepository(Protocol):
    def list_page(
        self, limit: int, position: dict[str, Any] | None
    ) -> tuple[list[Indicador], dict[str, Any] | None]:
        """Devuelve una página y la posición para la siguiente (None = fin)."""
        ...
```

### Paso 5 — Caso de uso

```python
"""Caso de uso: listar indicadores paginados."""

from dataclasses import dataclass
from typing import Any

from application.ports.indicadores import IndicadorRepository
from domain.indicadores import Indicador


@dataclass(frozen=True)
class PaginaIndicadores:
    items: list[Indicador]
    next_position: dict[str, Any] | None


class ListarIndicadores:
    def __init__(self, repository: IndicadorRepository) -> None:
        self._repository = repository

    def ejecutar(self, limit: int, position: dict[str, Any] | None) -> PaginaIndicadores:
        items, next_position = self._repository.list_page(limit, position)
        return PaginaIndicadores(items=items, next_position=next_position)
```

### Paso 6 — Adaptador de salida

```python
"""Implementación DynamoDB del puerto IndicadorRepository (single-table).

Claves (solo este archivo las conoce):
  PK = "DASHBOARD_1"            SK = "INDICADOR#<id>"
"""

from datetime import datetime
from typing import Any

from boto3.dynamodb.conditions import Key

from domain.indicadores import Indicador

PK = "DASHBOARD_1"
SK_PREFIX = "INDICADOR#"


class DynamoIndicadorRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def list_page(
        self, limit: int, position: dict[str, Any] | None
    ) -> tuple[list[Indicador], dict[str, Any] | None]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(PK) & Key("SK").begins_with(SK_PREFIX),
            "Limit": limit,
        }
        if position:
            kwargs["ExclusiveStartKey"] = position
        response = self._table.query(**kwargs)
        items = [self._to_entity(item) for item in response.get("Items", [])]
        return items, response.get("LastEvaluatedKey")

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> Indicador:
        return Indicador(
            id=str(item["SK"]).removeprefix(SK_PREFIX),
            nombre=str(item["nombre"]),
            valor=float(item["valor"]),
            actualizado_en=datetime.fromisoformat(str(item["actualizadoEn"])),
        )
```

### Paso 7 — Handler (adaptador de entrada)

```python
"""Lambda del dominio `dashboard_1`: todas sus rutas en un solo resolver."""

from datetime import datetime
from typing import Annotated, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.utilities.typing import LambdaContext

from adapters.inbound.auth.identity import require_resource
from adapters.inbound.http.errors import register_error_handlers
from adapters.outbound.dynamodb.client import app_table
from adapters.outbound.dynamodb.indicadores_repository import DynamoIndicadorRepository
from application.use_cases.listar_indicadores import ListarIndicadores
from shared.api_model import ApiModel
from shared.pagination import MAX_LIMIT, CursorPage, clamp_limit, decode_cursor, encode_cursor

RESOURCE = "dashboard_1"

logger = Logger()
app = APIGatewayHttpResolver(enable_validation=True)
register_error_handlers(app)


class IndicadorOut(ApiModel):
    id: str
    nombre: str
    valor: float
    actualizado_en: datetime


def build_use_case() -> ListarIndicadores:
    return ListarIndicadores(DynamoIndicadorRepository(app_table()))


@app.get("/v1/dashboard_1/indicadores")
def listar_indicadores(
    limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> CursorPage[IndicadorOut]:
    require_resource(app, RESOURCE)
    pagina = build_use_case().ejecutar(clamp_limit(limit), decode_cursor(cursor))
    return CursorPage[IndicadorOut](
        items=[
            IndicadorOut(id=i.id, nombre=i.nombre, valor=i.valor, actualizado_en=i.actualizado_en)
            for i in pagina.items
        ],
        next_cursor=encode_cursor(pagina.next_position),
    )


@logger.inject_lambda_context(clear_state=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    return app.resolve(event, context)
```

### Paso 8 — Infraestructura

En `template.yaml`: una función por dominio, con IAM mínimo y sus rutas ([05 §4](./05-infraestructura-sam.md#4-agregar-la-función-de-un-dominio)).

```yaml
  Dashboard1Function:
    Type: AWS::Serverless::Function
    Properties:
      Handler: adapters.inbound.http.dashboard_1_api.handler
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref AppTable
      Events:
        ListarIndicadores:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/dashboard_1/indicadores
            Method: GET
```

### Paso 9 — Tests y verificación

- `tests/unit/`: el caso de uso con un repositorio falso.
- `tests/integration/`: el handler con moto (200 con cursor, 403 con otro grupo, 400 con `limit=0`). Ver [07 §6](./07-convenciones-y-testing.md#6-testing).
- `tests/contract/`: pasa sin tocarlo si el paso 1 y el código coinciden.
- `uv run poe verify`.

### Checklist

- [ ] Ruta en `contrato/openapi.yaml` con `x-recurso`, acordada con el frontend.
- [ ] Recurso en `RESOURCE_GROUPS` con los grupos correctos del User Pool **de cada entorno**.
- [ ] Entidad, puerto, caso de uso y adaptador en su capa.
- [ ] Handler que llama a `require_resource(app, RESOURCE)` y devuelve un modelo `ApiModel` (nunca `dict`).
- [ ] Función en `template.yaml` con IAM mínimo.
- [ ] Tests unitarios, de integración y de contrato.
- [ ] `uv run poe verify` en verde.

---

## 7. Antipatrones

- `boto3`, `os.environ` o Powertools dentro de `domain/` o `application/`.
- Un handler que arma consultas a DynamoDB o SQL.
- Devolver `dict` desde un handler: el contrato no puede verificarlo. Siempre un modelo `ApiModel`.
- Olvidar `require_resource`: el authorizer solo prueba que hay sesión, no que el grupo tenga acceso.
- Leer grupos o identidad de headers, query o body, en vez de los claims verificados.
- Claves de DynamoDB o nombres de tablas SQL fuera de su adaptador.
