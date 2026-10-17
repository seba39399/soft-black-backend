# Backend soft-black-frontend — reglas

API HTTP serverless: Python 3.13, AWS SAM, API Gateway HTTP API + authorizer JWT de Cognito, Powertools for AWS Lambda, pydantic 2, arquitectura hexagonal. `dev` y `prod` son cuentas de AWS y User Pools distintos.

## Capas (las verifica tests/unit/test_architecture.py)

- `src/domain/`: entidades (`@dataclass(frozen=True)`) y errores. Sin boto3, os, Powertools, pydantic ni otras capas.
- `src/application/`: `ports/` (Protocol) y `use_cases/` (reciben puertos por constructor). Sin boto3, os, Powertools ni adapters.
- `src/adapters/outbound/<fuente>/`: implementan puertos y devuelven entidades. Las claves y tablas viven solo aquí.
- `src/adapters/inbound/http/<dominio>_api.py`: un `APIGatewayHttpResolver(enable_validation=True)` por dominio, con `register_error_handlers(app)`.
- `src/shared/`: `authz.py` (RESOURCE_GROUPS), `pagination.py`, `api_model.py`. Solo stdlib y pydantic.
- Carpetas `inbound`/`outbound`, **nunca** `in`/`out` (`in` es palabra reservada).

## Cada ruta de datos

1. Existe primero en `docs/contrato/openapi.yaml` (con `x-recurso`).
2. Primera línea: `require_resource(app, RESOURCE)`.
3. Parámetros tipados con `Annotated[..., Query(...)]`.
4. Devuelve un modelo `ApiModel` o `CursorPage[...]`, **nunca** `dict`.
5. Tiene su `Event` en la función del dominio en `template.yaml`, con IAM mínimo.
6. Tests: 200, 403 con otro grupo y 400 con entrada inválida.

## Siempre

- `uv run poe verify` en verde antes de dar algo por terminado.
- Nunca secretos en código, `template.yaml` ni `samconfig.toml` (usar Secrets Manager).
- Nunca desplegar a `prod` ni hacer `git push` sin confirmación explícita del usuario.

Detalle: `docs/02-arquitectura.md`
