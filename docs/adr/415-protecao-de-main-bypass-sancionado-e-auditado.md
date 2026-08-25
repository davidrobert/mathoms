---
id: ADR-415
type: adr
title: "Proteção de main: squash-only, bypass sancionado e auditado, e o SHA mergeado como unidade de verificação"
status: Proposto
phase: PLAN-ci-trust Onda 0
date: "2026-08-25"
relates_to:
  - "[[ADR-210]]"
  - "[[ADR-322]]"
  - "[[ADR-320]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 415"
  - "merge protection"
  - "bypass do ruleset"
tags:
  - type/adr
  - status/proposto
  - area/ci
---

# ADR-415 — Proteção de main: squash-only, bypass sancionado e auditado

**Status:** Proposto • **Data:** 2026-08-25 • **Relaciona** [[ADR-210]], [[ADR-322]], [[ADR-320]] • **Plano:** [[PLAN-ci-trust]] §Onda 0

## Contexto

O Ruleset `main-protection` (id `15884038`) é o único gate de `main`:
`required_approving_review_count: 0`, então nenhum humano revisa por obrigação
— o CI é a totalidade da proteção. Ele nunca teve ADR; existia como prosa no
`CLAUDE.md`. A consequência dessa ausência é mensurável em dois lugares.

**Primeiro: a configuração divergiu da política escrita sem ninguém ver.**
`allowed_merge_methods` está em `["merge","squash","rebase"]` enquanto o
`CLAUDE.md` afirma *"squash é o único método"*. `required_linear_history`
barra o merge-commit na prática, mas **rebase-merge passa** — e põe em `main`
N commits cujas mensagens nunca passaram pelo check `Title (Conventional
Commits)`, que valida o título do **PR**. A [[ADR-322]] §Emenda 2026-08-21
declara o predicado 3 do skip docs-only como dependente de squash-only
(*"se o ruleset algum dia aceitar merge commit em main, o predicado 3 afrouxa
calado"*); a condição que ela teme já vale.

**Segundo: 64 merges entraram sem gate e nada os registrou.** Varredura de
2026-08-25 sobre `rulesets/rule-suites` com `time_period=month` (611
avaliações, 08-05→08-25):

| Data | Bypasses | Defeito de CI documentado no mesmo dia |
|---|---:|---|
| 08-05 → 08-08 06:37 | **0** | — |
| 08-08 | 13 | 403 do PAT starva a fila ([[ADR-322]] §Emenda 2026-08-08) |
| 08-12 | 15 | cluster `GH` no gate de liveness |
| 08-14 | 7 | waiver de `nightly`+`security` venceu em 08-13 |
| 08-17 | 9 | cluster `GH` + `auto-update-prs` falhando 10×/5h |
| 08-18 · 08-19 | 4 · 1 | — · 1ª `S2` obsoleta medida |
| 08-21 | 11 | 6 falhas `S2` + lock de billing |
| 08-24 · 08-25 | 2 · 2 | `S2` com página inteira obsoleta |

Três leituras que a janela certa produz e a janela default (`day`, que devolve
2 dos 64) esconde:

1. **É mudança de regime, não taxa de fundo** — zero até 08-08, 16% dos pushes
   em `main` depois.
2. **9 de 9 dias com bypass coincidem com um dia de defeito de CI
   documentado.** O bypass não é indisciplina: é a válvula de escape da
   não-confiabilidade do gate. Remover a válvula sem consertar o gate teria
   convertido 64 bypasses em 64 merges bloqueados exatamente nos dias em que o
   repo precisava andar.
3. **A assinatura dominante é `required status check "expected"`** — o check
   nunca reportou (corrida, starvation, outage), não "vermelho ignorado". A
   minoria grave existe e é o que dói: o #1701 virou `All checks green:
   failure` 2min após o merge, e o #1508 (2026-08-17) entrou com `Pipeline
   tests` vermelho e **quebrou `main`**.

O #1508 esteve registrado por uma semana como possível corrida do trem. A
timeline diz outra coisa: `auto_merge_disabled` por `davidrobert` às
19:56:37Z, `merged` às 19:56:42Z, com o required check **ausente** no SHA
naquele instante — bypass administrativo, sancionado por
`bypass_actors: [{actor_id: 5 (RepositoryRole admin), bypass_mode:
"pull_request"}]`.

## Decisão

- **D1 — `allowed_merge_methods: ["squash"]`.** Uma chamada `gh api`; elimina
  a divergência com o `CLAUDE.md` e restaura a premissa de que a [[ADR-322]]
  §Emenda 2026-08-21 depende. Consequência aceita: rebase-merge deixa de ser
  possível pela UI.
- **D2 — `bypass_actors` permanece, e o bypass vira uso *sancionado e
  nomeado*.** Ele é o único rollback existente para a operação de maior blast
  radius do repo: uma mudança que brique o `all-green` só pode ser revertida
  por um PR que precisaria passar pelo `all-green` brickado. Usos sancionados,
  exaustivos:
  1. **rollback de gate brickado** (revert de PR que quebrou o próprio
     caminho de merge);
  2. **indisponibilidade repo-wide da plataforma** — runner não inicia, lock
     de billing, outage declarado em githubstatus — quando o merge é urgente.

  Fora dessas duas, bypass é incidente. O que muda o custo não é a proibição
  (inexequível: o dono é admin) e sim o **registro automático**: todo bypass
  vira Issue com o SHA e o veredito do check-run no momento do merge (D3).
- **D3 — o SHA mergeado é a unidade de verificação.** Um job em `push: main`
  lê o check-run `All checks green` **no SHA que entrou** e classifica em três:
  `ausente` (corrida/outage), `failure` (**P0 — pede revert**) e `bypass`
  (cruzado com rule-suites). O predicado é *o veredito no momento do merge*:
  run que fecha verde depois **não** reclassifica — foi lendo o estado
  eventual que uma varredura de 40 PRs concluiu "38/40 íntegros" no mesmo
  período em que 64 merges passavam sem gate.
- **D4 — a auditoria de bypass é diária, paginada e com `time_period=week`.**
  O default `day` mais página única vê ~2 de 64. O sweep também compara
  `rulesets/{id}/history`: desabilitar o ruleset, mergear e reabilitar é
  bypass que **não** aparece em rule-suites, e sem esse braço a auditoria
  fecha a porta e deixa a janela.
- **D5 — `required_approving_review_count` continua 0.** Num repo de um humano
  com N agentes, exigir aprovação converte 550 merges/25d numa fila de
  aprovação e o resultado previsível é **mais** bypass, não mais qualidade.
- **D6 — condição de re-decisão datada.** `bypass_actors` é
  `RepositoryRole: 5`, isto é, **qualquer** admin presente ou futuro. Em repo
  público, conceder admin alarga a bypass em silêncio: adicionar admin obriga
  a reabrir esta ADR.

## Alternativas rejeitadas

- **Remover `bypass_actors`.** Mata o único rollback de gate brickado e, pelos
  dados, teria parado o repo nos 9 dias em que o CI estava doente. O problema
  medido não é a existência da válvula — é ela não deixar rastro.
- **Tornar o bypass tecnicamente impossível para o owner.** Não existe no
  GitHub para quem administra o repo; qualquer desenho nesse sentido é teatro.
- **Confiar na auditabilidade nativa.** `rule-suites` não é retenção infinita e
  a paginação default engana: a evidência dos 64 precisou ser **capturada**
  (`docs/plan/CI_TRUST/evidence/`). Auditoria que só existe sob demanda é
  auditoria que não existe no dia em que se precisa dela.

## Consequências

- Todo bypass passa a custar uma Issue e um follow-up; nenhum deixa de existir
  no registro por decurso de prazo.
- `main` ganha, pela primeira vez desde a remoção do `push: main`
  ([[ADR-210]] §camada 2), um sinal contínuo — ainda que só sobre o veredito
  do gate, não sobre a suíte.
- **Backfill é parte da decisão, não follow-up:** os 64 SHAs conhecidos são
  varridos na entrega e viram um inventário único. Ele responde uma pergunta
  aberta de outro item do plano — se o vermelho das 3 últimas medições de
  `main` vem desses merges ou de gates que não compõem.
- KR-B do [[PLAN-ci-trust]] só começa a contar quando D3/D4 estão no ar: uma
  janela de 30 dias não é auditável com retenção de API menor que ela.
