---
id: ADR-355
type: adr
title: "Intenção \"sem LLM\" do run é propagada até o stage, não só até a lista de stages"
status: Decidido
phase: A40 (dívida independente da F2 do GO_SHELL)
date: "2026-07-31"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-150]]"
  - "[[ADR-173]]"
  - "[[ADR-303]]"
  - "[[ADR-329]]"
  - "[[A41.l1]]"
  - "[[A41.l2]]"
  - "[[A41.l3]]"
  - "[[A41.l4]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
---

# ADR-355 — Intenção "sem LLM" do run é propagada até o stage, não só até a lista de stages

## Contexto

`skip_llm` promete run determinístico e zero gasto de LLM. Ele cumpre **metade**:
filtra a lista de stages por `is_llm` (`DETERMINISTIC_ORDER` vs `FULL_ORDER`) e
nunca chega aos wrappers. Stage não-`is_llm` que faz chamada LLM **condicional**
continua chamando.

Medido neste worktree (spy nomeado sobre `anthropic.Anthropic`, sem API):
`route_documents.run(ctx)` sobre 1 documento de conteúdo genérico → **1 chamada
LLM**, e o documento é roteado com base na resposta do modelo. No workspace de
dogfood há 14 documentos abaixo do threshold de 0,8 ([[ADR-081]] camada 2).

São **quatro** superfícies, não três — a emenda 2026-07-31 da [[ADR-150]]
subcontou:

| superfície | stage (não-`is_llm`) | gate hoje |
| --- | --- | --- |
| fallback de classificação ([[ADR-081]] camada 2) | `route_documents` | `use_llm=True` hardcoded |
| `section_summaries` | `generate_narratives` | env `MATHOMS_LLM_SECTION_SUMMARIES` |
| extração por visão de PDF sem camada de texto | `extract_statements` / `extract_invoices` | **nenhum** (`scripts/e2/banks/caixa.py::_extract_via_llm`) |
| stub `requires_llm_fallback` | `extract_statements` / `extract_invoices` | não gasta LLM — consumido por `extract_with_llm`, que é `is_llm` |

Duas consequências não-óbvias da terceira linha: `requires_llm_fallback` só é
gravado **depois** que a chamada de visão falha, logo "0 `requires_llm_fallback`
no artefato" **não prova zero invocação**; e como E0, E2-caixa e narrativas
passam por fora do `LLMService`, asserção empírica de "0 chamada" só é confiável
no boundary do SDK `anthropic`, não instrumentando o choke-point.

A degradação sem LLM não é "`doc_type` errado": `needs_review` → o documento
**fica no inbox** e não entra em `data/`, logo E1/E2 nunca o veem. Um run com
`skip_llm=True` analisa um **corpus menor** que o run full — hoje sem nada no
registro do run dizendo isso. É auto-curativo entre runs (o arquivo continua no
inbox), o que limita o dano a "relatório incompleto", não "documento perdido".

## Decisão

**`skip_llm` filtra stages; `WorkspaceContext.llm_calls_allowed` governa chamada
LLM *dentro* de stage.** São semânticas distintas com nomes distintos, ligadas
por uma negação única em `build_hydrated_context(skip_llm=...)` — os três
executores (Celery, HTTP, CLI) hidratam por ali.

Invariante greppável: **todo call-site novo de LLM em stage não-`is_llm` lê
`ctx.llm_calls_allowed`.** Sem isso, a próxima superfície repete o bug.

`skip_llm` permanece o vocabulário do wire (request HTTP, flag CLI, contrato Go)
— simetria com `--incremental` e negação em um lugar só.

Bool, não value object: as superfícies consomem **o mesmo bit único**. Tier,
budget, cache e métricas já têm casa própria no contexto (`llm_call_hooks`,
`llm_response_cache`, `llm_metrics_emitter`). Promover a VO quando aparecer a
segunda dimensão — a promoção é barata porque todos leem por um nome só.

**Degradação carrega sinal tipado**, nunca `needs_review` silencioso:
`classification_meta.llm_skipped_reason = "llm_disabled_for_run"`, membro de
`RETRIABLE_SKIP_REASONS` ([[ADR-329]]) — a pré-condição volta num run premium.
`needs_review` já acumula 5 causas e não distingue "não perguntamos" de
"perguntamos e ficou ambíguo".

## Escopo

Fechado agora: E0 + narrativas + as 5 camadas de propagação (contexto,
`run_context_factory`, contrato HTTP per-stage + client, CLI `--skip-llm`, Go
`BuildArgs`) + orquestrador puro (`run_stages`/`run_pipeline`, usado por testes e
`dev/`).

Deferido, com motivo (organizado na [[A41]] em 2026-08-03):

1. **Caixa E2** — [[A41.l3]]. `parser_fn(file_path, filename)` é contrato
   uniforme de ~10 módulos em `scripts/e2/banks/`; threading exige mudar todos.
   **Não** resolver com global nem contextvar ([[ADR-111]]). A lane reabre o
   enquadramento: `extract_with_llm` já é o caminho gated e a Caixa é o único
   banco que o atalha, então o fix pode ser deletar o call-site em vez de
   propagar o contexto.
2. **Rotear E0 + caixa pelo choke-point** — [[A41.l2]] (E0) e [[A41.l3]]
   (caixa). É o buraco maior: sem hard-stop de budget ([[ADR-173]]), sem
   `LLMCallLog`, sem cache ([[ADR-307]]), sem métricas ([[ADR-110]]), sem
   sanitização de prompt-injection ([[ADR-175]]) — e o caixa manda PDF
   financeiro inteiro em base64 para a API. Depois disso, o choke-point vira
   *enforcement* e o contexto segue sendo *política*. O gate que fecha a rota
   alternativa é [[A41.l4]].
3. **Free tier.** Hoje `tier == "free"` pula stages `is_llm` mas o E0 continua
   gastando. Ligar `llm_calls_allowed=False` para free é decisão de produto
   (gate: `gtm-strategist` + `product-manager`), com regressão real de qualidade
   — não viaja sob título de bugfix. O contador `llm_classified` deste PR mede
   exatamente quantos documentos por run só rotearam graças ao LLM. Registrado
   como decisão pendente em [[A41]], **não** como lane: o número não é
   mensurável com validade sobre um corpus premium curado.

Achado colateral desta implementação, organizado em [[A41.l1]]: a asserção
"0 LLM" do gate F2 conta artefato de stage `%llm%` e não vê chamada de visão
bem-sucedida.

Não bloqueia a F2 do GO_SHELL: o gate (`dev/go_parity_run.py`, #1136) contorna
o E0 exigindo **inbox vazio** como pré-condição — sem documento para classificar,
a superfície não dispara.

## Alternativas rejeitadas

- **Mudar a assinatura `run(ctx)` dos stages.** 18 runners + `_run_stage` +
  pipeline-service + CLI + testes, e espalha política de run em toda assinatura.
- **Enforçar no choke-point em vez de propagar.** Inviável hoje: o E0 não está
  no choke-point (chama o SDK direto). Vira o deferido 2.
- **Chamar o campo do contexto de `skip_llm`.** Colar os nomes funde as duas
  semânticas e multiplica a negação por fan-out — três lugares para errar a
  polaridade e produzir o bug ao contrário (run full sem LLM).
- **Erro no boundary para `is_llm` + `skip_llm=true` no endpoint per-stage.**
  Rejeitada: o caminho in-process **pula** essa combinação com sucesso; errar só
  no HTTP recria divergência entre executores — a classe de bug que esta ADR fecha.

## Consequências

Positiva: `skip_llm=True` passa a cumprir o que promete nos três executores, e o
corpus do run determinístico deixa de encolher em silêncio.

Negativa: run determinístico sobre corpus com documentos de baixa confiança rende
relatório com menos documentos que o run full — agora **declarado** no `detail`
do stage (`llm_calls_allowed`, `inbox_review`, `llm_classified`) e com warning
quando ambos disparam.

Para o track de cutover Go: `_llm_artifact_count` (`dev/go_parity_run.py`) conta
artefato de stage `%llm%` — não vê uma extração de visão **bem-sucedida** do
parser Caixa, que grava artefato normal de `extract_statements`. A asserção
empírica de "0 chamada" só fecha hookando o SDK `anthropic`.
