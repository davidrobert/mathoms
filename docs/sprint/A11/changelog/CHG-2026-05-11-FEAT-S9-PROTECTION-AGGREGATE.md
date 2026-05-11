---
id: CHG-2026-05-11-FEAT-S9-PROTECTION-AGGREGATE
type: changelog-entry
date: "2026-05-11"
sprint: A11
lane: "[[A11.w5]]"
adrs:
  - "[[ADR-192]]"
prs: [212]
commits: ["2ec4254"]
summary: |
  feat(backend): Protection aggregate + ProtectionBundle skeleton (ADR-192
  Decidida); S9-T01 + S9-T02 (Sprint A11.W5 · s9-riscos-expansion track).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/backend
  - area/domain
  - area/pipeline
  - area/multitenancy
  - methodology/cerbasi
  - methodology/perini
---

# feat(backend): `Protection` aggregate + `ProtectionBundle` (S9-T01 + S9-T02)

Track `s9-riscos-expansion` — ondas 1+2 entregues (T01 hotfix + T02
skeleton). ADR-192 sai de `Proposto` para `Decidido (Sprint A11.W5)` no
PR de T02.

**S9-T01 — Hotfix narrativa** ([#212](https://github.com/davidrobert/mathoms/pull/212), commit `2ec4254`):

- Guard early-return em `_narrate_riscos_decisoes` para `_riscos_top3 == []` (`pipeline/domain/services/narrativas/charts_narrator.py`).
- Remove string hardcoded "CPA expatriado + seguro term R$ X-Y M"; compliance USA só aparece com `payload.has_us_exposure`.
- Defaults de `seguro_vida_minimo/maximo` para `None` → renderiza "a definir".
- `S9RiscosSection` lê `data_state="empty"` e renderiza `<EmptyStateCard/>` com CTA "Cadastrar riscos no Console".
- Testes regressão: `test_riscos_decisoes_empty_list` + `test_riscos_default_no_us_assumption`.

**S9-T02 — Protection aggregate + bundle skeleton** (este PR):

- Aggregate `Protection` workspace-scoped: 11 colunas + 3 índices (incluindo `(workspace_id, ends_at)` para job futuro de vencimento).
- `category`/`status`/`coverage_type` como `String(N) + frozenset` (coerência com `Risk`/`Decision`).
- Alembic migration `c9d0e1f2a3b4` cria `protections` + adiciona `risks.mitigation_protection_ids JSON`.
- 6 use cases (`create_protection`, `get_protection`, `list_protections`, `update_protection`, `cancel_protection`, `link_to_risk`+`unlink_from_risk`).
- 8 endpoints HTTP + `GET /protection-bundle` (skeleton para o renderer S9; calculators populam em T03).
- `ProtectionBundle` TypedDict em `pipeline/domain/protection_bundle.py` (sem SQLAlchemy).
- Adapter `_project_protection_bundle_sync/async` + `build_protection_bundle*` em `pipeline_adapter.py`.
- PII: `policy_ref` em Fernet vault (ADR-109); logs ADR-110 redatam `policy_ref`, `coverage_brl`, `premium_monthly_brl`, `holder_name`; INFO emite `coverage_bucket: int (0-5)`.
- `insurer` allowlist regex (ASCII+acentos PT-BR, S/A aceito; URLs/paths rejeitados — defesa SSRF).
- Cancelamento via `status="Cancelada"` (soft delete); hard delete reservado para `/admin/lgpd-request` (T-futuro).
- 26 specs em `backend/tests/test_protection_aggregate.py` (26/26 passing).
- OpenAPI snapshot + DB_SCHEMA_REFERENCE.md regenerados.

**Gate triplo de revisão pré-codigo** (`data-engineer` + `financial-planner` + `sre-devops`)
gerou 8 ressalvas — todas aplicadas neste PR. Ver ADR-192 §"Atualizações
pós-revisão". Itens parqueados para T-futuro com justificativa: rate-limit
DB-backed + cache Redis no bundle, KEK rotation no runbook.

**Mudança de escopo em T03** (financial-planner review): `emergency_reserve_target`
removido do módulo `protection/` — é meta de liquidez, domínio `Goal`
(ADR-180). T03 fica com **4 calculators** (life, disability, ITCMD,
US-person), todos lendo thresholds de `fiscal_parameters` (ADR-135) por
`effective_date`.

**Próximos passos:** T03 (calculators), T04 (codegen layout + 5 cards UI),
T05 (UI cadastro), T06 (reset goldens E5).
