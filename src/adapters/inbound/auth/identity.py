"""Identidad del usuario a partir de los claims YA verificados por el
JWT authorizer de API Gateway. Nunca de headers, query ni body."""

from dataclasses import dataclass
from typing import Any

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver

from shared.authz import is_authorized


class UnauthenticatedError(Exception):
    """No hay claims verificados (ruta sin authorizer o evento inválido)."""


class ForbiddenError(Exception):
    """El usuario no tiene acceso al recurso."""


@dataclass(frozen=True)
class Identity:
    sub: str
    username: str
    groups: tuple[str, ...]


def parse_groups(raw: Any) -> tuple[str, ...]:
    """Normaliza `cognito:groups`.

    En HTTP API llega como string "[admin ventas]"; en tests o en otros
    orígenes puede llegar como lista. Los nombres de grupo no llevan espacios.
    """
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(str(g) for g in raw if str(g))
    if isinstance(raw, str):
        return tuple(g for g in raw.strip("[]").replace(",", " ").split() if g)
    return ()


def identity_from_claims(claims: dict[str, Any] | None) -> Identity:
    if not claims or "sub" not in claims:
        raise UnauthenticatedError()
    return Identity(
        sub=str(claims["sub"]),
        username=str(claims.get("username", claims["sub"])),
        groups=parse_groups(claims.get("cognito:groups")),
    )


def current_identity(app: APIGatewayHttpResolver) -> Identity:
    authorizer = app.current_event.request_context.authorizer
    claims = authorizer.jwt_claim if authorizer else None
    return identity_from_claims(claims)


def require_resource(app: APIGatewayHttpResolver, resource: str) -> Identity:
    """Devuelve la identidad o lanza ForbiddenError (→ 403)."""
    identity = current_identity(app)
    if not is_authorized(identity.groups, resource):
        raise ForbiddenError()
    return identity
