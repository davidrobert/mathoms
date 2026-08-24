---
id: A40.l36
type: lane
title: "Double-count potencial na base da cascata fiscal da S8: pró-labore pode entrar duas vezes"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l36-double-count-base-cascata-s8
adrs:
  - "[[ADR-236]]"
  - "[[ADR-375]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l36 — `double-count-base-cascata-s8`

> **Aberta em 2026-08-11**, achado do co-design da [[A40.l34]] (`senior-cto`).
> Registrada como §Não-objetivo da [[ADR-375]] para não inchar aquela lane.
> **Não medida ainda** — o achado é de leitura de código, e a lane começa
> confirmando ou refutando.

## Problema (a confirmar)

`cascata_calculator.py:383` compõe a base PF como
`cargas.bruto_anual` (pró-labore anualizado) `+ outras_rendas_tributaveis_pf_anual`.
O segundo termo é preenchido por `tributario_input_builder._assemble_input` a
partir de `_load_irpf_renda_tributavel`, que é o **total** de rendimentos
tributáveis do IRPF.

**Se o total do IRPF já contém o pró-labore, a base da S8 soma duas vezes.**

Isto importa mais depois da [[ADR-375]], não menos: aquela ADR faz da S8 a
**dona única** do limite PGBL publicado. Um defeito na base da S8 deixa de ter
uma segunda opinião no documento para contradizê-lo.

## Escopo

1. **Medir primeiro.** Confirmar se `_load_irpf_renda_tributavel` inclui a ficha
   de pró-labore. O achado é de leitura; pode não reproduzir.
2. Se reproduzir: decidir quem é a fonte do pró-labore quando as duas existem —
   é regra de domínio, gatilho de `financial-planner`.
3. O defeito é do produtor da S8 e cai **dentro** da [[ADR-236]]: emenda datada,
   não ADR nova, salvo se a decisão mudar a base declarada.

## Critério de aceite

- Medição registrada, com o caso que reproduz **ou** a refutação datada.
- Se reproduzir: teste com pró-labore presente nas duas fontes, provando a
  contagem única.
- Delta declarado e conferido por `dev/golden_diff.py` — a base cairia, então o
  sinal é `↓`.

## Colisão declarada

Toca `cascata_calculator.py`, que a [[A40.l34]] **não** modifica (a l34 só
consome a base). Sem colisão de conteúdo; quem mergear depois rebaseia.

## Entregue — 2026-08-17

Confirmado, medido e corrigido. Base 318.000 → 174.000 (**−82,8%**), teto PGBL
38.160 → 20.880. Decisão de domínio em [[ADR-236]] §Emenda 2026-08-17
(`financial-planner`, duas rodadas).

**A ADR-236 se contradizia**: o §D3 mandava somar pró-labore + outras, a §Riscos
proibia inferir base de pró-labore só. Sobreviveu a §Riscos — só o IRPF tem o
*total* que o RIR/2018 art. 68 manda usar.

### O delta tem DUAS dimensões — declarar só a monetária engana o revisor

| dimensão | direção |
|---|---|
| monetária (`pgbl_base_anual`, `renda_pf_tributavel_total`) | **↓** sempre, = 12% do pró-labore anualizado |
| conjunto de triggers | **não-monótona**: T3 apaga sem IRPF; T1 **acende** com IRPF |

T1 é *prescritivo* ("subir pró-labore", com custo real de INSS) e sua guarda de
elegibilidade (`base/(base+delta) ≥ 0,80`) é **monotônica na base** — baixar a
base só pode ligá-lo. Quem olhar o `golden_diff` e vir só o dinheiro cair não vê
a prescrição aparecer.

### Achados que não estavam no escopo

- **Dois testes que PASSAVAM** asseveram ausência de T1/T3 e passariam por
  construção com base zero — verde sem cobertura. Ganharam guarda anti-vacuidade.
- **O gate LGPD pegou regressão real do rename**: a denylist de `redaction.py`
  casa por prefixo, e `outras_rendas` deixou de cobrir o campo — ele vazaria em
  log. Foi o único gate que viu.
- **A fixture do T1 precisou de dimensionamento medido**: com 174k a razão passa
  de 0,80 (alvo = teto INSS 8.157,41) e o trigger DESLIGA, deixando o teste verde
  sem exercitar o que existe para exercitar. Ficou em 96k.
- **O gate `test_pgbl_base_...` foi reescrito em pé e ficou mais forte**: passou a
  discriminar quatro grandezas (canônica, `receita×32%`, pró-labore-only,
  double-count) em vez de uma. Com IRPF = 0 as duas primeiras coincidiam.

### Follow-up P1 que esta lane destravou — [[A40.l65]]

Com o pró-labore fora, **a base perdeu a âncora do titular**.
~~`_read_latest_workspace_artifact` pega o IRPF mais recente por `created_at`, sem
resolver ano-base e sem dedup~~ — e o artifact é **por declarante**. Numa família
de dois, a base do PGBL vira a declaração de quem foi processado por último, e o
teto de 12% é por CPF, não por família.

> **Metade fechou em 2026-08-24 (#1672).** O eixo do **ano** já não depende da
> ordem de processamento: `_read_latest_workspace_artifact` deixou de existir, e
> a S8 passa por `resolve_ano_base_fiscal` com a mesma partição e dedup do E5
> ([[A40.l65]] §Escopo 1). **Segue aberto** o eixo do **declarante** — com dois
> declarantes no ano eleito a escolha ainda é por recência, e o teto de 12%
> continua sendo por CPF ([[A40.l65]] §Escopo 2).
