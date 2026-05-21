---
id: CHG-2026-05-20-FEAT-ADR-235-NU-PROPRIETARIO
type: changelog-entry
date: "2026-05-20"
sprint: A16
lane: "[[TRACK-a16-adr235-nu-proprietario-flip]]"
adrs: ["[[ADR-235]]"]
summary: |
  feat(adr-235): adiciona classification `nu_proprietario` ao enum —
  nu-propriedade com usufruto vitalício de terceiro (ADR-235 Decidido,
  Sprint A16 L1).
tags:
  - type/changelog-entry
  - sprint/a16
  - area/methodology
  - area/db
  - area/backend
  - area/pipeline
  - area/frontend
---

# feat(adr-235): classification nu_proprietario (Sprint A16 L1)

L1 da Sprint A16 flippa [[ADR-235]] (Proposto → Decidido) e entrega o
valor `nu_proprietario` cross-stack para cobrir imóvel em nu-propriedade
com usufruto vitalício de terceiro (caso real workspace dogfood
2026-05-20).

**Semântica:** ativo no patrimônio do cliente, com ônus civil (usufruto
vitalício de terceiro), zero fluxo hoje, ilíquido por contrato civil até
consolidação plena no falecimento do usufrutuário. Comporta-se como
`uso_pessoal` nos filtros computacionais (não-gerador, fora de cap rate,
fora de `investivel_efetivo`), mas é **entidade semântica distinta** para
relatório, parecer LLM (E6) e diagnóstico de liquidez.

**Entregue:**

- Migration `adr235nupropriet1` — drop+recreate CHECK em
  `workspace_property_overrides.classification`; pre-down guard impede
  rollback se houver rows com `nu_proprietario`.
- Backend: `CLASSIFICATION_NU_PROPRIETARIO` em `models/property_identity.py`
  + re-export em `models/__init__.py`; CheckConstraint inline estendida.
- Pipeline: `patrimonio_imovel_classifier.py` exporta constante; **não**
  entra em `_CLASSIFICATIONS_GERADORAS` (paridade `uso_pessoal`).
  `real_estate_metrics.py` estende `ClassificationLiteral`;
  `INVESTMENT_CLASSIFICATIONS` permanece sem `nu_proprietario` (cap rate
  indefinido).
- Frontend: `Classification` union estendido em `properties.ts`;
  `ResidenciaSection.tsx` ganha opção "Nu-propriedade (usufruto
  vitalício)" + tooltip explicando consolidação futura.
- Parecer E6: prompt em `config/prompts/parecer_planejador.yaml`
  recebe bullet instruindo o LLM a NÃO recomendar venda como solução de
  liquidez (juridicamente travado até consolidação). Manifest bumpado
  para 1.3.
- CI gate `dev/check_classification_exhaustive.py` + auto-tests:
  detecta `switch (classification)` / `match classification:` sem branch
  default (TS/Python), prevenindo regressões silenciosas pelo
  schema-evolution risk de [[ADR-188]].
- ADRs adjacentes atualizadas no mesmo PR: [[ADR-215]] §1 estende enum,
  [[ADR-142]] invariante explícito (nu_proprietario nunca em
  `investivel_efetivo`), [[ADR-145]] cat_2 não-gerador, [[ADR-216]] fora
  do denominador de cap rate.
- Testes regressivos: `tests/unit/pipeline/test_split_imoveis_with_overrides.py`,
  `tests/test_real_estate_metrics.py`,
  `tests/unit/pipeline/test_patrimonio_calculator.py` (rename
  `test_investivel_efetivo_exclui_uso_pessoal_e_especulacao_sempre` →
  `test_investivel_efetivo_exclui_nao_geradores_sempre`),
  `backend/tests/test_property_identity_model.py`.

**Não-objetivos preservados:** `expected_extinction_year`, captura de
`valor_mercado_consolidado`, sub-bucket "Patrimônio ilíquido condicional"
em [[ADR-145]] — FUs documentados na ADR.

**Frequência esperada:** 5–15% do ICP wealth-tech BR (famílias com
planejamento sucessório ativo).
