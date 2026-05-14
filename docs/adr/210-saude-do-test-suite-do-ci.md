---
id: ADR-210
type: adr
title: "Saúde do test suite do CI — gates, telemetria e ciclo de vida"
status: Proposto
phase: "Sprint A12 (test health · CI cost)"
date: "2026-05-14"
relates_to:
  - "[[ADR-067]]"
  - "[[ADR-093]]"
  - "[[ADR-114]]"
  - "[[ADR-143]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 210"
  - "Saude test suite CI"
  - "Test health policy"
tags:
  - area/ci
  - area/testing
  - area/devex
  - phase/a12
  - status/proposto
  - type/adr
---

# ADR-210 — Saúde do test suite do CI

## Contexto

Em 2026-05-14, auditoria do CI achou três anti-padrões custando ~3 min do
tempo de PR sem entregar sinal proporcional:

1. **`tests/unit/pipeline/test_no_legacy_stage_names.py`** — parametrize
   19× repetindo scan completo do repo (helper sem cache), e modo
   soft-fail (`print` em vez de `pytest.fail`) cuja env var de hard-fail
   (`MATHOMS_ENFORCE_STAGE_RENAME`) nunca foi setada em workflow.
   Resultado: ~28 s de CI/PR sem dar sinal de correctness.

2. **bcrypt com 12 rounds** em testes via fixtures `auth_client` +
   `ops_yaml`. Em prod é correto (defesa contra força bruta); em teste
   só atrasa setup. ~30-150 chamadas × 0.5-2 s/call no runner do GH
   Actions = **2-4 min** de overhead em backend-tests.

3. **Migration tests de migrations já executadas em prod** rodando em
   todo PR. `test_close_orphan_goals_migration.py`,
   `test_correct_ir_brackets_deducao_migration.py`,
   `test_stage_rename_migration.py`, `test_a73_seed_migrations.py`
   testam código one-shot que não muda mais após o merge inicial.

Investigação também revelou pelo menos um teste explicitamente marcado
como **descartável após cutover** (`backend/tests/test_decisions_migrator.py`,
docstring: "Após a Sprint A7.5, este arquivo + o migrator podem ser
removidos juntos") que sobreviveu meses além do prazo — Sprint A7 foi
entregue em 2026-04-27.

A raiz é organizacional: não há **gate** no fluxo de adicionar teste
que pergunte "esse teste vai dar sinal proporcional ao custo?", nem
**ciclo de vida** para remover testes que perderam função (cutover,
deprecation, soft-fail permanente, migration one-shot).

## Decisão

Adotar política de **saúde do test suite** em três camadas:

### 1. Gate de adoção — `dev/check_test_health.py` (pre-commit + CI)

Script novo bloqueia commit quando detecta anti-padrões catalogados:

| Anti-padrão | Detecção | Sugestão automática |
|---|---|---|
| Parametrize que recomputa helper caro | Helper sem args/sem param na chamada + helper faz I/O ou loop | `@functools.lru_cache` no helper, OU despararametrizar |
| Soft-fail sem hard-fail-env ativo no CI | `os.environ.get('MATHOMS_*')` em path de fail + env não está em `.github/workflows/` | `@pytest.mark.skipif(os.getenv(...) != '1')` |
| Migration test sem marker | `test_*_migration.py` ou import de `alembic.versions.*` sem `@pytest.mark.migration` | Adicionar `pytestmark = pytest.mark.migration` |
| Test pós-cutover órfão | Docstring com `Após a Sprint <id>` cujo cutover já passou | Deletar arquivo + código testado |
| bcrypt prod-grade em test | `bcrypt.hashpw(...)`/`bcrypt.gensalt()` em test individual e conftest sem `_fast_bcrypt_for_tests` | Adotar o fixture autouse session-scope |

Heurísticas conservadoras (falsos negativos OK; falsos positivos custam
crédito do gate). Allowlist via padrão `@functools.lru_cache` no source
do helper, fixture `_fast_bcrypt_for_tests` em `backend/tests/conftest.py`,
e `@pytest.mark.skipif` sobre o env var.

### 2. Marker `migration` + path filter — opt-in para migration tests

`pyproject.toml [tool.pytest.ini_options]` registra marker `migration`.
Testes de migration one-shot recebem `pytestmark = pytest.mark.migration`.
`.github/workflows/ci.yml` step `Run backend tests`:

```yaml
MARKER_FILTER='-m "not migration"'
if [ "${{ needs.changes.outputs.migration }}" = "true" ]; then
  MARKER_FILTER=""
fi
eval pytest backend/tests/ ... $MARKER_FILTER
```

Filtro `migration` no path-filter cobre `backend/alembic/versions/**`,
`backend/alembic/env.py`, `backend/tests/test_*_migration.py`,
`backend/app/models/**`. PR que toca esses paths roda a suíte completa
(sem deselect); PR de feature pura roda só não-migration.

`test_alembic_guardrails.py` (drift schema↔model + idempotência) **não**
recebe o marker — é gate permanente, sempre roda.

### 3. Fixture session-scoped `_fast_bcrypt_for_tests` — bcrypt rounds=4

`backend/tests/conftest.py` adiciona fixture autouse session-scoped que
monkeypatcha `bcrypt.gensalt` para retornar salt com `rounds=4` (mínimo
do bcrypt). Asserts de auth verificam **emparelhamento** hash↔senha; o
work-factor real é responsabilidade do prod (testado por
`test_password_hashing_uses_bcrypt_with_min_rounds` em
`test_auth.py` quando existe).

## Consequências

### Ganhos quantificados (CI ubuntu-latest, observados em 2026-05-14)

| Fix | Antes | Depois | Δ |
|---|---:|---:|---:|
| Fix #1 (cache `_find_occurrences`) — pipeline-tests | 1m16s | ~48s | −28s |
| Fix #2 (bcrypt rounds=4) — backend-tests | 8m19s | ~5min (est.) | **−3min** |
| Fix #3 (migration deselect) — backend-tests | ~20s extra/PR | 0s em PRs não-migration | −20s |
| Removal `test_decisions_migrator.py` | ~0.5s | 0 | −0.5s |

**Total estimado**: tempo de CI por PR típico cai de **~8m30s → ~5m**,
sem perder cobertura real.

### Custos

- **Manutenção do checker** (`dev/check_test_health.py`): ~200 linhas,
  testes futuros podem detectar padrões novos. Baixo overhead.
- **Risco de falso-negativo no marker `migration`**: PR que aplica
  migration mas esquece de tocar `backend/alembic/versions/` deixaria
  o teste pular silenciosamente. Mitigação: filter cobre também
  `backend/tests/test_*_migration.py` (mexer no teste re-ativa).
- **bcrypt rounds=4 em test não testa força do hash em prod**: aceito.
  O teste de força (que `hash_password` usa `bcrypt` com ≥12 rounds em
  ambiente real) deve ser ADR-decoupled — vive em smoke test contra
  staging, não em unit test. Adicionar como follow-up se ainda não
  existe.

### Não-decisão / out of scope

- Não migrar bcrypt para argon2 em prod (decisão maior, fora desta ADR).
- Não eliminar a redundância repository↔use_case↔API (mantém debug
  localizado; auditar caso-a-caso é tarefa de outro track).
- Não cobrir frontend (Vitest local 16s não é caminho crítico).

## Alternativas consideradas

### A) Manter status quo + investir só em hardware do runner

CI runner `ubuntu-latest-large` (4 vCPU → 16 vCPU). Custaria ~$0.064/min
extra × ~5000 min/mês = **$320/mês** sem corrigir as causas. Rejeitada:
dinheiro mascara a dívida técnica.

### B) Job separado para migration tests (não marker)

GH Actions job `backend-migration-tests` gated por path filter.
Equivalente em ganho mas adiciona um job ao gate `all-green`, um cache
extra, e duplicação do setup. Marker `+ if`-step é mais idiomático e
reaproveita o setup já pago pelo `backend-tests`.

### C) Marker progressivo, sem hard-fail no checker

Versão "warning-only" do `check_test_health.py`. Rejeitada: padrões
detectáveis devem virar gate; warnings ignorados são código morto
de processo.

## Plano de adoção

1. **PR único** (este): Fix #1 + Fix #2 + Fix #3 + checker + ADR.
2. **Follow-up curto**: catalogar mais anti-padrões conforme aparecem em
   `check_test_health.py`. Cada padrão novo justificado em commit
   message com link para issue/PR onde foi descoberto.
3. **Audit semestral** (sre-devops + product-manager): comparar tempo
   de CI atual vs baseline ADR-210; revisar markers; remover testes
   pós-cutover detectados pelo checker.

## Referências

- CLAUDE.md §Code style › Testes — comandos canônicos e fixtures.
- `.github/workflows/ci.yml` job `changes.outputs.migration` + step
  `Run backend tests` `MARKER_FILTER`.
- `dev/check_test_health.py` — heurísticas e exit codes.
- `backend/tests/conftest.py` — `_fast_bcrypt_for_tests` fixture.
- ADR-067 — coverage progressivo (frontend).
- ADR-093 — stage rename (origem do soft-fail).
- ADR-114 — code style baseline (lint cycle).
- ADR-143 — methodology = code (princípio análogo: testes ≡ código,
  têm ciclo de vida).
