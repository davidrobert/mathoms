---
id: A40.l58
type: lane
title: "schema_validation warn → strict: o PR5 que a l5 declarou como outra lane"
sprint: A40
plan: PLAN-report-trust
status: blocked
priority: P2
branch_slug: a40-l58-flip-do-schema-para-strict
owner: sre-devops
depends_on:
  - "[[A40.l5]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p2
  - area/pipeline
---

# A40.l58 — `flip-do-schema-para-strict`

> **`blocked` por [[A40.l5]]** — o flip exige *"o drift medido em mãos"*
> (§Forma da l5), e o drift só existe depois que os PRs 2–4 da l5 tiparem os
> blocos restantes do `e5_analysis.schema.json`. Flipar antes é converter
> lacuna de tipagem em run de cliente abortado.
>
> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Origem: [[A40.l5]] §Forma, PR5 — *"Proposta `warn → strict` …
> **Outra lane.** ADR própria + gatilho `sre-devops` (blast radius = run de
> cliente)"*. Esta lane materializa a rota que a l5 prometeu; "outra lane" que
> não existe é rota que aponta para o nada.

## Problema

A validação de schema do pipeline roda em modo `warn` em produção
(`pipeline.json → schema_validation.mode`, override
`MATHOMS_PIPELINE_SCHEMA_MODE`): payload que viola o contrato **loga e passa**.
O gate real de schema é o golden de execução — que a l5 descobriu ter ficado
**anos sem validar nada** (o `pipeline.json` de teste era `{}`, `enabled`
defaultava `False`). A l5 ligou a validação `strict` **fixa** na suíte; falta o
flip em produção, onde o blast radius é run de cliente.

## Escopo

1. **ADR `Proposto` antes do PR** (exigência registrada na l5) — decide o modo
   de rollout: strict direto, ou observação → strict com kill-switch.
2. Medição do drift real: com os PRs da l5 mergeados, quantos payloads de
   produção violariam `strict` hoje? (Zero é hipótese, não premissa.)
3. Flip com kill-switch documentado (`MATHOMS_PIPELINE_SCHEMA_MODE=warn` como
   rollback de 1 env var, sem deploy).
4. Re-adoção do "flip órfão" que a l5 registrou: a suíte valida com `strict`
   fixo, não dependente de CI lembrar de setar env.

## Critério de aceite

- ADR mergeada antes do PR de flip, com a decisão de rollout e o rollback
  declarados.
- O drift pré-flip está **medido e citado** na ADR (não "acreditamos que zero").
- Kill-switch provado: com a env de rollback setada, payload inválido volta a
  logar-e-passar — teste, não prosa.
- Runbook de incidente: o que fazer quando um run de cliente aborta por schema
  (gatilho `sre-devops`).
