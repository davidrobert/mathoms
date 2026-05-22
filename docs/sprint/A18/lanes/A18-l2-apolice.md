---
id: A18.l2
type: lane
title: "Comprovantes de Bem — L2 Apólice de seguro polimórfica (combinada V1, vida/saúde/PJ V2)"
sprint: A18
status: shipped
ship_prs:
  - "https://github.com/davidrobert/mathoms/pull/419"
  - "https://github.com/davidrobert/mathoms/pull/420"
  - "https://github.com/davidrobert/mathoms/pull/422"
  - "https://github.com/davidrobert/mathoms/pull/424"
  - "https://github.com/davidrobert/mathoms/pull/425"
ship_date: "2026-05-22"
priority: P1
branch_slug: a18-l2-apolice
depends_on:
  - "[[A18.l1]]"
parallel_with:
  - "[[A18.l3]]"
adrs:
  - "[[ADR-239]]"
prompt: "[[TRACK-a18-l2-apolice-seguro]]"
tags:
  - type/lane
  - sprint/a18
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/persistence
  - area/methodology
---

# A18.L2 — Apólice de seguro polimórfica

> **Onda 2 de 3** em [[MOC-sprint-a18]]. Lane mais complexa: schema polimórfico com **3 tipos de bem segurado** (veículo, imóvel, pessoa-V2-placeholder) + **5 tipos de cobertura** (material, RCFV, vida-V2, saúde-V2, acidentes-V2) — tudo Discriminated Union.

## Objetivo

Modelar `tipo_comprovante="apolice"` ponta a ponta. Schema antecipa V2 (vida/saúde/PJ) já em V1 para evitar migration breaking. **Apólice combinada Porto Seguro (Toro + residência) é caso V1 obrigatório** — multi-bem em 1 PDF dispara cascata LLM Haiku→Sonnet.

## PDFs do batch destravados

- Apólice Tokio Marine Moto (NMAX STH2C88) — auto simples
- Apólice Porto Moto (NMAX DAV0351) — auto simples
- **Apólice Porto Proteção Combinada** (Toro GDK6A27 + residência R Tasso da Silveira 61) — multi-bem ⭐

## Critério de aceite

- 3 apólices do batch classificam como `tipo_comprovante="apolice"` com `confidence ≥ 0.7`.
- Apólice combinada Porto renderiza com `len(bens_segurados) == 2` (auto + imóvel).
- Cascata LLM Haiku→Sonnet dispara quando: `len(bens_segurados) > 1` OU confidence < 0.7 OU detecção textual "combinada"/"residencial+auto".
- `congenere_anterior` populado quando apólice declara renovação inter-seguradora (Tokio doc cita PORTO 8891272 classe bônus 2).
- `pagador_cpf ≠ segurado_cpf` corretamente capturado (Tokio paga SONIA cônjuge, segurado é David).
- FK opcional `veiculo_id` resolvida via reconciliação assíncrona — apólice Tokio NMAX STH2C88 vincula ao Vehicle correspondente quando CRLV L1 estiver presente.
- Histórico de apólices imutável temporal — múltiplas rows em `pipeline_artifacts` (uma por apólice), query temporal por vigência.
- Cobertura `lmi_modo: Literal["valor_fixo", "fipe_percentual", "primeiro_risco_absoluto"]` discriminada — não union de tipos no valor.
- Catalog `institutions` ganha `insurance_carrier` (porto, tokiomarine) e `insurance_broker` (futuro — V1 mantém corretor inline em `CorretorRef`).
- Goldens sintéticos: 3 PDFs do owner anonimizados + 3 sintéticos mock (vida, saúde, acidentes — placeholder V2).
- Schema cobre placeholder `sinistro_indenizacao_recebida_brl` para evitar migration breaking V2 ([[ADR-238]] integração futura).

## Coordenação

L1 (CRLV) precisa estar em `main` antes desta lane começar — valida o padrão arquitetural (classifier + stage + tabela canônica + reconciliação assíncrona) que L2 reusa. Paralela a L3 (FIPE) — não compete por arquivos.

## Detalhe operacional

[[TRACK-a18-l2-apolice-seguro]].
