---
id: A12.bank-account-disambig
type: lane
title: "Desambiguação conta bancária → membro (multi-membro mesmo banco)"
sprint: A12
status: shipped
aliases: ["A12.bank-account", "A12.BANK_ACCOUNT_DISAMBIG"]
priority: P1
depends_on: []
parallel_with: ["[[A12.cat-learning-loop]]", "[[A12.sunset-disk-artifact]]"]
adrs_canonical:
  - "[[ADR-226]]"
tags:
  - type/lane
  - sprint/a12
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
  - area/persistence
  - area/methodology
---

# A12.bank-account-disambig — Conta bancária → membro com discriminador real

> Lane multi-PR (4 PRs sequenciais). **Plano canônico:** [[ADR-226]] —
> a ADR é o plano (5 mudanças coordenadas, 4 PRs, gates, riscos). Esta
> lane é o índice de execução; **não duplique conteúdo da ADR**.
> Track operacional: [bank-account-disambig](../tracks/bank-account-disambig.md).

## Origem

Bug latente descoberto 2026-05-19: o mapping `banco_membro: dict[str, str]`
construído em [config_materializer.py:100](../../../../backend/app/services/config_materializer.py),
[config.py:425](../../../../backend/app/api/config.py) e
[extract_members.py:55](../../../../pipeline/stages/extract_members.py) é
1:1 — quando dois membros têm conta no mesmo banco (cenário comum no
ICP brasileiro: casal com Itaú/Bradesco/Nubank), o último sobrescreve
o primeiro silenciosamente. Transações + posições de investimento são
atribuídas ao membro errado em [e4_categorize.py:330](../../../../scripts/categorize_transactions.py)
e [investments_consolidator.py:141](../../../../pipeline/domain/services/investments_consolidator.py).

`account_number` e `agency` são extraídos pelos parsers E2 mas **nunca
casados** com `bank_accounts` cadastrados — coleta morta no caminho do
dado. `titular: string` em E3 schema é sintoma correlato (fatura
conjunta perde co-titular).

Co-design 2026-05-19: `data-engineer` (boundary + normalização) +
`financial-planner` (Cerbasi/Perini/AUVP — atribuição correta é core,
relatório fiscalmente incorreto sem fix).

## Sequência (4 PRs)

| # | PR | Effort | Gate principal |
|---|---|---|---|
| 1 | **PR1** — Migration `workspace_id` denormalizado em `bank_accounts` + `is_joint`/`co_titulares` reservados; serializer gera `contas[]` aditivo; parser constrói `account_map`; UI valida UNIQUE em-app | ~1.5d | Backfill staging completo; zero break em goldens single-member |
| 2 | **PR2** — `account_normalization.py` compartilhado; 11 parsers E2 atualizados; E3 propaga `account_number` por transação + `titulares: list`; schema bump aditivo; `make update-openapi-snapshot` | ~2d | Schema strict verde; goldens single-member verdes; normalização canônica por banco testada |
| 3 | **PR3** — `account_resolver.py` puro + DI; E4 + InvestmentsConsolidator + E1 (merge idempotente) consomem; **golden multi-membro novo verde**; `needs_review` em ambiguidade investments | ~2d | Golden multi-membro verde; golden single-member verde (paridade); teste idempotência E1 verde |
| 4 | **PR4** — `CREATE INDEX CONCURRENTLY` partial unique no DB; backend 409 em colisão; UI pre-fill IRPF + mensagem clara; telemetria `account_resolver.resolve_total{confidence}`; flip ADR-226 → Decidido | ~1d | Index sem lock visível; telemetria emitindo; fallback rate monitorado em workspaces piloto |

**Ordem obrigatória:** PR1 → PR2 → PR3 → PR4. PR1+PR2 são aditivos
(zero risco runtime); PR3 é onde efetivamente muda comportamento; PR4
fecha contrato. Total ~5-6d eng em ~2 semanas calendário.

## Branch prefix

`agent/bank-account-disambig-pr<N>/<yyyyMMdd-HHmm>` por PR
(ex.: `agent/bank-account-disambig-pr1/20260520-0900`).

## Gates de promoção entre PRs

- Cada PR mergeia em `main` independente (revertível via `git revert`).
- Suíte verde (`pytest backend/tests -q`, `pytest tests -q`, `cd frontend && npm test -- --run`).
- Pre-commit verde (`pre-commit run --all-files`).
- Goldens E3/E4/E5 verdes (paridade single-member preservada após PR2; multi-membro novo verde após PR3).
- **PR3 não pode subir antes do golden multi-membro existir** (criar no próprio PR3, mas é gate explícito).
- **PR4 exige telemetria já emitindo em staging** antes de roll-out 100%.

## Riscos principais (referência [[ADR-226]] §Consequências)

| Risco | P | Mitigação resumida |
|---|---|---|
| Schema bump E3 quebra parser legado | P1 | Aditivo (leitura tolerante); `MATHOMS_PIPELINE_SCHEMA_MODE=strict` valida; goldens single-member preservados |
| E1 merge idempotente regride no re-upload IRPF | P1 | Teste idempotência cobre re-run; `source_tier=editorial` manual sempre vence IRPF/LLM |
| Heterogeneidade parsers E2 deixa account_number `None` em banco específico | P1 | Helper compartilhado + audit em PR2 por banco (11 parsers) |
| UNIQUE rejeita row legado válido | P2 | Partial index só sobre `account_number IS NOT NULL`; NULL preservado |
| Ambiguidade vira ruído (muitos `needs_review`) | P2 | Telemetria — se >10% piloto têm ambíguo, sprint follow-up melhora UX |
| `BANCO_MEMBRO` global em `e4_categorize.py:332` continua mutável após refactor | P1 | Resolver recebe config via DI; global some por construção |

Lista completa em [[ADR-226]] §Consequências §Riscos.

## Out-of-scope ([[ADR-226]] §Follow-ups)

- **Conta conjunta com rateio proporcional** — V2 ADR follow-up
  (`co_titulares` ativos + `default_split` editorial 50/50 Cerbasi).
  Schema reservado em V1 (`is_joint` + `co_titulares` JSONB NULL).
- **Faturas de cartão multi-titular** (`final_cartao` discriminador) —
  ADR futura quando ICP exigir.
- **UI merge human-in-loop** para divergências E1 vs cadastro manual —
  follow-up; merge idempotente padrão cobre maioria.
- **Backfill de artefatos E2 já gerados** — deixar para reprocessamento
  natural; não retroativo.

## Definition of Done

- ☑ PR1 — absorvido em PR2 squash ([#337](https://github.com/davidrobert/mathoms/pull/337))
- ☑ PR2 ([#337](https://github.com/davidrobert/mathoms/pull/337)) — Schema E3 bump aditivo + 11 parsers E2 normalizam via `finalize_e2_result` + `titulares: list` + OpenAPI snapshot
- ☑ PR3 ([#339](https://github.com/davidrobert/mathoms/pull/339)) — `account_resolver` puro + E4/InvestmentsConsolidator/E1 consomem + golden multi-membro verde
- ☑ PR4 — partial unique index + 409 colisão backend + telemetria emitindo + flip ADR
- ☑ [[ADR-226]] flippada `Proposto` → `Decidido (A12.bank-account-disambig)` no PR4
- ☑ Telemetria `mathoms.account_resolver.resolve` emite `confidence` em logging estruturado
- ☑ FAQ produto: [FAQ_bank_account_member.md](../../../reference/FAQ_bank_account_member.md)
- ☐ UI pre-fill IRPF (follow-up V2 — não bloqueia fechamento V1)
- ☐ Monitoring `resolve_total{confidence}` por 1 semana pós-merge (operacional)
