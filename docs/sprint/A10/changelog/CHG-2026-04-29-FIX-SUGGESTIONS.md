---
id: CHG-2026-04-29-FIX-SUGGESTIONS
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-153]]"]
summary: |
  fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29). - **fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29):** rodar o pipeline completo deixava `/acao` Inbox e `SuggestionCallout` do relat
tags:
  - type/changelog-entry
  - sprint/a10
---


# fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29)

- **fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29):**
  rodar o pipeline completo deixava `/acao` Inbox e `SuggestionCallout`
  do relatório vazios — Onda 5 entregou gerador, endpoint
  `POST /reports/{id}/regenerate-suggestions` e UI consumidora, mas
  **nenhum lugar disparava** o endpoint. Adicionado
  `_persist_aggregate_suggestions(ws_id, run_id)` em
  `backend/app/tasks/pipeline_task.py` (sync, espelha o use case async
  pelo motivo já documentado em `_persist_llm_suggestions`:
  `asyncio.run()` em gevent crasha) chamado dentro de
  `_run_post_processing` após `_create_report_from_output`. Idempotente
  via `dedup_key` (ADR-153 §2). [ADR-153](DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples)
  recebeu nota datada clarificando que "trigger via endpoint dedicado,
  NÃO hook do pipeline" referia-se ao boundary `pipeline/**` →
  `backend.*` (que segue valendo); disparar de `pipeline_task.py`
  (backend→backend) não viola o boundary. Endpoint REST permanece para
  re-execução manual (debug, smoke test, regerar após mudança nas
  regras). 4 testes novos em `TestPersistAggregateSuggestions`
  (caminho feliz · idempotência · sem artefato · snapshot saudável).
