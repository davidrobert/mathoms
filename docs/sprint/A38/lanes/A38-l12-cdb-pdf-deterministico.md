---
id: A38.l12
type: lane
title: "CDB em PDF (extrato mensal Itaú + detalhes Santander): 100% E2-llm sem parser determinístico"
sprint: A38
status: open
priority: P1
branch_slug: a38-l12-cdb-pdf-deterministico
adrs: []
depends_on: ["[[A38.l1]]", "[[A38.l3]]", "[[A38.l5]]"]
tags:
  - type/lane
  - sprint/a38
  - status/open
  - priority/p1
  - area/pipeline
  - area/dados
---

# A38.l12 — `cdb-pdf-deterministico` (corpus de investimentos 2026-07-22)

## Problema (certificação empírica 2026-07-22, corpus de investimentos)

Extratos mensais de CDB do Itaú (DI e Metas, PDF: `SALDO ANTERIOR`/`SALDO
FINAL` + movimentos + nº de operação) e o "Detalhes do Investimento" do
Santander (PDF: total por produto CDB + operações, com "Você possui N
contratos") **classificam certo** (`cdbdetalhes` conf 1.0) mas caem 100% no
E2-llm — os anchors de rota só aceitam `.xls`/`.xlsx`. Consequências: no
**Free tier** (determinístico, sem LLM) esses documentos produzem **zero
patrimônio** — gap silencioso de classe North-Star (decisão do painel/pm;
dissenso registrado do financial-planner, que os via como P2 por não serem
silent-wrong no tier premium); no premium, custo/latência de LLM e o checksum
natural `Σ contratos = total` desperdiçado.

## Escopo (decisões do painel encodadas)

- `parse_itau_cdb_pdf` + `parse_santander_cdb_pdf` em
  `scripts/e2/banks/{itau,santander}.py`, espelhando **verbatim** o dict dos
  parsers xls/xlsx existentes — **`tipo="cdbresumo"`, nunca `cdbdetalhes`**:
  o E4 seleciona artefato por `_INVESTMENT_POSITION_TYPES` e `cdbdetalhes`
  não está lá (emitir errado = artefato passa no schema, passa no E3 e
  **some no E4 em silêncio**). Posições fluem pela key `posicoes`.
- Anchors de rota **format-specific** (`^itau_cdbdetalhes_.*\.pdf$`,
  `^itau_cdbresumo_.*\.pdf$`, idem santander) — CDB não tem subtipo de
  moeda; anchor bare não se aplica (decisão do painel/data-engineer).
- **Checksums como emenda à [[ADR-342]]** (contrato único anti-silêncio,
  co-design com a [[A38.l3]] — o gate da l3 cobre transações, não posições):
  1. `Σ posicoes.valor == total declarado do produto` (cents, tolerância
     zero — o aviso atual do consolidador usa R$ 1, que viola o sprint);
  2. contagem declarada: `len(posicoes) == N` de "Você possui N contratos";
  3. predicado CDB: `saldo_final` presente, senão escala (conservação de
     transação é tautológica aqui — saldo derivado).
  Falha ⇒ `requires_llm_fallback` (E2-llm one-shot), rollout WARN→HARD por
  banco, reasons novos (`extract.investment_sum_mismatch` /
  `extract.investment_count_mismatch`).
- **Rendimento do período = passthrough** no artefato, sem ligação a KPI
  (decisão do painel/financial: é accrual, nunca receita de fluxo; o lar
  natural — TRS — já tem fonte canônica IRPF; precedência é V2).
- `$defs/posicao_investimento` mínimo no `e2_extract.schema.json` (`nome`,
  `tipo`, `valor_atual: [number,null]`, `quantidade: [number,null]`) —
  fecha o buraco de posição malformada contribuindo 0 em silêncio.
- Fixtures sintéticas PII-zero: PDF via reportlab (builders per-banco em
  `tests/fixtures/pdf/`); **não** reusar o builder xlwt (formato errado).

## Critério de aceite

- Teste de rota: `itau_cdbdetalhes_*.pdf`/`itau_cdbresumo_*.pdf` (e
  santander) roteiam para o parser novo; artefato tem `tipo=="cdbresumo"` e
  a posição **chega em `total_por_membro` do E4** (teste de integração).
- Checksums verdes nas fixtures + caso negativo (row-drop) que **escala**.
- Corpus local (harness [[A38.l1]]): os 3 CDBs PDF do corpus de
  investimentos extraem 100% dos contratos com checksum verde, sem LLM.
- Regressão zero: fixtures CDB xls/xlsx existentes idênticas; **Rico
  (extrato conta corretora, 15/15) pinado no baseline como controle verde**
  — esta lane e a [[A38.l5]] mexem em classificação/rota e não podem
  quebrá-lo (KR-E).
- Relatório mascarado do harness no corpo do PR.

## Risco

Baixo-médio: parsers aditivos conforme padrão E2 (sem ADR própria — a
emenda à [[ADR-342]] é do contrato de checksum). Gotcha nº1 documentado:
`tipo="cdbresumo"`. `depends_on` [[A38.l5]] (required forte garante que só
CDB genuíno roteia aqui) e [[A38.l3]] (contrato de escalação).
