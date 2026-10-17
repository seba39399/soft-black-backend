"""Tabla DynamoDB compartida. Se crea una vez por contenedor (fuera del handler)."""

import os
from functools import cache
from typing import Any

import boto3


@cache
def app_table() -> Any:
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
