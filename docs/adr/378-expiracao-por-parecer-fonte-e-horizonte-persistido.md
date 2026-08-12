---
id: ADR-378
type: adr
title: "Expiração por parecer-fonte + horizonte persistido — sugestão do parecer tem validade igual à da fotografia que a originou"
status: Proposto
phase: "A42"
date: "2026-08-11"
relates_to:
  - "[[ADR-136]]"
  - "[[ADR-153]]"
  - "[[ADR-199]]"
  - "[[ADR-269]]"
  - "[[ADR-290]]"
  - "[[ADR-366]]"
supersedes: []
superseded_by: []
aliases: ["ADR 378", "expiração por parecer-fonte", "horizonte da sugestão"]
size_lines: 138
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/llm
  - area/produto
---

# ADR-378 — Expiração por parecer-fonte + horizonte persistido

**Status:** Proposto • **Data:** 2026-08-11 •
**Plano:** [[PLAN-suggestion-lifecycle]] §F5 • Estende [[ADR-290]]

## Contexto

Auditoria do workspace dogfood em 2026-08-11 (26 runs de parecer desde a
entrega de [[ADR-290]] em A25): **15 `Suggestion` Pendentes** — 11 `warning`,
4 `info`, 0 `danger`. O supersede-per-run funciona (435 `Superseded`, 9 no
run do dia), mas três defeitos sobrevivem, e os três são de ciclo de vida:

1. **Zumbis imortais.** 7 das 15 pendentes são de 2026-06-12 com
   `thesis_key = NULL` — sobreviventes do backfill heurístico da F4. O
   predicado de supersede filtra `thesis_key IS NOT NULL` (B1, fallback
   "seguro"), então essas linhas **nunca** podem ser supersedidas. Elas citam
   valores da fotografia de junho ("transferir R$ 140 mil do excesso de
   caixa", "reserva de R$ 200–300 mil") contra um E5 de agosto. O
   `financial-planner` classificou como **bloqueante**: conselho de mover
   caixa é condicional ao saldo corrente — se o caixa caiu, a ação corrói a
   reserva. Um fallback desenhado para proteger *dados* criou, para
   *conselho*, a pior classe possível: recomendação sem validade, imune a
   correção, indistinguível na tela da recomendação vigente.
2. **`thesis_key` não discrimina.** 3 pendentes do run de 2026-08-11
   compartilham a mesma chave sendo teses distintas (alocação-alvo, exposição
   cambial, concentração imobiliária). A cardinalidade de
   `sha256(ws | tema_canonico | section_id | ancora)` é 9 temas × 12 seções ×
   4 âncoras; um único trio (tema "Alocação", seção `S3`, âncora
   metodológica) cobre as três. O gate de estabilidade da F1 mede
   **reaparição** (≥90%), não colisão — passa verde errando pelo erro oposto.
3. **Horizonte descartado na persistência.** `_iter_sugestoes` achata
   `sugestoes_execucao`/`taticas`/`estrategicas` e joga o bucket fora. O
   inbox apresenta "faça agora" e "considere em 3 anos" como itens
   equivalentes da mesma fila — causa estrutural de 11 acionáveis
   simultâneas, quando as três metodologias de referência convergem em ≤3
   compromissos por ciclo.

Dois achados de leitura de código entram como decisão porque mudam o desenho:
`_existing_dedup_keys` considera **todos** os status, então uma `Superseded`
antiga bloqueia para sempre a reinserção do mesmo texto (tese reafirmada some
em silêncio); e `uq_sugagg_ws_dedup_status` é UNIQUE **full**, que já é bug
latente hoje — [[ADR-153]] §2 permite recriar após a janela de 90 dias, e o
segundo descarte da mesma `dedup_key` levanta `IntegrityError`.

## Decisões

- **D1 — Expiração por parecer-fonte.** Ao persistir o parecer de um run
  **entregue**, toda `Suggestion` `Pendente` de `origin='llm'`,
  `kind='parecer_planejador'` que **não foi criada pelo run atual** vira
  `Superseded` — **inclusive `thesis_key IS NULL`**. O motivo não é "a tese
  sumiu", é "a fotografia que originou este conselho não é mais a vigente";
  independe de existir tese equivalente no run novo. Corolário: nenhuma
  sugestão de parecer sobrevive a um parecer novo sem ser **reafirmada** —
  tese ainda válida é reemitida com o valor de agora. Proteções mantidas:
  `accepted_decision_id IS NULL` ([[ADR-290]] B3), guard run-level
  `_find_existing_review` (B6), `superseded_by_run_id != run_atual`.
  **Guard obrigatório:** `outcome = retido` ([[ADR-366]] §D1) ou artifact sem
  sugestões **não expira nada** — parecer que não entregou não pode apagar o
  inbox do cliente; run de debug via `from_stage` é o caso mais provável.
  `entregue_com_retencao` expira normalmente: os itens derrubados são os de
  citação não confirmada, e mantê-los vivos preservaria número fabricado.
  Coluna `pipeline_run_id` (FK `SET NULL`) torna o predicado explícito — hoje
  ele depende da ordem de execução dentro da transação.
- **D2 — Dup-check só sobre status ativos.** O conjunto que bloqueia insert
  passa a ser `{Aceita, Modificada}` (`Descartada` segue governada pela
  janela de 90 dias por tese, B4). Não é regra nova: é o mesmo conjunto que
  `regenerate_for_report._should_skip` já usa no caminho determinístico
  ([[ADR-153]] §2) — o caminho `origin='llm'` é que havia divergido.
  Consequência aceita: texto byte-idêntico ao de uma sugestão já `Aceita` não
  renasce enquanto a `Decision` existir; o trabalho vive no aggregate
  `Decision` ([[ADR-136]]). O contador `skipped_dup` mede quantas vezes isso
  ocorre — se subir, é a evidência que abre o dedup cross-aggregate.
- **D3 — Índice único parcial sobre os status ativos.**
  `uq_sugagg_ws_dedup_status` (UNIQUE full de 3 colunas) é substituído por
  `uq_sugagg_ws_dedup_ativa` — `(workspace_id, dedup_key)` WHERE
  `status IN ('Pendente','Aceita','Modificada')`. Espelha exatamente o
  invariante do service ("no máximo uma linha ativa por conteúdo") em vez de
  ficar mais frouxo que ele; histórico (`Superseded`/`Descartada`) é ilimitado
  por design. Nenhuma transição legítima colide: `accept`/`modify` movem a
  linha dentro do conjunto indexado, `dismiss` a retira. Duplicatas ativas
  pré-existentes medidas em 2026-08-11: **zero**.
- **D4 — Horizonte persistido.** Coluna `horizon`
  (`execucao|tatica|estrategica`, nullable) gravada na escrita a partir do
  bucket do artifact; `NULL` para `origin='deterministic'` e linhas legadas.
  O valor persistido é o canônico curto, não o nome da chave do schema LLM.
  **Polaridade do gate de display é obrigatória:** a UI esconde
  `horizon IN (tatica, estrategica)`, **nunca** mostra apenas
  `horizon = execucao` — a segunda formulação sumiria com toda sugestão
  determinística (`NULL`). Sem backfill: a expiração de D1 limpa o legado no
  primeiro run entregue.
- **D5 — Telemetria antes do julgamento.** KR4 ganha `skipped_dup`,
  `reemitted`, `pending_after` (o único contador que enxerga o modo de falha
  novo — "inbox esvaziou") e `thesis_collision_intra_run`. Supressão pela
  janela de dismiss passa a logar item a item (`thesis_key` + `dedup_key` +
  `section_id`): com chave de baixa cardinalidade, descartar T1 silencia T2 e
  T3 por 90 dias, e isso precisa deixar rastro. A colisão **já foi medida em
  2 num run real**; por isso `action_slug` de vocabulário fechado deixa de ser
  "Later condicional" e vira **F6 nomeada** no plano — não hard-fail nesta
  fase, mas gatilho disparado, não hipótese.
- **D6 — `Superseded` é reutilizado, `thesis_key` permanece.** Um status
  `Expirada` teria semântica idêntica para todo consumidor (fora do inbox,
  recuperável, auditável por run) ao custo de enum + DTO + OpenAPI + máquina
  de estados; a distinção "expirou sem sucessor" é derivável de
  `superseded_by_run_id` + ausência de linha nova com a mesma `dedup_key`.
  `thesis_key` continua gravada, mas **muda de papel**: deixa de ser predicado
  de supersede e passa a ser (a) identidade da janela de dismiss (B4) e (b)
  telemetria de near-dup.

## Alternativas rejeitadas

- **Sinalizar a idade em vez de expirar** (badge "de junho/2026"): transfere
  ao usuário a decisão de qual número é confiável — que é o trabalho que ele
  contratou o produto para fazer. A UI ainda agrupa por lote, mas o dado
  velho não pode continuar `Pendente`.
- **Backfill de `thesis_key` nas linhas órfãs:** impossível de forma
  determinística — as linhas antigas não guardam `tema_canonico` nem
  `ancora_metodologica` (constatado na F4). Qualquer recomputação seria
  heurística sobre título, e heurística não deve governar expiração.
- **Corrigir só `action_slug` (F6) e manter o predicado por tese:** não
  resolve os zumbis `NULL`, que são imunes a qualquer chave — a expiração
  precisa ser ortogonal à identidade da tese.
- **Manter a exceção "dedup_key reaparecida sobrevive":** `dedup_key` não
  cobre `rationale` nem `impacto_estimado.valor_estimado_brl`; a linha
  sobrevivente carregaria valor velho sob texto igual, violando a
  imutabilidade de conteúdo de [[ADR-153]].

## Consequências

- O inbox passa a ser projeção do parecer vigente, não acumulação histórica.
  `created_at` deixa de significar "primeira aparição da tese" e vira
  desempate intra-run; IDs de sugestão são efêmeros por run (nenhuma FK
  aponta para `suggestions` — verificado).
- Em regime estável, `suggestions_created ≈ suggestions_superseded` a cada
  run; por isso o KR4 original perde poder de detecção e `pending_after`
  passa a ser o sinal que importa.
- Concorrência: dois runs de parecer simultâneos no mesmo workspace disputam
  o conjunto `Pendente` e o perdedor falha com `IntegrityError` — fail-closed
  e detectável (evento `planner_review_persistence_conflict`), premissa
  load-bearing sendo a serialização de runs ativos por
  `ux_pipeline_runs_ws_active`.
- Código mergeado **não** limpa o dogfood sozinho: os 7 zumbis de junho só
  morrem no próximo run entregue (ou via `suggestion_backfill` em modo
  `latest_batch`, já aprovado na F4). O aceite da lane inclui essa ação.
- `Superseded` cresce ~9–15 linhas por run por workspace. É trilha de
  auditoria (espírito [[ADR-136]]); retenção não é decidida aqui, fica
  registrada como consequência aceita.
