---
id: TRACK-f2-cutover
type: track
title: "Track F2 — cutover do pipeline-service-go (Caminho 1): gate técnico + gate humano + flip em prod"
plan: PLAN-go-shell
status: ready
created_at: "2026-07-08"
agent_role: senior-cto
tags:
  - type/track
  - area/pipeline
  - area/observability
  - status/ready
  - priority/p1
---

# Track F2 — `f2-cutover`

> Executa a **F2 do [[PLAN-go-shell]]** (cutover), autorizada pelo owner em
> 2026-07-08. **Sem ADR nova** — [[ADR-150]] §7 (cutover) + §8 (coexistência)
> são autoritativas; a emenda datada 2026-07-08 na [[ADR-150]] registra a
> reinterpretação do critério de paridade (byte-a-byte vs. não-determinismo
> LLM) e a correção do fallback de prod. Este track só as instancia.
> **Co-design 2026-07-08** (`senior-cto` = gate técnico; `sre-devops` = rollout,
> rollback, soak, observabilidade) — decisões abaixo são fechadas, não reabrir.
> Se algum passo exigir mudança de contrato HTTP ou de boundary de artefatos:
> **pare e invoque `senior-cto`**.
> **Branch prefix:** `agent/go-f2-<slice>/*`.

## Estado de entrada (reconciliação factual 2026-07-08)

O `_README` do plano descrevia uma "pré-condição adicional" pendente; **ela já
está fechada**. O que resta de F2 é gate + flip, não código de produto:

| Item | Estado real | Evidência |
|---|---|---|
| Paridade de hidratação de contexto (DBConfigStore, resolvers, budget hooks, tarefas.md) | ✅ fechada 2026-07-03 | `backend/app/services/pipeline/run_context_factory.py::build_..._context` — fonte única dos 3 executores; [[ADR-303]] §Escopo deferido (PR #742) |
| Enablement do smoke em container/compose | ✅ fechado 2026-07-03 | [[ADR-303]] §Escopo deferido (PR #743) |
| Fiação do toggle | ✅ pronta | `MATHOMS_PIPELINE_SERVICE_URL` lido em `backend/app/main.py` + worker; `pipeline_client.py::get_pipeline_client()` alterna InProcess↔Http |
| Overlay de dogfood | ✅ pronto | `make go-on/go-off ENV=native\|smoke` sobe o shell Go (:8002), re-aponta o worker Celery, health-check, idempotente |
| Primitiva de diff | ✅ existe | `dev/golden_diff.py` (differ genérico, cents byte-exact) |

**Falta construir:** o harness de paridade de **payload completo** (F1 decisão 10
diferiu-o explicitamente para cá) e o runbook de cutover.

## Pré-condições bloqueantes (antes de qualquer flip)

1. **Postgres em staging.** O gate byte-a-byte de dois processos **exige
   Postgres** — o smoke SQLite tem incoerência WAL host↔container
   (`docs/reference/runbooks/pipeline_service_container_smoke.md §3`). Sem
   staging Postgres-backed, este é o primeiro blocker.
2. **Fixture curada com zero LLM no E2.** O fallback LLM do E2 é condicional
   *dentro* do stage (`requires_llm`, setado por parsers como `wise`/
   `bankofamerica`/`quintoandar` em `scripts/extract_bank_documents.py`) — **não**
   é suprimido por `skip_llm`/`DETERMINISTIC_ORDER`. A fixture de Tier-1 tem que
   ser 100% parseável por regex; o run assert **0 invocações E2-LLM** na
   telemetria, senão o Tier-1 flaka.
3. **`ANTHROPIC_API_KEY`** disponível no env do serviço Go para o Tier-2 (run
   full com narrativas). Owner-gated (custo LLM — orçar; ordem de grandeza
   abaixo dos evals de parecer, mas medir).

## Fase A — gate técnico (`senior-cto`)

Critério diferencial: **`divergência(Go,Python) ⊆ divergência(Python,Python)`**.
Um run de controle Py↔Py pelo mesmo harness mede o piso de ruído; campo que
diverge Go↔Py mas não Py↔Py é bug de executor.

### A1 — harness `dev/go_parity_gate.py`

- **Compõe** `dev/golden_diff.py` como biblioteca (`diff_golden`, `FieldDiff`,
  `is_monetary`, `to_cents`) — **não** estender in-place: o golden_diff tem
  semântica de escape via manifesto de rebaseline (mudança intencional com ADR);
  a paridade Go **não tem escape** (divergência = bug). Misturar polui o SRP e
  arrisca o gate de baseline da A23.l2.
- Responsabilidade do harness novo: orquestrar (subir 8001/8002 via `go-on`),
  semear a fixture, coletar de `pipeline_artifacts` por `run_id` e parear por
  `(stage, artifact_key)`, rodar o controle, comparar envelope WS + span, aplicar
  normalização e tiering.
- **Ler o payload lógico via artifact reader do backend** (decriptado), **nunca**
  a linha crua do DB: com `ENCRYPT_PIPELINE_ARTIFACTS` o `content` tem nonce
  por-escrita → 100% de divergência espúria.
- Vive em `dev/`; roda via `make go-parity` (reusa `go-on ENV=native`).

### A2 — normalização (allowlist fechada, por IDENTIDADE, nunca por VALOR)

- **Identidade:** `run_id`, `pipeline_run_id`, UUID do run → sentinela.
- **Tempo:** `timestamp`, `created_at`, `updated_at`, `generated_at`, `*_at`
  ISO-8601 → sentinela (reusa a lista que o envelope WS já normaliza, F1 dec. 5).
- **Path absoluto:** prefixo = workspace root / storage dir → `<WS>`. **Não**
  normalizar o `arquivo`/`source_document` lógico do E3 (`generate_legacy_filename`
  — determinístico, carrega significado).
- **Ordering:** **não** adicionar sort global (mascara bug). O golden_diff já
  reconcilia listas por `_natural_key`; lista sem chave natural que reordena é
  **finding** (ordenar na fonte ou declarar sort-key estreito para aquele path).
- **Guarda anti-mascaramento:** o controle Py↔Py **com a mesma allowlist** tem
  que dar **0 diff residual**. Sobrou diff → não-determinismo fora da allowlist
  (investigar) ou normalização incompleta → **o gate não está pronto**.

### A3 — Tier-1 (determinístico) — o "byte-a-byte do §7"

`skip_llm=True` → `DETERMINISTIC_ORDER`, fixture sem `requires_llm`. **3× Go vs
3× Python.** Paridade **value-exact/cents-exact de payload completo E0→E5**,
tolerância zero, após normalização. Controle Py↔Py = 0 diff residual. Confirmar
que `DETERMINISTIC_ORDER` produz o conjunto esperado (E1.5, E2, E3, E4,
E5-analysis-sem-narrativa) — nenhum stage intermediário desejado marcado `is_llm`
por engano. Este tier testa **a invocação do subprocess pelo Go** (args/env/
flags), não o domínio (código idêntico).

- **Candidato a job de CI recorrente** (`go-parity-deterministic`, Postgres
  service container, nightly ou on-Go-change) — guarda barata de regressão do
  serviço Go. Não é per-PR.

### A4 — Tier-2 (full) — envelope + span + estrutural

`skip_llm=False` → `FULL_ORDER` (narrativas E5.N). **1× Go + 2× Python.**
- Envelope WS: paridade de **shape + sequência** (timestamp/run_id normalizados);
  eventos de stage LLM existem em ambos (mesmos tipos, mesma ordem).
- Span OTel: attrs normalizados por identidade (`run_id`/`workspace_root`) +
  exatos (`stage`/`is_llm`/`success`/`exit_code`); **continuidade** de trace
  (span filho.trace_id == pai.trace_id) como estrutura, **não** byte-compare de
  `trace_id`.
- Subtrees LLM: paridade **estrutural** (chaves/tipos/cardinalidade/proveniência);
  valores com backstop `⊆ divergência(Py,Py)`. Prosa não é value-gated.
- **Make target owner-run** (custo LLM) — alimenta o gate humano; não é CI.

## Fase B — gate humano (obrigatório, não-pulável — [[ADR-150]] §7)

Owner roda o protocolo [SMOKE_TEST_HUMAN](../../../reference/SMOKE_TEST_HUMAN.md)
sobre o run **full** real em staging e **valida visualmente** o relatório em
`/reports/[id]`. Pega divergência semântica (formatação de narrativa, copy de
status) que escapa da paridade byte-a-byte. Precedente: [[ADR-103]]. **Sem
PASS aqui, não há flip em prod.**

## Fase C — flip em prod (`sre-devops`)

**Rollout decidido:** staging bake → flip **global** no worker de prod (canário
**temporal**, não per-tenant) → watch → widen. Per-tenant (dual-queue) fica
pré-registrado, não construído (prod é efetivamente single-tenant dogfood; a
redução de blast radius de canário per-workspace é ≈zero hoje).

1. **Staging (bake real):** Postgres-backed, `go-on` equivalente, roda Fase A
   (gate técnico, trace-continuity **bloqueante** em staging) + Fase B (gate
   humano). É aqui que o "por workspace" da [[ADR-150]] §7 de fato acontece
   (múltiplas fixtures).
2. **Prod (flip global):** setar `MATHOMS_PIPELINE_SERVICE_URL` em **backend +
   worker** → **restart do worker + backend** (o flip **não é a quente**:
   `get_pipeline_client()` memoiza o singleton por processo; ler a env var só no
   boot). Watch **intensivo nos 3 primeiros runs reais** (espelha o gate
   técnico). Limpo → widen = deixar ligado; o relógio do soak começa.
3. **Honestidade do runbook:** "reverte em segundos" da ADR = **restart**, não
   hot-reload. RTO = 1 restart (segundos–1min). Runs em voo: drain SIGTERM
   (grace 30s) + re-run idempotente (escrita só commita no sucesso).

## Rollback (gatilhos acionáveis — reverter = `go-off`)

Fallback = **unset da env var → `InProcessPipelineClient`** (caminho batido em
prod), **não** o Python HTTP. Todo rollback **zera o relógio do soak** e entra
no ledger com causa + evidência.

| # | Gatilho | Onde medir | Limiar | Ação |
|---|---|---|---|---|
| 1 | Divergência de paridade (cents≠0, envelope WS≠0, ou schema-validation falha no `write()` que não ocorria sob Python) | golden_diff em double-run agendado + logs | **1 ocorrência** | Rollback imediato |
| 2 | Nova classe de falha de stage shell-caused (503 `executor_unavailable`, subprocess morto, stdout não-parseável, env faltando) — verde sob Python, falha sob Go, mesmo input | WS `stage_failed`/`run_failed` + logs | **1 ocorrência** | Rollback imediato (falha de domínio idêntica nos dois **não** é gatilho) |
| 3 | Runs quebrados shell-caused acumulando | WS + `pipeline_runs` | **≥2 na janela** OU ≥1 que quebrou relatório de usuário real | Rollback + incidente (status page <15min se user-facing) |
| 4 | `:8002 /health` não-200 (shell down = todo run hard-fail, sem auto-degrade) | monitor Coolify/externo, 30s | **>90s (3 checks)** | Rollback |
| 5 | OOMKill do container Go (~115MB RSS/subprocess × concorrência) | OOMKilled status, host `free -m`/dmesg | **≥1** | Rollback imediato |
| 6 | Subprocess zumbi/defunct (lifecycle hardening deveria impedir) | host `ps aux \| grep defunct` | >60s → investigar; recorrência → rollback | Rollback na recorrência |
| 7 | Latência de run estoura SLO por causa do shell | `pipeline_runs` / timestamps WS | Free >5min / Premium >15min p95, sustentado | Rollback (boot ~550ms/stage é esperado, não é gatilho) |

**Procedimento:** env var vazia/removida em backend+worker no Coolify → restart →
`InProcess` retoma → re-executar runs falhos sob Python (idempotente) → registrar
no ledger.

## Soak de ≥2 semanas (pré-F3 — [[ADR-150]] §8)

**Relógio:** 14 dias-calendário consecutivos com o worker de prod em Go **e zero
rollbacks**. Rollback por gatilho zera para dia 0. Janela em Python por motivo
não-Go (manutenção/deploy) **pausa** (não zera).

**Barra de atividade (14 dias ociosos não provam nada):** **≥10 runs E0→E5
reais** (≥1 workspace), incluindo **≥3 runs Premium/LLM** (maior risco de
env-passthrough/OTel no subprocess). Ociosidade → estende a janela.

**Ledger append-only (o "documentado" do §8):** por run (`run_id`, workspace,
Free/Premium, executor=Go, status, duração vs SLO, timestamp); falhas + classe
(shell vs domínio); uptime :8002 (≥99%); **parity check semanal** (double-run:
`go-off` → re-run Python → golden_diff cents=0 + envelope=0); pico RSS + eventos
OOM/zumbi (zero); resultado do gate humano; ledger de rollback (contagem 0
exigida).

**F3 abre quando:** 14 dias + barra de atividade + parity checks todos zero +
zero rollback + zero OOM/zumbi + health ≥ SLO, **tudo no ledger**. F3 remove só
o `pipeline-service/` **Python HTTP** (a reversibilidade `unset→InProcess` vive
em `backend/`+`pipeline/` e **sobrevive à F3**) — ADR de remoção própria.

## Observabilidade mínima (sem Sentry)

**Floor bloqueante (antes do flip):** (1) logs JSON consultáveis por
`run_id`/`workspace_id`/`stage` dos três (Go slog + worker + backend, via
Coolify/`docker logs`); (2) status terminal + stage falha via WS/`pipeline_runs`;
(3) monitor `:8002 /health` com alerta red >90s; (4) schema-validation no
`write()` sempre ligada (sinal de paridade grátis); (5) detecção OOM/RSS; (6)
procedimento parity double-run pronto; (7) `go-off` testado em staging.

**Nice-to-have:** OTel collector em prod (**bloqueante só em staging** —
trace-continuity é gate técnico lá); Sentry (owner-gated); dashboards de duração.

## Follow-ups / fora de escopo

- **Fragilidade crítica (follow-up, `senior-cto`) — ENDEREÇADA por [[ADR-323]]
  (dark launch, default OFF até pós-F3).** `HttpPipelineClient.execute_stage`
  fazia `raise_for_status` sem auto-fallback → shell down = todo run hard-fail até
  `go-off` manual. O `FallbackPipelineClient` ([[ADR-323]]) degrada a `InProcess`
  em `ConnectError`/connect-timeout/5xx (circuit breaker sticky run-scoped via
  `ctx.shell_degraded`), com telemetria LOUD (`event=pipeline_shell_fallback`).
  Gated por `MATHOMS_PIPELINE_SHELL_FALLBACK` **default `0`**: fica desligado no
  soak (não mascara o rollback trigger #2 — o Go tem que provar 14 dias sozinho);
  o owner flippa `1` pós-F3. **Pré-condição do flip:** shell Go faz reap/kill do
  subprocess antes de responder 5xx (rollback trigger #6). **NÃO era requisito de
  F2** — código shipado como dark launch, ativação é decisão pós-soak.
- **Dual-queue / worker canário per-workspace** — escalação pré-registrada para
  quando tenants ativos > ~5 antes da F3. Não construir em F2.
- **F3 (decommission)** e port de domínio (Caminho 2/3) — fora deste track.
- **On-call:** formalizar contato (RUNBOOK §6 em aberto) antes do widen.

## Critério de aceite

- **Tier-1:** 3× Go vs 3× Python em `DETERMINISTIC_ORDER`, fixture com 0
  `requires_llm`; `go_parity_gate` = 0 divergências value/cents em E0→E5 após
  normalização; controle Py↔Py = 0 diff residual; telemetria assert 0 E2-LLM.
- **Tier-2:** envelope WS shape+sequência = 0; span attrs normalizados exatos +
  trace contínuo; subtrees LLM estruturais; `⊆ divergência(Py,Py)` nos valores.
- **Gate humano:** SMOKE_TEST_HUMAN PASS em `/reports/[id]` (run full staging).
- **CI:** job `go-parity-deterministic` (Postgres service) verde; run full é make
  target owner-run que alimenta o gate humano.
- **Prod:** staging bake → flip global backend+worker (restart) → watch 3 runs →
  widen; rollback = `go-off` com RTO ≤1min; ledger de soak iniciado.
- **Doc:** emenda 2026-07-08 na [[ADR-150]] §7 ✅; entrada em
  `docs/reference/RUNBOOK.md` apontando para este track (procedimento go-on/go-off
  prod + tabela de gatilhos + template de soak).
