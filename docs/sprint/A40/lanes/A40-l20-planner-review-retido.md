---
id: A40.l20
type: lane
title: "PlannerReview representa gerado-e-retido: hoje o estado é inalcançável e a UI mente"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l20-planner-review-retido
adrs:
  - "[[ADR-204]]"
  - "[[ADR-357]]"
  - "[[ADR-366]]"
depends_on:
  - "[[A40.l18]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/backend
  - area/frontend
---

# A40.l20 — `planner-review-retido`

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]). Desbloqueia a [[A40.l22]] já
> no **PR1**.
>
> **Correção de premissa (2026-08-05, decisão do dono).** A forma anterior —
> *"depende da decisão, não do merge, da [[A40.l18]]"* — está **falsificada por
> medição**: o desfecho retido do parecer retorna `success: False`
> (`_needs_review_return`, `pipeline/stages/parecer_planejador.py:98`), e nesse
> ramo `backend/app/tasks/pipeline_task.py` (a) rolla a sessão de artifact
> (`:1329`), (b) só chama `_persist_planner_review_if_applicable` dentro de
> `if result.success` (`:1192-1193`) e (c) grava `stage_log.status = failed` +
> `run.failed_at_stage` (`:1180-1200`). Persistir o desfecho retido exige
> **exatamente as linhas que a [[A40.l18]] reescreve** — mesma função, mesmo hunk.
> `depends_on` fica; `parallel_with` seria mentira de máquina.
>
> **O que não depende da l18 é o contrato.** Entrega em **2 PRs** (§Sequência de
> entrega): PR1 (modelo + API + estado de UI + contador) implementa contra o
> vocabulário da [[ADR-357]] `Proposto` e mergeia em paralelo; PR2 (wire-up no
> orquestrador) fica atrás do merge da l18. Mesma disciplina reader-first da
> [[A40.l21]], com a **mesma amarra**: se a l18 não mergear até `date_target`, o
> PR1 é revertido junto com a l21 (§Gate de saída e encerramento do
> [`_README`](../_README.md)). `status: open` pela **2ª cláusula** do §Predicado
> (amarra explícita de entrega parcial), precedente [[A40.l27]].

## Problema

O estado "parecer foi gerado e teve conteúdo retido" **não existe** no modelo:

- `PlannerReview.status` é hardcoded `"Gerado"`
  ([`planner_review_persistence.py:93`](../../../../backend/app/services/planner_review_persistence.py),
  citando [[ADR-204]] §D1).
- `_should_persist_planner_review` (def em `:1130`) retorna `False` quando
  `detail["status"] == "needs_review"`
  ([`pipeline_task.py:1136`](../../../../backend/app/tasks/pipeline_task.py)).

Resultado: em retenção **não existe row**, a API responde 404, e a seção do
relatório cai na copy de "ainda não gerado" — que **mente** para um cliente
premium que pagou pela geração. Nenhuma mudança de copy resolve isso sem tocar o
aggregate.

Segundo defeito no mesmo lugar: `items_gated_count` é **tier gating** (comercial,
ação = comprar). Reutilizá-lo para itens retidos por qualidade (ação =
reprocessar) produz copy contraditória no mesmo card.

## Decisão

1. `PlannerReview.status` passa a representar o desfecho real, com vocabulário
   alinhado ao da [[ADR-357]]. Provável **emenda em [[ADR-204]]** §D1 — é ela que
   fixa o vocabulário hoje.
2. Persistir o aggregate também no desfecho retido (com o artifact degradado que
   a [[ADR-357]] §6 manda commitar).
3. **Contador novo**, separado de `items_gated_count`, para itens retidos por
   qualidade.
4. A API expõe uma **classe fechada de motivo** client-facing
   (ex.: `citacao_nao_confirmada` / `politica_de_conteudo` / `dado_insuficiente`).
   **Nunca** `error_detail` cru — o valor real é
   `"evidencia unverified (severidade alta): risco:3"`, vocabulário de operador
   que não pode chegar ao cliente.
   > Atualizado 2026-08-03 pela [[A40.l16]]: a forma anterior citada aqui
   > (`"valor monetário na prosa (severidade alta): risco:3"`) **deixou de ser
   > produzível** — `_LAYER_LABELS` foi deletado com a saída de `number_in_prose`
   > de `_HARD_LAYERS`, e o reason volta ao `_DEFAULT_LABEL` para as 3 camadas
   > hard restantes. O argumento não muda: o vocabulário continua de operador.
5. Persistir a tupla estrutural `(item_type, index, layer, severidade)` no
   summary — hoje o `dropped` do `StrictDecision` perde a camada no caminho e só
   sobra `count`. **Sem prosa e sem valor monetário**, preservando o padrão
   PII-safe já declarado no stage.
   > Delta da [[A40.l16]] (2026-08-03): `_parse_hard_violations` voltou a
   > 2-tupla. Isso **não** remove capacidade desta lane — `dropped` nunca carregou
   > o `layer` (era descartado antes do `return`, inclusive antes de #875); o que
   > muda é que reintroduzir o 3º elemento no parse passa a ser parte do escopo
   > desta decisão (~2 linhas), agora desacoplado de qualquer rótulo
   > client-facing.

## Sequência de entrega (2 PRs — amarra de entrega parcial)

**PR1 · contrato do desfecho retido — paralelo à [[A40.l18]].** Itens 1, 3, 4 e 5
da §Decisão: `PlannerReview.status` com o vocabulário da [[ADR-357]] (emenda
[[ADR-204]] §D1), contador de retidos separado de `items_gated_count`, classe
fechada de motivo na API, tupla estrutural no summary, estado novo em
`usePlannerReview`, termo em `COPY_GUIDELINES` §2.2. Provado por fixture que chama
a persistência **direto**, não pelo caminho do run. Aceite = os 4 primeiros
bullets da §Critério de aceite + rebaseline do snapshot do view-model.

**PR2 · wire-up no orquestrador — atrás do merge da [[A40.l18]].** Item 2 da
§Decisão: `_should_persist_planner_review` deixa de excluir o desfecho retido e o
call-site passa a ser alcançável no ramo degradado (`pipeline_task.py:1192-1193`,
que a l18 reescreve). **Não abrir antes do merge da l18** — o diff colide no
mesmo hunk.

**Se a l18 já estiver em `main` no pickup:** ignore o split e faça PR único — o
split é permissão para paralelismo, não obrigação.

## Critério de aceite

- Fixture com item de alta severidade + violação hard ⇒ row de `PlannerReview`
  existe com status de retenção; API 200 (não 404).
- O `state` que `usePlannerReview`
  ([`frontend/src/hooks/usePlannerReview.ts:67`](../../../../frontend/src/hooks/usePlannerReview.ts))
  devolve ganha o estado correspondente; nenhuma resposta da API
  contém `error_detail` cru, `risco[N]`, nome de camada interna, `stage`, `E5` ou
  `E6`.
- `items_gated_count` inalterado em semântica; contador de retidos é campo
  distinto.
- ~~Snapshot do view-model rebaselinado com `MATHOMS_UPDATE_SNAPSHOT=1`.~~
  **Corrigido 2026-08-06 por medição — o critério era inalcançável.**
  `backend/tests/snapshots/dogfood_view_model.json` tem **zero** ocorrência de
  `parecer`/`planner`/`items_gated`/`PlannerReview`, e o substrato golden
  (`tests/pipeline_golden_substrate.py`) roda só E1.5→E5: o stage do parecer nunca
  executa. A seção é aggregate-driven por endpoint próprio (`usePlannerReview`),
  fora do view-model. Rebaselinar produziria diff vazio — ou capturaria drift de
  outro PR como se fosse deste. Substituído por `make update-openapi-snapshot`
  (o DTO muda) + `make update-db-schema-reference` (3 colunas novas).
- Termo novo registrado em `COPY_GUIDELINES` §2.2 com data, antes de propagar.

## Estado — PR1 entregue (2026-08-06)

Canônica: [[ADR-366]] (`Proposto`; flippa no merge do **PR2**, não deste — a tese
"o desfecho retido é alcançável" só fica provada quando o membro ganha produtor).

**Três decisões desta lane foram revistas em co-design** (`data-engineer` +
`senior-cto` + `product-designer`, 2026-08-06):

1. **`status` NÃO recebe o desfecho** (§Decisão item 1 da lane). São dois
   desfechos de retenção, e `entregue_com_retencao` é um parecer **publicável** —
   como valor de `status` daria 409 no publish de algo publicável. Eixo próprio
   (`outcome`), com guard explícito de publish para o retido.
2. **A classe fechada tem 3 membros, não os 3 propostos.** `dado_insuficiente`
   foi cortado (zero produtores); `politica_de_conteudo` foi dividido em
   `parecer.sigilo` e `parecer.conselho_vedado`, que têm produtores distintos.
   Os 2 ramos de **indisponibilidade técnica** (LLM ausente, chamada sem output)
   **não geram row** — dizer "seu conteúdo foi retido" quando nada foi gerado é a
   mesma mentira invertida.
3. **O item 5 estava no lugar errado.** `(item_type, index, layer)` já existia em
   `_meta.evidencia_verification`; o que faltava era a **severidade** e o
   **veredito** do enforcement. E `dropped` ganhou par (`retention_trigger`)
   porque no ramo de alta severidade nada é removido.

**Blocker que a lane não nomeava, e que teria tornado o PR1 pior que o bug:** o
artifact do desfecho retido é o placeholder de `empty_needs_review_output` — 3
pontos fortes intitulados `"placeholder"` e um `diagnostico_geral` que manda
*"Inspecione `_meta.error_detail`"*. Persistir e servir sem suprimir entregaria
conteúdo **fabricado** a um cliente premium, com `items_shown_count=3`. Daí
`content: Optional`, decidido antes de carregar o artifact.

### Pendente — PR2 (atrás do merge da [[A40.l18]])

`_should_persist_planner_review` deixa de excluir o desfecho retido. Medido em
2026-08-06: são **3** guards independentes, não 1 — a lane citava só
`status == "needs_review"`. O 3º (`"persona_hash" in result.detail`) é o mais
silencioso, e um PR2 que abra só a cláusula citada fica verde no diff e **morto em
runtime**. O enriquecimento do detail que o fecha já entrou neste PR1.

### Achados nomeados, não corrigidos aqui

- **Free tier cai na mesma copy que mente** — o stage recusa antes de gerar
  (`{"skipped": True}`), não há row, e o 404 vira "ainda não gerado". É a outra
  metade da mesma mentira; o flag da [[ADR-208]] §D2 que faria free gerar **não
  existe em código**. Destino: [[A40.l22]].
- **`output_summary` de `stage_logs` expõe a prosa crua** por outro endpoint —
  o gate de não-vazamento desta lane cobre `/planner-review`, não aquele DTO.
- **`check_orphan_planner_artifacts` é falso-verde** — casa `stage == "E6-parecer"`
  sem `stage_aliases`, logo nunca encontra órfão. Ganhou a guarda de `_meta.status`
  neste PR para que corrigir o filtro depois não abra a janela; o filtro **não**
  foi corrigido.
- **`riscos_truncados` é uma 4ª subtração silenciosa** (cap ≤12), fora do
  contador desta lane.
