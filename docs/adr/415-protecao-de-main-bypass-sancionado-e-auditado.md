---
id: ADR-415
type: adr
title: "Proteção de main: squash-only, bypass sancionado e auditado, e o SHA mergeado como unidade de verificação"
status: Decidido
phase: PLAN-ci-trust Onda 0
date: "2026-08-25"
amended_at: ["2026-08-26"]
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
  - status/decidido
  - area/ci
---

# ADR-415 — Proteção de main: squash-only, bypass sancionado e auditado

> **Emenda 2026-08-26 (correção de fato, não de decisão):** a §Validação
> afirmava que o merge do #1723 *"não é bypass"*. É — `rule-suite 3817455583`
> registra `result: bypass` com `required_status_checks: fail`. Corrida do
> `update-branch` e bypass não são alternativas: a primeira deixou o check
> `expected`, o segundo liberou o merge. O closeout do plano pegou. D1–D6 não
> reabrem; o que muda é o registro do 1º incidente sob a vigência desta ADR e
> os denominadores das taxas de bypass. Ver §Validação e §Contexto.

**Status:** Decidido • **Data:** 2026-08-25 • **Relaciona** [[ADR-210]], [[ADR-322]], [[ADR-320]] • **Plano:** [[PLAN-ci-trust]] §Onda 0

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
2026-08-25 sobre `rulesets/rule-suites` com `time_period=month` — **611
avaliações capturadas, 07-27→08-25**. A taxa depende do recorte, e os dois
números só coexistem se o denominador estiver escrito: **zero** bypass em 214
avaliações até 08-08 07:53; **16,1%** (64/397) a partir daí; 10,5% sobre o
total, que mistura os dois regimes.

| Data | Bypasses | Defeito de CI documentado no mesmo dia |
|---|---:|---|
| 07-27 → 08-08 07:53 | **0** (214 avaliações) | — |
| 08-08 | 13 | 403 do PAT starva a fila ([[ADR-322]] §Emenda 2026-08-08) |
| 08-12 | 15 | cluster `GH` no gate de liveness |
| 08-14 | 7 | waiver de `nightly`+`security` venceu em 08-13 |
| 08-17 | 9 | cluster `GH` + `auto-update-prs` falhando 10×/5h |
| 08-18 · 08-19 | 4 · 1 | — · 1ª `S2` obsoleta medida |
| 08-21 | 11 | 6 falhas `S2` + lock de billing |
| 08-24 · 08-25 | 2 · 2 | `S2` com página inteira obsoleta |

Três leituras que a janela certa produz e a janela default (`day`, que devolve
2 dos 64) esconde:

1. **É mudança de regime, não taxa de fundo** — zero em 214 avaliações até
   08-08 07:53, 16,1% dos pushes (64/397) depois.
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
  possível pela UI. **Aplicado em 2026-08-25**, verificado ao vivo
  (`allowed_merge_methods: ["squash"]`, `strict: true`, 2 required checks e o
  `bypass_actor` preservados). Backup do estado anterior tomado antes do PUT.
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
  resolve SHA de `main` → PR → **head** → check-run `All checks green` (o
  squash cria commit novo: check-runs do SHA de `main` são sempre vazios) e
  classifica em **cinco** vereditos, quatro deles "não gateado":

  | veredito | significado | ação |
  |---|---|---|
  | `gated` | verde **e** concluído antes do merge | nenhuma |
  | `late` | verde concluído **depois** do merge | Issue — **classe dominante** (46 de 53 no backfill) |
  | `red` | check vermelho no head | Issue — **pede revert** |
  | `absent` | nenhum check-run no head | Issue — corrida/outage |
  | `unknown` | sem PR associado, ou sem timestamp para ordenar | Issue |

  O predicado é *o veredito no momento do merge*: run que fecha verde depois
  **não** reclassifica — foi lendo o estado eventual que uma varredura de 40
  PRs concluiu "38/40 íntegros" no mesmo período em que 64 merges passavam sem
  gate. `bypass` **não** é veredito: é enriquecimento opcional da causa, e a
  ausência dele não impede a detecção (corrida e outage não deixam rastro em
  rule-suites).
- **D4 — a auditoria de bypass é paginada e com `time_period=week`.** O default
  `day` mais página única vê ~2 de 64; página cheia até o teto é truncagem e
  vira erro, não silêncio. **Sem leitura não há contagem**: quando
  `rule-suites` responde 403 — o caso *esperado* sob `GITHUB_TOKEN`, que não
  pode receber `Administration: read` porque essa permissão não existe na
  chave `permissions:` do Actions — o sweep aborta com código ≠ 0 em vez de
  imprimir "0 bypasses", que seria o instrumento cometendo a falta que ele
  existe para denunciar.

  > **Fase — o que existe hoje e o que é da Onda 1.** O braço `push: main`
  > está em produção desde 2026-08-25. O **agendamento diário** e a comparação
  > de `rulesets/{id}/history` (desabilitar o ruleset, mergear e reabilitar é
  > bypass que não aparece em rule-suites) **ainda não existem**: workflow com
  > `schedule:` precisa de entrada no manifesto (S0) e que o Actions já conheça
  > o arquivo (S1), e o Actions só o conhece após o merge — um PR que nasça
  > agendado não mergeia a si mesmo. Entram na leva da Onda 1 do
  > [[PLAN-ci-trust]], junto com o token que consiga ler `rule-suites`. Até lá
  > o sweep é rodável à mão com credencial de admin
  > (`--sweep --period month`).
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

- Todo merge sem gate passa a custar uma Issue e um follow-up; nenhum deixa de
  existir no registro por decurso de prazo. **O registro ACRESCENTA** (uma
  entrada por merge): `issue edit --body` substituiria o corpo inteiro e
  guardaria só o último — a promessa desta linha exige append.
- `main` ganha, pela primeira vez desde a remoção do `push: main`
  ([[ADR-210]] §camada 2), um sinal contínuo — ainda que só sobre o veredito
  do gate, não sobre a suíte.
- **Backfill é parte da decisão, não follow-up:** os 64 SHAs conhecidos são
  varridos na entrega e viram um inventário único. Ele responde uma pergunta
  aberta de outro item do plano — se o vermelho das 3 últimas medições de
  `main` vem desses merges ou de gates que não compõem.
- KR-B do [[PLAN-ci-trust]] só começa a contar quando D3/D4 estão no ar: uma
  janela de 30 dias não é auditável com retenção de API menor que ela.
- **A label `merge-protection` é pré-requisito operacional, não decoração.**
  `gh issue create --label X` aborta se a label não existir e o `gh` não a
  cria; como o caminho de escrita só é alcançado quando há merge sem gate, a
  ausência fica latente e explode no primeiro incidente — foi o que aconteceu
  no primeiro run real (32887693308). O workflow a garante com
  `gh label create --force`, e um teste amarra o nome que ele cria ao que o
  script pede.

## Validação do primeiro run — o detector denunciou o merge que o entregou

O PR que trouxe esta ADR (#1723) foi mergeado às 19:06:31Z. O trem havia feito
`update-branch` **19 segundos antes**, criando o head `75246ac7`; nesse head,
`Lint` e `Pipeline tests` ainda rodavam (`completed_at: null`) e
`All checks green` **nem existia**. O run de `merge-audit` no push classificou
o próprio merge como **`absent`** (run 32887693308, 19:06:37Z — ~6s após o
merge).

**O veredito é uma leitura datada, e isto é propriedade do predicado, não
defeito.** Re-medido em 08-26 com o check-run já concluído, o mesmo SHA devolve
**`late`** (205s). O que muda entre `absent` e `late` é *quando se olha*; o que
não muda é que o SHA **não foi gateado** — as duas classes estão em `UNGATED`.
Ao citar um veredito, cite o run e o instante.

**Correção de 2026-08-26 (o closeout refutou a primeira leitura desta seção).**
A versão original afirmava *"isto não é bypass: é a corrida do `update-branch`"*.
A fonte primária diz o contrário, e é a mesma de onde saíram os 64:

```
gh api repos/davidrobert/mathoms/rulesets/rule-suites/3817455583
→ result: "bypass" · actor_name: "davidrobert"
→ rule_evaluations[0]: {required_status_checks, "fail",
   "Required status check \"All checks green\" is expected."}
```

**Corrida e bypass não são alternativas — são camadas.** A corrida do
`update-branch` produziu o check `expected` (que *é* o `fail` do
`required_status_checks`); o merge entrou porque o `bypass_actor` admin o
liberou. Escrever "não é X, é Y" negava justamente o lado que o endpoint
registra. Que o rótulo `bypass` **discrimina** está medido: no mesmo dia e com
o mesmo ator, 46 avaliações saíram `pass` e 3 `bypass` — ele não carimba todo
push de admin.

O que a versão original acertou: a suíte completa foi rodada em `main` depois
(7.650 + 3.526 testes, verde), então o defeito é de **processo**, não
regressão — o SHA que entrou nunca foi verificado, e desta vez deu certo.

**Enquadramento sob D2:** este bypass **não** é nenhum dos dois usos
sancionados (não era rollback de gate brickado nem indisponibilidade
repo-wide), logo pela própria ADR é **incidente** — o 1º sob a vigência dela,
registrado na Issue #1728.

Consequência para o critério de aceite da Onda 0: "mergeado sem bypass" era
**duplamente** inadequado — não suficiente (a corrida entra sem bypass) e,
aqui, nem verdadeiro. O critério correto é o veredito do detector sobre o SHA
de merge, cruzado com o `result` do rule-suite daquele push.
