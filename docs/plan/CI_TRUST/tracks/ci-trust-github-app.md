---
id: TRACK-ci-trust-github-app
type: track
title: "Track GitHub App — identidade não-admin do trem substitui o AUTOUPDATE_PAT"
plan: PLAN-ci-trust
status: ready
created_at: "2026-10-09"
agent_role: sre-devops
tags:
  - type/track
  - area/ci
  - area/security
  - status/ready
  - priority/p1
---

# Track GitHub App — `ci-trust-github-app`

> Executa o **item 2.5 do [[PLAN-ci-trust]]**: o trem de auto-merge e o
> watchdog trocam o `AUTOUPDATE_PAT` por um GitHub App. A decisão já existe na
> [[ADR-322]]: a D2 fixou o App como alvo estrutural ("PAT é stopgap aceito"),
> e a §Emenda 2026-10-08 (PR #2050) tirou a condicional e pôs prazo. **Prazo:
> track consumido até 2026-12-07, com o flip para o App até 2026-11-20.** As
> duas datas são absolutas e não se movem com o dia da rotação do PAT.
> Prioridade **P1**, com os gatilhos de P0 em §Prioridade. Desenho técnico:
> co-design `sre-devops` de 2026-10-09; escopo e KR: `product-manager`; forma:
> `information-architect`; registro e cancelamento: `senior-cto`. Não é lane de
> sprint: o plano temático já é dono do tema (critério de admissão da A42,
> cláusulas 1 a 4; precedente da Onda 0).

## Onde a decisão mora — sem ADR nova

Decisão `senior-cto` de 2026-10-09:

- O registro é **só** a §Emenda 2026-10-08 da [[ADR-322]] (PR #2050). Não há
  ADR nova: este track conforma o repositório a uma decisão já tomada, e o
  desenho de implementação (`vars.TRAIN_IDENTITY`, Environment
  `automerge-train`, critério de revogação) mora aqui, no §Desenho técnico.
- **ADR nova só nasce em dois casos:**
  1. o spike refuta a premissa: update-branch feito pelo App nasce
     `action_required`;
  2. o desenho sai da D2: App em `bypass_actors`, ou App com a permissão
     `workflows`.

  Nos dois casos o track para onde estiver. O ID da ADR é alocado na escrita
  (`ls docs/adr/ | tail`) e re-checado no rebase; nunca é reservado em prosa.
- O fechamento também é emenda: uma emenda datada na [[ADR-322]] registra a
  revogação do PAT (§PR de limpeza).

## Por que agora — o incidente de 2026-10-07

- O `AUTOUPDATE_PAT` (fine-grained, 90 dias, gravado em 2026-07-09) **expirou
  em 2026-10-07**. O último run verde do `auto-update-prs` foi às 01:47 UTC (o
  do `automerge-watchdog`, às 01:39), e o primeiro `HTTP 401: Bad credentials`
  saiu às 02:35, no `automerge-watchdog` (no trem, a primeira falha foi às
  02:46). Até 2026-10-09 02:30 UTC foram **203 runs falhos**: 114 do
  `auto-update-prs` e 89 do `automerge-watchdog`.
- O canal de falha funcionou e abriu a #2038 (`ops-train`) às 02:35. O `S3`
  conta a idade da issue por data (UTC) e reprova quando ela passa de 3 dias:
  com a #2038, o `Lint` de **todo PR** passaria a reprovar em 10-11. A #2038 foi
  triada e fechada em 10-09 01:36 UTC. A falha seguinte abriu a #2083 às 01:39,
  e o `S3` dela reprova o `Lint` a partir de **2026-10-13 00:00 UTC**. Enquanto
  isso, o trem anda à mão (runbook §5).
- A data podia ser conhecida desde julho. O pré-vencimento previsto no PR 3 da
  Onda 1 não saiu a tempo, e a decisão 2.0 (~09-20) também não.
- Custo de fila: o #2046 (`951fc4ba`) zerou `npm audit` + `pip-audit` na
  `main` e destravou os 18 PRs do Dependabot então parados. A maioria deles foi
  absorvida e fechada entre 10-08 20:50 e 10-09 01:36 UTC, e restam 5 abertos.
  Sem o trem, todo PR aberto fica `BEHIND`, porque o Ruleset é strict
  ([[ADR-322]] D4). Medido em 2026-10-09 03:13 UTC: 16 PRs em `BEHIND`, 15
  deles de agente.
- O #2050 cobre o PAT de transição: aviso T-14 em `ops-pat-expiry` e 401 com
  mensagem acionável. Ele **antecipa** o próximo vencimento, mas não elimina a
  classe de falha.
- Achado da §Emenda 2026-10-08 (PR #2050): o Ruleset tem
  `bypass_actors = [RepositoryRole 5 (Admin), bypass_mode: pull_request]`, o
  PAT age como o dono, que é admin, e o repo é público.
- Medido em 2026-10-09 com `gh secret list` e
  `gh api repos/davidrobert/mathoms/environments`, que lista só `production`:
  o `AUTOUPDATE_PAT` é secret **de repositório**, então qualquer run
  `pull_request` de branch interna o lê, inclusive com um workflow que o próprio
  PR escreveu.

**O que o App muda:**

- o token de instalação vive 1h, e a chave não expira;
- a identidade é própria (`<slug>[bot]`), sem papel Admin e fora de
  `bypass_actors`;
- a chave fica num Environment que só `main` alcança.

## Pré-condições e cláusula de cancelamento

1. **Rotação do PAT — P0, owner-only, até 2026-10-12** (o `S3` da #2083
   reprova o `Lint` de todo PR a partir de 2026-10-13 00:00 UTC). Não é entrega
   deste track, mas o rollback dele (`TRAIN_IDENTITY=pat`) só funciona com PAT
   válido, e o App não fica pronto antes dessa data. Siga o runbook
   [automerge_train](../../../reference/runbooks/automerge_train.md) §2 e anote
   a nova data de expiração no OWNER-GATED §0. Depois do primeiro run verde,
   feche a #2083: o canal de falha só cria e comenta issue, nunca a fecha, e o
   `S3` mede a idade dela, não o estado do trem.
2. **Validação do aviso — obrigação datada, até 1h depois da rotação.** Se o
   #2050 entrar em `main` depois da rotação, a hora conta do merge. Rode
   `gh workflow run automerge-watchdog.yml`. No log do step
   `Aviso de expiração do AUTOUPDATE_PAT` tem de aparecer
   `pat-expiry: folga > 14 dias`. Se aparecer `sem medição`, ou se a issue
   `ops-pat-expiry` abrir com um PAT de 90 dias, reverta o step: um PR que o
   remove junto da entrada `ops-pat-expiry` do `.github/scheduled-workflows.yml`,
   porque o `TestManifestoTemProdutor` reprova label sem produtor. O header
   nunca foi lido com um PAT fine-grained deste repo; até essa validação, o
   aviso T-14 é hipótese.
3. **#2050 em `main`.** O merge está decidido (auto-merge ligado) e não espera
   a rotação. Mas nem o trem nem o runbook §5 o atualizam: ele toca
   `.github/workflows/**` e está atrás do #2084, que mudou os dois workflows.
   Pelas duas leituras do 403 ([[ADR-322]] §Emenda 2026-08-25), o update-branch
   dele é recusado com o PAT rotacionado e também com o `gh` local, que não tem
   o escopo `workflow` (§Emenda 2026-08-08). A saída é o autor rebasar e pushar
   da própria conta (runbook §1, linha do `HTTP 403`). Em 2026-10-09 ele estava
   `BEHIND`.

**Cláusula de cancelamento.** O track **independe** do item 2.0
(Organization + merge queue). Ele só é cancelado se o 2.0 sair `sim` **com data
de migração** antes de o PR de workflows deste track mergear. Nesse caso o
track passa a `cancelled`, porque o merge queue aposenta o trem e o PAT junto.
Um `sim` sem data não cancela: deixaria o PAT vivo sem prazo. Depois do merge
do PR de workflows, o custo restante é o spike e a limpeza, e o track segue.

## Divisão do trabalho

O agente **nunca** encosta em material de chave nem em token: não gera, não
lê, não cola e não imprime. Mudança de configuração do repo (Environment,
variável, secret) o agente só faz depois de um "sim" do owner no chat da
sessão, e anuncia cada uma em 1 linha.

**OWNER-ONLY**

| # | Passo |
|---|---|
| O1 | Rotacionar o PAT e fechar a #2083 (pré-condição 1) |
| O2 | Criar o App na UI (§Configuração do App) e informar o slug e o Client ID, que não são segredo |
| O3 | Gerar a chave privada e baixar o `.pem` |
| O4 | Instalar o App **só** em `davidrobert/mathoms` |
| O5 | Depois de A2: `gh secret set TRAIN_APP_PRIVATE_KEY --env automerge-train --repo davidrobert/mathoms < <arquivo>.pem` e apagar o `.pem` local |
| O6 | Depois do PR de limpeza em `main`: revogar o PAT em <https://github.com/settings/personal-access-tokens> |

**AGENTE**

| # | Passo |
|---|---|
| A1 | Validar o aviso do #2050 (pré-condição 2) e, se ele estiver cego, abrir o PR de reversão do step |
| A2 | Criar o Environment `automerge-train` com branch policy só para `main` (pode sair antes de O2; comandos abaixo). Depois de O2: `gh variable set TRAIN_APP_CLIENT_ID` |
| A3 | **PR de workflows** (§PR de workflows). O merge é inerte: nada muda até a variável mudar |
| A4 | **Spike**: flip para `app`, medição, rollback ensaiado, evidência (§Spike) |
| A5 | **Janela de 14 dias** seguidos em `app` (§Janela) |
| A6 | **PR de limpeza** (§PR de limpeza) |
| A7 | Depois de O6: `gh secret delete AUTOUPDATE_PAT`; emenda datada na [[ADR-322]] registrando a revogação; este track passa a `consumed` |

Ordem: O1 → A1. A2 corre em paralelo com O2–O4; O5 depende de A2. A3 pode
mergear antes de o App existir. A4 depende de O2–O5 e de A3 em `main`. Depois
vêm A5 → A6 → O6 → A7.

**Marcos:** O2–O5 até **2026-11-13**; flip para `app` (A4 concluído) até
**2026-11-20**; track consumido até **2026-12-07**.

Passo A2. Confira a resposta com
`gh api repos/davidrobert/mathoms/environments/automerge-train`.

```bash
gh api -X PUT repos/davidrobert/mathoms/environments/automerge-train \
  -F 'deployment_branch_policy[protected_branches]=false' \
  -F 'deployment_branch_policy[custom_branch_policies]=true'
gh api -X POST repos/davidrobert/mathoms/environments/automerge-train/deployment-branch-policies \
  -f name=main -f type=branch
```

## Configuração do App (passo O2)

Permissões de repositório. Todas as outras ficam em "No access":

| Permissão | Nível | Por quê |
|---|---|---|
| Contents | Read and write | `update-branch` feito por App exige escrita no head; kick via Git Data API (watchdog b) |
| Pull requests | Read and write | `update-branch`; re-habilitar auto-merge (watchdog a) |
| Issues | Read and write | issue de stall do watchdog (c) |
| Actions | Read-only | runs por commit (`runs_for_commit` via `gh run list --commit`): trem e watchdog (a), (b) e (c) |
| Metadata | Read-only | obrigatória |

É o mesmo conjunto do `AUTOUPDATE_PAT` de hoje (runbook §2), que roda trem e
watchdog sem Checks nem Commit statuses: nenhum dos dois lê `statusCheckRollup`
desde o #918 (`PR_LIST_FIELDS` e `WATCHDOG_PR_FIELDS`). O `permissions:` do job
do watchdog ainda pede `checks: read` e `statuses: read` para o `GITHUB_TOKEN`
de fallback; ele não é referência para o App.

**Fora, por decisão:**

- **Workflows.** O 403 de PR que toca `.github/workflows/**` continua
  ([[ADR-322]] §Emenda 2026-08-08). Uma identidade que escreve workflow
  consegue exfiltrar secrets. Pedir essa permissão tira o desenho da D2 e exige
  ADR nova (§Onde a decisão mora).
- **Administration.** O App não é admin. O token de admin do sweep do PR 4 da
  Onda 1 **não** é esta identidade.
- **Checks** e **Commit statuses.** O código não os lê (acima). Se o spike
  mostrar `Resource not accessible by integration` por falta deles, o owner
  adiciona a permissão no App e aprova a mudança na instalação.
- **Secrets** e **Environments.**

Webhook **desligado**, opção "Only on this account", instalação só neste repo.

Formulário pré-preenchido, com parâmetros conforme a doc "Registering a GitHub
App using URL parameters". O nome precisa ser único no GitHub; ajuste se for
recusado. A URL só pré-preenche: **confira cada permissão na tela** antes de
criar.
<https://github.com/settings/apps/new?name=mathoms-automerge-train&url=https://github.com/davidrobert/mathoms&public=false&webhook_active=false&contents=write&pull_requests=write&issues=write&actions=read&metadata=read>

## Desenho técnico

Desenho de implementação da [[ADR-322]] D2, fixado aqui por decisão do
`senior-cto`:

- **Identidade:** App privado, com as permissões da tabela acima, instalado só
  neste repo.
- **Material:** `vars.TRAIN_APP_CLIENT_ID` (o input `app-id` está deprecated
  na v3 da action) e o secret `TRAIN_APP_PRIVATE_KEY` no Environment
  `automerge-train`, com branch policy só para `main`. Os jobs declaram
  `environment: {name: automerge-train, deployment: false}`, o que evita ao
  menos 96 registros de deployment por dia (os dois crons somam 96 runs, mais
  um run do trem por push em `main`). Nenhuma cópia do `.pem`: se a chave se
  perder, gera-se outra.
- **Troca explícita:** `vars.TRAIN_IDENTITY` vale `pat` quando ausente e `app`
  quando ligada. Não há fallback: mint que falha deixa o job vermelho, e a
  falha cai no `ops-train`.
- **Governança:** o App não entra em `bypass_actors`. Incluí-lo reabre a
  [[ADR-415]] (D6) e tira o desenho da D2.
- **Rotação da chave:** anual, ou na hora se houver suspeita, sem downtime
  (§Operação). Sem lembrete automático.
- **Critério de revogação do PAT:** 14 dias seguidos verdes em `app` (§Janela),
  depois o PR de limpeza e a revogação.
- **Alternativas rejeitadas:**
  - PAT com rotação mais curta: mantém a bomba, só encurta o pavio;
  - `GITHUB_TOKEN`: é o `action_required` que motivou a [[ADR-322]];
  - fallback `app || pat`;
  - permissão Workflows no App;
  - App em `bypass_actors`;
  - merge queue: é o item 2.0, fora daqui (ver a cláusula de cancelamento).

## PR de workflows (`.github/workflows/**`; merge inerte)

- `auto-update-prs.yml` e `automerge-watchdog.yml` ganham, no job,
  `environment: {name: automerge-train, deployment: false}`.
- **Step de mint**, com `if: vars.TRAIN_IDENTITY == 'app'`:
  `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0`.
  O SHA foi conferido contra a tag em 2026-10-09. O pin é por SHA mesmo sendo
  `actions/*`, porque essa action manuseia a chave; o ecossistema
  `github-actions` do Dependabot mantém o pin atualizado. Inputs: `client-id`,
  `private-key` e `permission-*` por job:
  - trem: `contents: write`, `pull-requests: write`, `actions: read`. Sem
    `actions: read`, o `runs_for_commit` leva 403 "Resource not accessible by
    integration" em todo run;
  - watchdog: `contents: write`, `pull-requests: write`, `issues: write`,
    `actions: read`.
- **Seletor sem fallback.** Dois steps de trabalho mutuamente exclusivos por
  `if:`, cada um com o seu `GH_TOKEN` definido no step. **Nunca** use a
  expressão `a && b || c`: quando o token vem vazio, ela cai no PAT, e esse é
  exatamente o fallback vetado. Se `TRAIN_IDENTITY` tiver qualquer valor fora
  de {ausente, `pat`, `app`}, o job emite `::error::` e fica vermelho. Um `App`
  digitado errado não pode virar `pat` sem ninguém ver.
- **Modo `app`:** `AUTOMERGE_KICK=1`. Token de App dispara workflow, então o
  kick não gera órfão.
- **Modo `pat`:** o comportamento atual fica intacto, inclusive o fallback
  `GITHUB_TOKEN` do watchdog nas funções que não dependem de atribuição
  ([[ADR-322]] D3).
- **O step `Aviso de expiração do AUTOUPDATE_PAT` mede o PAT nos dois modos**,
  com `GH_TOKEN` e `AUTOMERGE_KICK` próprios derivados de
  `secrets.AUTOUPDATE_PAT`, nunca do token do job. Em modo `app`, herdar o
  `GH_TOKEN` do job faria o script ler a expiração do token de instalação (1h) e
  abrir um `ops-pat-expiry` falso a cada run. O PAT continua sendo medido porque
  é o rollback até a revogação.
- O canal de falha (`if: failure()` → `ops-train`) não muda e continua com
  `github.token`.
- **Teste estrutural** em `tests/dev/`, com mutação:
  1. todo job que referencia `TRAIN_APP_PRIVATE_KEY` declara o Environment
     `automerge-train`;
  2. nenhuma expressão combina o token do App e o `AUTOUPDATE_PAT` por `||`;
  3. o conjunto `permission-*` do mint do trem inclui `actions`.

  Reintroduzir o `||` ou tirar `permission-actions` do trem precisa reprovar o
  teste.
- Runbook `automerge_train`: seção nova "Identidade App", cobrindo o seletor,
  o rollback, a rotação da chave e o diagnóstico de mint falho.
- Custo para o KR-H: ~0 na mediana open→merge, porque o mint leva segundos e
  roda fora do caminho do PR. Declare isso no PR.
- **Residual conhecido:** o PR toca `.github/workflows/**`, e o trem leva 403
  nele pela leitura conservadora do mecanismo ([[ADR-322]] §Emenda 2026-08-25
  deixa em aberto se o 403 vem do PR ou do merge de `main` que traz workflow).
  A saída é o autor rebasar e pushar da própria conta (runbook §1). Antes de
  abrir, rode `gh pr list` e `git log origin/main -- .github/workflows/`. O PR
  não viaja junto de PR que muda o veredito do `all-green`.
- **Coordenação (estado em 2026-10-09):**
  - o #2084 (`actions/*` → Node 24) já está em `main` (`390a61af`) e mudou os
    dois workflows deste PR (`actions/checkout@v4` → `@v5`): parta da `main`
    atual;
  - o #2085 (terceiros SHA-pinned → Node 24), par do #2084, segue aberto e toca
    outros workflows.

  Abra o PR de workflows depois do #2085 em `main`, ou rebaseado sobre ele.
- **Endurecimento oportunista (opcional):**
  1. Se o Environment já existir quando o owner rotacionar o PAT (O1), ele grava
     o PAT novo também como secret do Environment
     (`gh secret set AUTOUPDATE_PAT --env automerge-train`).
  2. Depois do merge do PR de workflows, os jobs passam a ler a cópia do
     Environment, e o agente apaga a cópia de repositório.

  Isso fecha a leitura por run `pull_request` semanas antes da revogação. Se o
  Environment não existir na hora da rotação, não vale fazer outra rotação só
  para isso.

## Spike obrigatório (passo A4)

O spike roda em `main`: a branch policy impede o teste a partir de branch, por
desenho.

1. `gh variable set TRAIN_IDENTITY --body app` (anunciado, depois do "sim" do
   owner), seguido de `gh workflow run auto-update-prs.yml`.
2. Para cada SHA novo que o App produzir:
   `gh api "repos/davidrobert/mathoms/actions/runs?head_sha=$SHA&event=pull_request"`.
3. Amostra mínima de **3 PRs**: pelo menos 1 de agente e pelo menos 1 do
   Dependabot que **não** toque `.github/workflows/**`. Bump de pin de action
   pode levar 403 sem relação com o App ([[ADR-322]] §Emenda 2026-08-25) e
   confundiria a medição.
4. **1 merge** por auto-merge habilitado pelo App, seguido de um run `push` do
   `auto-update-prs`. Isso prova que a cadeia continua viva: merge feito por App
   dispara workflow; merge feito com `GITHUB_TOKEN` não dispara.
5. Caminho (a) do watchdog: desligar de propósito o auto-merge de um PR verde
   (anunciado) e ver o App re-habilitá-lo. O caminho (b), kick de órfão, é
   observado se ocorrer na janela; não é forçado.
6. **Rollback ensaiado uma vez** (§Rollback).
7. **Environment:** abrir um PR descartável, com label `do-not-merge`, nunca
   mergeado e fechado no fim, contendo um job que referencia `automerge-train`.
   O job tem de ser recusado pela branch policy. Ele testa só a presença do
   valor (`[ -n "$K" ] && echo presente || echo ausente`) e **nunca** o imprime.
   A doc do `deployment: false` sugere que a branch policy continua valendo, mas
   não diz isso na tabela de regras; por isso o aceite é por execução.

**Critério mensurável, por SHA que o App atualizar:**

- actor `<slug>[bot]`;
- nenhum run com `conclusion=action_required`;
- run do CI com `jobs.total_count > 0`;
- `All checks green` concluído no SHA;
- `reviewDecision` ≠ `REVIEW_REQUIRED`.

Um único `action_required` refuta a premissa: o flip volta para `pat` e o
track para (§Onde a decisão mora).

**O que o spike observa porque não está documentado** (objeções do co-design,
ambas medidas em 2026-10-09):

- O Ruleset tem `require_extra_approval_for_unattributed_changes: true`. Com
  `required_approving_review_count: 0` deve ser inerte, mas commit de App pode
  contar como "unattributed". Critério: `reviewDecision` ≠ `REVIEW_REQUIRED`.
- O repo tem `fork-pr-contributor-approval = first_time_contributors`. A doc
  limita isso a forks, mas o bot do App é "first-time" por definição. Critério:
  nenhum run `action_required`.

**Veredito do bypass, registrado na evidência:**

- **App:** medido. O `rule-suites` dos merges do App mostra avaliação normal,
  nunca `bypass`, e `bypass_actors` segue `[RepositoryRole 5]`.
- **PAT:** **não medido, por decisão deste track (2026-10-09)**, por três
  razões:
  - o `rule-suites` registra o ator, não o tipo de credencial (as 611 rows de
    `all[]` em
    [evidence/rule-suites-2026-08-25.json](../evidence/rule-suites-2026-08-25.json)
    só identificam o ator por `actor_id`/`actor_name`; nenhum campo do endpoint
    List repository rule suites descreve o tipo de credencial);
  - o código do trem nunca pede merge com bypass, então a observação passiva sai
    verde por vacuidade;
  - uma sonda ativa geraria bypass fora dos usos sancionados da [[ADR-415]] D2.

  A pergunta deixa de existir com a revogação do PAT. A §Emenda 2026-10-08 (PR
  #2050) registra o mesmo: a confirmação por `rule-suites` é insatisfazível
  pelas três razões acima.

**Evidência:** `docs/plan/CI_TRUST/evidence/github-app-spike-<data>.md`, com
os run ids, os SHAs, os ids de `rule-suite` e o resultado do ensaio de rollback.

**Se der errado:** o estrago é 1 PR órfão, e ele se resolve ao voltar para
`pat` (o watchdog com PAT dá o kick).

## Rollback por variável

`gh variable set TRAIN_IDENTITY --body pat`: sem PR, em menos de 1 minuto. O
aceite do ensaio no spike é o `workflow_dispatch` seguinte sair verde em modo
`pat`. O rollback só funciona enquanto o PAT estiver válido. Por isso o PAT
fica até o fim da janela, e a rotação de agora (O1) é obrigatória mesmo com o
App a caminho.

## Janela de 14 dias (passo A5)

- Conta 14 dias **corridos e seguidos** em `app`, a partir do flip, com zero
  401 e zero "Resource not accessible by integration" nos runs do
  `auto-update-prs` e do `automerge-watchdog`.
- Um rollback para `pat` **zera** a contagem.
- Todos os merges da janela saem `gated` no `merge-audit`.
- No fim, a evidência do spike ganha uma seção datada com a contagem de runs
  da janela por conclusão.
- Só depois disso abre o PR de limpeza.

Com o flip até 2026-11-20, a janela fecha até 2026-12-04, e sobram 3 dias para
a limpeza e a revogação.

## Operação depois do flip

- **Rotação da chave:** anual, ou na hora se houver suspeita de vazamento. Sem
  downtime:
  1. o owner gera a chave 2 e roda
     `gh secret set TRAIN_APP_PRIVATE_KEY --env automerge-train`;
  2. o agente roda o watchdog e confirma verde;
  3. o owner apaga a chave 1 na página do App e o `.pem` local.

  Sem lembrete automático: não há API que mostre a idade da chave, e um
  lembrete baseado numa data informada à mão seria decoração.
- **Modos de falha do App** (chave apagada, App desinstalado ou suspenso,
  permissão reduzida): falham no step de mint, de forma visível, e caem no
  `ops-train`. Não há o que medir com antecedência, porque o token vive 1h e a
  chave não expira. Por isso `dev/ci_pat_expiry.py` **não** é adaptado ao App.

## PR de limpeza (passo A6)

- Remove o caminho do PAT nos dois workflows e o seletor `TRAIN_IDENTITY`.
- Remove juntos `dev/ci_pat_expiry.py`, `tests/dev/test_ci_pat_expiry.py`, o
  step `Aviso de expiração do AUTOUPDATE_PAT` e a entrada `ops-pat-expiry` do
  `.github/scheduled-workflows.yml`. Eles saem juntos porque label sem produtor
  reprova o `TestManifestoTemProdutor`.
- **No MESMO commit que deleta `dev/ci_pat_expiry.py`:**
  - na [[ADR-322]] §Emenda 2026-10-08, item 1, tire o backtick de
    `dev/ci_pat_expiry.py`. Essa é a forma histórica que o gate aceita
    (docstring de `dev/check_doc_code_paths.py`, §"O BACKTICK É A AFIRMAÇÃO").
    Sem isso, o hook `doc-code-paths` (pre-commit, `always_run`) recusa o
    commit, então deixar para um docs-only seguinte não é viável;
  - no runbook §2, faça o mesmo com `dev/ci_pat_expiry.py::rotation_url`. O
    gate não casa essa forma (o match é exato), mas a citação viraria morta.
- Depois do merge, o owner revoga o PAT (O6). O agente roda
  `gh secret delete AUTOUPDATE_PAT` e, se a variável ainda existir,
  `gh variable delete TRAIN_IDENTITY` (A7).
- Os demais docs podem ir num docs-only seguinte:
  - emenda datada na [[ADR-322]] registrando a revogação: a D2 deixa de ter
    stopgap. Leva heading `## Emenda <data>`, `amended_at` e blockquote de sinal;
  - o runbook §2 passa a descrever a rotação da chave do App, e a seção do PAT
    vira registro histórico;
  - o OWNER-GATED §0 perde a linha de 2026-12-07;
  - um `docs(ci-trust)` atualiza o §Datas duras e o item 2.5 do plano;
  - este track passa a `consumed`, com `consumed_at`.

## Prioridade e escalada

**P1.** Depois da rotação, o custo de atraso cai: há ~90 dias de folga, e o
prazo de 12-07 deixa ~1 mês antes do próximo vencimento. O track sobe para
**P0** se:

- houver suspeita de vazamento do PAT (alerta de secret scanning ou gitleaks,
  token em log). Nesse caso a revogação imediata é ação do owner, independente
  do track;
- 2026-11-20 passar sem o flip para `app`, o que torna o prazo de 12-07
  inalcançável com a janela de 14 dias;
- a issue `ops-pat-expiry` abrir (T-14 do PAT novo) com o track ainda `ready`.

A herança do bypass pelo PAT **não** é gatilho: não há como medi-la sem violar
a [[ADR-415]] D2 (§Spike), e prioridade não sobe por hipótese.

## KR

**KR-I** do [[PLAN-ci-trust]]: em 90 dias a partir do flip, 0 h de fila parada
por credencial expirada ou revogada **e** 0 credencial de longa duração no
caminho de merge (baseline: 1).

- Anti-Goodhart: KR-B não piora, KR-H não regride, e o App não aparece em
  `bypass_actors`.
- Instrumentos que já existem: runs de `auto-update-prs` e
  `automerge-watchdog` com 401/403, `gh secret list` (repo + Environment) e o
  `merge-audit`.

## Fora de escopo

- A decisão Organization + merge queue (item 2.0). Daqui só sai a cláusula de
  cancelamento.
- A permissão Workflows no App e o 403 de PR que toca `.github/workflows/**`,
  inclusive nos bumps do Dependabot no pin da action.
- Qualquer mudança em `bypass_actors` ([[ADR-415]] D2/D6).
- A corrida do `update-branch` (item 2.1).
- O heartbeat e o S1/S2/S3 fora do required (item 1.1, PR 3 da Onda 1). O
  pré-vencimento do PAT **não** volta para lá: o #2050 é o único instrumento
  desse fato até a revogação.
- O token de admin do sweep agendado (PR 4 da Onda 1).
- A drenagem dos PRs do Dependabot.
- Outras credenciais de longa duração (PAT do Coolify; credencial de push do
  GHCR, se houver).
- Lembrete automático de rotação da chave do App.

## Critério de aceite

1. **Pré-condições:**
   - rotação feita: 1 run verde de `auto-update-prs` e 1 de
     `automerge-watchdog` sem 401, e a issue `ops-train` aberta do incidente
     (hoje a #2083) fechada;
   - aviso validado até 1h depois da rotação: `pat-expiry: folga > 14 dias` no
     log, ou o step revertido;
   - #2050 em `main`.
2. **Spike:** o critério mensurável do §Spike vale para todo SHA atualizado
   pelo App. A amostra é de pelo menos 3 PRs (pelo menos 1 do Dependabot e 1 de
   agente), mais 1 merge por auto-merge habilitado pelo App seguido de run
   `push` do `auto-update-prs`, mais o caminho (a) do watchdog.
3. **Governança:**
   - o `rule-suites` mostra os merges do App avaliados, nunca como `bypass`;
   - `bypass_actors` continua `[RepositoryRole 5]`;
   - o veredito do bypass está registrado na evidência (App medido; PAT não
     medido, com o motivo).
4. **Environment:** aceita só `main`, e um run `pull_request` não lê
   `TRAIN_APP_PRIVATE_KEY` (provado por execução, sem imprimir valor).
5. **Rollback** ensaiado uma vez durante o spike.
6. **Janela:** 14 dias seguidos em `app`, conforme o §Janela. Só então: PR de
   limpeza, PAT revogado, secret apagado, `dev/ci_pat_expiry.py` e a entrada
   `ops-pat-expiry` do manifesto removidos.
7. **Docs:**
   - emenda datada na [[ADR-322]] registrando a revogação, sem ADR nova;
   - runbook descrevendo a identidade nova;
   - plano com §Datas duras e item 2.5 atualizados;
   - OWNER-GATED sem a linha;
   - este track `consumed`.
8. **Concluído** significa PRs mergeados em `main` com CI verde e merge `gated`
   no `merge-audit`, sem bypass, e KR-H sem regressão (janela de 14 dias antes e
   depois). Prazo: **2026-12-07**.
