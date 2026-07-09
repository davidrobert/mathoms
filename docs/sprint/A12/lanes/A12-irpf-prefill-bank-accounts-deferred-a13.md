---
id: A12.irpf-prefill-bank-accounts
type: lane
title: "Pre-fill UI a partir de IRPF — V1 contas bancárias (deferred → A13)"
sprint: A12
status: shipped
aliases: ["A13.irpf-prefill-bank-accounts"]
priority: P2
depends_on: ["[[ADR-226]]"]
parallel_with: []
adrs_canonical:
  - "[[ADR-229]]"
tags:
  - type/lane
  - sprint/a12
  - status/shipped
  - priority/p2
  - area/backend
  - area/frontend
  - area/methodology
---

# A12.irpf-prefill-bank-accounts — Pre-fill IRPF V1 (deferred → A13)

> Lane **planejada para Sprint A13** (abre quando A11 → done e A12 → current). Mantida em `docs/sprint/A12/lanes/` apenas porque A13 ainda não existe como diretório (schema permite só 1 `sprint_status: candidate` por vez). Quando A13 abrir, mover para `docs/sprint/A13/lanes/` via `git mv`.

## Origem

Sessão de discussão 2026-05-20 pós-fechamento da lane A12.bank-account-disambig (ADR-226 entregue em 4 PRs). Usuário levantou pergunta sobre fricção do `/config` → Membros — cadastrar ~12 contas à mão é o ponto onde família multi-membro desiste do onboarding.

A informação **já existe** no Mathoms via E1 (`extract_members`, ADR-127) extraindo IRPF Ficha de Bens e Direitos código 61 — banco/agência/conta/CPF/saldo. Pós-PR3 da [[ADR-226]], E1 grava `contas[]` aditivo no artifact `members-1b_unified.json`. UI não usa.

Co-design 2026-05-20: `product-designer` (UX cards inline + diff modal âmbar + badge sunset por uso real + a11y + copy "você declarou") + `financial-planner` (Cerbasi/Perini/AUVP — IRPF como timeline anual + diff vs mesclagem silenciosa + zero telemetria omissão fiscal LGPD).

## Sequência (2 PRs)

| # | PR | Effort | Gate principal |
|---|---|---|---|
| 1 | **PR1** — Migration (`workspace_irpf_suggestion_dismissals` + `bank_accounts.irpf_snapshots JSONB`) + endpoint `GET .../suggestions-from-irpf` + use case + telemetria base | ~1d | Backend tests verdes; OpenAPI snapshot atualizado |
| 2 | **PR2** — UI cards inline + diff modal de conflito IRPF↔manual + dismissals + a11y + dogfood 3 famílias | ~1d | E2E flow verde; tempo médio cadastro < 2min em 3 famílias dogfood (vs >10min manual hoje) |

**Ordem obrigatória:** PR1 → PR2. PR1 é aditivo (zero risco runtime); PR2 expõe UI.

**Branch prefix:** `agent/irpf-prefill-bank-accounts-pr<N>/<yyyyMMdd-HHmm>`.

## Gates de promoção

- Cada PR mergeia em `main` independente (revertível via `git revert`).
- Suíte verde (`pytest backend/tests -q`, `pytest tests -q`, `cd frontend && npm test -- --run`).
- Pre-commit verde.
- PR2 exige **dogfood com 3 famílias** (tempo médio < 2min) antes de roll-out 100%.
- A11y AAA verificado em PR2 (cards teclado-navegáveis, badge `aria-label`, toast `role="status"`).

## Riscos principais (referência [[ADR-229]] §Consequências)

| Risco | P | Mitigação resumida |
|---|---|---|
| LLM falso-positivo descoberto após "Adicionar" | P1 | Badge "IRPF" pós-add com sunset por uso real; toast Undo 10s; campo "Origem: IRPF 2024" read-only |
| Telemetria "omissão fiscal" vazar (LGPD) | P0 | V1 não detecta; V2 explícito sem telemetria |
| Usuário confuso em diff modal IRPF↔manual | P2 | UX testada com 3 famílias dogfood antes de roll-out 100% |
| `irpf_snapshots` JSONB cresce indefinido | P3 | Cap 5 anos mais recentes V1 V0; cleanup automático V2 |
| Privacy CPF cru em artifact E1 | P1 | UI nunca renderiza CPF cru; mascara como `***.123.456-**`; artifact workspace-scoped + DB encrypted |

Lista completa em [[ADR-229]] §Consequências §Riscos.

## Out-of-scope ([[ADR-229]] §Follow-ups V2)

- **Códigos IRPF 31/32/41/45/47/49** (ações, FIIs, CDB, Tesouro, fundos, previdência). V1 só código 61.
- **Sugestão de membros + imóveis + investimentos** via pattern genérico. V2 reutiliza endpoint structure.
- **Banner soft de omissão fiscal** ("conta em extrato mas não no IRPF"). V2.
- **Renderização de timeline `irpf_snapshots` no card da conta**. V1 V0 só armazena.
- **Tabela `workspace_suggestion_dismissals` genérica** (não-IRPF-específica). V2 quando segundos consumidores chegarem.

## Definition of Done

- ☑ PR1 — Migration + endpoint + use case + telemetria — [#345](https://github.com/davidrobert/mathoms/pull/345), commit `5e36be00`, 2026-05-20.
- ☑ PR2 — UI cards inline + diff modal + dismissals + feature flag — [#347](https://github.com/davidrobert/mathoms/pull/347), commit `e0499967`, 2026-05-20.
- ☑ [[ADR-229]] flippada `Proposto` → `Decidido (A13.irpf-prefill-bank-accounts)` no PR2.
- ☑ Telemetria `mathoms.irpf_suggestions` — logger em `backend/app/api/family_members.py`.
- ☐ Métrica dogfood: tempo médio cadastro < 2min validado em 3 famílias — sem registro de execução.
- ☑ FAQ produto — seção "Como o Mathoms sugere contas a partir do IRPF" em `docs/reference/FAQ_bank_account_member.md`.

## Pré-requisito externo

~~Sprint A13 deve estar `current`.~~ **Superado pelos fatos:** a sprint A13
nunca foi aberta (numeração pulou A12 → A15), e a lane foi entregue
diretamente em 2026-05-20 (PRs #345/#347) sem cerimônia de sprint própria.

## Status (reconciliação 2026-07-08)

Lane **entregue em `main`** em 2026-05-20 (PRs #345/#347); [[ADR-229]]
`Decidido (A13.irpf-prefill-bank-accounts)`. Frontmatter estava stale
(`planned`) e a instrução "mover para `docs/sprint/A13/` quando A11 fechar"
tornou-se inexecutável (A13 não existe como pasta de sprint) — a lane
permanece em `docs/sprint/A12/lanes/` como registro histórico. Único item
sem evidência: métrica de dogfood (3 famílias), nunca registrada.
