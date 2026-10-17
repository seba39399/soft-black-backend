# soft-black-frontend API — Documentación

Backend de los dashboards: una **API HTTP serverless en Python** que valida el token de Cognito, autoriza por grupo y sirve datos desde **varias fuentes** (DynamoDB, bases SQL, S3…). Se comunica con el frontend (`soft-black-frontend`) **solo** a través del contrato [`contrato/openapi.yaml`](./contrato/openapi.yaml).

> **¿Primera vez aquí?** Empieza por [`00-empezar.md`](./00-empezar.md): herramientas, cuentas de AWS y primer despliegue.
>
> **¿Vas a agregar un endpoint?** Sigue [`02-arquitectura.md` §6 — Agregar un endpoint](./02-arquitectura.md#6-agregar-un-endpoint-paso-a-paso).

---

## Mapa de la documentación

| # | Documento | Léelo cuando… |
|---|---|---|
| 00 | [Empezar](./00-empezar.md) | Vas a instalar, configurar tus cuentas o desplegar por primera vez |
| 01 | [Visión y stack](./01-vision-y-stack.md) | Quieres saber qué hace el backend y con qué está hecho |
| 02 | [Arquitectura](./02-arquitectura.md) | Vas a escribir o mover código (incluye *agregar un endpoint*) |
| 03 | [Autenticación y autorización](./03-autenticacion-autorizacion.md) | Tocas Cognito, grupos, permisos o `/v1/me/permissions` |
| 04 | [Contrato de API](./04-contrato-api.md) | Defines o cambias un endpoint, errores o paginación |
| 05 | [Infraestructura con SAM](./05-infraestructura-sam.md) | Tocas `template.yaml`: funciones, rutas, IAM, CORS, timeouts |
| 06 | [Fuentes de datos](./06-fuentes-de-datos.md) | Un endpoint lee de DynamoDB, SQL o S3 |
| 07 | [Convenciones y testing](./07-convenciones-y-testing.md) | Escribes cualquier código o test |
| 08 | [Entornos y despliegue](./08-entorno-y-despliegue.md) | Despliegas a `dev` o `prod`, o configuras perfiles de AWS |
| 09 | [Git](./09-git.md) | Creas ramas, commits o PRs |
| 10 | [Trabajar con Cursor](./10-cursor.md) | Usas Cursor (reglas `.mdc` y skills) en este repo |
| 11 | [Troubleshooting](./11-troubleshooting.md) | Algo no funciona |

Anexos:

- [`contrato/openapi.yaml`](./contrato/openapi.yaml): **fuente de verdad** del contrato front ↔ back.
- [`agente/`](./agente/): fuente de las reglas y del procedimiento del agente (se copian a `.cursor/rules/`; la skill `/nuevo-endpoint` los lee).
- [`PARA-EL-FRONTEND.md`](./PARA-EL-FRONTEND.md): cambios que el frontend debe aplicar (paginación por cursor, `/v1/me/permissions`, contrato).

---

## Reglas que no se negocian

1. **Contrato primero.** Un endpoint existe en `contrato/openapi.yaml` **antes** de existir en el código. Un test hace fallar el build si difieren ([04](./04-contrato-api.md)).
2. **Toda ruta exige token de Cognito** (`DefaultAuthorizer`). Solo `/v1/health` es pública, y cualquier otra excepción se declara explícitamente ([03](./03-autenticacion-autorizacion.md)).
3. **El backend decide quién ve qué.** `src/shared/authz.py` es la única fuente de permisos. El frontend los consulta con `/v1/me/permissions`.
4. **Hexagonal estricto.** `domain/` y `application/` no importan AWS, Powertools ni HTTP ([02](./02-arquitectura.md)).
5. **IAM mínimo por función.** Cada función declara solo lo que usa ([05](./05-infraestructura-sam.md)).
6. **`uv run poe verify` en verde** antes de cualquier despliegue o PR ([07](./07-convenciones-y-testing.md)).
7. **Si cambias un comportamiento, actualiza el doc** en el mismo cambio.

---

## Estado

- **Documentación:** lista para implementar.
- **Código:** esqueleto funcional en la raíz del repo (`src/`, `tests/`, `template.yaml`, `samconfig.toml`), verificado el 22-sep-2026 con Python 3.13: 48 tests, `ruff`, `mypy --strict` y `sam validate --lint` en verde. Incluye `GET /v1/health`, `GET /v1/me/permissions` y el **ejemplo** `GET /v1/dashboard_1/indicadores` (DynamoDB, paginado), que se borra al crear el primer dominio real.
- **Pendiente antes del primer despliegue:** `CognitoClientIds` de `dev` y todo el bloque `prod` de `samconfig.toml` (hoy con marcadores `<...>`).
- **Frontend:** la plantilla `soft-black-frontend` ya enlaza a este contrato y usa `CursorPage<T>`. El cambio de permisos a `/v1/me/permissions` está planificado para su v1.1 ([PARA-EL-FRONTEND.md](./PARA-EL-FRONTEND.md)).
