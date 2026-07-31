---
id: A40.l3
type: lane
title: "Janela canônica: todo número rotulado 12m lê janela_12m"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l3-janela-canonica-fluxo
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/frontend
  - area/pipeline
---

# A40.l3 — `janela-canonica-fluxo` (RV3-02 · causa-raiz)

## Problema

`fluxo_caixa.janela_12m.*` tem **zero consumidores** em `frontend/src`
(`rg janela_12m frontend/src` → 0). Todo número de fluxo na tela **e no PDF** vem
do bloco de janela `full`, enquanto o valor canônico de 12 meses existe no payload
e nunca é lido.

Consequência visível: o gráfico declara a janela do slice renderizado
(`FluxoMensalChart.tsx:76-92`) e cita agregado de janela `full` na mesma frase. O
`isPrint` força a janela curta, então **o PDF carrega a mesma inconsistência**.

Não é inconsistência a decidir — é **não-conformidade com invariante já escrito**:
a janela canônica para ratios/KPIs já está declarada, e `full` já está restrito a
"apenas com rótulo". Isso muda o custo de fechar (é conformidade, não co-design) e
a guarda (gate de contrato, não ADR nova). RV3-16 e RV3-17 são a mesma violação.

## Escopo

> **Quatro itens deste escopo foram corrigidos após medição no DOM e no PDF
> reais** — a regra geral abaixo é mais estrita que a [[ADR-306]] e o item do
> Consumo Consciente saiu para a [[A40.l15]]. Leia §"Correção de escopo" no fim
> do arquivo **antes** de auditar a lane.

- `FluxoMensalChart.tsx` — `buildContext` deriva do **slice renderizado** ou
  consome `fluxo_caixa.janela_12m.*` quando a janela é 12m.
- `conclusionUtils.ts` (builder `fluxo_mensal` + `SECTION_SUMMARIES.S2`) — mesma
  correção, e passa a **rotular** a janela.
- ~~`ConsumoConscienteCard.tsx` — consome `total_pontuais_janela` quando
  `janela != full`~~ → **movido para [[A40.l15]]** (mudança de domínio, exige
  co-change no E5). Aqui o card só ganha **rótulo impresso** por base.
- Regra geral (revista): **nenhum texto cita agregado sem declarar a base.**
  Mensalização lê `janela_12m`; composição pode ficar em full **rotulado** — é o
  que a [[ADR-306]] D1 diz, e `janela_12m` não tem contraparte para `por_fonte`,
  `receita_por_natureza` ou `tabela_receitas`.

## Critério de aceite

- `rg 'janela_12m' frontend/src` retorna **> 0**.
- Teste de contrato de janela com fixture onde `janela_12m.*` ≠ bloco `full` por
  valor detectável: todo componente cujo rótulo declara 12m exibe o valor de
  `janela_12m`. **Hoje esse teste falharia** — é o sinal de que ele mede o certo.
- **Verificação renderizada** — spec em `frontend/tests/e2e/reports/`, usando
  `mockReportPage(page, { fixture })` + `waitForReportReady`. A fixture precisa ter
  `janela_12m.*` **divergente** do bloco `full` por valor detectável; se nenhuma das
  5 variantes representar isso, **a lane adiciona uma** (PII-zero, versionada em
  `frontend/tests/e2e/fixtures/reports/` — vale como regressão permanente). A perna
  de PDF reusa o padrão de `print.@critical.spec.ts`.
- Declarar o sinal esperado do delta — atenção: a correção move a sobra exibida
  **para cima**, não para baixo (a legenda de 44m *subestimava* a sobra dos 12m).

## Guarda anti-regressão

Teste de contrato de janela permanente: fixture com os dois blocos divergentes +
assert por componente rotulado. Impede que a próxima feature volte a ler o
agregado longo por conveniência.

**Reforço pós-medição (2026-07-31).** Assert por componente **não basta** —
enumeração não detém o componente que ainda não existe (foi exatamente assim
que `ReceitaDespesaMensalChart` passou). A guarda tem quatro camadas:

1. **Regra ESLint `no-restricted-syntax`** (`frontend/eslint.config.mjs`) sobre
   o **acesso** aos campos com base temporal declarada, com allowlist só para
   `report/utils/fluxoJanela.ts` (o seletor). Roda no step ESLint de
   `frontend-checks` (job já em `all-green.needs`), custo ~0. Provado com
   componente violador temporário: **5 erros** — acesso por ponto, por string
   literal, por destructuring, e os dois campos de headline do hero
   (`taxa_poupanca_recorrente_pct`, `taxa_poupanca_total_pct`).
   **Limite honesto:** a regra **não** detém componente que deriva a própria
   média de uma série já renderizada — foi exatamente o caso do
   `ReceitaDespesaMensalChart`, que somava `receita_datasets`/`despesa_datasets`
   e dividia por `data.length`, sem tocar campo restrito. Essa classe cai na
   camada 2. Afirmar o contrário no comentário do gate seria a própria classe de
   defeito desta sprint (promessa de garantia inexistente).
2. **Invariante de SEÇÃO** em `janelaCanonica.contract.test.tsx`: renderiza
   `S2FluxoCaixaSection` composta e exige (a) que S2 **não** emita taxa de
   poupança própria (a canônica vive no hero, S1), (b) todo valor `X/mês` da
   seção pertencente ao bloco `janela_12m` — medido: `{92.000, 81.000}` e nada
   mais —, (c) um único número de "quanto sobra" na seção, e (d) que **todo**
   `[data-chart-conclusion]`/`[data-chart-context]` declare a base.
3. **Step de render bloqueante** em `frontend-checks`, gateado por
   `needs.changes.outputs.report` (`ci.yml`) — não por label. `frontend-e2e`
   roda por label `e2e`, ficou skipped em 12/12 runs recentes e **não** está em
   `all-green.needs`: vermelho lá não impede merge. O step passa
   `PLAYWRIGHT_WEB_SERVER_COMMAND=npx next dev --turbopack`: `npm run dev`
   dispara `predev` → `codegen:check` → `python3 …`, e `frontend-checks` é
   node-only. Sem esse override o gate **falharia sempre** por falta de
   setup-python — medido lendo o job, não inferido.
4. **Smoke por fixture** — `janela-divergente` entrou em `FIXTURES` de
   `sections.fixtures.smoke.visual.spec.ts`. É a única fixture com
   `fluxo_caixa.janela_12m` + `consumo_consciente` populados; sem ela o smoke
   por variante nunca renderizava os componentes que esta lane corrige.

**Buraco conhecido da camada 3.** O filtro `changes.report` cobre
`frontend/src/components/report/**`, `frontend/src/types/report*.ts`,
`frontend/tests/e2e/{reports,fixtures/reports}/**` e o próprio `ci.yml` — mas
**não** `config/prompts/chart_conclusions.yaml`. PR que só edite o template do
YAML não dispara o step de render. Impacto real é baixo (o YAML não é lido em
runtime; `conclusionUtils.ts` duplica a lógica e
`dev/check_chart_conclusion_parity.py` roda no pre-commit), mas o buraco existe e
fica registrado em vez de coberto por otimismo.

## Correção de escopo (obrigatório para o painel)

Quatro correções ao escopo original. Onde lane e ADR divergiram, **a ADR venceu**.

1. **A regra geral do escopo é mais estrita que a [[ADR-306]] — e inexequível.**
   "Nenhum texto de chart cita agregado de janela diferente da renderizada"
   proíbe o que a ADR permite e exige o que o payload não oferece:
   `fluxo_caixa.janela_12m` **não tem contraparte** para `por_fonte`,
   `receita_por_natureza` nem `tabela_receitas` (medido no substrato versionado:
   esses três, mais `janela_12m` e `por_fonte_detalhado` e
   `receita_despesa_mensal_detalhado`, existem só no bloco top-level). Cumprir a
   regra literalmente obrigaria a apagar a composição de receitas do relatório.
   **Regra vigente = a da ADR:** mensalização (ratios/KPIs/médias por mês) lê
   `janela_12m`; agregado de composição pode ficar em full **desde que
   ROTULADO**. Medido no DOM: os 8 textos derivados do relatório declaram base —
   4 citam a janela de 12m documentados, 2 a janela exibida (range), 2 todo o
   período analisado.
2. **O item 3 do escopo (Consumo Consciente) saiu desta lane.**
   "Consome `total_pontuais_janela` quando `janela != full`" é mudança de domínio
   no que a família vê e exige três co-changes no E5 + rebaseline de snapshot.
   Virou a lane **A40.l15**
   (`docs/sprint/A40/lanes/A40-l15-consumo-consciente-base-janela.md`), com a
   análise do `financial-planner` preservada. Aqui o card entrega o que a
   [[ADR-306]] já exige e nada além: KPI de pontuais + equivalente no acumulado
   **full ROTULADO** (mesma base da prosa que o E5 emite ⇒ card internamente
   coerente), folga + teto rotulados com a janela da folga. Duas bases, dois
   rótulos impressos, zero número sem base.
3. **O escopo listava 3 sites; o defeito estava num quarto.**
   `ReceitaDespesaMensalChart` mensalizava a série inteira (36 meses) **sem
   rótulo** e emitia uma **segunda** taxa de poupança, ao lado do texto
   corrigido, na mesma seção. Medido no DOM e no PDF. Corrigido: o chart
   totaliza a **janela exibida**, rotulada, sem mensalizar e sem taxa.
   Consequência de método: a lane pediu "assert por componente rotulado" e é
   justamente esse formato que não detém o site não-listado — daí as camadas 1 e
   2 da guarda acima.
4. **A verificação renderizada estava declarada como coberta por CI e não
   estava.** `frontend-e2e` é opt-in por label. O gate mudou de lugar (step em
   `frontend-checks`). Precisão obrigatória no critério: a superfície de print é
   assertada por **conteúdo** (`emulateMedia({media:"print"})`); rasterização de
   PDF segue label-only em `frontend-print-visual` e é **cega** a diferença de
   valor (`MAX_DIFF_PIXELS = 500` não distingue R$ 4.000 de R$ 11.000 em 12px).

### Sinal do delta — medido nos dois substratos

O critério de aceite pedia "declarar o sinal esperado do delta" e afirmava
**↑**. Medido, o sinal depende do substrato:

- **Substrato real versionado** (`backend/tests/snapshots/dogfood_view_model.json`):
  os dois blocos de `fluxo_caixa` compartilham **11 chaves**, e entre elas **só
  `janela` difere em valor** (`"full"` vs `"12m"`) — nenhum campo monetário
  divergente, porque `janela_meses = 1` faz a janela de 12m coincidir com o
  período completo. Δ monetário = **0** ⇒ sinal **`=`**.
  A divergência real desse payload é de **presença**, não de valor: 6 chaves
  existem só no bloco de 12m (`despesa_consumo`, `n_meses`, `periodo`,
  `taxa_poupanca_recorrente`, `taxa_poupanca_total`, `transferencia_patrimonial`)
  e 6 só no top-level (`janela_12m`, `por_fonte`, `por_fonte_detalhado`,
  `receita_despesa_mensal_detalhado`, `receita_por_natureza`, `tabela_receitas`).
  É por isso que a lane vale mesmo com Δ = 0: o bloco full **não consegue**
  fornecer a taxa ex-aporte canônica — quem lê full ou omite a taxa ou a
  recomputa errado. (A versão anterior desta seção dizia "os dois blocos diferem
  em UM campo", sem qualificar "entre as chaves comuns" — falso como escrito.)
- **Fixture `janela-divergente.json`** (construída para divergir): receita
  exibida 40.000 → 92.000/mês e despesa 36.000 → 81.000/mês ⇒ **↑** em ambos —
  mas por construção, não por propriedade do dado real.

Consequência: **nenhuma das duas serve como evidência de que a correção move o
número na base do cliente para um lado específico.** A afirmação honesta é
"elimina base mista e habilita a taxa canônica"; o efeito numérico é
workspace-dependente.

Efeito colateral medido do `janela_meses = 1`: a copy rendia "os últimos 1
meses documentados" — bug de plural **alimentado por dado**, não hipótese, e
`pluralMeses()` sozinho não o resolve (concorda o substantivo, não o artigo nem
o particípio). Corrigido em `describeMesesDocumentados()`, que concorda a frase
inteira ("o último mês documentado"), com assert de **igualdade exata** — o
assert anterior era `toContain("1 mês documentado")` e passava com a string
quebrada.

### Assimetria de rótulo que esta lane NÃO fecha (handoff)

Medido no substrato versionado: **8 blocos** do view-model trazem a chave
`janela` (`consumo_consciente`, `equilibrio_cerbasi`, `fluxo_caixa`,
`fluxo_caixa.janela_12m`, `orcamento_prospectivo`, `passive_income`, `ratios`,
`reserva_emergencia`). Depois desta lane:

- **4 com rótulo IMPRESSO:** `ratios` (badge no hero), `consumo_consciente`
  (4 badges), `fluxo_caixa` + `fluxo_caixa.janela_12m` (cláusula de base na
  prosa dos charts e no resumo de S2).
- **1 só com tooltip:** `reserva_emergencia` — `InfoTooltip` em
  `ReservaEmergenciaCard`, que por [[ADR-306]] §Emenda A40.l3 **não conta** como
  rótulo (não imprime no PDF).
- **3 sem rótulo algum:** `equilibrio_cerbasi`, `orcamento_prospectivo` e
  `passive_income` (este consumido em `S7IndependenciaSection` como `data.n`, com
  `janela: "irpf"` nunca exposto).

Os 4 restantes **não são desta lane** (escopo é fluxo de caixa). Registrado como
handoff explícito para não passar por cobertura completa.

### Follow-ups registrados (fora do escopo desta lane)

- **[[A40.l15]] — base do KPI de gastos pontuais** (spun off deste escopo, ver
  correção 2 acima): card fala em 4 bases temporais; exige 3 co-changes no E5 +
  rebaseline de snapshot + sinal de delta próprio.
- **Assimetria de FILTRO entre KPI e lista** (ameaça de credibilidade maior que
  a escolha de base): `consumo_consciente_calculator._collect_candidates`
  filtra só categoria + threshold, enquanto o endpoint `/reports/consumo-pontuais`
  aplica `InternalTransferDetector`. O total do KPI pode conter PIX entre contas
  próprias que a lista exclui — a família vê um total que **não encontra nos
  itens**. Qualquer que seja a janela, KPI e lista precisam do mesmo filtro.
- **Guarda de domínio para janela insuficiente** (decisão nova, pequena):
  `janela: "12m"` com `janela_meses: 1` invalida a copy **e o conselho** —
  `teto_sugerido = despesas_recorrentes_mensal × 1,15` derivado de um mês não é
  recomendação, e o card o exibe em fonte de KPI. Proposta: abaixo de ~6 meses
  documentados, suprimir `teto_sugerido`/`folga_pct` e declarar janela
  insuficiente. É o espírito de D3 na camada de apresentação, ainda não aplicado.
- **Nenhum sinal pós-merge desde 2026-06-15**: `Nightly` está
  `disabled_manually` e o `push: main` foi removido do `ci.yml`, mas
  `ci.yml:36-37` continua afirmando que o `main-smoke` cobre o drift. É drift de
  decisão-vs-realidade mais grave que esta lane (owner-gated: reabilitar só o
  cron diário custa ~84 min/mês).
- **`changes.outputs.report` tinha zero consumidores** desde que a ADR-210
  removeu o auto-trigger de `frontend-visual`. Esta lane passa a consumi-lo; a
  fiação já estava paga.
