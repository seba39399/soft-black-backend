# 05 — Infraestructura con AWS SAM

> Todo lo que se despliega está en `template.yaml`, y los valores por entorno en `samconfig.toml` ([08](./08-entorno-y-despliegue.md)). Este `template.yaml` pasa `sam validate --lint`.

---

## 1. Qué se despliega

| Recurso | Tipo | Para qué |
|---|---|---|
| `HttpApi` | `AWS::Serverless::HttpApi` | Rutas, CORS, throttling y authorizer JWT de Cognito por defecto |
| `PlatformFunction` | `AWS::Serverless::Function` | `/v1/health` (pública) y `/v1/me/permissions` |
| `<Dominio>Function` | `AWS::Serverless::Function` | Una por dominio/dashboard, con sus rutas y su IAM |
| `AppTable` | `AWS::DynamoDB::Table` | Tabla single-table (si el dominio usa DynamoDB; ver [06](./06-fuentes-de-datos.md)) |
| Salida `ApiUrl` | Output | Valor de `NEXT_PUBLIC_API_BASE_URL` del frontend |

---

## 2. `template.yaml` completo

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: soft-black-frontend API (Python 3.13 + Powertools + API Gateway HTTP API + Cognito)

Parameters:
  Stage:
    Type: String
    AllowedValues: [dev, prod]
  CognitoUserPoolId:
    Type: String
    Description: User Pool de ESTA cuenta/entorno (ej. us-east-1_AbC123)
  CognitoClientIds:
    Type: CommaDelimitedList
    Description: App Clients públicos que pueden llamar a la API (audiencia del JWT)
  AllowedOrigins:
    Type: CommaDelimitedList
    Description: Orígenes del frontend (CORS), ej. http://localhost:3000
  LogLevel:
    Type: String
    Default: INFO
    AllowedValues: [DEBUG, INFO, WARNING, ERROR]

Conditions:
  IsProd: !Equals [!Ref Stage, prod]

Globals:
  Function:
    Runtime: python3.13
    Architectures: [arm64]
    CodeUri: src/
    MemorySize: 256
    Timeout: 10 # por defecto; cada función puede sobrescribirlo (máx. útil ~12 s, ver docs 05 §6)
    Tracing: Active
    Environment:
      Variables:
        STAGE: !Ref Stage
        TABLE_NAME: !Ref AppTable
        POWERTOOLS_SERVICE_NAME: soft-black-frontend-api
        POWERTOOLS_LOG_LEVEL: !Ref LogLevel

Resources:
  HttpApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Stage
      CorsConfiguration:
        AllowOrigins: !Ref AllowedOrigins
        AllowHeaders: [Authorization, Content-Type]
        AllowMethods: [GET, POST, PUT, PATCH, DELETE, OPTIONS]
        MaxAge: 600
      DefaultRouteSettings:
        ThrottlingBurstLimit: !If [IsProd, 100, 20]
        ThrottlingRateLimit: !If [IsProd, 50, 10]
      Auth:
        DefaultAuthorizer: CognitoJwt # toda ruta protegida salvo Auth NONE explícito
        Authorizers:
          CognitoJwt:
            IdentitySource: $request.header.Authorization
            JwtConfiguration:
              issuer: !Sub https://cognito-idp.${AWS::Region}.amazonaws.com/${CognitoUserPoolId}
              audience: !Ref CognitoClientIds

  # ── Rutas transversales: /v1/health y /v1/me/permissions ─────────────────
  PlatformFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: adapters.inbound.http.platform_api.handler
      Events:
        Health:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/health
            Method: GET
            Auth:
              Authorizer: NONE # única ruta pública
        MyPermissions:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/me/permissions
            Method: GET

  # ── Dominio dashboard_1: una función por dominio, todas sus rutas ────────
  Dashboard1Function:
    Type: AWS::Serverless::Function
    Properties:
      Handler: adapters.inbound.http.dashboard_1_api.handler
      Policies:
        - DynamoDBReadPolicy: # solo lectura
            TableName: !Ref AppTable
      Events:
        ListarIndicadores:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/dashboard_1/indicadores
            Method: GET

  AppTable:
    Type: AWS::DynamoDB::Table
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Properties:
      TableName: !Sub soft-black-frontend-${Stage}
      BillingMode: PAY_PER_REQUEST
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: !If [IsProd, true, false]
      AttributeDefinitions:
        - { AttributeName: PK, AttributeType: S }
        - { AttributeName: SK, AttributeType: S }
      KeySchema:
        - { AttributeName: PK, KeyType: HASH }
        - { AttributeName: SK, KeyType: RANGE }

Outputs:
  ApiUrl:
    Description: Valor para NEXT_PUBLIC_API_BASE_URL del frontend (sin barra final)
    Value: !Sub https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/${Stage}
```

> `Dashboard1Function` y sus rutas son el **ejemplo** de [02 §6](./02-arquitectura.md#6-agregar-un-endpoint-paso-a-paso) y vienen en el esqueleto. Al crear tu primer dominio real, bórralos junto con su código, sus tests y su entrada en `openapi.yaml`.

---

## 3. Decisiones del template

| Decisión | Por qué |
|---|---|
| `Runtime: python3.13`, `Architectures: [arm64]` | Graviton: más barato por ms y arranque similar. `sam build` baja las dependencias para Linux arm64 |
| `CodeUri: src/` global | Todas las funciones comparten el código. Cada una solo importa lo suyo (el handler define qué módulos se cargan) |
| `DefaultAuthorizer: CognitoJwt` | **Seguro por defecto:** una ruta nueva queda protegida sin hacer nada. Abrirla exige `Auth: { Authorizer: NONE }` explícito |
| `CorsConfiguration` con `AllowOrigins` por parámetro | Solo el frontend del entorno puede llamar desde el navegador. API Gateway agrega los headers CORS a todas las respuestas, incluidos los 401 del authorizer |
| `DefaultRouteSettings` (throttling) | Defensa básica contra abuso: más bajo en `dev` y más alto en `prod`. No reemplaza la autenticación |
| `Tracing: Active` | Traza básica de X-Ray sin agregar dependencias |
| `AppTable` con `DeletionPolicy: Retain` | Borrar el stack **no** borra los datos |
| `PointInTimeRecovery` solo en `prod` | Recuperación a un punto en el tiempo donde importa; en `dev` se ahorra el costo |
| `POWERTOOLS_SERVICE_NAME` / `POWERTOOLS_LOG_LEVEL` | Configuran el `Logger` de Powertools sin código |

---

## 4. Agregar la función de un dominio

```yaml
  VentasFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: adapters.inbound.http.ventas_api.handler
      # Timeout: 12             # solo si difiere del global (ver §6)
      Policies:
        - DynamoDBReadPolicy:   # o DynamoDBCrudPolicy si escribe
            TableName: !Ref AppTable
      Events:
        Resumen:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/ventas/resumen
            Method: GET
        Detalle:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /v1/ventas/detalle/{id}
            Method: GET
```

- **Una función por dominio** con **todas** sus rutas como `Events`. Cada ruta nueva del resolver necesita su `Event`: si no, API Gateway responde 404 aunque el código la tenga.
- El `Handler` es la ruta Python del módulo `*_api.py` + `.handler`.
- Nombres: `<Dominio>Function` en PascalCase; el módulo, `<dominio>_api.py`.

---

## 5. IAM mínimo: plantillas de políticas de SAM

Cada función declara **solo** lo que usa, con las plantillas de políticas de SAM:

| Necesita | Plantilla |
|---|---|
| Leer DynamoDB | `DynamoDBReadPolicy: { TableName: !Ref AppTable }` |
| Leer y escribir DynamoDB | `DynamoDBCrudPolicy: { TableName: !Ref AppTable }` |
| Leer un bucket S3 | `S3ReadPolicy: { BucketName: <bucket> }` |
| Leer un secreto (credenciales SQL) | `AWSSecretsManagerGetSecretValuePolicy: { SecretArn: <arn> }` |
| Leer parámetros SSM | `SSMParameterReadPolicy: { ParameterName: <ruta-sin-slash-inicial> }` |
| Consultar Athena | `AthenaQueryPolicy: { WorkGroupName: <wg> }` + `S3ReadPolicy` del bucket de datos + `S3CrudPolicy` del bucket de resultados |

- Nada de `Resource: "*"` ni políticas administradas amplias (`AmazonDynamoDBFullAccess`, etc.).
- Un dominio de **solo lectura** nunca tiene permisos de escritura.
- `PlatformFunction` no tiene políticas de datos: no toca ninguna fuente.

---

## 6. Timeouts y memoria

- **Por defecto** (`Globals`): `Timeout: 10` y `MemorySize: 256`. Cada función puede sobrescribirlos en sus `Properties`.
- **Límites que no se configuran:**
  - API Gateway HTTP corta a los **30 s**, pase lo que pase en la Lambda.
  - El frontend corta a los **15 s** (`apiFetch`).
  - Por eso, en funciones HTTP, **el timeout útil máximo es ~12 s**. Por encima de eso, el usuario ve "No se pudo conectar" aunque la Lambda termine bien.
- **Si algo tarda más:** no se hace dentro del request. Opciones: la Lambda deja un trabajo en una cola (SQS) o arranca otra Lambda, y responde `202` con un id; el frontend consulta el estado.
- **Memoria:** en Lambda, más memoria = más CPU. Si una función es lenta por cálculo, prueba 512–1024 MB antes de subir el timeout.

---

## 7. Checklist

- [ ] `sam validate --lint` en verde (incluido en `poe verify`).
- [ ] Toda ruta nueva tiene su `Event` en la función de su dominio.
- [ ] Rutas públicas marcadas con `Auth: { Authorizer: NONE }` y documentadas en el contrato con `security: []`.
- [ ] Políticas IAM mínimas por función.
- [ ] `Timeout` de funciones HTTP ≤ 12 s.
