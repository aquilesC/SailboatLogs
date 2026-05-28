# Agent Guidelines for Sailboat Logs

## Git Rules

- **Never rewrite git history.** Do not use `git commit --amend`, `git rebase -i`, `git reset`, `git push --force`, or `git push --force-with-lease`. Every commit is final once created.
- Always create a **new commit** when fixing mistakes — even trivial ones.
- Write clear, conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`).
- Do not combine `git commit` and `git push` into a single chained command. Let the user review and push manually.
- **Always finish work with a git commit.** After completing a task, create a commit with a clear, meaningful message describing the changes made.

## Python

- **Use `uv`** to run Python commands (e.g., `uv run python manage.py ...`, `uv run pytest`, etc.). Do not use bare `python` or `pip`.

## Django

- **Create migrations when necessary.** If model changes are made, run `uv run python manage.py makemigrations` to generate the corresponding migration files before committing.
