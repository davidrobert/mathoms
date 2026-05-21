---
id: CHG-2026-05-21-FEAT-ADR-236-P1-BUSINESS-PROFILE
type: changelog-entry
date: "2026-05-21"
sprint: A16
lane: "[[TRACK-a16-adr236-tributario-pj-cascata]]"
adrs: ["[[ADR-236]]"]
summary: |
  feat(adr-236 P1): BusinessProfile expandido com 4 campos A16 + admin
  endpoint /admin/workspaces/{id}/business-profile (Sprint A16 L2 P1 —
  ADR-236 fase 1 de 6).
tags:
  - type/changelog-entry
  - sprint/a16
  - area/methodology
  - area/backend
  - area/persistence
  - area/ops
---

# feat(adr-236 P1): BusinessProfile expandido + admin endpoint (Sprint A16 L2 P1)

P1 de 6 fases da L2 (`tributario-pj-cascata`) — entrega o modelo de
domínio que P2/P3 vão consumir. [[ADR-236]] permanece `Proposto` até P6
fechar (cutover + telemetria + flip).

**Entregue:**

- Schema Pydantic em `backend/app/schemas/business_profile.py` ganha 4
  chaves novas declaradas-pelo-consultor (princípio "derivado ≫ declarado"
  da [[ADR-236]] §D2):
  - `anexo_simples: Literal["III", "V"] | None` — relevante quando
    `regime=simples` (fator-R).
  - `iss_aliquota_pct: float | None` — 2–5% conforme Lei Complementar
    116/2003.
  - `cnae_principal: str | None` — formato `NNNN-N/NN` (max_length=10).
  - `tipo_declaracao_ir: Literal["completa", "simplificada"] | None` —
    simplificada anula PGBL.
- Demais inputs da cascata fiscal (pró-labore, lucros distribuídos,
  folha, DAS, ISS, receita PJ, renda tributável PF) **continuam fora**
  de `BusinessProfile` — derivam de E3/E4/E1.6 (entrega em P2/P3).
- Alembic `adr236bizprofile1_business_profile_expanded.py` — revision
  no-op de audit trail (`business_profile_json` é JSON livre; enforcement
  é Pydantic-side). Up/down reversíveis.
- Endpoint cliente PATCH/GET `/workspaces/{id}/business-profile` (A10.7)
  auto-extende sem mudança de router — usa `BusinessProfile` Pydantic.
- Admin endpoint novo `/admin/workspaces/{id}/business-profile` (GET +
  PATCH) com `require_internal_operator` para o consultor preencher
  durante onboarding sem ser membro do workspace.
  Camada de serviço `update_workspace_business_profile.py` audita via
  `append_audit(action="workspace.update_business_profile")`.
- OpenAPI snapshot regenerado (1 schema BusinessProfile com 4 props
  novas + 2 paths admin novos).
- Tests:
  - `backend/tests/test_business_profile.py` — 27 casos (12 novos
    cobrindo Literal/range de cada campo A16 + round-trip combinado).
  - `backend/tests/api/admin/test_workspaces.py` — 9 casos (GET default,
    GET 404, PATCH full A16 com audit, PATCH replace, PATCH 404, rejeições,
    401 sem cookie ops_session).

**Não-objetivos (escopo de fase):**

- Classifier E4 (5 labels novas `pro_labore`, `lucros_distribuidos`,
  `das_simples`, `folha_pj`, `iss`) — vem em **P2**.
- Calculator canônico + 4 goldens — vem em **P3**.
- Adapter `bundle["tributario"]` + narrator reescrito — vem em **P4**.
- `<CascataFiscalCard/>` UI + co-design `product-designer` — vem em **P5**.
- Telemetria estruturada + flip ADR — vem em **P6**.

**Próximo:** P2 — derivação E3/E4/E1.6 (~2d eng) em branch
`agent/a16-adr236-tributario-pj-cascata-P2/*`.
