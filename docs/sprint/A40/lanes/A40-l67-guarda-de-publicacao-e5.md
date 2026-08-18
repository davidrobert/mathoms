---
id: A40.l67
type: lane
title: "Guarda de publicação no E5: nenhum balde de patrimônio publica negativo, e o schema deixa de aceitá-lo"
sprint: A40
plan: PLAN-deterministic-authority
status: in_progress
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
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l67 — `a40-l67-guarda-de-publicacao-e5`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (itens 1d,
> 1e). **Destravada em 2026-08-18** — a [[A40.l66]] shipou (#1522) e o roteamento
> por fato existe. Era `blocked` por ela: a guarda tem de rodar sobre roteamento já
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

## 1e entregue — 2026-08-18 (#1529 · `144911a6`)

`patternProperties` `^(31_12_)?\d{4}$` com `minimum: 0` nos 3 baldes de ativo;
`additionalProperties` segue **aberto**. `test_e15c_r6_payload_reprova_no_schema`
desmarcado e verde, provado por mutação nas duas direções.

A assimetria era literal: `dividas[].saldo_31_12` **já** declarava `minimum: 0`
e os três `valores_31_12` de ativo eram `{"type": "object"}`. O passivo era
guardado; o ativo aceitava qualquer coisa.

**Flip para strict NÃO entra** — o critério da lane é drift = 0 por **≥7 dias**
de dogfood, temporal por construção. Retomada: medir a janela e citar o número
no PR do flip, coordenado com [[A40.l58]] (dona de `mode_overrides`).

## 1d — desenho corrigido antes de codar (2026-08-18)

**Correção factual da própria lane:** ela afirma que `next_aporte_classe`,
`desvio_max_pct` e `motivo_supressao` "já são `Optional`". Os dois primeiros são
(`alocacao_alvo_deviation.py:122-123`); **`motivo_supressao` não existe no
repo** — é campo novo. O plano repete a afirmação em §Onda 1 1d. Mesma correção
já feita ao escrever a [[A40.l69]].

**O seam da reclassificação não é a `composicao`.** Medido:
`_compute_bruto` e `_build_composicao` (`patrimonio_calculator.py:165` e `:196`)
são **duas somas independentes sobre os mesmos seis componentes**. Uma guarda que
pós-processe as linhas da `composicao` — zerando o balde negativo e somando à
dívida — dessincroniza `composicao` de `bruto`, e o `pct` por largest-remainder
passa a distribuir sobre um total que não existe.

A reclassificação tem de acontecer **no componente**, a montante das duas somas:
`caixa_total_brl` (cheque especial) e os `investimentos_*` (conta margem) são
corrigidos antes de alimentar `_compute_bruto`/`_build_composicao`, e o montante
vai para `total_dividas`. Assim `composicao ≡ bruto` se preserva e
`patrimonio_liquido` **não muda** — o que muda é a honestidade da apresentação.

Consequência de fila: o 1d tem efeito monetário no publicado (baldes e dívidas
mudam de valor mesmo com líquido constante), logo **precisa da janela J2**, com
`dev/golden_diff.py --manifest` e sinal ↑/↓/= declarado.

Uma primeira versão do serviço foi escrita sobre a `composicao` e **descartada
sem commit** ao medir isto — guarda meio-certa que dessincroniza dois agregados
é pior que guarda nenhuma, porque o defeito passa a ser invisível no lugar onde
o leitor confere.
