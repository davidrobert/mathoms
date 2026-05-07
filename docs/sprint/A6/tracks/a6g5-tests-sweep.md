---
id: TRACK-a6g5-tests-sweep
type: track
title: "Track A6g.5 — Tests Sweep (fakes nomeados + nomes descritivos)"
sprint: A6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a6
  - status/consumed
---

# Track A6g.5 — Tests Sweep (fakes nomeados + nomes descritivos)

> **Lane ID:** A6g.5
> **Branch prefix:** `agent/a6g5-tests-sweep/*`
> **Depende de:** A6g.1 ✅ (baseline de ofensores)
> **Paralelo com:** A6g.2 pipeline sweep, A6f.1 pipeline-service, A6e.3 use cases — zero overlap **se** respeitar o escopo de arquivos abaixo.
> **Conflita com:** commits ativos em `backend/tests/test_pipeline_task.py`, `backend/tests/test_events.py` (overlap potencial com slice 2 de A6f.1; rebase resolve na ordem "A6g.5 → A6f.1").
> **Onda:** 2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [CLAUDE.md §Code style › Testes](../../CLAUDE.md#testes)

> **Objetivo:** aplicar CLAUDE.md §Code style aos arquivos de teste em
> `tests/`, `tests/unit/pipeline/` e `backend/tests/` (não-fixture,
> não-golden). Focos: substituir `MagicMock` inline por fakes nomeados,
> descer fixtures >20 linhas, uniformizar nomes (`test_reconcile_drops_
> duplicate_when_same_hash` > `test_dedupe_1`). F.I.R.S.T preservado.

---

## Por que este slice agora

A6g.1 baseline mostrou que testes carregam drift silencioso: 39
`MagicMock(` em `backend/tests/`, 2 fixtures de produção >40 linhas, e
nomes genéricos sobreviventes. Ninguém vai fazer isso em sweep dedicado
se não for agendado; por osmose só piora (cada teste novo copia o
estilo do vizinho).

Escopo cirúrgico — só renomes, decomposição de fixtures e trocas
`MagicMock` → fake nomeado. **Zero lógica de negócio tocada, zero
código fora de `tests/**`.**

---

## Regras inegociáveis

Do CLAUDE.md §Testes:

1. **F.I.R.S.T.** Fast, Independent, Repeatable, Self-validating, Timely.
2. **Mocks de I/O externo** via fakes nomeados (`tests/fakes/`, `InMemoryArtifactStore`), **não** `MagicMock` inline.
3. **DB em testes: nunca mocar** — SQLite em memória ou fixtures Alembic-aware.
4. **Função nova → teste.** Bug fix → teste de regressão antes do fix.
5. **Fixtures pequenas** (<20 linhas). Passou, extraia helper.
6. **Nomes descritivos** — `test_<verbo>_<objeto>_<condição>`. Grep do nome retorna <5 hits em suíte.
7. **Preserve comentários existentes em refactor.**
8. **Goldens e paridade são imutáveis** — arquivos listados em §3 fora de escopo.

---

## Estado atual — baseline

**Inventário in-scope** (161 arquivos Python):

| Diretório | Arquivos | Notas |
|---|---|---|
| `tests/` (root) | 37 | stage goldens + integration (filtrar out 16 goldens) |
| `tests/unit/pipeline/` | 54 | unit tests isolados; mais seguro para renomear |
| `backend/tests/` | 70 | includes 6 com `MagicMock` |
| **Total in-scope** | ~145 (após filtrar goldens) | |

**Top 10 maiores em linhas** (candidatos a split):

| Arquivo | Linhas | Status |
|---|---|---|
| `tests/test_llm_stages.py` | 920 | in-scope — candidato a split |
| `backend/tests/test_content_classifier.py` | 655 | in-scope |
| `backend/tests/test_task_repository.py` | 532 | in-scope |
| `backend/tests/test_multi_tenant_isolation.py` | 517 | in-scope |
| `backend/tests/test_patrimonio_calculator.py` | 513 | in-scope |
| `backend/tests/test_statement_preprocessor.py` | 482 | in-scope |
| `tests/unit/pipeline/test_patrimonio_resolvers.py` | 705 | in-scope |
| `tests/unit/pipeline/test_e3_reconciler_adapter.py` | 545 | in-scope |
| `tests/test_e5n_builder_decomposition.py` | 440 | in-scope |
| `tests/test_e4_main_with_store_parity.py` | 315 | ⚠️ GOLDEN — não tocar |

**`MagicMock` ofensores** (39 total):

| Arquivo | Instâncias | Ação prioritária |
|---|---|---|
| `backend/tests/test_pipeline_task.py` | 22 | fake nomeado `FakeCeleryDispatcher` |
| `backend/tests/test_events.py` | 13 | `FakeRedisPublisher` (ou reutilizar `fakeredis`) |
| `backend/tests/test_premissas_snapshot.py` | 3 | fake inline de `Report` |
| `backend/tests/test_llm_service.py` | 1 | `FakeLLMClient` (existe? check) |
| outros | 0 | — |

**Fakes já existentes (padrão):**
- `backend/tests/factories/builders.py` (2.1 KB) — builders de domínio.
- `backend/tests/fixtures/llm_mock.py` (5.1 KB) — **out-of-scope** (A6g.2 territory).
- `InMemoryArtifactStore` em `pipeline/artifact_store.py` — modelo de fake nomeado.

**Fixtures longas candidatas a split** (in-scope, não-golden):
- `tenant_and_project` em `backend/tests/test_content_addressed_upload.py` — 42 linhas.
- ⚠️ `workspace` em `backend/tests/test_serializers_round_trip.py` (133 linhas) é **golden** — não tocar.

---

## Out-of-scope (GOLDEN — não tocar)

**16 arquivos intocáveis** — nomear, mover ou decompor quebra goldens:

```
tests/test_e3_golden_execution.py
tests/test_e4_golden_execution.py
tests/test_e5_golden_execution.py
tests/test_e5n_golden_execution.py
tests/test_e6_golden_execution.py
tests/test_e3_main_with_store_parity.py
tests/test_e4_main_with_store_parity.py
tests/test_e5_main_with_store_parity.py
tests/test_e5n_e7_main_with_store_parity.py
tests/test_e15c_main_with_store_parity.py
tests/test_llm_golden.py
tests/test_classification_parity.py
tests/test_golden_pipeline.py
backend/tests/test_serializers_round_trip.py
backend/tests/test_alembic_guardrails.py
tests/fixtures/**   (inteira — A6g.2)
```

**Outros fora de escopo:**
- `frontend/tests/**` (A6g.4)
- `tests/fixtures/**`, `tests/fakes/**` (A6g.2)
- Migrações de DB (`backend/alembic/versions/*.py`)

---

## Targets — tier por risco

### Tier 1 — MagicMock → fake nomeado (baixo risco)

**T1.a — `backend/tests/test_events.py` (13 MagicMock)**

- Padrão atual: `mock_publisher = MagicMock(); mock_publisher.publish.assert_called_once(...)`.
- Extrair `backend/tests/fakes/fake_redis_publisher.py`:
  ```python
  class FakeRedisPublisher:
      def __init__(self) -> None:
          self.published: list[tuple[str, dict]] = []

      def publish(self, channel: str, payload: dict) -> None:
          self.published.append((channel, payload))
  ```
- Usar `fakeredis` quando interação real de Redis for testada (já disponível em `backend/tests/`).
- **Gate:** `pytest backend/tests/test_events.py -q` verde, mesmo contador de tests.

**T1.b — `backend/tests/test_pipeline_task.py` (22 MagicMock)**

⚠️ **Coordenar com A6f.1:** esse arquivo vai ser tocado em slice 2 de A6f.1 (refactor `PipelineServiceClient`). Se A6f.1 estiver ativa, **A6g.5 merge primeiro**; A6f.1 faz rebase. Se A6f.1 já mergeou slice 2, use os novos fakes dele (provavelmente `InProcessPipelineClient` serve).

- Fakes a criar (se A6f.1 ainda não fez): `FakeCeleryDispatcher`, `FakeStageRunner`, `FakePipelineEventPublisher` em `backend/tests/fakes/`.
- **Gate:** `pytest backend/tests/test_pipeline_task.py -q` verde.

**T1.c — `backend/tests/test_premissas_snapshot.py` + `test_llm_service.py` (4 MagicMock)**

- Usar `FakeReportSnapshot` e `FakeLLMClient` já existentes (se não, criar).
- **Gate:** ambos verdes individualmente.

**Commit 1:** `test(backend): MagicMock → fake nomeado em events/pipeline_task/premissas (A6g.5 — T1)`

### Tier 2 — Nomes descritivos (baixo risco, cirúrgico)

Buscar todos `def test_<nome-genérico>`:

```bash
grep -rn "def test_" tests/ backend/tests/ tests/unit/pipeline/ | \
  grep -E "def test_(it|works|basic|case_[a-z]|[a-z]+_[0-9]+)\(" | \
  grep -v golden
```

Renomear em-place, mantendo o que o teste realmente verifica:

- `test_basic_signature` → `test_ledger_signature_strips_whitespace`
- `test_itau_extrato` → `test_itau_parser_extracts_saldo_when_multiple_accounts`
- `test_item_to_dict` → (inspecionar; provavelmente `test_transaction_serializer_preserves_decimal`)
- `test_cross_tenant_get_returns_403_for_member_1/2/3` → consolida em 1 teste paramétrico

**Regras:**
- **Nunca** renomear para "melhor ficar" sem ler o teste; se não entende, pule.
- **Teste paramétrico** se >3 tests diferem só por dado de entrada.
- Mesmo arquivo pode virar 2 (`split` se >500 linhas **e** dividir por responsabilidade óbvia — ex.: `test_task_repository.py` vira `test_task_repository_filters.py` + `test_task_repository_mutations.py`). Caso contrário, deixe.

**Gate:** `pytest` total conta passes idêntico ou >= baseline. Nenhum skip novo.

**Commit 2:** `test: nomes descritivos em ~N tests de backend+pipeline (A6g.5 — T2)`

### Tier 3 — Fixtures longas (baixo risco, cirúrgico)

Busca por fixtures >30 linhas que **não** são goldens:

```bash
# in-scope por padrão
grep -B2 "def [a-z_]*fixture" backend/tests/test_content_addressed_upload.py
```

Decomposição típica: `tenant_and_project` (42 linhas) → `_create_tenant()` + `_create_project(tenant)` helpers + `@pytest.fixture` chaining.

**Gate:** fixture resultante <20 linhas; `pytest` verde.

**Commit 3 (opcional — só se encontrar >5 fixtures in-scope reais):** `test: decompõe fixtures >30l em helpers nomeados (A6g.5 — T3)`

### Tier 4 — Split de arquivos >500 linhas (opcional)

**Só se sobrar tempo.** Split `tests/test_llm_stages.py` (920 linhas) em `tests/test_llm_stages_e15.py` + `tests/test_llm_stages_e2.py` + `tests/test_llm_stages_e7.py`. Gate crítico: `pytest -q` conta todos os tests de antes.

**Commit 4 (opcional):** `test: split test_llm_stages por stage (A6g.5 — T4)`

### Tier 5 — Fora de escopo (explicitar em CHANGELOG)

- Nomes em 16 arquivos golden — mantidos.
- Fixtures em `tests/fixtures/**` — A6g.2.
- Frontend tests — A6g.4.

---

## Sequência de execução

### 1. Setup

```bash
git fetch origin
git worktree list
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
# Confirma que ninguém está em agent/a6g5-*
git checkout -b agent/a6g5-tests-sweep/$(date +%Y%m%d-%H%M)
```

### 2. Baseline

```bash
pytest tests -q 2>&1 | tail -3
pytest backend/tests -q 2>&1 | tail -3
# anotar N passed. Qualquer falha nova pós-sweep = rollback.

# Re-rodar audit baseline
python dev/audit_code_style.py --format json --output-dir _scratch/
# Antes de qualquer edit, anotar:
# - Total MagicMock em backend/tests
# - Total fixtures >20l in-scope
# - Total nomes genéricos
```

### 3. Tiers em ordem (T1 → T2 → T3 opcional → T4 opcional)

### 4. Gates de push

```bash
pre-commit run --all-files
pytest tests -q                          # zero regressão
pytest backend/tests -q                  # zero regressão
# Frontend não precisa — A6g.5 não toca frontend/

# Audit confirma redução
python dev/audit_code_style.py --format json --output-dir _scratch/
# MagicMock deve ter caído; contador de fixtures longas também

# Drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] `grep -rn "MagicMock(" backend/tests/test_events.py` = 0 ocorrências (ou só em docstring/comentário).
- [ ] `grep -rn "MagicMock(" backend/tests/test_pipeline_task.py` ≤ baseline (A6f.1 pode ajustar).
- [ ] `backend/tests/fakes/` existe com pelo menos 2 fakes nomeados novos (`FakeRedisPublisher`, `FakeLLMClient` ou similar).
- [ ] Zero novos `unittest.TestCase`, zero `setUp()` classe-based (validar com `grep`).
- [ ] `pytest tests -q` + `pytest backend/tests -q` com **mesmo número** de tests passando (+ opcional: novos tests não destruídos).
- [ ] Audit pós-sweep mostra redução em `P1_long_functions` nos arquivos tocados + redução em "magic_mock_inline" (se existir categoria).
- [ ] Nenhum arquivo em §3 (goldens) alterado — `git diff --stat` não lista eles.
- [ ] `pre-commit run --all-files` passa.

---

## Rollback criteria — ABORTE se

- Qualquer golden (`test_e*_golden_execution.py`, `_parity`, `round_trip`) passa a falhar.
- Total de tests `pytest -q` cai vs baseline (teste deletado por engano).
- Fake nomeado quebra em paralelismo (xdist); precisa de isolation por-process.
- Rename conflita com `pytest.ini` / `conftest.py` collection (`test_foo` vira `foo_test` por engano).
- `pytest backend/tests -q` mostra >5 failures novos vs baseline.

---

## Anti-patterns a evitar

- **Renomear teste sem entender o que ele testa.** Ler código + última execução do CI antes de mudar nome.
- **Consolidar 3 tests em 1 paramétrico "porque é mais limpo"** quando os 3 testam invariantes distintas. Paramétrico é bom para **mesmo conceito × input diferente**, não para "cabe numa tabela".
- **Mover `FakeFoo` para `pipeline/fakes/`.** Fakes de backend ficam em `backend/tests/fakes/`; pipeline fakes já vivem em `pipeline/artifact_store.py` (in-memory). Respeite a fronteira.
- **Tocar golden "só para consistência de nome".** A listagem de 16 arquivos é imutável por este sweep. Volta em A6g.5b pós-A6c.3 (se fizer sentido).
- **Split de arquivo grande que muda collection.** Se separar `test_llm_stages.py` em 3 arquivos e o total de collected tests mudar, algo está errado (provavelmente uma fixture que era módulo-scope agora não é visível).
- **Misturar Tier 1 + Tier 2 num commit.** Tier 1 é semântico (novos fakes); Tier 2 é puramente rename. Gate independente por commit facilita rollback cirúrgico.

---

## Coordenação com outros agentes

Em paralelo a você, lanes ativas:

- `agent/a6g2-pipeline-style/*` — `scripts/`, `pipeline/`, `tests/fixtures/`. **Zero overlap** — `tests/fixtures/` é dele, `tests/test_*.py` é seu.
- `agent/a6g4-frontend-style/*` — 🚧 `frontend/src/`. **Zero overlap** com `tests/`, `backend/tests/`.
- `agent/a6f1-pipeline-service/*` — **OVERLAP potencial** em `backend/tests/test_pipeline_task.py` (A6f.1 slice 2 reescreve imports). **Regra:**
  - Se A6g.5 merge primeiro → A6f.1 faz rebase e consome seus fakes nomeados.
  - Se A6f.1 slice 2 merge primeiro → A6g.5 consome os fakes dele (`InProcessPipelineClient` substitui vários `MagicMock`).
  - Antes de começar T1.b, verifique `git log origin/main --oneline | head -10` — se tem commit A6f.1 slice 2, ajuste plano.
- `agent/a6e3-use-cases/*` — `backend/app/application/` + `backend/tests/application/` (diretório novo). **Overlap mínimo** (testes novos em diretório novo; você renomeia testes existentes em `backend/tests/*.py` raiz).

**Hotspots compartilhados** (`docs/CHANGELOG.md` + `docs/BACKLOG.md`):

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no **mesmo turno** (≤5min).

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# Se CLAUDE.md mudou, releia §Testes e §Antes de pegar uma task
```

---

## O que este sweep NÃO entrega (explicitar no CHANGELOG)

- **Rename em goldens** — 16 arquivos listados em §3 permanecem.
- **Split de `test_llm_stages.py` (920 linhas)** se Tier 4 não for executado.
- **Fakes em `tests/fakes/`** — diretório existe para pipeline (`InMemoryArtifactStore`); backend tem seus próprios. Unificar seria over-reach.
- **Frontend tests** — A6g.4 (🚧).
- **Fixtures em `tests/fixtures/`** — A6g.2.
- **Enforcement em pre-commit** — A6g.6.

---

## Referências

- Baseline: `docs/audits/code_style_audit_20260421.md`
- Regras: `CLAUDE.md §Code style` + §Testes
- Padrão de fake: `pipeline/artifact_store.py::InMemoryArtifactStore`
- Factories backend: `backend/tests/factories/builders.py`
- Prompts paralelos: [track_a6g2](track_a6g2_pipeline_style_sweep.md), [track_a6g4](track_a6g4_frontend_style_sweep.md), [track_a6f1](track_a6f1_pipeline_service.md), [track_a6e3](track_a6e3_use_cases.md)
- ADRs relevantes: ADR-097 (domain types em tests), ADR-107 (DB isolation)
