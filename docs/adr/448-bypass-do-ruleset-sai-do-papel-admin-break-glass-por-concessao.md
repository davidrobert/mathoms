---
id: ADR-448
type: adr
title: "Bypass do Ruleset sai do papel Admin: break-glass por concessão temporária para um merge"
status: Decidido
date: "2026-10-09"
amended_at: ["2026-10-09"]
relates_to:
  - "[[ADR-415]]"
  - "[[ADR-322]]"
  - "[[ADR-210]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 448"
  - "bypass_actors vazio"
  - "break-glass por concessão"
tags:
  - type/adr
  - status/decidido
  - area/ci
  - area/security
---

> Supersedure parcial de [[ADR-415]] §D2: o bypass do papel Admin. As decisões
> D1 e D3–D6 seguem canônicas na 415. **Decidido e aplicado em 2026-10-09**,
> com o `GET` de verificação e o ensaio do break-glass registrados em §Aceite.

> **Emenda 2026-10-09 — os itens deferidos foram executados (#2210):** cada
> incidente vira uma issue própria, e o Ruleset ganhou alarme em dois braços: o
> sweep com admin varre o `history` (tolerância de break-glass: 15 min) e um
> tripwire sem admin roda a cada push. Ver §Emenda 2026-10-09.

# ADR-448 — Bypass do Ruleset sai do papel Admin

## Contexto

A D2 da [[ADR-415]] manteve `bypass_actors = [RepositoryRole 5 (Admin),
bypass_mode: pull_request]`. Ela restringiu o bypass a dois usos sancionados:
rollback de gate brickado e indisponibilidade de plataforma. A aposta era que
"o que muda o custo não é a proibição, e sim o registro automático" (D3).

**Medido em 2026-10-09** (`rule-suites` de `refs/heads/main`, 24h):

- **24 de 88 pushes em main foram `bypass`**, todos com o ator do dono, em duas
  rajadas de ~1 merge/min (11:37–12:03 e 13:47–14:02 UTC). Nenhum deles era
  um dos dois usos sancionados.
- **Assinatura**, pelos issue events: update-branch, depois
  `auto_merge_disabled` ("Manually disabled by user") em 1–6 s, depois
  `merged` em 6–25 s. Os merges normais pelo auto-merge não têm o
  `auto_merge_disabled`. É o fluxo de quem mergeia "passando por cima das
  regras", seja pela UI web, seja por `gh pr merge --admin` ou `PUT /merge`.
  Sete sessões de agente negaram com evidência. **O dono confirmou (2026-10-09)
  que mergeou pela UI web**, com "Update branch" e o merge que passa por cima
  das regras. O bypass do papel não distingue intenção, pressa ou cliente.
- **Dano:**
  - o #2131 (vite 8) entrou antes de o `All checks green` concluir; o check
    terminou vermelho 2 min depois, e o `npm ci` de todo PR falhou até o
    revert #2172;
  - o #2163 deixou o lock violando o piso de `cryptography`;
  - o #2151 partiu o par Playwright frontend↔Python.
- **O registro funcionou e não mudou nada.** A D3 comentou os 24 casos na
  #1728, aberta desde 2026-08-25 e já com 56+ comentários, e ninguém reagiu.
  A premissa da D2 caiu empiricamente.
- **Superfície:** o token das sessões de agente é o do dono (escopo `repo`), e
  o `AUTOUPDATE_PAT` age como o dono. Os dois aparecem como
  `current_user_can_bypass: pull_requests_only`. Qualquer cliente com essa
  credencial mergeia passando por cima dos checks pendentes.

## Decisão

- **D1 — `bypass_actors: []`.** O papel Admin sai do bypass. Nenhuma credencial
  do dono passa a contornar `required_status_checks` em merge rotineiro.
- **D2 — break-glass por concessão temporária para UM merge.**
  - Re-adicionar o bypass, mergear um único PR com `--admin` e revogar na saída
    do subshell (`trap … EXIT`); comando em
    `docs/reference/runbooks/pipeline_rollback.md` §4.2.
  - As demais regras seguem ativas durante a janela.
  - O merge fica no `rule-suites` como `bypass`, e as duas trocas ficam em
    `rulesets/15884038/history`.
  - Os usos sancionados são os mesmos da 415 D2.
- **D3 — não desligar o `enforcement` como break-glass.** Com `disabled`, o
  ruleset inteiro some: `main` não tem proteção clássica (404). Na janela, todo
  PR com auto-merge cujo check termine mergeia sem gate (eram 15, 13 deles
  BEHIND), o force-push fica livre, e o merge nem gera rule-suite.
- **D4 — residual declarado.** O mesmo token do dono ainda pode dar `PUT` no
  ruleset. A D1 tira o atalho, não a capacidade. Fechar a capacidade exige que
  as sessões de agente usem um `GH_TOKEN` sem a permissão Administration.
  Decisão do dono, fora deste texto.

## Alternativas rejeitadas

- **Manter a 415 D2 e só endurecer o alerta** (S3 na #1728, ou issue por
  incidente). A #1728 prova que registro sem atrito não muda comportamento.
  Um S3 que trava todo merge tem como saída o próprio bypass.
- **Ator dedicado de break-glass** (App ou deploy key). Em conta pessoal, seria
  uma chave de longa duração com merge sem gate, o oposto do KR-I do
  PLAN-ci-trust e da [[ADR-322]] D2.
- **Toggle de `enforcement`.** Ver D3.

## Consequências

- O dreno de backlog fica serial no ritmo do CI. A rajada de 24 merges levaria
  ~3h a p50 de 8 min, contra 41 min com bypass, mas o atalho custou ~35 min de
  main quebrada e dois defeitos de lock. Remédio para backlog: agrupar.
- O rollback de gate brickado continua possível pela D2, com custo de ~1 min de
  comando.
- `docs/reference/runbooks/pipeline_rollback.md` §4.2 e
  `docs/reference/runbooks/security_gates.md` §Override passam a usar o
  break-glass da D2. O `gh pr merge --admin` sozinho falharia em pleno incidente.
- **Deferido, com dono (agente que pegar o item):**
  - o sweep da [[ADR-415]] D4 passa a alarmar quando `bypass_actors ≠ []` fora de
    uma janela de break-glass;
  - o bypass vira **uma issue por incidente**, com a #1728 triada e fechada.
  Condição de retomada: logo após esta ADR virar `Decidido`.
  **Executados em 2026-10-09 (#2210)** — ver §Emenda 2026-10-09.

## Aceite

1. O dono aplica a mudança, com backup:

   ```bash
   R=repos/davidrobert/mathoms/rulesets/15884038
   gh api $R > _scratch/ruleset-pre.json
   gh api -X PUT $R --input - <<<'{"bypass_actors":[]}'
   gh api $R --jq '{enforcement,bypass_actors,current_user_can_bypass,n:(.rules|length)}'
   ```

   Esperado: `active`, `[]`, `"never"`, `5`. Se não bater, restaure o backup
   (só os campos graváveis).
2. **Ensaio do break-glass sem merge:** conceder e revogar uma vez. O `history`
   ganha +2 versões, e `rules|length` continua 5 em cada.
3. Só então: `status: Decidido`, tag `status/decidido`, e emenda na 415
   registrando a supersedure efetiva.

### Executado em 2026-10-09 (autorização do dono no chat)

- **`PUT` aplicado com backup.** O `GET` depois dele: `enforcement=active`,
  `bypass_actors=[]`, `current_user_can_bypass=never`, `rules=5`.
  `rules` e `conditions` ficaram idênticos ao backup; só `bypass_actors` mudou.
- **Ensaio do break-glass sem merge** (subshell com `trap`). O
  `rulesets/15884038/history` passou de 2 para 5 versões:
  - remoção (`v52592012`, bypass=0);
  - concessão (`v52592028`, bypass=1, janela de <1 s);
  - revogação pelo `trap` (`v52592029`, bypass=0).

  As três versões têm `rules=5` e `enforcement=active`.

## Emenda 2026-10-09 — os itens deferidos, executados

Os dois itens de §Consequências entraram no `merge-audit` (#2210), com
co-design do `sre-devops`. O estado foi medido antes de ligar o alarme
(`bypass_actors=[]` desde a versão 52592012), então ele nasce armado, sem
condição de guarda.

- **Uma issue por incidente.** O braço `--sha` abre a issue do SHA fora do
  gate, com o SHA curto e o PR no título. O `--sweep` abre uma para todo
  `bypass`, mesmo com veredito `gated`. Um marcador do SHA no corpo, lido na
  listagem REST de issues, torna o re-run idempotente. A search API, que o
  `gh issue list --label` usa, indexa com atraso. Issue fechada conta como
  registrada.
- **Antes da aplicação desta ADR, o registro é o legado.** O sweep ignora
  bypass e janela anteriores à versão 52592012. A #1728 fica como registro
  legado e é triada e fechada, com o resumo dos 58 casos, no fecho deste PR.
- **Tolerância de break-glass: 15 min**, só para concessão de bypass. A D2
  dura um `gh pr merge --admin`, e o ensaio ficou aberto 703 ms. Os 15 min
  cobrem o break-glass feito à mão, sem o `trap`, e rede lenta. Acima disso,
  não é concessão para UM merge.
- **O sweep varre o `history`**, não só o estado atual: um sweep diário quase
  nunca pega aberta uma janela de 703 ms. Ele alarma toda janela acima de
  15 min. Também alarma, sem tolerância, gate enfraquecido: `enforcement`
  fora de `active` (D3), `All checks green` fora dos required ou `strict`
  desligado. Janela ainda aberta é condição viva, e issue fechada com ela de
  pé é reaberta.
- **Tripwire sem admin, a cada push**, em job com fila global. Ele lê
  `enforcement`, as regras e o `updated_at`. Gate enfraquecido vira alarme
  vivo, e mudança nova vira issue a explicar com o sweep. É por aqui que
  aparece o toggle de `enforcement`, que não deixa rule-suite.
- **`bypass_actors` ausente não é zero.** A API omite a chave para quem não
  administra o ruleset, então `--jq '.bypass_actors|length'` com o
  `GITHUB_TOKEN` daria `0`. O sweep sai "não medido" (rc=2), e o runbook
  §4.2 testa `has("bypass_actors")`.

**Achado que a D3 da [[ADR-415]] não previa.** Três dos 24 bypasses de
2026-10-09 (#2139, #2153 e #2163) saíram `gated` no detector: o check estava
verde no head, mas a base estava desatualizada sob `strict`, e o rule-suite
registra `2 of 2 required status checks are expected`. O #2163 deixou o lock
violando o piso do `cryptography`. O sweep pega esse caso pelo `bypass`, mas o
braço `--sha`, sem admin, não pega. O veredito `stale` ficou deferido com dono
em [[PLAN-ci-trust]], item 0.2c.
