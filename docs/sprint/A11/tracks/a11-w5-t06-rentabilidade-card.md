---
id: TRACK-a11-w5-t06-rentabilidade-card
type: track
title: "Card S3 Rentabilidade — rebrand TRS efetiva + enriquecimento + cobertura essencial"
lane: "[[A11.w5]]"
sprint: A11
plan: PLAN-platform-review
status: ready
created_at: "2026-05-11"
agent_role: data-engineer (PR-A lead) + product-designer (PR-B lead)
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/report
  - area/frontend
  - area/methodology
  - phase/a11
---

# Track — Card S3 Rentabilidade (rebrand TRS + enriquecimento)

> **Lane ID:** A11.w5 (Frontend + Methodology) · Task T06
> **Branch prefix:** `agent/a11-w5-t06-rentabilidade-card/<yyyyMMdd-HHmm>`
> **Depende de:** A11-W5-T05 PR-A mergeado em `main` (consolida shape de
> `PassiveIncomeResult`).
> **Paralelo com:** A11-W5-T01 (a11y), A11-W5-T02 (Recharts), A11-W5-T03
> (MonetaryValue), A11-W5-T04 (ADR-161 enrichment — adiciona consumer
> de TRS, sem conflito de arquivo).
> **Conflita com:** outra sessão `agent/a11-w5-t06-*` ativa.
> **Sprint:** A11
> **Time-box:** ≤3 dias eng (1,5d backend+doc + 1,5d frontend).
> **Owners:** `data-engineer` (PR-A); `product-designer` (PR-B).
> **Decisão arquitetural:** [[ADR-191]]
> **Inputs consolidados:** revisão multi-agente 2026-05-11
> (`product-designer` + `financial-planner` + `senior-cto` +
> `data-engineer` + `product-manager`)
> **Fonte de verdade das regras:** [CLAUDE.md](../../../../CLAUDE.md)

---

## 1. Objetivo

Resolver 3 problemas independentes no card "Rentabilidade" da seção S3
do relatório ([S3InvestimentosSection.tsx:91-100](../../../../frontend/src/components/report/sections/S3InvestimentosSection.tsx)):

1. **Rótulo enganoso** → renomear UI para refletir TRS efetiva (yield
   de renda passiva), não retorno total.
2. **Conteúdo incompleto** → enriquecer DTO com ano-base IRPF,
   defasagem, meta 5%, comparativo, status, **nova métrica derivada**
   "cobertura de despesa essencial via renda passiva" (tradução
   Cerbasi).
3. **Drift spec ↔ código** → implementar `custo_essencial_mensal_brl`
   que [FORMULAS.md linha 32](../../../reference/FORMULAS.md) promete mas
   nenhum cálculo entrega hoje (`EmergencyReserveCalculator` usa total).

**Não-objetivos (decisões fechadas — não rediscutir):**

- Não comparar com CDI no card (yield ≠ taxa nominal RF). Justificativa
  em [[ADR-191]] §D5.
- Não calcular retorno total da carteira (yield + capital gain). Sem
  NAV histórico; fora de escopo. [[ADR-191]] §D5.
- Não renomear `rentabilidade_pct` no domínio (custo alto, ganho
  cosmético). [[ADR-191]] §D2.
- Não corrigir `EmergencyReserveCalculator` nesta lane (risco de
  regressão em `score.componentes`). Abrir issue separada que reutilize
  o helper novo.
- Não tocar `passive_income_calculator.py` (escopo W5-T05).
- Não tocar regra `renda_passiva_real_baixa` (escopo W5-T04).

## 2. Por que esta lane existe

Usuário relatou que o card "Rentabilidade" não comunica nada — só um
número solto sem ano-base, sem comparativo, sem indicação do que é
medido. Revisão multi-agente 2026-05-11 (`product-designer` +
`financial-planner` em paralelo, depois `senior-cto` + `data-engineer`
+ `product-manager` em paralelo) confirmou:

- `product-designer`: card precisa de hierarquia de informação completa
  (KPI hero, comparativo, contexto temporal, empty state).
- `financial-planner`: o número exibido é **TRS efetiva**, não
  rentabilidade total. Comparar com CDI induz mau comportamento.
  Métrica "cobre N% das despesas essenciais via renda passiva" (tradução
  Cerbasi) dá significado real ao número.
- `senior-cto`: rename interno custa caro; estender DTO em estrutura
  aninhada é mais limpo. ADR `Proposto` antes do PR.
- `data-engineer`: a base de "despesa essencial" **já está
  especificada** em `scoring.json:reserva_emergencia._base_calculo.categorias_in`
  mas não implementada — gap fechável em ~50 LOC.
- `product-manager`: 2 PRs sequenciais (não 3); P2 dentro do W5;
  bloqueado por T05 PR-A.

Ver [[ADR-191]] para racional arquitetural completo + decisões "não
fazer" com justificativas.

## 3. Decomposição

### PR-A — Backend domain + schema + doc canônica

Owner: `data-engineer`. Time-box: ~1,5 dia.

#### 3.A.1. Helper `compute_custo_essencial_mensal`

- Novo módulo `pipeline/domain/services/essential_expense_calculator.py`
  com helper puro:
  ```python
  def compute_custo_essencial_mensal(
      despesas_por_categoria: Mapping[str, Decimal],
      categorias_in: Sequence[str],
  ) -> Decimal:
      """Soma despesas mensais médias das categorias canônicas essenciais."""
  ```
- Lista canônica `categorias_in` lida via `ConfigStore` de
  `scoring.json:reserva_emergencia._base_calculo.categorias_in`
  (já existe — 9 categorias).
- TODO docstring: impostos não-PJ (IPTU, IPVA, IRPF) ainda não cruzam
  com origem do lançamento — v1 documenta limitação; lane separada
  endereça.

#### 3.A.2. `FluxoCaixaEnricher` popula essencial

- `pipeline/domain/services/fluxo_caixa_enricher.py` passa a expor
  `despesa_mensal_essencial_brl: Decimal` no shape do fluxo enriquecido.
- Additive — campos legados preservados.

#### 3.A.3. `RentabilidadeConfig` + extensão `RatiosCalculator`

- Novo value-object frozen dataclass em
  `pipeline/domain/services/ratios_calculator.py` (ou módulo próprio se
  ficar volumoso):
  ```python
  @dataclass(frozen=True)
  class RentabilidadeConfig:
      meta_pct: Decimal = Decimal("5.0")  # Perini default
  ```
- Injetado em `RatiosCalculator.__init__` (não em `.calculate(...)`),
  alinhado com [[ADR-097]] §config tipada.
- `_Window` ganha `despesa_mensal_essencial_brl: Decimal` populado por
  `_resolve_window` lendo o fluxo enriquecido.
- `FinancialRatios` ganha campo aninhado:
  ```python
  @dataclass(frozen=True)
  class RentabilidadeRatio:
      valor_pct: Decimal | None
      ano_base: int | None
      defasagem_meses: int | None
      meta_pct: Decimal
      cobertura_despesa_essencial_pct: Decimal | None
      status: Literal["ok", "sem_irpf", "gerador_zero", "sem_dados_essencial"]
  ```
- `to_legacy_dict()` serializa como `rentabilidade: {...}` aninhado;
  campo flat `rentabilidade_pct` permanece como atalho (back-compat).

#### 3.A.4. Schema E5

- `config/schemas/e5_analysis.schema.json`: declarar `ratios.rentabilidade`
  como objeto com 6 properties tipadas. `additionalProperties` segue
  política atual do schema (modo `warn`, débito W6-T01).

#### 3.A.5. Doc canônica `FORMULAS.md` §TRS efetiva

- Adicionar seção em [docs/reference/FORMULAS.md](../../../reference/FORMULAS.md):
  - Fórmula TRS efetiva (`renda_passiva_anual / patrimonio_gerador × 100`)
  - Meta 5% (referência consagrada — sem citar Perini por nome, §13
    COPY_GUIDELINES)
  - Relação com Trinity 4% (SWR, conceito distinto — não comparáveis
    direto)
  - Cobertura essencial via renda passiva (nova métrica derivada)
- Validar com `dev/validate_frontmatter.py` se a seção tocar frontmatter.

#### 3.A.6. Testes

- `tests/unit/pipeline/test_essential_expense_calculator.py` (novo) —
  lista completa, parcial, vazia, categoria desconhecida (ignorar).
- `tests/unit/pipeline/test_ratios_calculator.py` — happy path com
  `rentabilidade` populada; 3 status (`sem_irpf`, `gerador_zero`,
  `sem_dados_essencial`); defasagem ≥18m → status flagado.
- `tests/test_e5_golden_execution.py` — não exige regen (validação via
  schema, additive não quebra modo warn). Confirmar via rerun.

#### 3.A.7. Snapshot OpenAPI

- `make update-openapi-snapshot` + commit do diff. Esperado: campo novo
  aninhado em DTO de leitura.

### PR-B — Frontend card S3

Owner: `product-designer`. Time-box: ~1,5 dia.

#### 3.B.1. Re-layout do card

- Promover para `md:col-span-4` (full-width).
- KPI hero (TRS efetiva valor + unidade `% a.a.`) com cor semântica
  (`var(--semantic-gain|attention|loss)`) por status vs meta.
- Linha de comparativo: meta 5% (sem CDI, sem Trinity — [[ADR-191]] §D5).
- Métrica derivada: "cobre N% das despesas essenciais via renda passiva"
  quando `cobertura_despesa_essencial_pct != null`.
- Rodapé: ano-base IRPF + defasagem em meses.
- Empty state honesto quando `status != "ok"`:
  - `"sem_irpf"`: "Indicador indisponível. Carregue o IRPF mais recente
    em Documentos → Adicionar."
  - `"gerador_zero"`: "Sem patrimônio gerador identificado nesta carteira."
  - `"sem_dados_essencial"`: card mostra TRS mas omite cobertura, com
    nota "Categorização incompleta — cobertura essencial não disponível."
- Badge "Dado defasado" quando `defasagem_meses > 18`.

#### 3.B.2. Copy + a11y

- §13 COPY_GUIDELINES (sem nomear Perini/Trinity em copy user-facing).
- Aria-labels, contraste AA, tabular-nums via `<MonetaryValue/>` quando
  aplicável (% também respeita font-mono tabular).
- Sem hex literal — só design tokens.

#### 3.B.3. Testes

- Unit (`vitest`): branches por status, branch defasagem >18m, branch
  cobertura null.
- E2E `@critical`: render do card em light + dark; export PDF cobre o
  mesmo redesign (renderer único pós-[[ADR-129]]).

## 4. Critério de aceite

- [ ] [[ADR-191]] flippa para `Decidido (A11.W5)` no merge do PR-A.
- [ ] PR-A mergeado em `main` (CI verde, commit-merge confirmado).
- [ ] PR-B mergeado em `main` (CI verde, commit-merge confirmado).
- [ ] `FinancialRatios.rentabilidade` (nested) presente no DTO; campo
      flat `rentabilidade_pct` preservado.
- [ ] Schema E5 declara `ratios.rentabilidade` com 6 properties tipadas.
- [ ] `compute_custo_essencial_mensal` coberto por unit tests.
- [ ] `RatiosCalculator` coberto por unit tests cobrindo 4 status.
- [ ] Card S3 rebrandeado (UI), full-width, com KPI hero + comparativo
      meta + cobertura essencial + rodapé ano-base/defasagem + empty
      state por status.
- [ ] [FORMULAS.md §TRS efetiva](../../../reference/FORMULAS.md)
      publicado.
- [ ] Empty state branch `defasagem_meses > 18` coberto por teste
      unitário.
- [ ] Sem regressão em `pytest tests -q`, `pytest backend/tests -q`,
      `npm test -- --run`, `npm run test:e2e -- --grep @critical`.
- [ ] Snapshot OpenAPI atualizado (`backend/tests/test_openapi_snapshot.py`
      verde após `make update-openapi-snapshot`).

## 5. Riscos e dependências

### 5.1. Dependências hard

- **A11-W5-T05 PR-A mergeado** — consolida shape de `PassiveIncomeResult`
  (especialmente `ano_referencia_irpf` e `defasagem_meses`, que esta
  lane consome via passthrough). Sem T05 PR-A, refazer ordem de
  campos.

### 5.2. Coexistências sem conflito

- **A11-W5-T04** (ADR-161 enrichment) adiciona consumer rule
  `renda_passiva_real_baixa` que lê TRS — não modifica o produtor.
  Paralelizável.
- **A11-W5-T01..T03** tocam outros arquivos. Paralelo.

### 5.3. Débitos identificados (lane separada, não fixar aqui)

- `EmergencyReserveCalculator` em
  [reserva_emergencia_calculator.py:87](../../../../pipeline/domain/services/reserva_emergencia_calculator.py)
  usa `despesa_mensal_media` total quando metodologia exige
  essencial. Fix reutiliza `compute_custo_essencial_mensal` desta lane.
  Risco de regressão em `score.componentes[]` — isolar em PR próprio.
- `despesa_essencial_historico` (12 meses) consumido pela regra
  `lifestyle_creep` ([[ADR-161]]) só existe em fixtures de teste; snapshot
  real não popula. Pode entrar junto com o fix acima.
- Impostos não-PJ (IPTU, IPVA, IRPF) em `categorias_in` exigem
  cruzamento com origem do lançamento — v1 documenta limitação.

### 5.4. Riscos baixos

- Card é read-only; nenhum cálculo crítico de saúde financeira muda.
- Modo warn de schema E5 tolera campo novo; W6-T01 strict cutover é
  futuro.
- Empty state cobre todos os casos não-felizes — sem `null` vazando
  pra UI.

## 6. Como executar

### 6.1. Pickup

```bash
git fetch origin
git checkout -b agent/a11-w5-t06-rentabilidade-card/$(date +%Y%m%d-%H%M) origin/main
```

### 6.2. Pré-condições (checar antes de codar)

- [ ] [[ADR-191]] está em `main` com `status: Proposto`.
- [ ] T05 PR-A está em `main` (`git log origin/main --oneline | grep "A11.W5.T05"`).
- [ ] `python3 dev/validate_frontmatter.py` verde.

### 6.3. Execução por PR (sequencial)

1. Implementar PR-A (backend+doc) inteiro localmente.
2. Rodar `pre-commit run --all-files` + `pytest tests -q` + `pytest backend/tests -q`.
3. Rebase em `origin/main`, push, abrir PR.
4. Aguardar merge.
5. Pull main, criar nova branch para PR-B.
6. Implementar PR-B (frontend) lendo shape novo.
7. Rodar `cd frontend && npm test -- --run` + `npm run test:e2e -- --grep @critical`.
8. Rebase, push, abrir PR.

### 6.4. Pós-merge

- Flippar [[ADR-191]] para `Decidido (A11.W5)` no PR-A.
- Abrir issue: "EmergencyReserveCalculator usa despesa total ao invés de
  essencial" (referência §5.3).
- Atualizar [docs/sprint/A11/lanes/A11-w5-frontend-methodology.md](../lanes/A11-w5-frontend-methodology.md)
  marcando T06 ✅ ao final.

## 7. Referências

- **ADR:** [[ADR-191]] — Card Rentabilidade expõe TRS efetiva, não retorno total
- **ADRs relacionadas:** [[ADR-076]] (design tokens), [[ADR-090]] (Money),
  [[ADR-129]] (renderer único React), [[ADR-143]] (rules-as-code),
  [[ADR-161]] (regras canônicas de suggestion)
- **Sprint:** [[MOC-sprint-a11]]
- **Wave:** [docs/sprint/A11/lanes/A11-w5-frontend-methodology.md](../lanes/A11-w5-frontend-methodology.md)
- **Plano canônico:** [docs/plan/PLATFORM_REVIEW/_README.md](../../../plan/PLATFORM_REVIEW/_README.md)
- **Code paths:**
  - Frontend: `frontend/src/components/report/sections/S3InvestimentosSection.tsx:91-100`
  - Domínio: `pipeline/domain/services/{ratios_calculator,passive_income_calculator,fluxo_caixa_enricher}.py`
  - Schema: `config/schemas/e5_analysis.schema.json`
  - Doc: `docs/reference/FORMULAS.md` (§TRS efetiva — a criar)
  - Config base: `config/scoring.json:reserva_emergencia._base_calculo.categorias_in`
- **Inputs revisão:** sessão 2026-05-11 (5 especialistas paralelos)
