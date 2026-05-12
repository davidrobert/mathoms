---
id: CHG-2026-05-12-FEAT-IRPF-OTIMIZACAO-CARDS-REVIVAL
type: changelog-entry
date: "2026-05-12"
sprint: A12
lane: "[[TRACK-irpf-otimizacao-cards-revival]]"
adrs:
  - "[[ADR-194]]"
prs: [223]
commits: ["fdb2efc"]
summary: |
  feat(report): reativa cards Dependentes Declarados + Dedutíveis
  Aplicados na seção S_IRPF_OTIMIZACAO com números reais via
  IRPFAnalyzer — ADR-194 Decidida (A12).
tags:
  - type/changelog-entry
  - sprint/a12
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# feat(report): reativação de cards Dependentes + Dedutíveis em S_IRPF_OTIMIZACAO

Reativa 2 cards da seção `S_IRPF_OTIMIZACAO` do relatório Premium
(removidos em 2026-05 por serem prose-only). Agora consomem 2 KPIs novos
de `IRPFAnalyzer` que agregam dados já extraídos por E1.6
([[ADR-157]]). [[ADR-194]] **Decidida** no merge (PR #223).

**Co-design 2026-05-12** — `data-engineer` + `financial-planner` +
`product-designer` em paralelo (1 mensagem, 3 vereditos):

- **G2 (data-engineer):** contrato Opção B (`{count, por_relacao}`) +
  Opção B (`{utilizado_brl, teto_brl, teto_aplicado}` por categoria);
  4 categorias publicadas; PGBL excluído por anti-duplicação (já tem
  card próprio [[ADR-189]]); pensão consolidada (3 variantes RFB → 1
  chave); sparse omit zerados; ADR Proposto obrigatória.
- **G0 (financial-planner):** copy literal congelada em [[ADR-194]]
  §6.1/§6.2; card "Dependentes" `neutral half` factual sem disclaimer;
  card "Dedutíveis" rebatizado para "Aplicados por Categoria"
  (não-prescritivo); variante condicional `info`/`neutral` por
  subutilização; disclaimer-rodapé único; "no teto" sem `warn`.
- **G4 (product-designer):** hierarquia PGBL + Dependentes na linha 1
  (half/half) + Dedutíveis (full) na linha 2; lista `<dl>` com
  `role="progressbar"` (não tabela); padrão S3.

**Entregue:**

- **Pipeline / backend:**
  - `IRPFAnalyzer.dependentes_count(ano) -> {count, por_relacao}`
    em [pipeline/domain/services/irpf_analyzer.py](../../../pipeline/domain/services/irpf_analyzer.py).
  - `IRPFAnalyzer.dedutiveis_aplicados(ano) -> dict[str, dict]` sparse,
    4 categorias (saúde, educação, pensão alimentícia consolidada,
    previdência oficial). PGBL excluído.
  - `EDUCACAO_TETO_PER_PESSOA = Decimal("3561.50")` hardcoded; teto
    agregado = `(dependentes + 1) × teto unitário`. Débito anotado
    em [[ADR-194]] §D5: migrar para `fiscal_parameters` ([[ADR-135]])
    quando RFB atualizar.
  - `scripts/e5_analyze.py::_e5_kpis_from_analyzer` emite chaves novas
    `dependentes` + `dedutiveis_aplicados` (additive; workspaces sem
    IRPF continuam ausentes). Helpers `_e5_kpis_basicos`/`_e5_kpis_pgbl`
    extraídos para respeitar baseline P1.
- **Frontend:**
  - `frontend/src/types/irpf.ts`: tipos strict `DependentesKpi` +
    `DedutivelLinha` + `DedutivelCategoria`; guard `isIrpfKpis`
    decomposto em 3 helpers para respeitar baseline T3.
  - `IrpfDependentesCard.tsx` — factual, `neutral` half, copy
    [[ADR-194]] §6.1 com singular/plural e ordem fixa de relações RFB.
  - `IrpfDedutiveisAplicadosCard.tsx` — `<dl>` + `<progress>` com
    `aria-label`, variante `info` se há subutilização else `neutral`,
    disclaimer-rodapé único, copy [[ADR-194]] §6.2.
  - `IrpfOtimizacaoSection.tsx` — guards `shouldRenderDependentes`
    (count > 0) + `shouldRenderDedutiveis` (≥ 1 categoria publicável)
    para degradação graciosa.
- **Layout:**
  - `config/report_layout.yaml` — 2 cards reativados (`half` +
    `full`); comentário de bloco atualizado com hierarquia G4 +
    referências [[ADR-189]]/[[ADR-194]].
  - Codegen sincronizado: `frontend/src/generated/report-layout.ts` +
    `backend/app/generated/report_layout.py`.

**Testes:**

- Pytest `tests/test_irpf_analyzer_dependentes_dedutiveis.py`: 16
  cenários determinísticos (zero/empty, múltiplas relações, casal,
  teto agregado por dependentes, consolidação pensão, PGBL excluído,
  categorias não-acionáveis excluídas, propagação `teto_aplicado`,
  rounding Decimal sem float drift).
- Regressão `tests/test_irpf_analyzer_pgbl_status.py` +
  `test_irpf_full_schema_unit.py` + `test_irpf_analyzer_bucket_capital.py`
  + `test_e5_golden_execution.py`: **61/61 verde** ([[ADR-189]] não
  regride).
- Vitest `frontend/tests/components/IrpfSections.test.tsx`: 20
  cenários novos (presence/absence/variantes/chips por status/sparse/
  degradação count==0).
- Suíte frontend completa: **907/908 verde** (1 skipped pré-existente).
- Code style baseline: 0 regressão.

**Não-objetivos** (ver [[ADR-194]] §5):

- Lookup de tetos via `fiscal_parameters` table.
- Threshold AUVP/Cerbasi para modular variantes.
- Cruzar com `family_members` para inferir "dependentes elegíveis
  faltando".
- Comparativo Simplificada × Completa (lane separada).
