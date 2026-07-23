---
id: A39.l9
type: lane
title: "Posição de renda variável: TypeRule + parser + identidade ticker+proprietário + null-não-soma (cobre 2 não-coberto)"
sprint: A39
status: planned
priority: P1
branch_slug: a39-l9-posicao-renda-variavel
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
  - priority/p1
  - area/pipeline
  - area/dados
---

# A39.l9 — `posicao-renda-variavel` (achado PC-07 · adota [[A38.l13]])

## Problema (certificação 2026-07-23)

2 dos 6 `não-coberto` são **posição de investimento** (`itau_investimentosposicao
.pdf` custódia + `rico_investimentosposicao .xlsx` carteira): conf 0.0 (TypeRule
`investimentosposicao` não casa) e a XLSX sai com **instituição None**. Perder
posição corrompe **patrimônio** (financial-planner: ausência silenciosa > presença
não-verificada → **P1**, não P2). Dupla contagem latente: mesmos papéis+qtd em
2 fontes; o consolidador soma `null→0` (custódia sem marcação **deflaciona** sem
sinal).

Esta lane **adota e fecha [[A38.l13]]** (cauda P2 do A38, reconciliada em A39).

## Escopo

Ordem interna obrigatória (herdada de [[A38.l13]]):

- **TypeRules + instituição** (hotspot `type_classifier.py`): âncoras p/ "Posição
  Acionária" e carteira consolidada; **instituição vazia proibida** (cai em key
  órfã no consolidador).
- **ADR `Proposto` nova ANTES do PR de impl** (eixo de identidade novo, análogo a
  [[ADR-271]] mas eixo próprio): chave **`ticker_norm + proprietário`**;
  resolução tabelada (1 valorada + qty-only → colapsa; 2 valoradas iguais →
  `needs_review`; qtd diferente → nunca funde); calibração "não funde → escala".
- **`null-não-soma`** no `InvestmentsConsolidator`: valor `None` conta em
  `n_posicoes`, **fora** de `total_por_membro`, flag `posicao_sem_marcacao`.
- **Parsers** + checksums: carteira XLSX (`Σclasses == total investido`, cents);
  posição acionária (`n_papéis`, checksum de contagem) — falha → escala (emenda
  [[ADR-342]] da l12).
- Proventos (JCP/dividendo) → categoria própria, fora da base de poupança.

## Critério de aceite

- Harness [[A39.l1]]: os 2 docs saem de `não-coberto` (conf 0.0) para conf ≥ 0.8
  + tipo correto; instituição resolvida (nunca vazia).
- Golden do consolidador: null conta em `n_posicoes` e NÃO soma; custódia
  qty-only + carteira valorada → total = só a valorada (patrimônio não dobra);
  2 valoradas mesmo ticker+qtd → `needs_review`.
- ADR nova `Decidido (A39.l9)` no merge; auto-resolução registrada como
  follow-up. KR-E: corpus de classification existente inalterado.

## Risco

Médio-alto (contrato E2→E4 + invariante de domínio novo). Mitigação: ordem
interna obrigatória, ADR-gated, calibração "não funde → escala". **Reservar ID da
ADR cedo.** Supersede [[A38.l13]] (marcar cancelled no A38 ao aterrissar).
