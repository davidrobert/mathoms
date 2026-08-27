---
id: A40.l84
type: lane
title: "O invariante é declarado global em comentário e enforçado num só ponto de entrada: run completa sobre review que ninguém aprovou"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1771
ship_date: "2026-08-27"
priority: P0
branch_slug: a40-l84-guard-na-camada-errada
adrs:
  - "[[ADR-404]]"
  - "[[ADR-359]]"
  - "[[ADR-417]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/backend
  - area/pipeline
---

# A40.l84 — Guard na camada errada (RV8-08)

> **O comentário declara o invariante como se fosse global; o código o enforça
> num ponto de entrada.** O outro caminho está documentado no runbook como ação
> operacional, o que normaliza o contorno.

> **Re-âncora datada — 2026-08-26 (rodada unificada **U1**, [[ADR-416]] ·
> [[PIPELINE-REVIEWS-active]] §r9 PV9-29).** O sítio moveu: `_flip_run_to_resuming` está em
> `backend/app/services/pipeline/pipeline_service.py:281` (era `:262`) e já carrega
> `_reject_if_executor_concorrente` na `:289`, entregue pelo PR2 da [[A40.l87]] (#1743,
> `shipped` em 2026-08-26). **O predicado desta lane continua ausente**: nenhuma linha da
> função consulta `stage_reviews` — medido em `origin/main`, zero ocorrências.
>
> **Não há absorção, e a distinção importa.** As duas lanes tocam a mesma função com
> **predicados disjuntos** — a l87 barra executor concorrente, esta barra review pendente.
> Fundi-las apagaria a partição que as duas pagaram para declarar, e escrever o fecho desta
> como *"terminal + pending"* morderia o resíduo sancionado da [[ADR-417]] D3. O que muda
> aqui é só o sítio de inserção e o rebase. A lane irmã é **terminal**, então a paralelização
> que a prosa desta lane descrevia deixou de existir — não há campo de frontmatter a mexer.
>
> A **U1** também mediu o agravante: o `resume_run` lê a contagem numa sessão e o flip
> acontece em outra — duas sessões, nenhuma atomicidade, TOCTOU por construção. E a
> [[ADR-417]] introduziu um **segundo ator** sobre o estado pausado, então aprovar-e-retomar
> e cancelar agora competem pelo mesmo run.

## O fato, medido no r8

`pipeline_service.resume_pipeline_run` (`:292`) chama `_flip_run_to_resuming`
(`:262`), cujo único predicado é `run.status != PipelineRunStatus.needs_review`.
**Zero consulta a `stage_reviews`.**

O predicado que importa — `count(StageReview.status == pending) > 0 →
ConflictError` — existe **apenas** em
`backend/app/application/pipeline_run/resume_run.py:21-33`, a camada HTTP.

E `backend/app/tasks/pipeline_task.py:1129-1132` **declara o invariante como se
fosse global**:

> *`StageReview` fica do lado do CONTROLE de propósito ([[ADR-404]]): `resume_run`
> só libera a retomada com zero reviews `pending`… falha silenciosa pior que a
> barulhenta.*

**A falha silenciosa é o estado corrente.** No DB de dogfood,
`stage_reviews ⋈ pipeline_runs` tem os pares: `(completed, approved) 8` ·
`(failed, approved) 4` · **`(completed, pending) 2`** · `(completed, edited) 1`.

Os dois `(completed, pending)` são o **r7 e o r8** — os dois últimos runs da skill
`pipeline-review`, que retoma pelo service. O r7 é o **baseline de comparação do
r8**: todo veredito de regressão daquela revisão foi medido contra um run que
completou sobre review não resolvida.

`docs/reference/runbooks/stuck_pipeline_runs.md:197` documenta o service como ação
operacional — o contorno não é acidente de um agente, é caminho documentado.

## O que a lane tem de decidir, não só mover

**Mover o predicado quebra a skill `pipeline-review`, e isso é o comportamento
desejado.** Ela retoma pelo service justamente para não precisar aprovar. Depois
do fix, ela **não vai conseguir** — e é assim que tem de ser: um run retido por
`review_reason` só deve completar depois que alguém decidiu.

Mas quebrar em silêncio troca um defeito por outro. O escopo inclui **dar à skill
uma ação explícita de aprovação** (ou de recusa registrada), senão o próximo
`pipeline-review` trava sem saber por quê e o operador volta a contornar — agora
por um caminho ainda menos visível.

**Segundo ponto de decisão: o fecho.** Hoje nada impede
`(completed, pending)` de nascer por outro caminho. Um predicado só na entrada
volta a ser guard de porta. `_finalize_run` recusar `completed` com
`StageReview.pending` do mesmo run é o que fecha a **classe**; sem isso a lane
fecha a instância.

**Terceiro: as 2 rows históricas.** Decida explicitamente — anotar, backfillar ou
deixar. Row que documenta um estado que o código passa a proibir vira armadilha
para quem consultar depois. Registre a escolha.

## Restrição

A ordem da [[ADR-404]] permanece: controle commita primeiro e sozinho; o
analítico depois, em sessão própria, fail-open. O predicado novo é **de
controle** e vive na mesma sessão da transição — é exatamente onde a ADR o quer.
Há hook de pre-commit (`Diagnóstico não divide sessão com transição de run`).

Cuidado com a compensação: `_dispatch_resume` já reverte `resuming → needs_review`
em falha de dispatch ([[ADR-359]] §2 — compensar é **reverter**, não marcar
`failed`). O predicado novo deve **recusar antes** de flipar o status, não flipar
e compensar depois.

## Critério de aceite

**Corretude** — `resume_pipeline_run` levanta com review `pending`, e o run
permanece `needs_review` (não vira `resuming` nem `failed`). Teste por entrada:
um pelo service, um pela rota HTTP.

**Completude** — o par `(completed, pending)` deixa de ser alcançável por
**qualquer** caminho. Teste de fecho em `_finalize_run`, não só de entrada.

> ⚠️ **O predicado é `(completed, pending)`, nunca "terminal + pending".** Registrado
> pela [[A40.l87]] em 2026-08-26: a [[ADR-417]] D3 sanciona `(cancelled, pending)` —
> quando alguém **descarta** uma pausa, as `StageReview` ficam `pending` de propósito,
> porque ninguém decidiu e ninguém vai decidir. Escrever o fecho como "terminal +
> pending" morde esse resíduo e as duas lanes passam a se refutar. Há teste em
> `backend/tests/test_needs_review_exit_door.py` provando que os dois pares convivem.

**Consistência** — o comentário de `pipeline_task.py:1129-1132` passa a descrever
o que o código faz. Hoje ele afirma cobertura que a medição refuta; se o fix não
alcançar todos os caminhos, o comentário é **corrigido para a verdade menor**, não
mantido na maior.

**Precisão** — o erro nomeia o que falta: qual stage, quantas reviews pendentes e
o que fazer. "Conflict" sozinho manda o operador para o mesmo contorno.

**Prova de fecho (predicado do r9)** — `SELECT` do par `(completed, pending)` não
cresce; e o próximo `pipeline-review` completa **com** aprovação registrada, não
por contorno.

## Delegação

`senior-cto` decide onde o predicado mora e se `_finalize_run` entra no escopo.
`sre-devops` revisa o runbook, que hoje ensina o contorno.

## Rastro

RV8-08 do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`, 2026-08-24) —
achado que a **própria revisão** produziu ao se apoiar no contorno. Medições
refeitas nesta lane.

## Fecho — 2026-08-27

**Corretude.** `resume_pipeline_run` levanta com conferência sem decisão e o run permanece
`needs_review` (nem `resuming`, nem `failed`), com `paused_at_stage` íntegro: a recusa é
**antes** do flip, então não há ação forward a compensar ([[ADR-359]] §2). Teste por
entrada: `test_resume_pelo_service_recusa_review_sem_decisao` (service) e
`test_resume_blocked_with_pending_reviews` + `test_resume_requires_no_pending_reviews`
(rota), estes dois reescritos para asserir o **desfecho** — 409 nomeando stage e review —
em vez de substring.

**Completude — e a rota da linha do §r8 estava incompleta em dois pontos.**

1. **`_finalize_run` não é o único escritor de `completed`.** `_mark_run_completed`
   (`pipeline_service.py`) grava direto, sem passar por ele, quando `_stages_after_paused`
   devolve `[]`. O **mecanismo** foi medido por execução: o par `(completed, pending)`
   nasce num salto. Ganhou guard próprio, que **reverte a pausa antes de levantar** —
   levantar sobre `resuming` + `celery_task_id IS NULL` entregaria o run ao ceifador de
   órfãos, que grava `failed`/`DISPATCH_UNCONFIRMED` sobre um dispatch que nunca foi
   tentado.
> **Correção de precisão — 2026-08-27, no closeout.** A redação original desta alínea
> dizia que o `[]` "acontece com o stage pausado sendo o último do `FULL_ORDER`
> (`review_finances_holistic`, 17 de 18)" e chamava isso de **medido**. O mecanismo foi
> medido; **essa rota específica, não** — e ela está **inerte hoje**. `_stages_after_paused`
> devolve `[]` para **quatro** entradas, medidas agora: o último do `FULL_ORDER`, um nome
> **legado** (`"E5"` → `[]`), um nome desconhecido, e `None`. Só **4 stages emitem bloco
> `validation`** e portanto podem pausar — `extract_baseline`, `extract_members`,
> `extract_irpf_full`, `extract_with_llm` —, todos na **cabeça** do `FULL_ORDER`; o
> `parecer_planejador` emite **zero**, então pausa natural no último stage não dispara.
> **As rotas vivas são as outras três** — `paused_at_stage` legado (a [[ADR-093]] mantém
> `STAGE_RENAME_MAP` e rows anteriores ao F9.4 existem), desconhecido, ou `NULL` (a
> [[A40.l27]] parou de zerar, rows anteriores não). Isso **justifica mais** o guard, não
> menos; o que não se sustentava era o adjetivo "medido" sobre a rota nomeada. Erro da
> mesma classe que esta lane existe para fechar: afirmação mais forte que a medição.

2. **`_finalize_run` recusar `completed` era a resposta errada.** Levantar ali aborta a
   task **depois** do trabalho feito, e o `on_failure` grava `failed` — converte "ninguém
   decidiu" em "morreu", a alternativa que a [[ADR-359]] §2 rejeitou. Ele **re-estaciona**
   a pausa, e só sobre desfecho que ENTREGA. `needs_review` está fora de
   `_POST_PROCESS_STATUSES`, então nenhum relatório nasce sobre output não conferido — de
   graça, sem tocar caller nenhum.

**O escopo é `(completed, pending)`, e há teste que o prova.** `DELIVERING_STATUSES` é
tupla **listada** (`completed`, `partial_failure`), nunca derivada de "terminal menos X".
`test_finalize_grava_failed_mesmo_com_review_pendente` é o que impede o próximo refactor de
reescrever o fecho como "terminal + pending" e morder o resíduo sancionado da [[ADR-417]]
D3. Mutação nos dois eixos: sem o guard, o teste de repark reprova; com o gate alargado
para `failed`, o teste de escopo reprova — e cada mutação reprova **só** o teste que a mede.

**O predicado é `NOT IN (approved, edited)`, não `== pending`.** Restritivo por default:
membro futuro do enum destravaria calado, o modo de falha que a [[ADR-417]] D3 evitou ao
recusar `dismissed`. `edited` destrava, e há teste.

**A cópia da camada HTTP foi substituída, não duplicada.** `resume_run.py` contava numa
`AsyncSession` enquanto `_flip_run_to_resuming` flipava numa `SyncSessionLocal` — TOCTOU
por construção, medido na U1 (PV9-29). O predicado passou para dentro da sessão do
`UPDATE`. Não há o falso-verde que a [[A40.l27]] pagou com o cancel: aquele use case tem
caminho próprio de flip, este só chama o service, e o 409 continua vindo da tradução do
`ValueError`.

**Consistência — eram cinco sítios, não um.** A afirmação de que "`resume_run` exige zero
reviews `pending`" estava em `pipeline_task.py`, no comentário que justifica a exclusão de
`StageReview` do `dev/check_diagnostic_session_isolation.py`, no teste desse gate, na
[[ADR-411]] D4 e na §r7 de [[PIPELINE-REVIEWS-active]] — além da própria [[ADR-404]] D2.

> **Correção — 2026-08-27, no closeout.** O #1771 corrigiu **quatro** dos cinco: a
> [[ADR-411]] D4 ficou de fora e seguiu publicando a formulação por camada. A frase de
> fecho dizia "os cinco passam a descrever o que o código faz" e era **falsa no momento em
> que foi escrita**. Corrigida no PR de closeout. O achado é da própria classe da lane —
> e apareceu no painel que eu mesmo escrevi. Isso **inverte** o custo
da alternativa que o §Critério oferecia: "corrigir o comentário para a verdade menor"
custaria cinco edits e enfraqueceria a razão de um gate; tornar o invariante verdadeiro
custou um. Os cinco passam a descrever o que o código faz.

**Precisão.** O erro nomeia quantas conferências, **quais** (stage + id de review) e as
**duas** saídas com a rota de cada uma, além de dizer que a retomada re-custa LLM e que não
se escreve no DB. Verificado ponta-a-ponta contra a API, não só em teste.

**A skill ganhou a saída, e a primeira execução real pagou.**
`.claude/skills/pipeline-review/scripts/resolve_pause.py` faz `--list`/`--approve`/`--edit`/
`--resume`/`--cancel --reason` pelo `ASGITransport` contra o app real — mesma autorização,
mesmas guardas, mesma telemetria `review_action`. Sem `--approve-all`: aprovar em massa sem
ler os `validation_issues` é aprovação cega, e quem não vai conferir tem `--cancel`.
Exercitado num harness sintético (nunca no dogfood): `--list` 200 → `--resume` **409** com
a mensagem precisa → `--approve` grava `approved` + `reviewed_at` → `--resume` flipa
`resuming` e, com o dispatch morto, **compensa de volta** para `needs_review` preservando
`paused_at_stage` → `--cancel` grava `cancelled_from_status='needs_review'`. A execução
achou três defeitos que revisão de código não pegaria: coluna `cost_usd` (o certo é
`cost_usd_cents`, int por [[ADR-090]]), corpo não-JSON do 500 estourando `resp.json()`, e o
`--list` indexando o corpo às cegas — mostrava `TypeError` no lugar do 403.

**As 2 rows históricas: ANOTADAS, não backfilladas.** Runs
`33514dc4-115b-45fe-8976-03e25ba971c8` (r7, `extract_with_llm`, review `064426fd`) e
`d0f6260a-10f5-4b9c-82d0-dcf36650b995` (r8, `analyze_finances`, review `bdbcdf63`).
`approved` forjaria uma decisão humana que não houve — mesma doutrina que a [[ADR-417]] D3
usou para recusar `dismissed` — e a rota sancionada recusa por desenho (`action_review` não
aceita ação sobre run terminal), então o backfill só sairia por `UPDATE` cru, que o runbook
proíbe. São a evidência do RV8-08, e uma é o baseline da outra.

**Prova de fecho.** `dev/check_par_completed_pending.py` mede **quais**, não quantos: os 2
ids ficam congelados e qualquer id novo reprova. Contador diria "2, ok" com uma row nova
entrando e outra saindo por `ON DELETE CASCADE`. Banco sem runs é **WARN, não PASS** — gate
fechando sobre ausência de dado é o modo de falha do gate Fernet. Os três ramos verificados
contra dados reais (PASS no dogfood, WARN em banco vazio, FAIL com par sintético). Tem CLI
própria de propósito: o `preflight_unified_review` que o consome **não é citado por nenhuma
`SKILL.md`**, e predicado que só roda dentro da rodada unificada morre quando a rodada para
de acontecer — mesma classe do `nightly` desabilitado.

## Aberto — 2026-08-27

1. **`resume_run` responde 500 em falha de dispatch, não 409.** Medido no harness:
   `PipelineDispatchError` é `RuntimeError`, e o use case só traduz `ValueError`. A
   **compensação está correta** (o run volta a `needs_review` com `paused_at_stage`
   intacto), mas o operador recebe `Internal Server Error` em texto puro. É superfície da
   [[ADR-359]], não deste predicado — não expandi o escopo. Dono: `sre-devops`.
2. **`_finalize_run` continua `db.get` + atribuição**, sem `UPDATE ... WHERE status=<esperado>`
   + `rowcount` — é o único escritor de status do repo sem essa forma. Com dois executores
   no mesmo run, uma pausa commitada por `_commit_needs_review_pause` entre o `SELECT` do
   guard e a atribuição é sobrescrita. **Plausível, não confirmado**: `reject_on_worker_lost`
   implica worker morto, não vivo em paralelo. Retomar com evidência de duplo-dispatch.
   Dono: `data-engineer`.
3. **`_mark_run_started` continua flipando `needs_review` → `running` sem consultar nada.**
   O fecho contém o **desfecho** (repark), não o **desperdício**: cada redelivery re-executa
   a cauda e re-paga LLM antes de re-estacionar. O discriminante existe e não é usado —
   resume legítimo chega em `resuming`, redelivery-sobre-pausa chega em `needs_review`.
   Mexer nisso toca crash-recovery; lane própria. Dono: `senior-cto`.
4. **Índice `stage_reviews (pipeline_run_id, status)` não foi criado.** `_finalize_run`
   ganhou uma query por run em caminho quente sob transação. `pipeline_run_id` já tem
   índice; o composto não existe e em SQLite local não se mede. Conferir o plano em
   Postgres. Dono: `data-engineer`.
