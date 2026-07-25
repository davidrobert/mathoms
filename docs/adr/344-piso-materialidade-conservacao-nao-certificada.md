---
id: ADR-344
type: adr
title: "Piso de materialidade no gate de conservação: roteamento sobre o caminho não-certificado (transitório)"
status: Decidido
phase: A39.l10
date: "2026-07-24"
relates_to:
  - "[[ADR-342]]"
  - "[[ADR-272]]"
  - "[[ADR-090]]"
  - "[[ADR-111]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/dados
  - methodology/patrimonio
---

# ADR-344 — Piso de materialidade no gate de conservação (não-certificado)

**Status:** Decidido (A39.l10) · **Data:** 2026-07-24 · **Lane:** [[A39.l10]] (P2)

## Contexto

O gate de conservação de saldo por extrato (`saldo_inicial + Σtx == saldo_final`,
cents, [[ADR-342]]) é **binário**:

- Parser que declara `conservacao_verificavel=True` (semântica de saldo observada,
  não-tautológica) → **HARD**: qualquer `gap ≠ 0` escala p/ `needs_review`.
- Parser **sem** essa declaração → **WARN-∞**: nunca escala; não distingue um gap
  de R$296 de um de R$17k no caminho não-certificado.

Um `gap ≠ 0` significa que **uma ou mais transações sumiram do razão** (row-drop)
ou que a semântica de saldo do parser está errada — integridade de dado. A perda
sub-declara despesa → **superestima a taxa de poupança** (o viés otimista que a
metodologia combate). O `status quo` WARN-∞ deixa isso passar em silêncio.

## Decisão

**Piso de materialidade SÓ no ramo não-certificado:** `gap > piso` escala p/
`needs_review`; `gap ≤ piso` segue WARN (como hoje). O caminho **certificado
permanece cents-tolerância-zero** ([[ADR-342]] item 2 **intocado**).

- **Piso = R$ 100,00** (`_CONSERVATION_MATERIALITY_PISO_CENTS = 10000`),
  **absoluto, único, global**, constante de módulo (não `pipeline.json`).
- **Code próprio `extract.conservation_above_piso`** ([[ADR-272]]) só no ramo que
  escala; o sub-piso reusa `extract.incomplete_conservation` (WARN, inalterado);
  o certificado reusa `extract.incomplete_conservation` (HARD, inalterado). Fora de
  `BLOCKING_CODES`. Isola **exatamente** o comportamento transitório — quando o
  piso for aposentado, a contagem do code → 0 e o membro do enum é **deletado**.

### Reconciliação obrigatória com [[ADR-342]] §Alternativas rejeitadas

A [[ADR-342]] rejeitou "tolerância monetária no gate (ex.: R$ 10)". **Não há
contradição:** aquela rejeição vale para o **caminho certificado** (não afrouxar
onde a semântica de saldo fecha em cents). O piso opera no ramo **WARN-∞, onde a
tolerância hoje é infinita** — logo um piso **finito aperta** (∞ → materialidade),
é **estritamente mais estrito** que o `status quo`. Sem esta frase, um leitor
futuro lê contradição direta.

### Por que R$ 100 (e por que absoluto)

- **Materialidade-de-interrupção + detecção de leak**, NÃO noise floor: ruído real
  é `< R$1` (centavo/sentinela). A faixa **R$1–R$100 é drop real pequeno**,
  conscientemente tolerada no caminho não-certificado. A propriedade que fixa o
  valor é **agregação**: leak *sistemático* (o perigoso, viés-otimista) **soma
  acima do piso e é pego**; drop isolado imaterial escapa até a certificação.
- **Absoluto vence por domínio** (não só pelo veto técnico anti per-banco): piso
  **relativo** daria à conta **maior** o **maior orçamento de drop silencioso**
  (0,1% de R$1M = R$1.000 de tolerância → deixaria passar os drops reais de R$296
  e R$1.000). As contas grandes são o ICP alta-renda, onde o drop importa mais em
  absoluto. R$100 fica ~3× abaixo do menor drop real (R$296) e bem acima do ruído.
- R$500/R$1.000 perdem o drop de R$296; R$10/R$50 floodam `needs_review` (alarm
  fatigue). Corte por percentil de corpus é **indefensável** — magnitude não
  separa drop-real de cosmético (os cosméticos R$7k–R$17k são MAIORES que os drops
  reais). O eixo que separa sinal de ruído é semântico (`conservacao_verificavel`),
  já existente; o piso é backstop de materialidade, **não** classificador.

## Transitoriedade (o piso NÃO é estado terminal)

O piso é **estritamente mais estrito** que o `status quo` (∞ → materialidade) **e
estritamente menos estrito** que a certificação (materialidade → cents-zero). A
certificação **domina** o piso nos **dois** tipos de erro (remove o falso-positivo
cosmético grande **e** o falso-negativo sub-piso). Logo, para qualquer parser com
volume real, **certificar é estritamente melhor** — o piso só compra tempo para a
cauda longa de baixo volume.

- **Gatilho de sunset:** quando a fração de artefatos não-certificados com gap
  cair abaixo do marco de cobertura por 1 sprint cheio, o piso é depreciado e o
  resíduo flippa para HARD (o code `above_piso` é deletado do enum).
- **Dois sinais** (anti-incentivo a não-certificar, deriváveis sem campo novo no
  schema `e2_extract`): (a) **escalados-pelo-piso** (`escalation_code ==
  conservation_above_piso`) = docs que o piso salvou; (b) **escapando-abaixo-do-
  piso** (`warn_reason incomplete_conservation ∧ ¬conservacao_verificavel`) =
  superfície de risco residual — o KPI que prioriza **certificar** um parser.

## Consequências

- Cosméticos R$7k–R$17k **não-certificados** VÃO escalar — **aceito e declarado**:
  `needs_review` ≠ bloqueio, e a persistência é **sinal de backlog de certificação**
  (pressão pró-certificação), não bug do piso.
- Sem campo novo no `e2_extract` (`piso_dependent` rejeitado — contrato é sticky;
  conceito transitório não deixa rastro permanente). Telemetria via code + log
  estruturado com bucket coarse (`above_piso`/`below_piso`) — **nunca** o gap em
  cents ([[ADR-342]] item 5: sem valores na mensagem).
- Corpus real (dogfood): **0/8** não-certificados-com-gap escalam a R$100 (backstop
  inerte hoje, zero regressão em goldens; morde só um gap material futuro).
- **Nota (pré-existente, não introduzida aqui):** `escalate_result` sobrescreve
  `escalation_reason` (dict único) e o gate de conservação roda por último — venceria
  uma escalação anterior de empty-result. Não surpreende: docs vazios não têm gap.

## Alternativas rejeitadas

- **Piso relativo/percentual** — anti-ICP (orçamento de drop cresce com a conta).
- **Piso per-banco** — institucionaliza row-drop (veto data-engineer, [[ADR-342]]).
- **Campo `piso_dependent` no schema** — sticky; transitório não deve virar contrato.
- **Cravar valor por percentil de corpus** — magnitude não separa drop de cosmético.
- **Piso no `pipeline.json`** — transitório quer-ser-deletado via código (revisável).
