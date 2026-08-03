> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# PLAN_PROGRESS — Status agregado de planos canônicos

Volta para [`00-INDEX`](../00-INDEX.md).

18 planos detectados em [`docs/plan/`](../../plan/).

## Em execução (`in_progress`)

### PLAN-data-lineage — Data Lineage fim-a-fim + Fonte plugável

- Status: `in_progress` · Sprint atual: A26
- Sprints envolvidas: A23, A24, A25, A26, A27, A32
- Lanes: 31 done · 1 in_progress · 0 open · 1 blocked
- ADRs canônicas: [[ADR-278]], [[ADR-279]], [[ADR-280]], [[ADR-281]]

### PLAN-go-shell — Go shell (Caminho 1 da ADR-150) — port do pipeline-service para Go + Python via subprocess

- Status: `in_progress` · Sprint atual: —
- Sprints envolvidas: —
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-150]], [[ADR-303]], [[ADR-112]], [[ADR-113]]

### PLAN-internal-admin — Console interno (operadores) — IA-0 a IA-4

- Status: `in_progress` · Sprint atual: A11
- Sprints envolvidas: A30, A31, F7
- Lanes: 4 done · 0 in_progress · 0 open · 0 blocked
- ADRs canônicas: [[ADR-116]]

### PLAN-launch-trust — Launch Trust — três frentes que precisam estar verdes antes de produção

- Status: `in_progress` · Sprint atual: —
- Sprints envolvidas: A21, A22
- Lanes: 14 done · 0 in_progress · 0 open · 0 blocked
- ADRs canônicas: [[ADR-246]], [[ADR-255]], [[ADR-267]], [[ADR-268]], [[ADR-271]]

### PLAN-ledger-integrity — Ledger Integrity — conservação do razão (E3/E4) + roteamento dos 5 gaps da certificação

- Status: `in_progress` · Sprint atual: A39
- Sprints envolvidas: A39
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-347]]

### PLAN-pipeline-review-r2 — Pipeline Review r2 — remediação dos achados sistêmicos (run 9d47574c, ws-1b9f2cf5)

- Status: `in_progress` · Sprint atual: A39
- Sprints envolvidas: A39
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-343]]

### PLAN-public-release — PUBLIC_RELEASE — tornar o repo público in-place com segurança e qualidade de referência

- Status: `in_progress` · Sprint atual: A34
- Sprints envolvidas: A34
- Lanes: 12 done · 0 in_progress · 13 open · 0 blocked
- ADRs canônicas: [[ADR-313]], [[ADR-314]], [[ADR-315]], [[ADR-316]], [[ADR-317]], [[ADR-318]], [[ADR-319]], [[ADR-320]]

### PLAN-report-premium — Elevar `/reports/[id]` ao nível do `EXEMPLO_DE_RELATORIO.html`

- Status: `in_progress` · Sprint atual: —
- Sprints envolvidas: —
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-117]], [[ADR-129]]

### PLAN-report-trust — Report Trust — o relatório não pode afirmar precisão que os dados não sustentam

- Status: `in_progress` · Sprint atual: A40
- Sprints envolvidas: A28, A40
- Lanes: 12 done · 0 in_progress · 22 open · 0 blocked
- ADRs canônicas: [[ADR-191]], [[ADR-240]], [[ADR-186]], [[ADR-357]], [[ADR-358]]

### PLAN-snapshot-changelog-v3 — Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica

- Status: `in_progress` · Sprint atual: —
- Sprints envolvidas: A11
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-190]], [[ADR-148]]

### PLAN-suggestion-lifecycle — Ciclo de vida de sugestões do Parecer no /acao — supersede, thesis_key, valores determinísticos

- Status: `in_progress` · Sprint atual: A25
- Sprints envolvidas: A25
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-290]]

## Pausados (`paused`)

### PLAN-i18n — Internacionalização (i18n)

- Status: `paused` · Sprint atual: —
- Sprints envolvidas: F12
- Lanes: 1 done · 0 in_progress · 0 open · 6 blocked · 1 outras
- ADRs canônicas: [[ADR-130]]
- Pausado em: 2026-04-26 · Razão: Aguarda gatilho objetivo de demanda (ver §10). ICP confirmado em
2026-05-15: brasileiros nômades digitais morando fora do Brasil.
Escopo reduzido para 3 locales (pt-BR + en + es). Frente não-iniciada
por falta de evidência quantificada de demanda em pré-PMF; recomendação
GTM 2026-05-15 mantém pausada até atingir um dos 3 gatilhos de §10.


## Concluídos (`done`)

### PLAN-cenarios-estresse — Cenários de Estresse — plano canônico

- Status: `done` · Sprint atual: A11
- Sprints envolvidas: A8
- Lanes: 1 done · 0 in_progress · 0 open · 0 blocked
- ADRs canônicas: [[ADR-168]]

### PLAN-llm-prompts-hardening — LLM Prompts Hardening — LGPD + ADR-090 + PROMPT_VERSION + telemetria + cross-cutting

- Status: `done` · Sprint atual: A33
- Sprints envolvidas: A17, A20, A33
- Lanes: 4 done · 0 in_progress · 5 open · 0 blocked
- ADRs canônicas: [[ADR-081]], [[ADR-090]], [[ADR-097]], [[ADR-110]], [[ADR-111]], [[ADR-137]], [[ADR-157]], [[ADR-191]], [[ADR-212]], [[ADR-233]], [[ADR-246]]

### PLAN-s4-real-estate-enrichment — S4 Real Estate — Enriquecimento do card de yield (cap rate líquido + benchmarks + tabela por imóvel)

- Status: `done` · Sprint atual: A12
- Sprints envolvidas: A12
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-216]]

### PLAN-tributario-pj — Tributário PJ — Cascata Fiscal canônica (modelo de domínio + narrator correto)

- Status: `done` · Sprint atual: A16
- Sprints envolvidas: A16
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-236]]

## Rascunhos (`draft`)

### PLAN-competitive-pierre — Resposta competitiva — Pierre + ChatGPT Finance (recon, MCP, chat, memories, reposicionamento)

- Status: `draft` · Sprint atual: A11
- Sprints envolvidas: A11
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-183]], [[ADR-262]], [[ADR-263]], [[ADR-264]]

### PLAN-market-rates-ingestion — Ingestão de market rates dirigida por catálogo — Bacen SGS + Tesouro Direto

- Status: `draft` · Sprint atual: A12
- Sprints envolvidas: A12
- Lanes: _(sem lanes vinculadas por `plan:`)_
- ADRs canônicas: [[ADR-221]]

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
