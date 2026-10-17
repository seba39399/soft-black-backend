# 00 — Empezar

> De "clonado" a "API desplegada en `dev` respondiendo a mi frontend". Sigue los pasos en orden.

---

## 1. Herramientas

| Herramienta | Versión | Para qué | Instalación en Windows |
|---|---|---|---|
| **Python** | 3.13 | Runtime de las Lambdas; `sam build` lo necesita localmente | python.org o `winget install Python.Python.3.13` |
| **uv** | última | Entornos virtuales, dependencias y lockfile | `winget install astral-sh.uv` |
| **AWS CLI** | v2 | Perfiles y credenciales de las cuentas | `winget install Amazon.AWSCLI` |
| **AWS SAM CLI** | ≥ 1.166 | Build, validación, despliegue y pruebas locales | Instalador MSI de AWS o `winget install Amazon.SAM-CLI` |
| **Docker Desktop** | opcional | Solo para `sam local` y para builds en contenedor | docker.com |

No hace falta Node.js: el backend no usa Serverless Framework.

---

## 2. Instalar el proyecto

```powershell
uv sync            # crea .venv con Python 3.13 e instala todo (runtime + dev)
uv run poe verify  # lint + formato + tipos + tests + validación del template
```

`verify` debe terminar en verde **antes** de cualquier cambio. Si falla en un repo recién clonado, revisa [11 — Troubleshooting](./11-troubleshooting.md).

---

## 3. Cuentas de AWS: `dev` y `prod` son cuentas distintas

Cada entorno vive en **su propia cuenta de AWS** y usa **su propio User Pool de Cognito**. Nada se comparte entre entornos.

| | `dev` | `prod` |
|---|---|---|
| Cuenta AWS | cuenta de desarrollo | cuenta de producción |
| Perfil AWS CLI | `soft-black-frontend-dev` | `soft-black-frontend-prod` |
| User Pool | `<user-pool-dev>` | `<user-pool-prod>` |
| App Client | el del frontend en `dev` | el del frontend en `prod` |
| Orígenes CORS | `http://localhost:3000` (+ URL de preview) | dominio real del frontend |

Configura los perfiles una vez. Se recomienda SSO si la organización usa IAM Identity Center:

```powershell
aws configure sso --profile soft-black-frontend-dev
aws configure sso --profile soft-black-frontend-prod
aws sts get-caller-identity --profile soft-black-frontend-dev   # confirma que apunta a la cuenta correcta
```

Los valores por entorno viven en `samconfig.toml` (ver [08 §3](./08-entorno-y-despliegue.md#3-samconfigtoml-un-bloque-por-entorno)).

---

## 4. Primer despliegue a `dev`

1. Completa en `samconfig.toml`, bloque `[dev.deploy.parameters]`, el `CognitoClientIds` (el mismo App Client del `.env.local` del frontend).
2. Despliega:
   ```powershell
   sam build
   sam deploy --config-env dev
   ```
3. Copia la salida `ApiUrl`: es el valor de `NEXT_PUBLIC_API_BASE_URL` del frontend.
4. Prueba:
   ```powershell
   curl https://<ApiUrl>/v1/health                  # 200 {"status":"ok"}
   curl https://<ApiUrl>/v1/me/permissions          # 401 (sin token)
   ```
5. Desde el frontend (con sesión iniciada), `GET /v1/me/permissions` debe devolver tu usuario, tus grupos y tus recursos.

---

## 5. Siguiente paso

Crea tu primer endpoint siguiendo [02 §6](./02-arquitectura.md#6-agregar-un-endpoint-paso-a-paso). Con Cursor: `/nuevo-endpoint` ([10](./10-cursor.md)).
