# Autenticación y autorización

- El token lo valida API Gateway (authorizer `CognitoJwt`, por defecto en todas las rutas). La Lambda solo lee claims ya verificados.
- Identidad **solo** de `requestContext.authorizer.jwt.claims`, nunca de headers, query ni body.
- `cognito:groups` llega como texto `"[a b]"` en HTTP API: usar siempre `parse_groups`.
- `src/shared/authz.py` → `RESOURCE_GROUPS` es la **única** tabla de permisos. Los grupos deben existir con el mismo nombre en los User Pools de dev y prod.
- `GET /v1/me/permissions` expone los recursos al frontend.
- Nunca devolver el motivo técnico de un 401/403, ni loguear tokens.

Lee antes de empezar: `docs/03-autenticacion-autorizacion.md`
