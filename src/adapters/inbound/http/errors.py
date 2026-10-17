"""Traducción de errores a la forma del contrato: {"error", "code"}.

Único lugar que conoce los códigos HTTP. Se registra en cada resolver con
`register_error_handlers(app)`.
"""

from http import HTTPStatus

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response, content_types
from aws_lambda_powertools.event_handler.openapi.exceptions import RequestValidationError

from adapters.inbound.auth.identity import ForbiddenError, UnauthenticatedError
from domain.errors import NotFoundError, ValidationError
from shared.pagination import InvalidCursorError

logger = Logger()


def error_response(status: HTTPStatus, message: str, code: str) -> Response[dict[str, str]]:
    return Response(
        status_code=status.value,
        content_type=content_types.APPLICATION_JSON,
        body={"error": message, "code": code},
    )


def register_error_handlers(app: APIGatewayHttpResolver) -> None:
    @app.exception_handler(RequestValidationError)
    def _validation(_: RequestValidationError) -> Response[dict[str, str]]:
        return error_response(
            HTTPStatus.BAD_REQUEST, "Los parámetros enviados no son válidos.", "VALIDATION_ERROR"
        )

    @app.exception_handler(InvalidCursorError)
    def _cursor(_: InvalidCursorError) -> Response[dict[str, str]]:
        return error_response(
            HTTPStatus.BAD_REQUEST, "El cursor de paginación no es válido.", "VALIDATION_ERROR"
        )

    @app.exception_handler(ValidationError)
    def _domain_validation(exc: ValidationError) -> Response[dict[str, str]]:
        return error_response(
            HTTPStatus.BAD_REQUEST, str(exc) or "Datos inválidos.", "VALIDATION_ERROR"
        )

    @app.exception_handler(UnauthenticatedError)
    def _unauthenticated(_: UnauthenticatedError) -> Response[dict[str, str]]:
        return error_response(HTTPStatus.UNAUTHORIZED, "No autorizado.", "UNAUTHENTICATED")

    @app.exception_handler(ForbiddenError)
    def _forbidden(_: ForbiddenError) -> Response[dict[str, str]]:
        return error_response(HTTPStatus.FORBIDDEN, "Acceso denegado.", "FORBIDDEN")

    @app.exception_handler(NotFoundError)
    def _not_found(exc: NotFoundError) -> Response[dict[str, str]]:
        return error_response(
            HTTPStatus.NOT_FOUND, str(exc) or "El recurso no existe.", "NOT_FOUND"
        )

    @app.not_found
    def _route_not_found(_: Exception) -> Response[dict[str, str]]:
        return error_response(HTTPStatus.NOT_FOUND, "La ruta no existe.", "NOT_FOUND")

    @app.exception_handler(Exception)
    def _unexpected(exc: Exception) -> Response[dict[str, str]]:
        logger.exception("Error no controlado")
        return error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Ocurrió un error inesperado.", "INTERNAL_ERROR"
        )
