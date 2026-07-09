---
id: TRACK-a18-l2-apolice-seguro
type: track
title: "Track A18 L2 — Apólice polimórfica: Discriminated Union bens+coberturas + cascata Haiku→Sonnet + combinada V1"
lane: "[[A18.l2]]"
sprint: A18
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: data-engineer
tags:
  - type/track
  - sprint/a18
  - status/ready
  - area/pipeline
  - area/persistence
  - area/methodology
---

# Track A18 L2 — Apólice de seguro polimórfica

> **Lane:** [[A18.l2]] · **ADR canônica:** [[ADR-239]] §D2 + §D6 + §D7 · **Pré-requisito:** [[A18.l1]] (CRLV) mergeada em `main` — valida padrão · **Paralela com:** [[A18.l3]] (FIPE)
> · **Branch prefix:** `agent/a18-l2-apolice/*` · **Tamanho estimado:** ~6d eng em 5 PRs

## Briefing

L1 estabeleceu padrão arquitetural completo (stage `extract_comprovantes_bens`, tabela canônica `vehicles`, classifier content-first, parser LLM Haiku, reconciliação assíncrona). **Esta lane estende o padrão** para `tipo_comprovante="apolice"` com schema polimórfico (Discriminated Union em `bens_segurados[]` E em `coberturas[]`).

**Caso V1 obrigatório:** apólice combinada Porto Seguro (carro ABC1234 + residência Rua Exemplo, 100) — multi-bem em 1 PDF. Cascata LLM Haiku→Sonnet dispara quando combinada detectada.

## Decisões já fechadas (não reabrir)

- **Discriminated Union** em `bens_segurados[]` (veículo/imóvel/pessoa-V2) E em `coberturas[]` (material/RCFV/vida-V2/saúde-V2/acidentes-V2) — antecipa V2 sem migration breaking ([[ADR-239]] D2 + D8 Risco 2).
- **LMI** via `lmi_modo: Literal["valor_fixo", "fipe_percentual", "primeiro_risco_absoluto"]` + valores separados — não union de tipos no valor ([[ADR-239]] D2 tweak).
- **FK opcional** `veiculo_id`/`imovel_id`/`family_member_id` + reconciliação assíncrona ([[ADR-239]] D3).
- **Cascata LLM Haiku→Sonnet** com gate explícito ([[ADR-239]] D6): combinada OU confidence<0.7 OU strings detectadas.
- **Histórico imutável temporal** — múltiplas rows em `pipeline_artifacts` por apólice, query temporal por vigência. Renovação = apólice nova ([[ADR-239]] D7).
- **`pagador_cpf ≠ segurado_cpf`** capturado, FK opcional `family_members` ambos ([[ADR-127]]).
- **`congenere_anterior`** no payload preserva lineage de bônus (não FK porque pré-Mathoms).
- **`sinistro_indenizacao_recebida_brl: Decimal | None`** placeholder V1 para evitar migration breaking V2 ([[ADR-239]] D8 Risco 1, integração futura [[ADR-238]]).
- **`CorretorRef.cpf_or_cnpj`** aceita PJ (CNPJ majoritário) e PF (CPF + SUSEP) com discriminator.
- **Catalog** `institutions.category` ganha `insurance_carrier` (porto, tokiomarine); corretoras ficam inline (não viram entries de catalog).

## Plano (esqueleto — refinar no pickup)

- **P1** — Schema Pydantic `ApolicePayload` polimórfico + JSON schema + Cobertura discriminated + goldens 3 cenários (Tokio simples, Porto simples, Porto combinada).
- **P2** — Classifier `apolice_seguro` (regex content: "Apólice", "SUSEP", "Cobertura", "Prêmio Líquido", CNPJs seguradoras top-5). Catalog entries `porto` (insurance_carrier), confirmar `tokiomarine` categoria. Mapping E0→`DocumentType.COMPROVANTE_BEM` + `tipo_comprovante="apolice"`.
- **P3** — Stage `extract_comprovantes_bens` ganha dispatch `tipo_comprovante="apolice"` + parser LLM Haiku→Sonnet cascade (gate em [[ADR-239]] D6) + cache de prompt por SHA.
- **P4** — Reconciliação assíncrona `apolice.bens_segurados[*].veiculo_id` via placa; `imovel_id` via endereço normalizado (precisa entity `real_estate_assets` materializada — [[ADR-216]]).
- **P5** — Goldens sintéticos: 3 owner anonimizados + 3 sintéticos mock V2 (vida, saúde, acidentes placeholder). Telemetria + changelog + flip.

## Pegadinhas (do co-design data-engineer)

- **Cobertura discriminated já em V1** — vida tem `beneficiarios[]`, saúde tem `rede_credenciada`, acidentes tem `capital_segurado_morte`. Resolva em V1, não em V2.
- **Corretor PF existente** — `cpf_or_cnpj: str` + validador (Corretor PF Exemplo do batch é PF).
- **Apólice combinada Porto = 2 seções "Valores do seu seguro"** (auto + residencial). LLM Haiku confunde em ~30% dos casos — gate de cascata é essencial.
- **`pagador_cpf` cônjuge** — o Cônjuge paga Tokio Marine; FK family_members captura.
- **Apólice expira, não é "superseded"** — modelo temporal por vigência, não chain de versões.

## Critério de aceite (lane completa)

Em [[A18.l2]] §Critério de aceite. Cobre 3 apólices do batch + apólice combinada Porto como caso V1 obrigatório.
