---
id: TRACK-a17-l1-previdencia-privada
type: track
title: "Track A17 L1 — Previdência privada (PGBL/VGBL): schema-base + parser LLM + FiscalAnalyzer polimórfico + UI"
lane: "[[A17.l1]]"
sprint: A17
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a17
  - status/ready
  - area/pipeline
  - area/methodology
  - area/persistence
  - area/report
  - area/backend
  - area/frontend
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
---

# Track A17 L1 — Previdência privada (PGBL/VGBL)

> **Lane:** [[A17.l1]] · **ADR canônica:** [[ADR-238]] §D1-D9 + §Gates + §Implementação
> · **Branch prefix:** `agent/a17-l1-previdencia-P<N>/*` (um prefixo por fase, se quebrar em múltiplos PRs)
> · **Pré-requisito:** [[ADR-238]] mergeada em `main` como `Proposto`
> · **Bloqueia:** [[A17.l2]], [[A17.l3]], [[A17.l4]] (esta lane valida o padrão arquitetural)
> · **Tamanho estimado:** ~7-9d eng em 4-5 PRs sequenciais

## Briefing

Sessão dogfood 2026-05-21 com 14 PDFs de Informes de Rendimentos: o informe BrasilPrev 2025 (PGBL) cai em `.other` silencioso. S8 Previdência ([[ADR-189]]) só calcula `PgblStatus.capacidade_disponivel` quando E1.6 existe — workspaces que adotam Mathoms em jan-fev (antes de declarar) ficam sem o KPI mais valioso da seção, mesmo tendo o informe da seguradora em mãos.

[[ADR-238]] decidiu **stage único `extract_informes_anuais` paralelo a `extract_irpf_full`**, com 5 tipos canônicos polimórficos. Esta lane (L1) implementa o **primeiro tipo (`previdencia_privada`)** e **valida o padrão arquitetural completo** que L2-L4 replicam.

## Decisões já fechadas (do co-design `financial-planner` + `data-engineer` 2026-05-21 · [[ADR-238]])

- **Schema-base polimórfico** com `tipo_informe` discriminator + payload tipado ([[ADR-238]] D2). Top-level lenient, sub-models strict (padrão [[ADR-216]] `informe_aluguel.py`).
- **Stage único** `extract_informes_anuais` em `STAGE_REGISTRY` com sufixo `-2_informe_anual.json` ([[ADR-238]] D3). `artifact_key` codifica tipo + instituição + ano (`previdencia_brasilprev_2024`).
- **Declaração vence informe** quando ambos existem para o mesmo `(ano_base, fonte_pagadora_cnpj)` ([[ADR-238]] D4). `source_priority` no schema-base; warning de divergência em E5 efêmero (não persistir por LGPD — [[ADR-231]]).
- **`FiscalAnalyzer` polimórfico** ([[ADR-238]] D5) sobre `FiscalSource` que aceita `IRPFFullOutput` + lista de informes. `IRPFAnalyzer` renomeado.
- **`InformeQuery` service** em `backend/app/application/informes/` para consumo por `previdencia_analyzer.py` + `irpf_renda_tributavel.py` (preparação para L2 sinergia com [[ADR-236]]).
- **VGBL nunca conta como capacidade PGBL** ([[ADR-238]] D8 + Não-objetivos). Schema modela `plano_tipo: pgbl|vgbl` mas calculator filtra.
- **LLM Sonnet** para previdência (cálculos complexos, múltiplas seguradoras com layout heterogêneo).
- **Guardrails 3 lugares** ([[ADR-238]] D8): footnote inline em KPI fiscal, badge no upload, system prompt restritivo em E6-parecer.
- **Goldens sintéticos** em `tests/fixtures/informes/previdencia/sample_brasilprev_anonymized.pdf` ([[ADR-238]] D9). Eval real fora do git.

## Plano de fases

### P1 — Migration Alembic catálogo + `InformeRendimentosBase` schema (~1d)

- Migration: `institutions.category` enum ganha `insurance`, `broker`, `holding`; nova coluna `tax_regime` default `both`.
- Seeds: `brasilprev` (insurance, both). XP e Itaúsa vêm em L3/L4.
- `pipeline/llm/schemas/informe_base.py` — Pydantic `InformeRendimentosBase` com Discriminated Union (5 tipos).
- `config/schemas/informe_base.schema.json` — JSON Schema com referências a sub-schemas.
- `pipeline/llm/schemas/informe_previdencia.py` — sub-schema strict (campos D2 de [[ADR-238]]).
- `config/schemas/informe_previdencia.schema.json`.
- Reaproveitar `CodigoRendimentoIsento` de [`pipeline/llm/schemas/e16_irpf_full.py`](../../../../pipeline/llm/schemas/e16_irpf_full.py) sem alteração in-place (gate G4).
- Hook `DBArtifactStore.write` ([[ADR-212]]) — adicionar `informe_anual` em `SCHEMA_BY_STAGE`.

**Gate P1:** `pytest backend/tests/test_models.py tests/test_schemas.py -q` verde + migration smoke test.

### P2 — Stage `extract_informes_anuais` + parser LLM previdência (~2d)

- `pipeline/stages/extract_informes_anuais.py` (paralelo a [`extract_irpf_full.py`](../../../../pipeline/stages/extract_irpf_full.py)).
- Registrar em `STAGE_REGISTRY` (`pipeline/stage_spec.py`) com nome descritivo + sufixo `-2_informe_anual.json` em `_STAGE_TO_SUFFIX` ([`pipeline/artifact_store.py`](../../../../pipeline/artifact_store.py)).
- `pipeline/llm/prompts/informe_previdencia.py` — `PROMPT_VERSION = "informe-prev-v1.0.0"`.
- LLM model: Sonnet via `anthropic` SDK ([[ADR-144]] cache idempotente).
- Despacho interno por `tipo_informe` detectado em E0 — para esta lane, só `previdencia_privada` despacha; outros tipos `raise NotImplementedError` com mensagem clara (apontando lane correspondente).

**Gate P2:** smoke test com `tests/fixtures/informes/previdencia/sample_brasilprev_anonymized.pdf` produz artifact válido. Schema validation verde.

### P3 — Classifier E0 + mapping E0→DocumentType (~1d)

- [`backend/app/services/classification/type_classifier.py`](../../../../backend/app/services/classification/type_classifier.py) — adicionar `TypeRule` content-based para `informepgbl` / `informe_previdencia_privada` (regex robusto: "PGBL", "VGBL", "Previdência Privada", "Tabela Regressiva", + CNPJ seguradora).
- [`backend/app/services/document_classification.py`](../../../../backend/app/services/document_classification.py) — adicionar enum `DocumentType.INFORME_RENDIMENTOS_ANUAIS`; `map_e0_doc_type_to_document_type` mapeia `informe_previdencia_privada` para esse enum (NÃO mais para `.irpf`).
- Adicionar `tipo_informe` no payload de classificação para roteamento downstream.

**Gate P3:** BrasilPrev 2025 do batch classifica como `INFORME_RENDIMENTOS_ANUAIS` + `tipo_informe="previdencia_privada"` com `confidence ≥ 0.7`. 13 outros PDFs continuam em `.other` (não regridem).

### P4 — `FiscalAnalyzer` polimórfico + `InformeQuery` service (~2d)

- Renomear [`pipeline/domain/services/irpf_analyzer.py`](../../../../pipeline/domain/services/irpf_analyzer.py) classe `IRPFAnalyzer` → `FiscalAnalyzer` (manter alias por 1 sprint para compat).
- Introduzir `FiscalSource` adapter (`pipeline/domain/services/fiscal_source.py`) com `from_irpf_full(...)` + `from_informes(...)`.
- Política de precedência [[ADR-238]] D4: declaração vence; informes preenchem gaps; divergência → warning em E5 efêmero.
- `backend/app/application/informes/informe_query.py` — service para `previdencia_analyzer.py` consumir (preparação para [`irpf_renda_tributavel.py`](../../../../pipeline/domain/services/tributario/irpf_renda_tributavel.py) em L2).
- [`pipeline/domain/services/previdencia_analyzer.py`](../../../../pipeline/domain/services/previdencia_analyzer.py) — consumir `InformeQuery` em vez de E1.6 direto. Workspace sem E1.6 mas com informe previdência **funciona**.

**Gate P4:** teste unitário em `tests/test_fiscal_analyzer.py`: (a) workspace só com informe → `PgblStatus.capacidade_disponivel > 0` quando renda tributável inferida; (b) workspace com E1.6 + informe divergente → declaração vence + warning gerado; (c) VGBL nunca conta como capacidade PGBL.

### P5 — UI integration S8 + guardrails copy + cutover (~1-2d)

- [`frontend/src/components/report/sections/S8PrevidenciaSection.tsx`](../../../../frontend/src/components/report/sections/S8PrevidenciaSection.tsx) — renderizar KPI PGBL para workspace sem E1.6 quando informe existe. Footnote: "Cálculo informativo. Confira com seu contador antes de declarar. Mathoms não substitui orientação tributária." ([[ADR-238]] D8).
- Frontend codegen: regenerar tipos via `python3 dev/codegen_report_layout.py`.
- Upload UI: badge "Documento fiscal — usado para análise patrimonial, não para preencher declaração."
- E6-parecer ([[ADR-199]]) system prompt: adicionar instrução "não recomende aporte específico em PGBL; padrão Cerbasi 'capacidade disponível, vale conversar com contador'."
- Eval LLM no parecer: golden atualizado para refletir nova narrativa quando informe presente.
- OpenAPI snapshot: `make update-openapi-snapshot` se rota nova ou DTO mudou.

**Gate P5:** E2E `@critical` `cd frontend && npm run test:e2e` verde. Smoke test manual com PDF BrasilPrev sintético. Disclaimer visível.

### P6 — Cutover + telemetria + flip ADR (~0.5d)

- Telemetria: log estruturado `mathoms.informes.classified` com `{tipo_informe, instituicao, confidence, ano_base}` (sem PII — alinhado [[ADR-231]]).
- Atualizar [docs/CHANGELOG.md](../../../CHANGELOG.md) via `docs/sprint/A17/changelog/CHG-YYYY-MM-DD-a17-l1-previdencia.md`.
- Flippar [[ADR-238]] de `Proposto` para `Decidido (Sprint A17 L1)` — só após L1 inteira (P1-P5) em `main`.
- Atualizar [[A17.l1]] status → `shipped` + `ship_pr` + `ship_date`.
- Atualizar [[MOC-sprint-a17]] §Lanes com checkmark.

**Gate P6:** PR de Decidido + flip. `git fetch origin && git log -1 origin/main` confirma commit-merge.

## Critério de aceite (lane completa)

- BrasilPrev 2025 (PDF real do batch) classifica corretamente com `confidence ≥ 0.7`.
- Workspace sem E1.6 + com informe BrasilPrev renderiza S8 com `PgblStatus.capacidade_disponivel` calculado.
- VGBL filtrado de capacidade PGBL (teste unitário).
- Declaração entregue vence informe quando divergente; warning aparece em E5.
- 13 PDFs do batch fora desta onda continuam em `.other` (não regridem).
- `pre-commit run --all-files` + `pytest backend/tests tests -q` + `cd frontend && npm test -- --run` verdes.
- Disclaimer "não substitui contador" visível em S8 + upload badge.

## Co-design já feito (não reabrir)

- Q1 (5 tipos canônicos) — [[ADR-238]] D1.
- Q2 (campos por tipo) — financial-planner consolidou em [[ADR-238]] §Implementação.
- Q3 (cascade) — [[ADR-238]] D4: declaração vence.
- Q4 (guardrails) — [[ADR-238]] D8.
- Q5 (ordem) — L1 → L2 → L3 → L4 (sinergia ADR-236 em L2).
- Q6 (objeções) — informes não vão por E2; absorção de aluguel adiada para A18; codigo_rfb invariante mantido.
