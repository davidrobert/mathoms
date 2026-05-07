---
id: ADR-140
type: adr
title: "Goal IF schema v2 (renda passiva atual + IF meta líquida)"
status: Roadmap
date: "2026-04-27"
relates_to: ["[[ADR-073]]", "[[ADR-141]]", "[[ADR-142]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 140"]
tags:
  - area/money
  - area/persistence
  - methodology/auvp
  - methodology/perini
  - status/roadmap
  - type/adr
size_lines: 37
---

# ADR-140 — Goal IF schema v2 (renda passiva atual + IF meta líquida)

**Status:** Roadmap • **Data:** 2026-04-27 • **Implementação:** schema candidato em `config/schemas/goal.if.v2.schema.json`; backend, frontend e DB ainda emitem v1 — adoção exige lane dedicada.

**Contexto:** Auditoria multi-agente (rodada 1, item 5 do financial-planner; rodada 2, item B1 do senior-cto) identificou dois gaps no schema v1 do Goal IF:

1. **Premissa nominal vs real implícita.** `renda_passiva_mensal_brl` não declarava se é em valor presente (deflacionado) ou nominal futuro. Trinity assume retorno e retirada **reais**; produto opera em BRL de hoje. Sem campo explícito, planejadores externos (público B2B2C de [PRODUCT.md](PRODUCT.md)) preenchem manualmente e a UI pode capturar errado.

2. **Dupla contagem de renda passiva atual.** A fórmula `if_meta = renda × 12 / TRS` ignora a renda passiva já fluindo (aluguéis, dividendos, juros). Família com R$9k/mês de aluguel e meta de R$30k/mês de IF tem **gap real** de R$21k/mês (não R$30k). Schema v1 não modela isso.

**Decisão:** Criar `goal.if.v2.schema.json` (não substitui v1) com:

- `inputs.renda_passiva_atual_mensal_brl` (default 0)
- `derived.if_meta_bruta_brl` = patrimônio total que sustenta o alvo (didático)
- `derived.if_meta_liquida_brl` = `MAX(0, (renda_passiva_mensal − renda_passiva_atual) × 12 / (trs_pct/100))` (operacional — métrica usada em `score.progresso_if`)
- Description explicita "BRL de hoje (poder de compra atual)"
- Anti-dupla-contagem com `imoveis_no_if` documentada (ADR-142)

**Por que schema separado e não bump in-place:** evita breaking change. Backend (`goal_service.py`, `IFGoalDerived`, mapper, seeds, DB schemas) e frontend (`goals.ts`, `IFGoalForm`) operam em v1; bump in-place quebraria toda a base. Schema v2 fica como contrato disponível para a lane de migração.

**Roadmap de adoção:**

1. Adicionar coluna `meta_version` em `goals` table (já existe nos schemas Pydantic — checar se DB acompanha).
2. Migrar `IFGoalDerived` para emitir os 3 (`if_meta_brl`, `if_meta_bruta_brl`, `if_meta_liquida_brl`); deprecar `if_meta_brl` em commit subsequente.
3. UI de IF expõe os 4 campos novos (`renda_passiva_atual` em input; bruta/liquida lado a lado em hero; banner "já gera R$ X/mês").
4. `score.progresso_if` consome `if_meta_liquida_brl` (não `if_meta_brl`).
5. Migrator one-shot: `renda_passiva_atual_mensal_brl=0` em todos os goals existentes; `if_meta_liquida = if_meta_bruta` por construção.

**Consequências:**

- Goals existentes não mudam comportamento até migrator rodar (zero default preserva v1).
- Cálculo de progresso passa a refletir gap real após migração — relatórios pré-migração mostravam progresso subestimado para famílias com renda passiva atual ativa.
- Schema v1 fica como compat reverso até cleanup F-pós-A7.

**Relaciona-se a:** [ADR-073](#adr-073--goals-como-entidade-versionada-não-config-estático) (Goals no banco), [ADR-141](#adr-141--goal-alocação-alvo-schema-v2-7-classes-auvp), [ADR-142](#adr-142--toggle-imoveis_no_if-em-pipelinejson--invariante-anti-dupla-contagem). Detalhamento das fórmulas em [FORMULAS.md §IF](FORMULAS.md).
