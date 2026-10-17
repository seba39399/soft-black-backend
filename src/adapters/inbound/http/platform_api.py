"""Lambda "platform": rutas transversales (salud y permisos).

GET /v1/health          → sin authorizer (Auth: NONE en el template)
GET /v1/me/permissions  → con authorizer Cognito
"""

from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

from adapters.inbound.auth.identity import current_identity
from adapters.inbound.http.errors import register_error_handlers
from application.use_cases.get_my_permissions import get_my_permissions
from shared.api_model import ApiModel

logger = Logger()
app = APIGatewayHttpResolver(enable_validation=True)
register_error_handlers(app)


class HealthOut(ApiModel):
    status: str


class MyPermissionsOut(ApiModel):
    user: str
    groups: list[str]
    resources: list[str]


@app.get("/v1/health")
def health() -> HealthOut:
    return HealthOut(status="ok")


@app.get("/v1/me/permissions")
def my_permissions() -> MyPermissionsOut:
    identity = current_identity(app)
    result = get_my_permissions(identity.username, identity.groups)
    return MyPermissionsOut(user=result.username, groups=result.groups, resources=result.resources)


@logger.inject_lambda_context(clear_state=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    return app.resolve(event, context)
