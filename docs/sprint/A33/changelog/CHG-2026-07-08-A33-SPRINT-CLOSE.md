---
id: CHG-2026-07-08-A33-SPRINT-CLOSE
type: changelog-entry
date: "2026-07-08"
sprint: A33
adrs: ["[[ADR-090]]", "[[ADR-135]]", "[[ADR-285]]", "[[ADR-307]]", "[[ADR-238]]"]
prs: [827, 830, 831, 833, 834, 835, 836, 844, 849, 850, 852, 853, 854, 855]
summary: |
  Sprint A33 fechada `done` — 8/8 lanes shipped em ~20h com zero ações do
  owner (KR1), executada durante a janela da A32 `current` (precedente
  A27). Entregas: Decimal no boundary E2-llm + gate `--scan-schemas`
  (#827, KR2); fechamento da A17 → `done` via financeiro PF P3-P5 com
  PTAX compra 31/12 real + validações Wise (#833/#835/#850) e
  proventos→S3 com yield líquido (#830) (KR3); nightly drift do
  extract_with_llm com 1ª execução 4/4 PASS consultável e retenção de
  artifacts com prune dry-run gate-zerado (#831/#844, KR4); OTLP
  mathoms.llm.* (#834); catálogo de instituições injetado nos prompts +
  códigos RFB em YAML anual (#836); services taxonomy em 5 PRs com
  ADR-285 flippada Decidido e 37 shims removidos (#849–#855). Bônus:
  emenda ADR-135 (PTAX compra como invariante) + correção do bootstrap
  de câmbio que devolvia cotação de 2026 para consultas históricas.
tags:
  - type/changelog-entry
  - sprint/a33
  - area/llm
  - area/pipeline
  - area/backend
---
