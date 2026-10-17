"""Entidades del dominio `dashboard_1` (ejemplo). Sin AWS, sin HTTP."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Indicador:
    id: str
    nombre: str
    valor: float
    actualizado_en: datetime
