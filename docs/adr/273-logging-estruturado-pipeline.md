---
id: ADR-273
type: adr
title: "Logging estruturado do pipeline (contextvars neutros + bind backend→pipeline + tail bounded)"
status: Decidido
phase: A26
date: "2026-05-30"
relates_to:
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-093]]"
  - "[[ADR-272]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 273"
  - "logging estruturado pipeline"
tags:
  - area/pipeline
  - area/observability
  - status/decidido
  - type/adr
---

# ADR-273 — Logging estruturado do pipeline

**Status:** Decidido (A26 — PR1 entregue 2026-07-03; concebida na Sprint A20) • **Data:** 2026-05-30 • **Relaciona** [[ADR-110]] (logging estruturado do backend — `MathomsJsonFormatter`, correlação, reaproveitado), [[ADR-111]] (stateless rigoroso — contextvar é exceção registrada), [[ADR-093]] (nomes de stage descritivos), [[ADR-272]] (razão estruturada de `needs_review` — par desta ADR no mesmo pacote)

> **Co-design.** Contrato de log / propagação de contexto / custo revisado por `sre-devops` antes do PR. Boundary do `bind()` backend→pipeline a revisar por `senior-cto` no PR de implementação.

## Contexto

Quando o pipeline quebra ou produz output errado, quem depura tem pouquíssimo contexto: os stages logam quase tudo com `print`, e o orchestrator captura **apenas a última linha do stderr** ([`pipeline/orchestrator.py`](../../pipeline/orchestrator.py) — `_extract_error_message`). Todo o contexto que levou à falha é descartado.

Estado atual:

- **Backend já tem logging estruturado** ([[ADR-110]]): `backend/app/core/logging.py` (`MathomsJsonFormatter` injeta `trace_id`/`workspace_id`/`user_id`/`pipeline_run_id` de contextvars + allowlist PII `SENSITIVE_FIELD_SUBSTRINGS`), `backend/app/middleware/correlation.py` (seta os contextvars), `backend/app/core/otel.py` (OTLP opt-in).
- **Pipeline NÃO usa isso** — `print` em `scripts/e*.py` + `pipeline/stages/`.
- **Stages rodam in-process** — o orchestrator faz redirect de `sys.stdout`/`sys.stderr`, não subprocess. Logo **não há perda de contexto por fronteira de processo**; o problema é o redirect que joga o stdout fora.
- **Boundary enforçado:** `pipeline/**` não importa `fastapi`/`celery`/`sqlalchemy` (`check_pipeline_boundaries.py`). A middleware de correlação vive no backend e não pode ser importada pelo pipeline.

## Decisão

Dar ao pipeline logging estruturado próprio (estilo [[ADR-110]]) sem violar o boundary, com **agregação por stage** como caminho primário e **per-decisão atrás de flag**.

### Propagação de contexto — contextvar neutro + bind na fronteira

Módulo `pipeline/observability/context.py` (zero deps de framework) com contextvars próprios: `run_id`, `workspace_id`, `correlation_id`, `stage`. O backend, ao invocar o orchestrator, lê seus contextvars de `correlation.py` e faz `bind()` no módulo do pipeline — **dependência aponta backend→pipeline, nunca o inverso** (se vazar import de backend no pipeline, `check_pipeline_boundaries.py` quebra — é o gate funcionando). Rodando standalone (CLI), os contextvars ficam vazios e degrada limpo.

`get_logger` do pipeline puxa desses contextvars locais. **Não** injetar logger por parâmetro nas funções de domínio — polui assinaturas e viola ISP ([[ADR-089]]/[[ADR-097]]: domain services recebem value objects tipados, não loggers).

É exceção stateless [[ADR-111]] idêntica à já aceita no backend (item (b): singleton idempotente request-scoped) — **registrar em `STATELESS_AUDIT.md §2`** no PR de implementação.

### Cardinalidade — stage-level estruturado, per-decisão atrás de flag

Evento por-transação em E3/E4 (milhares de linhas/run) explode volume e custo. Contrato:

- **INFO** = transição de stage + **agregado final** (`reconciled=N, unmatched=M, needs_review=K`).
- **WARNING** = anomalia recuperável que altera output, emitida **por classe com contador**, não por instância (`needs_review`, fallback LLM, período sentinel `999999`, dedup fuzzy).
- **ERROR** = aborta o stage.
- Per-decisão (linha-a-linha) atrás de `MATHOMS_PIPELINE_DEBUG_DECISIONS`, **stdout→coletor, nunca DB**.

Sem sampling probabilístico no MVP — é cardinalidade categórica, não tráfego; sampling esconderia justamente o evento raro que o agente debugando precisa.

### Retenção — dois sinais separados

- **(a) stdout→coletor** — JSON lines, retenção do coletor (~7–30d), histórico completo.
- **(b) `output_summary` no DB** — **tail bounded estruturado**: últimos ~50 eventos WARNING/ERROR + contadores agregados, hard cap ~8KB. É o que o agente lê primeiro; não é ring buffer de todos os eventos (seria o pecado do `stderr.last_line` invertido).

### PII — reusar o mecanismo + proibir interpolação no `message`

`SENSITIVE_FIELD_SUBSTRINGS` ([[ADR-110]]) já existe e mascara `extra=` por **chave** — mas **não** mascara conteúdo livre de `message`. Contrato:

- **Proibido interpolar valor variável no `message`** (apenas IDs/contadores/enums). `logger.info(f"saldo {valor}")` vaza apesar do formatter.
- Todo dado variável vai via `extra=` com chave allowlisted.
- Gate novo `dev/check_pipeline_log_pii.py` falha se um `logger.*` no pipeline tem f-string com nome de variável conhecido-sensível (`cpf`, `saldo`, `valor`, `descricao`…).

### Orchestrator — parar de depender do `stderr.last_line`

Com o logger estruturado emitindo direto, `_extract_error_message` vira **fallback** para stages legados ainda-em-`print`, não o caminho primário. Migração **stage-a-stage**, não big-bang; o tail estruturado coexiste com `print` durante a transição.

## Consequências

**Positivas:**
- Falha do pipeline passa a ter contexto estruturado (stage/artifact_key/document_id) em vez de uma linha de stderr.
- Correlação ponta-a-ponta backend↔pipeline ([[ADR-110]]) — `trace_id` único do request ao stage.
- Par com [[ADR-272]]: a `ReviewReason` referencia o mesmo `correlation_id`.

**Negativas / trade-offs aceitos:**
- Migração de centenas de `print` é o custo real — incremental, não bloqueante (coexistência durante transição).
- Mais um contextvar (exceção stateless registrada e justificada).
- Gate de PII pode ter falso-positivo em nome de variável inocente — aceito (allowlist explícita resolve).

## Critério de aceite

1. `pipeline/observability/context.py` com contextvars neutros (zero import de framework); `check_pipeline_boundaries.py` continua verde.
2. `bind()` no adapter do backend propaga `correlation_id`/`workspace_id`/`run_id`; log do pipeline carrega os campos.
3. Standalone (sem backend) → contextvars vazios, sem crash.
4. Agregado por stage emitido como INFO; WARNING por classe com contador (não por instância).
5. `output_summary` guarda tail bounded ≤8KB; orchestrator não depende mais de `stderr.last_line` para stages migrados.
6. `dev/check_pipeline_log_pii.py` falha em `logger.info(f"... {cpf}")`; passa com `extra={"cpf_masked": ...}`.
7. Entrada em `STATELESS_AUDIT.md §2` para o novo contextvar.
8. `MATHOMS_PIPELINE_DEBUG_DECISIONS` liga per-decisão (stdout-only).

## Alternativas consideradas

- **Injetar logger por parâmetro nas funções de domínio:** rejeitado — polui assinaturas, viola ISP ([[ADR-089]]).
- **Importar a middleware de correlação do backend no pipeline:** rejeitado — viola o boundary; `check_pipeline_boundaries.py` quebraria.
- **Evento estruturado por-decisão sempre ligado:** rejeitado — explode volume/custo em E3/E4; fica atrás de flag.
- **Sampling probabilístico:** rejeitado no MVP — esconde o evento raro que é justamente o alvo do debug.
- **Manter `stderr.last_line` (status quo):** rejeitado — descarta o contexto que custou tempo nas correções recentes.

## Próximos passos

- **PR1 (este escopo):** `pipeline/observability/context.py` + `get_logger` + `bind()` no adapter + gate PII + tail bounded no `output_summary` + migração de **1 stage piloto** (E3 ou E4) como prova. Flippa para `Decidido (Sprint A20)` no merge.
- **PR2..N (follow-up):** migração stage-a-stage dos `print` restantes.
- **PR final (follow-up):** endpoint interno `ops.mathoms.ai` ([[ADR-116]]) com bundle de diagnóstico consolidado por run (par com [[ADR-272]]).
