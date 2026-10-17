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
