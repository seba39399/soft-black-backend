# 04 — Contrato de API

> La frontera con el frontend. **La fuente de verdad es [`contrato/openapi.yaml`](./contrato/openapi.yaml)**, en este repo. Este doc explica las reglas que el YAML aplica y cómo se cambia.

---

## 1. Dónde vive y quién manda

| Pieza | Dónde | Rol |
|---|---|---|
| `docs/contrato/openapi.yaml` | Repo **backend** | **Fuente de verdad.** Todo endpoint se escribe aquí primero |
| Este doc (04) | Repo backend | Reglas transversales y proceso de cambio |
| Doc 07 del frontend | Repo frontend | Resumen para el frontend + enlace a este YAML. **No** repite endpoints |
| `tests/contract/` | Repo backend | Verifica en cada `poe verify` que el código cumple el YAML |

**Cómo lo obtiene el frontend:** el YAML se comparte con el equipo del frontend en cada cambio (PR, copia a su carpeta `docs/contrato/` o, si lo prefieren, publicado desde la API). Lo que importa es que haya una sola fuente y que se edite solo aquí.

---

## 2. Reglas transversales

| Tema | Regla |
|---|---|
| Transporte | HTTPS. Base = salida `ApiUrl` del stack (`https://<id>.execute-api.<región>.amazonaws.com/<stage>`) |
| Versión | Todas las rutas bajo `/v1/...` |
| Formato | JSON. `Content-Type: application/json` |
| Nombres de campo | **camelCase** en el JSON. En Python se escriben en snake_case y `ApiModel` los convierte |
| Fechas | ISO 8601 en UTC (`2026-09-01T12:00:00Z`; pydantic lo serializa así si el `datetime` tiene zona UTC). Fechas sin hora: `YYYY-MM-DD` |
| Montos | Números, no strings. La moneda se documenta en el campo |
| Auth | `Authorization: Bearer <accessToken>` en todo, salvo rutas con `security: []` |
| Autorización | Cada ruta de datos declara su recurso con `x-recurso` |
| Respuestas | Siempre un objeto. Nunca un array suelto (permite agregar campos sin romper) |

---

## 3. Errores

```json
{ "error": "Mensaje en español, apto para mostrar", "code": "FORBIDDEN" }
```

| Status | `code` | Cuándo |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Parámetros inválidos (tipos, rangos, cursor corrupto) o regla de negocio |
| 401 | `UNAUTHENTICATED` | Sin claims. El 401 del **authorizer** llega como `{"message":"Unauthorized"}` (ver [03 §6](./03-autenticacion-autorizacion.md#6-errores-de-seguridad)) |
| 403 | `FORBIDDEN` | El grupo no tiene acceso al recurso |
| 404 | `NOT_FOUND` | Recurso o ruta inexistente |
| 409 | `CONFLICT` | Conflicto de estado |
| 500 | `INTERNAL_ERROR` | Error inesperado. Nunca stack traces ni detalles internos |

- Los traduce **un solo lugar**: `adapters/inbound/http/errors.py`. Los casos de uso lanzan errores de dominio (`NotFoundError`, `ValidationError`) sin saber de HTTP.
- La validación automática de Powertools devolvería 422; **se convierte a 400** para cumplir el contrato.
- El frontend decide por el **status**. El `error` lo muestra tal cual en 400, 404 y 409.

---

## 4. Paginación por cursor

Una sola forma para **todas** las fuentes (DynamoDB, SQL, S3):

```
GET /v1/dashboard_1/indicadores?limit=50
GET /v1/dashboard_1/indicadores?limit=50&cursor=eyJQSyI6…
```
```json
{ "items": [ … ], "nextCursor": "eyJQSyI6…" }
```

| Parámetro / campo | Regla |
|---|---|
| `limit` | 1–200. Por defecto 50. Fuera de rango → 400 |
| `cursor` | El `nextCursor` recibido. **Opaco**: el frontend no lo interpreta ni lo construye. Corrupto → 400 |
| `items` | Siempre presente (puede estar vacío) |
| `nextCursor` | `null` = no hay más páginas |
| `total` | **No** existe por defecto. Si un endpoint lo necesita y su fuente lo calcula barato (SQL con índice), se declara como campo opcional de ese endpoint |

**Por qué cursor y no `page`/`total`:** DynamoDB y S3 no pueden saltar a "la página 5" ni contar sin leer todo. SQL sí puede, pero el contrato debe ser igual para todas las fuentes. El cursor funciona en todas: cada adaptador guarda dentro lo que necesita (`LastEvaluatedKey`, la última clave vista en SQL o un token de S3).

**En el código:** `shared/pagination.py` → `CursorPage[T]`, `clamp_limit`, `encode_cursor` y `decode_cursor` ([02 §5](./02-arquitectura.md#5-piezas-compartidas-ya-definidas)).

---

## 5. Cómo se escribe un endpoint en el contrato

```yaml
  /v1/dashboard_1/indicadores:
    get:
      operationId: listarIndicadores
      summary: Indicadores de dashboard_1 (paginado)
      x-recurso: dashboard_1            # clave en RESOURCE_GROUPS
      parameters:
        - $ref: "#/components/parameters/Limit"
        - $ref: "#/components/parameters/Cursor"
      responses:
        "200":
          description: Página de indicadores
          content:
            application/json:
              schema: { $ref: "#/components/schemas/IndicadoresPage" }
        "400": { $ref: "#/components/responses/BadRequest" }
        "401": { $ref: "#/components/responses/Unauthenticated" }
        "403": { $ref: "#/components/responses/Forbidden" }

components:
  schemas:
    Indicador:
      type: object
      required: [id, nombre, valor, actualizadoEn]
      properties:
        id: { type: string }
        nombre: { type: string }
        valor: { type: number }
        actualizadoEn: { type: string, format: date-time }
    IndicadoresPage:
      type: object
      required: [items, nextCursor]
      properties:
        items: { type: array, items: { $ref: "#/components/schemas/Indicador" } }
        nextCursor: { type: [string, "null"] }
```

- **`operationId`** en camelCase: el frontend lo puede usar para nombrar su función (`listarIndicadores`).
- **`x-recurso`**: el recurso de autorización. `null` = cualquier usuario autenticado. Las rutas públicas no llevan `x-recurso` y declaran `security: []`.
- Reutiliza `components/parameters` (`Limit`, `Cursor`) y `components/responses` (`BadRequest`, `Unauthenticated`, `Forbidden`).

---

## 6. El test de contrato

`tests/contract/test_openapi_contract.py` carga el OpenAPI que **genera Powertools** a partir de los resolvers (`*_api.py`) y lo compara con `contrato/openapi.yaml`:

1. **Mismas rutas y métodos:** un endpoint en el código que no está en el contrato, o al revés, hace fallar el test.
2. **Mismos query params.**
3. **Misma forma de la respuesta 200:** nombres de campos, recursivamente.

Por eso **todo handler devuelve un modelo `ApiModel`** (nunca `dict`): con `dict`, Powertools no sabe la forma y el test falla.

---

## 7. Cambiar el contrato

1. **Proponer:** PR que edita `contrato/openapi.yaml` (y nada de código). Lo revisan backend y frontend.
2. **Implementar:** el backend implementa hasta que `poe verify` pase, lo que incluye el test de contrato.
3. **Consumir:** el frontend actualiza sus tipos en `src/features/<feature>/types.ts` desde el YAML.

| Tipo de cambio | Cómo |
|---|---|
| Endpoint nuevo, campo nuevo **opcional** en respuesta, parámetro nuevo opcional | Compatible: va en `/v1` |
| Quitar o renombrar un campo, cambiar un tipo, volver obligatorio un parámetro | **Incompatible:** `/v2/...` para esa ruta, o despliegue coordinado con el frontend |

Sube `info.version` del YAML en cada cambio (menor si es compatible, mayor si es incompatible).

---

## 8. Endpoints actuales

| Método y ruta | Recurso | Para qué |
|---|---|---|
| `GET /v1/health` | público | Verificar que la API responde |
| `GET /v1/me/permissions` | cualquier usuario autenticado | Usuario, grupos y recursos visibles ([03 §5](./03-autenticacion-autorizacion.md#5-get-v1mepermissions)) |
| `GET /v1/dashboard_1/indicadores` | `dashboard_1` | **Ejemplo** del esqueleto: listado paginado desde DynamoDB. Se borra al crear el primer dominio real |

El detalle exacto está en el YAML.
