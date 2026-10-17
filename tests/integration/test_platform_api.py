from typing import Any

import pytest

from adapters.inbound.http import platform_api
from conftest import body, http_event
from shared import authz


def test_health(context: Any) -> None:
    response = platform_api.handler(http_event("/v1/health", authenticated=False), context)
    assert response["statusCode"] == 200
    assert body(response) == {"status": "ok"}


def test_me_permissions(context: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    # Mapa fijo: el test no depende de los menús reales de RESOURCE_GROUPS.
    monkeypatch.setattr(authz, "RESOURCE_GROUPS", {"dashboard_1": frozenset({"admin"})})
    response = platform_api.handler(
        http_event("/v1/me/permissions", groups="[admin otro]"), context
    )
    assert response["statusCode"] == 200
    assert body(response) == {
        "user": "usuario.prueba",
        "groups": ["admin", "otro"],
        "resources": ["dashboard_1"],
    }


def test_me_permissions_sin_claims_es_401(context: Any) -> None:
    response = platform_api.handler(http_event("/v1/me/permissions", authenticated=False), context)
    assert response["statusCode"] == 401
    assert body(response) == {"error": "No autorizado.", "code": "UNAUTHENTICATED"}


def test_ruta_inexistente_es_404(context: Any) -> None:
    response = platform_api.handler(http_event("/v1/nada"), context)
    assert response["statusCode"] == 404
    assert body(response)["code"] == "NOT_FOUND"
