"""Lambda del dominio `dashboard_1`: todas sus rutas en un solo resolver."""

from datetime import datetime
from typing import Annotated, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.utilities.typing import LambdaContext

from adapters.inbound.auth.identity import require_resource
from adapters.inbound.http.errors import register_error_handlers
from adapters.outbound.dynamodb.client import app_table
from adapters.outbound.dynamodb.indicadores_repository import DynamoIndicadorRepository
from application.use_cases.listar_indicadores import ListarIndicadores
from shared.api_model import ApiModel
from shared.pagination import MAX_LIMIT, CursorPage, clamp_limit, decode_cursor, encode_cursor

RESOURCE = "dashboard_1"

logger = Logger()
app = APIGatewayHttpResolver(enable_validation=True)
register_error_handlers(app)


class IndicadorOut(ApiModel):
    id: str
    nombre: str
    valor: float
    actualizado_en: datetime


def build_use_case() -> ListarIndicadores:
    return ListarIndicadores(DynamoIndicadorRepository(app_table()))


@app.get("/v1/dashboard_1/indicadores")
def listar_indicadores(
    limit: Annotated[int | None, Query(ge=1, le=MAX_LIMIT)] = None,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
) -> CursorPage[IndicadorOut]:
    require_resource(app, RESOURCE)
    pagina = build_use_case().ejecutar(clamp_limit(limit), decode_cursor(cursor))
    return CursorPage[IndicadorOut](
        items=[
            IndicadorOut(id=i.id, nombre=i.nombre, valor=i.valor, actualizado_en=i.actualizado_en)
            for i in pagina.items
        ],
        next_cursor=encode_cursor(pagina.next_position),
    )


@logger.inject_lambda_context(clear_state=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    return app.resolve(event, context)
