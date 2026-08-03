---
id: ADR-111
type: adr
title: "Stateless-rigoroso: padrão e gate empírico (A6f.6)"
status: Decidido
phase: "A6f.6"
date: "2026-04-20"
relates_to: ["[[ADR-359]]"]
supersedes: []
superseded_by: []
amended_at: ["2026-08-03"]
aliases: ["ADR 111"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 136
---

# ADR-111 — Stateless-rigoroso: padrão e gate empírico (A6f.6)

**Status:** Decidido (A6f.6) • **Data:** 2026-04-20

> **Correção factual (2026-08-03, [[ADR-359]]):** a bullet "Background tasks: 0
> ocorrências de `asyncio.create_task`, `BackgroundTasks` ou `threading.Thread`
> em app code" abaixo era **falsa na data em que foi escrita** —
> `pipeline_service._start_fallback_thread` existia desde 2026-04-14. A decisão e
> a regra R19 permanecem íntegras; o que falhou foi o método de verificação. Ver
> §Correção do método de verificação no fim desta nota.

**Contexto:** Para que a stack escale horizontalmente (ADR-102 R19 — "Stateless-ready")
precisa existir uma garantia — auditada e testada — de que nada no código da
aplicação *requer* que um request pertença ao mesmo worker do anterior. Um
único `@lru_cache` mal colocado, um `dict` global que acumula estado ou um
`set[WebSocket]` em memória quebram a premissa e escondem o bug até o
segundo uvicorn worker entrar em produção.

A6f.6 foi planejada como refactor preventivo (mover WS para Redis pub/sub,
migrar rate limit para DB, etc.). Durante o audit `docs/reference/STATELESS_AUDIT.md`,
concluímos que **o backend já está multi-worker-safe**:

- `@lru_cache`/`cached_property` em `backend/app/`: 0 ocorrências.
- Globais de módulo: 17 cataloged, todos imutáveis (constantes de regex,
  mappings, thresholds) ou singletons lazy idempotentes (`engine`, `_redis_client`,
  `_singleton` do Vault) — cada worker inicializa o seu, sem interop necessário.
- WS sessions: `api/ws.py` já era Redis pub/sub desde P5 (F6.5B.14) — nenhum
  `set[WebSocket]` ou `dict[run_id, list]` local.
- Rate limits: único existente (`MAX_PENDING_PER_WORKSPACE = 10`) é DB-backed.
- Background tasks: 0 ocorrências de `asyncio.create_task`, `BackgroundTasks`
  ou `threading.Thread` em app code — tudo vai pelo Celery.
- File locks: 0 ocorrências de `fcntl`/`flock`/`filelock` em `backend/` + `pipeline/`.

O risco portanto já **estava** mitigado por acaso/coincidência de boas
decisões anteriores. A contribuição de A6f.6 passa a ser:

1. **Auditar** e documentar o estado (cria memória organizacional).
2. **Proteger** com um teste de integração que falha em regressões.
3. **Formalizar** o padrão como regra operacional para novo código.

**Alternativas consideradas:**

1. **Não formalizar** (status quo) — risco: próxima sessão adiciona
   `_request_counter = {}` num módulo e não tem como diferenciar isso
   de `_MONTH_PT` (constante OK). Descartada: o custo de uma regra
   explícita é pequeno.
2. **Lint custom** (proibir globais mutáveis via AST check) — descartada
   por ora; exemplos legítimos (singletons lazy, `engine`) tornam a regra
   difícil de expressar sem falsos positivos. Audit + teste empírico
   dão o mesmo valor com menos fricção.
3. **Teste multi-processo real** (spawn 2 uvicorn + 2 celery via
   `multiprocessing.Process`) — descartada: flaky em CI, lento, exige
   Redis real + Postgres real. O teste empírico com `AsyncClient`s
   duplos + fakeredis compartilhado exercita o que a aplicação pode
   quebrar; isolamento real de processos é responsabilidade do
   framework (FastAPI + Celery).
4. **Gate manual via runbook** sem teste automatizado — descartada: o
   teste é barato, dá sinal imediato em PR e não depende de humano
   executar checklist.

**Decisão:**

1. `docs/reference/STATELESS_AUDIT.md` é o catálogo canônico — qualquer novo
   global de módulo entra nessa tabela com veredito (imutável,
   idempotente, ou **proibido**).
2. `backend/tests/integration/test_multi_worker_concurrency.py` é o gate
   automatizado. Cobre os 4 cenários críticos:
   - JWT cross-worker (2 AsyncClients + mesmo `SECRET_KEY`).
   - Upload/query cross-worker (2 AsyncClients + mesma DB).
   - Rate limit cross-worker (alternância A/B, 11ª = 429).
   - WS + pub/sub cross-worker (TestClient sync + fakeredis shared server).
3. Regra operacional **R19** formalizada (complementar ao R19 genérico
   em ADR-102):
   - **Zero estado mutável in-memory** em nível de módulo/classe em
     `backend/app/` e `pipeline/`. Exceções explicitamente aceitas:
     (a) constantes imutáveis (regex compilados, mappings de domínio,
     thresholds); (b) singletons lazy **idempotentes** (mesma key
     produz mesmo objeto em qualquer worker — ex: `engine` SQLAlchemy,
     `_redis_client` Redis, `_singleton` Vault).
   - **Proibido**: cache por-request, counter compartilhado, `set` ou
     `dict` que acumula entre requests, `@lru_cache` em código de
     aplicação, `asyncio.create_task` fora do Celery, file lock
     (`fcntl`/`flock`/`filelock`).
   - Qualquer "queria usar cache de resposta" resolve via Redis, não
     memória local.
   - Qualquer "queria rate-limit" resolve via DB (invitation pattern)
     ou Redis `SET NX` + TTL — nunca token bucket em memória.
4. `_PLAYWRIGHT_AVAILABLE` em `services/pdf_renderer.py` é **workaround
   aceito** (capability probe idempotente cross-worker) — documentado no
   audit §2.
5. **Runbook de fail-over manual** (cenário 5 — worker A morre durante
   request) referenciado em `docs/reference/RUNBOOK.md`; não é parte do gate
   automatizado porque depende de infra real.

**Contratos a manter:**

- `publish_event()` em `services/events.py` é a **única** via de
  comunicação workers → clientes. Qualquer evento novo (stage,
  activity, needs_review, terminal) passa por aí — Celery não
  abre WebSocket direto, uvicorn não pushea para Celery sem Redis.
- Canal `pipeline:{run_id}` é o contrato pub/sub (ver ADR-095 F6.5B.14).
- `MaterializationBridge` + `DBArtifactStore` (ADR-086) são os únicos
  adapters autorizados a cruzar framework boundary do `pipeline/`.
- Adicionar módulo global novo (`_ALGO = ...` no topo de um arquivo)
  exige decisão consciente: se não é imutável nem idempotente, **não
  adicione**. Se é, adicione entrada ao audit.

**Consequências:**

- ✅ Garantia empírica testada (5 tests) de que 2 workers + 1 Celery
  funcionam com Redis + Postgres como único estado compartilhado.
- ✅ Zero refactor de código de aplicação (WS já era pub/sub, rate
  limit já era DB). A6f.6 fecha em docs + testes.
- ✅ Regra de oro documentada para novos módulos (audit + §R19 do
  ADR-102 + regra operacional no CLAUDE.md).
- ⚠️ Teste usa **fakeredis** + `AsyncClient` duplicado, não processos
  reais. Runbook manual (`docs/reference/RUNBOOK.md` — a criar) cobre fail-over.
- ⚠️ `MATHOMS_USE_DB_ARTIFACTS=False` (default **na época deste ADR**;
  flipado para `True` em
  [ADR-118](#adr-118--flip-do-default-mathoms_use_db_artifacts-para-true)
  em 2026-04-23) mantém escrita em disco via `DiskArtifactStore`. Em
  produção multi-worker com disco compartilhado, concurrency depende de
  Celery `task_acks_late=True` garantir 1 worker por `run_id`. Cutover
  pleno (A6-human → A6c) elimina essa classe de risco escrevendo via DB.
- ❌ Novo dev que adicione dict mutável global precisa conhecer a regra
  — mitigado por (a) code review; (b) audit como referência viva;
  (c) CLAUDE.md "Regras operacionais" lista a proibição.

**Artefatos:**

- [docs/reference/STATELESS_AUDIT.md](../reference/STATELESS_AUDIT.md) — catálogo de 10 seções
  com veredito por arquivo + gap list.
- [backend/tests/integration/test_multi_worker_concurrency.py](../../backend/tests/integration/test_multi_worker_concurrency.py) —
  5 tests, 1.05s, sem Redis/Postgres reais.
- Regras novas em `CLAUDE.md` §"Regras operacionais" — proibição
  explícita de `asyncio.create_task`, globais mutáveis, file locks.

**Próxima sub-fase relacionada:** nenhuma direta — A6f está dividida em
.2 ✅, .3 ✅, .5a ✅, .6 ✅; .1 (pipeline-as-service) e .4 (DB schema
review) seguem independentes. A6-human (§18 do plano) valida cutover DB
end-to-end e destrava A6c (remoção do `MaterializationBridge`).

## Correção do método de verificação — 2026-08-03

`_start_fallback_thread` em `services/pipeline/pipeline_service.py` fazia
`threading.Thread(target=..., daemon=True)` desde `6219acd5` (2026-04-14), **6
dias antes** deste audit. A afirmação "0 ocorrências" e o eco dela em
`STATELESS_AUDIT.md` §5 nasceram falsos e sobreviveram 3,5 meses. Não houve
drift — houve ausência de verificação.

**Lição transferível: afirmação de audit sem gate é dívida, não garantia.** Um
documento que conta ocorrências à mão registra o momento em que foi escrito, não
um invariante; e o próprio gate empírico desta ADR
(`test_multi_worker_concurrency.py`) testa **comportamento** multi-worker, não a
**ausência das primitivas** proibidas — nunca teve como pegar isto.

**Emenda ao ponto 2 (gate automatizado):** o gate passa a ser um par.

1. `test_multi_worker_concurrency.py` — comportamento (inalterado).
2. `dev/check_stateless_primitives.py` — ausência das primitivas nomeadas como
   proibidas no ponto 3, em `backend/app/**` + `pipeline/**`, hard-fail em
   `pre-commit`, allowlist por `(path, símbolo)` com justificativa. Cada entrada
   da allowlist deve estar mencionada em `STATELESS_AUDIT.md`, fechando o loop
   doc↔código.

Isto **não** contradiz a alternativa 2 rejeitada acima: ela descartou lint para
**globais mutáveis**, onde singleton legítimo é indistinguível de dict acumulador
por AST. Conjunto fechado de primitivas nomeadas é a metade tratável, com zero
falso-positivo. §2 deste audit segue manual, pela razão original.

Consequência editorial: §5 e §6 do `STATELESS_AUDIT.md` deixam de afirmar "zero
resultados" e passam a apontar para o gate. O que substituiu a contagem à mão foi
o mecanismo, não uma contagem nova.
