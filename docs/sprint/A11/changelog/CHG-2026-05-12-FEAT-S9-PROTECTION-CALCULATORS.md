---
id: CHG-2026-05-12-FEAT-S9-PROTECTION-CALCULATORS
type: changelog-entry
date: "2026-05-12"
sprint: A11
lane: "[[A11.w5]]"
adrs:
  - "[[ADR-192]]"
summary: |
  feat(domain): 4 calculators determinísticos protection + auto-inferência
  (ADR-192 §D3, S9-T03) — Cobertura ideal de vida, gap invalidez, ITCMD
  estimado e compliance US-person. Adapter popula bundle a partir de
  family_members + workspace; thresholds default no adapter como débito
  documentado para `fiscal_parameters` (ADR-135).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/domain
  - area/pipeline
  - area/backend
  - methodology/cerbasi
  - methodology/perini
---

# feat(domain): 4 calculators protection + auto-inferência (S9-T03)

Track `s9-riscos-expansion` — onda 2 (T03) entregue.

**Calculators determinísticos puros (ADR-097 D3 / ADR-111 stateless):**

- `life_insurance_coverage_ideal(LifeInsuranceInputs) → CoverageRecommendation`
  — Cerbasi (10× renda anual × fator deps 1.0/1.5/2.0) **max** Perini
  (PV anuidade até maioridade do dep mais novo, taxa real 3% default).
  Emite `RiskInferred("falta_seguro_vida_cobertura_insuficiente")` quando
  gap > 5% do ideal **e** > R$ 50k.
- `disability_coverage_gap(DisabilityInputs) → CoverageGap` — Cerbasi:
  share renda ativa > 40% **e** cobertura < 60% renda → emite
  `RiskInferred("invalidez_subcobertura")` com impacto anualizado.
- `itcmd_estimated(ITCMDInputs) → ITCMDEstimate` — tabela de alíquotas
  por UF **injetada** (não hardcoded) via parâmetro; emite
  `RiskInferred("sucessorio_itcmd_estimado")` quando ITCMD > R$ 10k.
- `compliance_risk_us_person(USExposureInputs) → list[ComplianceFlag]` —
  gate explícito por `us_tax_status` ∈ `{resident, former_resident_within_10y,
  greencard_expiring, citizen}` OU `has_us_assets AND us_assets > FBAR`.
  Emite FBAR, FATCA e Estate Tax NRA conforme regra. **Não dispara** para
  cliente brasileiro padrão (corrige bug histórico do S9 antigo).

**Whitelist `RiskInferred`** (ADR-192 §D3): apenas estes 4 `source_calculator`
podem emitir; `build_risk_inferred` levanta `ValueError` para qualquer outro
(holding/D&O/fideicomisso ficam fora). Teste `test_risk_inferred_whitelist`
afirma o invariante.

**Disclaimer fiduciário canônico** em todo `rationale`:

> "Estimativa metodológica baseada em <Cerbasi/Perini>; não constitui
> recomendação fiduciária. Consultar corretor habilitado pela Susep e
> planejador CFP®. Dados fiscais válidos para `<effective_date>`."

**Adapter populator** (`backend/app/services/protection_bundle_adapter.py`):

- Substituiu `_empty_bundle` por `_populate_bundle` que monta value
  objects a partir de `family_members` (idades, `us_tax_status`),
  `Workspace.business_profile_json` (UF do titular, `us_exposure_explicit`)
  e cobertura ativa por categoria. Chama os 4 calculators; agrega
  resultados em `gap_analysis` / `recommendations` / `auto_inferred_risks`
  / `methodology_thresholds` / `has_us_exposure`.
- `_PROTECTION_BUNDLE_VERSION` bumpado para `2`.
- Pipeline boundary preservado (ADR-101 R5): adapter no app layer
  injeta tudo; calculators em `pipeline/domain/services/protection/`
  importam apenas stdlib + `pipeline.domain.*`.
- Thresholds default (`_ITCMD_ALIQUOTAS_DEFAULT_PCT` cobrindo 27 UFs
  + DF; `_US_THRESHOLDS_DEFAULT` com FBAR $10k / FATCA $50k / Estate
  Tax NRA $60k) documentados como débito de migração para
  `fiscal_parameters.itcmd_aliquota_por_uf` e `.us_thresholds_usd`
  (ADR-135 follow-up).

**Schema/DB:**

- Alembic migration `d0e1f2a3b4c5_adr192_family_member_us_tax_status.py`
  adiciona `family_members.us_tax_status: String(32)` nullable.
- Códigos aceitos (enforce app-layer): `none` (default), `resident`,
  `former_resident_within_10y`, `greencard_expiring`, `citizen`.

**Domain Rule notes** publicadas em `docs/reference/rules/`:

- `life-insurance-coverage.md`
- `disability-coverage-gap.md`
- `itcmd-estimated.md`
- `compliance-risk-us-person.md`

`docs/reference/ARCHITECTURE.md §4.1 Domain glossary` ganhou 4 entradas
apontando para enforcer + ADR.

**Testes:**

- 50 specs novos em `tests/pipeline/domain/services/protection/` (12
  life + 9 disability + 9 ITCMD + 11 US compliance + 4 whitelist).
- 3 specs novos em `backend/tests/test_protection_aggregate.py` exercitando
  o populator end-to-end com `family_members.us_tax_status`.
- Anti-regressão: workspace vazio continua devolvendo
  `gap_analysis={}`, `auto_inferred_risks=[]`, `has_us_exposure=False`
  (existing `test_bundle_skeleton_returns_empty_lists` ajustado para
  `_adapter_version == 2`).

**Decisões de orquestrador** (gate triplo `financial-planner` /
`data-engineer` / `product-designer` não pôde ser invocado neste
sub-fluxo; orquestrador com autoridade senior-cto delegada tomou as
decisões abaixo, registradas para auditoria):

- Disclaimer canônico aplicado em todos os outputs (`rationale`).
- Fator dependência Cerbasi 1.0 / 1.5 / 2.0 (conservador; documentado).
- Perini com PV anuidade discount real 3% default (injectable).
- Material gates: vida (gap > 5% E > R$ 50k), invalidez (gap > R$ 1k/mês),
  ITCMD (> R$ 10k). Evita poluir `auto_inferred_risks` com ruído.
- Pipeline boundary preservado; calculators 100% puros, sem `@lru_cache`.
- Renda/patrimônio não preenchidos: calculators recebem 0 e o bundle
  fica em empty-state seguro (compatível com workspace recém-criado).

**Goldens E5** marcados para reset em **T06** (paridade narrativa S9
+ bundle protection); este PR **não atualiza goldens**. Justificativa
para holdar: shape do `bubble_riscos.context/conclusion` ainda não muda
em T03 — calculators povoam bundle paralelo (`ProtectionBundle`), narrador
S9 ainda lê pela via legada até T04 (codegen layout + cards). T06 é o
reset único conforme R5 do track.

**Próximos passos:** T04 (codegen layout + 5 cards UI), T05 (UI cadastro
de apólice), T06 (reset goldens E5).
