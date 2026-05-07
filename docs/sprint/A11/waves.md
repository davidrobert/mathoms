# Sprint A11 — Ondas (mapa de dependências)

> Bloqueio duro: Wave 2 só destrava após Wave 1 ✅. Wave 4 só após W4-T01 (backup off-site) validado em drill. Wave 5 ativa em paralelo a W6 (independentes).

```
╔════════════════════════════════════════════════════════════════════╗
║ WAVE 1 — Hot patches + ADR backfill (5d, 8 tasks)                  ║
╠════════════════════════════════════════════════════════════════════╣
║  P0 latentes em main: tokens fantasma, regras dormentes,           ║
║  PII em pipeline_artifacts. ADRs 170-175 backfill (Proposto).      ║
║  ✅ entregue 2026-05-06/07                                          ║
╚════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ WAVE 2 — Pipeline + DB hardening (7d, 6 tasks)                     ║
╠════════════════════════════════════════════════════════════════════╣
║  Stuck-runs heartbeat (ADR-172), schemas E5 strict, prompt          ║
║  injection defense (ADR-175), pipeline observability.              ║
║  ☐ ready (W1 mergeada)                                              ║
╚════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ WAVE 3 — Auth + LLM ops + Email (12d, 5 tasks)                     ║
╠════════════════════════════════════════════════════════════════════╣
║  Refresh tokens (ADR-170), Fernet rotation (ADR-171), LLM budget    ║
║  hard-stop + LLMCallLog (ADR-173), email infra.                    ║
║  ☐ blocked (W2 ✅)                                                  ║
╚════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ WAVE 4 — Production readiness (10d, 5 tasks)                       ║
╠════════════════════════════════════════════════════════════════════╣
║  Off-site backup R2 (ADR-174) + DR drill, F7B/F7E security pré-    ║
║  prod, rate limit hardening, deploy strategy.                       ║
║  ☐ blocked (W3 ✅ + drill backup)                                   ║
╚════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════╗
║ WAVE 5 — Frontend + Methodology (10d, 5 tasks, paralelo W6)        ║
╠════════════════════════════════════════════════════════════════════╣
║  Frontend a11y residual, metodologia financeira (Perini/Cerbasi/   ║
║  AUVP), UX cross-route coherence.                                   ║
║  ☐ ready (W1 ✅ parcial)                                            ║
╚════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════╗
║ WAVE 6 — Tech debt cleanup (12d, 6 tasks, paralelo W5)             ║
╠════════════════════════════════════════════════════════════════════╣
║  F9 cleanup (rename completion), MLOps universal hooks,            ║
║  schemas E5 strict completion, code quality residuals.              ║
║  ☐ blocked parcial (W3-T02 → W6-T02)                                ║
╚════════════════════════════════════════════════════════════════════╝
```

## Coordenação multi-agente A11

- Branches usam prefix `agent/platform-review-w<N>-t<NN>/<timestamp>` (ex.: `agent/platform-review-w2-t01/20260510-0930`).
- **Hotspot principal:** [docs/PLATFORM_REVIEW_PLAN.md](../../PLATFORM_REVIEW_PLAN.md) — atualizar frontmatter `ready_tasks` quando wave fecha + status na tabela de cada wave + adicionar checkbox ✅ na seção da wave.
- **Hotspots secundários:** este BACKLOG (linha de status na tabela A11), `docs/CHANGELOG.md` (entry por PR mergeado referenciando W<N>-T<NN>).
- **CTO supervision** segue padrão A7/A10 (4 gates). Wave boundary review obrigatório antes de destravar wave seguinte.
- **Re-sync periódico em sessão >1h:** `git fetch origin && git log --oneline HEAD..origin/main` a cada ~30min. Se outra task A11 mergeou, releia [PLATFORM_REVIEW_PLAN.md §<wave em curso>](../../PLATFORM_REVIEW_PLAN.md).
