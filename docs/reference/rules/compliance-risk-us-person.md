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

> **Hold normativo 2026-08-14 ([[ADR-387]]).** O calculator monolítico abaixo
> não está autorizado a produzir `computed`: mistura bases de FBAR, FATCA e
> Estate Tax NRA. A [[A40.l62]] o substitui por três checks person-scoped; até
> lá, exposição positiva ou incerta permanece `missing_data`.

**Conceito.** Triagem de três obrigações/exposições independentes, sempre por
pessoa e ano: FBAR, FATCA/Form 8938 e Estate Tax para nonresident not citizen.
O resultado indica necessidade de validação; não determina obrigação fiscal.

**Por quê.** Os três checks usam sujeitos, bases, datas e thresholds diferentes.
Colapsá-los em “ativo em USD” pode tanto ocultar uma obrigação potencial quanto
fabricar um alerta. A saída precisa registrar o rule-set vigente e recomendar
validação por profissional habilitado em Brasil/EUA.

**Doutrina canônica.** O calculator monolítico veio da
[ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3.
A [[ADR-387]] o retém e exige três contratos/rule-sets independentes, por
vigência. Referências: [FinCEN FBAR](https://www.fincen.gov/report-foreign-bank-and-financial-accounts),
[IRS Form 8938](https://www.irs.gov/businesses/corporations/do-i-need-to-file-form-8938-statement-of-specified-foreign-financial-assets) e
[IRS Estate Tax NRNC](https://www.irs.gov/businesses/small-businesses-self-employed/frequently-asked-questions-on-estate-taxes-for-nonresidents-not-citizens-of-the-united-states).

**Computabilidade (emendas 2026-08-13/14).** FBAR exige U.S. person, contas
financeiras fora dos EUA e máximo agregado anual; FATCA exige status,
residência/filing status e specified foreign financial assets nas bases
aplicáveis; Estate Tax NRA exige NRA e ativos US-situs. Moeda USD, renda
“exterior” e `has_us_assets` não substituem essas evidências. Cada check tem
status próprio; ausência produz `missing_data`, nunca `False` ([[ADR-387]]).

**Enforcer.**
- [`pipeline/domain/services/protection/compliance_us_person.py`](../../../pipeline/domain/services/protection/compliance_us_person.py) — `compliance_risk_us_person(USExposureInputs) -> list[ComplianceFlag]`. Cada flag carrega `RiskInferred(source_calculator="compliance_risk_us_person", category="compliance_us")`.
- Aggregate `family_members` ganhou coluna `us_tax_status: String(32)` (migration `d0e1f2a3b4c5_adr192_family_member_us_tax_status.py`) — codes válidos: `none | resident | former_resident_within_10y | greencard_expiring | citizen`. Adapter deriva `has_us_exposure` a partir desse campo.

**Disclaimer fiduciário.** “Triagem indicativa sob os dados e rule-sets
capturados em `<effective_date>`; não determina obrigação fiscal. Validar com
profissional tributário habilitado em Brasil/EUA.”

**Boundary legado sob hold.** O enforcer atual recebe um único
`us_tax_status`, `has_us_assets` e `us_assets_usd`; esse shape não pode produzir
`computed`. Seus códigos existentes são preservados somente para migração:

| Code | Descrição |
|---|---|
| `none` | Legado ambíguo; não distingue “não aplicável” de “não declarado” |
| `resident` | Código legado “residente fiscal”; exige revalidação no perfil V1 |
| `former_resident_within_10y` | Código legado de ex-residência; não prova obrigação atual |
| `greencard_expiring` | Código legado de green card; não prova filing status atual |
| `citizen` | Código legado de cidadania; exige bases separadas por check |

**Cobertura de teste legada.** [tests/pipeline/domain/services/protection/test_compliance_us_person.py](../../../tests/pipeline/domain/services/protection/test_compliance_us_person.py) cobre 11 perfis do calculator incorreto; os resultados não são aceite para a S9:
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

**Metodologias.** É matéria fiscal, não metodologia de planejamento. Rule-sets
versionados e fontes oficiais prevalecem sobre o comportamento legado.
