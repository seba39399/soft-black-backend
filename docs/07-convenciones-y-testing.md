# 07 — Convenciones y testing

> Reglas para todo el código nuevo. Todo lo verificable está en `uv run poe verify`.

---

## 1. Herramientas (fijadas)

| Para | Herramienta | Comando |
|---|---|---|
| Entorno y dependencias | **uv** (`pyproject.toml` + `uv.lock`) | `uv sync` |
| Lint e imports | **ruff** | `uv run poe lint` |
| Formato | **ruff format** | `uv run poe format` |
| Tipos | **mypy --strict** | `uv run poe typecheck` |
| Tests | **pytest** + **moto** | `uv run poe test` |
| `requirements.txt` para SAM | `uv export` | `uv run poe requirements` |
| Template | `sam validate --lint` | `uv run poe validate` |
| **Todo lo anterior** | **poethepoet** | **`uv run poe verify`** |

`poe` corre igual en PowerShell, macOS y Linux: no hace falta `make`.

### `pyproject.toml`

```toml
[project]
name = "soft-black-frontend-api"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
# Dependencias de RUNTIME (van a Lambda). boto3 NO: lo trae el runtime.
dependencies = [
  "aws-lambda-powertools==3.35.0",
  "pydantic==2.13.5",
]

[dependency-groups]
# Solo desarrollo y tests (no se despliegan).
dev = [
  "boto3==1.43.100",
  "boto3-stubs[dynamodb]==1.43.100",
  "moto[dynamodb]==5.2.3",
  "poethepoet==0.48.0",
  "mypy==2.3.1",
  "pytest==9.1.1",
  "pyyaml==6.0.3",
  "ruff==0.16.8",
]

# Tareas: uv run poe <tarea>   (funciona igual en PowerShell, macOS y Linux)
[tool.poe.tasks]
lint = "ruff check src tests"
format = "ruff format src tests"
format-check = "ruff format --check src tests"
typecheck = "mypy src"
test = "pytest"
requirements = "uv export --no-dev --no-hashes --no-emit-project -q -o src/requirements.txt"
validate = "sam validate --lint"
verify = ["requirements", "lint", "format-check", "typecheck", "test", "validate"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM", "RUF"]

[tool.mypy]
python_version = "3.13"
strict = true
mypy_path = "src"
explicit_package_bases = true

# Los decoradores de exception_handler de Powertools no están tipados.
[[tool.mypy.overrides]]
module = "adapters.inbound.http.errors"
disallow_untyped_decorators = false
```

> El override de mypy existe porque los decoradores `exception_handler` de Powertools no están tipados. Es la única excepción a `strict`.

---

## 2. Python

- **Python 3.13.** Sintaxis moderna: `X | None`, genéricos PEP 695 (`class CursorPage[T]`), `match` cuando aclare.
- Anotaciones en **todo** (mypy strict). `Any` solo en fronteras (eventos crudos, respuestas de boto3) y se acota enseguida.
- **Entidades de dominio:** `@dataclass(frozen=True)`. **Modelos HTTP** (entrada/salida): pydantic, heredando de `ApiModel`.
- Nombres: módulos y funciones `snake_case`, clases `PascalCase`, constantes `UPPER_SNAKE_CASE`. El **dominio** puede usar español (`Indicador`, `listar_indicadores`), igual que el frontend.
- Línea máxima: 100.

---

## 3. Handlers (Powertools)

- Un `APIGatewayHttpResolver(enable_validation=True)` por módulo `*_api.py`, con `register_error_handlers(app)`.
- Parámetros tipados con `Annotated[..., Query(...)]` / `Path(...)` / `Body(...)`: Powertools valida y responde 400.
- **Siempre** devolver un modelo `ApiModel` o `CursorPage[...]`, **nunca** `dict` (lo exige el test de contrato).
- `require_resource(app, RESOURCE)` como primera línea de toda ruta de datos.
- El `handler` lleva `@logger.inject_lambda_context(clear_state=True)`.

---

## 4. Errores

- El **dominio** lanza `NotFoundError` o `ValidationError` (`domain/errors.py`) con un mensaje en español apto para el usuario.
- **Solo** `adapters/inbound/http/errors.py` conoce los status HTTP ([04 §3](./04-contrato-api.md#3-errores)).
- Excepciones inesperadas → 500 genérico + `logger.exception(...)`. **Nunca** se devuelve el detalle.
- No uses `try/except Exception` para silenciar errores dentro de casos de uso: deja que suban.

---

## 5. Logging

- `Logger` de Powertools (JSON). Nivel por `POWERTOOLS_LOG_LEVEL` (parámetro `LogLevel` del template).
- **Nunca** loguear tokens, headers `Authorization`, contraseñas ni datos personales. El usuario se identifica por `sub` o `username`.
- `logger.info` para hitos del negocio; `logger.exception` en errores inesperados. Nada de `print`.
- Agrega contexto con `logger.append_keys(recurso=..., usuario=identity.sub)` cuando ayude a depurar.

---

## 6. Testing

```
tests/
├── conftest.py            # http_event(), fixture `table` (moto), contexto Lambda
├── unit/                  # sin AWS: dominio, casos de uso, shared, reglas de capas
├── integration/           # handler completo + adaptador con moto
└── contract/              # código vs contrato/openapi.yaml
```

| Qué | Dónde | Obligatorio |
|---|---|---|
| Reglas de dominio y casos de uso (con puertos falsos) | `unit/` | Sí |
| `shared/` (authz, paginación) | `unit/` | Sí |
| Reglas de capas (imports prohibidos) | `unit/test_architecture.py` | Ya existe |
| Por endpoint: 200, **403 con otro grupo**, 400 con entrada inválida | `integration/` | **Sí** |
| Adaptadores (DynamoDB y S3 con moto; SQL con contenedor o doble) | `integration/` | Sí |
| Código vs contrato | `contract/test_openapi_contract.py` | Ya existe |

### `http_event()`: simula API Gateway con claims de Cognito

```python
def http_event(
    path: str,
    *,
    groups: str | None = "[admin]",
    query: dict[str, str] | None = None,
    authenticated: bool = True,
) -> dict[str, Any]:
    """Evento de API Gateway HTTP API (payload 2.0) con claims del JWT authorizer."""
    event: dict[str, Any] = {
        "version": "2.0",
        "routeKey": f"GET {path}",
        "rawPath": path,
        "rawQueryString": "&".join(f"{k}={v}" for k, v in (query or {}).items()),
        "headers": {"content-type": "application/json"},
        "queryStringParameters": query,
        "requestContext": {
            "http": {
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "1.1.1.1",
                "userAgent": "t",
            },
            "requestId": "req-1",
            "routeKey": f"GET {path}",
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }
    if authenticated:
        claims = {"sub": "abc-123", "username": "usuario.prueba", "token_use": "access"}
        if groups is not None:
            claims["cognito:groups"] = groups
        event["requestContext"]["authorizer"] = {"jwt": {"claims": claims, "scopes": None}}
    return event
```

### Ejemplo: tests de integración de un endpoint

```python
from typing import Any

from adapters.inbound.http import dashboard_1_api
from conftest import body, http_event

PATH = "/v1/dashboard_1/indicadores"


def seed(table: Any, n: int) -> None:
    for i in range(n):
        table.put_item(
            Item={
                "PK": "DASHBOARD_1",
                "SK": f"INDICADOR#{i:03d}",
                "nombre": f"Indicador {i}",
                "valor": i * 10,
                "actualizadoEn": "2026-09-01T12:00:00+00:00",
            }
        )


def test_pagina_con_cursor(table: Any, context: Any) -> None:
    seed(table, 5)
    first = dashboard_1_api.handler(http_event(PATH, query={"limit": "2"}), context)
    assert first["statusCode"] == 200
    page1 = body(first)
    assert [i["id"] for i in page1["items"]] == ["000", "001"]
    assert page1["items"][0]["actualizadoEn"].startswith("2026-09-01T12:00:00")
    assert page1["nextCursor"]

    second = dashboard_1_api.handler(
        http_event(PATH, query={"limit": "2", "cursor": page1["nextCursor"]}), context
    )
    assert [i["id"] for i in body(second)["items"]] == ["002", "003"]


def test_ultima_pagina_sin_cursor(table: Any, context: Any) -> None:
    seed(table, 1)
    page = body(dashboard_1_api.handler(http_event(PATH, query={"limit": "5"}), context))
    assert page["nextCursor"] is None


def test_grupo_sin_acceso_es_403(table: Any, context: Any) -> None:
    response = dashboard_1_api.handler(http_event(PATH, groups="[ventas]"), context)
    assert response["statusCode"] == 403
    assert body(response) == {"error": "Acceso denegado.", "code": "FORBIDDEN"}


def test_limit_invalido_es_400(table: Any, context: Any) -> None:
    response = dashboard_1_api.handler(http_event(PATH, query={"limit": "0"}), context)
    assert response["statusCode"] == 400
    assert body(response)["code"] == "VALIDATION_ERROR"


def test_cursor_invalido_es_400(table: Any, context: Any) -> None:
    response = dashboard_1_api.handler(http_event(PATH, query={"cursor": "%%%"}), context)
    assert response["statusCode"] == 400
```

### Test de reglas de capas

```python
"""Las reglas de capas de docs 02 §3, verificadas en cada `poe verify`."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

FORBIDDEN: dict[str, tuple[str, ...]] = {
    "domain": (
        "boto3",
        "botocore",
        "os",
        "aws_lambda_powertools",
        "pydantic",
        "application",
        "adapters",
        "shared",
    ),
    "application": ("boto3", "botocore", "os", "aws_lambda_powertools", "adapters"),
    "shared": ("boto3", "botocore", "aws_lambda_powertools", "domain", "application", "adapters"),
    "adapters/outbound": ("adapters.inbound", "aws_lambda_powertools.event_handler"),
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


CASES = [(layer, path) for layer in FORBIDDEN for path in sorted((SRC / layer).rglob("*.py"))]


@pytest.mark.parametrize(("layer", "path"), CASES, ids=lambda v: str(v).split("src/")[-1])
def test_capa_no_importa_lo_prohibido(layer: str, path: Path) -> None:
    for module in imported_modules(path):
        for banned in FORBIDDEN[layer]:
            assert not (module == banned or module.startswith(banned + ".")), (
                f"{path.relative_to(SRC)} importa {module!r}, prohibido en {layer}/"
            )
```

### Test de contrato

```python
"""El código cumple el contrato (docs/contrato/openapi.yaml).

Compara las rutas que registran los resolvers de Powertools con las del
contrato: mismos métodos y rutas, mismos query params y misma forma
(nombres de campos) de la respuesta 200. Si agregas un endpoint en el código
sin ponerlo en el contrato (o al revés), este test falla.
"""

import importlib
import json
import pkgutil
from pathlib import Path
from typing import Any

import pytest
import yaml

import adapters.inbound.http as http_pkg

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "contrato" / "openapi.yaml"


def load_code_spec() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    schemas: dict[str, Any] = {}
    for mod in pkgutil.iter_modules(http_pkg.__path__):
        if not mod.name.endswith("_api"):
            continue
        module = importlib.import_module(f"{http_pkg.__name__}.{mod.name}")
        spec = json.loads(module.app.get_openapi_json_schema(title="code", version="0"))
        paths.update(spec.get("paths", {}))
        schemas.update(spec.get("components", {}).get("schemas", {}))
    return {"paths": paths, "components": {"schemas": schemas}}


def resolve(node: Any, spec: dict[str, Any]) -> Any:
    while isinstance(node, dict) and "$ref" in node:
        name = node["$ref"].split("/")[-1]
        section = node["$ref"].split("/")[-2]
        node = spec["components"][section][name]
    return node


def shape(schema: Any, spec: dict[str, Any], depth: int = 0) -> Any:
    """Estructura de nombres de campos, ignorando tipos y descripciones."""
    schema = resolve(schema, spec)
    if depth > 8 or not isinstance(schema, dict):
        return None
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [shape(o, spec, depth + 1) for o in schema[key]]
            options = [o for o in options if o is not None]
            return options[0] if options else None
    if schema.get("type") == "array" or "items" in schema:
        return [shape(schema.get("items"), spec, depth + 1)]
    if "properties" in schema:
        return {k: shape(v, spec, depth + 1) for k, v in schema["properties"].items()}
    return None


def operations(spec: dict[str, Any]) -> dict[tuple[str, str], Any]:
    return {
        (method.upper(), path): op
        for path, item in spec["paths"].items()
        for method, op in item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }


CODE = load_code_spec()
CONTRACT_SPEC = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


def test_mismas_rutas() -> None:
    assert set(operations(CODE)) == set(operations(CONTRACT_SPEC))


@pytest.mark.parametrize("key", sorted(operations(CONTRACT_SPEC)))
def test_misma_forma(key: tuple[str, str]) -> None:
    code_op = operations(CODE)[key]
    contract_op = operations(CONTRACT_SPEC)[key]

    def query_params(op: Any, spec: dict[str, Any]) -> set[str]:
        return {
            resolve(p, spec)["name"]
            for p in op.get("parameters", [])
            if resolve(p, spec)["in"] == "query"
        }

    assert query_params(code_op, CODE) == query_params(contract_op, CONTRACT_SPEC)

    def ok_shape(op: Any, spec: dict[str, Any]) -> Any:
        schema = op["responses"]["200"]["content"]["application/json"]["schema"]
        return shape(schema, spec)

    assert ok_shape(code_op, CODE) == ok_shape(contract_op, CONTRACT_SPEC)
```

---

## 7. Seguridad en el código

- Identidad y grupos **solo** de los claims (`current_identity` / `require_resource`).
- Validar toda entrada con tipos y rangos (`Query(ge=…, le=…, max_length=…)`).
- DynamoDB: condiciones con `Key(...)`, no expresiones armadas con texto del usuario. SQL: siempre parametrizado.
- Secretos: Secrets Manager o SSM leídos con Powertools `Parameters`. Nunca en código, variables del template ni `samconfig.toml`.

---

## 8. Definición de terminado

- [ ] `uv run poe verify` en verde (requirements, lint, formato, tipos, tests y template).
- [ ] El endpoint está en `contrato/openapi.yaml` y el test de contrato pasa.
- [ ] Tiene tests 200 / 403 / 400.
- [ ] IAM mínimo en su función.
- [ ] Desplegado y probado en `dev` con un token real del frontend.
- [ ] Docs actualizados si cambió una regla.
