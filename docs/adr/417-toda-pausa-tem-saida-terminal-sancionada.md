---
id: ADR-417
type: adr
title: "Toda pausa tem saída terminal sancionada, e abandonar é decisão de run, não de review"
status: Decidido
phase: A40
date: "2026-08-26"
relates_to:
  - "[[ADR-359]]"
  - "[[ADR-411]]"
  - "[[ADR-404]]"
  - "[[ADR-172]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 417"
  - "porta de saída do needs_review"
  - "descartar processamento pausado"
tags:
  - type/adr
  - status/decidido
  - area/backend
  - area/pipeline
---

# ADR-417 — Toda pausa tem saída terminal sancionada

**Status:** Decidido (A40.l87) • **Data:** 2026-08-26 • **Relaciona** [[ADR-359]], [[ADR-411]], [[ADR-404]], [[ADR-172]] • **Lane:** [[A40.l87]]

## Contexto

`PipelineRunStatus.needs_review` é uma pausa legítima: o stage devolve
`needs_review`, o run grava `paused_at_stage` e cria `StageReview` pendentes.
A saída sancionada é `POST /runs/{id}/resume`, que exige zero reviews
pendentes e **roda todos os stages a jusante** — inclusive os LLM.

Não existe outra. `cancel` recusa: `needs_review` está fora de
`CANCELLABLE_STATUSES` (`backend/app/services/pipeline/dispatch_contract.py`),
com o comentário *"pausa é estado legítimo e cancelá-la é decisão de produto,
não de operação"*. **Um run pausado só sai da pausa completando-se.**

Isso é a patologia que o próprio arquivo documenta ter consertado para outro
estado — *"órfão em `resuming` era o único estado inescapável do sistema"*
([[ADR-359]] · [[A40.l27]]). O conserto de lá admitiu `resuming` na tupla;
`needs_review` ficou de fora por uma decisão que **pressupôs uma porta de
produto que nunca foi construída**.

### A decisão de produto já existia — o backend é que a recusa

`NeedsReviewCard.tsx` renderiza um botão **"Cancelar execução"**, e `page.tsx`
o monta exatamente quando `activeRun.status === "needs_review"`. O clique cai
em 409 `"Execução não pode ser cancelada (status: needs_review)"` e vira banner
de erro com o nome cru do status.

O card existe desde **2026-04-21**. O comentário que afirma *"é decisão de
produto"* entrou em **2026-08-07** — três meses depois de o produto ter
decidido na única superfície que o usuário toca. Logo o defeito **alcança o
usuário**, não só a operação.

### Dois testes pinam a crença errada

`frontend/tests/components/NeedsReviewCard.test.tsx` assere apenas que
`onCancel` foi chamado — pina a fiação, nunca o desfecho; passa no CI e falha
em produção. `backend/tests/test_detect_undispatched_runs.py` assere
literalmente `needs_review not in CANCELLABLE_STATUSES`.

### O buraco não é só orfanamento — é executor duplo

`_flip_run_to_resuming` (`pipeline_service.py`) checa **só** que *este* run é
`needs_review`; não há consulta a run ativo. Como a pausa é invisível ao índice
parcial `ux_pipeline_runs_ws_active` (`IN ('pending','running')`) **e** ao
fast-path `_check_no_active_run`: pausa P → trigger N é permitido → aprovar as
reviews de P → resume P → dois workers escrevendo artefatos no mesmo
workspace. É a falha que a [[A40.l27]] nomeou para `resuming`.

### O que forçou a decisão

Dois runs do workspace de dogfood pararam em `needs_review` no stage
`analyze_finances` em 2026-08-25 e bloquearam o preflight da rodada unificada
([[runbook-unified-certify-review]] §5 F0, check `run-em-voo`). O texto de
remediação dizia *"retome … ou marque terminal"* — e "marque terminal" não
existia como ação sancionada. Resolveu-se escrevendo `status=cancelled` direto
pela ORM, contornando um guard deliberado.

## Decisão

### D1 — `needs_review` é cancelável

`needs_review` entra em `CANCELLABLE_STATUSES`. Simetria explícita com a
[[ADR-359]], que admitiu `resuming` pelo mesmo motivo ("o zumbi tem de ter uma
porta de saída manual"). O comentário que afirmava a política contrária é
reescrito no mesmo commit — comentário que declara cobertura que a decisão
refuta é a patologia RV8-08 da [[A40.l84]].

A objeção original não se sustenta: nenhuma varredura automática alcança
`needs_review` (`detect_stuck_runs` filtra `running`; `_heal_undispatched_run`
filtra pre-dispatch), e `cancel` é sempre iniciado por humano autenticado atrás
de `require_write_role`. A guarda protegia contra uma ameaça que os sweeps não
oferecem.

### D2 — o verbo é run-level; `action_review` não ganha ação de abandono

`action_review` opera no grão da `StageReview`; abandonar é decisão do **run**.
Com N reviews pendentes, qual `review_id` mata o run? Qualquer resposta é
arbitrária. E a [[ADR-411]] D4 decide que `StageReview` significa uma coisa só.
Rota nova (`POST /runs/{id}/abandon`) também é recusada: criaria um **segundo
caminho de transição-para-terminal** que o próximo predicado estilo
`is_run_active` pode esquecer — a fragmentação que a [[ADR-359]] consolidou.

**Corolário:** `action_review` passa a recusar ação sobre run terminal. Hoje
aceita `approve` num run morto e emite telemetria `review_action` (KR1 da
A29.l1) poluída com ações sobre runs abandonados.

### D3 — `(cancelled, pending)` é resíduo sancionado; `(completed, pending)` continua proibido

As `StageReview` do run descartado **ficam `pending`**. Não se cria
`StageReviewStatus.dismissed`: gravaria um fato falso (ninguém dispensou a
review — o run foi abandonado), exigiria `ALTER TYPE` em enum nativo no
Postgres, e `dismissed` lido como "resolvida" reabriria o P0 da [[A40.l84]].

`pending` sobre run terminal diz a verdade: *ninguém decidiu, e não vai
decidir*. A fila da UI é chaveada por status do **run**
(`PendingReviewQueue.tsx`), então esvazia por construção — nenhum leitor muda.

> **Amarra com a [[A40.l84]]:** o predicado de fecho dela é
> **`(completed, pending)`**, nunca *"terminal + pending"*. Escrito como
> "terminal", morde o resíduo que esta ADR sanciona e as duas se refutam.

### D4 — o descarte é distinguível por estado GRAVADO, nunca por resíduo

`pipeline_runs` ganha **`cancelled_from_status`** (`String(20)`, nullable): o status do
run no instante em que virou terminal. Writer **único**, dentro da sessão de
`cancel_pipeline_run`, no mesmo `commit` do flip — o service já lê `run.status` na
guarda, imediatamente antes de sobrescrevê-lo, então não há janela.

Não é `Enum(...)`: um segundo tipo enum nativo no Postgres traz o
`ALTER TYPE ... ADD VALUE` cujo custo o D3 já recusa. Grave `.value`. Forma precedente:
`tier_at_run` (`String(20)`), `failure_reason` (`String(50)`).

**Sem backfill.** Rows `cancelled` legadas ficam `NULL` para sempre, e `NULL` significa
*desconhecido* — nunca "interrompido". Inferir o valor delas seria commitar dentro de uma
migração exatamente a derivação que a §abaixo refuta, onde ela deixa de ser reversível.

**Motivo e ator continuam fora da linha do run.** Quem abandonou vai para o `AuditLog`
(ação nova em `AuditAction`), que já é a resposta do repo para "quem fez o quê", já
sobrevive ao purge de leitura ([[ADR-275]] D5) e não exige migração. A coluna carrega
**estado do ciclo de vida**, não motivo: são fatos de grãos diferentes, e o lugar do
ciclo de vida de um run é a linha do run.

`failure_reason` fica recusado por dois motivos, não um. O conhecido: abandono deliberado
ali contaminaria métrica de confiabilidade, e o campo tem read path no DTO. O estrutural,
mais forte: `failure_reason` é campo de **motivo**, e o que falta aqui é **estado** —
discriminar exigiria escrever valor nos dois casos (cancelado de `running` e de
`needs_review`), e nesse ponto a coluna de estado já existe, com o nome errado, dentro de
um módulo chamado `pipeline_failure_reasons.py`.

**Gate, de graça pela estrutura do D7:** `test_todo_estado_escapavel_sai_pela_rota` já
parametriza sobre os estados escapáveis; a asserção `cancelled_from_status == status` faz
estado novo cujo writer alguém esqueça **falhar por ausência**.

#### Alternativa considerada e refutada: derivar de `paused_at_stage`

A primeira redação deste D4 dizia que `(cancelled, paused_at_stage IS NOT NULL)` bastava,
"zero migração". **Está errado, e a medição fica registrada aqui para que a proposta não
volte em seis meses vinda de quem só vê a coluna e a acha redundante:**

1. `rg 'paused_at_stage *= *None|paused_at_stage=None' backend/app` devolve **zero**.
   O único write é a pausa (`pipeline_task.py`, `run.paused_at_stage = stage_name`).
2. `_flip_run_to_resuming` o **preserva de propósito** — [[A40.l27]] parou de zerá-lo
   porque é *"a única cópia durável do ponto de retomada"*. Um campo cuja função declarada
   é **sobreviver** não pode discriminar **quando** algo terminou.
3. Logo o par também é verdadeiro para o run que pausou → foi conferido → **retomou** →
   foi interrompido em execução. Isso é interrupção, e o histórico o rotularia
   "Descartado durante a conferência".

O erro de fundo é de grão, e é o mesmo que o D3 rejeita: `paused_at_stage` é **resíduo de
um momento passado**, não **estado no momento terminal** — derivar um fato sobre a
terminação a partir de um fato sobre o histórico.

Duas outras derivações foram consideradas e também refutadas. **Última linha de
`pipeline_stage_logs`:** resume que despacha e morre antes de escrever qualquer log deixa
a última linha em `needs_review`, rotulando "descartado" uma interrupção de resume.
**Ler o `AuditLog` como projeção:** ele é gravado *depois* do flip, em outra transação
(crash no meio dá `cancelled` sem linha de audit), acopla rendering de produto a uma
tabela com política de retenção, e é o anti-padrão "audit como banco de aplicação" —
audit registra o **ato**, não é fonte consultável de estado.

**O que NÃO depende da coluna, e por isso ficou de pé:** o `detail` da resposta HTTP
(`cancel_run` lê `run.status` **antes** do flip) e a copy do diálogo (`cancelCopyFor` lê
`status === needs_review` no instante do clique). Leitura de **estado vivo** é correta por
construção; só a leitura de resíduo caiu.

### D5 — disparar sobre pausa viva é recusado, em fast-path; o índice não muda

Hoje disparar por cima de uma pausa é **silencioso e destrutivo**: a pausa
nunca mais será retomada e as `stage_reviews` dela ficam `pending` órfãs, sem
varredura que as colha. `_check_no_active_run` passa a incluir `needs_review`,
com 409 que nomeia a saída ("retome ou descarte"), nunca "aguarde".

O predicado do índice parcial `ux_pipeline_runs_ws_active` **não muda**.
Precedente literal: a [[A40.l27]] pôs `resuming` no fast-path e não no índice.
Estado bloqueado por decisão humana não vira lock de DB — "o usuário viajou"
não pode ser "o workspace parou". A correção do executor duplo é a guarda em
`_flip_run_to_resuming`, não o índice.

> **Entregue no PR2:** o fast-path recusa com 409 que nomeia as duas saídas, e
> `_flip_run_to_resuming` ganhou a guarda de executor concorrente — é **ela**, não o
> índice, que fecha o executor duplo, porque a pausa não segura executor: ela é uma
> **pretensão** a virar um, e o resume é o instante em que essa pretensão é exercida.
>
> **§Deferimento datado 2026-08-26 — alargar o índice parcial.** Dono
> `data-engineer`. Condição de retomada: evidência de corrida real
> trigger↔resume que o fast-path não pegou. **Armadilha a carregar:**
> `CREATE UNIQUE INDEX` sobre o predicado alargado falha em qualquer workspace
> com 2+ linhas nele — o dogfood tem exatamente isso hoje. A migração precisa
> liquidar todas menos a mais recente por workspace **antes** de criar o
> índice, ou o deploy quebra.

### D6 — a ordem não é invertível

D1+D4 (a porta) shipam **antes** de D5 (o bloqueio). Bloquear o trigger sem
porta de saída converte "pausa" em "workspace tijolado" — que é literalmente
o incidente de origem da [[ADR-359]], agora enforçado por código.

### D7 — todo estado não-terminal declara sua saída, exaustivamente

Tabela declarada ao lado de `CANCELLABLE_STATUSES` classificando **cada**
membro de `PipelineRunStatus` em terminal, saída manual sancionada ou saída
automática, com teste exigindo cobertura total do enum. Membro novo falha **por
ausência**, não por alguém lembrar de adicionar um caso — foi assim que
`resuming` e depois `needs_review` escaparam. Forma copiada de
`test_todo_status_pre_dispatch_tem_relogio`.

Teste de tabela não basta: a [[A40.l27]] mediu que a guarda do cancel é
**duplicada** e alargar só um lado deixa o endpoint em 409 com o teste de
constante verde. Acompanha **um teste de endpoint por estado manualmente
escapável** exigindo 200 + status terminal no DB.

## O que esta decisão reverte da ADR-359

A [[ADR-359]] segue integralmente em vigor: dispatch falha alto, e quem cria
estado pendente compensa. Um run que pausa legitimamente e é abandonado por um
humano **não é falha de dispatch nem compensação** — está fora do escopo dela.

O que a implementação da 359 introduziu e esta ADR reverte é uma cláusula
lateral: a exclusão de `needs_review` de `CANCELLABLE_STATUSES` e a asserção
de teste que a pina. Por isso `relates_to`, não `supersedes` — marcar a 359
como superseded faria o `ADR_INDEX` mentir.

## Consequências

**Positivas.** O botão morto há 4 meses passa a funcionar. O preflight da
rodada unificada deixa de ensinar contorno por ORM. A classe de defeito
("estado sem saída") ganha gate que pega o *próximo* estado, não só este.

**Negativas assumidas.** Perde-se distinção de primeira classe entre
"cancelei o que rodava" e "abandonei o que estava pausado" no campo `status` —
mitigado pela derivação de D4. E D5 é regressão de conveniência: uma pausa
passa a bloquear disparo novo. Só é aceitável **porque a porta existe** (D6).

**Risco.** Se D5 shipar sem D1, o workspace fica tijolado. A ordem é gate, não
sugestão.

## Validação

Reproduzir 2026-08-25: run pausado ⇒ preflight `run-em-voo` em FAIL ⇒ resolver
**por chamada de API, sem nenhuma escrita direta no DB** ⇒ check passa a PASS.
É o que prova que a porta é **usável**, não apenas existente — as duas
resoluções anteriores exigiram ORM.
