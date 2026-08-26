---
id: A40.l87
type: lane
title: "A pausa não tem porta de saída, e o botão que o produto já oferece devolve 409 há quatro meses"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
priority: P1
branch_slug: needs-review-porta-de-saida
ship_pr: 1743
ship_date: "2026-08-26"
adrs:
  - "[[ADR-417]]"
  - "[[ADR-359]]"
  - "[[ADR-411]]"
depends_on: []
parallel_with:
  - "[[A40.l84]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
  - area/frontend
---

# A40.l87 — Porta de saída da pausa

> ✅ **Entregue em 2 PRs, 2026-08-26:** **#1740** (a porta · `f9e13def`) e **#1743**
> (a pré-condição e o estado gravado). **Canônica:** [[ADR-417]] (`Decidido`).
> Aberta 2026-08-26 no desbloqueio do preflight da [[runbook-unified-certify-review]].
> Admissão retro-registrada 2026-08-26 (§Fora do sprint), precedente [[A40.l46]].

## O fato, medido

`PipelineRunStatus.needs_review` é o **único estado não-terminal sem saída que
não seja completar o run**. `resume` roda todos os stages a jusante e paga LLM;
`cancel` recusa, porque `needs_review` está fora de `CANCELLABLE_STATUSES`.

O comentário em `dispatch_contract.py` justifica a exclusão dizendo que
*"cancelá-la é decisão de produto, não de operação"* — **uma decisão que já
tinha sido tomada, três meses antes, na única superfície que o usuário toca**:

- `NeedsReviewCard.tsx:63` renderiza **"Cancelar execução"**; `page.tsx:442` o
  monta exatamente em `activeRun.status === "needs_review"`.
- O clique cai em 409 `"Execução não pode ser cancelada (status: needs_review)"`
  e vira banner de erro **com o nome cru do status**.
- O card existe desde **2026-04-21**; o comentário entrou em **2026-08-07**.

O confirm (`page.tsx:490`) diz *"interrompido ao final da etapa em execução"* —
numa pausa não há etapa executando. A copy está errada mesmo se a API passasse.

### Dois falsos-verdes pinam a crença

`frontend/tests/components/NeedsReviewCard.test.tsx:71` assere apenas
`expect(onCancel).toHaveBeenCalledOnce()` — fiação, nunca desfecho: passa no CI
e falha em produção. `backend/tests/test_detect_undispatched_runs.py:243`
assere literalmente `needs_review not in CANCELLABLE_STATUSES`.

### O buraco é maior que orfanamento: é executor duplo

`_flip_run_to_resuming` (`pipeline_service.py:257`) checa **só** que *este* run
é `needs_review`; zero consulta a run ativo. A pausa é invisível ao índice
parcial `ux_pipeline_runs_ws_active` (`IN ('pending','running')`) **e** ao
fast-path `_check_no_active_run`. Caminho: pausa P → trigger N passa → aprovar
as reviews de P → resume P → **dois workers escrevendo artefatos no mesmo
workspace**. É a falha que a [[A40.l27]] nomeou para `resuming`.

### O que forçou

Dois runs do dogfood parados em `needs_review` no `analyze_finances` desde
2026-08-25 bloquearam o preflight da rodada unificada (check `run-em-voo`).
A remediação escrita dizia *"retome … ou marque terminal"* — e "marque
terminal" não existia. Resolveu-se por escrita ORM direta, contornando um guard
deliberado. Mesma classe do contorno que a [[A40.l84]] nomeia no runbook.

## Escopo — dois PRs, ordem não-invertível

**PR1 — a porta.** `needs_review` em `CANCELLABLE_STATUSES` + comentário
reescrito · `cancel_run` honra o `bool` de `cancel_pipeline_run` (hoje descarta
e responde sucesso sobre no-op) · `AuditAction` nova registrando **quem**
abandonou · guarda de terminalidade em `action_review` · tabela exaustiva de
saída por estado + teste de endpoint por estado escapável · copy do card, do
confirm e da linha de histórico · preflight e runbook param de ensinar o ORM.

**PR2 — a pré-condição e o estado gravado.** `needs_review` no fast-path
`_check_no_active_run`, com 409 que nomeia a saída · guarda de run ativo em
`_flip_run_to_resuming` (é ela, não o índice, que fecha o executor duplo) ·
**coluna `pipeline_runs.cancelled_from_status`** + writer + os dois leitores
([[ADR-417]] D4, reescrito em 2026-08-26) · card da pausa no **carregamento** da
página, não só ao vivo · gatilho `data-engineer` (migração Alembic).

**PR2 nunca antes de PR1.** Bloquear o trigger sem porta converte "pausa" em
"workspace tijolado" — o incidente de origem da [[ADR-359]], agora enforçado
por código.

## Restrição — o índice parcial não muda

Precedente literal: a [[A40.l27]] pôs `resuming` no fast-path e **não** no
índice. Ver [[ADR-417]] D5 §Deferimento datado (dono `data-engineer`), que
carrega a armadilha: `CREATE UNIQUE INDEX` sobre o predicado alargado **falha
hoje** no dogfood, que tem 2+ linhas nele.

## Partição de arquivos vs. [[A40.l84]] (`open`, P0, paralela)

| Esta lane | [[A40.l84]] |
|---|---|
| `dispatch_contract.py` | `resume_run.py` |
| `cancel_run.py` · `action_review.py` | `pipeline_service.py::_flip_run_to_resuming` |
| `api/pipeline.py` (rota de cancel) | `pipeline_task.py::_finalize_run` |
| `NeedsReviewCard.tsx` · `page.tsx` · `HistoryRow.tsx` | runbook `stuck_pipeline_runs.md` §resume |

**Sobreposição declarada:** as duas tocam `pipeline_service.py` e o runbook.
A l84 muda `_flip_run_to_resuming`; o PR2 desta lane acrescenta ali a guarda de
run ativo. Quem chegar depois rebaseia — não são o mesmo predicado.

> **Colisão a evitar, e é a razão de as duas serem `parallel_with`:** o
> predicado de fecho da l84 é **`(completed, pending)`**, nunca *"terminal +
> pending"*. Esta lane cria `(cancelled, pending)` como **resíduo sancionado**
> ([[ADR-417]] D3). Escrito como "terminal", morde o resíduo e as duas se
> refutam.

## Critério de aceite

**Corretude** — `POST /runs/{id}/cancel` sobre run `needs_review` responde 200 e
o run fica `cancelled`. Teste por **duas entradas** (use case *e* rota HTTP): a
guarda é duplicada, e alargar só o service deixa o endpoint em 409 com o teste
de service verde — verde-falso literal, documentado em `cancel_run.py:16-18`.

**Botão morto** — teste de frontend que **falha hoje** (o card chama cancel e
recebe 409) e passa depois. Escrito antes do fix.

**Completude da classe** — tabela exaustiva sobre `PipelineRunStatus`: membro
novo falha **por ausência**. A asserção de `test_detect_undispatched_runs.py:243`
é apagada e substituída por ela. Teste de tabela não basta sozinho ([[A40.l27]]):
acompanha um teste de **endpoint** por estado manualmente escapável.

**Consistência** — o comentário de `dispatch_contract.py` passa a descrever o
que o código faz. Enquanto ele afirmar a política contrária, todo agente que
abrir o arquivo lê "não mexa" — é a patologia RV8-08 da [[A40.l84]].

**Precisão** — o histórico distingue run **descartado** de run **interrompido**,
por derivação `(cancelled, paused_at_stage IS NOT NULL)`, e o discriminador tem
**leitor no mesmo PR** (`RunContextLine`). Sem leitor, é falso-verde da classe
que a [[A40.l81]] fechou.

**Não-regressão da l84** — teste provando que o predicado `(completed, pending)`
**não** morde `(cancelled, pending)`. Nenhuma `StageReview` é apagada nem muda
de status.

**Prova de fecho** — reproduzir 2026-08-25: run pausado ⇒ preflight `run-em-voo`
em FAIL ⇒ resolver **por chamada de API, sem nenhuma escrita direta no DB** ⇒
PASS. É o que prova que a porta é **usável**, não apenas existente; as duas
resoluções anteriores exigiram ORM.

**Concluído** — PR1 e PR2 mergeados em `main` com CI verde. A [[ADR-417]] flippa
a `Decidido` no merge do **PR2**, não do PR1: até o trigger recusar, a decisão
está pela metade.

## Registro de execução

**PR1 entregue 2026-08-26** — commit de merge `f9e13def` (#1740), em 4 commits (docs ·
backend · frontend+preflight · correção do D4). Os SHAs pré-merge **não** são ancestrais
de `main`: a branch foi rebaseada e o merge é squash, então `git show` deles falha em
clone novo. O par auditável é `(#1740, f9e13def)`.

### Cinco asserções pinavam a crença errada, não duas

O enunciado nomeava duas. A implementação achou **cinco**, e todas passavam
enquanto o botão devolvia 409 em produção:

| Arquivo | O que pinava |
|---|---|
| `test_detect_undispatched_runs.py:243` | `needs_review not in CANCELLABLE_STATUSES` |
| `test_detect_undispatched_runs.py` §`nao_e_cancelavel_nem_colhido` | `cancel_pipeline_run(...) is False` |
| `NeedsReviewCard.test.tsx` §fiação | `expect(onCancel).toHaveBeenCalledOnce()` — nunca o desfecho |
| `NeedsReviewCard.test.tsx` §regressão ADR-158 | botão `/cancelar execução/i` presente |
| `HistoryRow` (ausência) | nenhuma cobertura do par `(cancelled, paused_at_stage)` |

Nenhuma foi apagada: as quatro primeiras foram **substituídas** com o registro de
por que existiam. Prova de mutação: tirar `needs_review` da tupla derruba 6
testes; tirar a guarda de terminalidade derruba 1 **com `review_action` emitido e
HTTP 200** no log; devolver o rótulo antigo derruba 2 no frontend.

**Snapshot OpenAPI inalterado** — é o que prova que D2 não alargou a superfície da
API. Se um dia produzir diff, alguém escorregou para a opção (a).

### Achado novo: a pausa some da tela ao recarregar

Medido durante a implementação, **não estava no enunciado**. O card só renderiza
ao vivo: `handleWSEvent` (`page.tsx:154`) faz `setActiveRun(updated)` incondicional
quando chega o evento `needs_review`. Mas no **carregamento** da página
(`page.tsx:241`) o `activeRun` sai de `ACTIVE_STATUSES`, que **não inclui**
`needs_review` — então quem recarrega perde o card, vê o `TriggerCard` convidando
a disparar de novo, e a pausa fica acessível só pelo link "Revisar" da linha de
histórico.

É a rampa de orfanamento inteira numa tela: a superfície que pede a decisão some,
e a que a contradiz aparece. **Dono: PR2 desta lane** — o 409 do fast-path é
exatamente o que fecha isso, e o card na carga é o par de leitura dele.

### O D4 foi refutado por medição durante a execução, e reescrito antes do merge

A 1ª redação do D4 dizia que `(cancelled, paused_at_stage IS NOT NULL)` discriminava
descarte de interrupção, "zero migração". **Não discrimina:** ninguém nunca zera
`paused_at_stage` — `rg 'paused_at_stage *= *None' backend/app` devolve zero, e a
[[A40.l27]] o preserva **de propósito** no resume, por ser "a única cópia durável do
ponto de retomada". Logo o par também vale para quem pausou → conferiu → **retomou** →
foi interrompido, que é interrupção.

Erro de grão, e o mesmo que o D3 rejeita: resíduo de um momento passado usado como
estado no momento terminal.

**Linha de corte no PR1** (decisão `senior-cto`, escalação de 1 rodada): *o que lê
status vivo fica, o que lê resíduo sai.* Ficou `cancelCopyFor` (lê `status` no instante
do clique) e o `detail` da rota (lê antes do flip) — corretos por construção. Saíram
`discarded_at_review`, `foiDescartadoNaConferencia` e os 2 call-sites do `HistoryRow`.
Run `cancelled` volta a ficar **sem linha de contexto**, que é a paridade com `main`:
zero rótulo errado embarcado, zero regressão.

Isso **não** viola o critério "discriminador com leitor no mesmo PR" do
`product-manager`: sem discriminador não há órfão. O critério volta a morder no PR2,
onde coluna + writer + os dois leitores entram juntos.

A ADR foi **reescrita in place, não emendada** — `Proposto` nunca vigorou, e emendar
fabricaria uma história que não aconteceu. Se estivesse `Decidido` em `main`, a resposta
inverteria. A §"Alternativa considerada e refutada" da [[ADR-417]] carrega os três fatos
medidos, mais duas outras derivações testadas e recusadas (última linha de
`pipeline_stage_logs`; `AuditLog` como projeção).

**Pin de regressão, entregue no PR2:** `test_retomado_e_depois_interrompido_nao_le_como_descarte`
— teste-antes-do-fix, que mora no PR que corrige, não no que remove. O
`xfail(strict=True)` do PR1 saiu por ter passado a passar, que é como foi desenhado.

### O que o PR1 deliberadamente não fez

> Registro histórico do recorte do PR1. **Os três primeiros itens foram entregues pelo
> PR2 (#1743)**; só o índice parcial segue deferido.

- ~~Guarda de run ativo em `_flip_run_to_resuming` (executor duplo)~~ — ✅ #1743.
- ~~`needs_review` no fast-path `_check_no_active_run`~~ — ✅ #1743.
- ~~Coluna `cancelled_from_status` e os leitores do discriminador~~ — ✅ #1743.
- Índice parcial — **segue deferido**: [[ADR-417]] D5 §Deferimento, dono `data-engineer`.
- `action_review` segue acima do teto de 20 linhas do P1: dívida **preexistente**,
  não ampliada (o guard saiu para `_require_run_aberto`).

## Delegação

Co-design feito 2026-08-26 (`product-manager` + `senior-cto`, convergentes em
D1/D2/D3). `data-engineer` é gatilho obrigatório **se** o §Deferimento de D5
(índice parcial) for retomado — não antes.
