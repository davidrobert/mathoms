---
id: ADR-211
type: adr
title: "llm_config e pipeline.json como overrides DB-direto (cutover completo do A7)"
status: Decidido
phase: A12
date: "2026-05-14"
relates_to:
  - "[[ADR-134]]"
  - "[[ADR-137]]"
  - "[[ADR-180]]"
  - "[[ADR-111]]"
  - "[[ADR-109]]"
supersedes: []
superseded_by: []
aliases: ["ADR 211", "llm_config DB override", "A7 cutover final"]
tags:
  - area/backend
  - area/pipeline
  - area/security
  - phase/a12
  - status/decidido
  - type/adr
---

> **Decidido (A12) — rollout parcial.** A decisão (overrides DB-direto p/ `llm_config`)
> está tomada e o **contrato central da lane 1 shipou** (`serialize_llm_config` em
> `build_config_overrides_from_db`). Resíduo de faxina: lane 3 (deletar
> `prepare_pipeline_config_dir`) segue pendente — ver §"Roadmap pós-PR" abaixo. Não há
> tabela duplicada; o roadmap residual é a fonte de status das lanes.

## Contexto

Sprint A7 (ADR-134/137/180) iniciou a migração de configs do filesystem
para o DB via `WorkspaceContext.config_overrides`. Cinco configs foram
migradas:

- `family_members.json` (ADR-134)
- `categorization.json` (ADR-137)
- `institutions.json` (ADR-137)
- `report_layout.yaml` (ADR-134)
- `goals.json` (ADR-180, A10.6)

**Duas configs ficaram para trás** e continuam sendo materializadas em
disco por `prepare_pipeline_config_dir`
([backend/app/services/config_materializer.py:28](../../backend/app/services/config_materializer.py)),
chamada antes de cada `POST /pipeline/run`:

- `llm_config.json` — `LLMConfig` row decifrada via Fernet vault →
  escrita em `<tenant_root>/config/llm_config.json` (plaintext em disco).
- `pipeline.json` — `PipelineConfig` row → escrita em
  `<tenant_root>/config/pipeline.json`.

Stages LLM (`extract_members`, `extract_baseline`, `extract_with_llm`,
`extract_irpf_full`, `review_finances`, `review_finances_holistic`)
leem via `ctx.load_config("llm_config.json")` — que checa
`config_overrides` primeiro e cai no fallback de disco quando ausente.
Hoje só funciona via fallback.

O incidente de 2026-05-14 (PR #255) expôs o gap: o stage
`review_finances_holistic` (parecer planejador, ADR-199) foi escrito
buscando `ANTHROPIC_API_KEY` direto do env em vez de
`ctx.load_config("llm_config.json")`. Quem corrigiu o stage usou o
padrão dos outros stages LLM, mas o caminho continua sendo
"materializar disco → ler do disco". Esta ADR fecha o cutover.

## Decisão

Mover **`llm_config.json`** para `build_config_overrides_from_db`
(DB-direto via `config_overrides`), eliminando a materialização em
disco. **`pipeline.json` fica como roadmap** (lane 2 separada — ver
§Roadmap).

```python
# backend/app/services/pipeline/pipeline_adapter.py
def _llm_config_override(workspace_id, db):
    from backend.app.services.config_materializer import serialize_llm_config
    return serialize_llm_config(workspace_id, db)  # decifra vault

sources = {
    ...,
    "llm_config.json": _llm_config_override(workspace_id, db),
}
```

Stages não mudam — continuam usando `ctx.load_config("llm_config.json")`;
muda apenas a fonte (overrides em vez de fallback de disco).

### Cutover — dual-write defensivo

Em vez de feature flag explícita, usa **dual-write transitório**:

1. **PR de adição (este sprint):** registrar `llm_config.json` em
   `build_config_overrides_from_db`. **Manter** `_override_llm_config`
   rodando paralelo. `ctx.load_config` prefere overrides
   automaticamente; fallback de disco continua funcionando se overrides
   for `None` (workspace sem LLMConfig).
2. **PR de cleanup (sprint+1, após observação em prod):** remover
   `_override_llm_config` e o write. `<tenant_root>/config/llm_config.json`
   deixa de existir. Runbook atualizado.

Dual-write equivale à feature flag de leitura, sem complicar env vars
ou cleanup de flags pós-cutover.

### Boundary preservado

`build_config_overrides_from_db` é chamado **dentro da Celery task**
([backend/app/tasks/pipeline_task.py:484](../../backend/app/tasks/pipeline_task.py)),
não no dispatcher síncrono. Isso preserva a invariante de que
**plaintext da api_key nunca atravessa o broker Redis** —
serializadação Celery do task arg só carrega `run_id`, `ws_id`,
`tenant_root_str`, etc., nenhum secret.

## Não-objetivos (escopo intencionalmente excluído)

1. **Typed value object `LLMConfig` injetado em `WorkspaceContext`**
   (ADR-089/097 D2 estilo). Multiplicaria diff em 6 stages, quebraria
   simetria com os outros 4 configs DB-direto que continuam por nome,
   e não resolve problema real. Avaliar em lane separada se for útil.

2. **`pipeline.json` para overrides** (lane 2). Bloqueada por 7+
   scripts CLI que leem o arquivo via path direto, não via
   `ctx.load_config` — `scripts/e0_route.py:58`, `e2/common.py:83`,
   `e3_reconcile.py:114`, `e4_categorize.py:70`, `e7_review.py:75`,
   `e_reset.py:84`, `e15_consolidate.py:51`, `scripts/pipeline_common.py`.
   Pré-requisito: refactor uniformizando leitura via `ctx.load_config`,
   sub-lane separada com vários PRs incrementais.

3. **Deletar `prepare_pipeline_config_dir` por completo** (lane 3).
   Bloqueada por (a) CLI standalone (`scripts/eN_*.py` rodando fora do
   backend lê de disco) — precisa caminho explícito; (b) `_copy_global`
   ainda copia `config/schemas/*` por tenant (read-only mas usado por
   `pipeline_common.py`). Avaliar deletar após resolver CLI bootstrap.

4. **Scrubber central de secrets em telemetria.** SRE flagou que
   `config_overrides` carregando api_key em memória aumenta surface
   de leak via log estruturado (`MathomsJsonFormatter`), OTel spans,
   Sentry exception capture. Lane separada — adicionar redaction
   central de keys `api_key|*_key|*_secret|*_token` em
   `backend/app/core/logging.py` + OTel hook + Sentry `before_send`.
   Cobertura por teste `test_no_api_key_in_logs.py`. **Não é regressão
   deste refactor** (hoje api_key já vive em memória durante run via
   fallback de disco lido para dict in-process); é débito pré-existente
   que vale endereçar paralelo.

5. **Audit de `pipeline_runs.config_snapshot`.** Campo declarado em
   [backend/app/models/pipeline_run.py:46](../../backend/app/models/pipeline_run.py)
   mas **não populado em runtime** — verificado por grep. ADR-199
   (telemetria do parecer) presume reconstruível mas não depende
   desse campo. Não é regressão deste refactor (hoje o campo já é
   morto); registrar como débito para lane que reativar snapshot
   (cuidado para nunca persistir api_key plaintext em DB sem
   encryption — usar referência a `LLMConfig.id` + `vault_key_id`).

## Alternativas consideradas

**A. Feature flag explícita `MATHOMS_LLM_CONFIG_FROM_DB`.**
Sugerida por sre-devops para rollback rápido. **Rejeitada** em favor de
dual-write defensivo: equivale ao mesmo efeito (fallback automático
quando overrides falha), sem complicar env vars nem exigir cleanup
de flag pós-cutover. Janela de cutover é curta (1 sprint) e o
fallback de disco já funciona como Plan B.

**B. Drop-in completo (remover disco-write no mesmo PR).**
**Rejeitada.** Hot path de boot de pipeline run sem janela de rollback
= risco SEV1 desnecessário. Custo de PR separado para cleanup é
trivial vs. ganho de bisect cirúrgico.

**C. Cache Redis com TTL para chave decifrada.**
**Rejeitada por enquanto.** Decrypt Fernet é ~50-200µs, ruído em run
de 5-15min. Aplicar cache só se benchmark futuro mostrar regressão
(unlikely). Documentado como Plan B.

## Consequências

### Positivas

1. **Stateless rigoroso reforçado (ADR-111).** Elimina side-effect de
   I/O em disco compartilhado entre runs. File write por run era
   estado mutável de facto — worker A pode pisar em worker B se
   workspace_id idêntico (race condition latente, não documentada).

2. **Surface de leak reduzida.** api_key plaintext sai do filesystem.
   Backup do tenant root deixa de capturar credencial. Escalation
   lateral (worker comprometido lendo N tenants em um `find`) é
   cortada — atacante precisa decifrar via DB com creds que deixam
   audit trail.

3. **Paridade com configs A7.** llm_config segue o mesmo padrão dos
   5 configs migrados. Simetria reduz custo cognitivo de manutenção.

4. **Fix bug latente do parecer.** Em PR #255 cobrimos via fallback
   de disco; com overrides DB-direto, o caminho é o canônico desde
   o início.

### Negativas

1. **Decrypt Fernet em hot path.** Uma chamada por run, ms-baixos.
   Mensurável via métrica nova `mathoms.pipeline.config_overrides_build_duration_ms`
   (parte deste PR).

2. **Dual-write transitório.** Por 1 sprint, escrita em disco continua
   acontecendo redundantemente. Custo: ms-baixos extras por run +
   alguns kB de I/O. Aceito como custo de cutover seguro.

3. **CLI standalone não cobre.** `scripts/eN_*.py` rodando fora do
   backend continua precisando de `llm_config.json` em disco —
   nada muda na lane 1. Lane 3 (deletar materialização) precisa
   resolver isso.

### Neutras

- **Schema DB.** Sem mudança. Sem migration Alembic.
- **API portability (ADR-109).** Não toca Fernet payload, JWT, ou
  qualquer surface de auth. Ratificada.

## Critérios de aceite (lane 1)

### Implementação
- `_llm_config_override` em `pipeline_adapter.py` registrado em
  `build_config_overrides_from_db`.
- `_override_llm_config` **mantido** durante janela de cutover.

### Testes
- Teste de paridade `serialize_llm_config (DB) → ctx.load_config (overrides)`
  vs. estado anterior `(disco)`. Assert dict idêntico.
- Regressão em stage LLM (ex.: `extract_members`) com overrides
  populado e disco vazio — sucesso.
- Backward compat: workspace sem `LLMConfig` no DB → overrides retorna
  `None` (via filtro `{k: v for k, v in sources.items() if v is not None}`),
  fallback de disco continua viável (CLI/dev local).
- Auditoria de fixtures: nenhum teste novo escreve `llm_config.json`
  em disco; testes existentes que dependem do disco-write
  ([backend/tests/test_serializers_round_trip.py:376](../../backend/tests/test_serializers_round_trip.py))
  atualizados ou aceitam ambas as fontes.

### Observability
- Métrica `mathoms.pipeline.config_overrides_build_duration_ms` (RED,
  histogram) — adicionada em `build_config_overrides_from_db`. Alerta
  ticket (não page) se p95 > 500ms (sinal de DB saturado).
- Span OTel `pipeline.config_overrides_build` com `decrypt_count` —
  sem PII no atributo. Adicionado se OTel já estiver wired (ADR-110);
  caso contrário, lane separada.

### Documentação
- Runbook `docs/reference/RUNBOOK.md` mantido — instruções de "ssh
  worker, cat llm_config.json" são deletadas no PR de cleanup
  (lane 1 cleanup), substituídas por consulta DB documentada.

## Roadmap pós-PR

| Lane | Conteúdo | Pré-requisito |
|---|---|---|
| 1 (este PR) | `_llm_config_override` + dual-write + testes paridade | — |
| 1-cleanup | Remover `_override_llm_config` + disco-write | Lane 1 estável em prod ≥1 sprint |
| 2-prep | Refactor 7+ scripts CLI lendo `pipeline.json` via path direto → `ctx.load_config` | — |
| 2 | `_pipeline_config_override` mesmo padrão da lane 1 | Lane 2-prep |
| Side | Scrubber central de secrets em logging/OTel/Sentry + teste | — (paralelo) |
| Side | Audit/reativar `pipeline_runs.config_snapshot` (sem api_key plaintext) | — (paralelo, ADR-199 follow-up) |
| 3 | Deletar `prepare_pipeline_config_dir` + `ensure_tenant_pipeline_config` | Lanes 1-cleanup + 2 + CLI bootstrap |

## Referências

- [[ADR-134]] — DB-first para configs editoriais (A7.1).
- [[ADR-137]] — Catalog global + diff workspace (A7.3).
- [[ADR-180]] — `GoalsBundle` DB-first (A10.6).
- [[ADR-111]] — Stateless rigoroso.
- [[ADR-109]] — Auth portability (não afetada).
- PR #255 — `fix(planner): parecer lê api_key de llm_config.json + phases mapping descritivo` (2026-05-14, incidente que motivou esta ADR).
- [backend/app/services/config_materializer.py](../../backend/app/services/config_materializer.py) — origem do disco-write a ser eliminado.
- [backend/app/services/pipeline/pipeline_adapter.py:552](../../backend/app/services/pipeline/pipeline_adapter.py) — `build_config_overrides_from_db`, ponto de entrada da mudança.
