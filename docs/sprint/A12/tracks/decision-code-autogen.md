---
id: TRACK-decision-code-autogen
type: track
title: "Track Decision.code server-generated — PR único cross-cutting"
sprint: A12
lane: "[[A12.decision-code-autogen]]"
status: consumed
created_at: "2026-05-15"
consumed_at: "2026-05-15"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/consumed
  - area/backend
  - area/frontend
  - breaking/api
---

# Track Decision.code server-generated

> **Lane:** [[A12.decision-code-autogen]] · **ADR canônica:** [[ADR-214]]
> · **Branch:** `agent/decision-code-autogen/<yyyyMMdd-HHmm>` (1 PR único)
> · **Supervisão obrigatória:** **senior-cto** (geração no repo + use
> case); **data-engineer** revisa migration + audit pré-`VALIDATE`;
> **product-designer** já aprovou cleanup de UX (sessão 2026-05-15).

## Briefing (1 frase)

Mover geração de `Decision.code` (D01..D{1,3}) do cliente para o
servidor, com `pg_advisory_xact_lock` per-workspace, remover inputs
correspondentes dos 3 modais de frontend, e adicionar
`accepted_decision_code` no `SuggestionResponse` para toast pós-criação.

## Por que ler [[ADR-214]] antes de codar

A ADR é o plano: §Decisão detalha a estratégia de lock + repo + DTO
mudanças, §Alternativas justifica a escolha de Opção A vs counter table
(B), §Consequências lista riscos com mitigação. **Não duplique conteúdo
da ADR neste track** — referencie seção.

## Inventário (arquivos tocados)

### Backend

- **Migration nova:** `backend/alembic/versions/<hash>_add_check_decisions_code_canonical.py`
  - `op.execute("ALTER TABLE decisions ADD CONSTRAINT chk_decisions_code_canonical CHECK (code ~ '^D\\d+$') NOT VALID")`
  - `op.execute("ALTER TABLE decisions VALIDATE CONSTRAINT chk_decisions_code_canonical")`
  - Downgrade: `op.execute("ALTER TABLE decisions DROP CONSTRAINT chk_decisions_code_canonical")`
- **Repo protocol:** [`backend/app/application/decisions/_protocols.py`](../../../../backend/app/application/decisions/_protocols.py)
  - Adicionar `async def next_code(self, workspace_id: UUID) -> str: ...`
- **Repo impl:** [`backend/app/repositories/decision_repository.py`](../../../../backend/app/repositories/decision_repository.py)
  - Implementar `next_code` com `pg_advisory_xact_lock` + `SELECT MAX + 1` na mesma sessão (caller controla tx).
- **Use case:** [`backend/app/application/decisions/create_decision.py`](../../../../backend/app/application/decisions/create_decision.py)
  - Adicionar parâmetro `code: str | None = None`; se `None`, chama `repo.next_code(workspace_id)`.
  - Remover lookup `repo.get_by_code` + `ConflictError("duplicate_code")` (linhas ~24-29) — lock garante invariante por construção; `UNIQUE` continua como defesa em profundidade no schema.
- **Use case Accept:** [`backend/app/application/suggestions/accept_suggestion.py`](../../../../backend/app/application/suggestions/accept_suggestion.py)
  - Remover `code=cmd.decision_code` na construção de `DecisionCreateCommand`; deixa server gerar.
  - Popular `accepted_decision_code` no `SuggestionResponse` retornado (campo novo).
- **DTOs:**
  - [`backend/app/schemas/dto/suggestion/command.py`](../../../../backend/app/schemas/dto/suggestion/command.py) — remover `decision_code` de `AcceptSuggestionCommand` + `ModifySuggestionCommand`.
  - [`backend/app/schemas/dto/decision/command.py`](../../../../backend/app/schemas/dto/decision/command.py) — remover `code` obrigatório de `DecisionCreateCommand`; tornar `code: str | None = None`.
  - [`backend/app/schemas/dto/suggestion/response.py`](../../../../backend/app/schemas/dto/suggestion/response.py) — adicionar `accepted_decision_code: str | None = None`.
- **Endpoint:** [`backend/app/api/suggestions.py`](../../../../backend/app/api/suggestions.py) — sem mudança de signature (DTO muda; rota mantém).
- **Endpoint manual:** se houver `POST /workspaces/{id}/decisions` aceitando code do body, remover campo do request schema (verificar antes de mexer; pode não existir uso direto).

### Frontend

- `../../../../frontend/src/app/(app)/acao/_components/SuggestionDialogs.tsx` (linhas 45-118 e 130-220) — remover input "Código da decisão" em `AcceptDialog` + `ModifyDialog`; signature de `onAccept` / `onModify` perde `code`.
- `../../../../frontend/src/app/(app)/acao/_components/InboxTab.tsx` — deletar função `computeNextDecisionCode` (linhas 165-172); remover prop drilling `nextDecisionCode`.
- `../../../../frontend/src/app/(app)/plano/_components/DecisionFormDialog.tsx` — remover `FormField` do `code` (linhas 262-271); manter header `Editar decisão D02` no modo edit (code já vem do registro); modo create → header `"Nova decisão"` sem code; remover `code` de `FormValues` + `validateForm` na criação.
- **Toast pós-aceite:** acrescentar microcopy `"Decisão {code} criada"` consumindo `accepted_decision_code` do response (componente de toast existente; verificar arquivo onde mensagem é montada após aceite).
- **Types regen:** `frontend/src/generated/` regenerado após `make update-openapi-snapshot`.

### Tests

- **Novo:** `backend/tests/integration/test_multi_worker_concurrency.py` — adicionar `test_concurrent_decision_creation_no_code_collision`:
  - Setup: workspace fixture, repo real (sqlite-memory ou Postgres em CI).
  - Act: `asyncio.gather` de 10 chamadas paralelas a `create_decision`.
  - Assert: 10 codes únicos, sequenciais `D01..D10`, sem `IntegrityError`, zero gaps.
- **Atualizar:** testes que enviam `decision_code` em DTOs (Accept/Modify/CreateDecision) — remover campo do payload.
- **FakeDecisionRepository:** implementar `next_code` com `max + 1` sobre dict interno (determinístico).

### Doc

- `docs/CHANGELOG.md` — entry de 1 linha referenciando esta lane + ADR-214.
- [[ADR-214]] flippada `Proposto` → `Decidido (A12)` no frontmatter, no mesmo PR.
- [[ADR-136]] nota cross-link **já adicionada** no PR do track (commit `docs(adr): cross-link ADR-136 → ADR-214`).

## Etapas (ordem sugerida)

1. **Migration + audit pré-merge.** Rodar `SELECT workspace_id, code FROM decisions WHERE code !~ '^D\d+$'` em dump de staging/prod. Se aparecer row, decidir case-a-case antes (rename ou exclude na constraint via `WHERE` em índice parcial — improvável).
2. **Backend — repo + use case.** Adicionar `next_code` em protocol + repo impl + `FakeDecisionRepository`. Update `create_decision` para chamar quando `code is None`. Remover lookup duplicado.
3. **Backend — DTOs + endpoint.** Remover `decision_code`/`code` dos 3 commands. Adicionar `accepted_decision_code` em `SuggestionResponse`. `make update-openapi-snapshot` + commit snapshot diff.
4. **Frontend — cleanup.** Remover inputs em 3 componentes. Deletar `computeNextDecisionCode`. Ajustar toast. Regenerar tipos. Build verde.
5. **Tests.** Adicionar teste de concorrência. Atualizar testes que enviam `decision_code`. Suíte verde.
6. **Doc.** CHANGELOG entry. Flip ADR-214 status. Verificar nota em ADR-136 (já feita).

## Validação

```bash
# Audit pré-VALIDATE (rodar antes de mergear)
psql -c "SELECT workspace_id, code FROM decisions WHERE code !~ '^D\d+$'"

# Migration round-trip
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# Backend
pytest backend/tests -q
pytest backend/tests/integration/test_multi_worker_concurrency.py::test_concurrent_decision_creation_no_code_collision -q

# Pipeline (smoke)
pytest tests -q

# Frontend
cd frontend && npm test -- --run
npm run build

# Grep guards
grep -rn "decision_code" backend/app/schemas/dto/   # = 0
grep -rn "computeNextDecisionCode" frontend/src/     # = 0

# Pre-commit
pre-commit run --all-files
```

## Commit message sugerida

```
refactor(decisions): server-generate Decision.code with advisory lock (ADR-214)

- decisions.code agora gerado server-side via pg_advisory_xact_lock per-workspace
- DTOs perdem decision_code/code; SuggestionResponse ganha accepted_decision_code
- Frontend remove input "Código da decisão" em 3 modais; toast educa pós-criação
- CHECK constraint canoniza convenção '^D\d+$' no schema
- Teste de concorrência em test_multi_worker_concurrency.py
- Estende ADR-136 (invariantes preservados; muda apenas quem gera)

Breaking: clientes externos que enviavam decision_code recebem 422.
Único consumer é o frontend Next.js, regenerado neste mesmo PR.
```

## Decisões já tomadas ([[ADR-214]])

- **Opção A** (`pg_advisory_xact_lock` + `MAX + 1`) escolhida sobre Opção B (counter table) por YAGNI; `CHECK` constraint protege regressão.
- **Gap em codes aceitável** — code é editorial, não contábil.
- **Use case interno mantém `code: str | None` opcional** — importer/migrator continua funcionando.
- **Form manual em `/plano`** — header `"Nova decisão"` sem code (não há preview); toast pós-criação exibe `"Decisão D03 criada"`.
- **Override editorial** (pular números) — YAGNI; não previsto.

## Ligações

- ADR canônica: [[ADR-214]] (Proposto)
- Estende: [[ADR-136]]
- Aderente a: [[ADR-111]] (gate empírico de concorrência), [[ADR-097]] D3 (ISP), [[ADR-109]] (OpenAPI)
- Lane: [[A12.decision-code-autogen]]
