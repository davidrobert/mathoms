---
id: PLAN-s4-real-estate-enrichment
type: plan
title: S4 Real Estate — Enriquecimento do card de yield (cap rate líquido + benchmarks + tabela por imóvel)
status: draft
sprint_origem: A12
sprint_atual: A12
sprints_envolvidas: [A12]
created_at: "2026-05-15"
last_review: "2026-05-15"
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-216]]"
tags:
  - type/plan
  - status/draft
  - area/relatorio
  - area/pipeline
  - area/frontend
  - methodology/perini
  - methodology/auvp
---

# S4 Real Estate — Enriquecimento do card de yield

> **Origem:** sessão 2026-05-15 — usuário (workspace real com R$ 3,1M em
> imóveis, yield bruto 1,7%) classificou o card S4 atual como
> "superficial e não rico". Diagnóstico do orquestrador confirmou:
> S4 inteira é hoje **um único `NarrativeChartCard`** (texto puro) — sem
> chart, sem KPI, sem comparação visual com benchmark, e o título promete
> "vs CDI" sem mostrar CDI.
>
> **Co-design:** `financial-planner` + `product-designer` em paralelo
> (sessão 2026-05-15) convergiram em escopo mais ambicioso: cap rate
> **líquido** (não bruto) + benchmark **triplo** (CDI/NTN-B/IFIX) + tabela
> por imóvel + bloco de ação quantificado.
>
> **ADR canônica:** [[ADR-216]] — `Proposto` (2026-05-15). Consome
> classificação de imóveis estabelecida em [[ADR-215]] (enum
> `classification` via override DB; merged em paralelo em 2026-05-15).
> Gate obrigatório por CLAUDE.md §"Política operacional — ADR Proposto
> antes de PR P0/P1" antes de qualquer PR de implementação.
>
> **Não bloqueia / não é bloqueado por:** parecer planejador
> ([PLAN-planner-review](../PLANNER_REVIEW/_README.md), ✅ done). S4 é
> diagnóstico determinístico (P0); parecer é interpretação holística (E6
> LLM). Mesma família, camadas distintas.

---

## Status

| Onda | Status | PR | Notas |
|---|---|---|---|
| Onda 0 — Fundação metodológica (ADR + FORMULAS) | 🟡 em andamento | — | ADR-215 nesta sessão; FORMULAS.md update no mesmo PR ou seguinte. |
| Onda 1 — Investigação: imputação de aluguel por imóvel | ⏳ pendente | — | PR exploratório isolado. De-risca Ondas 2-6. |
| Onda 2 — Métricas determinísticas em E5.N | ⏳ pendente | — | Bloqueada por Onda 0 (ADR) e Onda 1 (achados). |
| Onda 3 — Renderer React Premium (`RealEstateYieldCard`) | ⏳ pendente | — | Bloqueada por Onda 2 (payload). |
| Onda 4 — Codegen + report_layout.yaml | ⏳ pendente | — | Trivial após Ondas 2-3; pode mergear junto. |
| Onda 5 — Testes + goldens E5 | ⏳ pendente | — | Em paralelo com Ondas 2-3. |
| Onda 6 — Empty states + cutover | ⏳ pendente | — | Último; finaliza v1. |

---

## Tese central

> O card S4 hoje pergunta a coisa errada ("yield bruto vs CDI?"); o card
> S4 enriquecido pergunta a coisa certa: **"o capital alocado em imóveis
> está rendendo o quanto deveria, líquido de IR e custos, comparado aos
> benchmarks honestos (renda fixa real e classe pareada)?"** — em 5
> segundos, com 1 alerta acionável quando aplicável.

A ADR-215 fixa **o que** muda metodologicamente. Este plano fixa **como**
implementar — em 6 ondas com gates explícitos.

---

## Pré-requisitos bloqueantes

| # | Bloqueio | Origem | Impacto se não resolvido |
|---|---|---|---|
| PR-1 | ADR-215 mergeada como `Proposto` | CLAUDE.md §"Política operacional" | PR de implementação sem ADR fere a regra. |
| PR-2 | `market_rates` populado com séries CDI + NTN-B + IFIX 12m | [[ADR-135]] | Tríade de benchmarks degrada para "CDI apenas" — viola D2 da ADR. |
| PR-3 | Decisão sobre imputação de aluguel por imóvel | Onda 1 | Define se tabela mostra aluguel individual (D4 cheio) ou só valor + status (D4 fallback). |
| PR-4 | Defaults de vacância/manutenção/IR aliquota confirmados por `financial-planner` | [[ADR-216]] D6 | Aciona ondas downstream sem revisão metodológica. |

PR-1 é desta sessão (em curso). PR-2/PR-3/PR-4 são gates da Onda 0/1.

---

## Onda 0 — Fundação metodológica

**Objetivo:** fechar princípios + fórmulas antes de qualquer linha de
código de domínio/UI.

**Entregáveis:**

1. [[ADR-216]] mergeada como `Proposto` (esta sessão).
2. [`docs/reference/FORMULAS.md`](../../reference/FORMULAS.md) §**Imóveis**
   nova, com 4 fórmulas:
   - `cap_rate_liquido_pct`
   - `cap_rate_bruto_pct` (preservado para auditoria)
   - `concentracao_imobiliaria_pct`
   - `spread_vs_benchmark_pp` (×3: CDI líquido, NTN-B real, IFIX 12m)
3. Tabela de defaults configuráveis em FORMULAS.md (vacância 15%,
   manutenção 1%, IR carnê-leão derivado, concentração alerta 40%).
4. Auditoria de `market_rates`: confirmar séries CDI + NTN-B + IFIX
   disponíveis; se faltar, abrir ticket de seed (pré-requisito Onda 2).
5. Revisão `financial-planner` dos defaults (1 rodada, anti-loop por
   CLAUDE.md).

**Gate de saída:** ADR mergeada + FORMULAS atualizada + audit de
`market_rates` documentado.

**Risco:** defaults controversos (manutenção 1% baixo para imóveis
tombados, vacância 15% alto para premium urbano). Mitigação: override
por workspace via [[ADR-134]]; tooltip explica "valores estimados".

**Duração estimada:** 1 dia.

**Owner:** orquestrador + `financial-planner` (review).

---

## Onda 1 — Investigação: imputação de aluguel por imóvel (PR exploratório)

**Objetivo:** descobrir se aluguel mensal pode ser imputado por imóvel
ou se v1 cai no fallback de [[ADR-216]] D4.

**Hipóteses a testar (em ≥3 workspaces reais com imóveis):**

1. **H1 — IRPF carnê-leão tem 1:1 com imóvel.** `pipeline/llm/schemas/e16_irpf_full.py:175`
   (`rendimentos_pf`) carrega `fonte`/`pagador`/`descricao`. Verificar
   se o campo `descricao` ou `imovel_endereco` (se existir) permite
   matching com o endereço/descrição do imóvel no E1.5 baseline.
2. **H2 — E4 receitas categorizadas como "Aluguel" têm referência ao imóvel.**
   Verificar se categorização atual de receitas guarda info de origem
   (qual conta, qual descrição) que mapeia para imóvel.
3. **H3 — Distribuição pro-rata pelo valor IRPF é aceitável como aproximação.**
   Se H1/H2 falham, calcular aluguel total ÷ valor total × valor_imóvel
   é uma aproximação válida? Comunicar como "estimado" no UI?

**Entregáveis:**

- Relatório técnico em [`docs/plan/S4_REAL_ESTATE_ENRICHMENT/INVESTIGATION_alugueis.md`](INVESTIGATION_alugueis.md)
  com achados por workspace, taxa de matching, e recomendação de
  caminho para Onda 2.
- Decisão registrada: tabela cheia (D4 happy path) ou fallback (D4
  degradado).

**Gate de saída:** decisão de caminho documentada; payload schema da
Onda 2 fica condicionado a este achado.

**Risco:** se H1/H2/H3 todos falham, tabela por imóvel degrada para
"valor + status do contrato" sem cap rate individual — degradação
aceitável da v1 conforme [[ADR-216]] D4 fallback.

**Duração estimada:** 1-2 dias (read-only — inspeção de payloads em
ambiente de dev).

**Owner:** `data-engineer` (delegação obrigatória por CLAUDE.md
§Protocolo de delegação — contrato entre stages).

---

## Onda 2 — Métricas determinísticas em E5.N

**Objetivo:** popular payload E5 com chave nova `real_estate` contendo
todos os campos consumidos pelo card.

**Localização do código:**

- Novo módulo: [`pipeline/domain/services/real_estate_metrics.py`](../../../pipeline/domain/services/real_estate_metrics.py)
  (puro; recebe `RealEstateConfig` value object, sem `StageConfig`
  inteiro — [[ADR-097]] D3).
- Consumido por:
  [`pipeline/domain/services/narrativas/metrics.py`](../../../pipeline/domain/services/narrativas/metrics.py)
  (ou módulo dedicado se o tamanho justificar).
- Refactor de [`charts_narrator.py:254`](../../../pipeline/domain/services/narrativas/charts_narrator.py):
  remove `yield_imoveis` narrative (substituído por payload estruturado);
  `summaries_narrator.py:81` mantém menção curta no texto da seção.

**Payload novo (anexado ao E5 `analise_financeira`):**

```json
{
  "real_estate": {
    "cap_rate_liquido_pct": 1.3,
    "cap_rate_bruto_pct": 1.7,
    "componentes_calculo": {
      "aluguel_anual_bruto": 52704,
      "ir_carne_leao_anual": 11857,
      "iptu_anual": 4800,
      "condominio_anual": 7200,
      "manutencao_anual": 31000,
      "vacancia_anual": 7905,
      "valor_imovel_irpf": 3100000
    },
    "benchmarks": {
      "cdi_liquido_pct": 8.7,
      "ntnb_real_pct": 6.5,
      "ifix_yield_pct": 9.2,
      "as_of_date": "2026-05-15"
    },
    "spreads_pp": {
      "vs_cdi": -7.4,
      "vs_ntnb": -5.2,
      "vs_ifix": -7.9
    },
    "custo_oportunidade_anual_brl": {
      "vs_cdi": -228200,
      "vs_ntnb": -160000,
      "vs_ifix": -245000
    },
    "concentracao_pct": 35.8,
    "imoveis": [
      {
        "id": "imovel_01",
        "descricao": "Apto Vila Madalena",
        "valor_irpf": 1200000,
        "aluguel_mensal_bruto": 2100,
        "cap_rate_bruto_pct": 2.1,
        "cap_rate_liquido_pct": 1.6,
        "data_ultimo_reajuste": "2024-08-15",
        "indice_reajuste": "IGPM",
        "status_contrato": "atualizado"
      }
    ],
    "gap_otimizacao": {
      "n_contratos_pendentes": 2,
      "delta_mensal_brl": 8500,
      "delta_anual_brl": 102000
    },
    "alertas": [
      {
        "code": "spread_critico_persistente",
        "severity": "warning",
        "context": "Cap rate líquido <50% do CDI por 12+ meses"
      }
    ]
  }
}
```

**Schema:** atualizar
[`config/schemas/e5_analysis.schema.json`](../../../config/schemas/e5_analysis.schema.json)
com a chave `real_estate` (validação automática via hook `DBArtifactStore.write`,
[[ADR-212]]).

**Invariantes obrigatórias:**

- Tudo monetário em `Decimal` / `Money.brl` ([[ADR-090]]); float **proibido**.
- `cap_rate_liquido_pct ≥ 0` (cap rate negativo é sinal de erro de imputação,
  não business case válido).
- `concentracao_pct ∈ [0, 100]`.
- `imoveis[]` ordenado por `valor_irpf` desc.
- `as_of_date` dos benchmarks dentro da janela do relatório.

**Gate de saída:** schema validado, métricas reproduzem cálculos manuais
em 3 workspaces de teste, golden execution E5 atualizado.

**Duração estimada:** 1-2 dias.

**Owner:** orquestrador + `data-engineer` (review do contrato schema).

---

## Onda 3 — Renderer React Premium

**Objetivo:** substituir `NarrativeChartCard` da S4 por novo componente
rico.

**Localização:**

- Novo:
  [`frontend/src/components/report/cards/RealEstateYieldCard.tsx`](../../../frontend/src/components/report/cards/RealEstateYieldCard.tsx).
- Padrão de referência:
  [`frontend/src/components/report/cards/RentabilidadeCard.tsx`](../../../frontend/src/components/report/cards/RentabilidadeCard.tsx)
  (hero + bloco de contexto + footer; variants por threshold).
- Atualização:
  [`frontend/src/components/report/sections/S4RealEstateSection.tsx`](../../../frontend/src/components/report/sections/S4RealEstateSection.tsx)
  troca `NarrativeChartCard` por `RealEstateYieldCard`.

**Layout (wireframe textual):**

```
┌─ HERO (full, variant by spread/alerta) ──────────────────────────┐
│ Cap rate líquido                Custo de oportunidade vs CDI      │
│ 1,30% a.a.                      −R$ 228 mil/ano                   │
│                                                                    │
│ Benchmarks (a.a. líquido):                                         │
│ Cap rate ▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░ 1,3%                          │
│ NTN-B+   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░ 6,5%                          │
│ CDI      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░ 8,7%                          │
│ IFIX 12m ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░ 9,2%                          │
└────────────────────────────────────────────────────────────────────┘

┌─ TABELA POR IMÓVEL (Premium; ≤5 + "Ver todos N") ────────────────┐
│ Imóvel              │ Valor IRPF │ Aluguel/mês │ Cap líq │ Status │
│ Apto Vila Madalena  │ R$ 1.200k  │  R$ 2.100   │ 1,6%    │ ●      │
│ Casa Granja Viana   │ R$   980k  │  R$ 1.450   │ 1,2%    │ ▲      │
│ Sala Berrini        │ R$   620k  │    R$ 542   │ 0,8%    │ ▲      │
│ Terreno Cotia       │ R$   300k  │     —       │  —      │ ○      │
└────────────────────────────────────────────────────────────────────┘

┌─ AÇÃO (Premium; variant=warn se gap>0) ──────────────────────────┐
│ Gap de otimização                                                  │
│ 2 contratos com reajuste pendente — atualizá-los gera +R$ 8.500/mês│
│ (+R$ 102k/ano). Mesmo assim, cap rate líquido ficaria abaixo do    │
│ CDI — considerar realocação parcial.                               │
└────────────────────────────────────────────────────────────────────┘

┌─ Header da seção: badge "Concentração 35,8% do patrimônio" ──────┐
│ (variant=warn se >40%)                                             │
└────────────────────────────────────────────────────────────────────┘
```

**Tier gating** (alinhado com [[ADR-216]] D7):

- Free: Hero + concentração badge. Teaser "Detalhe por imóvel no Premium".
- Premium: + tabela + bloco de ação.

**A11y:**

- Badges com forma+cor+texto (não só cor).
- `aria-label` em todos os ícones.
- Tabela com `<caption>` screen-reader-only.
- Foco visível em hover de linha.
- WCAG AA: contraste 4.5:1 em badges e variants `critical`/`warn`.

**Mobile <md:** tabela colapsa em lista de cards (1 por imóvel); hero
empilha (cap rate em cima, benchmarks embaixo).

**Tokens:** apenas `var(--brand-*)`, `var(--surface-*)`, `var(--semantic-*)`.
Zero hex literal ([[ADR-076]]).

**Copy do título:** "Imóveis de investimento — Yield vs renda fixa e
FIIs" (limpo, alinhado à tríade de benchmarks).

**Gate de saída:** Vitest unit + Playwright E2E `@critical`; revisão
`product-designer` aprovada.

**Duração estimada:** 2-3 dias.

**Owner:** orquestrador + `product-designer` (review pré-merge).

---

## Onda 4 — Codegen + report_layout.yaml

**Objetivo:** atualizar layout codegen para usar o novo card em vez do
`NarrativeChartCard` genérico.

**Mudanças:**

1. [`config/report_layout.yaml`](../../../config/report_layout.yaml) §S4:
   ```yaml
   - id: "S4"
     title: "Imóveis de investimento — Yield vs renda fixa e FIIs"
     enabled: true
     summary: true
     divider_before: true
     charts: []   # remover yield_imoveis
     cards:
       - id: "real_estate_yield"
         enabled: true
         variant: "feature"
         size: "full"
   ```
2. Rodar `python3 dev/codegen_report_layout.py` — regenera
   [`frontend/src/generated/report-layout.ts`](../../../frontend/src/generated/report-layout.ts)
   + [`backend/app/generated/report_layout.py`](../../../backend/app/generated/report_layout.py).
3. Limpar referências a `yield_imoveis` em
   [`frontend/src/components/report/utils/conclusionUtils.ts:220`](../../../frontend/src/components/report/utils/conclusionUtils.ts)
   (entrada `yield_imoveis: "Rendimento dos imóveis comparado ao CDI."`
   torna-se obsoleta).

**Gate de saída:** codegen produz diff esperado; build frontend verde.

**Duração estimada:** 0,5 dia.

**Owner:** orquestrador.

---

## Onda 5 — Testes + goldens

**Em paralelo com Ondas 2-3.**

### Pipeline (`tests/test_e5n_real_estate_metrics.py` novo):

- `test_cap_rate_liquido_calc` — componentes conhecidos → resultado canônico.
- `test_cap_rate_zero_aluguel` — imóvel sem aluguel não quebra cálculo agregado.
- `test_concentracao_alerta_threshold` — `concentracao_pct ≥ 40` dispara alerta.
- `test_benchmarks_normalizados_liquidos` — CDI/NTN-B/IFIX vêm de `market_rates`
  já com normalização pós-IR aplicada.
- `test_spread_negativo_persistente_alerta` — flag `spread_critico_persistente`
  só se ≥12 meses E concentração >30%.
- `test_empty_state_zero_imoveis` — payload `real_estate` ausente ou vazio
  → seção S4 oculta.
- `test_residencia_principal_excluida` — imóvel com `investment=false`
  não entra no cálculo.

### Frontend unit (`frontend/tests/components/RealEstateYieldCard.test.tsx`):

- Renderiza 4 KPIs no hero (Free + Premium).
- Tabela escondida em Free; visível em Premium.
- Variants `critical`/`warn`/`success` por spread.
- A11y: roles ARIA, foco, contraste.
- Empty states (0/1/N imóveis).

### Frontend E2E (`@critical`):

- Workspace com imóveis → S4 aparece com hero + concentração.
- Workspace sem imóveis → S4 oculta no relatório.
- Premium tier → tabela visível; Free tier → teaser.

### Golden execution E5:

- Atualizar [`tests/test_e5_golden_execution.py`](../../../tests/test_e5_golden_execution.py)
  para incluir nova chave `real_estate` no schema validation.

**Gate de saída:** suíte completa verde local + CI.

**Owner:** orquestrador.

---

## Onda 6 — Empty states / cutover

**Objetivo:** finalizar v1 garantindo cobertura dos casos de borda.

**Entregáveis:**

1. Layout codegen condiciona `enabled: false` em S4 quando
   `imoveis_investimento == 0` (ou só residência principal).
2. Filtro de residência principal no
   [`member_analyzer.py:202-209`](../../../pipeline/domain/services/member_analyzer.py)
   propaga flag `investment=true` para o payload.
3. Workspace com 1 imóvel: hero + concentração + ação; tabela suprimida.
4. Remoção do código legado `yield_imoveis` em narradores (texto fica
   apenas em `SectionSummary` se útil para Free tier).
5. Atualizar [`docs/CHANGELOG.md`](../../CHANGELOG.md) com entry da
   sprint A12.

**Gate de saída:** rodar pipeline em ≥3 workspaces reais (com / sem /
parcial imóveis) e validar visual.

**Duração estimada:** 0,5 dia.

**Owner:** orquestrador.

---

## Dependências entre ondas

```
Onda 0 (ADR + FORMULAS)
  ├─→ Onda 1 (investigação imputação) ──┐
  │                                       ↓
  ├─→ Onda 2 (métricas E5.N) ────────────┴─→ Onda 3 (renderer React)
  │         ↓                                       ↓
  │   Onda 5 (testes pipeline)              Onda 5 (testes frontend)
  │                                                 ↓
  └─────────────────────────────────────────→ Onda 4 (codegen)
                                                    ↓
                                              Onda 6 (cutover)
```

Onda 0 e 1 são bloqueantes. Ondas 2/3/5 podem ter trabalho paralelo
dentro delas. Ondas 4 e 6 são sequenciais ao fim.

**Duração estimada total:** ~7-10 dias úteis, distribuídos em ~2 PRs
maiores (Onda 0+1 em PR docs; Ondas 2-6 em PR de implementação) ou
~6 PRs pequenos.

---

## Riscos consolidados

| Risco | Probabilidade | Mitigação | Owner |
|---|---|---|---|
| Aluguel por imóvel não imputável → tabela vira só "valor + status" | Média | Fallback D4 da ADR-215 já decidido; degradação aceitável da v1. | Onda 1 |
| `market_rates` sem séries NTN-B/IFIX históricas | Baixa | Onda 0 audita; seed antes da Onda 2. | Onda 0 |
| Defaults de vacância/manutenção controversos | Média | Override por workspace ([[ADR-134]]); tooltip explicativo; revisão metodológica explícita. | `financial-planner` |
| Concentração 40% threshold gera alarme falso | Média | Configurável + texto neutro do alerta. | Onda 2 |
| Card percebido como "pitch contra imóvel" | Baixa-média | Parecer E6 contextualiza ([[ADR-199]]); card S4 é só diagnóstico. | UX (Onda 3) |
| Breaking change em schema E5 quebra consumer atual | Baixa | Adição de chave `real_estate` é compatível (additive); `yield_imoveis_pct` legado mantido por 1 sprint antes de remoção. | Onda 2 |

---

## Critério de "concluído" (definition of done)

Plano transita para `done` quando:

1. ✅ ADR-215 mergeada e flippada para `Decidido` no PR final.
2. ✅ FORMULAS.md §Imóveis populada com as 4 fórmulas e defaults.
3. ✅ Card `RealEstateYieldCard` em produção (mergeado em `main`,
   CI verde, visto em workspace real).
4. ✅ Schema E5 com chave `real_estate` validado pelo hook
   `DBArtifactStore.write`.
5. ✅ Tier gating Free vs Premium funcionando (testado em ambos os
   tiers).
6. ✅ Empty states em 3 níveis (0 / 1 / N+ imóveis) validados.
7. ✅ Goldens de execução E5 atualizados; suíte verde.
8. ✅ Entry no `docs/CHANGELOG.md` (A12).

**Não conta como done:**

- Apenas ADR mergeada (sem implementação) — fica `in_progress`.
- v1 com fallback degradado de D4 (sem aluguel por imóvel) **conta**
  se Onda 1 documentou inviabilidade técnica; mas registra débito em
  lane futura para v2.

---

## Referências cruzadas

- [[ADR-216]] — decisão canônica (cap rate líquido + benchmarks tríade)
- [[ADR-191]] — precedente do card TRS (diferenciação carteira vs single-class)
- [[ADR-143]] — `methodology=code`
- [[ADR-090]] — `Decimal`/`Money.brl` para dinheiro
- [[ADR-097]] D3 — services recebem value objects tipados
- [[ADR-076]] — codegen do report layout
- [[ADR-134]] — `ConfigStore` (overrides por workspace)
- [[ADR-135]] — `market_rates` (CDI/NTN-B/IFIX)
- [[ADR-199]] / [[ADR-208]] — parecer E6 (camada de interpretação) + framework Free/Premium
- [[ADR-212]] — `DBArtifactStore` com schema validation hook
- Co-design: `financial-planner` + `product-designer` (sessão 2026-05-15)
