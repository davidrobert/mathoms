# Sprint A9 — Ondas paralelas

> Sprint sem ondas paralelas formais. As 11 frentes (PRs #46–#56 + #60) correram em paralelo no mesmo dia (2026-05-05) — coordenação via PR-flow standard, sem diagrama de dependência prescrito.

Sequenciamentos práticos observados:
- **A9.B7** (drop legacy tables) precisou rebase pós-merge de outros PRs que mexiam em modelos SQLAlchemy.
- **A9.A1** (F9.3 Alembic) destravou F9.4 ao mergear — sequência da migração F9 (sprint A6) continuou após.
- **A9.N3 PR-A** (IFProjector v2) precedeu **N3 PR-B+C** (IFConeChart + wire E5) — chart consome output da projeção.
