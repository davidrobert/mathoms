---
id: RULE-itcmd-estimated
type: domain-rule
concept: "Cenário indicativo de liquidez para ITCMD por pessoa e transmissão"
canonical_adr: "[[ADR-192]]"
enforcer_modules:
  - pipeline/domain/services/protection/itcmd_estimator.py
tags:
  - type/domain-rule
  - area/domain
---

# RULE — ITCMD estimado

> **Hold normativo 2026-08-14 ([[ADR-387]]).** `patrimônio bruto familiar ×
> alíquota de uma UF` não pode ser publicado como imposto devido. A regra só roda
> por cenário de falecimento com titularidade/quinhão, meação, natureza/situs do
> direito, UF/domicílio e rule-set vigente; antes disso, `missing_data`.

**Conceito.** Cenário indicativo de ITCMD por pessoa e transmissão, construído
sobre a base transmissível e o rule-set da jurisdição competente na data-base.
Não representa lançamento, obrigação ou imposto devido.

**Por quê.** Uma transmissão pode gerar necessidade de liquidez e incerteza
fiscal. O produto deve sinalizar a ordem de grandeza apenas quando titularidade,
meação, quinhão, natureza/localização do direito, competência e vigência forem
conhecidos, sempre para validação jurídica e contábil.

**Doutrina canônica.** O calculator linear histórico veio da
[ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3.
A [[ADR-387]] o retém até existir cenário person-scoped e `fiscal_rule_set`
versionado; tabela Markdown ou fallback local não é fonte fiscal. Referências de
competência: [CF art. 155](https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm)
e [LC 227/2026](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp227.htm).

**Computabilidade (emendas 2026-08-13/14).** O cálculo exige cenário por pessoa,
base transmissível com titularidade/meação e classificação dos direitos, UF
competente e rule-set fiscal vigente. Falta ou ambiguidade em qualquer item
produz `missing_data`; não há fallback SP nem tabela fiscal hardcoded. O
calculator linear abaixo é histórico e só pode sustentar cenário bruto
explicitamente rotulado, não obrigação tributária ([[ADR-387]]).

**Enforcer.**
- [`pipeline/domain/services/protection/itcmd_estimator.py`](../../../pipeline/domain/services/protection/itcmd_estimator.py) — `itcmd_estimated(ITCMDInputs) -> ITCMDEstimate`. UF case-insensitive (normaliza para upper); UF não-mapeada degrada graciosamente para 0 com warning textual no rationale. Emite `RiskInferred("sucessorio_itcmd_estimado")` quando ITCMD > R$ 10k.
- Populator app-layer: [`backend/app/services/protection_bundle_populator.py`](../../../backend/app/services/protection_bundle_populator.py) injeta `_ITCMD_ALIQUOTAS_DEFAULT_PCT` (26 estados + DF — 27 UFs) na vigência atual.

Esses dois comportamentos são legado incompatível: zero por UF ausente e tabela
local ficam retidos pela [[A40.l61]]/[[ADR-387]] e devem ser removidos no PR1 da
[[A40.l62]].

**Disclaimer fiduciário.** “Cenário indicativo sob os dados e a legislação
capturados em `<effective_date>`; não é cálculo definitivo nem orientação
jurídico-tributária. Validar com advogado e contador habilitados.”

**Fórmula legada sob hold.** Não pode ser rotulada como imposto devido nem
alimentar a S9; permanece documentada apenas para explicar o enforcer existente.

```
itcmd_brl_cents = patrimônio_bruto_brl_cents × aliquota_pct[UF] / 100

dispara_risk    = itcmd_brl_cents > R$ 10k   (impacto material para
                                              motivar planejamento sucessório)
```

Não existe tabela default canônica. A [[A40.l62]] só poderá habilitar um cenário
quando selecionar exatamente um rule-set revisado, vigente e com fonte.

**Cobertura de teste legada.** [tests/pipeline/domain/services/protection/test_itcmd_estimator.py](../../../tests/pipeline/domain/services/protection/test_itcmd_estimator.py) cobre 9 perfis do calculator linear; não satisfaz o novo contrato:
- solteiro SP patrimônio zero,
- casado MG 2M (5%),
- expatriado RJ 5M (8%),
- UF desconhecida (degrada para 0),
- UF lowercase (normaliza),
- ITCMD imaterial (< R$ 10k),
- disclaimer presente,
- idempotência,
- patrimônio negativo (zera).

**Metodologias.** É matéria fiscal, não uma fórmula de planejamento financeiro.
A regra versionada e sua fonte prevalecem sobre qualquer heurística do produto.
