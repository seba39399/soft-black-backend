# 08 — Entornos y despliegue

> `dev` y `prod` son **cuentas de AWS distintas** con **User Pools distintos**. Un mismo `template.yaml` se despliega en ambas con valores diferentes (`samconfig.toml`).

---

## 1. Mapa de entornos

```
            Cuenta AWS DEV                               Cuenta AWS PROD
┌───────────────────────────────────┐        ┌───────────────────────────────────┐
│ User Pool dev (<user-pool-dev>)│        │ User Pool prod                     │
│ Stack soft-black-frontend-api-dev       │        │ Stack soft-black-frontend-api-prod      │
│  └ HttpApi /dev  ← localhost:3000  │        │  └ HttpApi /prod ← dominio real    │
│  └ Lambdas, tabla soft-black-frontend-dev│       │  └ Lambdas, tabla soft-black-frontend-prod│
└───────────────────────────────────┘        └───────────────────────────────────┘
      perfil AWS CLI: soft-black-frontend-dev                      perfil AWS CLI: soft-black-frontend-prod
```

| Regla | Por qué |
|---|---|
| Un token de `dev` no sirve en `prod` (y al revés) | Cada authorizer confía solo en el User Pool de su cuenta |
| Los **grupos** se llaman igual en ambos pools | `RESOURCE_GROUPS` es código y es igual en los dos ([03 §4](./03-autenticacion-autorizacion.md#4-autorización-una-sola-fuente)) |
| El frontend de cada entorno apunta a su API y a su pool | `.env.local` en dev; variables del host en prod ([`PARA-EL-FRONTEND.md` §4](./PARA-EL-FRONTEND.md#4-variables-por-entorno)) |
| Los datos nunca se copian de `prod` a `dev` sin anonimizar | Datos personales y de negocio |

---

## 2. Perfiles de AWS

```powershell
aws configure sso --profile soft-black-frontend-dev      # o `aws configure --profile soft-black-frontend-dev` con llaves de IAM
aws configure sso --profile soft-black-frontend-prod
aws sts get-caller-identity --profile soft-black-frontend-prod   # verifica la cuenta ANTES de desplegar
```

- **Sin llaves en el repo, en `samconfig.toml` ni en variables.** Las Lambdas usan su rol IAM.
- Quien despliega a `prod` necesita un rol con permisos de CloudFormation, Lambda, API Gateway, DynamoDB, IAM (para crear los roles de las funciones) y S3 (artefactos).

---

## 3. `samconfig.toml`: un bloque por entorno

```toml
version = 0.1

[default.global.parameters]
stack_name = "soft-black-frontend-api"

[default.build.parameters]
use_container = false  # SAM descarga wheels Linux arm64; usar true (requiere Docker) solo si una dependencia no publica wheels
cached = true
parallel = true

[default.validate.parameters]
lint = true

[dev.deploy.parameters]
profile = "soft-black-frontend-dev"                     # perfil AWS CLI de la cuenta DEV
region = "us-east-1"
stack_name = "soft-black-frontend-api-dev"
resolve_s3 = true
capabilities = "CAPABILITY_IAM"
confirm_changeset = false
parameter_overrides = [
  "Stage=dev",
  "CognitoUserPoolId=<user-pool-dev>",
  "CognitoClientIds=<client-id-dev>",
  "AllowedOrigins=http://localhost:3000",
]

[prod.deploy.parameters]
profile = "soft-black-frontend-prod"                    # perfil AWS CLI de la cuenta PROD
region = "us-east-1"
stack_name = "soft-black-frontend-api-prod"
resolve_s3 = true
capabilities = "CAPABILITY_IAM"
confirm_changeset = true                # en prod se revisa el changeset antes de aplicar
parameter_overrides = [
  "Stage=prod",
  "CognitoUserPoolId=<user-pool-prod>",
  "CognitoClientIds=<client-id-prod>",
  "AllowedOrigins=https://<dominio-del-frontend>",
]
```

- **Se versiona**: no tiene secretos, solo IDs públicos (User Pool, App Client, orígenes).
- Rellena los `<…>` de `prod` con los datos de esa cuenta.
- `confirm_changeset = true` en `prod`: SAM muestra qué va a cambiar y pide confirmación.
- Si un valor debe ser secreto (credenciales SQL, llaves de terceros), **no** va aquí: va en Secrets Manager y el template recibe solo su ARN o nombre.

---

## 4. Build y despliegue

```powershell
uv run poe verify              # 1. todo en verde
sam build                      # 2. empaqueta src/ + src/requirements.txt para Linux arm64
sam deploy --config-env dev    # 3. despliega a la cuenta DEV
```

Producción:

```powershell
aws sts get-caller-identity --profile soft-black-frontend-prod
sam build
sam deploy --config-env prod   # muestra el changeset y pide confirmación
```

**Empaquetado de dependencias:** `sam build` descarga las versiones **Linux arm64** de las dependencias con binarios (como `pydantic-core`), aunque compiles desde Windows. Requiere **Python 3.13 instalado**. Si alguna dependencia no publica wheels para `aarch64`, usa `sam build --use-container` (requiere Docker).

**Salida:** `ApiUrl` → `NEXT_PUBLIC_API_BASE_URL` del frontend de ese entorno.

---

## 5. Operación

```powershell
sam logs --stack-name soft-black-frontend-api-dev --profile soft-black-frontend-dev --tail          # todas las funciones
sam logs -n Dashboard1Function --stack-name soft-black-frontend-api-dev --profile soft-black-frontend-dev --tail
sam delete --stack-name soft-black-frontend-api-dev --profile soft-black-frontend-dev              # la tabla se conserva (Retain)
```

- **Iterar rápido en `dev`:** `sam sync --stack-name soft-black-frontend-api-dev --profile soft-black-frontend-dev --watch` sube los cambios de código en segundos. **Nunca contra `prod`.**

---

## 6. Local

| Qué | Cómo | Nota |
|---|---|---|
| Lógica, handlers y adaptadores | `uv run poe test` | Es lo principal: no requiere AWS ni Docker |
| Invocar una función con un evento | `sam local invoke PlatformFunction -e events/health.json` | Requiere Docker |
| API local | `sam local start-api` | Requiere Docker. **No valida el JWT de Cognito** en local: las pruebas de autorización se hacen con tests o en `dev` |

---

## 7. CI/CD (cuando haya servidor de git)

Pipeline mínimo:

1. `uv sync --frozen` → `uv run poe verify`.
2. Rama `develop` → `sam build && sam deploy --config-env dev` con un rol de despliegue de la cuenta DEV (OIDC, sin llaves guardadas).
3. Rama `main` → lo mismo con `--config-env prod` y aprobación manual.

---

## 8. Checklist

- [ ] Perfiles `soft-black-frontend-dev` y `soft-black-frontend-prod` apuntan a las cuentas correctas (`get-caller-identity`).
- [ ] `samconfig.toml` completo para ambos entornos, sin secretos.
- [ ] Grupos con el mismo nombre en ambos User Pools.
- [ ] `ApiUrl` de cada entorno configurada en el frontend correspondiente.
- [ ] `AllowedOrigins` de `prod` = dominio real del frontend.
