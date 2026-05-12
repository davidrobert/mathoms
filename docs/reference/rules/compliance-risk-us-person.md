---
id: RULE-compliance-risk-us-person
type: domain-rule
concept: "Compliance US-person (FBAR / FATCA / Estate Tax NRA)"
canonical_adr: "[[ADR-192]]"
enforcer_modules:
  - pipeline/domain/services/protection/compliance_us_person.py
tags:
  - type/domain-rule
  - area/domain
---

# RULE — Compliance US-person

**Conceito.** Flags de compliance fiscal americana — emitidas **apenas** quando há sinal explícito de exposição aos EUA. Quatro perfis disparam: `resident`, `former_resident_within_10y`, `greencard_expiring`, `citizen`. Cliente brasileiro sem exposição americana **não** vê nenhuma flag — corrige o bug histórico de "CPA expatriado hardcoded" que vazava no S9 antigo.

**Por quê.** O IRS rastreia rendas globais de **US-persons** independentemente de residência atual; ativos estrangeiros disparam obrigações de reporte específicas (Form 8938 FATCA, FinCEN Form 114 FBAR). Não-US-person com ativos US-situs acima de $60k federal carrega exposição a Estate Tax federal (40%) na transmissão causa mortis. Detectar essas obrigações tarde resulta em multas pesadas (FBAR up to $10k/violação non-willful, willful $100k+).

**Doutrina canônica.** Decidida em [ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3 (Sprint A11.W5, S9-T03). Calculator puro (ADR-097 D3 / ADR-111). Thresholds vêm de `USPersonThresholds` **injetado** pelo adapter — ADR-192 §"Atualizações pós-revisão" exige `fiscal_parameters` (ADR-135) por `effective_date`. Default no adapter (`_US_THRESHOLDS_DEFAULT`) reflete a tabela vigente IRS 2026 (FBAR $10k · FATCA single $50k / joint $100k · Estate Tax NRA $60k) — débito documentado para migração à coluna `fiscal_parameters.us_thresholds_usd`.

**Enforcer.**
- [`pipeline/domain/services/protection/compliance_us_person.py`](../../../pipeline/domain/services/protection/compliance_us_person.py) — `compliance_risk_us_person(USExposureInputs) -> list[ComplianceFlag]`. Cada flag carrega `RiskInferred(source_calculator="compliance_risk_us_person", category="compliance_us")`.
- Aggregate `family_members` ganhou coluna `us_tax_status: String(32)` (migration `d0e1f2a3b4c5_adr192_family_member_us_tax_status.py`) — codes válidos: `none | resident | former_resident_within_10y | greencard_expiring | citizen`. Adapter deriva `has_us_exposure` a partir desse campo.

**Disclaimer fiduciário.** "Estimativa metodológica baseada em FBAR/FATCA/Estate Tax (fiscal_parameters); não constitui recomendação fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. Dados fiscais válidos para `<effective_date>`."

**Regra de disparo.**

```
us_person = us_tax_status ∈ {resident, former_resident_within_10y,
                              greencard_expiring, citizen}

# Gate: nenhuma flag se cliente sem exposição
emit_flags = us_person OR (has_us_assets AND us_assets_usd > FBAR_threshold)

# FBAR (FinCEN Form 114): qualquer US-person OU non-resident com ativos > threshold
emit_FBAR  = us_person OR us_assets_usd > FBAR_threshold

# FATCA (Form 8938): apenas US-person com ativos > threshold
emit_FATCA = us_person AND us_assets_usd > FATCA_single_threshold

# Estate Tax NRA: apenas não-US-person com ativos US-situs > $60k federal
emit_ESTATE_NRA = us_tax_status == "none"
                  AND has_us_assets
                  AND us_assets_usd > Estate_Tax_NRA_threshold
```

**Códigos `us_tax_status` aceitos.**

| Code | Descrição |
|---|---|
| `none` | Sem exposição (default; cliente brasileiro padrão) |
| `resident` | US tax resident — Form 1040 anual + Form 8938 se ativos > threshold |
| `former_resident_within_10y` | Expatriação recente; ainda tributável residualmente |
| `greencard_expiring` | Green card em vias de perda — janela de planejamento |
| `citizen` | Cidadão americano — tributado worldwide for life |

**Casos de teste.** [tests/pipeline/domain/services/protection/test_compliance_us_person.py](../../../tests/pipeline/domain/services/protection/test_compliance_us_person.py) cobre 11 perfis:
- brasileiro sem exposição (zero flags — anti-regressão ADR-192 §contexto),
- brasileiro com ativos USD < FBAR,
- brasileiro com ativos USD > FBAR (só FBAR),
- brasileiro com ativos USD > 60k (FBAR + Estate Tax NRA),
- US citizen sem ativos (só FBAR),
- expatriado recente com FATCA,
- greencard expirando,
- todas flags com disclaimer + whitelist,
- status inválido (ValueError),
- idempotência,
- category="compliance_us" em todos os RiskInferred.

**Metodologias.** Não há doutrina metodológica disputada — regra reflete legislação IRS/Treasury. Calculator integra a checagem com fluxo Mathoms.
