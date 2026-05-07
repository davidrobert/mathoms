---
id: CHG-2026-05-06-FEAT-SCHEMAS
type: changelog-entry
date: "2026-05-06"
sprint: A11
adrs: ["[[ADR-166]]"]
summary: |
  feat(schemas): cenarios_conjuge formal em e5_analysis.schema (W1-T08 · 2026-05-06). - **feat(schemas): cenarios_conjuge formal em e5_analysis.schema (W1-T08 · 2026-05-06):** Fecha gap deixado por ADR-166 — `CenariosConjugeAnalyzer.to_legacy_dic
tags:
  - type/changelog-entry
  - sprint/a11
---


# feat(schemas): cenarios_conjuge formal em e5_analysis.schema (W1-T08 · 2026-05-06)

- **feat(schemas): cenarios_conjuge formal em e5_analysis.schema (W1-T08 · 2026-05-06):**
  Fecha gap deixado por ADR-166 — `CenariosConjugeAnalyzer.to_legacy_dict()`
  produz bloco top-level `cenarios_conjuge` mas o schema E5 não o
  declarava, então drift de payload passa silencioso em modo `warn` e
  bloqueia transição para `strict` (W6-T01).
  `config/schemas/e5_analysis.schema.json` agora declara `cenarios_conjuge`
  formal (`labels`, `aportes`, `prazos_if`, `anos_if`, `premissas`,
  `cenarios[*]` com `nome/aporte_mensal/prazo_if_anos/ano_if/resumo`
  obrigatórios) + `patternProperties` para chaves dinâmicas
  `idade_<titular>_if` e `idade_<titular>` (sem upper bound — sentinela
  legada `prazo=999` propaga para idade>120). Mesma onda também declara
  formalmente outros 17 blocos top-level que `build_e5_output` produz
  (`periodo_dados`, `data_analise`, `orcamento_prospectivo`,
  `reserva_emergencia`, `endividamento`, `previdencia_pgbl`,
  `pontos_fortes`, `pontos_urgentes`, `equilibrio_cerbasi`, `tarefas`,
  `tarefas_status`, `alertas`, `consumo_consciente`,
  `diagnostico_comportamental`, `programa_milhas`, `narrativas`,
  `irpf_kpis`, `passive_income`, `if_monte_carlo`) — apenas `type` por
  enquanto, sem properties internas, para manter o diff focado.
  Modo continua `warn` (default em `pipeline.json`); cutover `strict` é
  W6-T01. 6 testes em `tests/test_schema_validation.py` (positivo +
  negativo + paridade `build_e5_output` real). Resolve DE-006 (parcial).
