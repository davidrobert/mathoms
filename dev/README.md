# `dev/` — Tooling de desenvolvimento

Esta pasta contém **ferramentas de engenharia** do repositório Fin.
**Não é código de produto** nem etapa do pipeline — são atalhos e hooks
usados por desenvolvedores e pelo CI para manter o repo saudável.

Diferença conceitual:

| Pasta        | Conteúdo                                         |
| ------------ | ------------------------------------------------ |
| `scripts/`   | Pipeline legado (E0–E7, determinístico) e utils  |
| `backend/`   | API FastAPI, modelos, serviços do produto        |
| `frontend/`  | SPA Next.js                                      |
| **`dev/`**   | **Dev tooling: commit, hooks, validadores**      |

## Dados no disco (o que os hooks bloqueiam)

- **`storage/`** na raiz do repo — árvore **multi-tenant** do backend
  (``storage/<workspace_id>/data/…``, ``inbox/``, ``processed/``, …). Nunca
  versionar: contém PDFs e artefatos por workspace.
- **`data/`**, **`inbox/`**, **`inbox_processed/`** na raiz — fluxo **CLI**
  single-tenant (pipeline legado em ``scripts/``), também ignorados pelo git.

Os hooks (`check_forbidden_paths`, lógica espelhada em `commit.py`) bloqueiam
ambos os mundos para evitar vazamento acidental de dados.

## Arquivos

- **`commit.py`** — wrapper opinado para `git add -A && git commit && git push`
  com guardrails (paths proibidos, mensagem validada, dry-run). Substitui o
  antigo `scripts/e_save.py`.

  ```bash
  python dev/commit.py -m "feat(api): endpoint de export do workspace"
  python dev/commit.py --dry-run -m "docs: ADR-068"
  python dev/commit.py --no-push -m "fix: corrigir classificação PDF"
  ```

- **`check_forbidden_paths.py`** — hook de `pre-commit` que bloqueia staging
  de `storage/`, `data/`, `inbox/`, `fin.db`, `.env`, etc. Protege contra
  vazamento de dados de usuário para o GitHub caso o `.gitignore` seja
  alterado sem querer.

- **`validate_commit_msg.py`** — hook `commit-msg` de `pre-commit` que
  valida o prefixo da mensagem. Lista de prefixos aceitos está no próprio
  arquivo (`VALID_PREFIXES`).

## Instalar os hooks

```bash
pip install pre-commit
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
```

Daí em diante, qualquer `git commit` (não só via `dev/commit.py`) passa
pelas validações.

## Rodar hooks manualmente

```bash
pre-commit run --all-files                    # todos os hooks em todo o repo
pre-commit run forbidden-paths --all-files    # só o check de paths
```

## Por que não fica em `scripts/`?

`scripts/` é o hub do **pipeline legado single-tenant** (`e0_*.py`,
`e2_*.py`, …). Misturar tooling de dev lá confunde quem está lendo: dá a
impressão de que `commit.py` é uma etapa do pipeline. Desde a migração para
produto web multi-tenant, os dois mundos estão claramente separados.
