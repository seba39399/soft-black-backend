# README-FULL: Soft Black Discografica (frontend + backend)

> Guía única para **poner en marcha** los dos proyectos, **replicarlos** y **crear menús nuevos asociados a grupos de Cognito**.
> Proyecto **Soft Black Discografica** (`C:\Users\Subocol\Documents\soft-black-frontend-frontend` y `C:\Users\Subocol\Documents\soft-black-frontend-backend`), trabajado con **Cursor**. La misma copia está en la raíz de los dos.
> Creado con el inicializador de la plantilla (`inicializar.mjs`); los nombres, perfiles y datos de Cognito de esta guía ya son los del proyecto.
> Revisado el 22-sep-2026: frontend v1.0.1 (23 tests) y backend con 48 tests, `mypy --strict` y `sam validate --lint` en verde. El ejemplo del §8 se probó completo en los dos proyectos.

---

## Índice

1. [Cómo encaja todo](#1-cómo-encaja-todo)
2. [Estado y pendientes](#2-estado-y-pendientes)
3. [Herramientas](#3-herramientas)
4. [Paso 1: Cognito (por entorno)](#4-paso-1-cognito-por-entorno)
5. [Paso 2: Backend en `dev`](#5-paso-2-backend-en-dev)
6. [Paso 3: Frontend local](#6-paso-3-frontend-local)
7. [Paso 4: Frontend en Vercel (sin git)](#7-paso-4-frontend-en-vercel-sin-git)
8. [Crear un menú nuevo asociado a grupos de Cognito](#8-crear-un-menú-nuevo-asociado-a-grupos-de-cognito)
9. [Pasar a `prod`](#9-pasar-a-prod)
10. [Replicar para un proyecto nuevo](#10-crear-otro-proyecto-desde-la-plantilla)
11. [Problemas frecuentes](#11-problemas-frecuentes)
12. [Dónde está el detalle](#12-dónde-está-el-detalle)
13. [Trabajar con Cursor](#13-trabajar-con-cursor)

---

## 1. Cómo encaja todo

```
 Usuario ──login──▶ Cognito (User Pool del entorno)
                        │ access token con cognito:groups = ["ventas"]
                        ▼
 ┌─────────────────────────────┐  Bearer <token>   ┌───────────────────────────────────┐
 │ FRONTEND (Next.js, Vercel)   │ ────────────────▶ │ BACKEND (API Gateway + Lambda,    │
 │                              │                   │          AWS SAM, Python)         │
 │ nav-config.ts                │                   │ authorizer JWT: token válido?     │
 │  GROUP_MENU_MAP              │                   │ shared/authz.py                   │
 │   ventas → ["reportes"]      │  ◀─── JSON ─────  │  RESOURCE_GROUPS                  │
 │  → menú y acceso a rutas     │                   │   "reportes" → {"admin","ventas"} │
 └─────────────────────────────┘                   │  → 403 si el grupo no tiene acceso│
                                                    └───────────────────────────────────┘
```

**La regla que lo une todo es una sola palabra.** Un menú se llama igual en todas partes:

| Dónde | Ejemplo `reportes` |
|---|---|
| Ruta del frontend | `/reportes` |
| Carpeta del feature | `src/features/reportes/` |
| Clave en `NAV_ITEMS` (frontend) | `reportes` |
| Recurso en `RESOURCE_GROUPS` (backend) | `"reportes"` |
| Prefijo de las rutas de la API | `/v1/reportes/...` |
| Handler del backend | `src/adapters/inbound/http/reportes_api.py` |
| `x-recurso` en el contrato | `reportes` |

**Los grupos** de Cognito deciden quién ve qué. Hoy (v1.0) el mapa grupo → menú está **dos veces** y debe coincidir:

- frontend: `GROUP_MENU_MAP` decide qué ve el menú y a qué rutas se entra;
- backend: `RESOURCE_GROUPS` decide qué datos entrega (si no hay permiso, responde 403).

En la v1.1 del frontend el menú saldrá de `GET /v1/me/permissions` y el backend será la única fuente ([§2](#2-estado-y-pendientes)).

**Entornos:** `dev` y `prod` son **cuentas de AWS distintas**, cada una con **su** User Pool, **su** API y **sus** variables del frontend. Nada se mezcla.

---

## 2. Estado y pendientes

### Lo que ya funciona

- **Frontend:** login real con Cognito (incluye la contraseña temporal), cierre de sesión automático a los 60 min (configurable), menú y acceso por grupos, `proxy.ts`, `apiFetch` y la pantalla de ejemplo `dashboard_1`.
- **Backend:**
  - código completo y probado localmente: `GET /v1/health`, `GET /v1/me/permissions` y el ejemplo `GET /v1/dashboard_1/indicadores`;
  - authorizer JWT de Cognito, CORS por entorno, tabla DynamoDB;
  - contrato OpenAPI con un test que lo hace cumplir.
- **Grupos alineados:** en los dos lados, `admin` da acceso a `dashboard_1`.

### Pendientes para desplegar y poner en marcha

| # | Pendiente | Dónde | Bloquea |
|---|---|---|---|
| 1 | Instalar Python 3.13, `uv`, AWS CLI v2 y SAM CLI, y correr `uv run poe verify` **en tu máquina** (solo se ha corrido en el entorno de pruebas) | Backend | Todo el backend |
| 2 | Tener acceso a la cuenta AWS **dev** y crear el perfil `soft-black-frontend-dev` | AWS | Despliegue |
| 3 | Cambiar `CognitoClientIds=<client-id-dev>` en `samconfig.toml` por el App Client ID del `.env.local` del frontend | Backend | Despliegue |
| 4 | `sam build` + `sam deploy --config-env dev` y copiar la salida `ApiUrl` | Backend | Frontend con datos |
| 5 | Poner esa `ApiUrl` en `NEXT_PUBLIC_API_BASE_URL` del `.env.local` (hoy tiene una URL de ejemplo) | Frontend | Llamadas a la API |
| 6 | Crear el proyecto en Vercel, cargar las tres variables y desplegar | Frontend | Acceso fuera de tu PC |
| 7 | Agregar la URL de Vercel a `AllowedOrigins` en `samconfig.toml` y redesplegar el backend | Backend | CORS desde Vercel |
| 8 | **Prod:** cuenta AWS, User Pool, App Client, grupos, perfil `soft-black-frontend-prod` y bloque `[prod]` de `samconfig.toml` (hoy con `<...>`) | AWS y backend | Producción ([§9](#9-pasar-a-prod)) |

### Siguiente mejora (después de desplegar el backend)

**Frontend v1.1:** el menú y el acceso saldrán de `GET /v1/me/permissions` y se eliminará `GROUP_MENU_MAP`. Así los permisos quedan en un solo lugar. Plan en `soft-black-frontend-frontend/docs/04-autorizacion.md` §8.

---

## 3. Herramientas

| Herramienta | Versión | Para | Instalación (Windows) |
|---|---|---|---|
| Node.js | 22.15.1 (`nvm use vercel`) | Frontend | NVM for Windows |
| Python | 3.13 | Backend (`sam build` lo necesita) | `winget install Python.Python.3.13` |
| uv | última | Backend: entorno y dependencias | `winget install astral-sh.uv` |
| AWS CLI | v2 | Perfiles de las cuentas | `winget install Amazon.AWSCLI` |
| AWS SAM CLI | ≥ 1.166 | Build y despliegue del backend | `winget install Amazon.SAM-CLI` |
| Vercel CLI | última | Desplegar el frontend sin git | `npm i -g vercel` |
| Docker | opcional | Solo `sam local` | docker.com |

---

## 4. Paso 1: Cognito (por entorno)

Se hace **una vez por entorno**, en la consola de AWS de **esa** cuenta, región `us-east-1`. En `dev` ya existe el pool `<user-pool-dev>`.

1. **User Pool** con inicio de sesión por *username*.
2. **App Client público, sin client secret.** Con secret, el login desde el navegador no funciona.
3. **Grupos** con los nombres **exactos** de `GROUP_MENU_MAP` / `RESOURCE_GROUPS` (hoy: `admin`). Distinguen mayúsculas.
4. **Usuarios** asignados a sus grupos. Cognito les da una contraseña temporal y el frontend pide cambiarla en el primer login.
5. Anota el **User Pool ID** y el **App Client ID**.

> Los grupos viajan **dentro del token**. Si cambias los grupos de un usuario, el cambio se ve cuando vuelve a iniciar sesión (o cuando el token se renueva, hasta 1 h).

Detalle: `soft-black-frontend-frontend/docs/00-usar-la-plantilla.md` §4 y `soft-black-frontend-backend/docs/03-autenticacion-autorizacion.md`.

---

## 5. Paso 2: Backend en `dev`

En `C:\Users\Subocol\Documents\soft-black-frontend-backend`, con PowerShell:

```powershell
# 1. Instalar y verificar (debe terminar en verde)
uv sync
uv run poe verify

# 2. Perfil de la cuenta DEV (una vez). SSO si la empresa usa IAM Identity Center:
aws configure sso --profile soft-black-frontend-dev
#    o con llaves de acceso:  aws configure --profile soft-black-frontend-dev
aws sts get-caller-identity --profile soft-black-frontend-dev   # confirma que es la cuenta correcta
```

**3. Completa `samconfig.toml`**, bloque `[dev.deploy.parameters]`:

```toml
parameter_overrides = [
  "Stage=dev",
  "CognitoUserPoolId=<user-pool-dev>",
  "CognitoClientIds=<App Client ID del frontend dev>",          # ← mismo del .env.local
  "AllowedOrigins=http://localhost:3000,https://<tu-proyecto>.vercel.app",
]
```

**4. Despliega:**

```powershell
sam build
sam deploy --config-env dev
```

Al terminar, SAM imprime la salida **`ApiUrl`** (por ejemplo `https://abc123.execute-api.us-east-1.amazonaws.com/dev`): es el `NEXT_PUBLIC_API_BASE_URL` del frontend.

**5. Prueba:**

```powershell
curl https://<ApiUrl>/v1/health            # 200 {"status":"ok"}
curl https://<ApiUrl>/v1/me/permissions    # 401 {"message":"Unauthorized"}  (sin token: correcto)
```

Con token (opcional; requiere habilitar `ALLOW_USER_PASSWORD_AUTH` en el App Client de **dev**):

```powershell
$token = aws cognito-idp initiate-auth --profile soft-black-frontend-dev --auth-flow USER_PASSWORD_AUTH `
  --client-id <client-id-dev> --auth-parameters USERNAME=<usuario>,PASSWORD=<clave> `
  --query AuthenticationResult.AccessToken --output text
curl -H "Authorization: Bearer $token" https://<ApiUrl>/v1/me/permissions
# 200 {"user":"...","groups":["admin"],"resources":["dashboard_1"]}
```

**6. (Opcional) Datos de ejemplo** para `GET /v1/dashboard_1/indicadores`. Guarda esto como `item.json`:

```json
{ "PK": {"S": "DASHBOARD_1"}, "SK": {"S": "INDICADOR#001"},
  "nombre": {"S": "Ventas del mes"}, "valor": {"N": "1250000"},
  "actualizadoEn": {"S": "2026-09-01T12:00:00+00:00"} }
```

```powershell
aws dynamodb put-item --profile soft-black-frontend-dev --table-name soft-black-frontend-dev --item file://item.json
```

> **Nunca** despliegues sin `--config-env`. Nunca copies `site-packages` de Windows a Lambda: siempre `sam build`.

---

## 6. Paso 3: Frontend local

En `C:\Users\Subocol\Documents\soft-black-frontend-frontend`:

```powershell
nvm use vercel          # Node 22.15.1
npm ci
```

`.env.local` (no se comparte ni se sube):

```bash
NEXT_PUBLIC_COGNITO_USER_POOL_ID=<user-pool-dev>
NEXT_PUBLIC_COGNITO_CLIENT_ID=<App Client ID dev>
NEXT_PUBLIC_API_BASE_URL=<ApiUrl del paso 2, sin barra final>
NEXT_PUBLIC_SESSION_MAX_MINUTES=60   # opcional: la sesión se cierra 60 min después del login
```

```powershell
npm run verify          # lint + typecheck + tests + build
npm run dev             # http://localhost:3000
```

Entra con un usuario del grupo `admin`: debes llegar a `/dashboard_1`.

---

## 7. Paso 4: Frontend en Vercel (sin git)

1. En la raíz del frontend, crea **`.vercelignore`** para no subir credenciales ni carpetas pesadas:
   ```
   .env.local
   node_modules
   .next
   ```
2. Vincula el proyecto y crea un preview:
   ```powershell
   vercel login
   vercel            # acepta la detección de Next.js
   ```
3. En Vercel → *Settings*:
   - *Build and Deployment → Node.js Version*: **22.x**.
   - *Environment Variables*: las tres `NEXT_PUBLIC_*`.
     - **Preview** y **Development**: valores de **dev**.
     - **Production**: valores de **prod** (o de dev mientras no exista prod).
4. Despliega de nuevo. Las `NEXT_PUBLIC_*` se inyectan al compilar, así que cualquier cambio exige un build nuevo:
   ```powershell
   vercel            # preview
   vercel --prod     # producción
   ```
5. Agrega la URL de Vercel a `AllowedOrigins` del backend y redespliega el backend (`sam deploy --config-env dev`).

> Cada preview de Vercel tiene una URL distinta. Para CORS usa la URL de producción del proyecto (`<proyecto>.vercel.app`) o un dominio propio, no URLs sueltas de preview.
>
> El plan gratuito (Hobby) de Vercel es para uso personal o no comercial. Para uso de la empresa, revisa si necesitan el plan Pro.

---

## 8. Crear un menú nuevo asociado a grupos de Cognito

Hay cuatro casos. Elige el tuyo:

| Caso | Qué quieres | Tocas |
|---|---|---|
| **A** | Menú nuevo **con datos** de la API | Cognito + backend + frontend |
| **B** | Menú nuevo **sin datos** (página estática o enlaces) | Cognito + frontend (+ una línea en el backend) |
| **C** | Dar o quitar a un grupo el acceso a un menú **existente** | Frontend + backend (una línea en cada uno) |
| **D** | Crear un **grupo nuevo** | Cognito + casos B o C |

**Con Cursor:** en el backend escribe `/nuevo-endpoint` en el chat (modo Agent); en el frontend, `/nuevo-dashboard`. El agente sigue estos mismos pasos y pide aprobación del contrato antes del código.

### Caso A: menú con datos (ejemplo completo `reportes`)

Objetivo: un menú **Reportes** que muestra ventas por región. Lo ven los grupos `admin` y `ventas`.

```
GET /v1/reportes/resumen?desde=2026-01-01&hasta=2026-01-31
→ 200 { "items": [{ "region": "Norte", "total": 150 }], "generadoEn": "2026-09-22T20:00:00Z" }
```

El orden importa: **Cognito → contrato → backend → desplegar backend → frontend → desplegar frontend.**

#### A.1 Cognito

En el User Pool de **cada** entorno: crea el grupo `ventas` (si no existe) y asigna los usuarios.

#### A.2 Backend (`soft-black-frontend-backend`)

**1. Contrato primero:** `docs/contrato/openapi.yaml`, en su propio cambio y antes del código.

```yaml
# en paths:
  /v1/reportes/resumen:
    get:
      operationId: resumenVentas
      summary: Resumen de ventas por región en un rango de fechas
      x-recurso: reportes
      parameters:
        - { name: desde, in: query, required: true, schema: { type: string, format: date } }
        - { name: hasta, in: query, required: true, schema: { type: string, format: date } }
      responses:
        "200":
          description: Totales por región
          content:
            application/json:
              schema: { $ref: "#/components/schemas/ResumenVentas" }
        "400": { $ref: "#/components/responses/BadRequest" }
        "401": { $ref: "#/components/responses/Unauthenticated" }
        "403": { $ref: "#/components/responses/Forbidden" }

# en components.schemas:
    ResumenRegion:
      type: object
      required: [region, total]
      properties:
        region: { type: string }
        total: { type: number }

    ResumenVentas:
      type: object
      required: [items, generadoEn]
      properties:
        items:
          type: array
          items: { $ref: "#/components/schemas/ResumenRegion" }
        generadoEn: { type: string, format: date-time }
```

**2. Permiso:** `src/shared/authz.py`.

```python
RESOURCE_GROUPS: dict[str, frozenset[str]] = {
    "dashboard_1": frozenset({"admin"}),
    "reportes": frozenset({"admin", "ventas"}),   # ← nuevo
}
```

**3. Dominio:** `src/domain/reportes.py`.

```python
"""Entidades del dominio `reportes`. Sin AWS, sin HTTP."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResumenRegion:
    region: str
    total: float
```

**4. Puerto:** `src/application/ports/reportes.py`.

```python
"""Puerto: lo que el caso de uso necesita, sin decir de dónde sale."""

from datetime import date
from typing import Protocol

from domain.reportes import ResumenRegion


class ReporteRepository(Protocol):
    def resumen_por_region(self, desde: date, hasta: date) -> list[ResumenRegion]: ...
```

**5. Caso de uso:** `src/application/use_cases/resumen_ventas.py`.

```python
"""Caso de uso: resumen de ventas por región en un rango de fechas."""

from datetime import date

from application.ports.reportes import ReporteRepository
from domain.errors import ValidationError
from domain.reportes import ResumenRegion

MAX_DIAS = 366


class ResumenVentas:
    def __init__(self, repository: ReporteRepository) -> None:
        self._repository = repository

    def ejecutar(self, desde: date, hasta: date) -> list[ResumenRegion]:
        if desde > hasta:
            raise ValidationError("La fecha 'desde' debe ser anterior o igual a 'hasta'.")
        if (hasta - desde).days > MAX_DIAS:
            raise ValidationError("El rango máximo es de un año.")
        return self._repository.resumen_por_region(desde, hasta)
```

**6. Adaptador de datos:** `src/adapters/outbound/dynamodb/reportes_repository.py`. Si los datos vienen de SQL, S3 u otra fuente, solo cambia este archivo (ver `docs/06-fuentes-de-datos.md`).

```python
"""Implementación DynamoDB de ReporteRepository.

Claves (solo este archivo las conoce):
  PK = "REPORTES#VENTAS"      SK = "<YYYY-MM-DD>#<region>"     total = número
"""

from collections import defaultdict
from datetime import date
from typing import Any

from boto3.dynamodb.conditions import Key

from domain.reportes import ResumenRegion

PK = "REPORTES#VENTAS"


class DynamoReporteRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def resumen_por_region(self, desde: date, hasta: date) -> list[ResumenRegion]:
        totales: dict[str, float] = defaultdict(float)
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(PK)
            & Key("SK").between(f"{desde.isoformat()}#", f"{hasta.isoformat()}#\uffff"),
        }
        while True:
            response = self._table.query(**kwargs)
            for item in response.get("Items", []):
                region = str(item["SK"]).split("#", 1)[1]
                totales[region] += float(item["total"])
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return [ResumenRegion(region=r, total=t) for r, t in sorted(totales.items())]
```

**7. Handler:** `src/adapters/inbound/http/reportes_api.py`. El nombre debe terminar en `_api.py` para que el test de contrato lo encuentre.

```python
"""Lambda del dominio `reportes`: todas sus rutas en un solo resolver."""

from datetime import UTC, date, datetime
from typing import Annotated, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.openapi.params import Query
from aws_lambda_powertools.utilities.typing import LambdaContext

from adapters.inbound.auth.identity import require_resource
from adapters.inbound.http.errors import register_error_handlers
from adapters.outbound.dynamodb.client import app_table
from adapters.outbound.dynamodb.reportes_repository import DynamoReporteRepository
from application.use_cases.resumen_ventas import ResumenVentas
from shared.api_model import ApiModel

RESOURCE = "reportes"  # = clave de RESOURCE_GROUPS = ruta y feature del frontend

logger = Logger()
app = APIGatewayHttpResolver(enable_validation=True)
register_error_handlers(app)


class ResumenRegionOut(ApiModel):
    region: str
    total: float


class ResumenVentasOut(ApiModel):
    items: list[ResumenRegionOut]
    generado_en: datetime            # sale como "generadoEn" (camelCase automático)


def build_use_case() -> ResumenVentas:
    return ResumenVentas(DynamoReporteRepository(app_table()))


@app.get("/v1/reportes/resumen")
def resumen(
    desde: Annotated[date, Query()],
    hasta: Annotated[date, Query()],
) -> ResumenVentasOut:
    require_resource(app, RESOURCE)          # 403 si el grupo no está en RESOURCE_GROUPS
    regiones = build_use_case().ejecutar(desde, hasta)
    return ResumenVentasOut(
        items=[ResumenRegionOut(region=r.region, total=r.total) for r in regiones],
        generado_en=datetime.now(UTC),
    )


@logger.inject_lambda_context(clear_state=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    return app.resolve(event, context)
```

Reglas del handler: siempre `require_resource(...)` y siempre devolver un modelo `ApiModel` (nunca un `dict`).

**8. Infraestructura:** `template.yaml`, una función por dominio, antes de `AppTable`.

```yaml
  ReportesFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: adapters.inbound.http.reportes_api.handler
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref AppTable
      Events:
        ResumenVentas:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/reportes/resumen
            Method: GET
```

**9. Tests:** `tests/integration/test_reportes_api.py`.

```python
from typing import Any

from adapters.inbound.http import reportes_api
from conftest import body, http_event

PATH = "/v1/reportes/resumen"
RANGO = {"desde": "2026-01-01", "hasta": "2026-01-31"}


def seed(table: Any) -> None:
    for sk, total in [
        ("2026-01-05#Norte", 100),
        ("2026-01-20#Norte", 50),
        ("2026-01-10#Sur", 30),
        ("2026-02-01#Sur", 999),  # fuera del rango
    ]:
        table.put_item(Item={"PK": "REPORTES#VENTAS", "SK": sk, "total": total})


def test_resumen_por_region(table: Any, context: Any) -> None:
    seed(table)
    response = reportes_api.handler(http_event(PATH, groups="[ventas]", query=RANGO), context)
    assert response["statusCode"] == 200
    data = body(response)
    assert data["items"] == [{"region": "Norte", "total": 150.0}, {"region": "Sur", "total": 30.0}]
    assert "generadoEn" in data


def test_grupo_sin_acceso_es_403(table: Any, context: Any) -> None:
    response = reportes_api.handler(http_event(PATH, groups="[otro]", query=RANGO), context)
    assert response["statusCode"] == 403


def test_rango_invertido_es_400(table: Any, context: Any) -> None:
    query = {"desde": "2026-02-01", "hasta": "2026-01-01"}
    response = reportes_api.handler(http_event(PATH, query=query), context)
    assert response["statusCode"] == 400
    assert body(response)["code"] == "VALIDATION_ERROR"


def test_sin_fechas_es_400(table: Any, context: Any) -> None:
    response = reportes_api.handler(http_event(PATH), context)
    assert response["statusCode"] == 400
```

Y `tests/unit/test_resumen_ventas.py` (caso de uso con un repositorio falso):

```python
from datetime import date

import pytest

from application.use_cases.resumen_ventas import ResumenVentas
from domain.errors import ValidationError
from domain.reportes import ResumenRegion


class FakeRepo:
    def resumen_por_region(self, desde: date, hasta: date) -> list[ResumenRegion]:
        return [ResumenRegion(region="Norte", total=10.0)]


def test_devuelve_lo_del_repositorio() -> None:
    result = ResumenVentas(FakeRepo()).ejecutar(date(2026, 1, 1), date(2026, 1, 31))
    assert result == [ResumenRegion(region="Norte", total=10.0)]


def test_rango_invertido() -> None:
    with pytest.raises(ValidationError):
        ResumenVentas(FakeRepo()).ejecutar(date(2026, 2, 1), date(2026, 1, 1))
```

**10. Verificar y desplegar:**

```powershell
uv run poe verify                  # 59 tests con este ejemplo
sam build
sam deploy --config-env dev
```

Datos de prueba (un registro por día y región). En `venta.json`:

```json
{ "PK": {"S": "REPORTES#VENTAS"}, "SK": {"S": "2026-01-05#Norte"}, "total": {"N": "100"} }
```

```powershell
aws dynamodb put-item --profile soft-black-frontend-dev --table-name soft-black-frontend-dev --item file://venta.json
```

#### A.3 Frontend (`soft-black-frontend-frontend`)

**1. Copia el contrato:** reemplaza `docs/contrato/openapi.yaml` por el `docs/contrato/openapi.yaml` del backend. No se edita a mano.

**2. Feature:** crea estos archivos. El código completo de cada uno está en `docs/02-arquitectura.md` §5, que usa este mismo ejemplo.

```
src/features/reportes/
├── types.ts                      # ResumenRegion, ResumenVentas (igual que el contrato)
├── utils/
│   ├── reportes-api.ts           # fetchResumenVentas(desde, hasta) con apiFetch
│   └── format.ts                 # formatCOP()
└── components/
    ├── ReportesPage.tsx          # useApiQuery + Spinner / ErrorState / EmptyState / datos
    └── ResumenTabla.tsx
```

`types.ts` y `utils/reportes-api.ts`:

```ts
// src/features/reportes/types.ts
export interface ResumenRegion {
  region: string;
  total: number;
}

export interface ResumenVentas {
  items: ResumenRegion[];
  generadoEn: string; // ISO 8601 UTC
}
```

```ts
// src/features/reportes/utils/reportes-api.ts
import { apiFetch } from "@/lib/api-client";
import type { ResumenVentas } from "@/features/reportes/types";

export function fetchResumenVentas(desde: string, hasta: string): Promise<ResumenVentas> {
  const qs = new URLSearchParams({ desde, hasta });
  return apiFetch<ResumenVentas>(`/v1/reportes/resumen?${qs.toString()}`);
}
```

**3. Ruta:** `src/app/(dashboard)/reportes/page.tsx`. Solo renderiza la página.

```tsx
import ReportesPage from "@/features/reportes/components/ReportesPage";

export default function Page(): React.ReactElement {
  return <ReportesPage />;
}
```

**4. Menú y acceso:** `src/features/main-dashboard/utils/nav-config.ts`.

```ts
export const NAV_ITEMS = {
  dashboard_1: { href: "/dashboard_1", label: "Dashboard 1" },
  reportes: { href: "/reportes", label: "Reportes" },          // ← nuevo (el orden = orden del menú)
} as const satisfies Record<string, NavItem>;

export const GROUP_MENU_MAP: Record<string, readonly NavItemKey[]> = {
  admin: ["dashboard_1", "reportes"],                          // ← agregado
  ventas: ["reportes"],                                        // ← grupo nuevo
};
```

**No toques `src/proxy.ts`:** protege toda ruta nueva automáticamente.

**5. Tests:** `tests/features/reportes/format.test.ts` (y cualquier lógica de `utils/`).

```ts
import { describe, expect, it } from "vitest";
import { formatCOP } from "@/features/reportes/utils/format";

describe("formatCOP", () => {
  it("formatea pesos sin decimales", () => {
    expect(formatCOP(1250000)).toMatch(/1\.250\.000/);
  });
});
```

**6. Verificar y desplegar:**

```powershell
npm run verify
vercel            # preview; luego vercel --prod
```

**7. Prueba manual:**

- Un usuario de `ventas` ve **solo** "Reportes" y la tabla carga.
- Un usuario de `admin` ve "Dashboard 1" y "Reportes".
- Un usuario de otro grupo no ve "Reportes". Si escribe `/reportes` en la URL, lo redirige.

### Caso B: menú sin datos

Solo los pasos A.1 (Cognito), A.3.2 a A.3.6 (sin `types.ts` ni `*-api.ts`) y, en el backend, **agrega igual la clave a `RESOURCE_GROUPS`**. No tiene endpoint, pero así `/v1/me/permissions` ya lo reporta y la migración a la v1.1 no requiere cambios.

### Caso C: dar o quitar acceso a un grupo en un menú existente

Dos líneas, una por proyecto, y deben quedar **iguales**:

```ts
// frontend: nav-config.ts
GROUP_MENU_MAP = { ventas: ["reportes", "dashboard_1"] };        // ← + dashboard_1
```

```python
# backend: shared/authz.py
"dashboard_1": frozenset({"admin", "ventas"}),                   # ← + ventas
```

Despliega los dos. Si solo cambias el frontend, el usuario verá el menú pero la API responderá 403. Si solo cambias el backend, la API permite, pero el menú no aparece.

### Caso D: grupo nuevo

1. Créalo con el **mismo nombre** en el User Pool de dev **y** de prod.
2. Asigna usuarios.
3. Aplica el caso C (o A o B) para decir qué menús ve.
4. Los usuarios deben cerrar sesión y volver a entrar.

### Checklist por menú nuevo

- [ ] Nombre único usado igual en ruta, feature, `NAV_ITEMS`, `RESOURCE_GROUPS` y `/v1/<nombre>/...`.
- [ ] Grupos creados en Cognito **de cada entorno**, con usuarios asignados.
- [ ] Endpoint en `openapi.yaml` del backend (antes del código) y copia en el frontend.
- [ ] Backend: dominio, puerto, caso de uso, adaptador, handler con `require_resource`, función en `template.yaml` y tests. `uv run poe verify` en verde.
- [ ] Backend desplegado **antes** que el frontend.
- [ ] Frontend: feature, ruta, `NAV_ITEMS` + `GROUP_MENU_MAP` y tests. `npm run verify` en verde.
- [ ] `GROUP_MENU_MAP` y `RESOURCE_GROUPS` coinciden.
- [ ] Prueba manual con un usuario con acceso y otro sin acceso.

---

## 9. Pasar a `prod`

1. **Cuenta AWS de prod:**
   - `aws configure sso --profile soft-black-frontend-prod`;
   - comprueba con `aws sts get-caller-identity --profile soft-black-frontend-prod`.
2. **Cognito en prod** ([§4](#4-paso-1-cognito-por-entorno)): User Pool, App Client público, **los mismos grupos** y los usuarios reales.
3. **`samconfig.toml`**, bloque `[prod.deploy.parameters]`: reemplaza los tres `<...>` (pool, client y dominio del frontend).
4. **Despliega el backend:** `sam build`, luego `sam deploy --config-env prod`. En prod te pide confirmar el changeset. Anota el `ApiUrl`.
5. **Vercel**, variables de **Production** con los valores de prod, y luego `vercel --prod`.
6. **Prueba:** login con un usuario de prod y un menú con datos.

> La tabla DynamoDB tiene `DeletionPolicy: Retain`: borrar el stack no borra los datos.

---

## 10. Crear otro proyecto desde la plantilla

Los proyectos nuevos **no se copian a mano**: se crean con el inicializador (`inicializar.mjs`) que está en la carpeta raíz de la plantilla.

1. **Con Cursor:** abre la carpeta raíz de la plantilla en Cursor y escribe `/crear-proyecto` en el chat (modo Agent). El agente te pide los datos y ejecuta el inicializador.
2. **Sin agente**, desde la raíz de la plantilla:
   ```powershell
   node inicializar.mjs
   ```
   Pregunta, uno por uno: nombre técnico (`ventas-app`), nombre visible, descripción, región, prefijo de los perfiles de AWS, datos de Cognito de dev y prod (opcionales), dominio de producción y carpeta destino.
3. El inicializador crea `<destino>\<nombre>-frontend` y `<destino>\<nombre>-backend` con **todo** renombrado (paquete, app, stack, tabla, servicio, perfiles, documentación), el `.env.local` del frontend, un `CHANGELOG.md` nuevo y un `proyecto.json` con los datos usados. No toca la plantilla ni ejecuta git.
4. En el proyecto nuevo:
   - `npm ci` + `npm run verify` en el frontend y `uv sync` + `uv run poe verify` en el backend (o usa `--instalar` para que el inicializador haga `npm ci` y `uv sync`);
   - los grupos de ejemplo siguen siendo `admin` → `dashboard_1`: reemplázalos con el caso C del [§8](#8-crear-un-menú-nuevo-asociado-a-grupos-de-cognito);
   - borra el ejemplo `dashboard_1` cuando crees tu primer menú real:
     - backend: `dashboard_1_api.py`, `listar_indicadores.py`, `ports/indicadores.py`, `domain/indicadores.py`, `indicadores_repository.py`, `Dashboard1Function`, su entrada en `openapi.yaml` y su test;
     - frontend: `src/features/dashboard_1`, su ruta y su entrada en `nav-config.ts`.

   Los tests de `authz` y de `/me/permissions` usan un mapa fijo, así que no se rompen al cambiar los menús. En el frontend, los tests de login y layout usan `admin → dashboard_1`: si borras `dashboard_1`, cámbialos a tu primer menú.
5. **Cognito:** pools propios o los mismos, según el caso. Si dos proyectos comparten pool, los **grupos** deben ser distintos por proyecto (por ejemplo `ventas-app-admin`). El stack y la tabla ya llevan el nombre del proyecto, así que dos proyectos pueden convivir en la misma cuenta de AWS.

---

## 11. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| "Tu usuario no tiene dashboards asignados" | El usuario no tiene grupos, o sus grupos no están en `GROUP_MENU_MAP` | Asigna el grupo en Cognito o agrega el grupo al mapa. Vuelve a iniciar sesión |
| El menú aparece pero dice "No tienes permiso…" (403) | `GROUP_MENU_MAP` y `RESOURCE_GROUPS` no coinciden | Caso C: iguala los dos y despliega el backend |
| Todo vuelve al login ("Tu sesión expiró") | La API respondió 401: token de otro entorno o App Client que no está en `CognitoClientIds` | Revisa que las tres variables sean del mismo entorno y el `samconfig.toml` |
| Error de CORS en el navegador | El origen del frontend no está en `AllowedOrigins` | Agrégalo (sin barra final) y redespliega el backend |
| "No se pudo conectar con el servidor" | `NEXT_PUBLIC_API_BASE_URL` mal escrita o con barra final, o la API tardó más de 15 s | `curl <ApiUrl>/v1/health`; revisa la variable y haz un build nuevo |
| Cambié un grupo y no se refleja | El token viejo sigue vigente | Cerrar sesión y volver a entrar |
| "Tu sesión expiró por tiempo" | Pasaron `NEXT_PUBLIC_SESSION_MAX_MINUTES` (60 por defecto) desde el login | Es lo esperado. Para cambiar el tiempo, ajusta la variable y reinicia o vuelve a desplegar |
| Ruta nueva da 404 en la API | Falta el `Event` en `template.yaml` | Agrégalo y redespliega |
| `test_mismas_rutas` falla | Ruta en el código que no está en `openapi.yaml` (o al revés) | Contrato y código deben coincidir |
| `test_misma_forma` falla con `None` | El handler devuelve `dict` | Devuelve un modelo `ApiModel` |
| La Lambda falla con `pydantic_core` | Se subieron binarios de Windows | Despliega siempre con `sam build` |
| Vercel compila con valores viejos | Las `NEXT_PUBLIC_*` se fijan al compilar | Cambia la variable y vuelve a desplegar |

Más casos: `soft-black-frontend-frontend/docs/09-troubleshooting.md` y `soft-black-frontend-backend/docs/11-troubleshooting.md`.

---

## 12. Dónde está el detalle

| Tema | Frontend (`docs/`) | Backend (`docs/`) |
|---|---|---|
| Empezar | `00-usar-la-plantilla.md` | `00-empezar.md` |
| Arquitectura y "agregar" | `02-arquitectura.md` §5 (dashboard) | `02-arquitectura.md` §6 (endpoint) |
| Autenticación | `03-autenticacion.md` | `03-autenticacion-autorizacion.md` |
| Autorización / grupos | `04-autorizacion.md` (incluye la migración v1.1) | `03-autenticacion-autorizacion.md` §4 |
| Contrato | `07-repos-y-contrato-api.md` + `contrato/openapi.yaml` (copia) | `04-contrato-api.md` + `contrato/openapi.yaml` (**fuente**) |
| Infraestructura | — | `05-infraestructura-sam.md` |
| Fuentes de datos (SQL, S3…) | — | `06-fuentes-de-datos.md` |
| Entornos y despliegue | `06-entorno-y-deploy.md` | `08-entorno-y-despliegue.md` |
| Git (cuando lo adopten) | `08-git.md` | `09-git.md` |
| Cursor | `10-cursor.md` | `10-cursor.md` |
| Cambios pendientes del front | — | `PARA-EL-FRONTEND.md` |

---

## 13. Trabajar con Cursor

| Pieza | Dónde |
|---|---|
| Reglas (fuente) | `docs/agente/` en cada proyecto |
| Lo que lee Cursor | `.cursor/rules/*.mdc`: copia de `docs/agente/` con su *frontmatter* (`alwaysApply` o `globs`) + `proyecto.mdc`. Si cambias una regla, edita `docs/agente/` y vuelve a copiarla |
| Procedimientos | Frontend: `/nuevo-dashboard`. Backend: `/nuevo-endpoint` (`.cursor/skills/`). Crear otro proyecto: `/crear-proyecto` en la raíz de la plantilla |
| Funcionalidades grandes | Modo **Plan** del chat, o un `SPEC.md` antes de implementar |
| Seguimiento de tareas (opcional) | Servidor MCP **Task Master AI** (ver `docs/10-cursor.md`) |
| Guía completa | `docs/10-cursor.md` en cada proyecto |
