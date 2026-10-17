# Git — resumen operativo

Norma completa en `docs/09-git.md`. Lo mínimo:

- Rama `<tipo>/<nombre>` (`feature|fix|chore|docs`) desde `develop`, **antes** de implementar. `<nombre>` = nombre del feature o de la tarea.
- Commits: `<slug>: <hito> — <resumen en español>`. El cambio al contrato va en su propio commit, antes del código.
- `git add <ruta>` por archivo. `uv.lock` y `src/requirements.txt` junto con el `pyproject.toml` que los cambió.
- **Nunca `git push` sin confirmación explícita del usuario.**

Lee antes de empezar: `docs/09-git.md`
