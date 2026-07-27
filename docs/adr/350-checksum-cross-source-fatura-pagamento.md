---
id: ADR-350
type: adr
title: "Checksum cross-source de fatura sem total impresso (fatura↔pagamento no extrato)"
status: Proposto
phase: A39
date: "2026-07-27"
relates_to:
  - "[[ADR-342]]"
  - "[[ADR-347]]"
  - "[[ADR-089]]"
  - "[[ADR-146]]"
  - "[[ADR-212]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/dados
---

# ADR-350 — Checksum cross-source de fatura sem total impresso

**Status:** Proposto (A39) · **Data:** 2026-07-27

## Contexto

A certificação parse-certify do workspace dogfood (2026-07-27) marcou as faturas
**c6 carbon CSV** (17 docs, 38–257 tx) como `fatura_checksum.status="faltando"`:
o CSV **não imprime "total a pagar"**, `parse_c6_carbon_csv` deriva
`saldo_atual = round(Σ transacoes)` (tautológico) e não emite
`total_lancamentos_conferivel`. Logo o checksum intra-artefato do [[ADR-342]]
(Σ lançamentos == subtotal declarado por escopo) é **impossível** — não há total
independente no documento. É o maior bucket de despesa discricionária ainda sem
prova de completude (viés otimista: despesa↓ → poupança/score↑).

A única evidência de completude **verificável** é **externa**: o pagamento da
fatura debitado no **extrato da conta** é uma testemunha independente do total
real. No corpus, a linha `Inclusao de Pagamento` de cada fatura casa **exato por
(data, valor_cents)** com um débito `PGTO FAT CARTAO C6` no extrato (16/17). O E2
vê o documento **isolado**; a testemunha só coexiste com a fatura no **E3**
(reconciliador), que já carrega ambos como `BankStatement` e já trata o pagamento
como transferência interna.

**Duas naturezas distintas do check (importante, não conflatar):**

- **Contrato A — integridade do par de transferência:** a linha de pagamento
  dentro da fatura ↔ o débito no extrato são o **mesmo evento** copiado em dois
  artefatos; casar os dois prova que o par transferência-interna está completo
  antes de o E3 netá-lo. É parse-integrity, barato e de alta confiança.
- **Contrato B — completude de compras:** o débito no extrato é o valor
  **realmente pago** (o "total a pagar" que o banco computou); se
  `Σ compras (+ saldo_anterior + encargos) == débito`, as compras estão completas.
  Para c6 carbon (sem `saldo_anterior`/encargos no CSV), reduz-se a
  `Σ compras == débito`. Isto **exige separar** as compras da própria linha de
  pagamento — senão a comparação é circular (`saldo_atual == Σtx == pagamento`).

## Decisão

1. O cross-check vive como **validador de domínio puro**
   `FaturaPaymentCrossChecker` em `pipeline/domain/services/`, sem I/O, injetado
   em `E3ReconcilerAdapter` com `default None` (opt-in seguro — mesmo padrão de
   `saldo_validator`/`temporal_detector`/`baseline_validator`; [[ADR-089]] ISP,
   config tipada `FaturaCrossCheckConfig`, não `StageConfig`/dict). Invocado sobre
   os statements **pré-merge** (preserva fidelidade por-arquivo).
2. **Pré-requisito bloqueante:** `parse_c6_carbon_csv` deve **isolar o escopo
   `pagamento`** só na linha `Inclusao de Pagamento` (hoje o ramo `valor<0`
   conflaciona estornos/refunds em `pagamentos`) — sem isso o Contrato B é
   circular. Escopo `pagamento` já é `_CHECKSUM_EXEMPT_SCOPES` no F6 exatamente
   porque é transferência interna reconciliada aqui; este ADR é o check que fecha
   esse balde exento **no lugar certo**.
3. Emite, por fatura, o traço `fatura_cross_checksum` com o **mesmo vocabulário**
   do [[ADR-342]]: `{status: "passou"|"mismatch"|"faltando", invoice_total_cents,
   witness_debit_cents|null, gap_cents|null, match_key, witness_source|null}`.
   `passou`=débito casa; `mismatch`=débito-pagamento-para-este-cartão fora de
   tolerância (tx perdida/extra); `faltando`=sem testemunha no corpus.
   Chave de matching: `(data, valor_cents)` exata; multiset por `(conta, data)`
   com fallback de soma same-date (N faturas pagas num débito só).
4. **Measure-then-emit** ([[ADR-347]]): PR1 mede e emite o traço + contagens
   run-level, **sem** escalar `needs_review`; política de gate = PR2 após medir a
   taxa de falso-positivo (matching cross-source é ruidoso).
5. **Não mutar o artefato E2.** O E2 `fatura_checksum` permanece a evidência
   intra-artefato ("faltando" p/ c6 carbon CSV); o E3 emite traço **paralelo**.
   A **certificação** (camada ledger-certify, pois requer a testemunha do extrato)
   compõe: `coberto = E2.status=="passou" OR E3.cross.status=="passou"`; `mismatch`
   de qualquer lado é surfaçado; `faltando` só quando ambos ausentes.
6. `parse_c6_carbon_csv` **não** ganha sinal sintético de total (seria falso-verde,
   exatamente o que o F6/[[ADR-342]] §Emenda 2026-07-27 combate).

## Alternativas rejeitadas

- **Passo E2 tardio lendo artefatos irmãos** — quebra o isolamento por-documento
  do E2 e seu read-path; o E2 não tem o extrato em escopo por design.
- **Método em `ReconciliationService`** — viola SRP/ISP; o serviço é mínimo e
  recebe só `ReconciliationConfig`; validadores são colaboradores injetados.
- **Stage novo no `FULL_ORDER`** — desproporcional; `validate_cross` (E7) roda
  sobre E5 (agregado demais, perde o débito bruto e a granularidade por-fatura).
- **Mutar o artefato E2 in-place a partir do E3** — quebra ownership de stage e
  idempotência do [[ADR-212]].
- **Sintetizar `total_lancamentos_conferivel` no parser c6** — desonesto; não há
  total impresso.

## Consequências

- (+) c6 carbon CSV (17 docs) ganha testemunha de completude que nunca teve;
  reusa o padrão de injeção de validador do E3 (custo estrutural baixo).
- (+) Dois traços com vocabulário idêntico compõem trivialmente, mantendo
  ownership de stage limpo.
- (−) Matching cross-source é **ruidoso** (pagamento mínimo/parcial, débito de
  conta externa fora do corpus, timing de vencimento) ⇒ obrigatoriamente
  WARN-first; `faltando` será comum quando a contraparte não está no corpus.
- (−) O status cross pode **oscilar** entre runs conforme o extrato-testemunha
  esteja no corpus — o ratchet de completude deve tratar cross-`faltando` como
  **NÃO-regressivo** (ausência de testemunha ≠ drop detectado).
- (−) Quem enxerga isto é **ledger-certify (E3)**, não parse-certify (E2) — leve
  split conceitual entre as duas skills, documentado aqui.
- (−) Contrato B só vale para bancos cujo débito de pagamento é a autoridade do
  total; discriminadores de descrição (`Inclusao de Pagamento`/`PGTO FAT CARTAO`)
  são C6-específicos → v1 declara-se **C6-only** e degrada `faltando` p/ outros.

## Trabalho futuro (fora do escopo v1)

- Fechamento econômico completo (Contrato B com `saldo_anterior`+encargos) para
  faturas que imprimem "Valor da fatura" (PDF, não CSV).
- Generalização banco-agnóstica dos discriminadores pagamento↔extrato.
- PR2: política de gate `needs_review` após soak da taxa de falso-positivo.
