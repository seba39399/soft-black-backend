"""Fuente única de autorización de datos: recurso -> grupos de Cognito.

La clave del recurso es la misma que el nombre del feature/ruta del
frontend (ej. "ventas" <-> /ventas <-> src/features/ventas).
"""

from collections.abc import Iterable

RESOURCE_GROUPS: dict[str, frozenset[str]] = {
    "dashboard_1": frozenset({"admin"}),
}


def resources_for(groups: Iterable[str]) -> list[str]:
    """Recursos permitidos para la unión de grupos, en orden estable."""
    user_groups = set(groups)
    return sorted(
        resource for resource, allowed in RESOURCE_GROUPS.items() if user_groups & allowed
    )


def is_authorized(groups: Iterable[str], resource: str) -> bool:
    allowed = RESOURCE_GROUPS.get(resource, frozenset())
    return any(g in allowed for g in groups)
