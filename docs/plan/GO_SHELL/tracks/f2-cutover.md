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

> **Reancorado 2026-07-31** ([[ADR-150]] emenda datada): o owner decidiu
> continuar o cutover **no dogfood local**, sem mudar a arquitetura de banco. A
> pré-condição 1 abaixo caiu; a 2 estava imprecisa. Ambiente do gate = overlay
> nativo (`make go-on ENV=native`) contra o SQLite `mathoms.db` do dogfood.

1. ~~**Postgres em staging.**~~ **CAÍDA.** A incoerência WAL é **host↔container**
   (`runbooks/pipeline_service_container_smoke.md §3`); o overlay nativo roda o
   binário Go **no host** (§6 do mesmo runbook: "binário no HOST — sem a
   restrição de WAL do container") e os stages são subprocess do Python do host —
   um só namespace, WAL coerente. Além disso **não existe produção** (#1130), logo
   staging Postgres seria *menos* representativo do alvo que o dogfood local.
   Postgres é **re-gate diferido** para quando [[ADR-228]] G2/G3 abrir.
2. **Fixture curada com zero LLM — em 3 superfícies, medidas (não escolhidas).**
   `skip_llm`/`DETERMINISTIC_ORDER` **não** suprime LLM condicional *dentro* de
   stage não-`is_llm`. São três:
   | Superfície | Gatilho | Como zerar |
   |---|---|---|
   | `route_documents` | fallback de classificação [[ADR-081]] camada 2 (confidence < 0,8) | todo doc da fixture classifica por regex com confidence ≥ 0,8 |
   | `extract_invoices` / `extract_statements` | `requires_llm_fallback` — setado também por `itau`/`c6bank` em falha de parse/validação (`scripts/e2/validation.py`), **não** só por `wise`/`bankofamerica`/`quintoandar`: é propriedade do **documento**, não do banco | todo doc parseia limpo, 0 falha de validação |
   | `generate_narratives` | `MATHOMS_LLM_SECTION_SUMMARIES=1` ([[ADR-144]]) — o stage está em `DETERMINISTIC_ORDER` | env var pinada **idêntica** nos dois braços (divergência aqui é o bug de env-passthrough que o gate caça) |

   A curadoria é **empírica**: rodar E0→E2 sobre os candidatos e assert 0
   invocação nas três antes de promover a fixture. Escolher por banco não basta.

   **Medido 2026-07-31 no workspace de dogfood — não é preciso fixture sintética.**
   O corpus real já satisfaz a pré-condição, desde que o inbox seja esvaziado:

   | Superfície | Medição | Veredito |
   |---|---|---|
   | E2 (`requires_llm_fallback`) | Últimos **dois** runs full (`5a0eae54` 28/07, `9d47574c` 27/07): 125 artefatos de E2 (86 `extract_statements` + 39 `extract_invoices`), **0** em `extract_with_llm`. As escalações cessaram após 25/07 — os 5 docs que ainda escalavam nesse run aparecem como `extract_statements` nos seguintes (foram **corrigidos**, não perdidos: set de keys idêntico, 125=125) | ✅ limpo |
   | E0 (`route_documents`) | 14 dos 163 docs têm `classification_confidence < 0,8` (3 em 0,0; 11 em 0,7) → dispararIAM o fallback. **Mas o E2 lê de `data/`** (`extract_bank_documents.py:69` itera `DATA_DIR`), não do inbox: em re-run de workspace já roteado o E0 só processa o que estiver no **inbox**. Hoje há 4 arquivos lá — justamente os não-classificados que o stage deixa para revisão manual (`unidentified > 0` → warning) | ⚠️ exige **esvaziar/mover o inbox** antes do run |
   | `generate_narratives` | `MATHOMS_LLM_SECTION_SUMMARIES` off por default | ✅ pinar idêntico nos 2 braços |

   **Receita do Tier-1 (sem custo de LLM, sobre o corpus real):** mover os 4
   arquivos do inbox para fora → rodar `DETERMINISTIC_ORDER` → E0 não tem o que
   classificar (0 LLM), E2 re-parseia os 125 de `data/` deterministicamente, os
   stages `is_llm` já saem por `skip_llm`. Assert de telemetria: 0 artefato em
   `extract_with_llm` e 0 chamada de classificação.

   **Dívida independente descoberta aqui (não bloqueia F2):**
   `pipeline/stages/route_documents.py:25` passa `use_llm=True` **hardcoded**, e o
   `skip_llm` do orquestrador atua **filtrando a lista de stages** por `is_llm` —
   nunca chega ao wrapper. Logo um run que pede "sem LLM" ainda gastaria LLM no E0
   se o inbox tivesse doc de baixa confiança. O gate contorna pelo inbox vazio.
3. **`ANTHROPIC_API_KEY`** disponível no env do serviço Go para o Tier-2 (run
   full com narrativas). Owner-gated (custo LLM — orçar; ordem de grandeza
   abaixo dos evals de parecer, mas medir).
4. **Risco novo assumido — dois escritores SQLite.** Sob `InProcess` o worker
   escreve artefatos in-process; sob o shell Go o **subprocess** escreve artefatos
   enquanto o worker escreve `pipeline_runs`/eventos. SQLite WAL admite um
   escritor por vez → `OperationalError: database is locked` é **falha
   shell-caused** (gatilho 8 abaixo). Não bloqueia o gate: é exatamente o que o
   soak no dogfood tem que falsificar.

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

## Fase C — flip no dogfood local (`sre-devops`)

> **Reancorado 2026-07-31:** não há staging nem prod hospedado (#1130). O "bake"
> e o "flip" acontecem **na mesma máquina** — o que muda entre eles não é
> ambiente, é **o que roda em cima**: fixture curada (bake) vs. o workspace real
> do owner (flip). O gate humano continua separando os dois.

**Rollout decidido:** bake com fixture → flip do overlay nativo sobre o
workspace real → watch → soak. Per-tenant (dual-queue) fica pré-registrado, não
construído (o dogfood é single-tenant; blast radius de canário per-workspace
é ≈zero).

1. **Bake (fixture curada):** `make go-on ENV=native`, roda Fase A completa
   (Tier-1 3×3 + Tier-2) sobre a fixture 0-LLM. Trace-continuity é **bloqueante
   aqui** — é o único lugar antes do dado real. Múltiplas fixtures cobrem o "por
   workspace" da [[ADR-150]] §7.
2. **Flip (workspace real):** `make go-on ENV=native` com o worker dev
   re-apontado (o target já seta `MATHOMS_PIPELINE_SERVICE_URL` e reinicia o
   worker — o flip **não é a quente**: `get_pipeline_client()` memoiza o
   singleton por processo). Rodar pela UI (`localhost:3000`) no workspace real.
   Watch **intensivo nos 3 primeiros runs** (espelha o gate técnico). Limpo → o
   relógio do soak começa.
3. **Honestidade do runbook:** "reverte em segundos" da ADR = **restart**, não
   hot-reload. RTO = `make go-off ENV=native` (segundos). Runs em voo: drain
   SIGTERM (grace 30s) + re-run idempotente (escrita só commita no sucesso).

## Rollback (gatilhos acionáveis — reverter = `go-off`)

Fallback = **unset da env var → `InProcessPipelineClient`** (caminho batido em
prod), **não** o Python HTTP. Todo rollback **zera o relógio do soak** e entra
no ledger com causa + evidência.

| # | Gatilho | Onde medir | Limiar | Ação |
|---|---|---|---|---|
| 1 | Divergência de paridade (cents≠0, envelope WS≠0, ou schema-validation falha no `write()` que não ocorria sob Python) | golden_diff em double-run agendado + logs | **1 ocorrência** | Rollback imediato |
| 2 | Nova classe de falha de stage shell-caused (503 `executor_unavailable`, subprocess morto, stdout não-parseável, env faltando) — verde sob Python, falha sob Go, mesmo input | WS `stage_failed`/`run_failed` + logs | **1 ocorrência** | Rollback imediato (falha de domínio idêntica nos dois **não** é gatilho) |
| 3 | Runs quebrados shell-caused acumulando | WS + `pipeline_runs` | **≥2 na janela** OU ≥1 que quebrou relatório de usuário real | Rollback + incidente (status page <15min se user-facing) |
| 4 | `:8002 /health` não-200 (shell down = todo run hard-fail, sem auto-degrade) | `curl` local no início de cada run + `_dev_pids/go.log` (monitor externo é **N/A** no dogfood) | **1 run iniciado com shell não-saudável** | Rollback |
| 5 | Pressão de memória (~115MB RSS/subprocess × concorrência 2) | `ps`/Activity Monitor no host; sem cgroup, **não há OOMKill** — o sintoma é swap/pressão | RSS do shell+subprocess > 1GB sustentado, ou pressão vermelha | Rollback + reduzir `--concurrency` |
| 6 | Subprocess zumbi/defunct (lifecycle hardening deveria impedir) | host `ps aux \| grep defunct` | >60s → investigar; recorrência → rollback | Rollback na recorrência |
| 7 | Latência de run estoura SLO por causa do shell | `pipeline_runs` / timestamps WS | Free >5min / Premium >15min p95, sustentado | Rollback (boot ~550ms/stage é esperado, não é gatilho) |
| 8 | **`OperationalError: database is locked`** — contenção SQLite entre o subprocess (artefatos) e o worker (`pipeline_runs`/eventos); classe de falha que `InProcess` não tem | logs do worker + `go.log` | **1 ocorrência** | Rollback imediato; reabrir com `senior-cto` + `sre-devops` (pode exigir o re-gate Postgres antes do prazo) |

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
(shell vs domínio); **shell saudável em 100% dos runs** (o "uptime :8002 ≥99%" de
calendário é **N/A** no dogfood — o shell sobe por sessão de trabalho, não 24×7);
**parity check semanal** (double-run: `go-off` → re-run Python → golden_diff
cents=0 + envelope=0); pico RSS + zumbis (zero); **zero `database is locked`**
(gatilho 8); resultado do gate humano; ledger de rollback (contagem 0 exigida).

**F3 abre quando:** 14 dias + barra de atividade + parity checks todos zero +
zero rollback + zero OOM/zumbi + health ≥ SLO, **tudo no ledger**. F3 remove só
o `pipeline-service/` **Python HTTP** (a reversibilidade `unset→InProcess` vive
em `backend/`+`pipeline/` e **sobrevive à F3**) — ADR de remoção própria.

## Observabilidade mínima (sem Sentry)

**Floor bloqueante (antes do flip):** (1) logs JSON consultáveis por
`run_id`/`workspace_id`/`stage` dos três (Go slog + worker + backend — no dogfood
são `_dev_pids/go.log` + `worker.log`, não Coolify); (2) status terminal + stage
falha via WS/`pipeline_runs`; (3) `curl :8002/health` verificado no início de cada
run (alerta automatizado é **N/A** — sem monitor externo local); (4)
schema-validation no `write()` sempre ligada (sinal de paridade grátis); (5)
observação de RSS/pressão (sem cgroup não há OOMKill — ver gatilho 5); (6)
procedimento parity double-run pronto; (7) `go-off ENV=native` testado no bake.

**Nice-to-have:** OTel collector local (**bloqueante no bake** — trace-continuity
é gate técnico lá); Sentry (owner-gated); dashboards de duração.

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

- **Tier-1:** 3× Go vs 3× Python em `DETERMINISTIC_ORDER`, fixture com 0 LLM nas
  **3 superfícies** (pré-condição 2); `go_parity_gate` = 0 divergências
  value/cents em E0→E5 após normalização; controle Py↔Py = 0 diff residual;
  telemetria assert 0 invocação LLM (E0-route, E2, narrativas).
- **Tier-2:** envelope WS shape+sequência = 0; span attrs normalizados exatos +
  trace contínuo; subtrees LLM estruturais; `⊆ divergência(Py,Py)` nos valores.
- **Gate humano:** SMOKE_TEST_HUMAN PASS em `/reports/[id]` (run full do bake).
- **CI:** job `go-parity-deterministic` verde **se** houver fixture commitável
  PII-zero que semeie E0→E2; sem ela, o Tier-1 é make target owner-run local e o
  CI cobre só E3→E5 semeando artefatos (decisão de escopo pendente — registrar no
  PR que criar o job). Run full é owner-run e alimenta o gate humano.
- **Dogfood:** bake com fixture → flip no workspace real (`go-on ENV=native`,
  restart do worker) → watch 3 runs → soak; rollback = `go-off ENV=native` com RTO
  em segundos; ledger de soak iniciado.
- **Doc:** emenda 2026-07-08 na [[ADR-150]] §7 ✅; emenda 2026-07-31 (gate no
  dogfood) ✅; entrada [RUNBOOK §11](../../../reference/RUNBOOK.md) apontando para
  este track ✅ (go-on/go-off, `make go-parity`, leitura dos exit codes, sinais de
  soak). Falta só o **template do ledger de soak**.

## Estado da execução (2026-07-31)

| Fatia | Estado |
|---|---|
| A1 — comparador `dev/go_parity_gate.py` | ✅ #900 |
| A2 — captura de eventos WS | ✅ #919 |
| A3 — orquestrador + `make go-parity` | ✅ #1136 |
| Pré-condição 2 (0-LLM) | ✅ medida — corpus real passa, sem fixture sintética |
| A4 — Tier-2 (WS via `psubscribe` pré-dispatch) | ✅ orquestração pronta; **execução é owner-run** (custo LLM) |
| Job CI `go-parity-deterministic` | ⏸ decisão de escopo (sem fixture commitável PII-zero) |
| Fase B — gate humano | ⏸ owner |
| Fase C — flip + soak | ⏸ owner |
