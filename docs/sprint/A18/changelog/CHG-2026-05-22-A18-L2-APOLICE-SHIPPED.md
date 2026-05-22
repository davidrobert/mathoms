---
id: CHG-2026-05-22-A18-L2-APOLICE-SHIPPED
type: changelog-entry
date: "2026-05-22"
sprint: A18
lane: "[[A18.l2]]"
adrs: ["[[ADR-239]]"]
summary: |
  feat(adr-239): A18 L2 (apólice polimórfica auto/residencial/combinada V1
  + V2 placeholder vida/saúde/acidentes) entregue em 5 PRs sequenciais
  (#419, #420, #422, #424, #425). ADR-239 ganha seção `## Entrega — L2`.
  Discriminated Union 2 níveis (bens_segurados + coberturas) + cascata
  LLM Haiku→Sonnet + match estrito veículo + token-set inclusivo imóvel
  validados.
tags:
  - type/changelog-entry
  - sprint/a18
  - status/shipped
  - area/pipeline
  - area/persistence
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
---

# feat(adr-239): A18 L2 apólice polimórfica shipped

## Sumário

Lane [[A18.l2]] entregue em 5 PRs squash-mergeados sequencialmente em `main` (todos com CI verde), validando padrão arquitetural completo para apólice de seguro polimórfica:

- **P1** [#419](https://github.com/davidrobert/mathoms/pull/419) — `ApolicePayload` Pydantic V2 strict com Discriminated Union 2 níveis: `bens_segurados[]` (veiculo|imovel|pessoa-V2) e `<bem>.coberturas[]` (material|rcfv|vida-V2|saude-V2|acidentes-V2). LMI via `lmi_modo` discriminator 3 modos (valor_fixo, fipe_percentual, primeiro_risco_absoluto). PROMPT_VERSION="apolice-v1.0.0". 3 goldens sintéticos LGPD-safe.
- **P2** [#420](https://github.com/davidrobert/mathoms/pull/420) — `TypeRule apolice_seguro` content-first + migration `adr239apolice` seed top-5 seguradoras (porto, tokiomarine, bradesco_seguros, itau_seguros, zurich) categoria `insurance`. `_COMPROVANTE_BEM_PREFIXES` ganha "apolice_seguro" / "apolice".
- **P3** [#422](https://github.com/davidrobert/mathoms/pull/422) — stage dispatch `tipo_comprovante=apolice` + cascata LLM Haiku→Sonnet (gate triplo D6: multi-bem OU confidence<0.7 OU strings combinada/residencial+auto). Cache key inclui modelo. CPFs mascarados Python pós-LLM (LGPD ADR-231 D8). Artifact key `apolice_<numero>_<vigencia_ano>` (D7 imutável temporal).
- **P4** [#424](https://github.com/davidrobert/mathoms/pull/424) — função pura `reconcile_apolice_bens` (match estrito veículo por placa, token-set inclusivo imóvel por endereço canônico) + runner backend `apolice_reconciliation_runner.py` + plumbing em `_persist_processed` apolice path. 4 outcomes tipados.
- **P5** [#425](https://github.com/davidrobert/mathoms/pull/425) — 3 goldens V2 placeholder (vida, saúde, acidentes) validando schema antecipa V2 sem migration breaking + flip ADR-239 ganha seção `## Entrega — L2` + lane `A18.l2 → shipped` + este changelog.

## ADR

[[ADR-239]] ganha seção `## Entrega — L2 (Apólice polimórfica)` com 5 PRs + padrão arquitetural revalidado (Discriminated Union 2 níveis, LMI discriminator, cascata LLM com gate explícito, cache key per-model, match imóvel via token-set não fuzzy, pessoa V2 placeholder sem expor pool).

## Padrão arquitetural revalidado (replicar em L3 FIPE refresh)

- **Discriminated Union 2 níveis** antecipa V2 (vida/saúde/acidentes) já em V1 — UI consome quando V2 entrar (A19 S_PROTECAO ou futuro).
- **LMI discriminator** (não union de tipo no valor) — consumer não precisa `isinstance` em todo lugar.
- **Cascata LLM Haiku→Sonnet** com gate explícito — cost-optimized; Sonnet só quando combinada multi-bem ou confidence baixo.
- **Cache key inclui modelo** — re-run com mesmo modelo serve do cache idempotente (ADR-144).
- **Match imóvel via token-set inclusivo** — preserva rigor sem floats arbitrários (não fuzzy ratio).
- **Pessoa V2 placeholder** em reconciliação retorna `no_candidate` sem expor pool `family_members` (LGPD).

## Próximo

- **A18 L3** — FIPE refresh assíncrono via BrasilAPI (paralelo a L2, agora destravado). Destrava disclaimer S4 "Valor atualizado via FIPE".
- **A19** — card S_PROTECAO (4º pilar AUVP) — **agora desbloqueado** (precisava de A18 L1 + L2 para identidade canônica de bens + apólices ativas).
