---
id: A34.l24
type: lane
title: "Varredura da PII residual sub-contada pelo audit (código/testes/fixtures/schema)"
sprint: A34
plan: PLAN-public-release
status: in_progress
priority: P1
branch_slug: residual-pii-surface
adrs: ["[[ADR-319]]"]
depends_on: ["[[A34.l9]]", "[[A34.l10]]", "[[A34.l11]]"]
tags:
  - type/lane
  - sprint/a34
  - status/in-progress
  - priority/p1
  - area/seguranca
---

# A34.l24 — `residual-pii-surface` (W1 · Saneamento — follow-up)

## Problema

A execução da [[A34.l9]] revelou que o [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md)
**sub-contou** a superfície de PII: os hotspots enumerados (§1.3–1.8) eram uma
amostra, não um inventário exaustivo. As lanes [[A34.l7]]–[[A34.l11]] limparam o
enumerado; sobra superfície real que **os gates de [[ADR-319]] baselineiam**
(logo não bloqueiam) mas que o flip público (W8) exporia. Decisão-independente de
[[ADR-316]] (in-place × repo-novo) — precisa ser limpa nos dois caminhos.

## Escopo (três categorias, todas fora do enumerado do audit)

1. **Resíduo no seed de produção** (`backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py`):
   1º nome `ELIANE` + negócio nomeado `ANDREA S LAVANDERIA` na lista
   `servicos_domesticos` (baixo-confiança; nomes completos já removidos pela
   [[A34.l11]]). Merchants públicos (COBASI/PETZ/etc.) permanecem.
2. **Sobrenome da família** (`*ferreira_campos`, member-keys de titular+cônjuge)
   persiste em ~15 arquivos de **teste** (`test_member_name_resolver.py`,
   `test_titular_key_normalizer.py`, `test_e15_member_cpf_resolver.py`, …),
   `tests/pipeline/perf/baseline_disk.json`, comentário em
   `pipeline/domain/services/property_identity_enricher.py`,
   `config/schemas/goal.alocacao_alvo.v2.schema.json` (**contrato — coordenar
   `data-engineer`**) e ADRs 126/141/243/268. Trocar member-key **quebra
   assertions** → atualizar assertion + fixture no mesmo commit.
3. **Nomes de terceiros/empresas** em código/prompts/fixtures:
   `pipeline/llm/prompts/apolice.py` (bump `PROMPT_VERSION`),
   `scripts/reconcile_transactions.py`, `pipeline/domain/services/_tx_identity.py`,
   `tests/fixtures/llm_golden/*` (**hook `golden-rebaseline-isolation`: golden em
   commit separado**), `tests/fixtures/pdf/generator.py`, `config/report_spec.md`
   (resíduo pós-[[A34.l11]]), `config/methodology.md`.

Placeholders canônicos: `Titular`/`Cônjuge`, `Prestador Exemplo`,
`Cliente PJ Exemplo`, `Empregador Exemplo`, placa `ABC1D23`, matrícula `999.999`.

## Critério de aceite

- `git grep` de cada padrão (sobrenome, 1º nome de prestador, nomes de
  terceiros/empresas, placas) = **zero** fora do inventário mascarado
  (`docs/plan/PUBLIC_RELEASE/`, `docs/sprint/A34/`).
- Gates verdes: `lint_no_real_pii`, `check_sigilo_terms --all`,
  `check_code_style_regression`, `golden-rebaseline-isolation`.
- Suíte completa verde (toca testes — assertions atualizadas).
- **Fechamento:** encolher os baselines burn-down
  (`dev/sigilo_terms_baseline.json` + `tests/utils/pii_lint_baseline.json` via
  `--update-baseline`) num commit próprio, refletindo a limpeza.

## Notas

- **Owner-visível antes de executar:** toca assertions de teste + um contrato de
  schema ([[ADR-141]] `alocacao_alvo` v2, escopo `data-engineer`). Não é sweep
  autônomo de madrugada — daí a prioridade P1 e o chip de tarefa criado
  2026-07-09.
- **Não bloqueia** as ondas já mergeadas; é burn-down adicional antes de W8.

## Referências

- Plano: [[PLAN-public-release]] (Onda W1 · burn-down).
- Origem: relatório da [[A34.l9]] (2026-07-09).
- Contrato de gate: [[ADR-319]].
- Pares W1: [[A34.l9]] · [[A34.l10]] · [[A34.l11]].
