---
id: A40.l21
type: lane
title: "Leitores tolerantes a partial_failure: run que produziu relatório para de ser pintado como falha"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1232
ship_date: "2026-08-06"
priority: P0
branch_slug: a40-l21-leitores-tolerantes-partial-failure
adrs:
  - "[[ADR-357]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/frontend
---

# A40.l21 — `leitores-tolerantes-partial-failure`

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]), mas **shipa antes da
> [[A40.l18]]** — disciplina expand/contract: leitor tolerante antes de o writer
> emitir. Risco zero, porque hoje o status é **inalcançável em produção**.

## Problema

`partial_failure` já existe no union type
([`frontend/src/lib/api/pipeline.ts`](../../../../frontend/src/lib/api/pipeline.ts))
e já tem rótulo "Parcial" com variante `warning` em
[`frontend/src/lib/format.ts`](../../../../frontend/src/lib/format.ts) — mas a
lógica o trata como **falha** em **7** read sites (9 hits de `partial_failure` em
`frontend/src/` menos as 2 declarações acima):

- `frontend/src/lib/pipelinePhases.ts` — `isFailed: runStatus === "failed" || runStatus === "partial_failure"`. (Descrição corrigida na execução: não pinta de vermelho — **veta** o ramo `completed` das 4 fases, deixando o stepper todo cinza. Ver §Correções de premissa.)
- `frontend/src/app/(app)/pipeline/page.tsx` (3 sites) — `lastFailedRun` levanta banner de falha para run que produziu relatório.
- `frontend/src/app/(app)/pipeline/_components/HistoryRow.tsx` (2 sites)
- `frontend/src/app/(app)/pipeline/_components/ActiveRunCard.tsx` — `bg-loss` onde deveria ser `bg-warning`. (Este site e o anterior são **inalcançáveis pela página** mesmo pós-[[A40.l18]]: `ActiveRunCard` só renderiza sob `ACTIVE_STATUSES`. Corrigidos por tolerância, provados por teste direto — teste de página com fixture parcial passaria verde sem tocá-los.)

E o **toast + redirect** disparam só em `completed`: run parcial hoje não emite
toast nenhum e **abandona o usuário em `/pipeline`** sem dizer que existe
relatório.

## Decisão

| Status | Rótulo | Variante | Ação primária | Contexto |
| --- | --- | --- | --- | --- |
| `completed` | Concluído | success | Ver relatório | — |
| `partial_failure` | **Concluído com ressalva** | warning | **Ver relatório** | "Relatório gerado. O parecer do planejador não foi publicado." |
| `needs_review` | Aguardando revisão | warning | Revisar | "Revisão pendente" |
| `failed` | Falhou | error | Reprocessar | "Falhou em {etapa}" |

Renomear "Parcial" → **"Concluído com ressalva"**: "Parcial" responde *"quanto
rodou?"*; a pergunta do usuário é *"eu tenho relatório?"*. Ação primária **igual**
à de `completed`, porque o resultado é o mesmo objeto.

> **Delta 2026-08-06 (o que shipou difere da tabela em dois pontos).** A tabela é
> o esboço pré-execução; o código a refinou e é ele que vale:
>
> - **Coluna Contexto.** A frase fixa *"Relatório gerado. O parecer do planejador
>   não foi publicado."* mentiria nos outros 2 add-ons degradáveis
>   ([[ADR-357]] §1). Shipou **derivada da etapa** em
>   `frontend/src/app/(app)/pipeline/_components/degradedStage.ts`:
>   `review_finances_holistic` → *"Relatório gerado, sem o parecer do
>   planejador."* · `generate_narratives` → *"…sem as análises e comentários."* ·
>   `validate_cross` → *"…sem a conferência de consistência dos números."* ·
>   2+ degradadas → *"…sem algumas das análises finais."* · fallback →
>   *"…com uma etapa final incompleta."*
> - **A coluna lista só a ação PRIMÁRIA.** `failed` e `partial_failure` carregam
>   também a secundária direcionada "Reprocessar a partir de {etapa}"
>   (`from_stage`, sancionada por [[ADR-357]] §8) — afordância **pré-existente**
>   do `FailedRunCard` que a l21 herdou e **estreitou**: no caminho degradado o
>   re-run integral saiu, sobrou só o direcionado. A l21 não criou decisão de
>   custo nova; reduziu a exposição.
>
> Superfície nova desta lane, para paridade com os paths da §Problema:
> `frontend/src/app/(app)/pipeline/_components/PartialRunBanner.tsx` e
> [`frontend/src/lib/pipelineRunOutcome.ts`](../../../../frontend/src/lib/pipelineRunOutcome.ts).

`partial_failure` e `needs_review` são ambos `warning` — correto, mesma
severidade. Diferencie por ícone e ação, não por cor (forma + cor + texto).

`publish_run_completed`/`publish_run_failed` passam a receber o status real como
parâmetro, em vez de ganhar um terceiro evento.

**Amarra de dead code:** se a [[A40.l18]] escorregar >1 sprint, **reverta esta
lane** — é dead code pelos nossos próprios critérios. O PR do writer referencia
o número deste PR.

## Correções de premissa medidas na execução (2026-08-05)

O recon de execução varreu `frontend/src/` inteiro e achou **24 sites
materiais**, não 7. Os 7 da §Problema conferem (`rg "partial_failure"` dá 9
hits menos 2 declarações), mas são o subconjunto que cita o literal. Três
correções que mudam o trabalho, não só a contagem:

1. **O site nº 1 está descrito errado.** `pipelinePhases.ts:198 isFailed` não
   pinta a fase de vermelho: o vermelho vem de `ctx.failedPhaseId`, que exige
   um `stage_log` com status `failed` — e a [[ADR-357]] §3 decide que a etapa
   degradada grava `degraded`. O que `isFailed` faz é **vetar** o ramo
   `completed` das 4 fases, que caem em `runStatus === "completed"` e viram
   `pending`: stepper todo cinza, progresso travado. Fix diferente — exige
   mexer também na linha do atalho de fase sem logs e no conjunto de etapas
   terminadas.
2. **Classe de omissão irmã, não enumerada.** Seis sites perguntam "este run
   entregou?" com `=== "completed"` e por isso **excluem** o run parcial:
   toast/redirect do WS, toast/redirect do polling, banner de free tier
   (casava um `completed` mais antigo e citava o `runId` errado), o slot
   transitório da página, o atalho de fase sem logs, e o loop do
   `golden-path.spec.ts`. Fechada com o predicado `isDeliveredRun`.
3. **`degraded` (stage) também é vocabulário novo da [[ADR-357]].** Leitor cego
   a ele mostraria a string crua com ícone `?` e nunca fecharia a fase final.
   Entra nesta lane pela mesma disciplina expand/contract.

**Falso-verde evitado no critério original:** 2 dos 7 sites
(`pipelinePhases.ts:198` e `ActiveRunCard.tsx:107`) só rodam dentro do
`ActiveRunCard`, que a página renderiza apenas sob
`ACTIVE_STATUSES = {pending, running, resuming}` — um teste de página com
fixture parcial passa verde **sem tocá-los**. Precisam de teste direto de
unidade.

**Limite declarado do gate axe:** em jsdom o axe classifica `color-contrast`
como `incomplete`, nunca `violations`, e o helper do repo lê só `violations`.
O par light/dark prova estrutura ARIA/DOM, **não** contraste; contraste real
exige Playwright/Lighthouse.

## Critério de aceite

- `pipelinePhases.isFailed` **não** contém `partial_failure`, e
  `stageLogs.find(status === "failed")` **continua cego** a `degraded`
  (as duas metades, provadas por mutação).
- Toast + redirect disparam em `partial_failure`, nos **dois** caminhos (WS e
  polling), e o desfecho vem do `status` do run — não do nome do evento.
- Fixture `makePartialRun()` (`status`, `report_id` populado e
  `failed_at_stage: null` juntos) ⇒ nenhum site renderiza afordância de falha
  **e** a afordância positiva "Ver relatório" é asserida.
- `cd frontend && npm test -- --run` verde; `tsc --noEmit` verde.
- axe-core 0 critical/serious no histórico com run parcial, light e dark.
- `make update-openapi-snapshot` com **diff vazio** — `partial_failure` já
  está publicado; diff ⇒ [[ADR-357]] §3 foi violada.

## Amarra de reversão (2026-08-05)

O gatilho já é computável e mora no
[§Gate de saída da [[MOC-sprint-a40]]](../_README.md): se a [[A40.l18]] não
tiver mergeado até `date_target` (`2026-08-17`), esta lane é revertida — os
read sites são dead code enquanto nenhum writer emite o status. **Dono:** quem
fizer o pickup seguinte após a data. Esta seção não cria mecanismo novo (seria
segunda fonte de verdade); registra a **receita**, que faltava:

- `git revert c8239386` (squash de #1232) — PR único, frontend-only + 2 testes de
  backend (um pina campo já emitido, outro é tripwire negativo).
- Não há PR pareado a reverter junto.

> **Delta 2026-08-06 (pós-#1242): o comando já não aplica limpo.** `4620cc04`
> (PR1 da [[A40.l18]]) apagou o tripwire e o substituiu pelo gate permanente
> `backend/tests/test_pipeline_status_enum_parity.py`. `git revert c8239386`
> agora sai com **EXIT=1 e 6 conflitos**, dos quais **um só é código**:
>
> - `backend/tests/test_events.py` — o lado do revert é vazio. Resolva apagando
>   `test_run_level_event_carries_status`, **ou** mantenha-o conscientemente como
>   pin do campo `status` que a l18 ainda vai consumir. As duas resoluções deixam
>   a suíte verde.
> - `docs/_MOC/_generated/{DOC_STATS,INDEX,PLAN_PROGRESS,SPRINT_CURRENT}.md` —
>   regerar com `python3 dev/build_doc_index.py`, não resolver à mão.
> - esta própria lane — manter HEAD.
>
> O inventário "2 testes de backend" acima descreve `c8239386`, não `main`: em
> `main` resta 1. **"Não há PR pareado" segue válido** — o PR1 da [[A40.l20]] não
> mergeou, e o #1242 (membro de enum inerte + gate de paridade) se sustenta
> sozinho.

**"Risco zero" é sobre o status novo, não sobre o PR inteiro** (correção de
2026-08-05). O PR carrega 5 mudanças de UX em statuses **vivos**, que o revert
também desfaz — enumeradas aqui porque um revert cego as perderia em silêncio:

1. "Ver relatório" volta a ser hover-only em todo run com `report_id` (inclui
   `completed`) — invisível em toque e no foco por teclado.
2. Metadados do histórico ("N etapa(s)", duração) voltam a aparecer abaixo de
   520px, onde sobrepõem o bloco da direita.
3. O `focus-within` + `pointer-events-none` do cluster de retry some — volta o
   alvo clicável invisível.
4. Copy dos toasts de `failed`/`cancelled` volta a "Pipeline falhou" /
   "Pipeline cancelado" (jargão vedado pelo COPY_GUIDELINES §6.3).
5. O caminho de polling volta a **não** anunciar `failed`/`cancelled` — quem
   está com WebSocket caído fica sem aviso nenhum.

Se o revert acontecer, re-landar os 5 em PR próprio.

## Pré-condições que este PR impõe à [[A40.l18]]

O leitor passou a depender de duas coisas que o writer precisa honrar:

1. **O call-site de `_finalize_run` tem de passar o status real** ao helper
   run-level. Assinatura com default (`status: str = "completed"`) não basta:
   `test_run_level_event_carries_status` chama o publisher sem argumento e
   continuaria verde. O gate é um teste **no call-site**, não no publisher.
2. **A etapa degradada tem de gravar `stage_log.status == "degraded"`** — o
   leitor casa a string exata para a copy da lacuna e para o reprocessamento
   direcionado. Gravar `skipped` ou `failed` degrada em silêncio (com `failed`,
   volta a pintar a fase de vermelho). Tripwire negativo em
   `backend/tests/test_events.py::test_degraded_stage_status_ainda_nao_existe`
   fica vermelho no PR que criar o membro do enum.

   > **Cumprido em 2026-08-06 (#1242, PR1 da [[A40.l18]]).** O tripwire ficou
   > vermelho, os 3 read sites foram reconferidos (já casam `degraded`) e o teste
   > se auto-deletou como previsto. No lugar dele, gate **permanente** de
   > paridade Python↔TS em `backend/tests/test_pipeline_status_enum_parity.py`.
   > A cláusula imperativa acima **continua valendo** para o PR2 (o writer), que
   > ainda não começou: quem grava o `stage_log` é ele.

**Não coberto:** se a [[A40.l18]] inventar um nome de evento novo apesar da
[[ADR-357]], `usePipelineWS.TERMINAL_EVENTS` não casa, `onRunFinished` nunca
dispara e a página gira para sempre num run terminado. Mudar aquele conjunto
para um predicado por status foi avaliado e recusado neste PR: altera semântica
de fechamento de socket para todos os runs, em troca de zero benefício
alcançável hoje.

**Hand-off para a [[A40.l22]]:** a lista em `/reports`
(`frontend/src/app/(app)/reports/page.tsx`) não tem indicador de degradação
nenhum — e é para lá que o usuário é redirecionado. A l22 é a dona.

Deliberadamente **fora** desta lane: estados de degradação dentro do relatório
e no PDF ([[A40.l22]]), e a UI de "gerado e retido" ([[A40.l20]]).
