---
id: CHG-2026-05-22-A18-L3-FIPE-SHIPPED
type: changelog-entry
date: "2026-05-22"
sprint: A18
lane: "[[A18.l3]]"
adrs: ["[[ADR-239]]"]
summary: |
  docs(adr-239): A18 L3 (FIPE refresh assíncrono via BrasilAPI) flippada
  → shipped retroativo após P1 (#431) e P2 (#433) mergeados. Lane V1
  entregue (Protocol + adapter + cron Janeiro + cache reader). P3 hook
  E5 enfileira refresh em miss rastreado como débito V2.
tags:
  - type/changelog-entry
  - sprint/a18
  - status/shipped
  - area/pipeline
  - area/persistence
---

# docs(adr-239): A18 L3 FIPE refresh V1 shipped (flip retroativo)

## Sumário

Lane [[A18.l3]] flippada `planned → shipped` retroativamente após auditoria de documentação. P1 e P2 entregaram caminho crítico:

- **P1** [#431](https://github.com/davidrobert/mathoms/pull/431) — `FipeLookupClient` Protocol + `InMemoryFipeLookup` + `BrasilAPIFipeClient` HTTP adapter + Celery task `refresh_fipe_value` com backoff exponencial. 37 testes (parser, validation, InMemory, cache flow).
- **P2** [#433](https://github.com/davidrobert/mathoms/pull/433) — Celery beat `fipe-refresh-annual` (cron 15-Jan 03:00 UTC) + `read_fipe_cache` helper consumido por A19. 9 testes adicionais (46 verde no agregado FIPE).

## Por que flip retroativo

P1+P2 cobriram o caminho crítico ADR-239 D5: lookup assíncrono, cache TTL 30d, cron anual. P3 (hook E5 que enfileira refresh em cache miss automaticamente) e goldens BrasilAPI mock HTTP foram identificados como refinamentos opcionais — ProtecaoAnalyzer V1 consume `read_fipe_cache` retornando `pending_refresh` quando ausente, sem bloqueio.

Manter `planned` por 8h pós-merge de P2 era inconsistente com a realidade do main. Flip retroativo + débito explícito no corpo da lane mantém honestidade documental sem esperar V2 condicional.

## Débitos V2 (rastreados no corpo da lane)

- **P3** — Hook E5 enfileira `refresh_fipe_value.delay()` em cache miss (gatilho automático).
- **Goldens BrasilAPI** — `httpx_mock` cobrindo response real (3 cenários G6).
- **Catálogo `institutions.brasilapi`** — entry `category='reference_data'` para exibir provedor.
- **Stage E1.5c propaga `fipe_status`** para `baseline.veiculos_consolidados[]`.

## ADR-239 §L3

Documento canônico permanece em `Decidido (Sprint A18)` no frontmatter — sem alteração necessária. Lane individual reflete shipping V1 + débito V2 separadamente.
