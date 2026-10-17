# Agregar un endpoint

Sigue **exactamente** `docs/02-arquitectura.md` §6. En orden:

1. Pregunta al usuario lo que falte: qué datos, de qué fuente (DynamoDB, SQL, S3, Athena), qué grupos acceden y si es paginado.
2. **Contrato:** propone el cambio en `docs/contrato/openapi.yaml` (con `x-recurso`, `Limit`/`Cursor` si pagina, y respuestas 400/401/403). **Detente y pide aprobación** antes de escribir código.
3. `src/shared/authz.py`: agrega el recurso con sus grupos.
4. Dominio → puerto → caso de uso → adaptador `outbound` → handler en `<dominio>_api.py` (con `require_resource` y un modelo `ApiModel`).
5. `template.yaml`: `Event` en la función del dominio (o una función nueva) con IAM mínimo.
6. Tests: unitario del caso de uso; integración con 200, 403 y 400; el de contrato debe pasar.
7. `uv run poe verify`.
8. No despliegues ni hagas push: díselo al usuario con los comandos (`sam build`, `sam deploy --config-env dev`).

Lee antes de empezar: `docs/02-arquitectura.md`, `docs/06-fuentes-de-datos.md`
