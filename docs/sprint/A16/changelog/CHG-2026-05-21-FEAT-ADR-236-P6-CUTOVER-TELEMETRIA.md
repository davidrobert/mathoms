---
id: CHG-2026-05-21-FEAT-ADR-236-P6-CUTOVER-TELEMETRIA
type: changelog-entry
date: "2026-05-21"
sprint: A16
lane: "[[TRACK-a16-adr236-tributario-pj-cascata]]"
adrs: ["[[ADR-236]]"]
summary: |
  feat(adr-236 P6): cutover + telemetria LGPD-safe + flip ADR-236 para
  Decidido (Sprint A16 L2 P6 — fechamento da lane).
tags:
  - type/changelog-entry
  - sprint/a16
  - area/methodology
  - area/pipeline
  - area/backend
---

# feat(adr-236 P6): cutover + telemetria + flip ADR-236 (Sprint A16 L2 P6)

P6 fecha a L2 (`tributario-pj-cascata`). Conecta a telemetria estruturada
de 3 eventos categóricos, endurece a denylist LGPD para o domínio
tributário PJ, publica FAQ produto e flippa [[ADR-236]] para
`Decidido (Sprint A16)`.

**Entregue:**

- [backend/app/services/tributario_telemetry.py](../../../../backend/app/services/tributario_telemetry.py) (NOVO) —
  3 emitters categóricos de logger estruturado:
  - `emit_cascata_rendered(regime, has_complete_profile, triggers_count)`
  - `emit_trigger_shown(trigger_code, regime)` — 1 por trigger no array (T1-T5)
  - `emit_profile_incomplete(missing_fields)` — só quando perfil incompleto
  - `emit_telemetry_for_section(...)` orquestra o pipeline completo.
  - `compute_profile_completeness(regime, anexo_simples, tipo_declaracao_ir)`
    retorna `(is_complete, missing_fields)` — `simples` exige `anexo_simples`,
    todos exigem `tipo_declaracao_ir`.

- [backend/app/services/pipeline_adapter.py](../../../../backend/app/services/pipeline/pipeline_adapter.py) —
  `_build_tributario_section_sync/async` chamam novo helper
  `_emit_tributario_telemetry(bp, cascata_dict)` após `cascata_compute`,
  antes de montar a seção. Sem mudança de contrato em
  `TributarioBundleSection`.

- [backend/app/core/logging.py](../../../../backend/app/core/logging.py) —
  `SENSITIVE_FIELD_SUBSTRINGS` ganha 21 substrings do domínio tributário
  (`receita_pj`, `pro_labore`, `lucros_distribuidos`, `lucro_contabil`,
  `folha_pj`, `das_pago`, `iss_pago`, `iss_total`, `pgbl_base`,
  `pgbl_limite`, `renda_pf`, `outras_rendas`, `inss_patronal`,
  `inss_empregado`, `irrf`, `tributos_federais`, `carga_total`,
  `break_even`, `razao_social`, `nome_fantasia`, `receita_bruta`,
  `receita_aluguel`). Defesa em profundidade contra regression de
  caller futuro que tente passar Money via `extra=`.

- [tests/test_telemetria_lgpd.py](../../../../tests/test_telemetria_lgpd.py) (NOVO · 13 casos):
  - 5 unit tests de `compute_profile_completeness` (cada regime + missing).
  - 4 whitelist tests por evento — afirma que `extra=` contém apenas
    campos enumerados (`event_type`, `regime`, `has_complete_profile`,
    `triggers_count`, `trigger_code`, `missing_fields`).
  - `test_emit_full_section_pipeline` — perfil incompleto: 1
    cascata_rendered + N trigger_shown + 1 profile_incomplete.
  - `test_emit_full_section_complete_profile_no_incomplete_event`.
  - **Gate hard `test_tributario_no_money_in_logs`** — 21 campos
    monetários canônicos da CascataOutput passados via `extra=` são
    mascarados a `***` pelo formatter.
  - `test_tributario_money_substrings_in_denylist` — invariante:
    novo campo Money em ADR-236 precisa ser adicionado à denylist.
  - `test_emitted_events_have_no_money_keys` — pipeline real
    `emit_telemetry_for_section` não vaza substring monetário.

- [docs/reference/FAQ_cascata_fiscal_pj.md](../../../reference/FAQ_cascata_fiscal_pj.md) (NOVO) —
  FAQ produto com 4 seções:
  1. Como o Mathoms calcula a cascata fiscal (inputs declarados ≫
     derivados, calculator puro, limites V1).
  2. **Por que o limite PGBL é diferente do que outras planilhas
     falam** (base = renda tributável PF, **não** `receita_pj × 32%`;
     desmonta confusão clássica com presunção 32% IRPJ/CSLL).
  3. Sobre os 5 decision triggers (T1-T5 + folclore rejeitado).
  4. Telemetria LGPD-safe (categorias-only).

- **Sunset audit do código canned** — `grep -rn "Lucro presumido (32%)"`
  retorna **zero hits** em `pipeline/`, `backend/`, `frontend/src/`. P4
  (PR #394) já removeu o texto canned ao reescrever `narrate_cascata`
  ramificando por regime ([[ADR-236]] §D4). Esta fase apenas confirma
  o estado.

- [docs/adr/236-tributario-pj-cascata-fiscal-canonica.md](../../../adr/236-tributario-pj-cascata-fiscal-canonica.md) —
  frontmatter flippa `status: Proposto → Decidido`, `phase: A16`,
  `decided_at: "2026-05-21"`; tag `status/proposto → status/decidido`.

- [docs/sprint/A16/_README.md](../_README.md) — `sprint_status: current → done`
  (ambas as lanes fechadas: L1 ✅ em [apps#388](https://github.com/davidrobert/mathoms/pull/388),
  L2 ✅ em #395 + esta P6).

- [docs/sprint/A16/tracks/a16-adr236-tributario-pj-cascata.md](../tracks/a16-adr236-tributario-pj-cascata.md) —
  `status: ready → consumed`, `consumed_at: "2026-05-21"`,
  `progress_notes` atualizada com todas as 6 fases entregues.

- `dev/build_doc_index.py --inline` regenera `docs/_MOC/_generated/`
  (SPRINT_CURRENT, ADR_INDEX). Sprint A16 sai do current; ADR-236 sai
  de Proposto na listagem.

**Não-objetivos (fora de P6, intencional):**

- UI de captura de `BusinessProfile` no console interno frontend —
  diferida em P1 (deferred para F7F-Remote). Admin endpoint backend já
  cobre o workflow do operador via API direta.
- Migration v2 `category_template` com as 5 labels PJ — diferida em
  P2; labels são categoria-livre em `ClassifiedTransaction.categoria`.
  V2 quando UI/admin reconhecer as labels.
- Renderer alternativo do card / cache `workspace_tributario_snapshot`
  — FU [[ADR-236]] §"Follow-ups V2".

**Métricas esperadas (1ª semana pós-deploy):**

- `mathoms.tributario.cascata_rendered` count = total de requests que
  montam `bundle["tributario"]` (proxy de uso do relatório premium).
- Distribuição `regime` (workspaces ativos com BP preenchido vs.
  pendente) — sinal de adoção do onboarding tributário.
- `mathoms.tributario.profile_incomplete.missing_fields` — heatmap dos
  campos que os consultores deixam vazios; informa eventual UI captura
  V2.
- `mathoms.tributario.trigger_shown` count por `trigger_code` — quais
  decisões T1-T5 disparam em produção (calibração de thresholds).

**Próximo:** Sprint A17 (ADR-238 informes anuais avulsos + W6-L3 Wise).
Lane L2 cascata fiscal **encerrada**.
