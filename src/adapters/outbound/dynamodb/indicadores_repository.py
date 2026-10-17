"""Implementación DynamoDB del puerto IndicadorRepository (single-table).

Claves (solo este archivo las conoce):
  PK = "DASHBOARD_1"            SK = "INDICADOR#<id>"
"""

from datetime import datetime
from typing import Any

from boto3.dynamodb.conditions import Key

from domain.indicadores import Indicador

PK = "DASHBOARD_1"
SK_PREFIX = "INDICADOR#"


class DynamoIndicadorRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def list_page(
        self, limit: int, position: dict[str, Any] | None
    ) -> tuple[list[Indicador], dict[str, Any] | None]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(PK) & Key("SK").begins_with(SK_PREFIX),
            "Limit": limit,
        }
        if position:
            kwargs["ExclusiveStartKey"] = position
        response = self._table.query(**kwargs)
        items = [self._to_entity(item) for item in response.get("Items", [])]
        return items, response.get("LastEvaluatedKey")

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> Indicador:
        return Indicador(
            id=str(item["SK"]).removeprefix(SK_PREFIX),
            nombre=str(item["nombre"]),
            valor=float(item["valor"]),
            actualizado_en=datetime.fromisoformat(str(item["actualizadoEn"])),
        )
