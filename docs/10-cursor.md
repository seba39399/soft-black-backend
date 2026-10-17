# 10 — Trabajar con Cursor

> Cómo se reparte la información entre `docs/`, `.cursor/rules/`, `docs/agente/` y las skills del backend.

---

## 1. Quién es la fuente de qué

| Dónde | Qué contiene |
|---|---|
| `docs/` (00–11) | **Las normas**: arquitectura, auth, contrato, infraestructura, datos, convenciones, git |
| `docs/contrato/openapi.yaml` | **El contrato** con el frontend |
| `docs/agente/` | **Fuente** de las reglas cortas para el agente y del procedimiento `nuevo-endpoint` |
| `.cursor/rules/*.mdc` | Las reglas de `docs/agente/` con su *frontmatter* de Cursor (copia) + `proyecto.mdc` |
| `.cursor/skills/nuevo-endpoint/` | `/nuevo-endpoint`: lee el procedimiento de `docs/agente/` |

Si cambias una regla, edita `docs/agente/<archivo>.md` y vuelve a copiarla al `.mdc`. Si una regla y un doc numerado se contradicen, manda el doc.

---

## 2. Reglas (`.cursor/rules/`)

| Archivo | Tipo | Cuándo se aplica |
|---|---|---|
| `proyecto.mdc` | `alwaysApply: true` | Siempre: comandos, despliegue, git, secretos |
| `arquitectura.mdc` | `alwaysApply: true` | Siempre: capas, Powertools, reglas del handler, `poe verify` |
| `git-workflow.mdc` | `alwaysApply: true` | Siempre: resumen de [09](./09-git.md) |
| `contrato.mdc` | `globs: docs/contrato/**` | Al tocar el contrato |
| `auth.mdc` | `globs: src/adapters/inbound/auth/**,src/shared/authz.py` | Al tocar identidad o permisos |
| `infraestructura.mdc` | `globs: template.yaml,samconfig.toml` | Al tocar la infraestructura |

---

## 3. Uso diario

Abre `C:\Users\Subocol\Documents\soft-black-frontend-backend` en Cursor (modo **Agent**).

- **Agregar un endpoint:** `/nuevo-endpoint resumen de ventas por región entre dos fechas, desde DynamoDB, para admin y ventas`. El agente se detiene con la propuesta del contrato y espera tu aprobación.
- **Cambio grande:** modo **Plan** o un `SPEC.md` primero.
- **Nombres:** nombre de la tarea = rama = recurso = dominio: `ventas` ↔ `feature/ventas` ↔ `ventas_api.py` ↔ `RESOURCE_GROUPS["ventas"]`.
- **Antes de terminar:** `uv run poe verify` en verde. El agente no despliega salvo que se lo pidas.

---

## 4. Agregar un procedimiento nuevo

1. Pasos en `docs/agente/<nombre>.md`, enlazando a los docs numerados.
2. `.cursor/skills/<nombre>/SKILL.md` con `name`, `description` y "Lee `docs/agente/<nombre>.md` y síguelo exactamente".
3. Menciónalo en `.cursor/rules/proyecto.mdc`.

---

## Opcional: seguimiento de tareas con Task Master (MCP)

Cursor no guarda el avance de las tareas entre sesiones. Si lo necesitas, agrega el servidor MCP **Task Master AI**: convierte un documento de requisitos en tareas con dependencias, te dice cuál sigue y guarda el estado en el proyecto (carpeta `.taskmaster/`).

1. Crea `.cursor/mcp.json`:
   ```json
   {
     "mcpServers": {
       "task-master-ai": {
         "command": "npx",
         "args": ["-y", "task-master-ai"],
         "env": { "ANTHROPIC_API_KEY": "<tu llave>" }
       }
     }
   }
   ```
   Task Master llama a un modelo con **su propia llave de API** (Anthropic, OpenAI u otro proveedor que soporte). No la subas a git: agrega `.cursor/mcp.json` a `.gitignore` o usa una variable de entorno del sistema.
2. Reinicia Cursor y revisa en *Settings → MCP* que aparezca activo.
3. En el chat: "Inicializa Task Master en este proyecto", luego "Genera las tareas a partir de `<tu-spec>.md`" y "¿Cuál es la siguiente tarea?".

Documentación: <https://github.com/eyaltoledano/claude-task-master>.
