import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import boto3
import pytest
from moto import mock_aws

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "soft-black-frontend-api-test")
os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "soft-black-frontend-api")


@dataclass
class FakeContext:
    function_name: str = "test"
    memory_limit_in_mb: int = 256
    invoked_function_arn: str = "arn:aws:lambda:us-east-1:000000000000:function:test"
    aws_request_id: str = "req-1"


@pytest.fixture
def context() -> FakeContext:
    return FakeContext()


def http_event(
    path: str,
    *,
    groups: str | None = "[admin]",
    query: dict[str, str] | None = None,
    authenticated: bool = True,
) -> dict[str, Any]:
    """Evento de API Gateway HTTP API (payload 2.0) con claims del JWT authorizer."""
    event: dict[str, Any] = {
        "version": "2.0",
        "routeKey": f"GET {path}",
        "rawPath": path,
        "rawQueryString": "&".join(f"{k}={v}" for k, v in (query or {}).items()),
        "headers": {"content-type": "application/json"},
        "queryStringParameters": query,
        "requestContext": {
            "http": {
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "1.1.1.1",
                "userAgent": "t",
            },
            "requestId": "req-1",
            "routeKey": f"GET {path}",
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }
    if authenticated:
        claims = {"sub": "abc-123", "username": "usuario.prueba", "token_use": "access"}
        if groups is not None:
            claims["cognito:groups"] = groups
        event["requestContext"]["authorizer"] = {"jwt": {"claims": claims, "scopes": None}}
    return event


def body(response: dict[str, Any]) -> Any:
    return json.loads(response["body"])


@pytest.fixture
def table() -> Iterator[Any]:
    with mock_aws():
        ddb = boto3.resource("dynamodb")
        t = ddb.create_table(
            TableName=os.environ["TABLE_NAME"],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        from adapters.outbound.dynamodb.client import app_table

        app_table.cache_clear()
        yield t
        app_table.cache_clear()
