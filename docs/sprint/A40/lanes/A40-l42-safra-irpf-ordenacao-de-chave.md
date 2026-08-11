---
id: A40.l42
type: lane
title: "Safra IRPF errada por ordenação de string: '31_12_2024' vence '2025' em max() lexicográfico"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l42-safra-irpf-ordenacao-de-chave
adrs:
  - "[[ADR-271]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
---

# A40.l42 — `safra-irpf-ordenacao-de-chave`

> **Aberta em 2026-08-11.** Root-cause candidato apontado pelo co-design
> `data-engineer`; é **insumo** da [[A40.l41]] — arbitrar frescor sobre safra
> errada troca um número errado por outro.

## Problema

`tabela_classes`/`top_ativos` do E5 usam valores de 31/12/**2024** (Itaú RDB
R$ 151.602,49; PicPay R$ 46.684,62) quando o IRPF 2026 declara 31/12/**2025**
(R$ 290.000,00; R$ 52.303,69). Candidato a root-cause: `_latest_value` em
[investimentos_dedup.py:199-204](../../../../pipeline/domain/services/investimentos_dedup.py)
faz `max(vals.keys())` **lexicográfico** sobre chaves de formato misto — com
`{"2025", "31_12_2024"}`, `"31_12_2024"` vence porque `"3" > "2"`.

## Entregável

PR único, precedido de prova:

1. **Prova por mutação plausível**: teste com chaves `{"2025", "31_12_2024"}`
   demonstrando que a safra escolhida muda quando a ordenação é corrigida —
   alimentado pelo shape real do produtor (`valores_31_12` de
   `investimentos_consolidados`), não fixture inventada.
2. Fix da ordenação (normalizar chave-ano antes de comparar). **Vetado**
   (`data-engineer`): mexer em `_identity_key`/`_merge_cross_year` para
   compensar bug de ordenação — a compensação fica.
3. Se a investigação provar ambiguidade genuína de política (IRPF declara
   dois anos e o consumidor escolhe mal), vira **emenda à [[ADR-271]]**, não
   ADR nova.

## Critério de aceite

- Teste de mutação passa a falhar no código antigo e verde no novo.
- No dogfood, `top_ativos` reflete a safra 31/12/2025 (Itaú RDB
  R$ 290.000,00; PicPay R$ 52.303,69); manifesto de rebaseline justificado.
- Nenhuma mudança em `_identity_key`/`_merge_cross_year`.
