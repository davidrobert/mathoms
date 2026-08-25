---
id: TRACK-ci-trust-onda0-governanca
type: track
title: "Track Onda 0 — registro e válvula: detector pós-merge, auditoria de bypass, ADR de merge-protection, PR 0 do trem"
plan: PLAN-ci-trust
status: consumed
created_at: "2026-08-25"
consumed_at: "2026-08-25"
agent_role: sre-devops
tags:
  - type/track
  - area/ci
  - status/ready
  - priority/p0
---

# Track Onda 0 — `ci-trust-onda0-governanca`

> **CONSUMIDO em 2026-08-25.** PRs #1723 (entrega) e #1729 (correção do que o
> primeiro run real expôs); Ruleset em `["squash"]`; [[ADR-415]] `Decidido`.
> Os dois merges seguintes ao fix entraram **gateados**, verificados pelo
> próprio detector. Entregue: PR 0 (recusa não mata o run) · ADR-415
> `Proposto` + waiver dos zumbis LLM · detector pós-merge + backfill.
> **O backfill mediu 53 dos 64 bypasses sem gate: 46 `late` (o required check
> concluiu DEPOIS do merge) e 7 `red` (check vermelho no head).** Inventário
> em [../evidence/backfill-inventario-2026-08-25.md](../evidence/backfill-inventario-2026-08-25.md).
> Dois desvios do desenho original, ambos por medição — ver §Desvios.

> Executa a **Onda 0 do [[PLAN-ci-trust]]**. Baseline que motiva: **64
> bypasses administrativos do Ruleset em 08-05→08-25 (16% dos pushes em
> `main`)**, zero registrados, com `main` sem medição de CI há 11 dias.
> Evidência em [../evidence/](../evidence/) (capturada 2026-08-25;
> rule-suites com `time_period=month` — o default `day` foi o que escondeu
> 62 dos 64). Nenhum item deste track toca `.github/workflows/**` exceto o
> detector (1 arquivo novo) — a leva grande de workflows é o track da Onda 1.

## Entregas (ordem)

### 1. PR 0 — trem: 403 não-fatal + classificação 4xx/5xx (`dev/` puro)

Implementa o que [[ADR-322]] §Emenda 2026-08-08 **já decidiu** ("o 403 é
terminal para aquele PR, nunca para o run"):

- `dev/ci_advance_automerge_train.py::update_branch`: trata 403 → registra
  `skip_reason` para aquele PR, **continua a fila**, emite o motivo no output.
- `dev/ci_advance_automerge_train.py::_gh`: classifica `rc`/status — **não
  re-tenta 4xx** (medido §Adendo 2026-08-21c: 9 re-tentativas de um 403
  determinístico, 0 recuperações).
- Teste em `tests/dev/test_ci_automerge_train.py` (fixtures existentes):
  403 na cabeça ⇒ próximo PR da fila ainda é processado.
- **NÃO** adicionar escopo Workflows ao `AUTOUPDATE_PAT` (rejeitado no
  co-design: PAT que escreve workflow pode exfiltrar secrets do repo —
  inaceitável em repo público compondo com futuros secrets LLM). O resíduo
  (autor de PR de workflow rebasa à mão, ~30s) fica documentado no runbook
  [automerge_train](../../../reference/runbooks/automerge_train.md).

### 2. ADR nova `Proposto` — política de merge-protection

O Ruleset `main-protection` (15884038) **não tem ADR** — existe só como prosa
no CLAUDE.md, e foi assim que `allowed_merge_methods` divergiu para
`["merge","squash","rebase"]` sem ninguém ver e 64 bypasses ficaram sem lugar
de registro. Alocar ID por `ls docs/adr/ | tail` **na escrita** (nunca citar
número antes). Conteúdo mínimo:

- `allowed_merge_methods: ["squash"]` (fecha a dependência declarada do
  predicado 3 de [[ADR-322]] §Emenda 2026-08-21, que hoje está violada).
- **Bypass como uso sancionado nomeado** — é o único rollback de mudança que
  brique o `all-green` (o revert também precisa passar pelo gate brickado).
  Usá-lo exige Issue automática (detector, item 3) + follow-up. Manter
  `bypass_actors` (removê-lo converteria dias de gate doente em repo parado:
  9/9 dias com bypass coincidem com dia de defeito de CI documentado).
- `bypass_actors` hoje = `RepositoryRole: 5` (**qualquer** admin futuro) —
  condição de re-decisão datada se aparecer admin novo.
- **Não** exigir `required_approving_review_count > 0` (repo de 1 humano + N
  agentes: viraria fila de aprovação e produziria MAIS bypass).
- Cadência de auditoria: sweep **diário** (item 3), não semanal.

Aplicação no Ruleset (1 chamada `gh api` PUT) só **após** a ADR mergeada.

### 3. Detector pós-merge + sweep de bypass (um job só; único toque em workflows)

Job novo `main-sha-verify` com trigger `push: main` (~10s/run, $0 em repo
público) + braço de sweep no cron do `budget-alert.yml` (já tem
`issues: write`):

- **Pós-merge**: para o SHA que entrou, classifica em `check-run ausente`
  (corrida/outage) · `check-run failure` (**P0 — código vermelho em main;
  Issue pede revert**) · `bypass` (cruza com rule-suites). Nota de leitura: o
  veredito é **no momento do merge** — run que completa verde depois não
  reclassifica (foi assim que a varredura "38/40 íntegros" mascarou o burst).
- **Sweep diário**: `rule-suites?time_period=week&per_page=100` **paginado
  até esgotar** + dedupe por `id` (o default `day` + página única vê ~2 de
  64) **e** diff de `rulesets/{id}/history` (desabilitar→mergear→reabilitar é
  bypass sem rule-suite — a janela que o sweep de suites não vê).
- Saída: Issue rotulada (`bypass-audit` / `main-sha-ungated`), com label
  declarada em `alerts:` no manifesto `.github/scheduled-workflows.yml`.
- **Backfill obrigatório na entrega**: rodar sobre os 64 SHAs de
  [../evidence/rule-suites-2026-08-25.json](../evidence/rule-suites-2026-08-25.json)
  e publicar **um** inventário (a retenção da API apaga a janela — é a última
  chance de auditar). O inventário decide o item 2.2 do plano (a hipótese
  barata para o vermelho das 3 medições de `main` são esses merges).

### 4. Waiver datado nos 2 zumbis LLM (manifesto; 3 linhas)

`llm-cross-provider-smoke.yml` e `planner-golden-monthly.yml` rodam verdes
sem secret (skip com warning). Waiver datado em `.github/scheduled-workflows.yml`
com reason "sem secret → não mede nada; vencimento força re-decisão do owner"
— usa o mecanismo de exceção datada que o repo já tem, sem janela de
workflow. O fail-closed em `schedule` entra na leva da Onda 1.

## Desvios do desenho, medidos na execução (2026-08-25)

1. **O detector não pode ler check-runs do SHA de `main`.** O squash cria
   commit novo e os checks ficam no head do PR: `commits/<sha-de-main>/check-runs`
   devolve `[]` para **todo** merge — um detector escrito assim diria `absent`
   em 100% dos casos e seria ruído puro. O fluxo correto é
   `commits/{sha}/pulls` → `head.sha` → `check-runs`. Coberto por teste com
   mutação (trocar o head pelo SHA de main derruba 3 testes).
2. **O sweep agendado saiu deste PR.** Workflow com `schedule:` precisa de
   entrada no manifesto (S0) **e** que o Actions já conheça o arquivo (S1) —
   e o Actions só o conhece após o merge, então um PR que nasça agendado não
   mergeia a si mesmo. É o mesmo bootstrap que a [[ADR-210]] §Adendo
   2026-08-21b registrou para a entrada `ops-watchdog`. Medido: com a entrada
   no manifesto, `check_scheduled_workflows` sai `exit=1` com
   `[S1] merge-audit.yml: declarado no manifesto mas o Actions não conhece o
   arquivo`. Um waiver de bootstrap resolveria, mas viraria dívida datada que
   trava o repo se ninguém a remover. Decisão: o braço `push: main` (que cobre
   todos os merges) entra agora; o sweep agendado + `rulesets/{id}/history`
   entra na leva da Onda 1, com o arquivo já em `main`. Rodável à mão nesse
   intervalo: `--sweep --period month`.

## Aceite

1. PR 0: teste de fila-continua-após-403 verde; `_gh` com 4xx sem retry.
2. ADR mergeada e Ruleset com `allowed_merge_methods == ["squash"]`
   (confirmar por `gh api`).
3. Detector provado por **mutação**: merge sintético em branch de teste com
   required check FAILURE ⇒ Issue aberta com classificação certa.
4. Inventário do backfill dos 64 publicado (comentário na Issue de auditoria
   + linha no plano).
5. Todos os PRs deste track mergeados **sem bypass** — se a Onda 0 precisar
   de bypass para entrar, falhou no próprio objeto.
6. Labels novas declaradas em `alerts:` no manifesto (KR-F conta 9/9 ao fim
   da Onda 1).
