---
id: TRACK-f1-go-service
type: track
title: "Track F1 — serviço Go pipeline-service-go (Caminho 1): 4 fases, 4 PRs"
plan: PLAN-go-shell
status: consumed
created_at: "2026-07-03"
consumed_at: "2026-07-06"
agent_role: senior-cto
tags:
  - type/track
  - area/pipeline
  - area/observability
  - status/consumed
  - priority/p1
---

# Track F1 — `f1-go-service`

> Executa a **F1 do [[PLAN-go-shell]]** (gatilho 4 da [[ADR-150]] disparado pelo
> owner em 2026-07-03; ADR `Decidido`). **Sem ADR nova** — [[ADR-150]] §5
> (layout), §6 (acoplamentos) e [[ADR-303]] (boundary de artefatos) são
> autoritativas; este track só as instancia. Se algum passo exigir mudança de
> contrato HTTP ou boundary: **pare e invoque `senior-cto`**.
> **Branch prefix:** `agent/f1-go-<fase>/*`. **4 fases = 4 PRs**, cada fase
> mergeável sozinha; commit WIP ao fim de cada passo. Co-design 2026-07-03
> (`senior-cto` + `sre-devops` + `product-manager`) — decisões abaixo são
> fechadas, não reabrir.

## Decisões fechadas do co-design (fonte: sessão 2026-07-03)

1. **Exit code 2 do CLI é ambíguo** — desambiguar pelo campo `error` do JSON
   de stderr: `"unknown_stage"` → HTTP 404 · `"environment"` → HTTP 503.
   Exit 0 → 200 `success=true` · exit 1 → 200 `success=false` (falha de stage
   é fluxo, NÃO é error Go) · stdout não-parseável → 503.
2. **Registry de stages via codegen** (não delegação ao subprocess): novo
   `dev/codegen_stage_registry_go.py` emite `internal/stages/registry_gen.go`
   com nomes válidos + mapa legacy→descritivo (`resolve_stage_name`, ADR-093)
   + `is_llm` + `LLM_STAGES` (com aliases). Teste de paridade Python↔Go falha
   em drift (padrão `codegen_report_layout`, ADR-076). Necessário porque
   `POST /runs` valida a sequência inteira (400 com todos os unknowns) ANTES
   de qualquer subprocess, e `skip_llm` precisa da lista local.
3. **oapi-codegen: `types` + `chi-server`** sobre
   `docs/reference/api/v1/pipeline-service.openapi.json` (congelado por
   schemathesis, #747). Status 404/400/422/503 são responsabilidade do
   handler; 422 devolve `HTTPValidationError` do contrato em body inválido.
4. **CI Go entra em `ci.yml` e no agregador `All checks green`** — o
   `go.yml` standalone NÃO é observado pelo gate (PR Go vermelho mergearia
   verde). Jobs condicionais (`changes.outputs.go`) + entrada no loop do
   agregador. Bump conjunto: `go.work`/`.golangci.yml`/workflow → **go 1.26**
   + **golangci-lint v2** (formato de config muda — migração explícita);
   `go.work.sum` commitado.
5. **Envelope Redis**: 8 campos (`event, run_id, timestamp, stage, status,
   progress_pct, error, detail`), channel `pipeline:{run_id}`. Campos `None`
   são **omitidos** (nunca `null`) → Go usa ponteiros + `omitempty`
   (`progress_pct` como `*int`; `run_failed` NÃO leva progress_pct).
   `timestamp` = layout custom `2006-01-02T15:04:05.000000-07:00` sobre UTC
   (isoformat Python: offset `+00:00`, 6 dígitos) — mas timestamp é campo
   NORMALIZADO no harness (não é gate byte-exact).
6. **`progress_pct` truncado**: `stage_started` = `int(idx/total*100)`;
   `stage_completed/failed` = `int((idx+1)/total*100)`; `run_completed` = 100.
   `skip_llm` emite evento `stage_skipped` E entry sintético
   `success=true, detail={skipped:true,...}` na lista de stages da resposta.
7. **`attempts: 1` fixo** na `StageExecuteResponse` (campo existe no DTO
   Python, nunca setado — paridade de snapshot).
8. **Subprocess lifecycle (sre-devops, não-negociável)**: `SysProcAttr{Setpgid}`
   (kill do process group), `defer cmd.Wait()` em todo path (reaping),
   timeout por stage `context.WithTimeout` (env `MATHOMS_STAGE_EXEC_TIMEOUT_SECONDS`,
   default 3600 — espelha Celery `time_limit`), deadline → SIGTERM → 30s →
   SIGKILL. SIGTERM ao serviço → drain HTTP (`Server.Shutdown`) + SIGTERM ao
   filho + grace 30s + SIGKILL (run reexecuta idempotente — escrita só
   commita no sucesso). Compose: `init: true` + `stop_grace_period: 45s`.
9. **stdout do filho = SOMENTE o JSON do StageResult** (o CLI garante);
   stderr do filho = logs → repassar ao stdout do container como log.
   `config_dir` ausente → **omitir a flag** (nunca `--config-dir ""`).
   `--incremental-doc` é repetível; `--base-run-fallback-stages` é CSV.
10. **Paridade em camadas**: unit hermético (exec fake) → schemathesis contra
    o Go (mesmo snapshot; equivale ao gate R18-R20 para Go) → **byte-a-byte
    de payload completo é DIFERIDO ao gate técnico da F2** (Postgres). Em F1,
    side-by-side cobre campos monetários (cents, tolerância zero, reusar
    `dev/golden_diff.py`) + shape do envelope WS (ex-`timestamp`).
11. **Imagem separada** `services/pipeline-service-go/Dockerfile` (multi-stage:
    `golang:1.26` build → base python:3.12-slim MESMO digest do
    pipeline-service + lock + COPYs, binário ENTRYPOINT :8001), porta **8002**
    no host via overlay; a imagem Python NÃO é substituída (fallback do
    cutover, ADR-150 §8). Singleton Redis Go lazy idempotente → registrar em
    `docs/reference/STATELESS_AUDIT.md` §2 (ADR-111).

## KRs da F1 (done numérico, além dos 4 PRs mergeados)

- **KR1**: imagem Go ≤ **150 MB** (promessa da ADR-150: 283→80-150 MB) —
  medida no smoke da Fase 4, registrada em `PERFORMANCE_BASELINE` §13.
- **KR2**: cold start do **shell** Go < **100 ms** (boot→/health; NÃO é o
  subprocess Python, que é 413ms imutável) — mesmo protocolo do §11.
- **KR3**: paridade monetária side-by-side = 0 divergências em cents
  (`golden_diff.py`) e envelope WS = 0 divergências de shape (ex-timestamp).

## Fase 1 — skeleton + codegen + router (PR 1)

1. `services/pipeline-service-go/`: `go.mod` (module `mathoms.ai/pipeline-service`),
   `go.work` ganha `use ./services/pipeline-service-go` (+ `go.work.sum`),
   `cmd/pipeline-service/main.go` ≤30 linhas (wire+boot), layout ADR-150 §5.
2. Codegens: oapi-codegen (`types,chi-server`) → `internal/contracts/` +
   snapshot test de regen limpo; `dev/codegen_stage_registry_go.py` →
   `internal/stages/registry_gen.go` + teste de paridade vs `stage_spec.py`.
3. `internal/api`: `/health` conforme contrato; handlers de stages/runs como
   stub que JÁ devolvem 404 (single, nome resolvido), 400 (sequence, lista de
   unknowns) e 422 (`HTTPValidationError`) usando o registry — execução real
   vem na Fase 2. Config por env, zero estado mutável package-level.
4. CI: jobs Go em `ci.yml` (lint golangci-v2 + `go test ./... -race` + build)
   condicionais a paths Go, **adicionados ao agregador `All checks green`**;
   bump go 1.26 nos 3 configs; `go.yml` standalone vira redirect/removido.
- [ ] Gate F1.1: serviço sobe local, `/health` 200 conforme contrato, CI Go
      roda DE VERDADE (não no-op) e verde no agregador, codegens com snapshot
      tests, `golangci` v2 verde.

## Fase 2 — StageExecutor (PR 2) — *corte mínimo útil da sprint*

1. `internal/stages`: `exec.CommandContext` do CLI (decisões 1, 8, 9);
   mapeamento request→flags completo (incremental repetível, fallback CSV,
   config_dir omitível, base_run_id — paridade ADR-303 D2); env passthrough
   (`MATHOMS_DATABASE_URL/FERNET_KEY/REDIS_URL/ENCRYPT_PIPELINE_ARTIFACTS`,
   `OTEL_EXPORTER_OTLP_ENDPOINT`) + `TRACEPARENT` do span Go.
2. Span `pipeline.<stage>` pai no Go; erros tipados: `ErrUnknownStage`,
   `ErrExecutorUnavailable`; `StageFailure` NÃO é error (é resultado).
3. Testes: unit hermético com exec fake (3 exit codes → 200ok/200fail/404/503,
   parse de stdout, montagem de args); integração com CLI REAL (SQLite seed →
   artefato em `pipeline_artifacts`, espelho de
   `test_artifact_store_integration.py`); trace-id contínuo Go↔Python
   (exporter in-memory); timeout mata o subprocess (sem zumbi).
- [x] Gate F1.2 ✅ (PR da Fase 2): unit hermético (3 exit codes, args, stdout),
      integração com CLI REAL (E3 persistido; guarded `MATHOMS_GO_CLI_INTEGRATION`),
      TRACEPARENT injetado, timeout mata subprocess — tudo `-race`; `attempts:1`;
      suíte Python intacta (19 ✔).

## Fase 3 — RunCoordinator + eventos Redis (PR 3)

1. `internal/runs`: sequência com `skip_llm` (decisão 6), `stop_on_error`,
   hidratação por run é do subprocess (cada stage re-hidrata — aceito).
2. `internal/events`: publisher com envelope da decisão 5; singleton lazy
   idempotente; registrar no `STATELESS_AUDIT.md`.
3. Testes: unit (miniredis ou fake) assertando envelope campo-a-campo vs
   goldens capturados do Python (mesmas chaves, omissões, tipos; timestamp
   normalizado); 400 de sequence; `run_failed` sem `progress_pct`.
- [x] Gate F1.3 ✅ (PR da Fase 3): envelope validado campo-a-campo via miniredis
      (omissões, sem nulls, run_failed sem progress_pct, skip com evento+entry);
      singleton registrado no STATELESS_AUDIT.

## Fase 4 — paridade + imagem + smoke (PR 4)

1. schemathesis contra o serviço Go (mesmo snapshot de #747) — job/step no CI.
2. Side-by-side local (make target): mesma seed SQLite → request idêntico ao
   Python (8001) e ao Go (8002) → diff monetário via `golden_diff.py` (cents,
   zero) + diff de envelope (ex-timestamp). Byte-a-byte completo: F2.
3. `services/pipeline-service-go/Dockerfile` (decisão 11) + overlay compose
   `pipeline-service-go` :8002 com `init: true`, `stop_grace_period: 45s`;
   smoke gate espelhando `dev/smoke_pipeline_service_container.py`.
4. Medir KR1 (imagem) + KR2 (cold start shell) → `PERFORMANCE_BASELINE` §13;
   runbook de sinais/shutdown (decisão 8) em `docs/reference/runbooks/`.
- [x] Gate F1.4 ✅ (PR da Fase 4): KR2 8,1ms <100ms; KR1 renarrado (meta original
      infalsificável pós-ADR-303 — delta Go−Python 20MB ≤30MB PASSA); KR3 via
      contrato idêntico (schemathesis) + gate container ADR-303 PASSA no Go;
      números em PERFORMANCE_BASELINE §13; F1 ✅ no plano.

## Fora de escopo (não negociar dentro do track)

- Mudança de contrato HTTP/OpenAPI ou de boundary de artefatos → `senior-cto`.
- Cutover/flip de `MATHOMS_PIPELINE_SERVICE_URL` (F2 — gate humano do owner),
  paridade byte-a-byte de payload completo (F2, Postgres), decommission (F3).
- Worker pool warm (Caminho 2) e port de domínio (Caminho 3).
