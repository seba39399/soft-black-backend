# 06 — Fuentes de datos

> Los datos pueden venir de DynamoDB, de bases SQL, de S3 o de otras fuentes. El dominio y los casos de uso **no saben cuál**: piden un **puerto** y un **adaptador** lo cumple.

---

## 1. El patrón (igual para todas las fuentes)

```
caso de uso ──usa──▶ puerto (Protocol en application/ports/)
                          ▲
                          │ implementa
      ┌───────────────────┼───────────────────┬────────────────────┐
 outbound/dynamodb/   outbound/sql/        outbound/s3/        outbound/athena/
```

1. El **puerto** describe *qué* necesita el caso de uso, en términos del dominio (`list_page(limit, position) -> (items, next_position)`), nunca *cómo*.
2. Cada **adaptador** traduce a su tecnología y devuelve **entidades del dominio**.
3. El **handler** (composition root) elige qué adaptador inyectar.
4. **Cambiar de fuente** = otro adaptador + otra línea en `build_use_case()`. El dominio y el caso de uso no cambian.

**Paginación:** cada adaptador devuelve su "posición" como `dict`. El handler la convierte en `nextCursor` con `encode_cursor` y la recupera con `decode_cursor` ([04 §4](./04-contrato-api.md#4-paginación-por-cursor)). El frontend nunca ve de qué fuente vino.

---

## 2. DynamoDB

**Cuándo:** datos propios del backend con patrones de acceso conocidos (por clave o por rango de claves), alta concurrencia, escrituras simples.

- **Single-table:** una tabla `soft-black-frontend-<stage>` con `PK` y `SK` genéricas. Se agregan GSIs solo cuando un patrón de acceso lo exige.
- **Diseño de claves por entidad**, documentado en el docstring del repositorio:
  ```
  PK = "DASHBOARD_1"            SK = "INDICADOR#<id>"
  ```
- La forma de las claves **solo** existe en `adapters/outbound/dynamodb/`.
- **Posición de paginación:** `LastEvaluatedKey` → `ExclusiveStartKey`.
- **Evita** `Scan` en endpoints: siempre `Query` por clave. Un `Scan` crece con la tabla y la paga cada request.
- **Tests:** `moto` (`tests/conftest.py` crea la tabla).
- **IAM:** `DynamoDBReadPolicy` o `DynamoDBCrudPolicy` de `AppTable`.

Ejemplo completo: [02 §6, paso 6](./02-arquitectura.md#paso-6--adaptador-de-salida).

---

## 3. Bases SQL (RDS / Aurora: PostgreSQL, MySQL, SQL Server)

**Cuándo:** los datos ya viven en una base relacional de la empresa, o se necesitan joins, agregaciones y filtros ad hoc.

**Arquitectura obligatoria:**

```
Lambda (en subredes privadas de la VPC) ──▶ RDS Proxy ──▶ RDS / Aurora
        │
        └─ credenciales: Secrets Manager (leídas con Powertools Parameters, con caché)
```

| Pieza | Por qué |
|---|---|
| **Lambda en la VPC** (`VpcConfig` con subredes privadas y security group) | La base no se expone a internet |
| **RDS Proxy** | Lambda escala a cientos de instancias; sin proxy, cada una abre conexiones y agota el límite de la base |
| **Secrets Manager** | Sin usuario ni contraseña en código, variables o `samconfig.toml`. Rotación sin redesplegar |
| **Usuario de solo lectura** para dominios de lectura | Mínimo privilegio también en la base |

**Reglas del adaptador `outbound/sql/`:**

- Driver fijado en `[project.dependencies]` (por ejemplo `psycopg[binary]` para PostgreSQL). Revisa que publique wheels Linux `aarch64` ([08 §4](./08-entorno-y-despliegue.md#4-build-y-despliegue)).
- La conexión se crea **fuera del handler** (una por contenedor) y se reutiliza entre invocaciones.
- **Siempre consultas parametrizadas.** Nunca concatenar texto del request en el SQL.
- **Paginación por *keyset***, no `OFFSET`: `WHERE (fecha, id) < (:ultima_fecha, :ultimo_id) ORDER BY fecha DESC, id DESC LIMIT :limit`. La posición es `{"fecha": …, "id": …}`.
- Nombres de tablas y columnas solo en el adaptador.
- **Tests:** integración contra una base efímera (contenedor) o, como mínimo, tests del SQL generado con un doble de la conexión.

> **Pendiente de definir con la primera fuente SQL:** motor y versión, VPC y subredes por cuenta, nombre del secreto y driver. Se documenta aquí cuando llegue.

---

## 4. S3

**Cuándo:** archivos (CSV, JSON, Parquet, reportes generados) que se entregan tal cual o que son pequeños.

- **Archivos pequeños** (≤ unos pocos MB): el adaptador lee el objeto, lo parsea y devuelve entidades.
- **Descargas para el usuario:** no pases el archivo por la Lambda (el payload de API Gateway tiene un límite de ~6 MB). Devuelve una **URL prefirmada** de corta duración (`generate_presigned_url`, 5–15 min). El contrato la documenta como `{ "url": "...", "expiraEn": "..." }`.
- **Paginación:** `ContinuationToken` de `list_objects_v2`.
- **IAM:** `S3ReadPolicy` del bucket (o `S3CrudPolicy` si escribe).
- **Tests:** `moto` (`mock_aws` también simula S3).

---

## 5. Athena (datos grandes en S3)

**Cuándo:** consultas SQL sobre volúmenes grandes en S3 (data lake, históricos, Parquet).

- Athena es **asíncrono** y puede tardar más que el límite HTTP (~12 s útiles, [05 §6](./05-infraestructura-sam.md#6-timeouts-y-memoria)). Patrones:
  - Consultas rápidas y acotadas (particiones por fecha, columnas mínimas): síncrono, esperando el resultado con timeout.
  - Consultas pesadas: el endpoint arranca la consulta y devuelve `202` con `queryId`; otro endpoint consulta el estado y el resultado.
- **Paginación:** `NextToken` de `get_query_results`.
- **IAM:** `AthenaQueryPolicy` del workgroup + `S3ReadPolicy` del bucket de datos + escritura en el bucket de resultados (y Glue si aplica).
- **Costo:** Athena cobra por datos escaneados. Particiona y usa formatos columnares (Parquet).

---

## 6. Otras fuentes (APIs internas, etc.)

Mismo patrón: `adapters/outbound/<nombre>/` implementa el puerto. Credenciales en Secrets Manager, timeouts explícitos menores al de la Lambda y errores de la fuente traducidos a errores de dominio (nunca se filtra la respuesta cruda).

---

## 7. Checklist por fuente nueva

- [ ] Puerto en `application/ports/` en términos del dominio.
- [ ] Adaptador en `adapters/outbound/<fuente>/` que devuelve entidades.
- [ ] Paginación por posición → cursor.
- [ ] Credenciales en Secrets Manager (nunca en código ni en `samconfig.toml`).
- [ ] IAM mínimo en la función del dominio.
- [ ] Tests del adaptador (moto, contenedor o doble).
- [ ] Sección de esta fuente actualizada en este doc.
