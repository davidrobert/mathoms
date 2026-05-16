---
id: CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S
type: changelog-entry
date: "2026-04-25"
sprint: A10
adrs: ["[[ADR-119]]"]
commits: ["e6e9ebd"]
summary: |
  Lane `livestep-emit-stages` E3 — adapter instrumentado (2026-04-25). - **Lane `livestep-emit-stages` E3 — adapter instrumentado (2026-04-25):** oitavo emissor migrado para o contrato [ADR-119](DECISIONS.md#adr-119--contrato-lives
tags:
  - type/changelog-entry
  - sprint/a10
---


# Lane `livestep-emit-stages` E3 — adapter instrumentado (2026-04-25)

- **Lane `livestep-emit-stages` E3 — adapter instrumentado (2026-04-25):**
  oitavo emissor migrado para o contrato
  [ADR-119](../../../DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5/E2/E1/E1.5c/E4/E5/E2-llm). Primeira lane que **instrumenta
  o adapter de domínio** — diferente das stages batch (E1.5c, E4, E5)
  que só ganharam preparing+finalizing pobres no wrapper, E3 tem loop
  real por (banco, conta, período) dentro de
  `E3ReconcilerAdapter.reconcile_via_store`.
  - **Adapter** ganha kwarg opcional `pipeline_run_id: str | None =
    None`. No loop `for key, stmts in grouped.items()` emite duas
    fases por chave: `preparing` (início da iteração) e `persisting`
    (antes de `store.write`). Após o loop, `finalizing` único bypassa
    throttle. `current_item` carrega a chave do artefato (ex.:
    `itau_BRL_202304_202404`).
  - **`scripts/e3_reconcile.py`:** `_e3_run_reconciliation` repassa
    `ctx.pipeline_run_id`; `main_with_store` emite `preparing`
    cosmético (items_total=1) cobrindo a fase silenciosa de
    load+reconcile que precede o primeiro per-key emit.
  - **Trade-off ISP:** domain adapter agora importa
    `pipeline.live_progress.emit_item_progress`. Aceitável porque
    (a) é opcional (None default), (b) `live_progress` é defensivo
    (no-op sem run_id), (c) há precedente de `output_stage`/
    `output_key_fn` como infrastructure concerns na mesma assinatura.
  Commit `e6e9ebd`. Suíte verde: 1464 pipeline + 22 events + 77 E3
  (incluindo golden e adapter direto).
