---
id: ADR-216
type: adr
title: "Cap rate líquido como métrica canônica de imóveis de investimento (S4)"
status: Proposto
phase: A12
date: "2026-05-15"
relates_to:
  - "[[ADR-191]]"
  - "[[ADR-215]]"
  - "[[ADR-157]]"
  - "[[ADR-145]]"
  - "[[ADR-143]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-076]]"
  - "[[ADR-134]]"
  - "[[ADR-135]]"
  - "[[ADR-199]]"
supersedes: []
superseded_by: []
aliases: ["ADR 216", "cap-rate-liquido-canonico-imoveis", "s4-real-estate-enrichment"]
tags:
  - area/relatorio
  - area/pipeline
  - area/methodology
  - methodology/perini
  - methodology/auvp
  - phase/a12
  - status/proposto
  - type/adr
---

## Contexto

Seção S4 do relatório ("Real Estate — Imóveis e Renda Passiva") hoje
contém **um único card narrativo** (`NarrativeChartCard` com `chartId="yield_imoveis"`,
[`frontend/src/components/report/sections/S4RealEstateSection.tsx`](../../frontend/src/components/report/sections/S4RealEstateSection.tsx)).
O renderer só exibe `context` + `conclusion` gerados em
[`pipeline/domain/services/narrativas/charts_narrator.py:254`](../../pipeline/domain/services/narrativas/charts_narrator.py).
Não há gráfico, tabela, KPI numérico em destaque nem comparação visual com benchmark.

Três problemas concretos:

1. **Título promete o que o card não entrega.** "Rentabilidade dos
   Imóveis (Yield) vs CDI" não mostra CDI em lugar nenhum — nem no
   payload, nem na narrativa. O usuário (sessão 2026-05-15, workspace
   real com R$ 3,1M em imóveis e yield 1,7%) classificou como
   "superficial e não rico". Comparado a S3 (doughnut + waterfall +
   `RentabilidadeCard`), S7 (3 cenários + renda passiva), S8 (impostos
   PJ com alíquota efetiva), S4 destoa por entregar **só prosa**.

2. **`yield_imoveis_pct` no payload é yield BRUTO** — `aluguel_anual / valor_imovel`
   ([`charts_narrator.py:260`](../../pipeline/domain/services/narrativas/charts_narrator.py),
   [`summaries_narrator.py:81`](../../pipeline/domain/services/narrativas/summaries_narrator.py)).
   Esconde IR carnê-leão PF (alíquota efetiva ~22-27,5%), IPTU,
   condomínio, manutenção (regra de bolso ~1% valor/ano), vacância
   (média BR ~15%). Para R$ 3,1M com yield bruto 1,7%, o yield
   **líquido** real fica ~1,1-1,3% — diferença material para a
   decisão "manter ou realocar".

3. **Comparação rasa com CDI é metodologicamente perigosa.** Revisão
   `financial-planner` (sessão 2026-05-15) e [[ADR-191]] §D5 alertam:
   yield bruto vs CDI nominal pré-IR é maçã/laranja, induz "se yield <
   CDI, vender e ir pra Selic" — que **ignora valorização patrimonial,
   diversificação e hedge inflacionário real**. Comparação honesta
   exige normalizar ambos os lados (líquido) e oferecer **benchmark
   adequado a renda real** (NTN-B IPCA+) e **classe pareada** (IFIX
   FII tijolo), não só CDI.

[[ADR-191]] §D5 estabeleceu **para o card TRS (S3)** que CDI não vai
nele — TRS é yield diversificado da **carteira toda**. Esta ADR aborda
caso **diferente**: cap rate de **uma classe** (imóveis), onde a
decisão "manter ou realocar" é legítima e exige benchmark. A resposta
não é "remover CDI"; é "normalizar comparação e adicionar benchmarks
metodologicamente honestos".

## Decisão

### D1 — `cap_rate_liquido` substitui `yield_imoveis_pct` como métrica canônica de S4

Cap rate **líquido** é a métrica que vai no hero do card e que governa
alertas. `yield_imoveis_pct` (bruto) permanece no payload para
auditoria/tooltip mas **não** é o número em destaque.

**Fórmula canônica** (vai para [`docs/reference/FORMULAS.md`](../reference/FORMULAS.md)
§Imóveis):

```
cap_rate_liquido_pct =
  (aluguel_anual_bruto
   − taxa_administracao_anual         # de Informe Imobiliária (D9) ou 0
   − ir_retido_anual                  # de Informe (PJ pagador) ou 0
   − ir_carne_leao_anual              # alíquota efetiva PF residual, do IRPF
   − iptu_anual                       # de Informe (quando administra) ou E4
   − condominio_anual                 # de Informe (quando administra) ou E4
   − manutencao_anual                 # default 1% × valor_irpf
   − vacancia_anual                   # empírica de Informe ou default 15%
  ) / valor_imovel_irpf × 100
```

Componentes individuais expostos no payload (não só o resultado) para
tooltip de explicação no card e para auditabilidade. **Cada componente
carrega a fonte** (`origem: "informe" | "irpf" | "e4" | "default"`) para
sinalizar nível de confiança ao usuário no tooltip.

### D2 — Benchmark TRIPLO substitui "vs CDI" sozinho

Hero compara cap rate líquido contra três séries da tabela global
`market_rates` ([[ADR-135]]):

| Benchmark | Justificativa | Normalização |
|---|---|---|
| **CDI líquido (12m)** | Custo de oportunidade de renda fixa pós-fixada (alocação default). | Aplicar IR efetivo PF de RF (média ponderada 15-22,5% pela curva de prazo do workspace; default 17,5%). |
| **NTN-B real (vértice 10y interpolado)** | Comparação **renda real ↔ renda real** — imóvel é hedge inflacionário, NTN-B é renda real explícita. Vértice 10 anos **constante** (interpolado), não título fixo (NTN-B 2035 vira 5y em 2030). | Já é taxa real; aplicar IR 15% (longo prazo). |
| **IFIX yield 12m** | Classe pareada (FII tijolo) — "vale a pena trocar imóvel físico por papel imobiliário?". | Yield isento IR PF; sem normalização. |

Display: 3 barras horizontais lado a lado no hero, todas em base anual
líquida. Spread em pp **e** em R$/ano (custo de oportunidade absoluto:
"se R$ 3,1M estivessem em NTN-B, renderia R$ X/ano a mais").

### D3 — Card S4 é determinístico (P0); LLM não entra

Cap rate, benchmarks, alertas e gap de otimização são **pure compute** a
partir do payload E5. Não há narrativa interpretativa gerada por LLM
neste card. Interpretação contextual ("manter, otimizar, desinvestir")
vai para o **Parecer do Planejador** (E6, [[ADR-199]]) — que tem persona,
sigilo metodológico §13 e gating Free/Premium. Card S4 alimenta o
parecer; não tenta substituí-lo.

### D4 — Tabela por imóvel é P0 (must-have v1) quando há ≥2 imóveis

Sem quebra por imóvel, a média esconde o imóvel ruim e o card volta a
ser "superficial". A tabela revela a alavanca acionável (qual contrato
está com reajuste pendente, qual imóvel destoa).

**Imputação de aluguel por imóvel** segue cascade de fontes definida em
D9 (Informe → IRPF → E4 → fallback agregado). Onda 1 do plano operacional
([PLAN-s4-real-estate-enrichment](../plan/S4_REAL_ESTATE_ENRICHMENT/_README.md))
audita empiricamente qual fonte aplica a cada workspace; Onda 0.5 ataca a
implementação do parser de Informe estruturado (caminho privilegiado).

### D5 — Concentração imobiliária como métrica de primeira classe

`concentracao_imobiliaria_pct = imoveis_investimento / patrimonio_liquido_total × 100`.
Aparece como badge no header da seção. **Alerta default >40%** (regra
Perini/AUVP — concentração de classe ilíquida desbalanceia carteira).
Threshold configurável via `WorkspaceContext.config_overrides`
([[ADR-134]]).

### D6 — Defaults configuráveis (vacância, manutenção, IR efetivo)

Defaults em `config/pipeline.json` (ou `config/real_estate.json` novo),
override por workspace via [[ADR-134]] `ConfigStore`:

| Parâmetro | Default | Range típico | Justificativa |
|---|---|---|---|
| `vacancia_pct` | 15% | 5-25% | Média BR mercado residencial (Secovi/FIPE); urbano premium pode ser <10%. Empírica vence default quando Informe traz `meses_locado` (cascade D9). |
| `manutencao_pct` | 1% valor/ano | 0,5-3% | Gradação por idade/tipo: novo <10a 0,5% · médio 1% · alto padrão/tombado 2-3%. Inclui CAPEX recorrente (pintura, reforma estrutural), não só zelador. |
| `ir_carne_leao_aliquota_efetiva` | derivado IRPF | — | Calculado pelo `irpf_analyzer.py:286` (alíquota **marginal** do bucket `rendimentos_pf`, **não** média do contribuinte). Fallback **27,5%** se IRPF ausente — viés conservador para ICP HENRY/UHNW (tipicamente topo da tabela). |
| `concentracao_alerta_pct` | 40% | 30-60% | Perini sugere ≤40% em uma classe ilíquida; AUVP idem. |
| `spread_critico_pct_do_benchmark` | **70%** | — | Gatilho `spread_critico` (snapshot, não temporal): `cap_rate_liquido < 70% × cdi_liquido` **E** `concentracao > 30%`. 50% seria frouxo demais (cap rate 4,5% vs CDI líq 8,7% = 51% → não disparava); 70% pega cap rate 5% / CDI 8,7% = 57% → dispara. Calibrar empiricamente após Onda 1. |
| `valor_imovel_origem` | `irpf` | `irpf` / `mercado` | IRPF carrega imóvel pelo **custo histórico** — cap rate sobre imóvel antigo fica inflado. Override `valor_mercado_brl` por imóvel via [[ADR-134]] elimina viés quando informado. |

Componentes IPTU/condomínio são **observados** (não defaults) — vêm
das despesas categorizadas em E4 (categorias `moradia` filtradas por
imóvel quando matching disponível; senão, valor agregado).

### D7 — Gating Free vs Premium (alinhado a [[ADR-208]])

| Bloco do card | Free | Premium |
|---|---|---|
| Hero (cap rate líq + 3 benchmarks + `spread_brl_anual`) | ✅ | ✅ |
| Concentração imobiliária (badge + alerta) | ✅ | ✅ |
| Tabela por imóvel | ❌ (teaser "Detalhe por imóvel no Premium") | ✅ |
| Bloco de ação (gap de otimização quantificado) | ❌ | ✅ |

Decisão alinhada com framework de gating estabelecido para o parecer
([[ADR-208]]) — diagnóstico é Free, drill-down é Premium.

### D8 — Empty states em 3 níveis (consome classificação de [[ADR-215]])

- **0 imóveis de investimento** → seção S4 inteira ocultada via
  `enabled` condicional no codegen ([[ADR-076]]); não polui relatório.
- **Apenas residência principal** → tratada como 0. [[ADR-215]] estabelece
  enum `classification` por imóvel (`residencia_principal`,
  `imovel_uso_familiar`, `investimento_locado`, `investimento_vago`,
  `terreno_improdutivo`). S4 filtra **apenas** `classification ∈
  {investimento_locado, investimento_vago}` — residência e uso familiar
  não entram. Sem essa classificação ([[ADR-215]] em produção), fallback
  conservador: considerar todos `cat_2` (`patrimonio_calculator.py::_split_imoveis`).
- **1 imóvel investimento** → Hero + concentração + ação; tabela suprimida.

### D9 — Hierarquia de fontes para aluguel por imóvel (cascade)

Aluguel mensal por imóvel é a métrica de mais alto leverage do card e a
de qualidade mais variável. Esta ADR fixa **ordem de prioridade**
canônica; o pipeline escolhe a melhor fonte disponível por imóvel:

| Prioridade | Fonte | Cobertura típica | Granularidade | Fidelidade |
|---|---|---|---|---|
| **1** | **Informe de Rendimentos de Imobiliária** (`informerendimentosaluguel`) | Imóveis administrados (~50-80% do mercado HENRY/UHNW) | Por imóvel + por mês + componentes (taxa adm, IPTU, IR retido) | Alta — fonte primária da imobiliária |
| **2** | **IRPF carnê-leão** (`rendimentos_pf` em [[ADR-157]]) | Todos os contribuintes com aluguel declarado | Por pagador (proxy de imóvel via descrição/endereço quando presente) | Média — declarado pelo contribuinte; pode estar agregado |
| **3** | **E4 receitas categorizadas** ("Aluguel") | Workspaces com extrato bancário | Agregado no fluxo bancário; matching por imóvel via heurística | Baixa para por-imóvel; OK para agregado |
| **4 (fallback)** | **Distribuição pro-rata pelo valor IRPF** | Universal | Estimativa | Aproximação — flagged como "estimado" no UI |

**Regras de seleção:**

1. **Por-imóvel:** se Informe presente para o imóvel → usar (#1); senão
   tentar matching IRPF carnê-leão por descrição/CPF pagador (#2); senão
   E4 com heurística (#3); senão pro-rata (#4).
2. **Componentes da fórmula** (D1 acima) seguem cascade independente — IPTU
   pode vir do Informe (#1) **enquanto** taxa de administração vem só do
   Informe (não há fallback aceitável para este componente; sem Informe,
   omitir e degradar tooltip).
3. **Auditabilidade:** cada componente do payload carrega
   `origem ∈ {"informe", "irpf", "e4", "default", "estimado_pro_rata"}`
   para que o card sinalize confiança no tooltip (`origem == "estimado_pro_rata"`
   → badge "estimado"; `origem == "informe"` → sem badge, alto-confiança).

**Implementação do parser de Informe** é objeto da **Onda 0.5** do plano
operacional — schema Pydantic dedicado em `pipeline/llm/schemas/`
(padrão [[ADR-157]] / `e16_irpf_full.py`) + prompt LLM dedicado em
`pipeline/llm/prompts/`. Hoje o doc é classificado e roteado
([`type_classifier.py:85`](../../backend/app/services/classification/type_classifier.py)
+ [`e0_route.py:112-113`](../../scripts/e0_route.py)) mas extraído pelo
schema **genérico** de E2-LLM (lista de transações sem semântica de
"aluguel do imóvel X, taxa adm Y, IR retido Z"). Falta semantizar a
extração.

## Alternativas consideradas

**(A) Manter `yield_imoveis_pct` bruto + adicionar `cap_rate_liquido` como campo opcional.**
Coexistência confunde — qual número aparece no hero? Qual o usuário vê
em destaque? `yield_imoveis_pct` permanece **internamente** (auditoria,
tooltip), mas o card destaca apenas líquido. Descartada por
ambiguidade narrativa.

**(B) "vs CDI" sozinho (proposta inicial do orquestrador).**
Maçã/laranja: CDI nominal pré-IR vs cap rate bruto pré-IR. Mesmo
normalizando (CDI líquido vs cap rate líquido), perde a comparabilidade
real (renda nominal vs renda real) e a classe pareada (FII tijolo).
Revisões `financial-planner` + `product-designer` convergiram em tríade.
Descartada.

**(C) "vs IFIX apenas" (classe pareada estrita).**
Mais honesta como benchmark único, mas perde a leitura de custo de
oportunidade vs renda fixa — pergunta legítima do cliente HENRY/UHNW que
considera realocar para Tesouro/CDB. Tríade cobre os três framings com
custo marginal (mesmo payload, 3 barras vs 1).

**(D) Card com LLM interpretativo (paralelo ao parecer E6).**
Duplicação de prompt + custo + ambiguidade narrativa entre S4 e E6.
[[ADR-199]] / [[ADR-128]] já estabeleceram que interpretação holística
vive **apenas** no parecer. S4 alimenta o parecer; não compete com ele.
Descartada por separação de responsabilidades.

**(E) Manter `NarrativeChartCard` e só adicionar KpiStrip acima
(versão "minimalista" do orquestrador inicial).**
Resolve a quebra título↔conteúdo a custo baixo, mas mantém o card
metodologicamente fraco (yield bruto, sem benchmark líquido, sem
quebra por imóvel). Revisão `financial-planner` foi enfática:
"yield bruto não é métrica válida". Aceitável **só** se Onda 1
descobrir que aluguel por imóvel é inviável **e** orçamento limitar a
v1; nesse caso, vira degradação aceitável da v1 — não a decisão de
princípio.

## Consequências

**Positivas:**

- ✅ Card responde a pergunta clara: "vale a pena manter R$ X em
  imóveis ou realocar?" — em 5s, com 3 benchmarks honestos.
- ✅ Metodologia consagrada (Perini/AUVP/Cerbasi) ancorada em fórmula
  canonizada em `FORMULAS.md`, não em parágrafo narrativo solto.
- ✅ Concentração imobiliária vira métrica de primeira classe (hoje
  é só agregado em `patrimonio_calculator.py`, sem exposição UX).
- ✅ Custo de oportunidade em R$/ano dói mais que pp abstrato; força
  decisão.
- ✅ Determinístico — sem custo LLM, sem cache miss; reproduzível em
  todo `pipeline_run`.
- ✅ Coerência com [[ADR-191]] §D5: comparação só com líquido
  normalizado; benchmarks adequados ao framing da seção (single-class).
- ✅ Defaults configuráveis preservam workspace overrides ([[ADR-134]]).
- ✅ Hierarquia de fontes (D9) permite degradação graceful: workspace
  com Informe → cap rate de alta-fidelidade; sem Informe → IRPF/E4 com
  badge "estimado". Card nunca quebra por ausência de dado.
- ✅ Taxa de administração da imobiliária (componente novo do líquido
  via D9) hoje **não aparece** em nenhum cálculo do produto — semantizar
  o Informe destrava esse dado para fluxo de caixa, score, FORMULAS.

**Negativas:**

- ⚠️ Breaking change no schema do payload E5 (`config/schemas/e5_analysis.schema.json`).
  Adição de chave `real_estate` com `cap_rate_liquido_pct`, `benchmarks`,
  `concentracao_pct`, `imoveis[]`, `alertas[]`. `yield_imoveis_pct` mantido
  como campo legado (deprecated mas presente) por 1 sprint.
- ⚠️ Custo de implementação maior que a proposta inicial: investigação
  de imputação de aluguel por imóvel (Onda 1) pode esticar v1 em 1 sprint.
  Mitigação: fallback explícito em D4.
- ⚠️ Dependência de `market_rates` ter série NTN-B + IFIX populada.
  Hoje só CDI é certo; NTN-B/IFIX precisam ser seeds antes da Onda 2.
  Gate operacional listado no plano.
- ⚠️ Tier gating exige feature flag no aggregate antes da serialização
  (padrão [[ADR-208]]) — coordenação com o code de gating do parecer.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Aluguel por imóvel não é imputável (E4 agrega) | Cascade D9 prioriza Informe → IRPF → E4 → pro-rata. Onda 1 audita cobertura empírica; Onda 0.5 implementa parser de Informe estruturado. Fallback em D4 (tabela só com valor + status) só se todas as 4 fontes falharem. |
| Workspace não tem Informe da imobiliária carregado | Cascade degrada para IRPF/E4; badge "estimado" no UI sinaliza confiança. Telemetria mede % de imóveis com `origem == "informe"` — KPI para campanha de upload do Informe. |
| Schema genérico do E2-LLM ([`e2_llm_extract.py`](../../pipeline/llm/schemas/e2_llm_extract.py)) já extrai informe como lista de transações soltas (sem semântica de aluguel/taxa/IR/imóvel) | Onda 0.5 implementa schema estruturado dedicado; legado coexiste por 1 sprint via flag `use_structured_informe_extractor` enquanto goldens são construídos. |
| Default de vacância/manutenção controverso para imóveis premium | Override por workspace via [[ADR-134]]; documentar em tooltip "valores estimados; ajuste em Configurações". |
| Card vira pitch de venda contra imóvel | Parecer (E6) contextualiza razões legítimas (uso futuro, herança, hedge psicológico) — Cerbasi. Card S4 é diagnóstico; E6 é interpretação. |
| Concentração 40% threshold gera alarme falso (imóvel é estratégico no perfil) | Threshold configurável + texto do alerta neutro ("revisão estratégica recomendada", não "venda imóveis"). |
| Cap rate líquido com IPTU/condomínio observados (E4) divergir de imóvel para imóvel | v1 usa agregado pro-rata pelo valor IRPF; v2 (lane futura) refina com matching por endereço. |

## Gates

- **FORMULAS.md atualizado** com 4 novas fórmulas (`cap_rate_liquido`,
  `cap_rate_bruto`, `concentracao_imobiliaria`, `spread_vs_benchmark`)
  + tabela de defaults — gate da Onda 0 do plano operacional.
- **Schema E5 com `additionalProperties: true`** ([[ADR-199]] PR-1 já
  cobriu) — adição de chave `real_estate` é compatível.
- **`config/schemas/e5_analysis.schema.json`** atualizado e validado pelo
  hook `DBArtifactStore.write` ([[ADR-212]]).
- **Snapshot OpenAPI** atualizado (`make update-openapi-snapshot`)
  quando endpoint de relatório expuser novos campos.
- **Testes determinísticos** em `tests/test_e5n_real_estate_metrics.py`:
  - cap rate líquido com componentes conhecidos
  - tríade de benchmarks normalizada
  - alerta de concentração no threshold
  - empty states (0/1/N imóveis; só residência principal)
- **Frontend unit** em `frontend/tests/components/RealEstateYieldCard.test.tsx`
  para variants + tier gating + a11y.
- **`market_rates` populado** com NTN-B + IFIX antes da Onda 2 (Onda 0
  audita e seed se necessário).

## Referências

- [[ADR-191]] — Card Rentabilidade (TRS) — precedente que esta ADR
  diferencia (carteira inteira vs single-class).
- [[ADR-215]] — Classificação de uso econômico de imóveis via override
  DB (enum `classification`); upstream do filtro de S4 (D8). ADR-216
  consome a classificação produzida; ADR-215 não depende de ADR-216.
- [[ADR-157]] — E1.6 extract_irpf_full; padrão de schema Pydantic +
  prompt LLM dedicado que a Onda 0.5 espelha para Informe de Imobiliária.
- [[ADR-145]] — Taxonomia patrimonial canônica (cat_1 vs cat_2); fonte
  metodológica da separação residência/investimento (alinhada com [[ADR-215]]).
- [[ADR-143]] — `methodology=code` (cap rate é regra universal, vive em
  docstring + FORMULAS.md).
- [[ADR-090]] — proibição `float` para dinheiro (cap rate calc usa `Decimal`).
- [[ADR-097]] D3 — services recebem value objects (`RealEstateConfig` tipado).
- [[ADR-076]] — codegen do report layout (seção S4 muda de `chart` para `card`).
- [[ADR-134]] — `ConfigStore` para overrides por workspace.
- [[ADR-135]] — `market_rates` global versionado por data (CDI/NTN-B/IFIX).
- [[ADR-199]] / [[ADR-208]] — Parecer planejador como camada de
  interpretação (não compete com S4); framework de gating Free/Premium.
- Plano operacional: [PLAN-s4-real-estate-enrichment](../plan/S4_REAL_ESTATE_ENRICHMENT/_README.md).
- Co-design: `financial-planner` + `product-designer` (sessão 2026-05-15).
