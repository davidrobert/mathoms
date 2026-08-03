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
   | E2 (`requires_llm_fallback`) | Últimos **dois** runs full (`5a0eae54` 28/07, `9d47574c` 27/07): 125 artefatos de E2 (86 `extract_statements` + 39 `extract_invoices`), **0** em `extract_with_llm`. As escalações cessaram após 25/07 — os 5 docs que ainda escalavam nesse run aparecem como `extract_statements` nos seguintes (foram **corrigidos**, não perdidos: set de keys idêntico, 125=125) | ⚠️ **medição cega** — ver reescrita abaixo |
   | E0 (`route_documents`) | 14 dos 163 docs têm `classification_confidence < 0,8` (3 em 0,0; 11 em 0,7) → dispararIAM o fallback. **Mas o E2 lê de `data/`** (`extract_bank_documents.py:69` itera `DATA_DIR`), não do inbox: em re-run de workspace já roteado o E0 só processa o que estiver no **inbox**. Hoje há 4 arquivos lá — justamente os não-classificados que o stage deixa para revisão manual (`unidentified > 0` → warning) | ⚠️ exige **esvaziar/mover o inbox** antes do run |
   | `generate_narratives` | `MATHOMS_LLM_SECTION_SUMMARIES` off por default | ✅ pinar idêntico nos 2 braços |

   **Receita do Tier-1 (sem custo de LLM, sobre o corpus real):** mover os 4
   arquivos do inbox para fora → `dev/go_parity_run.py --tier tier1`, que liga
   cada braço com **`LLM_FREE=1`** → `DETERMINISTIC_ORDER` roda, os stages
   `is_llm` saem por `skip_llm`, e as superfícies condicionais não têm credencial
   para usar.

   > **Reescrito 2026-08-03 pela [[A40.l24]].** Duas versões anteriores desta
   > asserção não podiam ficar vermelhas, cada uma por um motivo diferente.
   >
   > **O que estava errado.** "0 artefato em `extract_with_llm`" é cego: a
   > extração por visão do parser da Caixa grava artefato **normal** de
   > `extract_statements`, e o stub de escalação também vai para o stage
   > determinístico ([[ADR-342]]) — nenhum dos dois vira stage `%llm%`. A correção
   > seguinte (#1151) trocou a cegueira por uma **inversão**: gatear em
   > `requires_llm_fallback` reprova o braço **sem** credencial (zero chamada, o
   > flag é setado só quando a visão **falha**) e aprova o braço que fez chamada
   > paga (sucesso não deixa rastro no flag).
   >
   > **Por que o veredito ficava invertido entre os braços.** `_go-on-native`
   > injeta `ANTHROPIC_API_KEY` lida do `.env` no shell Go, e
   > `executor.go` a repassa a cada subprocess por `os.Environ()`; `dev-worker-up`
   > só herda o env do shell. Medido: o mesmo `artifact_key` do extrato da Caixa
   > saiu com **2986 bytes** nos runs com credencial e **1002** nos sem, e o E3
   > deixou de reconciliar a conta (105 vs 106 artefatos de
   > `reconcile_transactions`) — divergência que o gate leria como bug de executor.
   >
   > **O que vale agora.** O Tier-1 garante 0-LLM **impedindo** a chamada, não
   > detectando-a depois: `LLM_FREE=1` apaga a credencial do worker Celery **e**
   > do shell Go, e o harness exige o marcador `LLM-FREE: ANTHROPIC_API_KEY
   > scrubbed` na saída do `make` (scrub que não rodou falha alto). Asserções
   > secundárias, ambas sobre o DB: 0 row em `llm_call_log` para o run e 0
   > artefato de stage `%llm%`.
   >
   > **Limite declarado.** Detecção pós-hoc continua **estruturalmente incompleta**
   > enquanto `scripts/e2/banks/caixa.py` e `scripts/route_documents.py` montarem
   > o SDK `anthropic` direto de `os.environ`: essas chamadas nunca aparecem em
   > `llm_call_log` ([[ADR-355]] §Escopo). Fechar a rota é [[A41.l2]] / [[A41.l3]],
   > e o gate de ausência de rota (`rg 'import anthropic'` = 0 fora de
   > `pipeline/llm/`) é [[A41.l4]]. Até lá a garantia vem da credencial ausente.
   >
   > **Corpus menor, e isso é esperado.** 18–19 artefatos de E2 por run carregam
   > `requires_llm_fallback=True` sem serviço (quem os consome é `is_llm`), então o
   > corpus do Tier-1 é menor que o do run full — **simetricamente** nos dois
   > braços, o que preserva a validade da paridade. O harness passou a **reportar**
   > esses docs como corpus encolhido ([[ADR-355]] §Consequências) em vez de
   > reprovar o run com eles. Divergência de *quais* docs escalaram entre braços
   > continua sendo pega pelo diff de artefato do `go_parity_gate`.

   **Dívida independente descoberta aqui (não bloqueia F2):**
   `pipeline/stages/route_documents.py:25` passa `use_llm=True` **hardcoded**, e o
   `skip_llm` do orquestrador atua **filtrando a lista de stages** por `is_llm` —
   nunca chega ao wrapper. Logo um run que pede "sem LLM" ainda gastaria LLM no E0
   se o inbox tivesse doc de baixa confiança. O gate contorna pelo inbox vazio.
3. **`ANTHROPIC_API_KEY`** disponível no env dos **dois braços** para o Tier-2 (run
   full com narrativas). Owner-gated (custo LLM — orçar; ordem de grandeza
   abaixo dos evals de parecer, mas medir).

   > **Corrigido 2026-08-03.** Esta pré-condição dizia "no env do serviço Go" — e
   > pedir a credencial só de um lado **garante** a assimetria que a [[A40.l24]]
   > fechou no Tier-1. `_go-on-native` lê a chave do `.env` e a injeta no shell Go
   > (repassada a cada subprocess por `os.Environ()`); `dev-worker-up` só herda o env
   > do shell. `.env` com chave + shell sem chave = braço Go chamando LLM que o Python
   > não chama, e o diff aparece como bug de executor — a divergência de §B.1 de novo,
   > agora fora do escopo do `skip_llm`.
   >
   > **Como é enforçado:** `assert_credential_symmetry` em `assert_preconditions`
   > (`dev/go_parity_llm_free.py`) aborta o Tier-2 antes de gastar run se a chave
   > estiver no `.env` e não no shell, ou ausente nos dois. **Exportar no shell** é a
   > forma correta: `export ANTHROPIC_API_KEY=…` antes do `make go-parity`.
   >
   > **Por que não injetar a chave no worker** (que "resolveria" por cima): ligaria a
   > chamada de visão sem gate do `caixa.py` em **todo** run de dev, inclusive
   > determinístico ([[ADR-355]] 3ª superfície, [[A41.l3]]) — trocaria "os braços
   > divergem" por "os dois gastam LLM". O guard informa; a decisão fica com o dono.
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
| 8 | **`OperationalError: database is locked`** — contenção SQLite entre o subprocess (artefatos) e o worker (`pipeline_runs`/eventos) | logs do worker + `go.log` + **`api.log`** (a daemon thread do fallback roda no processo da API) | **1 ocorrência** | Rollback imediato; reabrir com `senior-cto` + `sre-devops` |

> **Correção 2026-08-03:** o gatilho 8 dizia "classe de falha que `InProcess` não tem".
> **Falso** — o worker nativo já roda `--concurrency=2` prefork e a API uvicorn escreve no
> mesmo SQLite, então múltiplos escritores já existem hoje. O flip **acrescenta um
> escritor**, não inaugura a classe. E o `busy_timeout=30s` herdado do `SyncSessionLocal`
> **não** é mitigação suficiente: [[ADR-256]] registra incidente de 2026-05-22 com
> `database is locked` **após** os 30s. O risco está amortecido, não resolvido — e segue
> aceito nominalmente pela emenda [[ADR-150]] 2026-07-31 item 5, logo **não é** motivo de
> adiamento por si.

**Procedimento:** `make go-off ENV=native` (mata o shell e reinicia o worker sem a env
var) → `InProcess` retoma → re-executar runs falhos (idempotente) → registrar no ledger.
Coolify **não existe** (#1130) — a menção anterior era herdada do desenho pré-emenda.

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
  0-LLM garantido por **credencial ausente** nos dois braços (`LLM_FREE=1`,
  marcador verificado) + 0 row em `llm_call_log` + 0 artefato de stage `%llm%`
  — ver pré-condição 2 para por que a asserção não é por telemetria de artefato.
- **Tier-2:** envelope WS shape+sequência = 0; span attrs normalizados exatos +
  trace contínuo; subtrees LLM estruturais; `⊆ divergência(Py,Py)` nos valores.
- **Gate humano:** SMOKE_TEST_HUMAN PASS em `/reports/[id]` (run full do bake).
- **CI:** job `go-parity-deterministic` **DEFERIDO** (decisão 2026-07-31, ver
  §Decisão abaixo). O Tier-1 é make target owner-run local; o Tier-2 é owner-run
  e alimenta o gate humano.
- **Dogfood:** bake com fixture → flip no workspace real (`go-on ENV=native`,
  restart do worker) → watch 3 runs → soak; rollback = `go-off ENV=native` com RTO
  em segundos; ledger de soak iniciado.
- **Doc:** emenda 2026-07-08 na [[ADR-150]] §7 ✅; emenda 2026-07-31 (gate no
  dogfood) ✅; entrada [RUNBOOK §11](../../../reference/RUNBOOK.md) apontando para
  este track ✅ (go-on/go-off, `make go-parity`, leitura dos exit codes, sinais de
  soak). Falta só o **template do ledger de soak**.

## Decisão 2026-07-31 — o job de CI `go-parity-deterministic` fica DEFERIDO

O A3 registrou o job como "candidato". Não construir agora, por três razões que
se somam:

1. **Orçamento de Actions.** O gasto de CI está em ~544% e a alavanca medida é o
   **número de jobs** (GitHub cobra 1min mínimo por job). Um job de paridade
   precisa de Redis + DB + worker Celery + binário Go de pé — é dos mais caros
   que existiriam no repo. Somar isso durante um estouro de orçamento é o oposto
   do que a causa-raiz recomenda.
2. **O nightly está desligado** (waiver ADR-210 c4). Um gate "nightly ou
   on-Go-change" cairia justamente na janela que não roda — gate verde sem
   verificar nada é pior que gate ausente.
3. **Falta fixture commitável.** Seedar E0→E2 exigiria documentos-fonte
   PII-zero, que não existem; a fixture sintética de `tests/fixtures/pipeline_golden/`
   é de **saída** de E2, então o job cobriria só E3→E5 — perdendo exatamente o E0/E2,
   onde vivem as superfícies de LLM condicional.

**Cobertura no lugar dele:** `go-test -race` + codegen sync + schemathesis contra
o Go já rodam no `All checks green` e cobrem o contrato HTTP. O que o parity gate
adiciona (corrupção de args/env no subprocess) é regressão que só aparece quando
alguém edita `services/pipeline-service-go/internal/stages/` — evento raro.

**Reabrir quando:** orçamento de Actions saudável **E** nightly religado. Aí o
job entra no nightly (não per-PR), com Tier-1 sobre fixture sintética de E3→E5 e
`log()` explícito do que ficou fora de cobertura.

## 1ª execução real do Tier-1 (2026-08-03) — veredito: **exit 2**, e achou divergência real

`make go-parity WS=<dogfood> RUNS=2` rodou ponta a ponta (4 runs). Veredito **exit 2 =
controle Py↔Py sujo**, portanto nenhuma conclusão Go↔Py é válida ainda. O guard funcionou
como projetado. Três achados.

> **Correção 2026-08-03 (pós-§B.1).** A frase original dizia "0 escalação LLM nos quatro —
> a pré-condição 2 se confirmou no campo". **Falso como escrito.** O que a asserção do
> harness mede é "0 artefato em stage `%llm%`" — e isso passou. Mas cada run carrega
> **18–19 artefatos de E2 com `requires_llm_fallback=True`** (escalações não-servidas,
> porque `extract_with_llm` é `is_llm` e sai do `DETERMINISTIC_ORDER`), e **cada braço Go
> fez 1 chamada LLM real** que a asserção não vê. A pré-condição 2 **não** está confirmada
> no campo; sua operacionalização é que está errada ([[A40.l24]]).

### A. Controle sujo — duas causas distintas

| Causa | Natureza | Estado |
|---|---|---|
| `categorize_transactions/{despesas,receitas}` → `consolidation_date` diverge entre runs | **Normalização incompleta.** É instante de processamento, não dado de domínio | ✅ corrigido — entrou em `_TIMESTAMP_KEYS` por **nome explícito** (não por sufixo `_date`, que mascararia `data_vencimento`/`data_adesao`) |
| `analyze_finances/analise_financeira` → `if_monte_carlo.caminho_p10[*]` diverge entre runs | **Não-determinismo de domínio**, não de normalização | ⛔ **bloqueia o byte-exact**. `if_projector.py:306` tem `seed: int \| None = None` e a 360 faz `np.random.default_rng(config.seed)`; **nenhum call-site seta seed** → 10.000 simulações com entropia do SO a cada run. Medido: `caminho_p10[22]` = R$ 11.037.269,90 vs R$ 10.961.276,98 (**0,7%**) com input idêntico |

O segundo item **não é problema do Go** — é do produto: o cone P10/P50/P90 da projeção de
IF não é reproduzível entre runs. Ver §Débito abaixo.

### B. Divergência real de executor (o gate se justificou)

O braço Go produziu **243** artefatos contra **242** do Python. O extra é
`('reconcile_transactions', 'caixa_extratoconta_BRL_202606_202606')`.

Hipótese de **efeito de ordem** (o run Go era o 3º, e o E3 lê artefato pelo mais recente
entre runs) foi **refutada por experimento**: um 5º run Python, na posição ordinal 5,
voltou a dar 242 sem o artefato.

| Ordinal | Executor | Artefatos | E3 `caixa` |
|---|---|---|---|
| 1, 2, **5** | Python InProcess | 242 | **0** |
| 3, 4 | shell Go | 243 | **1** |

**2/2 no Go, 0/3 no Python** — a diferença acompanha o executor e é reproduzível. Os runs
**full** históricos (Python, `skip_llm=False`) **têm** o artefato.

#### B.1 — Explicada (2026-08-03): a divergência nasce no E2, não no E3

A premissa de que "o E2 de entrada é idêntico nos quatro runs" era **falsa** — só a
*chave* era idêntica. O **conteúdo** difere:

| Braço | `requires_llm_fallback` | `n_tx` | `periodo` | `notas` |
|---|---|---|---|---|
| Python (runs 1, 2, 5) | `True` (`escalation.code=extract.empty_result`) | 0 | `2026-05-01…06-30` (do filename) | erro de parsing |
| Go (runs 3, 4) · full histórico | ausente | 8 | `2026-06-01…06-30` (do modelo) | `Transações extraídas via LLM (PDF somente-imagem)` |

O PDF da Caixa tem camada de texto (11 127 chars) mas **nenhuma transação parseável**:
tabelas vazias, fallback de texto vazio. Aí
[`caixa.py::_extract_via_llm`](../../../../scripts/e2/banks/caixa.py) entra — extração por
**visão**, mandando o PDF inteiro em base64. No braço Go ela roda e devolve 8 transações;
no braço Python ela desiste e o artefato virou stub, que o E3 exclui como `llm_stub`
([[ADR-342]], `e3_reconciler_adapter.py:236`). Daí `llm_fallback: 19` (Py) vs `18` (Go) no
`output_summary` do E2, e E3 = 105 vs 106.

**A única variável é `os.environ["ANTHROPIC_API_KEY"]`.** `_extract_via_llm` decide por
dois testes e nada mais: `import anthropic` e `os.environ.get("ANTHROPIC_API_KEY")`
(l. 220–226). Não recebe `ctx`, logo **não** consulta `ctx.llm_calls_allowed`.

Cadeia causal medida, ponta a ponta:

1. `_go-on-native` (Makefile l. 1201) **injeta `ANTHROPIC_API_KEY` explicitamente** no env
   do servidor Go — de propósito, com comentário ("só vai explícito o que é lido de
   `os.environ`").
2. `executor.go:125` faz `cmd.Env = append(os.Environ(), …)` → **todo subprocess de stage
   herda a chave**.
3. `dev-worker-up` (l. 711) sobe o worker Celery **sem env algum** — herda o shell que
   rodou `make dev`. Neste worker a chave não está presente (medido via `ps eww <pid>`).
   Os runs full de 25–28/07 tiveram a chave exportada no shell; é isso, e só isso, que
   explica eles terem o artefato.
4. Prova direta, 2 braços chamando `parse_caixa` sobre o PDF real do dogfood (custo zero;
   o 2º braço usa chave **inválida** de propósito e para no 401):
   - `env -u ANTHROPIC_API_KEY` → `n_tx=0, requires_llm_fallback=True`, log
     `ANTHROPIC_API_KEY não definida — LLM fallback desabilitado`. Reproduz o braço
     Python exatamente.
   - `ANTHROPIC_API_KEY=<inválida>` → log `PDF sem camada de texto — usando extração via
     LLM (visão)` seguido de `401 authentication_error`.

   Ou seja: **a decisão de chamar depende do env, jamais da política do run** — a função
   não recebe `ctx`. O gate de regressão desse comportamento é
   `tests/test_go_parity_llm_free_gate.py::test_visao_da_caixa_chama_o_sdk_e_nao_deixa_rastro_no_flag`
   (spy nomeado sobre o SDK, sem API), entregue pela [[A40.l24]] — é a forma versionada
   da mesma prova.

Hipóteses anteriores **refutadas**: não é efeito de ordem (5º run Python voltou a 242);
não é estado acumulado no `ctx` reusado do InProcess (a divergência nasce no E2, e ambos os
braços rodam o *mesmo* código com o *mesmo* input); não é o Go escrevendo a mais (o
artefato dele é uma extração legítima, idêntica em shape à do run full).

#### B.2 — Veredito: nenhum dos dois braços está certo, e não é bug de reconcile

- **O braço Go está errado no contrato.** Fez chamada LLM num run que declarou
  `skip_llm=True`. O *dado* dele é melhor (bate com o run full), mas chegou lá violando a
  política do run — e gastou LLM num Tier-1 que devia custar zero.
- **O braço Python está certo por acidente.** Não chamou porque a chave falta no env do
  worker, **não** porque honrou `skip_llm`. Exporte a chave e ele reproduz o Go (§B.1
  item 4). `skip_llm` não é enforçado nessa superfície em **nenhum** dos dois executores.

Logo o fix não é "fazer um imitar o outro": é fazer a decisão depender da **política do
run** em vez do **env do processo** — exatamente [[ADR-355]] (`Decidido`), 3ª superfície da
tabela, deferida para [[A41.l3]] com o enquadramento já escolhido ("o fix pode ser deletar
o call-site em vez de propagar o contexto": `extract_with_llm` já é o caminho gated e a
Caixa é o único banco que o atalha). A [[ADR-355]] §Consequências **previu este achado
textualmente** — "`_llm_artifact_count` … não vê uma extração de visão bem-sucedida do
parser Caixa". O gate falhou como ela avisou que falharia.

#### B.3 — O que isto muda para o flip

1. **Não é bloqueio de shell.** É defeito de produto pré-existente, com ADR `Decidido` e
   lane. §B sai da lista de bloqueios como "explicar" e entra como "declarar".
2. **Mas o cutover tem efeito colateral próprio, e ele é novo:** pós-flip o shell Go
   entrega a chave a **todo** subprocess de stage por construção, então o flip
   **silenciosamente religa** a chamada de visão sem gate em runs onde hoje ela está morta
   — inclusive determinísticos. Ou [[A41.l3]] fecha antes, ou isso vai declarado no gate
   humano. Não pode ir implícito.
3. ✅ **Tier-2 não era comparável enquanto os envs divergissem — fechado.** No run full a
   mesma assimetria reaparecia (Py sem chave → stub; Go com chave → extração), fora do
   escopo do `skip_llm`. `assert_credential_symmetry` (pré-condição 3) aborta o Tier-2
   antes de gastar run. Igualar **não** substitui [[A41.l3]]: sem o gate de política,
   igualar por cima só trocaria "divergem" por "os dois gastam LLM".
4. ✅ **O gate media a camada errada — fechado pela [[A40.l24]]** (#1151 → #1157). Duas
   iterações: #1151 trocou a cegueira (`stage LIKE '%llm%'`) por uma **inversão** (gatear
   em `requires_llm_fallback` reprova o braço sem credencial e aprova o que pagou, porque
   o flag só é setado quando a visão **falha**); #1157 fechou **impedindo** a chamada —
   `LLM_FREE=1` apaga a credencial dos dois braços, com marcador verificado e prova de
   mutação. Ver pré-condição 2 §Reescrito.

   > Meu item 4 original propunha medir "no boundary do SDK". A [[A40.l24]] mostrou que
   > **não é alcançável** no harness: o run executa no worker Celery / subprocess Go, fora
   > do alcance do spy, e instrumentar sempre-ligado violaria [[ADR-111]]. Impedir > medir.
5. ✅ **"O corpus de dogfood deixa de servir ao Tier-1" — resolvido, não confirmado.** Era
   consequência da inversão de #1151, não do corpus: com a asserção daquele PR os 18–19
   docs com `requires_llm_fallback` abortariam todo run. O #1157 os **reclassificou** como
   corpus encolhido ([[ADR-355]] §Consequências) — reportados, sem reprovar, porque sob
   `DETERMINISTIC_ORDER` o stub é o comportamento esperado (`extract_with_llm` é `is_llm`).
   A conclusão "não é preciso fixture sintética" da pré-condição 2 **volta a valer**, agora
   com a garantia de 0-LLM vindo da credencial ausente em vez de contagem de artefato.

### C. Defeito metodológico do harness — corrigido

Braços sequenciais (`py,py,go,go`) tornam "ser Go" e "ser o 3º run" perfeitamente
correlacionados; o 3×3 do §7 tem o mesmo vício. Agora `execute_interleaved` intercala e
**alterna quem vai primeiro em cada par**, então posição ordinal deixa de ser variável
confundida. Sem isso, todo achado exigiria o experimento manual acima.

## Estado da execução (2026-07-31, atualizado 2026-08-03)

| Fatia | Estado |
|---|---|
| A1 — comparador `dev/go_parity_gate.py` | ✅ #900 |
| A2 — captura de eventos WS | ✅ #919 |
| A3 — orquestrador + `make go-parity` | ✅ #1136 |
| Pré-condição 2 (0-LLM) | ⚠️ **conclusão caiu** — o Tier-1 de 03/08 gastou 1 chamada LLM por braço Go, invisível à asserção antiga (§B.1). #1151 endureceu a asserção; com ela o corpus real **não passa** (18–19 escalações), logo "não é preciso fixture sintética" precisa ser re-decidido (§B.3 item 5) |
| A4 — Tier-2 (WS via `psubscribe` pré-dispatch) | ✅ #1137 — orquestração pronta; **execução é owner-run** (custo LLM) |
| Doc — RUNBOOK §11 + template do ledger de soak | ✅ #1137 |
| Job CI `go-parity-deterministic` | ⛔ **deferido** (§Decisão 2026-07-31) |
| Fase B — gate humano | ⏸ owner |
| Fase C — flip + soak | ⏸ owner |

**Bloqueios do flip após a 1ª execução real (2026-08-03):**

1. ✅ **Seed do Monte Carlo de IF — fechado** ([[ADR-360]], 2026-08-03). Era débito de
   produto (reprodutibilidade do relatório), não do Go; o gate só o expôs. O seed passou a
   ser constante de modelo versionada (`_MC_SEED`) com guard de fail-fast contra
   `seed=None`, `n_simulacoes` 10k→50k, e proveniência (`mc_version`/`seed_usado`/
   `n_simulacoes_usado`) no artefato. Seed derivado do input foi **rejeitado** por quebrar
   monotonicidade em patrimônio/aporte e atribuibilidade de golden diff — ver
   [[ADR-360]] §Alternativas. Falta **re-rodar o Tier-1** para confirmar 0 diff residual no
   controle Py↔Py sem allowlist para o cone.
2. ✅ **Divergência `caixa` — explicada** (§B.1/B.2, 2026-08-03). Não é bug de executor: é
   [[ADR-355]] 3ª superfície ([[A41.l3]]) exposta por assimetria de env entre os dois
   braços. Dos quatro itens que ela gerou em §B.3, três fecharam no mesmo dia (asserção
   do Tier-1 pela [[A40.l24]]; corpus reclassificado; simetria de credencial do Tier-2 na
   pré-condição 3). **Sobra um, e é do gate humano** — item 3 abaixo.
3. ⛔ **Declarar no gate humano que o flip religa uma chamada LLM sem gate.** Único item de
   §B.3 ainda aberto, e não é fechável por harness: pós-flip o shell Go entrega
   `ANTHROPIC_API_KEY` a **todo** subprocess de stage por construção
   (`executor.go` → `os.Environ()`), então a extração de visão do `caixa.py` — que hoje
   está morta no worker por ausência de credencial — passa a rodar, **inclusive em runs
   determinísticos**, sem budget ([[ADR-173]]), sem `LLMCallLog`, sem sanitização
   ([[ADR-175]]) e mandando PDF financeiro inteiro em base64. Duas saídas, escolha do dono:
   fechar [[A41.l3]] antes do flip, ou aceitar explicitamente no gate humano com o custo
   declarado. **Não pode ir implícito** — é mudança de comportamento causada pelo cutover,
   não pré-existente a ele.
4. Depois disso: re-rodar Tier-1 (agora intercalado, com seed fixo e `LLM_FREE=1`) →
   Tier-2 (custa LLM; exige a chave exportada no shell) → gate humano → flip → soak com o
   ledger do RUNBOOK §11.3.
