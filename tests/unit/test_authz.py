"""Lógica de autorización con un mapa fijo de prueba.

Los tests NO dependen del contenido real de RESOURCE_GROUPS: agregar o quitar
menús no los rompe. Solo `test_claves_de_recurso_son_validas_como_rutas`
revisa el mapa real.
"""

import pytest

from shared import authz
from shared.authz import RESOURCE_GROUPS, is_authorized, resources_for

MAPA_DE_PRUEBA = {
    "dashboard_1": frozenset({"admin"}),
    "reportes": frozenset({"admin", "ventas"}),
}


@pytest.fixture(autouse=True)
def mapa_fijo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(authz, "RESOURCE_GROUPS", MAPA_DE_PRUEBA)


def test_union_ordenada_de_recursos() -> None:
    assert resources_for(["admin"]) == ["dashboard_1", "reportes"]
    assert resources_for(["ventas"]) == ["reportes"]
    assert resources_for(["ventas", "admin"]) == ["dashboard_1", "reportes"]


def test_grupo_desconocido_no_ve_nada() -> None:
    assert resources_for(["otro"]) == []
    assert not is_authorized(["otro"], "dashboard_1")


def test_recurso_inexistente_nunca_autoriza() -> None:
    assert not is_authorized(["admin"], "no-existe")


def test_claves_de_recurso_son_validas_como_rutas() -> None:
    for resource in RESOURCE_GROUPS:  # mapa real
        assert resource == resource.strip() and "/" not in resource
