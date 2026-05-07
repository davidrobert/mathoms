---
id: CHG-2026-04-26-A10-CARD-CONSUMO-CONSCIE
type: changelog-entry
date: "2026-04-26"
sprint: A10
adrs: ["[[ADR-133]]"]
commits: ["95f841c", "ba7b92e", "66e9030"]
summary: |
  Card "Consumo Consciente" — bug fix + ADR-133 (2026-04-26) — ✅. - **Card "Consumo Consciente" — bug fix + ADR-133 (2026-04-26) — ✅:** resolução do bug onde PIX entre contas próprias da família apareciam como gastos pontuais no card.
tags:
  - type/changelog-entry
  - sprint/a10
---


# Card "Consumo Consciente" — bug fix + ADR-133 (2026-04-26) — ✅

- **Card "Consumo Consciente" — bug fix + ADR-133 (2026-04-26) — ✅:**
  resolução do bug onde PIX entre contas próprias da família apareciam
  como gastos pontuais no card. Solução em três camadas:
  (a) novo endpoint `GET /workspaces/{id}/reports/consumo-pontuais` que
  centraliza no backend a lista filtrada — antes vivia em
  `frontend/src/lib/periodUtils.ts::filterConsumoPontuais` (filtro local
  só por valor + receita, sem detecção de transferência interna);
  (b) defesa em profundidade aplicando `InternalTransferDetector` sobre
  a descrição mesmo quando o E4 cai em `nao_identificado`;
  (c) **[ADR-133](DECISIONS.md#adr-133--transferencias_internas-modelado-em-transfer_configs-workspace-scoped)** —
  bloco `transferencias_internas` extraído de `config/family_members.json`
  para a tabela `transfer_configs` (workspace-scoped). Migration
  `w1x2y3z4a5b6`. Endpoints `GET/PUT /config/transfer`. Materializer
  ganha `_override_transfer_config` (overlay em `family_members.json`
  com fallback ao global). `list_consumo_pontuais` deixa de ler disco;
  recebe `InternalTransferDetector` injetado via
  `resolve_internal_transfer_detector` (DB-first → defaults globais).
  UI de edição entregue em **ADR-133b** (commits `95f841c` + `ba7b92e`
  + `66e9030`): aba "Transferências" em `/config` + rota dedicada
  `/config/transfer` com 4 seções editáveis (Recipients, Padrões PIX,
  Padrões Globais, Padrões por Banco). Add/edit/remove inline + Save
  desabilitado até dirty + `role="alert"`/`role="status"` para erro/
  sucesso. 6 unit tests Vitest verde + 1 E2E Playwright `@critical`.
