"""Errores de dominio. No conocen HTTP: el borde (inbound/http) los traduce."""


class DomainError(Exception):
    """Base de los errores de negocio."""


class NotFoundError(DomainError):
    """El recurso pedido no existe."""


class ValidationError(DomainError):
    """Los datos no cumplen una regla de negocio."""
