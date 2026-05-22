---
id: CHG-2026-05-22-A18-L1-CRLV-SHIPPED
type: changelog-entry
date: "2026-05-22"
sprint: A18
lane: "[[A18.l1]]"
adrs: ["[[ADR-239]]"]
summary: |
  feat(adr-239): A18 L1 (CRLV-e + tabela vehicles + reconciliação fuzzy IRPF G02)
  entregue em 5 PRs sequenciais (#388, #391, #412, #414, #416, #417). ADR-239
  flippada Proposto → Decidido (Sprint A18 L1). Padrão arquitetural validado —
  L2 (apólice de seguro) e L3 (FIPE refresh) replicam.
tags:
  - type/changelog-entry
  - sprint/a18
  - status/shipped
  - status/decidido
  - area/pipeline
  - area/persistence
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
---

# feat(adr-239): A18 L1 CRLV-e (comprovante de bem · veículo) shipped

## Sumário

Lane [[A18.l1]] entregue em 5 PRs squash-mergeados sequencialmente em `main` (todos com CI verde), validando padrão arquitetural completo para ingestão de comprovantes de bens polimórficos:

- **P1** [#388](https://github.com/davidrobert/mathoms/pull/388) — migration Alembic `vehicles` (UNIQUE `(workspace_id, placa)`, CHECK RENAVAM 9-11 dígitos ANSI portátil, CHECK `codigo_rfb IN ('21','22','23')`) + `market_rates.reference_month` + SQLAlchemy `Vehicle` model + invariante `codigo_rfb` imutável (ADR-225).
- **P2** [#391](https://github.com/davidrobert/mathoms/pull/391) — `CRLVPayload` Pydantic V2 strict (regex placa Mercosul+legado, normalização `mode='before'`) + prompt LLM Haiku + `PROMPT_VERSION = "crlv-v1.0.0"` + cache key SHA-256 do PDF.
- **P3** [#412](https://github.com/davidrobert/mathoms/pull/412) — `TypeRule crlv_eletronico` content-first + `DocumentType.comprovante_bem` + migration `adr239vehicles2` ALTER TYPE ADD VALUE.
- **P4** [#414](https://github.com/davidrobert/mathoms/pull/414) — stage `extract_comprovantes_bens` (despacho por `tipo_comprovante`, L1 só `crlv`) + upsert vehicles (identidade imutável; colisão placa↔renavam ≠ → `needs_review`) + telemetria LGPD-safe `mathoms.comprovantes.classified`.
- **P4 parte 2+3** [#416](https://github.com/davidrobert/mathoms/pull/416) — função pura `reconcile_baseline_veiculos` (gate triplo financial-planner: `auto_merge ≥ 0.90` + `tiebreaker_gap_min 0.05` + dual threshold `review ≥ 0.75`) + runner backend `vehicle_reconciliation_runner.py` + hook em `e15_consolidate.py::main_with_store` + schema bump `baseline_patrimonial.json` (`veiculo_id` opcional retroativo).
- **P5** [#417](https://github.com/davidrobert/mathoms/pull/417) — 3 goldens sintéticos LGPD-safe (`crlv_moto.json` + `crlv_carro.json` + `crlv_zero_km.json`) + classe `TestCRLVGoldens` (9 testes: schema parses, CPF null no payload, prompt_version bumped, confidence threshold, regex placa/renavam, `_build_payload` force prompt_version) + flip ADR-239 → `Decidido (Sprint A18 L1)` + lane → `shipped`.

## ADR

[[ADR-239]] flippada `Proposto → Decidido (Sprint A18 L1)`. Seção `## Entrega — L1 (CRLV-e)` adicionada com PRs + padrão arquitetural validado + débito conhecido (UI S4 disclaimer bloqueado por L3; `veiculos_consolidados[]` ainda é fonte de E5; `member_key` não confiável pós-LGPD).

## Padrão arquitetural validado (replicar em L2/L3)

- Tabela canônica para identidade cross-source — padrão `real_estate_assets` (ADR-216).
- Identidade imutável (ADR-225) — colisão `placa↔renavam` ≠ → `needs_review`, não merge automático.
- Reconciliação fuzzy assíncrona via função pura `pipeline/domain/services/` + runner backend `backend/app/services/` (ADR-097 isolation).
- LGPD ADR-231 — telemetria sem PII; CPF mascarado em Python pós-LLM (LLM nunca retorna CPF — instrução SYSTEM_PROMPT força null).
- Cache LLM idempotente por SHA-256 do PDF + PROMPT_VERSION (ADR-144).
- Schema validation hook em `DBArtifactStore.write` (ADR-212 PR3) — `informe_base.schema.json` reaproveitado para comprovantes na L1.

## Próximo

- **A18 L2** — apólice de seguro (auto + residencial; combinada Porto como caso V1) — replica padrão; discriminated union `ApolicePayload` antecipa V2 (vida/saúde/acidentes).
- **A18 L3** — FIPE refresh assíncrono via BrasilAPI — destrava disclaimer S4.
- **A19** — card S_PROTECAO (4º pilar AUVP) — depende de A18 L1+L2 (precisa de identidade `vehicles` + apólices ativas).
