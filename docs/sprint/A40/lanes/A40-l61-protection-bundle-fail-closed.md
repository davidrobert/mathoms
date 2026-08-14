---
id: A40.l61
type: lane
title: "ProtectionBundle fail-closed: ausência de insumo não vira zero/False e filho conta como dependente"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1443
ship_date: "2026-08-14"
priority: P1
branch_slug: a40-l61-protection-bundle-fail-closed
adrs:
  - "[[ADR-192]]"
  - "[[ADR-240]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/backend
  - area/financial-planning
---

# A40.l61 — `protection-bundle-fail-closed`

> **Aberta e iniciada em 2026-08-13**, no co-design da [[A40.l35]]. É a
> mitigação imediatamente mergeável do split [[A40.l61]] → [[A40.l62]] →
> [[A40.l35]]. Não liga a S9 nem conta como entrega parcial da l35.

> **Entregue em 2026-08-14 pelo PR #1443** (`0a343302`). O fail-closed está em
> `main`; [[A40.l62]] foi desbloqueada e a [[A40.l35]] continua bloqueada até a
> fotografia run-scoped existir.

## Problema

`protection_bundle_populator` convertia ausência de sete insumos em cinco zeros
e dois `False`. A API passava a distinguir mal uma família sem exposição de uma
família sem dados. O mesmo produtor ainda excluía `role == "filho"` do horizonte
de dependência.

O co-design mediu que o E5 atual não contém renda ativa líquida mensal nem situs
EUA canônicos, e que UF/parâmetro ITCMD não podem cair em defaults. Ligar a S9
com aproximações apenas substituiria um falso zero por uma falsa precisão.

## Escopo

- Inputs opcionais e computabilidade explícita por categoria:
  `computed`, `not_applicable` ou `missing_data`.
- Calculator só roda quando todo o conjunto obrigatório está presente; zero
  observado continua sendo valor.
- `filho` e `dependente` entram no predicado econômico tri-state. Idade ausente,
  futura ou dependente adulto não modelado retém o cálculo de vida.
- Família sem dependente econômico menor confirmado não recebe conselho de
  `10× renda`, em conformidade com [[ADR-365]].
- UF, alíquota fiscal, renda e exposição EUA ausentes não viram `SP`, `0` ou
  `False`.
- O endpoint live continua retornando cadastro de apólices, mas sem fabricar
  gaps. A fotografia histórica do Report pertence à [[A40.l62]].

## Fora de escopo

- Produzir os campos canônicos ausentes no E5.
- Persistir o `ProtectionComputationSnapshotV1` no Report.
- Injetar `data.protection_bundle` ou alterar a renderização da S9.

## Delta declarado

- **E5/view-model do Report:** `unchanged`; a lane não injeta bundle nem altera o
  artefato. `dev/golden_diff.py` sobre o snapshot canônico retorna
  `Nenhuma mudança`.
- **Endpoint live `/protection-bundle`:** contrato aditivo
  `calculation_status new ↑`; `has_us_exposure` passa de booleano forçado para
  `bool | null`; thresholds fiscais desconhecidos passam a `null`.
- **Calculators:** menos execuções quando input falta; zeros observados continuam
  calculáveis.

## Critério de aceite

- Remover um input obrigatório de vida, invalidez, sucessório ou compliance EUA
  produz `missing_data`, lista o campo e não emite gap, recomendação ou risco.
- O mesmo input presente com valor zero é distinguível de ausente.
- `role == "filho"` menor atravessa o predicado; idade indeterminada não vira
  ausência de dependentes.
- Perfil sem dependente econômico confirmado não publica `10× renda`.
- Nenhum dos cinco zeros e dois `False` originais sobrevive no populator; teste
  de regressão falha se algum literal voltar.
- Nenhum call-site desta lane injeta `protection_bundle` no Report.
- Suíte proporcional e snapshot OpenAPI verdes; PR squash-mergeado em `main`.
