---
id: CHG-2026-05-21-A17-L1-PREVIDENCIA-SHIPPED
type: changelog-entry
date: "2026-05-21"
sprint: A17
lane: "[[A17.l1]]"
adrs: ["[[ADR-238]]"]
summary: |
  feat(adr-238): A17 L1 (previdência privada PGBL/VGBL) entregue em 5 PRs
  sequenciais (#402-#407). ADR-238 flippada Proposto → Decidido (Sprint A17 L1).
  Padrão arquitetural validado — L2-L4 replicam.
tags:
  - type/changelog-entry
  - sprint/a17
  - status/shipped
  - status/decidido
  - area/pipeline
  - area/methodology
  - area/persistence
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
---

# feat(adr-238): A17 L1 previdência privada (PGBL/VGBL) shipped

## Sumário

Lane [[A17.l1]] entregue em 5 PRs squash-mergeados sequencialmente em `main` (todos com CI verde), validando padrão arquitetural completo para ingestão de informes anuais avulsos:

- **P1** [#402](https://github.com/davidrobert/mathoms/pull/402) — migration `adr238informes1` + `InformeRendimentosBase` polimórfico + sub-schema PGBL strict + seed BrasilPrev. Gate triplo (data-engineer + financial-planner) aplicado em 1 rodada.
- **P2** [#403](https://github.com/davidrobert/mathoms/pull/403) — stage runner LLM Sonnet com despacho por `tipo_informe`; cache key content-based + PROMPT_VERSION; CPF mask Python pós-LLM (LGPD).
- **P3** [#404](https://github.com/davidrobert/mathoms/pull/404) — `TypeRule informe_previdencia_privada` content-based + `DocumentType.informe_rendimentos_anuais`; migration `adr238informes2` ALTER TYPE ADD VALUE (Postgres) / no-op (SQLite). **Corrigiu bug histórico ADR-238 §Contexto §2** (informe caía em `.irpf` e quebrava pipeline silenciosamente).
- **P4** [#406](https://github.com/davidrobert/mathoms/pull/406) — `FiscalSource` adapter polimórfico (precedência D4: declaração vence; informe complementa) + `FiscalDivergencia` warnings efêmeros (LGPD) + `FiscalAnalyzer` alias (cutover A18) + `InformeQuery` service.
- **P5** [#407](https://github.com/davidrobert/mathoms/pull/407) — guardrails D8 nos 3 lugares prescritos: footnote CRC inline em S8 (`CascataFiscalCard`), badge fiscal no upload zone, regra #9 no parecer planejador (`PROMPT_VERSION` 1.0.0 → 1.1.0).

## ADR

[[ADR-238]] flippada `Proposto → Decidido (Sprint A17 L1)`. Seção `## Entrega — L1` adicionada com PRs + débito explícito.

## Telemetria

`pipeline/stages/extract_informes_anuais.py` emite evento `mathoms.informes.classified` com `{workspace_id, doc (PII-redacted), tipo_informe, instituicao, ano_base, confidence, needs_review, tokens_in/out, cost_usd}`. Zero PII, zero valor monetário ([[ADR-231]] alinhado).

## Débito explícito (deferido)

- **Plumbing E5**: `analyze_finances` ainda não consome `FiscalSource` para popular `data.tributario.pgbl_*` quando há informe sem E1.6. UI renderiza `RendaPfZeradaNotice` mesmo com informe processado. Fica como PR follow-up dentro de A17 ou em lane standalone antes da UI consumir capacidade via informe.
- **Eval golden parecer**: prompt v1.1.0 ainda não tem golden atualizado refletindo regra #9 (não-prescrição de aporte PGBL).
- **`source_artifact_id` UUID**: hoje é string-stem (lineage proxy); promoção para FK em PR que cobrir content-based metadata.
- **`IRPFAnalyzer` alias**: remover em A18 após L2 (`financeiro_pj`) consumir `FiscalAnalyzer` em produção.

## Próximas lanes da Sprint A17

- [[A17.l2]] `financeiro_pj` — C6 PJ, Stone (sinergia com [[ADR-236]] cascata fiscal).
- [[A17.l3]] `financeiro_pf` — Itaú, Santander, Caixa, Nubank, PicPay, C6 PF, XP Investimentos, Wise.
- [[A17.l4]] `proventos_acoes` — XP Proventos, Itaúsa.
