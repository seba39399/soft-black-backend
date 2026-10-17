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
