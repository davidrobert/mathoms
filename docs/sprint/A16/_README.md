---
id: MOC-sprint-a16
type: moc
title: "Sprint A16 — Flips ADR-235 nu_proprietario + ADR-236 Tributário PJ Cascata Fiscal"
aliases: ["A16", "Sprint A16"]
sprint_status: current
---

# Sprint A16 — Flips ADR-235 + ADR-236

> **Status:** `current` — sprint corrente com **2 lanes paralelas** (independentes; podem ser pegas em paralelo). Ambas implementam ADRs Proposto recém-decididas (2026-05-20).

## Resumo

Sprint com **duas lanes** que rodam em paralelo:

1. **L1 — Flip ADR-235 `nu_proprietario`** ✅ **entregue 2026-05-21** ([apps#388](https://github.com/davidrobert/mathoms/pull/388)) — adiciona valor `nu_proprietario` ao enum `classification` para cobrir imóvel em nu-propriedade com usufruto vitalício de terceiro. Frequência esperada: 5–15% do ICP wealth-tech BR (famílias com planejamento sucessório ativo). ADR canônica: [[ADR-235]] · pré-requisito [apps#382](https://github.com/davidrobert/mathoms/pull/382) ✅ mergeado.

2. **L2 — Tributário PJ Cascata Fiscal** (~9d eng em 6 fases P1-P6) — substitui card S8 com texto canned conceitualmente errado por cascata real (cálculo por regime, base PGBL canônica, inputs derivados ≫ declarados, decision triggers parametrizados). Diagnóstico em sessão dogfood 2026-05-20; co-design `financial-planner` validou metodologia. ADR canônica: [[ADR-236]] · plano: [[PLAN-tributario-pj]].

As lanes **não compartilham arquivos** — L1 toca `classification` enum cross-stack; L2 toca `BusinessProfile` + `pipeline_adapter` + narrator + UI card. Pickup independente.

## Escopo

### L1 — Flip ADR-235 `nu_proprietario`

PR único de **Decidido** que:

1. Adiciona migration Alembic estendendo CHECK constraint em `property_identity.classification` + `workspace_property_overrides.classification` com `nu_proprietario`.
2. Toca 6 call-sites identificados ([[ADR-235]] §"Plano de implementação"): models, classifier, real_estate_metrics, real_estate_adapter, type TS, dropdown UI.
3. Atualiza 4 ADRs adjacentes ([[ADR-215]] §1 lista valores, [[ADR-142]] invariante, [[ADR-145]] cat_2 não-gerador, [[ADR-216]] exclusão do denominador cap rate).
4. Atualiza prompt + golden + eval do parecer LLM E6 ([[ADR-199]]).
5. Adiciona CI gate `dev/check_classification_exhaustive.py`.
6. Testes de paridade com `uso_pessoal` + E2E `@critical`.
7. Regen OpenAPI snapshot.
8. Entrada [docs/CHANGELOG.md](../../CHANGELOG.md) citando ADR-235.
9. Flippa frontmatter da [[ADR-235]] para `Decidido (Sprint A16)`.

### L2 — Tributário PJ Cascata Fiscal

6 PRs sequenciais (~9d eng em ~2 semanas calendário):

- **P1** — `BusinessProfile` expandido (anexo_simples III/V, iss_aliquota_pct, cnae_principal, tipo_declaracao_ir) + Alembic + UI captura console interno (~1d).
- **P2** — Classifier E4 com 5 labels novas (`pro_labore`, `lucros_distribuidos`, `das_simples`, `folha_pj`, `iss`) + integração [[ADR-157]] E1.6 para renda tributável PF (~2d).
- **P3** — `pipeline/domain/services/tributario/cascata_calculator.py` (rules-as-code [[ADR-143]]) com 4 regimes V1 (Simples-III/V, Presumido, MEI) + fator-R + base PGBL correta + break-even + 5 decision triggers (~2d).
- **P4** — `pipeline_adapter` propaga `bundle["tributario"]`; narrator reescrito ramifica por regime; **remove "Lucro presumido (32%)" do template** (~1d).
- **P5** — `<CascataFiscalCard/>` UI com decomposição em camadas + co-design `product-designer` (~2d).
- **P6** — Cutover + telemetria + flip [[ADR-236]] para `Decidido (Sprint A16)` + FAQ produto (~1d).

Detalhe completo em [[PLAN-tributario-pj]].

## Lanes

- [[TRACK-a16-adr235-nu-proprietario-flip]] (`consumed`) — L1: flip nu_proprietario (1 PR). Mergeado em [apps#388](https://github.com/davidrobert/mathoms/pull/388) (2026-05-21).
- [[TRACK-a16-adr236-tributario-pj-cascata]] (`ready`) — L2: tributário PJ cascata fiscal (6 PRs sequenciais).

## Pré-requisitos

- [[ADR-235]] mergeada em `main` ([apps#382](https://github.com/davidrobert/mathoms/pull/382) — auto-merge habilitado).
- [[ADR-236]] mergeada em `main` (PR de Proposto + plano canônico).

## Bloqueios externos

Nenhum. L1 é extensão do enum + propagação cross-stack. L2 modela domínio tributário expandido — não introduz nova dependência externa nem altera infra.

## Não-objetivos

### Para L1 (ADR-235 nu_proprietario)

- `expected_extinction_year`, modelagem de cenário condicional pós-consolidação, tábua atuarial.
- `valor_mercado_consolidado` separado de `valor_brl` IRPF (cabe em FU unificado com [[ADR-227]]).
- Sub-bucket "Patrimônio ilíquido condicional" como categoria nova em [[ADR-145]].

### Para L2 (ADR-236 cascata fiscal)

- Cálculo de imposto devido específico, escolha de regime, enquadramento CNAE (linha CRC).
- Lucro Real e multi-PJ por workspace (V2).
- Reforma tributária / PEC dividendos (ADR de schema evolution quando aprovar).
- Holding patrimonial — gatilhos completos (sucessão multi-herdeiro, ITCMD por UF, PJ-aluguel formal). V1 tem 1 gatilho (T4: ≥3 imóveis alugados).
- Hot-fix paralelo (esconder/encurtar card no meio-tempo) — descartado pelo usuário em favor da solução completa.

## Follow-ups potenciais (post-A16)

### Da L1 nu_proprietario

- **FU-1 · `valor_mercado_consolidado`** estendendo `property_market_value` ([[ADR-227]]).
- **FU-2 · Aviso de seguro de vida** no parecer E6 (heurística condicional).
- **FU-3 · `expected_extinction_year`** — só se demanda materializar (≥10 workspaces solicitando captura).

### Da L2 tributário PJ

- **Lucro Real + multi-PJ** — V2 quando ICP materializar.
- **Holding patrimonial gatilhos completos** — co-design `financial-planner` profundo.
- **Comparativo Simples vs Presumido vs MEI** no card — V2 com co-design adicional.
- **Cache `workspace_tributario_snapshot`** — se latência virar problema.
- **Renderização cascata como timeline anual** — comparar 2024 vs 2025 vs 2026 (reusa pattern de `irpf_snapshots` [[ADR-229]]).
