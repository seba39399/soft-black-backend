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
