---
id: ADR-353
type: adr
title: "Confiança do diagnóstico comportamental condicionada à cobertura de categorização"
status: Proposto
phase: pipeline-review r2 (RV2-21)
date: "2026-07-27"
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-306]]"
  - "[[ADR-209]]"
  - "[[ADR-343]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
---

# ADR-353 — Confiança do diagnóstico comportamental

> Achado **RV2-21** do pipeline-review r2 ([[ADR-343]], run `9d47574c`, ws 5@5.com).
> `Proposto` — muda a densidade de um card do relatório + adiciona campo derivado.
> Co-design: financial-planner (regra de degradê) + data-engineer (shape aditivo) +
> product-designer (chrome do card, **deferido p/ Onda B**).

## Contexto

`diagnostico_comportamental` (lista de `{padrao, evidencia, mudanca_sugerida}`,
`diagnostico_comportamental_analyzer.py`) sai com densidade cheia
independentemente de quanto do gasto foi de fato **categorizado**. No ws real,
**21% das despesas** estão em `nao_identificado` — 1/5 do comportamento de gasto
é invisível, mas o card diagnostica "disciplina" com a mesma autoridade. É
enganoso: apontar padrão de comportamento com 1/5 fora da leitura.

Não há hoje `nao_identificado_share_pct` computado no E5; o frontend **já** tem
`computeNaoIdentificadoShare()` + `ReportDataQualityBanner` global (dispara em
>10%), mas o card comportamental não reflete isso.

## Decisão

### D1 — Tiers de confiança por `nao_identificado_share_pct`

Ancorados em constantes de domínio (rules-as-code, [[ADR-143]]):
`NAO_IDENTIFICADO_PARCIAL_PCT = 10`, `NAO_IDENTIFICADO_INSUFICIENTE_PCT = 30`.

| Share não-identificado | `confianca` | Densidade |
|---|---|---|
| ≤ 10% | `alta` | padrões cheios |
| 10–30% | `parcial` | padrões + 1 item de atenção ("Ponto cego nos gastos") |
| > 30% | `insuficiente` | **zero** padrão comportamental — só o item de insuficiência |

### D2 — Fonte do share (janela 12m first)

`share = despesas_por_categoria["nao_identificado"] / Σ despesas_por_categoria.values() × 100`,
lendo `fluxo.janela_12m.despesas_por_categoria` primeiro com fallback para
`fluxo.despesas_por_categoria` (mesmo precedente de `_resolve_cerbasi_window`,
[[ADR-306]]). Denominador = **Σ das categorias** (inclui `nao_identificado`), não
`despesa_total` (que diverge por transferências internas removidas). `nao_identificado`
é bucket **exclusivo de despesa** (`transaction_classifier`), sem ambiguidade
receita×despesa. Sem despesa categorizada (Σ ≤ 0) → `share = 0` → `alta`
(conservador: ausência de dado de categoria não fabrica alarme).

### D3 — Shape aditivo (sibling), não breaking

Campo **novo, irmão**, com o array `diagnostico_comportamental` **inalterado**:

```
diagnostico_comportamental: [ {padrao, evidencia, mudanca_sugerida}, ... ]   # gated
diagnostico_confianca: { nivel: "alta"|"parcial"|"insuficiente",
                         share_nao_identificado_pct: number }
```

Escolhido sobre (A) wrap `{confianca, itens}` (quebra os 5 consumidores + perturba
o dump `raw` que o parecer consome — baseline de eval da Onda C) e (C)
item-sentinela (não dá `confianca` machine-readable). O sibling nasce
**Onda-B-compliant** (enum + number [[ADR-209]], sem money-string, sem PII-key,
sem id instável) — **fold-ready** se a Onda B consolidar metadados de diagnóstico
num wrap. O gate de densidade (D1) muda a *contagem* de itens, não o *shape* do
array → zero churn em `validate_cross` (CV12 usa `len`/`bool`), no orchestrator
S2, no schema (`type: array`) e no card React.

## Consequências

**Positivas:** o diagnóstico degrada honestamente com a qualidade da
categorização; `confianca` fica consultável (parecer/summary podem ler). Aditivo:
artefatos E5 antigos seguem válidos (sem `diagnostico_confianca` ⇒ ausência ≡ "sem
badge"); sem backfill — E5 recomputa no re-run.

**Deferido (fora deste PR):**
- **Frontend chrome → Onda B** (product-designer): badge `Cobertura parcial`
  (amarelo, não flipar a borda do card), caveat *"{pct}% das despesas ainda estão
  sem categoria — o diagnóstico cobre os outros {100−pct}%"*, e empty-state no
  `insuficiente` (*"Diagnóstico indisponível — cobertura insuficiente"* + CTA
  "Categorizar despesas →"). Card **nunca escondido** (a ausência de diagnóstico é
  o próprio sinal; contrasta com hide-when-empty da [[ADR-216]]). Reusa
  `computeNaoIdentificadoShare()` + `NAO_IDENTIFICADO_THRESHOLD_PCT` já existentes —
  uma fonte de threshold, não duas.
- **Wiring no parecer → Onda C**: `$.diagnostico_confianca` no exec-context +
  enum `get_e5_section` exige PROMPT_VERSION bump + re-check de eval de citação.

## Alternativas consideradas

- **(A) Wrap `{confianca, share, itens}`** (rejeitado): cohesion, mas churn máximo
  nos 5 consumidores + perturba baseline de eval do parecer, sem ganho de Onda B.
- **(B) Sibling `diagnostico_confianca`** (escolhido): aditivo, machine-readable,
  Onda-B-compliant, fold-ready.
- **(C) Item-sentinela na lista** (rejeitado): não-breaking, mas `confianca` só
  como texto — o parecer teria que parsear item.

## Critério de aceite

1. Fixture ~21% `nao_identificado` → `nivel="parcial"` + item "Ponto cego nos gastos"; padrões comportamentais preservados.
2. Fixture > 30% → `itens` sem padrão comportamental (só o item de insuficiência); `nivel="insuficiente"`.
3. Fixture ≤ 10% (ou sem `despesas_por_categoria`) → `nivel="alta"`, densidade inalterada (12 testes legados verdes).
4. `share_nao_identificado_pct` de `janela_12m.despesas_por_categoria` first + fallback; Σ ≤ 0 guarded → `alta`.
5. `diagnostico_confianca` no schema E5 (`nivel` enum, `share_pct` number); validação `warn` verde.
6. `validate_cross` CV12 verde (array nunca vazio: ≥1 item em todo tier).
