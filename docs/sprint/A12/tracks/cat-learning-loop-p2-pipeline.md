---
id: TRACK-cat-learning-loop-p2-pipeline
type: track
title: "Track Cat Learning Loop P2 — Pipeline E4 (CategorizationRulesV2 + adapter)"
sprint: A12
plan: PLAN-cat-learning-loop
status: ready
created_at: "2026-05-10"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/categorization
  - area/pipeline
---

# Track Cat Learning Loop P2 — Pipeline E4

> **Lane:** [[A12.cat-learning-loop]] · **Plano canônico:**
> [PLAN-cat-learning-loop](../../../plan/CAT_LEARNING_LOOP/_README.md) §P2
> · **ADR canônica:** [[ADR-186]] §D5 (+ ressalvas data-eng/financial-planner
> consolidadas no review da P1)
> · **Branch prefix:** `agent/cat-learning-loop-p2-pipeline/*`
> · **Depende de:** P1 ✅ (PR #188, commit `2a36388`) +
>   [[A11.report-publication]] ✅ (PR #185, commit `182308a`).
> · **Bloqueia:** P3 (Backend API).

## Briefing

P1 entregou schema (`categorization_rules`, `transaction_overrides.source`,
`transaction_overrides.rule_id`). P2 introduz **comportamento novo no
pipeline E4** — passa a consumir regras aprendidas via adapter e
materializa overrides automáticos (`source='rule'`) com invariantes
enforce. Workspace **sem regras** continua com goldens E4 inalterados
(gate de paridade obrigatório).

### Value object frozen no domínio

Em `pipeline/domain/services/categorization_service.py`:

```python
@dataclass(frozen=True)
class LearnedRule:
    id: str
    keyword: str            # já uppercase, igual semântica E4
    target_category: str    # key do CategoryTemplate
    priority: int
    created_at: datetime

@dataclass(frozen=True)
class CategorizationRulesV2:
    template_keywords: Mapping[str, tuple[str, ...]]
    learned_rules: tuple[LearnedRule, ...]   # já sorted estável
```

### Sort estável (determinístico) — ADR-186 §D5

`(priority desc, len(keyword) desc, created_at asc, id asc)`.
`id` como tiebreaker final é **mandatório** (ressalva data-engineer
no review P1): `created_at` empata em precision sub-segundo entre regras
criadas em batch (transação única do P3 commit). Docstring 1-linha na
função `_sort_learned_rules` referencia `ADR-186 §D5`.

### Adapter (backend → pipeline)

Novo módulo em `backend/app/services/categorization_rules_adapter.py`:

- Lê `categorization_rules` filtrando `enabled=true AND workspace_id=…`.
- Hard cap **N=200** regras (warning em log estruturado `>50`,
  `mathoms.categorization.rule_count`). Erro 409 ao tentar criar
  201ª regra vem em P3 (endpoint-level enforcement).
- Retorna `CategorizationRulesV2` (value object frozen).
- Injetado via construtor no service ou via `WorkspaceContext` —
  **pipeline boundary preservado** (`pipeline/**` não importa
  SQLAlchemy; `dev/check_pipeline_boundaries.py` continua verde).

### Invariantes (enforce em P2)

**Sticky manual** (financial-planner sessão P1 review): ao criar
`TransactionOverride(source='rule', rule_id=…)`, query verifica que
não existe override `source='manual'` para a mesma
`(workspace_id, transaction_hash)`. Se existe, **skip silencioso** —
override manual é sticky (ADR-186 §D2 reforça invariante).

**Mês fechado** (ADR-187 · A11.report-publication): consultar
`report_publications` antes de criar override retroativo. Se mês de
`transaction.date` está fechado (`published_at IS NOT NULL`), skip a
transação. Heatmap UX (P4) reflete cinza não-clickável; pipeline
enforce o gate independente do UI.

**Conflito determinístico:** sort acima resolve. **Docstring 1-linha**
em `_categorize_with_learned_rules` referenciando `ADR-186 §D4`
(conflito de keyword: substring/superstring; priority + len(keyword)
desc).

### Counters (telemetria de saúde — ADR-186 §D6)

- `applied_count += 1` em `categorization_rules` ao criar
  `TransactionOverride(source='rule', rule_id=X)`. **Mesmo
  `Session.flush()`** do INSERT (ressalva data-eng: contadores fora do
  flush abrem janela de inconsistência sob crash entre INSERT e UPDATE).
- `revert_count += 1` é responsabilidade de P3 (endpoint revert/delete
  do override `source='rule'` ou conversão para `source='manual'` via
  edição). Não tocar aqui — só documentar contrato.

## Critério de aceite

- [ ] `CategorizationRulesV2` value object frozen criado em
      `pipeline/domain/services/categorization_service.py`. Sem
      `sqlalchemy`/`fastapi` no import.
- [ ] `LearnedRule` dataclass frozen com 5 campos
      (`id`, `keyword`, `target_category`, `priority`, `created_at`).
- [ ] Sort estável `(priority desc, len(keyword) desc, created_at asc,
      id asc)` testado isoladamente — `id` como tiebreaker final
      coberto.
- [ ] Adapter `backend/app/services/categorization_rules_adapter.py`
      testado isoladamente (input: workspace_id; output:
      `CategorizationRulesV2`). Filtragem `enabled=true` enforce.
- [ ] Hard cap N=200 no adapter — workspace com >200 regras pode
      criar erro estruturado (ou retornar primeiras 200 com warning
      no log; decisão final no PR). Warning `>=50` em log estruturado.
- [ ] `dev/check_pipeline_boundaries.py` verde —
      `pipeline/domain/services/categorization_service.py` **não**
      importa `sqlalchemy`/`backend.*`.
- [ ] Goldens E4 inalterados para workspace sem regras (`pytest tests -q`
      verde).
- [ ] Sticky manual: workspace com override `source='manual'` em
      transação X + regra que casaria → após E4, override permanece
      `source='manual'` (3+ casos: mesma categoria, categoria diferente,
      regra de prioridade alta).
- [ ] Mês fechado: regra criada em maio + transação de janeiro com
      `report_publications.published_at IS NOT NULL` → não cria
      override. 3+ casos: mês fechado limítrofe, mês reaberto, mês nunca
      publicado.
- [ ] Sort determinístico: 3+ casos — `(priority=100, 'IFOOD')` vs
      `(priority=100, 'MERCADO PAGO IFOOD')` (len desc) · empate em
      `(priority, len)` com `created_at` igual (id asc) · prioridade
      diferente.
- [ ] `applied_count` bumped no `Session.flush()` correto — teste
      verifica contagem pós-E4 igual ao número de overrides
      `source='rule'` criados naquela run.
- [ ] `pytest backend/tests -q` verde.
- [ ] `pytest tests -q` verde.
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

- **Novo:** `backend/app/services/categorization_rules_adapter.py`
- **Editado:** `pipeline/domain/services/categorization_service.py`
  (novo value object + função `_categorize_with_learned_rules`)
- **Editado:** `pipeline/stages/e4.py` (ou stage equivalente) — wire do
  adapter via DI; sem import SQLAlchemy.
- **Novo:** `backend/tests/test_categorization_rules_adapter.py`
- **Novo:** `tests/test_e4_learned_rules.py` (sticky · mês fechado · sort
  · adapter contract via fake)
- **Fake:** `tests/fakes/categorization_rules_fake.py` (InMemory adapter
  para tests/ não tocar DB).

## Decisões já tomadas (pre-PR)

- **`id` como tiebreaker final do sort** — ressalva data-eng (review P1):
  `created_at` empata em batch insert; sem `id` o sort vira não
  determinístico em SQLite.
- **`applied_count` no mesmo flush do INSERT** — ressalva data-eng:
  contador fora do flush abre janela de inconsistência sob crash.
  Aceito; comentário no código referencia ADR-186 §D6.
- **Sticky manual via query** (não app-level scan) — performance: scan
  in-memory de N=200 regras × M=milhares de overrides explodiria.
  Query SQL com `WHERE source='manual'` + index `(workspace_id,
  transaction_hash)` existente é O(log n).
- **Mês fechado consultado uma vez por run** — não por transação.
  Carregar `set[date]` de meses fechados no início do stage; lookup
  `O(1)`.
- **Cap N=200 advisory neste track, enforce em P3** — track P2 expõe
  comportamento "soft" (lê >200 mas avisa); P3 endpoint nega criação
  da 201ª.

## Testes

```bash
cd backend && pytest backend/tests/test_categorization_rules_adapter.py -q
pytest tests/test_e4_learned_rules.py -q
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

## Riscos

- **R1** — Pipeline boundary quebra silenciosa. Mitigação:
  `dev/check_pipeline_boundaries.py` no pre-commit. Quem importar
  `sqlalchemy` no pipeline trava no hook.
- **R2** — `applied_count` race condition em workers paralelos
  (mesma regra aplicada em 2 runs concorrentes). Mitigação imediata:
  `UPDATE … SET applied_count = applied_count + 1` (atômico no driver).
  Mitigação completa (lock-free counter): P3.
- **R3** — Sort de regras em Python (não SQL) custa O(N log N) em cada
  run. Com N=200 max, custo é desprezível (<1ms). Hard cap protege.

## Ligações

- Plano: [PLAN-cat-learning-loop](../../../plan/CAT_LEARNING_LOOP/_README.md) §P2
- ADR canônica: [[ADR-186]] §D5 (contrato `CategorizationRulesV2`) +
  §D4 (conflito determinístico) + §D6 (counters)
- Pré-req schema: PR #188 (P1), commit `2a36388`
- Pré-req mês fechado: PR #185 ([[ADR-187]]), commit `182308a`
- Lane: [[A12.cat-learning-loop]]
- Track P1 (concluído): `cat-learning-loop-p1-schema.md`
- Track P3 (próximo): `cat-learning-loop-p3-backend-api.md` (criado quando P2 mergear)
