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
| Onda 0 — Fundação metodológica (ADR + FORMULAS) | 🟡 em andamento | [#280](https://github.com/davidrobert/mathoms/pull/280) | ADR-216 mergeada (2026-05-15); FORMULAS.md update pendente. |
| Onda 0.5 — Schema estruturado de Informe de Imobiliária | ⏳ pendente | — | Parser LLM dedicado (padrão ADR-157) — destrava cascade D9 da ADR-216. Pode rodar em paralelo com Onda 1. |
| Onda 1 — Auditoria empírica: cobertura de Informe + IRPF + E4 | ⏳ pendente | — | PR exploratório isolado. Mede qual fonte aplica a cada workspace; de-risca Ondas 2-6. |
| Onda 2 — Métricas determinísticas em E5.N | ⏳ pendente | — | Bloqueada por Onda 0 (ADR), Onda 0.5 (parser) e Onda 1 (achados). |
| Onda 3 — Renderer React Premium (`RealEstateYieldCard`) | ⏳ pendente | — | Bloqueada por Onda 2 (payload). |
| Onda 4 — Codegen + report_layout.yaml | ⏳ pendente | — | Trivial após Ondas 2-3; pode mergear junto. |
| Onda 5 — Testes + goldens E5 | ⏳ pendente | — | Em paralelo com Ondas 0.5/2/3. |
| Onda 6 — Empty states + cutover | ⏳ pendente | — | Último; finaliza v1. |

---

## Tese central

> O card S4 hoje pergunta a coisa errada ("yield bruto vs CDI?"); o card
> S4 enriquecido pergunta a coisa certa: **"o capital alocado em imóveis
> está rendendo o quanto deveria, líquido de IR e custos, comparado aos
> benchmarks honestos (renda fixa real e classe pareada)?"** — em 5
> segundos, com 1 alerta acionável quando aplicável.

A ADR-216 fixa **o que** muda metodologicamente. Este plano fixa **como**
implementar — em 6 ondas com gates explícitos.

---

## Pré-requisitos bloqueantes

| # | Bloqueio | Origem | Impacto se não resolvido |
|---|---|---|---|
| PR-1 | ADR-216 mergeada como `Proposto` | CLAUDE.md §"Política operacional" | PR de implementação sem ADR fere a regra. **✅ Mergeada em [#280](https://github.com/davidrobert/mathoms/pull/280).** |
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

## Onda 0.5 — Schema estruturado para Informe de Imobiliária

**Objetivo:** semantizar o documento `informerendimentosaluguel` (hoje
classificado e roteado mas extraído via schema genérico de E2-LLM) para
povoar a fonte #1 da cascade D9 da [[ADR-216]].

**Fundamentação:** o doc type já existe no produto —
[`backend/app/services/classification/type_classifier.py:85`](../../../backend/app/services/classification/type_classifier.py)
classifica; [`scripts/e0_route.py:112-113`](../../../scripts/e0_route.py)
rotea via regex `informe.*rendimento.*aluguel`; legacy processou
`quintoandar_informerendimentosaluguel_2025-0_original.pdf`
([`_archive/legacy_scripts/extract_baseline_patrimonial.py:354`](../../../_archive/legacy_scripts/extract_baseline_patrimonial.py)).
Falta apenas a **camada semântica** — hoje o documento cai em
[`pipeline/llm/schemas/e2_llm_extract.py`](../../../pipeline/llm/schemas/e2_llm_extract.py)
que retorna lista plana de transações sem semântica de "aluguel do
imóvel X, taxa adm Y, IPTU descontado Z".

**Entregáveis:**

1. **Schema Pydantic dedicado**:
   [`pipeline/llm/schemas/informe_aluguel.py`](../../../pipeline/llm/schemas/informe_aluguel.py)
   espelhando o padrão [[ADR-157]] / `e16_irpf_full.py`:
   - `PROMPT_VERSION` constante (versionado)
   - `_coerce_decimal` para campos monetários ([[ADR-090]])
   - `InformeAluguelImovel` (per-imóvel: endereço, IPTU/matrícula,
     locatário CPF/CNPJ, locador CPF, período, aluguel bruto, taxa adm,
     IPTU pago pela imobiliária, condomínio pago, IR retido, aluguel
     líquido transferido, meses_locados_no_periodo)
   - `InformeAluguelExtract` (top-level: imobiliaria_cnpj,
     imobiliaria_nome, ano_referencia, membro_key, imoveis: list[...])
2. **Prompt LLM dedicado**:
   [`pipeline/llm/prompts/informe_aluguel.py`](../../../pipeline/llm/prompts/informe_aluguel.py)
   com instruções específicas para informes de imobiliária (variações
   típicas: QuintoAndar, Loft, imobiliárias locais).
3. **Roteamento em E2/E2-LLM**: se `doc_type == "informerendimentosaluguel"`,
   usar schema dedicado; senão cair no schema genérico de
   `e2_llm_extract.py` (compat).
4. **Persistência**: novo artifact key
   `("E2-informe-aluguel", "informe_imobiliaria")` ou anexação ao
   baseline (decisão de schema em revisão `data-engineer`).
5. **Gate empírico**: golden de extração em `tests/test_informe_aluguel_extraction.py`
   com PDF anonimizado de informe real (QuintoAndar ou similar).
6. **Flag de cutover**: `use_structured_informe_extractor` (default
   true; permite rollback rápido se LLM regredir).

**Componentes do informe a extrair** (must-have v1):

| Campo | Tipo | Cobertura típica em informes BR |
|---|---|---|
| `imovel.endereco` | string | Universal — sempre presente |
| `imovel.aluguel_bruto_anual` | Decimal | Universal |
| `imovel.taxa_administracao_anual` | Decimal | Universal (5-12% típico) |
| `imovel.iptu_pago_anual` | Decimal | Quando imobiliária administra IPTU (~70%) |
| `imovel.condominio_pago_anual` | Decimal | Quando aplicável e administrado (~50%) |
| `imovel.ir_retido_anual` | Decimal | Apenas quando pagador é PJ (~15-25% dos casos) |
| `imovel.aluguel_liquido_anual` | Decimal | Universal (transferido ao locador) |
| `imovel.meses_locado` | int | Universal — base para vacância empírica |
| `imobiliaria_cnpj` | string | Universal |
| `imobiliaria_nome` | string | Universal |

**Sigilo §13 ([[ADR-207]]):** valores reais e CPF/CNPJ **nunca** em commits,
docstrings, fixtures de teste — usar dados sintéticos anonimizados.

**Gate de saída:** schema valida ≥1 informe real em dev (workspace 5@5.com
com QuintoAndar); goldens fixados; flag de cutover ativa.

**Duração estimada:** 3-5 dias (schema + prompt + roteamento E2 +
persistência + 1 golden + teste integração).

**Owner:** orquestrador + `data-engineer` (review do schema + contrato
de stage).

---

## Onda 1 — Auditoria empírica: cobertura de fontes (PR exploratório)

**Objetivo:** medir empiricamente, em workspaces reais, qual fonte da
cascade D9 da [[ADR-216]] aplica a cada imóvel — input direto para a
priorização e o design do payload da Onda 2.

**Hipóteses a quantificar (em ≥3 workspaces com imóveis):**

1. **H1 — Cobertura de Informe de Imobiliária.** Quantos imóveis têm
   informe carregado? Quais imobiliárias aparecem mais (QuintoAndar,
   Loft, locais)? Confirma se Onda 0.5 destrava a maioria dos casos ou só
   uma minoria.
2. **H2 — IRPF carnê-leão tem 1:1 com imóvel.** [`pipeline/llm/schemas/e16_irpf_full.py:175`](../../../pipeline/llm/schemas/e16_irpf_full.py)
   (`rendimentos_pf`) carrega `fonte`/`pagador`/`descricao`. Verificar
   matching com endereço/descrição do imóvel no E1.5 baseline.
3. **H3 — E4 receitas categorizadas como "Aluguel" têm referência ao imóvel.**
   Categorização atual de receitas guarda info de origem (qual conta,
   qual descrição) que mapeia para imóvel?
4. **H4 — Pro-rata como fallback final.** Quando todas falham, qual é
   o erro empírico da distribuição pro-rata vs. realidade conhecida?

**Entregáveis:**

- Relatório técnico em [`docs/plan/S4_REAL_ESTATE_ENRICHMENT/INVESTIGATION_alugueis.md`](INVESTIGATION_alugueis.md)
  com:
  - Tabela: workspace × imóvel × fonte disponível (cascade D9)
  - % de cobertura por fonte (Informe / IRPF / E4 / pro-rata)
  - Imobiliárias mais frequentes (lista para priorizar prompt da Onda 0.5)
  - Recomendação: implementação da Onda 0.5 first vs. paralelo
- Decisão registrada: ordem de priorização Onda 0.5 vs. Onda 2.

**Gate de saída:** cobertura empírica documentada; payload schema da
Onda 2 fica condicionado aos achados.

**Risco:** se Informe presente em <30% dos imóveis, Onda 0.5 vira
"nice-to-have" e podemos priorizar Onda 2 com fallback IRPF.

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

**Payload novo (anexado ao E5 `analise_financeira`):** Cada componente
do `componentes_calculo` e cada campo numérico do `imoveis[]` carrega
`origem` para sinalizar fonte da cascade D9 ([[ADR-216]]).

```json
{
  "real_estate": {
    "cap_rate_liquido_pct": 1.3,
    "cap_rate_bruto_pct": 1.7,
    "componentes_calculo": {
      "aluguel_anual_bruto": {"valor": 52704, "origem": "informe"},
      "taxa_administracao_anual": {"valor": 5270, "origem": "informe"},
      "ir_retido_anual": {"valor": 0, "origem": "informe"},
      "ir_carne_leao_anual": {"valor": 11857, "origem": "irpf"},
      "iptu_anual": {"valor": 4800, "origem": "informe"},
      "condominio_anual": {"valor": 7200, "origem": "e4"},
      "manutencao_anual": {"valor": 31000, "origem": "default"},
      "vacancia_anual": {"valor": 4392, "origem": "informe"},
      "valor_imovel_irpf": {"valor": 3100000, "origem": "irpf"}
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
        "taxa_administracao_mensal": 210,
        "ir_retido_mensal": 0,
        "iptu_mensal": 400,
        "meses_locados_no_ano": 12,
        "vacancia_pct_empirica": 0.0,
        "cap_rate_bruto_pct": 2.1,
        "cap_rate_liquido_pct": 1.6,
        "data_ultimo_reajuste": "2024-08-15",
        "indice_reajuste": "IGPM",
        "status_contrato": "atualizado",
        "imobiliaria_cnpj": "12345678000190",
        "imobiliaria_nome": "QuintoAndar",
        "origem_aluguel": "informe"
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

**Cascade no service:** `real_estate_metrics.py` recebe (a) baseline E1.5,
(b) IRPF parsed E1.6, (c) **NOVO:** informe parsed Onda 0.5, (d) E4
receitas/despesas. Para cada imóvel, percorre cascade D9 ordenadamente
e popula campos + `origem`. Sem dado → omite campo + componente sai como
`default`.

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
Onda 0 (ADR + FORMULAS) ✅ ADR · FORMULAS pendente
  │
  ├─→ Onda 1 (auditoria empírica) ──┐
  │                                   │
  ├─→ Onda 0.5 (schema Informe) ────┤  (Onda 0.5 pode rodar
  │     ↑                             │   em paralelo com Onda 1;
  │     │ prioridade definida         │   prioridade ajusta-se
  │     │ por Onda 1 (PR-3)           │   pelo achado da Onda 1)
  │                                   ↓
  └─→ Onda 2 (métricas E5.N) ────────┴─→ Onda 3 (renderer React)
        ↓                                       ↓
   Onda 5 (testes pipeline)              Onda 5 (testes frontend)
                                                ↓
                                          Onda 4 (codegen)
                                                ↓
                                          Onda 6 (cutover)
```

**Caminho crítico:** Onda 0 (ADR ✅) → Onda 1 (audit) → Onda 0.5
(condicional ao resultado de Onda 1) → Onda 2 (métricas) → Onda 3
(renderer) → Onda 4/6 (cutover).

Onda 0.5 e Onda 1 podem ser paralelas (ambas read-only / additive).
Onda 2 depende de **achados** da Onda 1 e do **schema** da Onda 0.5.

**Duração estimada total:**
- v1 sem Onda 0.5 (cobertura Informe baixa): ~7-10 dias úteis
- v1 com Onda 0.5 (cobertura Informe alta): ~10-15 dias úteis

Distribuição em PRs: ~6-8 PRs pequenos (1 por onda, com Onda 0.5 e
Onda 2 possivelmente em 2 PRs cada por tamanho).

---

## Riscos consolidados

| Risco | Probabilidade | Mitigação | Owner |
|---|---|---|---|
| Aluguel por imóvel não imputável → tabela vira só "valor + status" | Baixa-média (cascade D9 reduz) | Cascade D9 (Informe → IRPF → E4 → pro-rata) cobre maioria dos casos; só falha total cai em fallback. | Onda 1 + 0.5 |
| Cobertura de Informe baixa (<30% dos imóveis) | Média | Onda 0.5 vira "nice-to-have"; v1 sai com fallback IRPF/E4 + badge "estimado". Onda 0.5 pode entrar em sprint+1 sem bloquear v1. | Onda 1 |
| Schema do Informe falha em variação de imobiliária local | Média | Flag `use_structured_informe_extractor` permite rollback rápido para schema genérico; goldens cobrem QuintoAndar/Loft em v1, locais entram conforme aparecem. | Onda 0.5 |
| `market_rates` sem séries NTN-B/IFIX históricas | Baixa | Onda 0 audita; seed antes da Onda 2. | Onda 0 |
| Defaults de vacância/manutenção controversos | Média | Override por workspace ([[ADR-134]]); tooltip explicativo; revisão metodológica explícita. | `financial-planner` |
| Concentração 40% threshold gera alarme falso | Média | Configurável + texto neutro do alerta. | Onda 2 |
| Card percebido como "pitch contra imóvel" | Baixa-média | Parecer E6 contextualiza ([[ADR-199]]); card S4 é só diagnóstico. | UX (Onda 3) |
| Breaking change em schema E5 quebra consumer atual | Baixa | Adição de chave `real_estate` é compatível (additive); `yield_imoveis_pct` legado mantido por 1 sprint antes de remoção. | Onda 2 |

---

## Critério de "concluído" (definition of done)

Plano transita para `done` quando:

1. ✅ ADR-216 mergeada e flippada para `Decidido` no PR final.
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

- [[ADR-216]] — decisão canônica (cap rate líquido + benchmarks tríade + cascade D9 de fontes)
- [[ADR-215]] — classificação de imóveis via override DB (enum `classification`) — consumido em D8
- [[ADR-191]] — precedente do card TRS (diferenciação carteira vs single-class)
- [[ADR-157]] — E1.6 IRPF full (padrão de schema Pydantic + prompt LLM espelhado pela Onda 0.5)
- [[ADR-143]] — `methodology=code`
- [[ADR-090]] — `Decimal`/`Money.brl` para dinheiro
- [[ADR-097]] D3 — services recebem value objects tipados
- [[ADR-076]] — codegen do report layout
- [[ADR-134]] — `ConfigStore` (overrides por workspace)
- [[ADR-135]] — `market_rates` (CDI/NTN-B/IFIX)
- [[ADR-199]] / [[ADR-208]] — parecer E6 (camada de interpretação) + framework Free/Premium
- [[ADR-212]] — `DBArtifactStore` com schema validation hook
- Co-design: `financial-planner` + `product-designer` (sessão 2026-05-15)
