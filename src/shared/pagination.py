"""Paginación por cursor, igual para todas las fuentes de datos.

El cursor es opaco para el frontend: base64url de un JSON que solo el
adaptador que lo generó sabe interpretar.
"""

import base64
import json
from typing import Any

from shared.api_model import ApiModel

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class InvalidCursorError(ValueError):
    pass


class CursorPage[T](ApiModel):
    """Forma única de toda respuesta paginada: {"items": [...], "nextCursor": ...}."""

    items: list[T]
    next_cursor: str | None = None


def clamp_limit(limit: int | None) -> int:
    if limit is None or limit < 1:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


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
