---
id: ADR-443
type: adr
title: "Stage roda uma vez por run — não há retry de stage em executor nenhum"
status: Decidido
date: "2026-10-08"
relates_to:
  - "[[ADR-270]]"
  - "[[ADR-357]]"
  - "[[ADR-323]]"
  - "[[ADR-284]]"
  - "[[ADR-291]]"
  - "[[ADR-112]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 443"
  - "stage roda uma vez"
  - "retry de stage apagado"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
---

# ADR-443 — Stage roda uma vez por run: não há retry de stage em executor nenhum

> Co-design 2026-10-08 com `senior-cto`. Nasce `Decidido` porque o enforcement é teste
> no mesmo PR (`backend/tests/test_run_stage_once.py`). Retrata o item 3 da
> [[ADR-270]] §Emenda 2026-08-15 e a abertura da [[ADR-357]] §8; deixa sem objeto a
> guarda de retry da [[ADR-284]] §A e a ressalva de retry da [[ADR-323]] §Consequências.

## Contexto

`STAGE_RETRY_CONFIGS` declarava retry de stage para `extract_members`,
`extract_baseline`, `extract_with_llm` (2×) e `review_finances_holistic` (1×), aplicado
por `_run_stage_with_retry` só no ramo `except`. Duas emendas mexeram no vocabulário
da tabela (A40.l18 PR2, 2026-08-07; [[ADR-270]], 2026-08-15) e as duas afirmaram efeito
sobre o run. **Nenhuma mediu o run.** Medido em 2026-10-08:

- **In-process (o executor de produção).** `pipeline/orchestrator.py::_run_stage`
  converte toda `Exception`/`SystemExit` do runner em `StageResult(success=False)` desde
  2026-04-13, e o retry nasceu no dia seguinte já envolvendo esse `_run_stage`. Probe pela
  composição de produção (`get_pipeline_client()` → `_run_stage` → runner levantando
  `LLMError` de overload): runner chamado 1×, 0 sleeps. **A tabela nunca operou em
  produção** — nos 4 stages, não só no parecer, como a [[ADR-357]] §8 registrava.
- **Shell Go ([[ADR-112]], owner-gated, não flipado).** O executor roda
  `pipeline/cli_run_stage.py`, que chama o mesmo `_run_stage` e responde `200` com
  `success=false`: a exceção do runner também não chega. Chega falha de **transporte**,
  e ali a tabela operava por acaso, casando needles de LLM no texto do `httpx`:
  `ConnectError`, `503` do executor, `ReadTimeout` e `RemoteProtocolError` faziam
  **3 POSTs com backoff 10/20s**, os dois últimos **com o fallback da [[ADR-323]]
  ligado** — a re-execução que a §2 dela recusa (o stage pode seguir rodando no shell e
  commitar depois).

## Decisão

1. **O stage roda uma vez por run, nos dois executores.** `retry_config.py` sai;
   `_run_stage_with_retry` vira `_run_stage_once`, a fronteira de exceção de tentativa
   única — ainda necessária para o que cruza o executor (transporte HTTP, import do
   runner).
2. **Cada camada é dona do próprio transiente.** O de LLM é do `LLMService.call`
   ([[ADR-270]]: 4 tentativas, backoff, escalada de timeout), que fecha com
   `retryable=False`; o de transporte do shell é da composição do client
   (`FallbackPipelineClient`, [[ADR-323]]). Uma camada acima reclassificaria o que a de
   baixo já fechou.
3. **Retentar um stage é run novo com `from_stage`** ([[ADR-291]]) — a metade da
   [[ADR-357]] §8 que continua de pé: degradável não retenta dentro do run.
4. **`output_summary.attempt_count` deixa de ser gravado e sai do `FailedRunCard`.** Um
   `1` fixo se leria como "não houve retry", falso na camada que tentou 4×. O sufixo
   `(after N attempt(s))` de `errors` sai junto.

## Alternativas rejeitadas

- **Manter a tabela escopada ao caminho HTTP.** Ali ela só vê transporte, com vocabulário
  de LLM, só para 4 stages, e religa a re-execução que a [[ADR-323]] §2 recusou; com o
  fallback desligado, ainda esconderia do soak a falha do shell que a §6 quer ver.
  Resiliência de transporte, se faltar, é da composição do client e por tipo de exceção —
  nunca por substring.
- **Religar de propósito** (o executor deixar a exceção transiente subir até o retry).
  Layering sobre o `LLMService`, cuja exceção final já diz `retryable=False`; re-paga as
  calls que o stage já fez (sem cache por default); e no incidente da emenda de
  2026-08-15 da [[ADR-270]] — EOF persistente aos 120s — só multiplicaria o wall-clock
  que aquela ADR existe para cortar.

## Consequências

- **Produção não muda:** o retry nunca operou in-process. Se a taxa de falha do Premium
  por transiente de LLM pedir mais resiliência, o lugar é o orçamento do
  `LLMService.call`, fonte única — não uma segunda camada.
- **Shell Go perde o retry acidental de blip curto com o fallback desligado.** Aceito: é o
  sinal do soak, e pós-F3 o fallback degrada.
- `_is_schema_validation_error` sai: a guarda da [[ADR-284]] §A protegia um backoff que
  não existe mais. `ValidationError` roda uma vez por construção.
- Retratações datadas em [[ADR-270]] e [[ADR-357]]; notas de obsolescência em
  [[ADR-323]] e [[ADR-284]]; lanes [[A40.l18]] e [[A40.l58]] anotadas.

## §Deferimento — a classe da falha do runner não sobrevive ao executor (2026-10-08)

O mesmo achatamento apaga o `reason_class` da [[ADR-357]] §2. `reason_from_exception`
só vê o que cruza o executor; exceção do runner grava `reason_class: unknown` via
`reason_from_stage_detail`. `budget_exhausted`, `timeout`, `provider_error` e o
`output_invalid` do abort do flip strict ([[A40.l58]]) **nunca chegaram ao card de
`/admin/metrics`**, antes ou depois da correção de 2026-08-24. Não entra aqui porque o
classificador mora em `backend/` e `pipeline/` não pode importá-lo: levar a classe no
`StageResult.detail` (que o shell Go repassa sem quebrar contrato) pede desenho de
boundary próprio.

- **Dono:** `senior-cto` (desenho do boundary); execução em lane a abrir.
- **Retomar antes de:** o flip `warn → strict` do schema, ou a primeira triagem que
  filtre o card por `reason_class`. Até lá, o §8.1 do runbook do flip
  (`docs/reference/runbooks/schema_validation_strict_flip.md`) filtra pela mensagem do
  raise.
- **Gate que cobra:** `test_classe_da_falha_do_runner_sobrevive_ao_executor`,
  `xfail(strict=True)` — fica vermelho quando a classe passar a sobreviver, e obriga a
  reescrever o §8.1.

## Critério de aceite

- `backend/tests/test_run_stage_once.py`:
  - composição de produção in-process: todo stage LLM que levanta transiente roda 1×,
    sem sleep, e termina `failed` ou `degraded` pela criticidade;
  - caminho HTTP (`MockTransport`): `RemoteProtocolError` e `ReadTimeout` com fallback
    ligado, `ConnectError` e `503` com ele desligado — 1 POST cada (eram 3);
  - o `xfail` estrito do §Deferimento.
- Mutações provadas: retry na fronteira reprova os 4 casos HTTP; retry sobre
  `success=False` reprova a composição in-process.
