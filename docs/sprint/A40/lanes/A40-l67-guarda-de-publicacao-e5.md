---
id: A40.l67
type: lane
title: "Guarda de publicação no E5: nenhum balde de patrimônio publica negativo, e o schema deixa de aceitá-lo"
sprint: A40
plan: PLAN-deterministic-authority
status: blocked
priority: P0
branch_slug: a40-l67-guarda-de-publicacao-e5
owner: financial-planner
adrs:
  - "[[ADR-145]]"
  - "[[ADR-212]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
depends_on:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/blocked
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l67 — `a40-l67-guarda-de-publicacao-e5`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (itens 1d,
> 1e). `blocked` por [[A40.l66]]: a guarda tem de rodar sobre roteamento já
> corrigido, senão mede o defeito da lane anterior e a taxa de disparo sai
> inflada — e o flip do schema para strict é, por desenho, o **último** passo da
> Onda 1.

## Problema

O E5 publicou um balde de **ativo negativo** e nada o segurou. A assimetria está
medida em `pipeline/domain/services/patrimonio_calculator.py`: a linha 194
clampa (`investivel_efetivo = max(0.0, …)`), a 179 não — o
`split_imoveis_geradores_vs_nao_geradores` e os baldes que alimentam
`composicao` passam o negativo adiante. No r6 isso publicou "Imóveis de Renda"
com valor rebaixado, as dívidas caíram 89%, e o score **subiu**.

O contrato tampouco segura: medido nesta sessão, `validate_dict` do payload r6
contra `baseline_patrimonial` retorna `True` — não há `minimum` nos
`valores_31_12` dos baldes de ativo. Vale notar que o retorno de `validate_dict`
é **dependente de modo** (warn devolve `True` mesmo com payload inválido), então
o golden da Onda 0 mede `iter_errors` direto.

## Escopo

**1d — guarda de sinal nos 7 baldes [[ADR-145]], com rota de reclassificação
ANTES da guarda.** Negativo legítimo (cheque especial, conta margem)
**reclassifica** determinístico para dívida de curto prazo e **publica**
normalmente; só o negativo que sobrevive à reclassificação vira warning tipado +
`needs_review`. Sem essa rota, a guarda transformaria saldo devedor legítimo em
ruído recorrente.

Regra unificadora (vai na ADR-A): **prescrição exige cobertura; descrição admite
ressalva.** Cobertura incompleta ⇒ `next_aporte_classe=None` +
`desvio_max_pct=None` + `motivo_supressao` (os três campos já são `Optional`),
**sem** suprimir o resto do relatório.

**1e — simetrização do contrato.** `patternProperties` `^(31_12_)?\d{4}$` com
`minimum: 0` nos 3 baldes de ativo de `baseline_patrimonial.schema.json`.
**Sem** fechar `additionalProperties` — os resolvers leem 3 formas de chave
vivas (§Anti-decisões do plano). O flip de `mode_overrides` para strict dos 2
schemas de baseline é o **último passo da Onda 1**, com gate medido: drift = 0
por ≥7 dias de dogfood, e o número citado no PR do flip.

## Enforcement

WARN-first ([[ADR-357]]/[[ADR-358]]). Budget de 1d medido sobre r5+r6 e
declarado antes do flip; kill-switch por env var. Para 1e o kill-switch é
`mode_overrides`. Estado terminal de unidade não processada é `degraded` +
`needs_review` — nunca run vermelho.

## Coordenação declarada

- **[[A42.l6]]** cede o eixo dos 2 schemas de baseline e mantém
  retenção/`SCHEMA_BY_STAGE`; **[[A40.l58]]** mantém `mode_overrides` e o
  kill-switch como infra. Disposição tripartite escrita na §Roteamento do plano
  (RV6-06) — esta lane **não** abre PR nas superfícies delas.
- O flip para strict compartilha a **fila serializada de rebaselines e
  migrations** do plano (§Onda 0 · 0d): uma janela por onda, dono declarado.

## Critério de aceite

- `tests/test_e15c_golden_execution.py::test_e15c_r6_payload_reprova_no_schema`
  desmarcado e verde.
- Balde negativo legítimo (cheque especial) **publica** após reclassificação —
  fixture própria, não coberta pelo golden r6.
- Balde negativo sobrevivente produz warning tipado + `needs_review` e **não**
  aborta o run (teste do kill-switch inclusive).
- Cobertura incompleta suprime só a prescrição (`next_aporte_classe`,
  `desvio_max_pct`) e emite `motivo_supressao`; o resto do relatório publica.
- Drift do schema = 0 por ≥7 dias de dogfood, número citado no PR do flip.
- ADR-A (aberta na [[A40.l66]]) emendada com a regra "prescrição exige
  cobertura; descrição admite ressalva", ou a lane cita a seção já escrita.

## Fora de escopo

- Roteamento por fato e conservação por eixo → [[A40.l66]].
- Copy/estado de banner e o 3º estado do export → lanes de render no
  [[PLAN-report-trust]] (7a/7e), fora desta lane.
- Subir `schema_validation.mode` **global** — anti-decisão explícita do plano;
  só per-schema com janela medida.
