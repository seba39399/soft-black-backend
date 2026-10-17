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
