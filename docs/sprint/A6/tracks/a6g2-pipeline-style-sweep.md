---
id: TRACK-a6g2-pipeline-style-sweep
type: track
title: "Track A6g.2 — Pipeline Code Style Sweep"
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

# Track A6g.2 — Pipeline Code Style Sweep

> **Lane ID:** A6g.2
> **Branch prefix:** `agent/a6g2-pipeline-style/*`
> **Depende de:** A6g.1 ✅ (baseline de ofensores em `docs/archive/audits/`)
> **Paralelo com:** A6g.4 frontend sweep (zero overlap — toca só `frontend/src/`)
> **Conflita com:** commits simultâneos em `scripts/`, `pipeline/`, `tests/fixtures/`
> **Onda:** 1
> **Índice de prompts:** [docs/agent_prompts/README.md](README.md)
> **Fonte de verdade das regras:** [CLAUDE.md §Code style](../../CLAUDE.md#code-style)

> **Objetivo:** aplicar o `## Code style` do CLAUDE.md ao Python em
> `scripts/`, `pipeline/` e `tests/fixtures/`, consumindo o baseline de
> ofensores já catalogado em `docs/archive/audits/code_style_audit_20260421.md`
> (A6g.1 ✅).
>
> **Por que defensivo:** o pipeline tem **goldens de paridade** em E3,
> E4, E5, E5.N, E6 e E7 (tolerância 0,01 BRL em whitelist monetária).
> Qualquer refactor em scripts `eN_*.py` que mexa num caminho tocado
> pelos goldens pode quebrar ~1184 testes silenciosamente. Este sweep
> ataca **só o que é comprovadamente seguro** nesta rodada; o resto
> volta como A6g.2b depois de A6c.3 deletar os `main(root_dir)` legados.
>
> **Paralelizável:** Zero overlap com `backend/app/` (A6e Task
> concluída) e com `frontend/src/` (A6g.4 em andamento). Você toca
> **apenas** `scripts/`, `pipeline/`, `tests/fixtures/` dentro dos
> targets listados.

---

## Contexto crítico — leia antes de tocar qualquer arquivo

### 1. A6c.3 ainda está ☐ — NÃO toque `main(root_dir)` legado

`docs/BACKLOG.md §A6c`:

```
A6c.3 | Deletar main(root_dir) legado dos 7 scripts determinísticos
        (E1.5c, E3, E4, E5, E5.N, E7) — manter helpers reutilizados
```

Os scripts `e3_reconcile.py`, `e4_categorize.py`, `e5_analyze.py`,
`e5n_narrativas.py`, `e7_review.py`, `e15_consolidate.py` hoje têm
**DUAS** entradas: `main(root_dir)` (legado — será deletado em A6c.3) e
`main_with_store(ctx)` (canônico Caminho B). Qualquer trabalho de style
dentro de `main(root_dir)` é **trabalho desperdiçado** — A6c.3 vai
apagar a função inteira. Não toque.

**Exceção:** `scripts/e_reset.py::main` (372 linhas) e
`scripts/e0_audit.py::main(root_dir)` **são** entrada de produção
(e_reset é CLI, e0_audit é chamado por `pipeline/stages/e0_audit.py`).
Ambos estão no escopo deste sweep.

### 2. Scripts com goldens = fora de escopo nesta rodada

| Script                      | Goldens em                               | Ação                |
| --------------------------- | ---------------------------------------- | ------------------- |
| `scripts/e3_reconcile.py`   | `tests/test_e3_golden_execution.py`      | **não tocar**       |
| `scripts/e4_categorize.py`  | `tests/test_e4_golden_execution.py`      | **não tocar**       |
| `scripts/e5_analyze.py`     | `tests/test_e5_golden_execution.py`      | **não tocar**       |
| `scripts/e5n_narrativas.py` | `tests/test_e5n_golden_execution.py`     | **não tocar**       |
| `scripts/e6_render.py`      | `tests/test_e6_golden_execution.py`      | **não tocar**       |
| `scripts/e7_review.py`      | `tests/test_e5n_e7_main_with_store_parity.py` | **não tocar** |

Esses são os **maiores ofensores** P2 (3875, 2862, 1478, 1268, 1090
linhas). Volta como A6g.2b depois de A6c.3 — prompt separado.

### 3. Rodar goldens antes e depois

Mesmo tocando **só** o escopo abaixo, `pytest tests -q` full **é
obrigatório** antes de cada push. Qualquer mudança de status em golden
= **rollback imediato**, não "corrige no próximo commit".

---

## Regras inegociáveis

Do CLAUDE.md `## Code style`:

1. **Funções 4-20 linhas.** Cap aspiracional; `high` severity = >40
   linhas. Passou, extraia.
2. **Arquivos ≤500 linhas.** Divida por responsabilidade.
3. **Uma coisa por função, uma responsabilidade por módulo** (SRP).
4. **Early returns > ifs aninhados.** Máximo 2 níveis de indentação em
   lógica; 3 aceitável só em parsing.
5. **Nomes específicos e únicos.** Evite `data`, `handler`, `Manager`,
   `Service` (sozinho), `Utils`, `Helpers`. Grep <5 hits é o teste.
6. **Type hints** obrigatórios em toda API pública. `Dict[str, Any]`
   só em código interno dinâmico.
7. **Dinheiro nunca é `float`** (ADR-090). Se encontrar `float` em
   fluxo monetário, **pare** e abra task separada — não é escopo de
   style sweep.
8. **Preserve comentários existentes em refactor.** Eles carregam
   histórico.
9. **Formatter:** `ruff format` + `ruff check` rodam no pre-commit.
   Diff "formatter-only" **nunca** mistura com lógica.
10. **Pipeline não importa framework.** `pipeline/**/*.py` sem
    `fastapi`/`celery`/`sqlalchemy` (enforçado por
    `dev/check_pipeline_boundaries.py`).

---

## Targets — tier por risco

### Tier 1 — Alvo primário (zero golden exposure)

#### T1.a — `scripts/e_reset.py::main` (len=372, file=1333)

- **Por que seguro:** CLI interativa (usuário faz reset do workspace).
  Nenhum golden chama `e_reset`. Nenhum teste automatizado executa
  `main()` inteira; `tests/test_stage_wrappers.py` só checa import.
- **Padrão de decomposição:**
  - Extrair `_parse_args()` → função dedicada
  - Extrair `_resolve_reset_plan(args, state)` → retorna struct com
    stages, files, dry_run
  - Extrair `_confirm_interactive(plan)` → loop de prompts
  - Extrair `_execute_plan(plan)` → dispatch para helpers já existentes
    (`artifacts_full_reset`, `delete_artifacts`, `run_script`, etc)
  - `main()` vira orchestrator ≤30 linhas: parse → resolve → confirm →
    execute
- **Gate:** `python scripts/e_reset.py --help` imprime usage idêntica
  antes/depois. Smoke manual com `--dry-run` comparando output é
  suficiente.

#### T1.b — `tests/fixtures/pdf_generator.py` (file=1067)

- **Por que seguro:** fixture para `tests/test_e2_synthetic_pdf_parsers.py`.
  Nenhum golden de paridade monetária depende desse arquivo —
  só testes de parser (E2) que validam shape do JSON extraído.
- **Padrão de decomposição:**
  - Mover cada `_draw_<banco>_<tipo>()` para `tests/fixtures/pdf/<banco>.py`
    (ex.: `tests/fixtures/pdf/itau.py`, `.../c6.py`, `.../rico.py`,
    `.../wise.py`, etc)
  - `tests/fixtures/pdf/formatters.py` — `_format_brl`,
    `_format_caixa_valor_cd`, `_format_usd_amount`,
    `_iso_date_to_br`, `_period_to_br_range`, `_wise_month_br`
  - `tests/fixtures/pdf_generator.py` (ou `tests/fixtures/pdf/__init__.py`)
    fica com `generate_statement()` + `write_statement_pdf()` como
    dispatcher fino (≤150 linhas)
- **Gate:** `pytest tests/test_e2_synthetic_pdf_parsers.py -q` verde
  (mesmo número de passes).

#### T1.c — `scripts/e0_audit.py::main` (len~, file=949)

- **Por que seguro:** `main(root_dir)` é a entrada **atual** (não
  legado — `pipeline/stages/e0_audit.py` chama `scripts.e0_audit.main`
  diretamente). **Não é afetado por A6c.3** (A6c.3 só deleta mains de
  E1.5c/E3/E4/E5/E5.N/E7).
- **Padrão:** arquivo tem 15 `def check_*()` funções independentes
  (`check_filename_vs_content`, `check_orphans`, `check_duplicates`,
  `check_inbox_log`, `check_saldo_gaps`, `check_hash_duplicates`,
  `check_name_collisions`, `check_html_as_xls`, `check_extract_naming`).
  Quebrar arquivo em:
  - `scripts/e0/audit_filename.py` — filename vs content, extract naming,
    html-as-xls, name collisions
  - `scripts/e0/audit_integrity.py` — orphans, duplicates, hash
    duplicates
  - `scripts/e0/audit_ledger.py` — inbox log, saldo gaps
  - `scripts/e0/audit_helpers.py` — `normalize`, `parse_data_filename`,
    `parse_e2_filename`, `_init_config`
  - `scripts/e0_audit.py` vira orchestrator fino (`main(root_dir)`
    chama helpers → agrega resultados → imprime) com ≤300 linhas
- **Gate:** `python scripts/e0_audit.py` em workspace de dev produz
  output **idêntico** antes/depois (ordenar + diff). Também
  `pytest tests/test_stage_wrappers.py -q` verde.

### Tier 2 — Opcional (risco moderado; só se sobrar tempo)

#### T2.a — `pipeline/domain/services/narrativas/charts_narrator.py::narrate` (len=284)

- **Por que moderado:** função pura, mas `ChartsNarrator` é chamada
  por `NarrativasBuilder` no fluxo E5.N. `tests/test_e5n_builder_decomposition.py`
  e `tests/test_e5n_golden_execution.py` exercitam o output textual.
- **Padrão:**
  - `narrate()` gera narrativas por tipo de gráfico. Extrair métodos
    privados `_narrate_fluxo()`, `_narrate_patrimonio()`,
    `_narrate_investimentos()`, etc, e chamar sequencialmente
  - `narrate()` fica ≤30 linhas como orchestrator
- **Gate:** `pytest tests/test_e5n_golden_execution.py tests/test_e5n_builder_decomposition.py -q`
  verde. **Se um golden falhar mesmo em 1 string**, rollback.

#### T2.b — `backend/app/tasks/pipeline_task.py::run_pipeline_task` (len=273)

- **Por que moderado:** Celery task. `backend/tests/test_pipeline_task.py`
  tem cobertura. Mexer aqui é no limite do escopo (backend) — só inclua
  se o sweep de pipeline foi rápido e você quer preencher.
- **Padrão:** extrair fases: `_setup_run_context()`,
  `_execute_stages_loop()`, `_finalize_run()`, `_handle_cancellation()`.
  `run_pipeline_task()` vira orchestrator ≤50 linhas.
- **Gate:** `pytest backend/tests/test_pipeline_task.py -q` verde +
  `make update-openapi-snapshot` (não muda, mas confirma).

### Tier 3 — Explicitamente fora de escopo

- **Todos os scripts `eN_*.py` com goldens:** e3_reconcile,
  e4_categorize, e5_analyze, e5n_narrativas, e6_render, e7_review.
  Aguardar A6g.2b (depois de A6c.3).
- **Todas as funções `main(root_dir)` legadas** dos scripts acima —
  A6c.3 vai deletá-las.
- **`pipeline/domain/**` fora de `narrativas/charts_narrator.py`** —
  já foi refatorado extensivamente em A6d; tocar agora gera drift com
  trabalho em andamento.
- **Tests não-fixture** (`tests/test_*.py`) — sweep de testes é A6g.5
  em Onda 2.
- **P5_float_money** (79 ofensores em `backend/app/schemas/*.py`) —
  isso é mudança de tipo (float → str/Decimal) com impacto em wire
  format. Não é style sweep; abrir task dedicada.
- **P7_multiparagraph_docstring** (706 ofensores) — low severity;
  pegar por osmose em commits que já tocam o arquivo, nunca commit
  dedicado.

---

## Sequência de execução

### 1. Setup (5 min)

```bash
git fetch origin
git checkout -b agent/a6g2-pipeline-style/$(date +%Y%m%d-%H%M)
git log --oneline origin/main -5
# conferir: último commit não pode ser de agente A6g.2 rodando em paralelo
```

### 2. Baseline funcional (OBRIGATÓRIO antes de qualquer edit)

```bash
pytest tests -q 2>&1 | tail -5
# anotar: N passed em M.Xs. Qualquer número acima de 1 novo failure
# pós-refactor = rollback.

pytest backend/tests -q 2>&1 | tail -5
# anotar: N passed
```

### 3. Regenere audit baseline (gate de progresso)

```bash
python dev/audit_code_style.py --format json --output-dir _scratch/
grep -c '"category":' _scratch/code_style_audit_*.json
# total inicial = 2047 (confere com docs/archive/audits/code_style_audit_20260421.md)
```

Cada commit seu deve **reduzir** o contador de P1/P2 sem aumentar
P3/P5/P6/P8/P9.

### 4. Commits — ordem sugerida (4-6 commits, cada um ≤400 linhas de diff)

**Commit 1** — `pipeline(scripts): decompõe e_reset::main em orchestrator fino (A6g.2 — T1.a)`
- `scripts/e_reset.py::main` 372 → ≤30 linhas (orchestrator)
- Novos helpers: `_parse_args`, `_resolve_reset_plan`,
  `_confirm_interactive`, `_execute_plan`
- Preservar comportamento CLI: `--dry-run`, `--stage`, `--all`, etc
- Gate: `python scripts/e_reset.py --help` idêntico,
  `pytest tests/test_stage_wrappers.py -q` verde,
  `pytest tests -q` total stable

**Commit 2** — `tests(fixtures): divide pdf_generator 1067 → módulos por banco (A6g.2 — T1.b)`
- Extrai `tests/fixtures/pdf/{itau,c6,bradesco,caixa,santander,rico,wise,picpay,bankofamerica,btgpactual,quintoandar}.py`
- `tests/fixtures/pdf/formatters.py` para utilitários
- `tests/fixtures/pdf/__init__.py` re-exporta
  `generate_statement`, `write_statement_pdf`
- Arquivo principal `tests/fixtures/pdf_generator.py` pode ficar como
  shim de compat (`from tests.fixtures.pdf import *`) ou ser removido
  se grep confirmar único call-site
- Gate: `pytest tests/test_e2_synthetic_pdf_parsers.py -q` verde

**Commit 3** — `pipeline(scripts): divide e0_audit 949 → checks por responsabilidade (A6g.2 — T1.c)`
- Extrai `scripts/e0/audit_{filename,integrity,ledger,helpers}.py`
- `scripts/e0_audit.py::main` vira orchestrator: import checks, agrega,
  imprime
- **Mantém `main(root_dir)` como entry point** — ela **não é legado**,
  é chamada por `pipeline/stages/e0_audit.py`
- Gate: output de `python scripts/e0_audit.py` em workspace dev =
  diff zero linha-a-linha (comparar com `> before.txt`, `> after.txt`)
- Gate: `pytest tests/test_stage_wrappers.py -q` verde

**Commit 4 (opcional Tier 2a)** — `pipeline(narrativas): extrai métodos privados em ChartsNarrator.narrate (A6g.2 — T2.a)`
- `narrate()` 284 → ≤30 linhas
- Métodos privados `_narrate_<tipo>` por seção de gráfico
- Gate: `pytest tests/test_e5n_golden_execution.py tests/test_e5n_builder_decomposition.py -q` verde
- **Rollback imediato** se golden falhar em QUALQUER string

**Commit 5 (opcional Tier 2b)** — `backend(tasks): extrai fases de run_pipeline_task (A6g.2 — T2.b)`
- `run_pipeline_task` 273 → ≤50 linhas
- Helpers: `_setup_run_context`, `_execute_stages_loop`,
  `_finalize_run`, `_handle_cancellation`
- Gate: `pytest backend/tests/test_pipeline_task.py -q` verde,
  `make update-openapi-snapshot` sem diff

**Commit N+1** — `docs(a6g.2): CHANGELOG + BACKLOG — 1ª rodada sweep pipeline`
- `docs/CHANGELOG.md [Unreleased]` — seção "A6g.2 1ª rodada" com:
  - Arquivos tocados (e_reset, pdf_generator, e0_audit, ±
    charts_narrator, pipeline_task)
  - Contagem antes/depois P1 long_functions + P2 long_files nos
    targets
  - Nota: "e3/e4/e5/e5n/e6/e7 fora de escopo — aguardando A6c.3"
- `docs/BACKLOG.md` — marcar A6g.2 "🚧 parcial — Tier 1 concluído
  2026-04-XX" (Tier 3 volta em A6g.2b)
- **Commit separado** (hotspot) — janela ≤5min

### 5. Gates de push (OBRIGATÓRIO)

```bash
# Pre-commit hooks
.venv/bin/pre-commit run --all-files

# Pipeline full — incluindo todos os goldens
pytest tests -q
# Deve casar com baseline. Qualquer teste novo que falha = rollback.

# Backend (se tocou Tier 2b)
pytest backend/tests -q

# Regenera audit — confirma redução
python dev/audit_code_style.py --format json --output-dir _scratch/
# Compare com baseline; P1 + P2 nos targets devem ter caído

# Drift check (obrigatório antes do push)
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
if [ "$BEHIND" -gt 0 ]; then
  git rebase origin/main
  pytest tests -q   # regressão silenciosa pós-rebase
fi

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] `scripts/e_reset.py::main` ≤30 linhas; arquivo total ≤1000 linhas
- [ ] `scripts/e0_audit.py` (arquivo) ≤300 linhas; novos módulos
      `scripts/e0/*.py` cada ≤400 linhas
- [ ] `tests/fixtures/pdf_generator.py` ≤150 linhas OU removido;
      novos módulos `tests/fixtures/pdf/*.py` cada ≤300 linhas
- [ ] `pytest tests -q` passa — mesmo número de testes passed do
      baseline, zero novos failures
- [ ] `pytest backend/tests -q` passa (se tocou Tier 2b)
- [ ] `pre-commit run --all-files` passa
- [ ] `python dev/audit_code_style.py` mostra redução de P1 e P2 nos
      targets; sem aumento em P3/P5/P6/P8/P9
- [ ] 3-5 commits atômicos em `origin/main` fast-forward
- [ ] `docs/CHANGELOG.md [Unreleased]` tem entrada A6g.2 1ª rodada
      com deltas numéricos + nota sobre Tier 3 deferrido
- [ ] `docs/BACKLOG.md` §A6g.2 marca parcial + data

---

## Rollback criteria — ABORTE o sweep se

- Qualquer teste golden (`test_e*_golden_execution.py`) passa a falhar
- Qualquer teste `test_e5n_builder_decomposition.py` ou
  `test_e5n_e7_main_with_store_parity.py` muda status
- `pytest tests -q` mostra número de passed menor que baseline em **≥1**
- `python scripts/e_reset.py --help` ou `python scripts/e0_audit.py`
  produzem output não-idêntico ao baseline
- `dev/check_pipeline_boundaries.py` falha (você importou framework
  dentro de `pipeline/`)
- Mudança sub-reptícia de comportamento (ex.: reordenar dict, mudar
  default arg) que passa nos testes mas não deveria estar no escopo

**Em rollback:** `git reset --hard origin/main` na sua branch local,
anuncie no chat o aprendizado, documente no `docs/CHANGELOG.md` como
"A6g.2 tentativa X — rollback, razão Y" (se já tinha commitado algo),
e abra issue para revisão do target.

---

## Anti-patterns a evitar

- **Tocar script `eN_*.py` com golden.** Mesmo "só extrair helper
  puro". Todo commit em `e3/e4/e5/e5n/e6/e7` está fora de escopo nesta
  rodada.
- **Refatorar `main(root_dir)` dos scripts legados.** A6c.3 vai
  deletá-los — trabalho desperdiçado.
- **Misturar categorias num commit.** "P1 + P2 do mesmo arquivo" OK
  (mesmo refactor resolve ambos), "P1 de arquivo A + P7 de arquivo B"
  não.
- **Formatter-only no mesmo commit de mudança real.** Rode
  `ruff format` em commit separado ou deixe pre-commit rodar antes.
- **Touch em `config/`.** Config é fonte de verdade de domínio
  (ADR-089). Se achar que precisa mudar shape de config, saia do
  escopo.
- **Mover lógica para comentário-tipo docstring multi-parágrafo** só
  para passar no linter. Remove o comentário **ou** deixe como está —
  docstring inflado é pior que função longa.
- **Arquivos temporários/reports na raiz.** Só em `_scratch/`
  (gitignored).

---

## Coordenação com outros agentes

Em paralelo a você pode estar rodando (Onda 1):
- `agent/a6g4-frontend-style/*` — sweep frontend
  (`docs/agent_prompts/track_a6g4_frontend_style_sweep.md`).
  Zero overlap — nunca toca `scripts/`, `pipeline/` ou `tests/fixtures/`.

**Hotspots compartilhados** (`docs/CHANGELOG.md` + `docs/BACKLOG.md`):

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md
```

Se agente A6g.4 (ou outro) fez commit <30min, pause 2 min, anuncie,
commite o doc e faça push no **mesmo turno** (janela ≤5min). Nunca
edite CHANGELOG e BACKLOG simultâneo com outro agente.

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# se origin/main moveu ≥1 commit, rebase incremental antes de continuar
# se CLAUDE.md mudou, releia §Code style antes de seguir
```

---

## O que este sweep NÃO entrega (explicitar no CHANGELOG)

- **Decomposição dos scripts grandes com goldens** (e3/e4/e5/e5n/e6/e7,
  >1000 linhas cada, representam 11 ofensores P2 + ~250 P1) — volta
  como **A6g.2b** depois de A6c.3 (que deleta `main(root_dir)`
  legado e abre o caminho para separar pipeline canônico do legado
  sem mexer em duas entradas).
- **P3 (dict_str_any_boundary, 71 ofensores)** — exige introduzir
  Pydantic DTOs nos boundaries afetados; é refactor de tipos, não de
  layout. A6g.3 em Onda 2.
- **P5 (float_money, 79 ofensores)** — mudança de tipo no wire format
  (float → string Decimal). Requer migração coordenada backend ↔
  frontend. Task dedicada pós-sweep.
- **P7 (multiparagraph_docstring, 706 ofensores)** — low severity;
  fica como "limpar por osmose" em commits que já tocam o arquivo,
  nunca como commit dedicado.
- **Enforcement automatizado** (ruff rule `--select=C901`,
  max-complexity) — só vale ligar o gate quando os números de P1
  estiverem baixos. A6g.6 em Onda 3.

---

## Referências

- Baseline de ofensores: `docs/archive/audits/code_style_audit_20260421.md`
- Regras de style: `CLAUDE.md §## Code style`
- Modelo de prompt frontend paralelo:
  `docs/agent_prompts/track_a6g4_frontend_style_sweep.md`
- Plano mestre A6: absorvido em 2026-04-21 nas fontes canônicas
  ([BACKLOG §Sprint A6](../BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal),
  [ARCHITECTURE §17](../ARCHITECTURE.md#17-arquitetura-alvo-pós-a6-migração-infradomínio),
  [TESTING §Critérios de aceite](../TESTING.md#critérios-de-aceite-por-fase-da-migração-a6),
  [runbooks/cutover.md](../runbooks/cutover.md))
- ADRs relevantes: ADR-089 (ISP services), ADR-090 (Money), ADR-097
  (domain types), ADR-101 (per-aggregate DDD), ADR-111 (stateless)
