---
id: CHG-2026-05-28-ADR-271-INVEST-DEDUP-SHIPPED
type: changelog-entry
date: "2026-05-28"
sprint: A20
adrs: ["[[ADR-271]]"]
prs: [501]
commits: ["c7c60bdd"]
breaking: false
summary: |
  feat(adr-271): dedup de investimentos cross-IRPF (cross-year + cross-declarante)
  entregue em 1 PR (#501, squash c7c60bdd, CI verde). ADR-271 flippada
  Proposto → Decidido (Sprint A20). Resolve inflação de patrimônio líquido por
  investimento duplicado ao subir IRPFs de anos sucessivos e/ou de cônjuges.
tags:
  - type/changelog-entry
  - sprint/a20
  - status/shipped
  - status/decidido
  - area/pipeline
  - area/methodology
  - methodology/auvp
---

# feat(adr-271): dedup de investimentos cross-IRPF shipped

## Sumário

[[ADR-271]] entregue em 1 PR squash-mergeado em `main` (CI verde, "All checks green" + Backend tests):

- [#501](https://github.com/davidrobert/mathoms/pull/501) (`c7c60bdd`) — helper `pipeline/domain/services/investimentos_dedup.py` (chave exata, 2 eixos) + aplicação nas 2 funções de `e15_consolidate.py` (`consolidate` + `consolidate_from_itens`) + defesa idempotente em `e4_categorize.py` + schema bump em `config/schemas/baseline_patrimonial.schema.json` + 17 testes.

## Problema

Ao subir IRPFs de **anos diferentes** (ex.: 2023 + 2024) e/ou de **cônjuges** (titular + cônjuge), investimentos apareciam **duplicados** em `baseline["investimentos_consolidados"]`, inflando o patrimônio líquido e deslocando a alocação-alvo AUVP (denominador inflado → aportes recomendados errados).

## Decisão (resumo)

Dedup determinístico no estágio E1.5c (consolidador) + defesa em profundidade em E4. **Chave exata** `(tipo_norm, instituicao_norm, descricao_norm)`, dois eixos:

- **Cross-year (mesmo dono):** une `valores_31_12` (não soma); valor corrente = ano mais recente (investimento é marcado a mercado, diverge de imóveis ADR-246 onde "maior valor vence"). Conflito mesmo-ano → maior vence + warning `valor_divergente_ano`.
- **Cross-declarante (donos distintos):** funde só se valor 31/12 idêntico ao centavo (conta conjunta) → `proprietario="casal"`, `proprietarios=[...]`. Divergente → não funde + warning `possivel_duplicata`.

Calibração conservadora: falso-positivo (some patrimônio, silencioso) é pior que falso-negativo (infla PL, visível) → na dúvida, não funde.

## Bug colateral corrigido

`consolidate_from_itens` carimbava `valores_31_12` com `ano_referencia` global; trocado por `item.get("ano")` por item — sem isso o eixo cross-year colapsava em falso conflito mesmo-ano.

## ADR

[[ADR-271]] flippada `Proposto → Decidido (Sprint A20)`. **Follow-ups documentados (não feitos):** PR2 = pass fuzzy gated por instituição idêntica (reusa `canonical_fuzzy_match`); PR3 = extração de CNPJ/conta no E1.5 como chave estável a rename de descrição.
