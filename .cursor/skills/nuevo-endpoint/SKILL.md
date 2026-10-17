---
name: nuevo-endpoint
description: Agrega un endpoint al backend soft-black-frontend (contrato OpenAPI, permiso por grupo de Cognito, dominio, puerto, caso de uso, adaptador, handler, template SAM y tests). Úsalo cuando pidan un endpoint, una ruta de API o datos nuevos para un dashboard.
---

Lee `docs/agente/nuevo-endpoint.md` y síguelo **exactamente** y en orden.

- La línea "Lee antes de empezar" del final lista documentos que debes leer primero.
- En el paso del contrato, **detente** y muestra el cambio propuesto en `docs/contrato/openapi.yaml` para que el usuario lo apruebe antes de escribir código.
- Termina con `uv run poe verify` en verde y muestra el resultado. No despliegues.

El pedido del usuario es lo que escribió junto a `/nuevo-endpoint`.
