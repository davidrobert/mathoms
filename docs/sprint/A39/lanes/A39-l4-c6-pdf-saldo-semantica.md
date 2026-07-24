---
id: A39.l4
type: lane
title: "C6 Bank PDF: corrigir semântica de saldo_inicial (ajuste do 1º dia) e então declarar verificabilidade"
sprint: A39
status: shipped
ship_date: "2026-07-23"
ship_pr: 1041
priority: P1
branch_slug: a39-l4-c6-pdf-saldo-semantica
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l2]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/dados
---

# A39.l4 — `c6-pdf-saldo-semantica` (achado PC-03)

## Problema (certificação 2026-07-23)

`parse_c6bank` (PDF) grava conservação quebrada em vários extratos C6 BRL. A
verificação adversarial separou dois casos:

- **Cosmético (não é perda):** #786e (gap −R$17k) e #c5c6 (+R$7k) — a abertura
  que reconciliaria (17.000 / 0) **está no texto bruto** e
  `abertura_documentada + Σtx == fechamento_documentado` **fecha exatamente** →
  transações completas, `saldo_final` (consumido pelo patrimônio) correto. Só o
  `saldo_inicial` interno defaultou. Causa (data-engineer): `saldo_inicial =
  saldo_values[0][1]` (`c6bank.py:598`) é **âncora bruta sem ajuste do 1º dia**
  (subtrair o Σ do 1º dia). Flipar o flag agora **false-escala** arquivos bons.
- **Defeito real:** #2570 (gap −R$1.000) — o valor reconciliador (1.188,75)
  **não está** no doc → transação derrubada OU dígito de saldo perdido.

## Escopo

- Aplicar o ajuste `summarize_saldos` do 1º dia à âncora de `saldo_inicial` em
  `parse_c6bank` (`c6bank.py:598`), espelhando a semântica **verificada** do
  Itaú 2026 e do C6 CSV ([[A39.l2]]).
- Validar que arquivos C6 PDF limpos fecham conservação em cents **antes** de
  flipar `conservacao_verificavel=True` (senão false-escala).
- Após o flip: #786e/#c5c6 passam (cosméticos resolvidos); #2570 **escala** se
  a transação estiver genuinamente ausente (KR-A) — disambiguar via cadeia de
  continuidade (`saldo_final[N] == saldo_inicial[N+1]`, `SaldoContinuityConfig`).
- Referencia [[ADR-342]] (mecanismo); sem ADR nova.

## Critério de aceite

- Golden: arquivo C6 PDF limpo fecha em cents com o ajuste do 1º dia; #786e/#c5c6
  fecham (cosméticos); flip só após fechamento provado.
- #2570 → `completo` (se disambiguado como saldo) ou `escalado-honesto` (se tx
  ausente) — nunca silencioso (KR-A).
- KR-E: extratos C6 PDF hoje corretos (o layout Global l15) inalterados.

## Risco

Médio — toca o parser C6 PDF (também dono do layout Global l15). Mitigação:
validar fechamento antes do flip; fixture dos layouts BRL/Global intocada.
`depends_on` [[A39.l2]] (hotspot `c6bank.py` — sequenciar).
