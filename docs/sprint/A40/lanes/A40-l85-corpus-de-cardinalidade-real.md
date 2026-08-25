---
id: A40.l85
type: lane
title: "O gate de ancorabilidade roda sobre um corpus que não consegue reproduzir o colapso que ele existe para pegar"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P1
branch_slug: a40-l85-corpus-cardinalidade-real
adrs:
  - "[[ADR-200]]"
  - "[[ADR-341]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/llm
  - area/pipeline
---

# A40.l85 — O corpus do gate não alcança o defeito (follow-up da [[A40.l83]])

> **O gate mede o instrumento certo sobre o payload errado.** Ele existe para pegar
> folha R$ visível sem rota de citação, e o corpus que o alimenta não tem cardinalidade
> para produzir o colapso.

## O que foi medido na [[A40.l83]] (2026-08-25)

O mesmo `measure_anchorability`, os mesmos parâmetros, dois payloads:

| | corpus sintético (`make_workspace_e5`) | E5 real (run `d0f6260a`) |
|---|---:|---:|
| antes do fix | 39,3% (11/28) | **0%** (0/36) |
| depois do fix | 92,9% (26/28) | 86,5% (32/37) |

O sintético lê **otimista nos dois estados**, e no estado defeituoso a diferença é
categórica: 39,3% contra zero.

## Por que ele não alcança

Cardinalidade das duas raízes que consomem o catálogo:

| bloco | real | sintético |
|---|---:|---:|
| Endividamento (E5) | 31 | **2** |
| Reserva de emergência (E5) | 28 | **4** |
| Top ativos (até 15) | 15 | **0** (cabeçalho órfão) |
| KPIs IRPF | 30 | 4 |
| Proteção patrimonial | 41 | 18 |

`_PRIORITY_ROOTS` ranqueia `reserva_emergencia` e `endividamento` primeiro. Em produção
elas sozinhas esgotam o orçamento e o catálogo colapsa em 2 raízes. Com 2 e 4 linhas o
colapso **não tem como acontecer** — o corpus é estruturalmente incapaz de exibir o
defeito. `iter_uncovered_paths` mede o mesmo por outro ângulo: **0** paths não fornecidos
no real, **16** no sintético.

## Armadilhas

**Mexer em `make_workspace_e5` tem raio de 11 arquivos**, incluindo
`test_parecer_planejador_golden.py` e `tests/llm_golden/test_pii_scan_parecer_context.py`.
Mudar os defaults rebaselina golden alheio. O caminho provável é **modo opt-in** de alta
cardinalidade, consumido só pelo snapshot de ancorabilidade — os outros 10 consumidores
seguem no corpus atual.

**Corpus derivado do payload real é PII.** Se a rota for anonimizar o real preservando
forma, o gate de PII do repo é a barra mínima, não a garantia: nome em string livre e
número de contrato passam por varredura de campo. O modo opt-in sintético não tem esse
risco e por isso é a rota default.

**Cardinalidade não é o único eixo.** O `header_orfao` de `Top ativos` (15 vs 0) é
`_render_table` emitindo cabeçalho sobre lista vazia — já nomeado em
`parecer_ancorabilidade.py` como fix do dono do distiller. Encher a lista muda a
ancorabilidade **e** apaga o único caso que exercita o cabeçalho órfão; se for encher,
preserve um bloco vazio em algum lugar.

## Escopo

| peça | superfície |
|---|---|
| modo de alta cardinalidade | `tests/test_parecer_planejador_golden.py::make_workspace_e5` (kwarg opt-in) |
| corpus do snapshot | `tests/test_parecer_ancorabilidade.py` passa a consumir o modo novo |
| rebaseline | `dev/snapshots/parecer_ancorabilidade.json` + `_comment` perde a ressalva de otimismo |

## Critério de aceite

**Corretude** — a distância entre o número do snapshot e o do E5 real cai abaixo de
5pp (hoje 6,4pp no estado bom e 39,3pp no estado defeituoso).

**Completude** — `iter_uncovered_paths` sobre o corpus novo devolve conjunto vazio, ou
os remanescentes têm razão declarada.

**Prova por mutação** — reverter a semente do catálogo (`seed_paths=()`) tem de derrubar
o snapshot **com magnitude comparável à de produção**. Medido em 2026-08-25 sob o
orçamento vigente (`max_bytes` 2400):

| corpus | com semente | sem semente | delta |
|---|---:|---:|---:|
| sintético | 92,9% | 85,7% | **7,2pp** |
| E5 real (`d0f6260a`) | 86,5% | 0% | **86,5pp** |

Doze vezes menos sinal. E o delta do sintético **encolheu** quando o orçamento subiu de
1600 para 2400 na [[A40.l83]] — sob o orçamento antigo essa mutação valia 53,6pp
(92,9% → 39,3%). Ou seja: quanto mais folgado o orçamento, menos o corpus sintético
consegue exibir o defeito, porque com 2 e 4 linhas nas raízes prioritárias tudo cabe de
qualquer jeito. O mecanismo segue gateado por diff de conjunto e por
`test_semente_ocupa_o_prefixo_do_catalogo`; o que está cego é o **percentual**.

## Rastro

Follow-up da [[A40.l83]] §Fecho ("a armadilha central não foi fechada — foi nomeada").
Medições em `dev/snapshots/parecer_ancorabilidade.json` `_comment` e no corpo do #1707.
