---
id: TRACK-adr272-review-reasons
type: track
title: "Track A20 — ReviewReason estruturado (ADR-272) em 4 fases"
sprint: A20
status: ready
created_at: "2026-05-30"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a20
  - status/ready
  - priority/p1
  - area/pipeline
  - area/backend
  - phase/a20-failure-diagnostics
---

# Track A20 — ReviewReason estruturado ([[ADR-272]]) em 4 fases

> **ADR canônica:** [[ADR-272]] (`Proposto`, Fase 0 fechada 2026-05-30 — unificação resolvida: destino único, produtores desacoplados via `ToReviewReason`). Par no mesmo pacote: [[ADR-273]] (logging estruturado do pipeline).
> · **Branch prefix:** `agent/adr272-review-reasons/*`
> · **Escopo:** **pipeline/extração apenas** — document-upload/classificação fica fora (UX própria; ver [[ADR-272]] §Escopo).

## Objetivo

Promover `needs_review` (hoje `bool` puro) para **razão estruturada consultável** na superfície do pipeline. As últimas ~5 correções de produção ([[ADR-238]], [[ADR-255]], [[ADR-267]]) foram **output errado silencioso**, não crash — a classe mais cara de depurar quando o sinal é booleano. O alvo é a query-mãe: *"dado workspace X, último run falho, devolva todas as razões com campo ofensor + agregado por código"* como `SELECT` indexado.

## Decisão de design fixada (Fase 0)

1. **Fonte única** `ReviewReason` (frozen dataclass) em `pipeline/domain/review_reason.py`, padrão [[ADR-097]] D1 (`code`/`offending_value`/`expected`/`.format()`).
2. **Unificação = destino, não produtor.** `ValidationIssue` ([[ADR-165]], conformidade de schema) e warnings de domínio ([[ADR-097]] D1) permanecem **tipos distintos** (SRP). Ambos projetam para `ReviewReason` via protocolo `ToReviewReason.to_review_reason(stage, artifact_key, document_id)`. **Rejeitada** a dataclass única (acopla schema-conformity com regra de domínio — `senior-cto` mandou recuar disso).
3. **`code` = String na coluna + enum Python namespaced** (`extract.low_confidence`, `dedup.possible_duplicate`, `domain.validation_conflict`, …). Nunca `Enum` SQL (`ALTER TYPE` não-transacional em rolling deploy).
4. **Redação de PII no `__post_init__`**, jamais no call-site. Cobre o `context` herdado de `ValidationIssue` (pode conter trecho de extrato). `message` só carrega IDs/contadores/enums.
5. **Tabela `review_reasons`** com índice composto `(workspace_id, pipeline_run_id, code)`; cap de 50 rows por `(run, code)` + `occurrence_count`.

## Garantias (como cada uma é provada)

| Garantia | Mecanismo de prova |
|---|---|
| **Corretude** | Teste de paridade: `StageReview.validation_issues` populado **da mesma** `ReviewReason` que vai para `review_reasons` — sem divergência. `EXPLAIN` da query-mãe usa o índice composto. |
| **Completude** | Gate `dev/check_needs_review_has_reason.py`: todo ponto que seta `needs_review=true` na superfície pipeline/extração anexa uma `ReviewReason`. Superfície enumerada e fechada (escopo exclui document-upload). |
| **Precisão** | `ReviewReasonCode` namespaced + `offending_value`/`expected` estruturados; teste afirma que dois produtores distintos (`ValidationIssue` + ≥1 warning de domínio) geram `ReviewReason` válida sem o adapter conhecer o tipo concreto. |
| **Sem regressão** | Fase 1 não toca call-site (só infra). Fase 2 adiciona projeção sem remover `validation_issues`/`validation_errors`. Suíte `backend/tests` + `tests` verde após cada fase; migração testada com `pytest.mark.migration` (upgrade+downgrade+PRAGMA). |
| **Sem vazamento de PII** | Teste de redação com CPF/valor **sintético** (gerador mod-11), incl. caminho `ValidationIssue.to_review_reason()` com `context` contendo trecho de extrato. `message` nunca interpola valor. |

## Fases (cada uma = 1 PR, mergeada antes da próxima)

### Fase 1 — fundação de dados (sem mudança de call-site)

Flippa [[ADR-272]] para `Decidido (Sprint A20)` no merge.

- `pipeline/domain/review_reason.py`: `ReviewReason` (frozen) + `ReviewReasonCode` (enum namespaced) + protocolo `ToReviewReason` + util de redação compartilhado + `to_dict()`.
- `config/schemas/review_reason.schema.json` (`version: "1.0"`), registrado em `SCHEMA_BY_STAGE`/validação `warn` se aplicável.
- Model `ReviewReason` em `backend/app/models/` (colunas conforme [[ADR-272]] §Projeção 1; FKs CASCADE; índice composto).
- Migration Alembic `ADD TABLE review_reasons` (chain do head atual; sem backfill).
- Testes: construção, `.format()`, **redação** (incl. `context` herdado), `to_dict()`, migration upgrade/downgrade.

**DoD:** PR em `main` CI verde; ADR-272 `Decidido`; `DB_SCHEMA_REFERENCE.md` snapshot atualizado; nenhum call-site de `needs_review` alterado.

### Fase 2 — seam de serialização

- `ValidationIssue.to_review_reason()` (mapeia `severity/path/context → code/offending_value/expected`, passando `context` pela redação).
- ≥1 warning de domínio implementa `to_review_reason()` (ex.: `DebtVsIrpfDeclaracaoConflict`).
- [`backend/app/tasks/pipeline_task.py`](../../../../backend/app/tasks/pipeline_task.py) `_record_stage_needs_review()`: consome `list[ToReviewReason]`, materializa rows em `review_reasons` **e** popula `StageReview.validation_issues` da mesma fonte (cap + `occurrence_count`).
- Teste de paridade (validation_issues ↔ review_reasons) + teste do cap (run com 800 dups → ≤50 rows).

**DoD:** PR em `main` CI verde; query-mãe demonstrada em teste com `EXPLAIN`.

### Fase 3 — completude (back-fill da superfície + gate)

- Anexa `ReviewReason` em todos os pontos `needs_review=true` da superfície pipeline/extração (schemas LLM `informe_base.py`/`crlv.py`/`apolice.py`/`informe_*`; stages `extract_comprovantes_bens.py`/`extract_informes_anuais.py`/`extract_irpf_full.py`/`parecer_planejador.py`; services `cash_flow_builder.py`/`investments_consolidator.py`/`vehicle_reconciliation.py`).
- `dev/check_needs_review_has_reason.py` (gate pre-commit + CI): falha se `needs_review=true` sem `ReviewReason` na superfície fechada.
- `validation.errors` (strings legado) marcado deprecado em favor de `ReviewReason`.

**DoD:** gate verde sobre a superfície enumerada; PR em `main` CI verde.

## Pré-flight (documentar no PR)

```bash
git fetch origin && git worktree list                 # nenhum agente em adr272-review-reasons
ls docs/adr/272-*.md docs/adr/273-*.md                 # ADRs em main
alembic heads                                          # head único p/ encadear migration
rg -n "needs_review\s*=\s*True" pipeline/ backend/app/ # superfície atual (Fase 3)
```

## Especialistas pre-PR

- **`data-engineer`** (Fase 1, obrigatório) — shape da tabela, índice composto, migration sem backfill, encadeamento de head.
- **`senior-cto`** (Fase 2, obrigatório) — boundary `pipeline/domain` ↔ adapter, protocolo `ToReviewReason`, ausência de import sqlalchemy em `pipeline/**`.
- **`sre-devops`** (Fase 1/3, consultivo) — redação de PII no construtor + gate de superfície fechada.

## Ligações

- **ADR:** [[ADR-272]] · **Par:** [[ADR-273]] · **Sprint MOC:** [[MOC-sprint-a20]]
- **Precedentes de design:** [[ADR-097]] (warning tipado) · [[ADR-165]] (`validation.issues`) · [[ADR-212]] (schema validation `warn`)
- **Incidentes que motivam:** [[ADR-238]] · [[ADR-255]] · [[ADR-267]]
