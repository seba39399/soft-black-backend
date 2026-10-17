# 09 — Git: ramas, commits y trazabilidad

> Misma convención que el frontend, adaptada al backend. El historial es la bitácora: qué se hizo, en qué orden y bajo qué tarea. **Única copia**: `docs/agente/git-workflow.md` enlaza aquí.

---

## 1. Ramas

| Rama | Propósito | Despliega a |
|---|---|---|
| `main` | Producción. Siempre desplegable | Cuenta **PROD** |
| `develop` | Integración | Cuenta **DEV** |
| `<tipo>/<nombre>` | Trabajo | — (se prueba con `sam sync` en DEV si hace falta) |

`<tipo>`: `feature`, `fix`, `chore` o `docs`. `<nombre>`: el nombre del dominio o de la tarea, o un slug corto.

```
feature/ventas
feature/me-permissions
fix/cursor-invalido
chore/python-3-13
docs/guia-despliegue
```

```bash
git switch develop && git pull
git switch -c feature/<nombre>
```

Nadie commitea directo en `main` ni en `develop`. Una rama = una tarea.

---

## 2. Commits

```
<slug>: <hito> — <resumen en español>
```

```
ventas: requirements y design
ventas: contrato — GET /v1/ventas/resumen en openapi.yaml
ventas: tasks 1-3 — dominio, puerto y caso de uso
ventas: tasks 4-6 — repositorio DynamoDB, handler y template
fix: paginación — 400 con cursor corrupto
chore: dependencias — powertools 3.35.0
```

- **El cambio al contrato va en su propio commit**, antes del código: así el historial muestra que se acordó primero.
- Si hay un `SPEC.md` o plan escrito, se commitea antes que su implementación.
- `git add <ruta>` por archivo; nunca `git add .` ni `-A`.
- `uv.lock` y `src/requirements.txt` se commitean **juntos** con el `pyproject.toml` que los cambió.
- Sin `--amend` sobre commits pusheados ni `--no-verify`.

```bash
git log --oneline --grep="^ventas:"
```

---

## 3. Push, PRs y despliegue

- **No se hace `git push` sin confirmación explícita del responsable.** Aplica también al agente de Cursor.
- Antes de abrir el PR: `uv run poe verify`.
- PR a `develop` → se despliega a **DEV**. PR de `develop` a `main` → se despliega a **PROD**, con aprobación.
- Si el PR cambia el contrato, avisa al frontend y adjunta el `openapi.yaml`.

---

## 4. Archivos que **nunca** se versionan

`.venv/`, `.aws-sam/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.env`, llaves de AWS y archivos de eventos con tokens reales.

`.gitignore` mínimo:

```gitignore
.venv/
.aws-sam/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
.env.*
events/*.local.json
```

---

## 5. Finales de línea y codificación

`.gitattributes` con `* text=auto eol=lf` y `.editorconfig` con `charset = utf-8`, igual que el frontend. Evitan problemas de finales de línea (CRLF) y BOM en Windows.

---

## 6. Checklist por tarea

- [ ] Rama `<tipo>/<nombre>` desde `develop`.
- [ ] Commit del contrato antes del código.
- [ ] Commits por hito, staging por archivo.
- [ ] `uv run poe verify` en verde.
- [ ] Push solo con confirmación.
