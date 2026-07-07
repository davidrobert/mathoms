---
id: A33.l3
type: lane
title: "PROMPT_VERSION semver puro nos 5 prompts legados + confidence/prompt_version persistidos em llm_call_log (W2)"
sprint: A33
plan: PLAN-llm-prompts-hardening
status: open
priority: P1
branch_slug: a33-l3-prompt-semver-telemetria
adrs: ["[[ADR-233]]", "[[ADR-081]]"]
depends_on: []
parallel_with: ["[[A33.l1]]", "[[A33.l2]]"]
tags:
  - type/lane
  - sprint/a33
  - status/open
  - priority/p1
  - area/llm
  - area/observability
---

# A33.l3 — `prompt-semver-telemetria` (W2 do [[PLAN-llm-prompts-hardening]])

## Problema

5 prompts usam `PROMPT_VERSION` em slug legado (`apolice-v1.0.0`,
`crlv-v1.0.0`, `e16-v1.1.0`, `informe-aluguel-v1.1.0`,
`informe-prev-v1.0.0`) contra o semver puro decidido em [[ADR-233]];
`informe_aluguel.py` não tem `PROMPT_VERSION` no arquivo do prompt (o
gate `check_prompt_version_bumped.py` monitora o arquivo — hoje é cego
para ele). `pipeline/llm/litellm_client.py:69-86` (`LLMCallResult`)
captura tokens/custo/duração mas **não captura `confidence` nem
`prompt_version`** — os thresholds de [[ADR-081]] (<0.7/<0.8) seguem
teoria sem dado empírico.

## Escopo

1. Migração dos 5 prompts legados para semver puro, com **migration
   coordenada** de `LLMCallLog.prompt_version` rows +
   `pipeline_artifacts.metadata.prompt_version` (preserva a dimensão
   histórica de telemetria — decisão 1 da revisão do plano).
2. Errata datada em [[ADR-233]] cobrindo a migração dos legados
   (padrão de emenda ADR-027: `amended_at` + blockquote de sinal).
3. `LLMCallResult` ganha `confidence` + `prompt_version` (aditivo,
   dataclass com defaults — não-breaking) e `llm_call_log` persiste ambos.
4. Goldens fiscais do plano: ≥2 fixtures por prompt migrado, incluindo
   caso PGBL+VGBL mesmo CPF (bloqueante do `financial-planner` na
   revisão 2026-05-22).
5. Cache de resposta LLM ([[ADR-307]] F1): bump de versão invalida
   cache — verificar interação e cobrir com teste.

## Critérios de aceite

1. 9/9 prompts em semver puro; gate `check_prompt_version_bumped.py`
   cobre os 9 (incl. `informe_aluguel`).
2. `SELECT confidence, prompt_version FROM llm_call_log` retorna dado
   real para chamada nova de qualquer prompt (KR3).
3. Telemetria histórica preservada: query por `prompt_version` legado
   continua encontrando os rows migrados.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
