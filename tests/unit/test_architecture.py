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
