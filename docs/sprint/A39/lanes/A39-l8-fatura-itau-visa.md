---
id: A39.l8
type: lane
title: "Fatura Itaú Visa: TypeRule determinístico + parser (via words) + checksum ADR-343 (cobre 3 não-coberto)"
sprint: A39
status: shipped
ship_date: "2026-07-23"
ship_pr: 1047
priority: P1
branch_slug: a39-l8-fatura-itau-visa
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l3]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/dados
---

# A39.l8 — `fatura-itau-visa` (achado PC-07 · adota [[A38.l9]])

## Problema (certificação 2026-07-23)

3 dos 6 `não-coberto` são **fatura Itaú Visa** (`itau_fatura .pdf`): conf 0.0 na
via regex → 100% E2-llm (custo/latência premium; precisão não garantida). É
**lacuna de TypeRule (regex), não ambiguidade** (prompt-engineer: pagar LLM por
tipo recorrente e de formato estável viola o caminho A da ADR-081 — regex
primário, LLM fallback). Agravante conhecido ([[A38.l9]]): 1 sub-layout tem texto
**sem espaços** (`extract_text` cru inutilizável; `extract_words` preserva).

Esta lane **adota e fecha [[A38.l9]]** (cauda P2 do A38, reconciliada em A39 para
evitar merge-hell) e a fatia de classificação de [[A38.l10]].

## Escopo

- **TypeRule determinístico** para `itau_fatura` (regex sobre conteúdo, anchor
  `itau_fatura(?!paoacucar)`) em `content_classifier`/registry → conf ≥ 0.8 sem
  LLM.
- **Parser `parse_itau_fatura`** (`scripts/e2/banks/itau.py`) via `extract_words()`
  (robusto ao sub-layout sem espaços): transações nacionais/internacionais,
  `total_fatura`, `vencimento`, pagamento anterior.
- **Checksum de fechamento via ADR-343** ([[A39.l3]]) — identidade limpa
  `saldo_anterior + Σcompras − Σpagamentos + encargos == total_fatura`, **não**
  Σtx×total (upgrade sobre o cross-check original do [[A38.l9]]).
- Se o sub-layout sem espaços for inviável deterministicamente: aceite
  alternativo explícito — permanece E2-llm **amarrado ao checksum ADR-343**
  (LLM extrai **e** fecha, senão `needs_review`). Nunca LLM cru sem checksum.

## Critério de aceite

- Harness [[A39.l1]]: as 3 faturas Itaú saem de `não-coberto` para `completo`
  (checksum ADR-343 passa) ou `escalado-honesto` (KR-A) — pelo caminho
  determinístico (ou fallback documentado + checksum).
- TypeRule: conf ≥ 0.8 sem LLM; fixtures sintéticas dos 2 sub-layouts (com/sem
  espaços) em CI; zero regressão em `faturapaoacucar` (KR-E).
- `depends_on` [[A39.l3]] (checksum de fatura). Hotspot `type_classifier.py` /
  `content_classifier.py` — coordenar com [[A39.l9]]/[[A39.l11]].

## Risco

Médio — layout de fatura é o mais denso. Mitigação: fixtures dos 2 sub-layouts +
checksum obrigatório. Supersede [[A38.l9]] (marcar cancelled no A38 ao aterrissar).
