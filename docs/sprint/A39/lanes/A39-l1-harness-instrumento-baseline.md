---
id: A39.l1
type: lane
title: "Harness como instrumento de medição: emitir campos de veredito + conservação em cents + congelar baseline"
sprint: A39
status: shipped
ship_date: "2026-07-23"
ship_pr: 1035
priority: P1
branch_slug: a39-l1-harness-instrumento-baseline
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/dx
---

# A39.l1 — `harness-instrumento-baseline` (transversal)

> **SHIPPED por #1035** (`a3188b7a`, 2026-07-23) — entregue **durante a autoria
> deste sprint**. O harness `dev/certify_parse_local.py` passou a emitir campos
> por-tipo, conservação em cents, `--compare` seguro e baseline PII-safe. O
> escopo abaixo é o que foi entregue; a lane nasce `shipped` (reconciliação com
> `main` — ver §Entregue durante a autoria no [[MOC-sprint-a39]]).

## Problema (certificação 2026-07-23)

O harness `dev/certify_parse_local.py` mede o veredito de cada doc, mas hoje
**não emite** os campos que o veredito de 5 estados exige — a certificação
degradou para `coberto-sem-verificação` por falta de sinal, não por falta de
dado. Faltam no baseline: `raw_rows_detected`, `conservacao_verificavel`,
`n_posicoes`, `checksum_ok`/`skipped_no_total`, e a conservação usa float
(`abs(diff) < 0.011`) em vez de `conservation_gap_cents` (tol zero, semântica de
prod). O `--compare` só falha em `n_tx` menor — não pega a **pior** regressão
(`escalated True→False` sem checksum-pass = silêncio reintroduzido).

Esta lane é o **instrumento de medição de todo o A39**: sem ela, KR-A/KR-B/KR-C
não são verificáveis. Vem **primeiro** e **congela o baseline sobre `origin/main`**
antes de qualquer mutação de parser (lição A38 — baseline pós-mutação mede o
próprio fix).

## Escopo

- Emitir por doc no baseline (ext #1): `raw_rows_detected`,
  `conservacao_verificavel`, `n_posicoes`, `checksum_ok`, `skipped_no_total`,
  `escalation_reason.code` — ler direto do result dict do parser (já existem
  onde o parser reporta; `None` quando ausente).
- Conservação em **cents** (ext #4): reusar `conservation_gap_cents` (tol zero)
  em vez do float `<0.011`, para o veredito bater com o gate de produção.
- `--compare` mais forte (ext #5): falhar em `escalated True→False` sem
  `checksum_ok`, em checksum `pass→fail`, e em queda do piso de cobertura
  determinística; erro **limpo** (não crash exit 1) quando o baseline sumiu.
- **Congelar baseline** do corpus dogfood em `storage/<uuid>/certify/` (fora do
  git) sobre `origin/main` — ponto de referência anti-regressão de todas as
  lanes seguintes.

## Critério de aceite

- Baseline emite os 6 campos novos + gap em cents para cada doc do corpus.
- `--compare` retorna exit ≠ 0 em cada uma das 3 regressões (tx menor,
  `escalated True→False` sem checksum, checksum `pass→fail`) — teste com baseline
  sintético; erro limpo (mensagem, não traceback) quando o arquivo sumiu.
- Baseline congelado sobre `origin/main` documentado no corpo do PR (path
  mascarado, fora do git).
- **Zero PII** no baseline (chave `doc_type|institution|period|sha256[:8]`,
  dropa filename legível — ext #6).

## Risco

Baixo — é tooling de medição, não toca parser de produção. Alta alavancagem:
destrava a medição binária de todos os KRs. `area/dx`.
