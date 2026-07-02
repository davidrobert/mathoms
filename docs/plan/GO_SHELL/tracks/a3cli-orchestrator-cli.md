---
id: TRACK-a3cli-orchestrator-cli
type: track
title: "Track A3.cli — entry-point CLI run-stage no orchestrator + injeção DBArtifactStore (Fase 1) + OTel TRACEPARENT (Fase 2)"
plan: PLAN-go-shell
status: consumed
created_at: "2026-07-02"
consumed_at: "2026-07-02"
agent_role: senior-cto
tags:
  - type/track
  - area/pipeline
  - area/observability
  - status/consumed
  - priority/p2
---

# Track A3.cli — `a3cli-orchestrator-cli`

> **Status 2026-07-02 — CONSUMED: Fase 1 ✅ (PR #737) + Fase 2 ✅ (PR #738).**
> Fase 2: `TRACEPARENT` → span filho W3C; provider via `OTEL_EXPORTER_OTLP_ENDPOINT`
> (`setup_otel` do backend, ADR-110); `_run_stage` emite os 6 attributes canônicos
> em todo caminho. Próximo da fila: [a3cli-benchmark](a3cli-benchmark.md).
>
> **Fase 1 ✅ entregue (PR #737):** `pipeline/cli_run_stage.py`
> + `backend/app/services/artifact_session_factory.py` (a sessão vive no backend —
> hook ADR-256 proíbe `Session` própria em `pipeline/**`; o plano original de
> abrir sessão no CLI era inviável). Precisões descobertas na execução: o env é
> **`MATHOMS_DATABASE_URL`** (prefixo canônico do backend, formato async
> `sqlite+aiosqlite://`/`postgresql+asyncpg://`), a assinatura ganhou
> **`--workspace-id`** obrigatório (tenancy do store, ADR-303 D3), e o CLI faz
> swap stdout→stderr durante a execução (echo do engine com `MATHOMS_DEBUG`
> poluía o stdout). **Resta a Fase 2 (OTel).**
>
> Executa os pré-requisitos **A3.cli + A3.cli.otel** do Caminho 1 ([[ADR-150]] §4).
> **Sem ADR nova** — a ADR-150 declara A3.cli "slice próprio, sem ADR" (interface
> aditiva, retro-compatível com `_run_stage` programático); a mecânica de store é
> consumo da [[ADR-303]] (D1/D4), já `Decidido` — **não reabrir**.
> **Branch prefix:** `agent/a3cli-orchestrator-cli/*`. **2 PRs** (um por fase);
> Fase 1 é mergeável sozinha.
> **Tese:** sem CLI, o shell Go do Caminho 1 vira hack de import dinâmico. O
> entry-point `python -m pipeline.orchestrator run-stage` é a interface estável
> que o `exec.Command` do Go (futuro) consome — e já serve debug/ops local hoje.

## Contexto mínimo (ler antes)

- [[ADR-150]] §4 (assinatura do CLI + sub-requisitos) e §Consequências (attributes OTel).
- [[ADR-303]] D1 (sessão+store por-stage), D2 (`base_run_id`/`base_run_fallback_stages`),
  D4 (fail-fast estruturado), D5 (suíte `pipeline-service/tests` no CI — não regredir).
- Implementações existentes da mecânica de injeção (espelhar, **não** reinventar):
  `backend/app/tasks/pipeline_task.py::_open_artifact_session` (Celery, produção) e
  `pipeline-service/app/services/artifact_session.py` (modo HTTP, #723).
- `pipeline/orchestrator.py` — `_run_stage`, `StageResult` (5 campos: `stage`,
  `success`, `duration_ms`, `detail`, `error`), `LLM_STAGES`; `pipeline/stage_spec.py`
  — `STAGE_REGISTRY`, `resolve_stage_name`.

## Restrições de boundary (invariantes — violação = PR rejeitado)

1. **`pipeline/**` não importa `fastapi`/`celery`/`sqlalchemy`**
   (`dev/check_pipeline_boundaries.py`, gate estático por raiz de import). Import
   de `backend.*` **não é banido** pelo gate e é o caminho aceito ([[ADR-303]] D1) —
   mas deve ser **lazy** (dentro da função de injeção), por três razões: (a) o CLI
   permanece importável/`--help` sem backend instalado; (b) cold start não paga
   SQLAlchemy à toa (o benchmark T2 mede isso); (c) fail-fast do D4 vira erro
   estruturado, não `ImportError` na linha 1.
2. **NÃO importar nada de `pipeline-service/**`** — o pacote será descomissionado
   na F3 ([[ADR-150]] §8); o CLI não pode depender dele. Se quiser dedupe da
   mecânica de sessão (3º call-site da rule-of-3), extraia helper para
   `backend/app/services/` (importável pelos três consumidores) — **sem** importar
   módulo que puxe `celery` no CLI.
3. **Importar a classe `backend.app.services.db_artifact_store.DBArtifactStore`,
   nunca reimplementar** — validação `SCHEMA_BY_STAGE` + crypto vivem no `write()`
   ([[ADR-303]] D1).
4. Dinheiro nunca `float` (ADR-090); nenhum dado sensível em logs/stdout de erro.

## Fase 1 — CLI `run-stage` (PR 1)

Assinatura ([[ADR-150]] §4, verbatim):

```
python -m pipeline.orchestrator run-stage <stage> --workspace <path> --run-id <id> \
  [--config-dir <path>] [--incremental] [--incremental-doc <path>...]
```

Passos (1 commit coeso por passo):

1. **Entry-point** — `if __name__ == "__main__"` em `pipeline/orchestrator.py` (ou
   `pipeline/__main__`-style equivalente que preserve `python -m pipeline.orchestrator`),
   `argparse` com subcomando `run-stage`. `<stage>` aceita nome descritivo ou legado
   via `resolve_stage_name` (ADR-093); stage inexistente → erro estruturado listando
   os válidos. Atenção ao limite de 4-20 linhas/função — decomponha (parse / injeção /
   execução / serialização).
2. **Injeção de store por-stage** — lê `DATABASE_URL` do env; lazy-import do backend;
   sessão nova + `DBArtifactStore` injetado em `ctx.artifact_store`, commit/rollback/
   close ao fim (espelho de `_open_artifact_session`). Sem `DATABASE_URL` ou backend
   não-importável → **exit code ≠0 + stderr JSON estruturado nomeando a causa e a
   [[ADR-303]] D4** — nunca `RuntimeError` opaco no meio do stage.
3. **Output** — stdout: **somente** o JSON do `StageResult` (mesmo shape do caminho
   programático — prints de progresso dos scripts legados não podem contaminar o
   stdout; redirecione/capture para stderr). stderr: erros estruturados. Exit codes:
   0 = success, 1 = falha de stage, 2 = erro de invocação/ambiente.
4. **Incremental / from_stage não-decorativo** — `--incremental`/`--incremental-doc`
   exercitam o caminho real (ADR-080) e o CLI aceita `--base-run-id` +
   `--base-run-fallback-stages` (paridade com o delta aditivo do contrato HTTP,
   [[ADR-303]] D2 / ADR-291) — sem eles, from_stage quebra no subprocess exatamente
   como quebrava no modo HTTP.
5. **Testes** (F.I.R.S.T; fixture sintética PII-zero, ex.
   `tests/fixtures/pipeline_golden/dogfood/`):
   - integração: CLI executa `reconcile_transactions` (stage não-LLM) com store
     SQLite; artefato persistido e verificável em `pipeline_artifacts`;
   - **paridade de shape**: dict do stdout == `asdict(StageResult)` do caminho
     in-process para o mesmo stage/fixture (snapshot que **falha** se `StageResult`
     mudar — o CLI é interface versionada, não script);
   - fail-fast: sem `DATABASE_URL` → exit 2 + stderr estruturado;
   - incremental: com `--base-run-id`, artefato do run base é reusado (não recomputa);
   - stage inválido → exit 2 + lista de stages válidos.

## Fase 2 — OTel `TRACEPARENT` (PR 2)

1. CLI lê `TRACEPARENT` do env e restaura o contexto (W3C trace context propagation);
   o span do stage nasce **filho** do trace do chamador (Go parent, no futuro).
2. Paridade bit-exact ([[ADR-150]] §Consequências — é gate de cutover, não nice-to-have):
   nome `pipeline.<stage>` + os 6 attributes canônicos (`pipeline.stage`,
   `pipeline.workspace_root`, `pipeline.run_id`, `pipeline.is_llm`,
   `pipeline.success`, `pipeline.exit_code`). Reuse o span já emitido por
   `_run_stage` — não crie span duplicado.
3. Sem `TRACEPARENT` → CLI executa normal (span raiz); nunca crasha por ausência.
4. Testes com exporter in-memory: parent trace-id == o injetado; nome + 6 attributes
   presentes; execução sem `TRACEPARENT` ok.

## Critério de aceite (concluído = 2 PRs mergeados em `main`, CI verde)

- [x] F1: os testes da Fase 1 passam (7 em `tests/test_cli_run_stage.py`, PR #737);
      `pytest tests -q` e `pytest backend/tests -q` verdes; suíte
      `pipeline-service/tests` **não regride** ([[ADR-303]] D5).
- [x] F1: `python -m pipeline.orchestrator run-stage --help` funciona **sem**
      `MATHOMS_DATABASE_URL`/backend no env.
- [x] F2: testes de trace passam (3 em `tests/test_cli_run_stage_otel.py`, PR #738);
      gate `dev/check_pipeline_boundaries.py` verde.
- [x] ADR-150 §4: A3.cli ✅ em #737; A3.cli.otel ✅ em #738 + F0 do
      [_README do plano](../_README.md) e `GO_PORT_DEPS.md` §6 atualizados.

## Fora de escopo

- Qualquer mudança no contrato HTTP do pipeline-service além do já entregue
  ([[ADR-303]] D2). Precisou? **Pare e invoque `senior-cto`** — vira ADR.
- Benchmark de cold start → [track seguinte](a3cli-benchmark.md).
- Worker pool / Caminho 2, codegen Go, qualquer `.go`.
