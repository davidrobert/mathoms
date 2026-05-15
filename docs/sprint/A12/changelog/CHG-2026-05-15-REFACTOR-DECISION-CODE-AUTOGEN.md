---
id: CHG-2026-05-15-REFACTOR-DECISION-CODE-AUTOGEN
type: changelog-entry
date: "2026-05-15"
sprint: A12
lane: "[[A12.decision-code-autogen]]"
prs: []
commits: []
summary: |
  refactor(decisions): Decision.code passa a ser server-generated com
  pg_advisory_xact_lock per-workspace. UI perde input "Código da decisão"
  em 3 modais; toast pós-aceite educa via accepted_decision_code.
breaking: true
tags:
  - type/changelog-entry
  - sprint/a12
  - area/backend
  - area/frontend
  - breaking/api
adrs:
  - "[[ADR-214]]"
  - "[[ADR-136]]"
---

# refactor(decisions): Decision.code server-generated (ADR-214)

Implementação da lane [[A12.decision-code-autogen]] / [[ADR-214]] —
fecha race condition (2 abas aceitando sugestão → `UNIQUE` collision)
e cleanup UX validado por `product-designer` (sessão 2026-05-15).

**Backend:**

- `DecisionRepository.next_code(workspace_id)` — Postgres usa
  `pg_advisory_xact_lock(hashtextextended('decision_code:' || ws, 0))`
  na transação corrente; SQLite (testes) usa fallback Python sem lock
  (file + StaticPool serializa naturalmente).
- Migration `adr214checkcode_decision_code_canonical` — `CHECK (code ~ '^D[0-9]+$')`
  em Postgres (defesa em profundidade); skipped em SQLite (operador `~`
  não suportado).
- `DecisionCreateCommand.code` agora `Optional[str]` — quando `None`,
  use case chama `repo.next_code` e usa o resultado.
- `AcceptSuggestionCommand` / `ModifySuggestionCommand` perderam
  `decision_code` (forbid → 422 se enviado).
- `SuggestionResponse` ganhou `accepted_decision_code: Optional[str]`
  (additive) — populado por `accept_suggestion` / `modify_suggestion`.
- Use case interno mantém `code: Optional[str]` para importer/migrator
  one-shot.

**Frontend:**

- `SuggestionDialogs.tsx`: input "Código da decisão" removido em
  `AcceptDialog` + `ModifyDialog`. Foco vai pro CTA primário (aceite)
  e pro título (modificação). Toast usa `accepted_decision_code` do
  response.
- `DecisionFormDialog.tsx`: input "Código" removido do modo `create`;
  modo `edit` mantém code no header `Editar decisão D02` (read-only).
  Foco inicial vai pro título.
- `DecisionSupersedeDialog.tsx`: input "Código da nova decisão" removido;
  toast `Decisão D01 substituída por D02` usa `created.code` do response.
- `InboxTab.computeNextDecisionCode` deletado; `decisionsCopy.nextDecisionCode`
  deletado; `useSuggestionActions.SuggestionAcceptArgs.decisionCode` deletado.
- `ParecerMovimentoCard.handleAccept` não gera mais `PAR-XXXX` derivado
  do dedup_key (quirk que violava `^D\d+$`); usa code real do response.

**Testes:**

- `backend/tests/integration/test_multi_worker_concurrency.py` —
  `test_concurrent_decision_creation_no_code_collision` (10 POST
  encadeados → D01..D10 únicos sequenciais).
- `backend/tests/test_decision_use_cases.py` —
  `test_create_decision_auto_generates_code_when_omitted` (D01→D02→D03)
  + `test_create_decision_auto_gen_respects_existing_max` (legado D06+D15
  → próximo D16). `test_create_duplicate_code_raises_conflict` removido
  (UNIQUE constraint vira defesa em profundidade, não contrato HTTP).
- `backend/tests/test_decisions_api.py` —
  `test_create_without_code_auto_generates_sequence` substitui
  `test_create_duplicate_returns_409`.
- Frontend: blocos `describe("computeNextDecisionCode")` e
  `describe("nextDecisionCode")` deletados (cobertura migrou pra backend).
- OpenAPI snapshot regenerado.

**Breaking:** clientes externos que enviarem `decision_code` ou `code`
nos commands afetados recebem 422. Único consumer formal é o frontend
Next.js, regenerado neste PR.

**Decidiu:** [[ADR-214]] flippada `Proposto → Decidido (A12)`.
