---
id: PLAN-ci-trust
type: plan
title: "CI Trust — o veredito do CI precisa ser confiável nos dois sentidos"
status: in_progress
created_at: "2026-08-25"
last_review: "2026-08-25"
sprint_origem: A40
sprint_atual: A40
sprints_envolvidas: [A40]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-210]]"
  - "[[ADR-322]]"
relates_to:
  - "[[PLAN-public-release]]"
tags:
  - type/plan
  - status/in-progress
  - area/ci
  - area/devex
  - area/testing
---

# PLAN-ci-trust — o veredito do CI precisa ser confiável nos dois sentidos

> Origem: investigação multi-agente de 2026-08-25 (auditoria dos 11 workflows;
> mineração de 1.412 runs do `ci.yml` 08-01→08-25; varredura de 40 PRs;
> rule-suites com `time_period=month`; 33 memórias verificadas no repo) +
> co-design com `sre-devops`, `product-manager` e `information-architect`.
> Evidência primária em [evidence/](evidence/). Este plano **executa**
> deferimentos datados de [[ADR-210]] e [[ADR-322]] cujas condições de
> retomada foram satisfeitas; abre decisão nova só onde indicado.

## Tese

Os sintomas que motivaram o plano são **uma** classe: *o gate de merge afirma
coisa que não mediu* — a tese da A42 aplicada à camada de entrega.

1. **Falso-vermelho**: o step de liveness (`dev/check_scheduled_workflows.py`,
   no job required `Lint`) reprovou PR verde 4× em 2026-08-25 por página
   inteira obsoleta do índice de runs do GitHub ("18d"/"60d" fixos, "0 de 11
   leituras falharam"). Sobreviveu às duas mitigações mergeadas (#1603, #1625).
   ~40% das falhas de required check amostradas na janela são instrumento, não
   código.
2. **A válvula de escape virou regime**: **64 bypasses administrativos do
   Ruleset em 17 dias (611 avaliações, 16% dos pushes em `main`)** — zero até
   2026-08-08, e 9 de 9 dias com bypass coincidem com dia de defeito de CI
   documentado (403 do PAT, cluster `GH`, waiver vencido, `S2` obsoleto,
   billing lock). A assinatura dominante nos casos amostrados é required check
   **"expected"** (nunca reportou), não "vermelho ignorado" — o bypass é a
   resposta racional a um gate não-confiável, e o caso minoritário e mais grave
   (#1701, `All checks green` FAILURE 2min após o merge; #1508 idem em 08-17,
   que quebrou `main`) entra junto. Consequência: `main` acumulou 64 merges
   sem gate e está **sem medição de CI há 11 dias** (as 3 últimas medições
   manuais falharam). O repo não sabe se `main` está verde.
3. **Falso-verde por rede desligada**: nightly `disabled_manually` há 72d;
   `lineage-eval` fail-open por construção (produtor morto); 2 workflows LLM
   agendados rodam **verdes sem fazer nada** (secret ausente → skip →
   success); `pip-audit`/`npm-audit-prod` se declaram "gate blocking" e nenhum
   consumidor os gateia — exposição de até 28 dias entre CVE introduzida por
   PR e qualquer consequência, em repo público de fintech.

**Critério de admissão** (cerca contra virar balde): entra o que muda **o que o
gate de merge afirma**; não entra otimização de custo ou latência de CI por si.
**Error budget do plano: a mediana open→merge de 12 min** — cada gate novo
declara quanto dela consome; janela de qualquer métrica de saúde ≥14d (o
fenômeno é burst: 4 dias ruins em 17).

## Premissa de custo — e sua contingência

O repo está **público** (verificado 2026-08-25; `isInOrganization: false`).
Actions em runner standard não fatura; a condição de retomada do endgame de
[[ADR-210]] §Adendo 2026-08-21b ("A34 G0") está satisfeita **de fato**. Mas a
vault nega a premissa: A34 está `paused` com W3 (rewrite de histórico) e W4
(metadados) owner-gated, e há sinais fortes de que o flip ocorreu **sem** elas
(99 branches `agent/*` remotas; e-mails reais no `git log`; PII no commit
inicial). Reconciliar [[PLAN-public-release]] com a realidade é **pré-condição
de premissa** deste plano e P0 daquele — se o desfecho for voltar a privado até
W3/W4, a parte "$0" da Onda 1 volta a ser decisão de FinOps (o restante do
plano não depende de visibilidade). E público **não** destrava merge queue
nativo: exige Organization (ver item 2.0).

## Estado medido (2026-08-25) — baselines dos KRs

| Métrica | Valor |
|---|---|
| Merges (08-01→08-25) | 550 (22/dia) · open→merge mediana 0,2h · p90 6,9h · p99 48,8h |
| Runs `ci.yml` | 1.412 — 66,5% success · 24,8% cancelled (trem/concurrency) · 8,7% failure |
| **Bypasses do Ruleset** | **64/611 avaliações em 08-05→08-25 (16%)**; 0 até 08-08; correlação 9/9 com dias de defeito de CI ([evidence/rule-suites-2026-08-25.json](evidence/rule-suites-2026-08-25.json)) |
| Falso-vermelho | ~40% das falhas de required check amostradas são instrumento (6/15) |
| Gate na prática | `required_approving_review_count: 0` — **CI é o único gate**; `allowed_merge_methods` inclui `merge` e `rebase` (contra CLAUDE.md e contra o predicado 3 de [[ADR-322]] §Emenda 2026-08-21) |
| main | 11d sem medição; 3 últimas medições (dispatch) FALHARAM — hipótese mais barata: os 64 merges sem gate, não "gates não compõem" |
| Baseline do watchdog (08-05→08-21) | 19 falhas do step: 7 `GH` · 5 waiver vencido (gate correto) · 7 `S2` obsoleto |
| security.yml | 14/14 falhas semanais até 08-22 → fix #1691 **validado** (dispatch 32876789176, `gitleaks full-history` success) |
| Nightly | disabled há 72d · waiver até 2026-10-15 (razão FinOps caducou) |
| AUTOUPDATE_PAT | criado 2026-07-09 · expira ~2026-10-07 · na expiração o kick do watchdog morre junto e `S2` fica **verde** (fail-open no próprio deadline) |

Nota de método: "38/40 PRs com gate íntegro" mediu ~2 dias e o estado
*eventual* do SHA — não contradiz os 64; o fenômeno é burst e o veredito
no *momento do merge* é outro instrumento (item 0.2).

## KRs (janela ≥14d; baselines acima)

| KR | Predicado | Anti-Goodhart |
|---|---|---|
| **KR-A** | 0 falso-vermelho de instrumento em check required por 30d; fração instrumento/falhas <10% (hoje ~40%) | **E** o caminho não-required emite ≥ os sinais verdadeiros do baseline (19 em 08-05→08-21) — tirar o sinal do required não pode zerar o numerador por cegueira |
| **KR-B** | Bypasses ≤5/30d, **cada um com Issue e follow-up** (hoje: 64/20d, nenhum registrado) | Caminho sancionado escrito em ADR própria; janela conta só com o detector 0.2 ativo; sweep cobre também `rulesets/{id}/history` (desabilitar/reabilitar é bypass sem rule-suite) |
| **KR-C** | Idade da última medição VERDE de main < 48h (7 noites verdes consecutivas para fechar) | Escopo fixado por [[ADR-210]] camada 2 (backend sem `-m "not migration"`, strict schema) — não se satisfaz encolhendo o smoke |
| **KR-D** | security.yml agendado verde 2 sábados consecutivos **E** `security-green` required no Ruleset | Prova por detecção (critério G2 de [[PLAN-public-release]]): commit sintético com segredo falso é BARRADO; CVE sintética em dep de teste reprova o agregador |
| **KR-F** | 9/9 workflows do manifesto com canal de falha declarado em `alerts:` | Provado por falha forçada que abre Issue (hoje 2/9; em 08-17 o `auto-update-prs` falhou 10× em ~5h e nada percebeu) |
| **KR-G** | Gate que depende de produtor externo hard-falha quando o produtor não rodou | Mutação: remover o produtor ⇒ exit ≠ 0 (`lineage-eval` é o caso nomeado) |
| **KR-H** | Mediana open→merge não regride (12 min) | Cada gate novo declara o custo em minutos de mediana antes de entrar |

## Mapa deferimento → item (a fonte é a ADR; o plano carrega predicado+dono+verificação)

| Item | Predicado a satisfazer | Decisão que o fixa | Veículo |
|---|---|---|---|
| 0.1 | 403 de update-branch é terminal para o PR, nunca para o run; `_gh` não re-tenta 4xx | [[ADR-322]] §Emenda 2026-08-08 (decisão já escrita; falta implementar) | [TRACK-ci-trust-onda0-governanca](tracks/ci-trust-onda0-governanca.md) — PR 0, `dev/` puro, fora da janela de workflows |
| 0.2 | Todo SHA que entra em `main` tem veredito registrado (ausente/failure/bypass ⇒ Issue classificada); sweep diário de rule-suites (`time_period=week`, paginado) + diff de `rulesets/{id}/history`; **backfill dos 64** | **ADR nova `Proposto`** (política de merge-protection — o Ruleset não tem ADR hoje) | idem — PR do detector |
| 0.3 | `allowed_merge_methods = ["squash"]`; bypass vira **uso sancionado nomeado** (é o rollback de mudança que brique `all-green`); condição de re-decisão para admin novo | idem ADR nova | idem |
| 0.4 | Workflows LLM sem secret deixam de contar como cobertura: waiver datado nas 2 entradas do manifesto (3 linhas, sem janela de workflow) | classe "teste que se auto-pula não é gate" | idem (manifesto não starva o trem) |
| 1.1 | S1/S2/S3 fora do required; gate de PR = sinais offline + **heartbeat-Issue durável** (existe + `updatedAt` ≤ máx + `violations: 0` + `checked: M/M`); 5 modos residuais R1–R5 declarados; pré-vencimento de PAT/waiver no corpo (warning ≤14d) | [[ADR-210]] §Adendo 2026-08-21b — endgame retomado; entrada `ops-watchdog` original **superada** (Issue que nunca fecha é incompatível com `max_issue_age_days: 3`; fechar por supersedure, precedente §21c) | [TRACK-ci-trust-onda1-workflows](tracks/ci-trust-onda1-workflows.md) — PR 3 da leva, com emenda datada da ADR-210 |
| 1.2 | Falha de compensador abre Issue (9/9) | [[ADR-210]] §Adendo 2026-08-21c §Deferido ("próxima leva que tocar `.github/workflows/**`") | idem — PR 2 |
| 1.3 | Timeouts declarados (go-lint/go-test/all-green); concurrency do nightly não deixa cron pesado cancelar main-smoke; comentários de custo re-medidos; teto do pipeline-tests re-baseado (mediana 3m15s = 65% do teto); legenda do budget-alert | [[ADR-210]] §Follow-ups 21b/21c | idem — PR 1 (inertes) |
| 1.4 | Nightly religado **por job** (main-smoke → 7 verdes → lineage-eval → pesados) e waiver **removido** (não renovado) | religar tudo de uma vez reativa o gate fail-open do lineage-eval — loop de 06-15, reincidente #638/#647 | idem + ação owner |
| 1.5 | `security-green` agregador (`if: always()`, espelho do all-green) required no Ruleset; `security` `max_issue_age_days` 21→7 | fecha a exposição de 28d; o cabeçalho do security.yml passa a ser verdade em vez de ser corrigido para menos | idem |
| 2.x | ver §Onda 2 | — | lanes `planned`; promoção por consumidor datado |

## Onda 0 — registro e válvula (esta semana; nenhum item depende de outro; zero janela de workflow exceto o detector)

Executa como **track self-contained** (precedente: runbooks do
[[PLAN-public-release]]); não abre lane na A40 (cláusula de admissão da A42).

- **PR 0** (`dev/` puro): 403 não-fatal por PR + classificação 4xx/5xx sem
  retry de 4xx — implementa o que [[ADR-322]] §Emenda 2026-08-08 já decidiu.
  Dissolve a classe "PR de CI starva a fila" **sem** alargar o PAT (escopo
  Workflows foi rejeitado no co-design: PAT que escreve workflow exfiltra
  secrets — inaceitável compondo com 1.x/secrets LLM em repo público).
- **Detector pós-merge + sweep de bypass** (um job só, `push: main`, ~10s):
  classifica cada SHA em check-ausente / check-failure (**P0, revert**) /
  bypass (cruza rule-suites); sweep diário no budget-alert
  (`time_period=week`, paginado, dedupe) + diff de `rulesets/{id}/history`.
  **Backfill dos 64 SHAs na entrega** — a janela de auditoria é finita.
- **ADR nova `Proposto` de merge-protection**: squash-only; bypass como uso
  sancionado nomeado (com Issue automática via detector); cadência de
  auditoria; re-decisão datada se aparecer admin novo. ID alocado na escrita.
- **Waiver datado nos 2 zumbis LLM** no manifesto.
- Evidência: capturada em 2026-08-25 ([evidence/](evidence/)) — rule-suites
  `time_period=month` (64 bypasses) + timeline do #1508.

**Aceite da Onda 0**: detector provado por mutação (merge sintético com
required check FAILURE ⇒ Issue); inventário do backfill publicado (explica ou
não o vermelho de main — decide o item 2.2); `allowed_merge_methods` =
`["squash"]` via `gh api`; ADR mergeada `Proposto→Decidido`; PRs da onda
mergeados **sem bypass** (se a Onda 0 precisar de bypass, falhou no objeto).

## Onda 1 — gate confiável + rede religada (leva única de `.github/workflows/**`, PRs na ordem 1 → 2 → 3)

Sequência de risco do co-design: PR 1 inertes (nenhum muda veredito) → PR 2
canal de falha (`issues: write` revisado job a job) → PR 3 endgame (muda o
significado do gate; **rollback nomeado = bypass sancionado + Issue do
detector 0.2**, e é por isso que 0.2 vem antes). Mudança na função de veredito
do `all-green` viaja **sozinha** num PR.

Desenho do PR 3 (heartbeat) — resumo executável; o detalhe fino vai na emenda
da [[ADR-210]] que acompanha o PR:

- Cron mantém **uma** Issue `ops-watchdog` que nunca fecha; corpo
  máquina-legível: `violations`, `checked: M/N`, idade da violação mais
  antiga, pré-vencimentos (PAT, waivers).
- Gate de PR faz **1 chamada** (endpoint de Issues — fora do índice de runs,
  onde moram as leituras obsoletas) e reprova se: Issue ausente (fail-closed),
  `updatedAt` > máx, `violations > 0` ou `checked < N`.
- Modos residuais declarados: R1 verdito rebaixado (mitigação `checked: M/N`);
  R2 latência = `max_age` (troca aceita — §21b); R3 Issue fechada à mão =
  fail-closed ruidoso (válvula = waiver offline); R4 corpo e gate consomem a
  **mesma** função `--report` + mutação (violação sintética aparece e reprova);
  R5 o job não-required tem `if: failure()` → Issue com label em `alerts:` e
  **não** entra em `all-green.needs`.

Itens da onda: 1.1–1.5 do mapa acima. `frontend-e2e` em `all-green.needs`
**não entra de carona** — timeout de 30min contra mediana de 12min é decisão
de latência (KR-H); decidir à parte, provavelmente gate por label/path.

## Onda 2 — só com evidência da Onda 1

| Item | P | O quê |
|---|---|---|
| 2.0 **gate de decisão: Organization + merge queue** | P0 da onda | ADR `Proposto` owner-gated (desenho `senior-cto`+`sre-devops`). Público **não basta** — merge queue exige org. Decisão até ~2026-09-20 amarra a rotação do PAT (org ⇒ PAT morre; senão rotacionar até 10-05). Princípio até lá: **nada de payback longo dentro do trem** (GitHub App, features de trem); investir só no que sobrevive (detector, canais de falha, heartbeat, manifesto, auditoria) |
| 2.1 starvation por classificação de run | P1 | Só se 2.0 = não. `required_workflow_failed` por JOB; watchdog com `gh run rerun --failed` capado |
| 2.2 índices `_generated` no CI | — | **Não decidir ainda**: esperar backfill 0.2 + 7 noites verdes — a hipótese barata para o vermelho de main são os 64 merges sem gate. Se sobrar drift, rotear a `information-architect` |
| 2.3 hooks diff-based inertes no CI | P1 | float-money per-line etc. sob `--all-files` — step `--commit-range` (padrão golden-rebaseline-isolation) + inventário da classe |
| 2.4 ligar `vars.CI_SKIP_DOCS_ONLY` | P2 | Dependência DURA de 1.4 (≥7 main-smoke verdes; [[ADR-322]] §Emenda 2026-08-21 item 4 — a trava é protocolo, nada a enforça); predicado no runbook; aceite: hit rate medido + 0 skips com predicado 5 sobre SHA não-success |

**Cortados desta janela (motivo declarado):** paginação `read_open_issues`
(guarda correta em #1625; morde só ≥100 issues, hoje ~10) · validador local de
título (CI já pega; ganho 1 ciclo) · planner-golden via PR (latente; nunca
exercitado — junto de 1.x quando o workflow ganhar vida) · recalibrar
budget-alert (depende da §Premissa) · migrar PAT→GitHub App (payback morto se
2.0 = sim).

## Datas duras (espelhadas em [OWNER-GATED §0](../../_MOC/OWNER-GATED-active.md))

| Data | Item | O que quebra | Mitigação no plano |
|---|---|---|---|
| ~2026-10-07 | AUTOUPDATE_PAT expira | Trem para **e** o kick do watchdog morre junto; `S2` fica verde (fail-open no deadline) | Pré-vencimento no heartbeat (warning ≤14d) — PR 3; decisão 2.0 até ~09-20 |
| 2026-10-15 | Waiver do nightly vence | Hard-fail em TODO merge, por desenho (precedente 08-13: 7 bypasses) | Onda 1 **remove** o waiver antes (não renova); warning T-30d no heartbeat |

## Correções de registro produzidas por esta investigação

- **#1508 não é incidente isolado: é 1 de 64.** A série (zero até 08-08; 64
  depois; correlação 9/9 com defeito de CI) entra na ADR de merge-protection.
  Timeline capturada em [evidence/pr1508-bypass-2026-08-25.json](evidence/pr1508-bypass-2026-08-25.json);
  memória de agente corrigida. A leitura anterior ("corrida do update-branch")
  fica válida apenas para a classe #1331/#1332.
- **Premissa de orçamento caducou** — emenda datada em [[ADR-210]] (Adendo
  2026-08-25); medições históricas ficam como estão.
- **#1184/gitleaks desarmada pela causa e validada** — fix #1691 + dispatch
  32876789176 verde (primeiro security.yml completo desde 2026-05-23).
- **#1589 mergeou reworked porém dormante** — `vars.CI_SKIP_DOCS_ONLY` não
  existe (`actions/variables` = 0); virou item 2.4.
