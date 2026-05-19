---
id: RULE-imoveis-no-if
type: domain-rule
concept: "Toggle imoveis_no_if (anti-dupla-contagem)"
methodology: [perini, auvp]
canonical_adr: "[[ADR-142]]"
enforcer_modules:
  - pipeline/domain/services/patrimonio_calculator.py
  - pipeline/domain/services/passive_income_calculator.py
formula_ref: "FORMULAS.md#patrimônio"
tags:
  - type/domain-rule
  - methodology/perini
  - methodology/auvp
---

# RULE — Toggle `imoveis_no_if` (anti-dupla-contagem)

**Conceito.** `workspace.imoveis_no_if: bool` (per-workspace, ADR-222) decide se imóveis investimento (cat_2) entram em `investivel_efetivo`. Invariante de exclusão mútua: se entram no numerador, **não podem** entrar no denominador como aluguéis em `renda_passiva_atual_mensal_brl` (e vice-versa).

**Por quê.** Sem invariante, imóveis aparecem **duas vezes** — somam no numerador (cat_2 em investível efetivo) **e** descontam no denominador (renda passiva atual reduz `if_meta_liquida`). Resultado: `progresso_if` superestimado em famílias com aluguéis. O produto não calcula yield líquido por imóvel (depende de carnê-leão real, vacância, manutenção), então o toggle é decisão consultiva do planejador — automatizar é overreach.

**Doutrina canônica.** Decidida em [ADR-142](../../adr/142-toggle-imoveis-no-if-em-pipelinejson-invariante.md); per-workspace implementada em [ADR-222](../../adr/222-imoveis-no-if-per-workspace.md). **Default `imoveis_no_if = false` (conservadorismo Perini)** desde [ADR-223](../../adr/223-flip-default-imoveis-no-if-conservador.md); workspaces existentes preservam estado (rows não tocadas pela migration). Opt-in para `true` exige signal afirmativo via banner UX em MembersTab (A13) — exige confirmação de que aluguel líquido rende > TRS (~3% real/ano) E que capital está comprometido com IF. Flip explícito via `PUT /workspaces/{ws}/imoveis-no-if` (audit `set_at` + `set_by_user_id`). `set_at IS NULL` distingue default conservador herdado de escolha explícita do usuário.

**Enforcer.**
- [`pipeline/domain/services/patrimonio_calculator.py`](../../../pipeline/domain/services/patrimonio_calculator.py) — aplica `cat_2 if imoveis_no_if else 0` em `investivel_efetivo`.
- [`pipeline/domain/services/passive_income_calculator.py`](../../../pipeline/domain/services/passive_income_calculator.py) — campo `renda_passiva_atual` deve respeitar a invariante (excluir aluguéis quando `imoveis_no_if=true`).

**Validação.** `e5_analyze.py` deve emitir warning quando `imoveis_no_if=true` **e** `renda_passiva_atual_mensal_brl > sum(aluguéis_categorizados_como_renda_recorrente)` — sinaliza provável dupla contagem.

**Fórmula.** Ver [FORMULAS.md §Patrimônio](../FORMULAS.md#patrimônio) — `investivel_efetivo = investivel_financeiro + (cat_2 if workspace.imoveis_no_if else 0)`.

**Metodologias.** Perini (imóvel investimento como capital gerador, residência principal fora) + AUVP (separação rigorosa entre patrimônio investido e bens de uso).
