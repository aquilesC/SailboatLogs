# Agent Guidelines for Sailboat Logs

## Git Rules

- **Never rewrite git history.** Do not use `git commit --amend`, `git rebase -i`, `git reset`, `git push --force`, or `git push --force-with-lease`. Every commit is final once created.
- Always create a **new commit** when fixing mistakes — even trivial ones.
- Write clear, conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`).
- Do not combine `git commit` and `git push` into a single chained command. Let the user review and push manually.
