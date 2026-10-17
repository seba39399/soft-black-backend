# 03 — Autenticación y autorización

> Quién eres (Cognito, validado por API Gateway) y qué puedes ver (grupos, decidido por el backend). El backend es la **última línea de defensa**: el frontend solo oculta menús.

---

## 1. Modelo

| Paso | Quién lo hace | Si falla |
|---|---|---|
| 1. Token válido (firma, emisor, expiración, audiencia) | **API Gateway** (authorizer JWT), antes de invocar la Lambda | **401**, sin ejecutar código |
| 2. Identidad y grupos | `adapters/inbound/auth/identity.py`, desde los claims ya verificados | **401** `UNAUTHENTICATED` si no hay claims |
| 3. ¿El grupo tiene acceso al recurso? | `require_resource(app, "<recurso>")` en el handler | **403** `FORBIDDEN` |
| 4. Datos | Caso de uso → adaptador | — |

El backend **no** emite tokens ni gestiona usuarios.

---

## 2. Authorizer JWT (API Gateway HTTP API)

Declarado una vez en `template.yaml` como **authorizer por defecto**: toda ruta lo tiene salvo que diga explícitamente `Auth: { Authorizer: NONE }`.

```yaml
Auth:
  DefaultAuthorizer: CognitoJwt
  Authorizers:
    CognitoJwt:
      IdentitySource: $request.header.Authorization
      JwtConfiguration:
        issuer: !Sub https://cognito-idp.${AWS::Region}.amazonaws.com/${CognitoUserPoolId}
        audience: !Ref CognitoClientIds
```

- **Emisor:** el User Pool **del entorno**. `dev` y `prod` son cuentas y User Pools distintos, así que un token de `dev` **nunca** sirve en `prod`.
- **Audiencia:** los *access tokens* de Cognito no traen `aud`. API Gateway valida entonces el claim `client_id` contra `audience` ([docs de AWS](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html)). Lista en `CognitoClientIds` **cada** App Client que llame a la API (por ejemplo, el del frontend).
- **Access token, no id token:** es lo que envía el frontend (`Authorization: Bearer <accessToken>`) y lo que trae `cognito:groups`.
- **Única ruta pública hoy:** `GET /v1/health`.

---

## 3. Identidad y grupos

API Gateway entrega los claims verificados en `requestContext.authorizer.jwt.claims`. En HTTP API los claims de lista llegan **aplanados como texto**: `"cognito:groups": "[admin ventas]"`. `parse_groups` normaliza todos los formatos:

```python
def parse_groups(raw: Any) -> tuple[str, ...]:
    """Normaliza `cognito:groups`.

    En HTTP API llega como string "[admin ventas]"; en tests o en otros
    orígenes puede llegar como lista. Los nombres de grupo no llevan espacios.
    """
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(str(g) for g in raw if str(g))
    if isinstance(raw, str):
        return tuple(g for g in raw.strip("[]").replace(",", " ").split() if g)
    return ()


def identity_from_claims(claims: dict[str, Any] | None) -> Identity:
    if not claims or "sub" not in claims:
        raise UnauthenticatedError()
    return Identity(
        sub=str(claims["sub"]),
        username=str(claims.get("username", claims["sub"])),
        groups=parse_groups(claims.get("cognito:groups")),
    )
```

**Reglas:**

- La identidad sale **solo** de los claims verificados, **nunca** de headers, query o body.
- **Los nombres de grupo no llevan espacios** (rompen el formato `"[a b]"`). Usa `snake_case` o `kebab-case`.
- Para identificar al usuario en logs se usa `sub` o `username`, nunca el email ni el token.

---

## 4. Autorización: una sola fuente

`src/shared/authz.py` define qué grupos pueden ver cada **recurso**. Es la **única** tabla de permisos del sistema:

```python
"""Fuente única de autorización de datos: recurso -> grupos de Cognito.

La clave del recurso es la misma que el nombre del feature/ruta del
frontend (ej. "ventas" <-> /ventas <-> src/features/ventas).
"""

from collections.abc import Iterable

RESOURCE_GROUPS: dict[str, frozenset[str]] = {
    "dashboard_1": frozenset({"admin"}),
}


def resources_for(groups: Iterable[str]) -> list[str]:
    """Recursos permitidos para la unión de grupos, en orden estable."""
    user_groups = set(groups)
    return sorted(
        resource for resource, allowed in RESOURCE_GROUPS.items() if user_groups & allowed
    )


def is_authorized(groups: Iterable[str], resource: str) -> bool:
    allowed = RESOURCE_GROUPS.get(resource, frozenset())
    return any(g in allowed for g in groups)
```

- **Recurso = dominio = feature del frontend:** `ventas` ↔ `/v1/ventas/...` ↔ `src/features/ventas` ↔ `/ventas`.
- **Los grupos deben existir con el mismo nombre en el User Pool de `dev` y en el de `prod`.** `RESOURCE_GROUPS` es código y se despliega igual en ambas cuentas. Si un grupo falta en un pool, en ese entorno nadie tiene ese acceso.
- Cambiar un permiso = PR que edita `authz.py`, con su test ([07 §6](./07-convenciones-y-testing.md#6-testing)) y un despliegue.

### En cada handler

```python
@app.get("/v1/dashboard_1/indicadores")
def listar_indicadores(...) -> CursorPage[IndicadorOut]:
    require_resource(app, RESOURCE)      # 403 si el grupo no tiene acceso
    ...
```

El authorizer solo prueba que hay sesión. **Olvidar `require_resource` deja el endpoint abierto a cualquier usuario del pool.** Los tests de integración de cada endpoint incluyen el caso 403 ([07 §6](./07-convenciones-y-testing.md#6-testing)).

---

## 5. `GET /v1/me/permissions`

Le dice al frontend qué puede mostrar, así el menú sale de la misma fuente que la seguridad:

```http
GET /v1/me/permissions
Authorization: Bearer <accessToken>
```
```json
{ "user": "usuario.prueba", "groups": ["admin"], "resources": ["dashboard_1"] }
```

```python
@app.get("/v1/me/permissions")
def my_permissions() -> MyPermissionsOut:
    identity = current_identity(app)
    result = get_my_permissions(identity.username, identity.groups)
    return MyPermissionsOut(user=result.username, groups=result.groups, resources=result.resources)
```

- Cualquier usuario autenticado puede llamarlo: no tiene `require_resource`.
- `resources` vacío = el usuario no tiene dashboards asignados. El frontend muestra el mensaje correspondiente.
- Cómo lo usa el frontend: [`PARA-EL-FRONTEND.md` §2](./PARA-EL-FRONTEND.md#2-permisos-desde-el-backend).

---

## 6. Errores de seguridad

| Caso | Status | Cuerpo |
|---|---|---|
| Sin token, token inválido o expirado | 401 (lo responde API Gateway) | `{"message":"Unauthorized"}` (formato de AWS, no del contrato) |
| Claims ausentes en una ruta protegida | 401 | `{"error":"No autorizado.","code":"UNAUTHENTICATED"}` |
| Grupo sin acceso | 403 | `{"error":"Acceso denegado.","code":"FORBIDDEN"}` |

> El 401 del authorizer lo genera API Gateway, no la Lambda, así que su cuerpo no sigue el contrato. El frontend decide por el **status** (401 → login), no por el cuerpo. Está documentado así en el contrato.

Nunca se devuelve el motivo técnico (firma, claim, grupo que faltó). Se loguea si hace falta, sin el token.

---

## 7. Checklist

- [ ] `DefaultAuthorizer: CognitoJwt` en el `HttpApi`; `Auth: NONE` solo en rutas públicas documentadas.
- [ ] `CognitoUserPoolId` y `CognitoClientIds` correctos en cada bloque de `samconfig.toml`.
- [ ] Cada handler de datos llama a `require_resource` con su recurso.
- [ ] Cada recurso en `RESOURCE_GROUPS` con grupos que existen en **ambos** User Pools.
- [ ] Tests: 200 con grupo permitido, 403 con otro grupo y 401 sin claims.
