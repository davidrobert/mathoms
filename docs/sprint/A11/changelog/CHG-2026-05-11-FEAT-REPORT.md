---
id: CHG-2026-05-11-FEAT-REPORT
type: changelog-entry
date: "2026-05-11"
sprint: A11
lane: "[[TRACK-pgbl-card-diagnostico]]"
adrs:
  - "[[ADR-189]]"
summary: |
  feat(report): PGBL diagnóstico tipificado em 4 estados substitui métrica
  monovalor no card de Otimização Tributária (ADR-189). Card resolve copy +
  variante por `pgbl_status` (capacidade_disponivel/modelo_simplificado/
  no_teto/sem_renda_tributavel); `R$ 0,00` só no estado `no_teto`; disclaimer
  "não é recomendação" restrito ao estado positivo.
tags:
  - type/changelog-entry
  - sprint/a11
  - area/irpf
  - area/frontend
  - area/report
---

# feat(report): PGBL diagnóstico tipificado em 4 estados (ADR-189)

Track `pgbl-card-diagnostico` transforma o card `IrpfPgblCapacidadeCard`
de métrica monovalor ambígua (`R$ 0,00` com dupla causa: simplificado *ou*
no teto) em diagnóstico tipificado em 4 estados, cada um com copy e
variante específicas, preservando a posição "capacidade ≠ recomendação"
do ADR-157.

**Entregue:**

- `pipeline/domain/services/irpf_analyzer.py`: enum `PgblStatus` (4 valores)
  + `IRPFAnalyzer.pgbl_status(ano)` (determinístico, regra agregada
  multi-declarante) + `IRPFAnalyzer.pgbl_resumo(ano) -> PgblResumo` (aporte
  + teto). `pgbl_capacidade_dedutivel(ano)` permanece intacto (additive).
- `scripts/e5_analyze.py::_e5_kpis_from_analyzer`: serializa 3 campos novos
  (`pgbl_status`, `pgbl_aportado_brl`, `pgbl_teto_brl`) ao payload
  `irpf_kpis` — workspaces sem IRPF continuam ausentes (sem regressão).
- `frontend/src/types/irpf.ts`: `IrpfKpis` ganha `pgbl_status: PgblStatus`
  + aportado/teto string-decimal; narrow guard `isIrpfKpis` valida enum.
- `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx`:
  reescrito como switch sobre `kpis.pgbl_status` em 4 ramos, com copy
  literal congelada por G0 financial-planner em ADR-189 §4 / §6.1.
- `config/report_layout.yaml`: `pgbl_capacidade` muda `variant: warn → info`
  e `size: full → half` (card monovalor não precisa de hero).
- **Design system**: nova variante `info` adicionada (`design-tokens/
  tokens.json`, schema, codegen e CSS gerado) — token `--brand-info` já
  existia, faltava apenas a entrada em `card_variants`.
- Tests: 13 pytest unitários (`tests/test_irpf_analyzer_pgbl_status.py`)
  cobrindo 4 estados + edge cases (casal misto, aporte > teto, sem
  declarações, só isentos); 5 cenários Vitest DOM novos (4 estados +
  guard de pgbl_status inválido).

**Não-objetivos (anotados para backlog futuro):**

1. Threshold AUVP (alíquota efetiva ≥ 22,5%, horizonte ≥ 10a) para
   modular variante — exige ADR nova com proxy de horizonte.
2. Comparativo Simplificada vs Completa — exige cálculo de contrafactual
   da declaração completa.
3. Voltar cards "Dependentes Declarados" e "Dedutíveis Subutilizados" —
   exige `dependentes_count` + `dedutiveis_por_categoria` no analyzer.
4. Reconciliar dois cards PGBL (S7 `previdencia_pgbl` inferido vs
   S_IRPF_OTIMIZACAO declarado) — lane separada.
