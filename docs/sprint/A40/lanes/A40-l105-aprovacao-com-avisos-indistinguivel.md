---
id: A40.l105
type: lane
title: "Aprovação-com-avisos é indistinguível de nunca-ter-pausado no desfecho do run, e é o desfecho que alimenta o banner de qualidade"
sprint: A40
status: shipped
ship_pr: 1984
ship_date: "2026-09-02"
priority: P2
branch_slug: a40-l105-aprovacao-com-avisos-indistinguivel
owner: sre-devops
depends_on: []
adrs: ["[[ADR-404]]"]
tags: [type/lane, sprint/a40, status/shipped, priority/p2, area/pipeline]
---

# A40.l105 — `aprovacao-com-avisos-indistinguivel`

> **Origem:** `PV12-03` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).

## O defeito

`backend/app/services/report_run_outcome.py` — `_runs_with_degraded_stage` filtra
`status == 'degraded'` **e nada mais**. Um run que **pausou** em conferência, foi
aprovado com avisos e retomou sai `complete`, byte-idêntico a um run que nunca pausou.
No `U4`: 6 avisos, 0 erros, pausa aprovada — desfecho `complete`.

## O que o cético rebaixou, e por que a lane sobrevive assim mesmo

O enunciado original dizia que o banner **afirma limpo** no PDF que circula fora de casa.
**Isso é falso neste relatório:** a `CleanBar` só é alcançada depois de
`if (signals.count > 0) return <SignalsAlert/>`, e os **5** documentos em revisão deste
workspace entram nessa contagem — a barra "sem pendências" **não renderiza**.

**O defeito é do predicado, não do sintoma de hoje.** Ele depende de um segundo sinal
(documentos em revisão) para não mentir; num workspace com zero documentos pendentes e uma
pausa aprovada com avisos, a `CleanBar` renderiza.

## Critério de aceite

- [x] O desfecho distingue `nunca pausou` de `pausou e foi aprovado com avisos`.
- [x] **Controle positivo:** montar o banner com `runOutcome='complete'`, **zero**
      documentos em revisão e uma pausa aprovada com avisos. Se a `CleanBar` renderizar
      hoje, a severidade sobe; se algum outro sinal a segurar, permanece contingente e a
      lane declara isso.

## O controle rodou, e a severidade SOBE

O controle tem duas metades, e a pausa **não é input do frontend** — esse é o achado.

**Metade backend (medida, sonda descartada).** Run `completed`, `paused_at_stage` setado,
`StageReview` `approved` com 6 issues `severity: warning`: `run_outcomes_for` devolvia
`ReportRunOutcome.complete`. O defeito procede exatamente como enunciado.

**Metade frontend (já coberta, `ReportDataQualityBanner.test.tsx`).** Payload sem sinal do
E5, `mockNeedsReview.count = 0`, `runOutcome="complete"` ⇒ `data-quality-clean` no
documento, com o texto "sem pendências". **Nada mais a segura.** A pausa não tem canal na
UI: `computeDataQualitySignals` não a lê, `countActiveSignals` não a conta, e
`mayAssertCleanQuality` é o único gate — que recebia `complete`.

Logo o defeito **não é contingente** no segundo sinal. A dependência que o cético
levantou é do *workspace da U4* (5 documentos em revisão), não do mecanismo: bastam zero
documentos pendentes e a afirmação falsa sai no PDF. A severidade sobe.

## A correção

`_outcome` ganha um terceiro termo, na mesma polaridade positiva dos outros dois ("o run
entregou tudo que ia entregar?"): `paused_at_stage is not None ⇒ with_gap`.

**Por que a pausa, e não a decisão da conferência.** `StageReview.status` custaria uma 3ª
query e discriminaria pior: `edited` também publica artefato que o pipeline não produziu
sozinho, e `validation_issues` é fail-open — fica `NULL` quando a projeção falha
([[ADR-165]] onda 2) —, então chavear nele calaria justamente o caso em que se sabe menos.
`paused_at_stage` é a única cópia durável do fato, nunca é zerada e é preservada de
propósito no `_flip_run_to_resuming` ([[ADR-417]] D4).

**Assimetria que decide o corte conservador:** errar para `with_gap` custa SILÊNCIO — a
barra some, nenhum alerta falso aparece, porque `runOutcome` de propósito não entra no
`count` ([[ADR-357]] · [[A40.l18]]). Errar para `complete` custa uma AFIRMAÇÃO falsa num
PDF que circula com cônjuge e contador.

## Sem ADR nova

O predicado de `ReportRunOutcome` não é definido em ADR — ele mora no docstring de
`backend/app/services/report_run_outcome.py`, que cita a [[ADR-357]] apenas pelo
vocabulário de `degraded`. Adicionar um termo **conforme** à polaridade positiva já
decidida ali não reabre decisão, e a lane é P2. O *porquê* do termo ficou no comentário
co-localizado com o enforcer ([[ADR-143]]).

## Entregue

- `backend/app/services/report_run_outcome.py` — 3º termo em `_outcome`; `_statuses_for`
  passa a devolver `(status, pausou)` e lê `paused_at_stage` na **mesma** query (segue em
  2 queries no total, nunca uma por relatório).
- `backend/tests/test_report_run_outcome.py` — 3 testes novos: a pausa aprovada não
  autoriza; o predicado não depende da tabela de reviews; e a **contra-prova** de que um
  run sem pausa segue autorizando (sem ela, `paused is not None` passaria constante).

## Fecho (closeout 2026-09-02 · #1984)

**CI verde no merge `30ae1a69`:** `All checks green`, **Backend tests** (7m34s) e
**Pipeline tests** (3m29s).

**O falso-verde do processo, registrado porque quase passou.** `pytest … | tail` devolve
o status do **`tail`**, não do pytest: o primeiro "exit 0" desta lane não provava nada, e
duas tentativas seguintes morreram a ~99% no limite da task de background. Verde só vale
com o exit code do pytest capturado.

**As 8 falhas locais da metade B são PRÉ-EXISTENTES** —
`test_category_cache_observability.py` (7) + `test_audit.py` (1). A/B contra `origin/main`
reproduz **exatamente as mesmas 8**, e o CI do #1984 passou `Backend tests`. Fica escrito
para ninguém as creditar a este PR. O A/B **não era formalidade**:
`test_report_run_outcome.py` cai nessa metade, logo os 3 testes adicionados deslocaram a
distribuição do xdist ali.

**O closeout achou 3 coisas que eu não tinha visto** — 2 delas contra mim:

1. **Sobre-crédito meu ao `PV13-18`.** Eu escrevera que esta lane fecha "metade" dele.
   Fecha **zero**: `with_gap` faz o banner `return null`
   (`ReportDataQualityBanner.tsx:73`) — troca afirmação falsa por **silêncio** —, e o
   predicado do `PV13-18` é sobre o silêncio (*"nada na UI diz isso"*). Medido na mesma
   passada: `RunContextLine` (`HistoryRow.tsx:27-73`) só lê `paused_at_stage` no ramo de
   run **descartado**, então run `completed` que pausou e retomou devolve `null` também na
   tela de pipeline. O que esta lane entrega ao `PV13-18` é **substrato** (o fato durável
   já é lido, na mesma query), não fecho. Ele fica **sem dona** — decisão registrada na
   trilha dele, para a `U6` não o redescobrir como novo.
2. **`tags` declarava `status/open`** com `status: shipped` no campo. Corrigido.
3. **O `RR9-21` afirma mais do que mediu** — os 4 achados que ele chama de `clareza-ux`
   são 2 (`RR8-01`/`RR8-02`; este nasce de `saúde-execução` e o [[A40.l108]] de
   `consistência`), e o defeito desta lane **não é observável em captura de viewport**,
   porque a `CleanBar` não renderiza neste workspace. Emenda datada no registro.
