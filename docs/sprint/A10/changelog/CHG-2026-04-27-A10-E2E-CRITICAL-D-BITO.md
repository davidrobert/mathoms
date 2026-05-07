---
id: CHG-2026-04-27-A10-E2E-CRITICAL-D-BITO
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["b47dd47"]
summary: |
  E2E `@critical` débito ✅ resolvido (2026-04-27). - **E2E `@critical` débito ✅ resolvido (2026-04-27):** Lane separada lançada em paralelo (`a86a806e8da6d60f1`) foi cancelada após Lane 4+2 (`b47dd47`) descobrir
tags:
  - type/changelog-entry
  - sprint/a10
---


# E2E `@critical` débito ✅ resolvido (2026-04-27)

- **E2E `@critical` débito ✅ resolvido (2026-04-27):** Lane separada lançada em paralelo (`a86a806e8da6d60f1`) foi cancelada após Lane 4+2 (`b47dd47`) descobrir e fixar o **mesmo root cause**: `useConsumoPontuais.toState()` shape coercion + `mock-report.ts` rota `/reports/consumo-pontuais`. Os 19 specs `@critical` que falhavam com `Cannot read properties of undefined 'length'` voltam ao verde após `b47dd47`; spec `snapshot-changelog.@critical.spec.ts` (marcado `test.skip` em v2.8 por causa desse bug) pode ter `skip` removido em lane futura quando alguém validar.
