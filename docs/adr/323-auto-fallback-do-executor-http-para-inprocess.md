---
id: ADR-323
type: adr
title: "Auto-fallback do executor HTTP para InProcess (circuit breaker do cutover Go)"
status: Proposto
date: "2026-07-08"
relates_to: ["[[ADR-112]]", "[[ADR-150]]", "[[ADR-303]]", "[[TRACK-f2-cutover]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
  - area/observability
---

# ADR-323 — Auto-fallback do executor HTTP para InProcess (circuit breaker do cutover Go)

**Status:** Proposto · **Data:** 2026-07-08 · Follow-up do co-design `senior-cto`
de [[TRACK-f2-cutover]] §Follow-ups.

## Contexto

No cutover para o shell Go ([[ADR-150]]), o worker de prod executa cada stage
via `HttpPipelineClient.execute_stage` ([[ADR-112]]). Hoje ele faz
`resp.raise_for_status()` **sem fallback**: se o shell Go (:8002) está down
(`ConnectError`) ou responde 5xx, **todo run hard-falha** até `go-off` manual
(unset da env var → restart). A reversibilidade da [[ADR-150]] §8 é um restart
(RTO ≤1min), não hot-reload — então uma janela de indisponibilidade do shell
quebra **todos** os runs até intervenção humana. Esta é a maior fragilidade
estrutural do desenho do cutover (não bloqueante da F2, mitigada por alerta de
health + rollback rápido, mas de blast radius catastrófico).

Queremos transformar "shell down = todos os runs quebrados" em "shell down =
runs continuam via `InProcessPipelineClient`" (o executor batido em prod),
**sem** mascarar o sinal que o rollback do cutover depende.

## Decisão

**1. `FallbackPipelineClient` — decorator, não herança.** Uma terceira
implementação do Protocol `PipelineServiceClient` compõe `primary`
(`HttpPipelineClient`) + `fallback` (`InProcessPipelineClient`). O transporte
HTTP fica no primary; a **política de resiliência** (classificação de gatilho,
sticky, telemetria) fica no decorator — SRP preservado, trivialmente testável.

**2. Gatilho por IDENTIDADE de falha de transporte, nunca por valor.** Degrada
**apenas** em `httpx.ConnectError`/`ConnectTimeout`/`PoolTimeout` (conexão nunca
estabelecida → shell garantidamente não commitou) **e** HTTP 5xx (o executor Go
faz rollback da sessão por-stage em qualquer exceção — [[ADR-303]]). **Não**
degrada em: `200 + success=False` (falha de domínio — re-rodar InProcess
reproduziria idêntico e mascararia falha real), `4xx` (bug de contrato — stage
inválido/payload ruim; InProcess bateria no mesmo bug), `ReadTimeout` (o stage
pode ainda estar rodando no shell e commitar depois → risco de double-write
concorrente; o `time_limit=3600` do Celery mata o hang).

**Split obrigatório do `httpx.Timeout`:** `connect=pool=5s`, `read=write=3600s`.
Um timeout flat de 3600s faria `ConnectTimeout`/`PoolTimeout` pendurar 1h antes
de degradar — pior que o hard-fail. Read/write generosos preservam stages LLM.

**3. Circuit breaker sticky, run-scoped.** No primeiro stage que degrada, seta
`ctx.shell_degraded = True`; os stages seguintes do **mesmo run** vão direto ao
InProcess sem re-sondar o shell caído. Uma sondagem, um evento de telemetria por
run — não 18 tentativas de connect contra um Go já sofrendo. O estado vive no
`ctx` (request/run-scoped, exceção [[ADR-111]] §1.b já usada por `artifact_store`)
— **nunca** no singleton do client (envenenaria runs cross-worker).

**4. Idempotência stage-level por construção.** `ConnectError`/5xx **garantem**
que o subprocess Go terminou (rollou back / morreu) antes do InProcess rodar, e
`DBArtifactStore.write` é read-then-update: uma row que o shell tenha commitado
para `(run_id, stage, key)` vira **UPDATE** numa sessão fresca, não colisão da
`uq_pipeline_artifacts_run_stage_key`. Run com executor misto (alguns stages Go,
alguns InProcess) **não** viola paridade — o código de domínio é idêntico; só
muda quem invoca o subprocess. **Pré-condição de flip:** o shell Go deve fazer
reap/kill do subprocess **antes** de responder 5xx (um zumbi commitando tarde
enquanto o InProcess re-roda seria o único caminho de double-write) — amarrado ao
lifecycle hardening do rollback trigger #6 do [[TRACK-f2-cutover]].

**5. Telemetria LOUD, nunca silenciosa.** Um ERROR estruturado
`event=pipeline_shell_fallback` (logger `mathoms.pipeline.*`, correlacionável por
`run_id`/`workspace_id`/`stage`/`trigger_class`) na virada do circuito + marcador
`_shell_fallback` em `StageResult.detail` → `pipeline_stage_logs.output_summary`
(DB, consultável pelo ledger do soak). O marcador não toca `pipeline_artifacts`,
então `go_parity_gate` fica intocado.

**6. Default OFF durante o soak, ON pós-F3.** Env var
`MATHOMS_PIPELINE_SHELL_FALLBACK` default `0`. Racional: o custo/benefício
**inverte** na fronteira do soak. Durante o soak (prod dogfood do owner), o
fallback converteria o rollback trigger #2 ("1 falha shell-caused → rollback")
num degrade — o run **sucede** via InProcess, e não há `run_failed` para o
trigger medir; o soak passaria enganado sobre a estabilidade do Go. Ship do
código em F2 como **dark launch** (testado e gated); o owner flippa `1` como
parte da estabilização **pós-F3**, quando há usuários reais a proteger e o soak
acabou. `=0` preserva exatamente o hard-fail legado (`get_pipeline_client()`
devolve `HttpPipelineClient` cru).

## Consequências

- ✅ Blast radius do cutover cai de catastrófico (todo run quebra) para degrade
  observável (run completa via InProcess, sinal LOUD).
- ✅ Kill-switch por env var; zero mudança no loop de `pipeline_task` (o
  decorator encaixa no gerenciamento de sessão por-stage existente).
- ✅ Sem mudança de contrato HTTP → sem `update-openapi-snapshot` (o boundary
  `PipelineServiceClient` é interno, sem snapshot).
- ⚠️ O fallback pré-empta o retry de 5xx do `_run_stage_with_retry` (o decorator
  consome o 5xx antes do wrapper ver exceção) — intencional (degrade-first).
- ⚠️ 5xx conflaciona infra-Go (502/503/504 — degrade limpo e valioso) com
  exceção-de-stage (500 — re-roda InProcess e reproduz; correto mas desperdiça
  minutos). Follow-up de contrato: exceção-de-stage → `200 + success=False`; infra
  → 503 `executor_unavailable`. Até lá 500 degrada (seguro pela idempotência §4).

## Alternativas rejeitadas

- **Fallback dentro do `HttpPipelineClient`** — dá duas responsabilidades ao
  client (transporte + resiliência); rejeitado por SRP.
- **Per-stage não-sticky** (re-sondar o Go a cada stage) — anti-padrão de
  circuit-breaker; martela um Go caído N vezes por run.
- **Default ON durante soak** — mascara a instabilidade transitória que o soak
  existe para falsificar; "o ledger lê o contador" é guarda mais frágil que
  simplesmente não mascarar.
- **Emenda na [[ADR-112]]/[[ADR-150]]** — a 112 é Decidido/histórico (só o
  contrato feliz); a 150 já passa do teto de linhas. ADR nova é a forma atômica
  ([[ADR-182]]).

## Artefatos

- `backend/app/services/pipeline/pipeline_client.py` — `FallbackPipelineClient`,
  split de timeout, toggle em `get_pipeline_client()`.
- `pipeline/context.py` — campo `WorkspaceContext.shell_degraded`.
- `backend/tests/test_pipeline_client.py` — gatilho/sticky/kill-switch/isolamento.
- `backend/tests/test_db_artifact_store.py::test_cross_session_rewrite_is_idempotent`
  — a fundação de idempotência cross-executor (§4).
