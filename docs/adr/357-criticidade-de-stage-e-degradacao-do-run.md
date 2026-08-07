---
id: ADR-357
type: adr
title: "Criticidade de stage e degradação do run — add-on advisory não veta o entregável"
status: Proposto
phase: "A40"
date: "2026-08-03"
relates_to:
  - "[[ADR-199]]"
  - "[[ADR-131]]"
  - "[[ADR-212]]"
  - "[[ADR-297]]"
  - "[[ADR-291]]"
supersedes: []
superseded_by: []
aliases: ["ADR 357", "stage criticality", "partial_failure alcancavel"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
  - phase/a40
---

# ADR-357 — Criticidade de stage e degradação do run

**Status:** Proposto (A40) • **Data:** 2026-08-03 • **Relaciona** [[ADR-199]]
(parecer declarado "não-bloqueante"), [[ADR-131]] (`Report.analysis_artifact_id`),
[[ADR-212]] (`ArtifactStore` DB-only), [[ADR-297]] (guarda de redelivery),
[[ADR-291]] (`from_stage`).

## Contexto

Run `2ded7aab` (2026-07-31) foi marcado `failed` com o E5 completo em
`pipeline_artifacts` (123.498 bytes). O relatório era derivável e não foi
derivado: `_finalize_pipeline_outcome` faz `if not has_failure:
_run_post_processing(...)`, e o post-processing é quem cria a linha em `reports`,
materializa lineage edges ([[ADR-279]]) e sincroniza status E2. Um defeito de
forma na prosa de um add-on advisory apagou os três.

`StageResult.success: bool` é o **único** canal de sinalização, e `False`
significa indistintamente "o pipeline não pode continuar" e "este add-on não
entregou". A política de raio de explosão fica codificada em quem **produz** o
valor, não em quem **decide** o destino do run — inversão de DIP.

A classe tem **3 membros vivos**, todos na cauda pós-`analyze_finances`:
`review_finances_holistic`, `generate_narratives`
([`scripts/generate_narratives.py:971,980`](../../scripts/generate_narratives.py))
e `validate_cross`
([`scripts/validate_cross.py:699,711,717`](../../scripts/validate_cross.py)).
Qualquer um destrói o entregável hoje.

Duas evidências de que o estado desejado já era o pretendido:

- [[ADR-199]] declara no próprio `STAGE_REGISTRY`
  ([`pipeline/stage_spec.py:243`](../../pipeline/stage_spec.py)) que o parecer é
  *"não-bloqueante"*. O código não cumpre a política escrita.
- `tier=free` **já** é a implementação de referência: o stage devolve
  `{"skipped": True}` (dict **sem** a chave `"success"`), o orquestrador conta
  como sucesso, o run completa e o relatório renderiza sem parecer. "Relatório
  sem parecer" já é estado de produto vendido e testado.

`PipelineRunStatus.partial_failure` existe no enum **desde a migration inicial**
e nunca é atribuído por nenhum caminho de código — vocabulário pré-pago.

## Decisão

### 1. `criticality` declarativa no registry

`StageSpec.criticality: Literal["required", "degradable"] = "required"` (default
fail-closed). `degradable` para os 3 membros da cauda. Invariante declarado:
**`analyze_finances` é o último stage `required`; a cauda é enriquecimento.**

Criticidade é do **registry**, não do stage (DIP) nem do run — com um único
deliverable ([[ADR-131]]), a variação "crítico num contexto, não em outro" não
existe hoje, e inventá-la seria abstração sem instância.

**`criticality` alcança apenas o canal de NÃO-ENTREGA (2026-08-06).** O canal
`validation` (`detail["validation"]["valid"]`, consumido por
`_has_validation_errors`) é **ortogonal** e permanece intocado: stage
`degradable` que **entrega** um veredito com `valid: False` continua pausando em
`needs_review`, com row em `StageReview` e `run.paused_at_stage`.

Declarado aqui, e não derivado do critério de aceite de uma lane, porque a
derivação silenciosa é o que produz mudança de contrato sem decisão. Dois
argumentos: (a) pausar **preserva** o E5 e deixa o run retomável — ninguém perde
entregável, que é o dano que esta ADR existe para impedir; (b) `validate_cross`
é o único degradável que emite `validation`, e ali `valid: False` são checks de
**conservação** (a soma fecha?) — publicar à família um relatório cujos números
não fecham, com banner de ressalva, seria vender informação **errada** como
incompleta. O que destrói o entregável hoje são os três
`return {"success": False}` do mesmo arquivo, e esses a `criticality` alcança.

### 2. Um canal, uma verdade

**Nenhuma chave nova no retorno do stage.** O stage continua dizendo "não
entreguei" (`success: False`); o orquestrador combina `(retorno, criticality)` →
`StageResult.outcome ∈ {completed, skipped, degraded, failed}`. Rejeitado o
contrato `{"degraded": True}`: daria ao produtor o poder de silenciar a própria
falha, e dois canais podem discordar (`degraded: True` num stage `required` →
política indefinida).

`{"skipped": True}` é normalizado para `outcome=skipped` no mesmo ato. O default
atual (dict sem `"success"` ⇒ `completed`) é **preservado**.

**A disposição é cega à FORMA da não-entrega.** As duas rotas do loop —
`result is None` (exceção após retries) e `result.success is False` — mapeiam
ambas para `degraded` quando `criticality=degradable`. **`result.error` é
proibido como discriminador:** `error is None` significa "nenhuma exceção cruzou
a fronteira do runner", não "o stage declarou". A assimetria é medida — a mesma
falha de rede vira `error=None` dentro de `llm.call` e `error=str(exc)` em
`store.write`, que fica fora do `try`.

**`reason_class` é descritivo, nunca dispositivo (2026-08-06).**
`StageFailureReason` (enum fechado: `enforcement`, `provider_error`, `network`,
`timeout`, `budget_exhausted`, `llm_unavailable`, `internal_error`, `unknown`)
viaja no `detail` e é persistido em `PipelineStageLog.output_summary`. Isso
**não** reabre a porta que esta seção fechou, e a diferença é verificável e não
retórica: `{"degraded": True}` era **dispositivo** — o produtor nomeava o próprio
raio de explosão. `reason_class` só entra em copy, log e alerta; **nenhuma
ramificação de status o consulta**. Invariante provado por teste paramétrico
sobre **todos** os membros do enum: para o mesmo stage degradável, a tripla
`(run.status, stage_log.status, existe row em reports)` é idêntica em todos.
Mutação que o teste mata: `if reason_class == "budget_exhausted": failed`.

Ele é **obrigatório, não cosmético**. A classe fechada client-facing da
[[A40.l20]] §4 tem 3 membros que são todos juízos sobre o conteúdo do cliente;
sem `reason_class`, um `ReadTimeout` da Anthropic cai nessa classe e a UI diz ao
cliente premium que o conteúdo dele foi retido por política — mentira nova, da
mesma família da que a l20 existe para consertar. A informação já existe e é
jogada fora: `_exc_label` lê `exc.error_type` e o achata em string de display.

### 3. `PipelineStageStatus.degraded` novo; `partial_failure` reusado

- **Stage:** valor novo `degraded`. Não reusar `needs_review`, que está acoplado
  a `StageReview` + `run.paused_at_stage` + `publish_needs_review` e é
  deliberadamente **excluído** de `_TERMINAL_RUN_STATUSES` para o resume
  re-entrar. Degradado é terminal e **não** retomável.
- **Run:** `partial_failure` reusado, com semântica **terminal, entregue, com
  lacuna declarada**. Decisivo: já está em `_TERMINAL_RUN_STATUSES`, logo herda
  de graça a guarda de redelivery ([[ADR-297]]). Um status novo obrigaria a
  lembrar de adicioná-lo ao set — esquecer reabre a regressão.
- `run.failed_at_stage` **não** é populado em degradação (hoje o é para todo
  não-sucesso): `failed_at_stage` preenchido + status `partial_failure` mentiria
  para todo leitor futuro. Derive o stage degradado de `stage_logs`.

### 4. `degraded` entra em `_STAGE_DONE_STATUSES`

Sem isso, o redelivery Celery re-executa e **re-paga** o stage LLM já cobrado
(US$ 0,48 no incidente) — reintroduz a regressão que a A37.l12 fechou, só no
ramo degradado. É a linha mais importante do PR.

### 5. Precondição do report é o artifact E5, não o status do run

Reafirmação de [[ADR-131]]. `_create_report_from_output` já checa apenas a
existência do artifact E5; o único gate é o `if not has_failure`. Nenhuma ADR
declarava "report só de run completo" — o invariante não existia escrito.
`_finalize_run` passa a ser 3-way e o post-processing roda em degradação.

### 6. Artifact degradado é persistido, nunca publicado

Em degradação o artifact é **commitado** (hoje é rolled-back), para que a
superfície de diagnóstico tenha o que ler. Não viola [[ADR-212]]:
`SCHEMA_BY_STAGE` não mapeia `review_finances_holistic`. É **obrigatório**, não
opcional: o marcador terminal promete "artefatos persistidos", e marcar
`degraded` com artifact rolled-back faz o marcador mentir.

Os dois leitores já discriminam por `_meta.status == "Gerado"`.

**Exceção travada:** commit-on-degrade só é seguro quando o stage escreve em
**chave própria**. `generate_narratives` escreve em
`analyze_finances`/`analise_financeira` — a mesma chave do E5 — e commitar merge
parcial ali corrompe o deliverable. A política é declarada **por stage**, não
derivada de `StageSpec.writes` (que é ficção para 2 dos 3 degradáveis).

### 7. Migration do drift de enum

A migration inicial criou `pipelinestagestatus` com 5 valores e
`pipelinerunstatus` com 6. O Python tem `skipped_free_tier`/`needs_review` e
`needs_review`/`resuming` a mais, **sem nenhum `ALTER TYPE`**. Funciona porque
dev é SQLite; em Postgres o caminho de `needs_review` do stage log — **já vivo**
([[ADR-272]]/E3) — quebraria no `INSERT`. A migration inclui os 4 valores em
drift + `degraded`, no padrão guardado por dialeto já usado no repo.

> ✅ **Entregue pela [[A40.l19]] em `c9688111` (#1241), 2026-08-06**, junto com
> `dev/check_enum_migration_parity.py` — o gate que faltava. Ele lê os dois lados
> por **AST** e não o banco de teste: este nasce de `Base.metadata.create_all`,
> que materializa o próprio enum Python, e teria ficado verde durante todos os
> meses de drift. Direção `python ⊆ declarado`, nunca igualdade — Postgres não
> tem `DROP VALUE`, e exigir igualdade transformaria toda remoção legítima em
> falha eterna. É também o que tornou seguro mergear a migration antes do membro
> Python (`degraded` declarado no tipo, ausente no código, gate verde).

### 8. Degradável = não-retryável in-run, não-reexecutável, re-rodável por run novo

`_run_stage_with_retry` só retenta exceção — correto como está. "Retentar só o
parecer" é run novo com `from_stage` ([[ADR-291]]), não resume.

**O motivo é que o retry transitório já foi consumido a montante.**
`LLMService.call` ([`pipeline/llm/litellm_client.py`](../../pipeline/llm/litellm_client.py))
já retenta `RETRYABLE_ERRORS` com backoff 30/60/120s e escalada de timeout
([[ADR-270]]). Repetir no orquestrador é layering de retry que a própria ADR-270
§1 proíbe.

> **Justificativa substituída em 2026-08-06, ainda em `Proposto`.** A forma
> anterior era *"veredito de enforcement sobre gerador estocástico não é
> transitório, e o dinheiro já foi gasto"*. **As duas premissas são falsas no
> ramo de infra**, e a medição é o `except Exception` de
> [`parecer_orchestrator.py`](../../backend/app/services/parecer_orchestrator.py)
> (`# noqa: BLE001 — todas exceções viram needs_review`), que envolve
> `llm.call` inteiro: queda de provider, `ReadTimeout`, 5xx, hard-stop de budget
> ([[ADR-173]]) e bug de código chegam ao orquestrador como `success: False` com
> `error is None`, indistinguíveis de um veredito de enforcement. Nesse ramo a
> falha **é** transitória e o dinheiro **não** foi gasto.
>
> A conclusão sobrevive; a justificativa não. Manter o texto original faria a
> próxima pessoa deduzir que degradação implica dinheiro gasto — e desenhar
> billing ou alerta em cima de uma premissa falsa.

## Alternativas rejeitadas

- **Contrato de retorno do stage (`{"degraded": True}`)** — criticidade viraria
  decisão do produtor; dois canais podem discordar. Ver §2.
- **Especializar só o parecer (`if stage_name == _PARECER_STAGE_NAME`)** — barato,
  não fecha a classe, e há precedente feio disso em
  `_should_persist_planner_review`.
- **`completed_with_degradation` novo** — perde a herança de
  `_TERMINAL_RUN_STATUSES`. Ver §3.
- **Coluna `degraded_at_stage`** — derivável de `stage_logs`.

## Consequências

- Frontend: os **7** read sites que tratam `partial_failure` como falha devem ser
  corrigidos **antes** do writer emitir (reader-first — ver [[A40.l21]]).
  Shipar o writer primeiro entrega um run que produziu relatório com banner
  vermelho de falha, pior que hoje.
- `publish_run_completed`/`publish_run_failed` recebem o status real como
  parâmetro em vez de ganharem um terceiro evento.
- `make update-openapi-snapshot` → **`PipelineRunStatus` inalterado** (é o que
  esta §3 protege — `partial_failure` já está publicado, e reuso é justamente o
  ponto). `PipelineStageStatus` **ganha `degraded`**, 1 linha; idem
  `docs/reference/DB_SCHEMA_REFERENCE.md` via `make update-db-schema-reference`.
  Diff no enum de **run** ⇒ alguém adicionou status novo e a §3 foi violada.
  > Corrigido 2026-08-06, ainda em `Proposto`, por medição na A40.l18. A
  > previsão original era "diff vazio esperado" e teria reprovado o PR que
  > cumpre a §3: [`backend/app/schemas/pipeline.py`](../../backend/app/schemas/pipeline.py)
  > declara `status: PipelineStageStatus` em `PipelineStageLogResponse`, logo o
  > enum de stage é superfície pública de API. O raciocínio original cobriu só o
  > status de run.
- Débito nomeado, **não** corrigido aqui: `StageSpec.writes` é ficção para
  `generate_narratives` (declara chave própria, escreve na do E5) e
  `validate_cross` (declara chave, é read-only). `validate_full_order` valida um
  grafo com 2 arestas fictícias.
- **Prevenção herdada de [[ADR-358]]:** decisão cujo enforcement depende de
  evidência futura nasce `Proposto`, ou nasce `Decidido` com o gate registrado em
  `OWNER-GATED-active.md`. `Decidido` + "validar depois" foi o defeito que
  produziu o incidente de origem.
