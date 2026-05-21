---
id: ADR-236
type: adr
title: "Cone Monte Carlo de IF inclui aporte mensal (paridade com projeção determinística)"
status: Proposto
phase: pos-A15
date: "2026-05-20"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-097]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 236"
  - "Monte Carlo IF com PMT"
  - "Cone IF com aporte"
tags:
  - area/pipeline
  - area/financial-planning
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - status/proposto
  - type/adr
---

## Contexto

A seção S7 do relatório expõe **duas projeções acopladas** de Independência Financeira:

1. **Card determinístico** — `IFProjector.project()` resolve `n` em `FV = PV·(1+r)^n + PMT·((1+r)^n − 1)/r`. Usa aporte mensal de `goals.aportes.meta_aporte_mensal`. Devolve `idade_titular_if` (ex.: "IF aos 55").

2. **Cone Monte Carlo** — `run_monte_carlo_if()` roda 10 000 simulações log-normais com `sigma_anual=0.11`, `retorno_real_esperado=0.05`. Devolve cone P10/P50/P90 + `prob_if_ate_idade_meta`.

A simulação atual compõe **apenas o patrimônio inicial**:

```python
patrimonios = pv * np.exp(np.cumsum(log_retornos, axis=1))
```

Zero aportes são simulados — apesar de o aporte estar disponível no `IFProjectorConfig` que originou o caller. Resultado: para usuário em acumulação (`if_pct < 50%`), o cone subestima dramaticamente a probabilidade de atingir IF, contradizendo o card determinístico mostrado logo acima ("IF aos 55" vs. "Probabilidade até 55: 0%").

## Decisão

**O Monte Carlo passa a incluir aporte mensal constante em termos reais**, alinhado à projeção determinística.

Mudanças concretas:

1. **`IFMonteCarloConfig`** ganha campo `aporte_mensal: Decimal = Decimal("0")` (ADR-090 — dinheiro nunca é `float` no boundary).

2. **`_simular_caminhos`** passa a aplicar PMT na simulação vetorizada. Convenção espelha o determinístico:
   - PMT entra no **início** de cada ano (anuidade antecipada).
   - PMT mensal × 12 = PMT anual (aproximação aceitável; erro <0,4% para retornos reais ~5%).
   - PMT é constante em **termos reais** (poder de compra de hoje preservado) — todo o modelo já roda em reais (`retorno_real_esperado`).

   Fórmula fechada:

   ```
   W_T = PV · ∏_{t=1..T} r_t + 12·PMT · Σ_{k=1..T} ∏_{t=k..T} r_t
   ```

   Vetorização: `cumprod` reverso por simulação dá os fatores `∏_{t=k..T} r_t`; soma vetorial fecha em <150 ms para n=10 000, h=40.

3. **`e5_analyzer_adapter.py`** passa `cfg.aporte_mensal` ao montar `IFMonteCarloConfig`.

4. **Labels e copy** do gráfico (`IFConeConeChart`, `S7IndependenciaSection`):
   - P10/P90 invertidos no frontend — P10 (10º percentil = bottom 10%) é **cenário adverso**, P90 (90º = top 10%) é **cenário favorável**. Cores semânticas seguem (`semantic.loss` para P10, `semantic.gain` para P90).
   - Texto exibe premissas: `"considerando aporte de R$ X/mês mantido em termos reais, com volatilidade de Y% a.a."`.
   - Display de probabilidade: `<1%` quando `prob ∈ (0, 0.01)`; `>99%` quando `prob ∈ (0.99, 1)`; `0%` somente quando literalmente zero.

5. **Goldens** em `tests/test_e5_golden_execution.py` recalibrados no mesmo PR (eram baseados no MC sem aporte).

## Alternativas consideradas

**A) Manter MC sem PMT, adicionar segundo card "estresse de capital".**
Rejeitado pelo `financial-planner`: dois cones competindo no mesmo painel confundem; o default precisa ser a história coerente com o card determinístico, não um *what-if* de exceção.

**B) Loop Python por ano (10 000 × 40 = 400 k iterações).**
Rejeitado pelo `senior-cto`: ~5 s de latência degrada UX do recompute do relatório; fórmula fechada vetorizada bate o mesmo resultado em <150 ms.

**C) Feature flag para PMT ativável.**
Rejeitado: cria dead code permanente (flag desligada → caminho novo não testado em prod); viola ADR-111 se a flag virar global.

**D) Versão paralela `MonteCarloIFResult.version`.**
Rejeitado: dobra superfície de teste e ninguém migra v1 → v2 sem deadline imposto.

**E) Mudar default `sigma_anual` de 11% para 14%** (recomendação do `financial-planner` para carteira AUVP-style).
Adiado: parametrização por perfil de risco depende de campo novo em `goals` e UX para escolher perfil — escopo separado. Esta ADR mantém `sigma_anual=0.11` como default; muda só o tratamento de PMT. Follow-up rastreado em [PLATFORM_REVIEW backlog](../plan/PLATFORM_REVIEW/_README.md).

## Consequências

**Positivas:**

- Paridade narrativa entre os dois widgets de S7: o cone passa a **confirmar ou problematizar** a âncora determinística, não contradizê-la silenciosamente.
- Métricas (`prob_if_ate_idade_meta`, `p50_ano_if`) ganham significado consistente com Perini/Cerbasi/AUVP — aporte é variável central, não dispensável.
- Teste invariante novo (`sigma=0 ∧ PMT>0 ⇒ MC P50 ≡ determinístico até centavo`) cria gate empírico que pega regressão futura.

**Negativas:**

- **Mudança semântica P0** da métrica `prob_if`: usuário com PV baixo e PMT alto vai ver a probabilidade saltar de "0%" para algo como "78%". É a leitura correta, mas merece comunicação no changelog do relatório.
- Goldens recalibrados num único commit — quem comparar payloads E5 pré/pós-merge vê diferença grande.
- A simulação não modela **choques no PMT** (perda de emprego, mudança de meta de poupança) nem inflação heterogênea — limitação documentada na docstring; trabalho futuro.

## Critério de aceite

- `test_mc_with_zero_vol_matches_deterministic`: `sigma=0 ∧ PMT>0 ⇒ MC P50_year = idade_titular_if` do `IFProjector` (tolerância: ±1 ano).
- `test_mc_pmt_increases_prob`: dados fixos exceto PMT (0 vs R$ 5 k/mês), `prob_if_ate_idade_meta` do segundo ≥ 2× a do primeiro (PMT importa).
- `test_mc_pmt_zero_preserves_legacy`: `aporte_mensal=Decimal("0")` produz percentis idênticos ao comportamento anterior (regression — protege contra cálculo errado de PMT=0).
- Frontend: labels P10/P90 ligados a `semantic.loss`/`semantic.gain` por inspeção (snapshot ou test unitário).
- Display do prob: 0,003 vira `"<1%"` na UI; 0,997 vira `">99%"`; 0,5 vira `"50%"`.
- `slog` em `mathoms.pipeline.if_projector` inclui `aporte_mensal` no payload do evento MC.

## Referências

- `pipeline/domain/services/if_projector.py` — `IFProjector.project()`, `_simular_caminhos`, `run_monte_carlo_if`.
- `pipeline/domain/services/e5_analyzer_adapter.py:541` — caller que monta `IFMonteCarloConfig`.
- `frontend/src/components/report/charts/IFConeConeChart.tsx` — labels/cores do cone.
- `frontend/src/components/report/sections/S7IndependenciaSection.tsx:155-160` — copy do card MC.
- `tests/test_if_projector_v2.py`, `tests/test_if_projector_mc_paths.py` — testes existentes.
- [[ADR-090]] — dinheiro nunca é `float`.
- [[ADR-097]] — services de domínio com value object de config tipada.
