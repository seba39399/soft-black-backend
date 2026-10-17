# Cambios para el frontend (`soft-black-frontend` v1.1)

> Lo que el frontend debe ajustar para alinearse con este backend. Son cambios **acordados**.
>
> **Estado (22-sep-2026):** la plantilla del frontend **v1.0.1** ya aplicó §1, §3 y §4 (contrato enlazado, `CursorPage<T>`, variables por entorno). Falta §2 (permisos desde `/v1/me/permissions`), planificado para la **v1.1**: se hace cuando este backend esté desplegado, porque desde ese momento el login del frontend depende de la API. Mientras tanto, el frontend usa su `GROUP_MENU_MAP`, que debe coincidir con `RESOURCE_GROUPS`.

---

## 1. El contrato vive en el backend

- **Fuente de verdad:** `backend/docs/contrato/openapi.yaml`.
- El doc `docs/07-repos-y-contrato-api.md` del frontend deja de describir endpoints y reglas en detalle: queda como un resumen que **enlaza** al YAML (y, si se copia al repo del frontend, a `docs/contrato/openapi.yaml`, sin editarlo).
- Los tipos de cada feature (`src/features/<feature>/types.ts`) se escriben a partir del YAML.

---

## 2. Permisos desde el backend

**Hoy:** `nav-config.ts` tiene `NAV_ITEMS` (pantallas) y `GROUP_MENU_MAP` (grupo → pantallas).

**v1.1:**

| Pieza | Queda en |
|---|---|
| `NAV_ITEMS` (href, label, ícono de cada pantalla) | Frontend (sin cambios) |
| `GROUP_MENU_MAP` | **Se elimina.** Lo reemplaza `GET /v1/me/permissions` |
| `DEFAULT_NAV_ITEMS` | Se elimina (sin recursos = sin menú) |

**Contrato:**

```http
GET /v1/me/permissions
→ 200 { "user": "usuario.prueba", "groups": ["admin"], "resources": ["dashboard_1"] }
```

**Regla de nombres:** la clave de `NAV_ITEMS` = el recurso del backend = el feature = la ruta (`ventas`).

**Cambios en el código:**

1. `src/features/auth/utils/permissions-api.ts`: `fetchMyPermissions()` con `apiFetch`.
2. `nav-config.ts`: `resolveNavItems(resources)` filtra `NAV_ITEMS` por las claves presentes en `resources`. `canAccessRoute` y `resolveRedirectTarget` reciben `resources` en vez de `groups`.
3. `MainDashboardLayout` y `LoginPage`: usan `fetchMyPermissions()` en lugar de `getUserGroups()`. Lo piden una vez por sesión y lo guardan en memoria (contexto de React).
4. `src/proxy.ts`: **solo verifica la sesión**. Deja de decidir por grupo. El acceso a cada pantalla lo resuelve el layout con los permisos, y los **datos** los protege el backend (403). Así se evita una llamada a Lambda por cada navegación.
5. Tests: los de propiedades de `nav-config` pasan a generar `resources` en lugar de `groups`.

**Si `/me/permissions` falla** (red, 5xx): el layout muestra `ErrorState` con "Reintentar". No asume permisos.

---

## 3. Paginación por cursor

**Hoy:** `Paginated<T> = { items, page, pageSize, total }` en `src/types/api.ts`, sin uso real.

**v1.1:**

```ts
/** Página de un listado. `nextCursor: null` = no hay más. */
export interface CursorPage<T> {
  items: T[];
  nextCursor: string | null;
}
```

- Petición: `?limit=50` y, para la siguiente página, `&cursor=<nextCursor>`. El cursor es **opaco**: no se interpreta ni se construye.
- UI: "Cargar más" o "Siguiente". Para "Anterior", guardar en memoria la pila de cursores visitados.
- No existe `total` salvo que un endpoint lo declare.
- Se elimina `Paginated<T>`.

---

## 4. Variables por entorno

`dev` y `prod` son cuentas y User Pools distintos. El frontend de cada entorno usa los **tres** valores de **su** entorno:

| Variable | `dev` | `prod` |
|---|---|---|
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | `<user-pool-dev>` | User Pool de prod |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | App Client de dev | App Client de prod |
| `NEXT_PUBLIC_API_BASE_URL` | `ApiUrl` del stack dev | `ApiUrl` del stack prod |

- El App Client de cada entorno debe estar en `CognitoClientIds` del bloque correspondiente de `samconfig.toml` del backend.
- El dominio del frontend en prod debe estar en `AllowedOrigins` del backend.
- Los **grupos** se llaman igual en ambos pools.

---

## 5. Errores: sin cambios

El frontend ya maneja lo que el backend devuelve:

- 401 del authorizer (`{"message":"Unauthorized"}`) → `apiFetch` decide por status → login. ✅
- 403, 400 y 404 con `{error, code}` → `ApiRequestError` con el `error` del backend. ✅
- Timeout del frontend (15 s) mayor que el útil del backend (~12 s). ✅

---

## 6. Checklist del frontend

- [x] Doc 07 reducido a un resumen + enlace al `openapi.yaml` (v1.0.1; copia en `docs/contrato/openapi.yaml`).
- [x] `CursorPage<T>` reemplaza a `Paginated<T>` (v1.0.1).
- [x] Docs 06 y 09: variables por entorno, 401 del authorizer, CORS (v1.0.1).
- [x] Doc 04 §8: migración a `/v1/me/permissions` documentada.
- [ ] `fetchMyPermissions()` + menú y acceso desde `resources`.
- [ ] `GROUP_MENU_MAP` y `DEFAULT_NAV_ITEMS` eliminados.
- [ ] `proxy.ts` solo valida sesión (docs 03 y 04 del frontend actualizados).
- [ ] Tests actualizados; `npm run verify` en verde.
- [ ] `CHANGELOG.md` del frontend: versión 1.1.0.
