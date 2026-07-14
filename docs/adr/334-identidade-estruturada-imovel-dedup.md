---
id: ADR-334
type: adr
title: "Identidade estruturada de imóvel + dedup (gated por auditoria empírica)"
status: Proposto
date: "2026-07-14"
relates_to:
  - "[[ADR-246]]"
  - "[[ADR-271]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-334 — Identidade estruturada de imóvel + dedup

> Cluster **G** (P1) da re-review dogfood 2026-07-13 · [[PLAN-dogfood-report-fix]].
> **BLOQUEADA** — gated por auditoria empírica (ver §Gate). Reserva de ID.

## Contexto

`real_estate.excluded_properties` mostra 1 matrícula 4× ("Classificação pendente") e 2
matrículas simultaneamente em `imoveis` (ativo) **e** em `excluded`. Narrativa diz "6
imóveis", tabela tem 4 (1 com valor 0). Raiz: identidade de imóvel só na prosa de
`descricao`, sem chave estruturada.

## Decisão

Proposta: identidade estruturada (matrícula normalizada + fallback endereço
normalizado) + dedup antes de render + invariante "um imóvel nunca em ativo E excluído".
Relaciona [[ADR-246]] (dedup co-declarado) e [[ADR-271]] (dedup investimentos).

## Gate (bloqueia esta ADR)

A verificação adversarial refutou a premissa: `_extract_matricula` depende de literal
"matrícula"+dígitos em `descricao`, e o fantasma provavelmente **não casa** (o resolver
faz early-return em `endereco_canonical is None`). **Antes de fixar o approach**, medir a
taxa real de extração nas 11 rows vivas de `property_identity` do dogfood (cópia do DB) e
registrar o número aqui como evidência — nunca "assumir 100%". `codigo_rfb` é invariante
imutável (não pode sofrer upgrade in-place).

## Consequências

Bump: migration Alembic (coluna nova) como head único. Não toca as 4 superfícies de
colisão (Parecer/Score/Narrativa/Schema).
