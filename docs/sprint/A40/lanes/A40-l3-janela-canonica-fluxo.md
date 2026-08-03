---
id: A40.l3
type: lane
title: "Janela canônica: todo número rotulado 12m lê janela_12m"
sprint: A40
plan: PLAN-report-trust
status: shipped
priority: P0
branch_slug: a40-l3-janela-canonica-fluxo
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
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

> **Cinco itens deste escopo foram corrigidos após medição no DOM e no PDF
> reais** — a regra geral abaixo é mais estrita que a [[ADR-306]], o item do
> Consumo Consciente saiu para a [[A40.l15]] e o defeito apareceu em dois sites
> não listados. **Depois disso, o TEXTO de dois cards (donut de despesas e
> `ReceitaDespesaMensalChart`) também saiu para a [[A40.l15]]** — ver §Residuais.
> Leia §"Correção de escopo" no fim do arquivo **antes** de auditar a lane.

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
   texto derivado que cite agregado (`R$` ou `%`) declare a base.
   **Escopo do invariante:** os dois cards herdados pela [[A40.l15]] (`Despesas
   por Categoria`, `Receita vs Despesa — Mês a Mês`) são excluídos por
   `CARDS_DA_L15` — exclusão **nominal**, com assert de que os dois títulos
   existem na seção (senão a exclusão viraria vácuo em silêncio) e de que a
   remoção tira exatamente 2 cards. Renomear um card devolve o texto ao
   invariante e falha alto.
   `No gráfico: N meses` **não conta** como declaração de base: é a contagem de
   barras renderizadas, e aceitá-la deixava passar texto que declara o desenho e
   não a base do número ("No gráfico: 12 meses. Receita média de R$ 42.667/mês.").
   Provado por mutação: reintroduzir a alternativa no regex derruba o caso
   dedicado. Contrapartida honesta: texto que **não** cita agregado (o ramo
   3M/6M/YTD do `FluxoMensalChart`, que omite a média por não haver bloco
   agregado) não é sujeito do invariante — não há número a rotular.
3. **Step de render bloqueante** em `frontend-checks`, gateado por
   `needs.changes.outputs.report` (`ci.yml`) — não por label. `frontend-e2e`
   roda por label `e2e`, ficou skipped em 12/12 runs recentes e **não** está em
   `all-green.needs`: vermelho lá não impede merge. O step passa
   `PLAYWRIGHT_WEB_SERVER_COMMAND=npx next dev --turbopack`: `npm run dev`
   dispara `predev` → `codegen:check` → `python3 …`, e `frontend-checks` é
   node-only. Sem esse override o gate **falharia sempre** por falta de
   setup-python — medido lendo o job, não inferido.
4. ~~**Smoke por fixture** — `janela-divergente` em `FIXTURES` de
   `sections.fixtures.smoke.visual.spec.ts`~~ → **revertido**. A fixture é a única
   da lista sem `real_estate`, e `S4RealEstateSection` é hide-when-empty
   ([[ADR-216]] · #305) ⇒ devolve `null`, enquanto `STRATEGIC_SECTIONS` exige
   `S4`. Medido: com a fixture na lista, **2 falhas** ("seção S4 faltando",
   light + dark); sem ela, 10/10 verdes.
   Popular `real_estate` só para caber no smoke afastaria a fixture do caso que
   ela existe para representar. Ela é exercitada pelo spec dedicado
   (`janela-canonica.@critical.spec.ts`, camada 3), que é o gate bloqueante — a
   camada 4 não agregava cobertura, só uma quebra.

**Buraco conhecido da camada 3.** O filtro `changes.report` cobre
`frontend/src/components/report/**`, `frontend/src/types/report*.ts`,
`frontend/tests/e2e/{reports,fixtures/reports}/**`, `frontend/tests/shared/**`,
o encanamento do próprio gate (`frontend/playwright.config.ts` — webServer e
override de comando — e `frontend/eslint.config.mjs` — regra
`no-restricted-syntax` de janela) e o próprio `ci.yml`. Fica de fora
`config/prompts/chart_conclusions.yaml`: PR que só edite o template do YAML não
dispara o step de render. Impacto real é baixo (o YAML não é lido em runtime;
`conclusionUtils.ts` duplica a lógica e `dev/check_chart_conclusion_parity.py`
roda no pre-commit), mas o buraco existe e fica registrado em vez de coberto por
otimismo.

**Paridade de guarda entre os dois runners.** A cláusula de base aceita vive em
`frontend/tests/shared/janelaBaseClause.ts` e é importada pelo contract test
(Vitest, bloqueante) **e** pelo spec de render (Playwright). As duas cópias
anteriores já haviam divergido: a forma singular "mês documentado" — a que
`janela_meses = 1` produz, valor do substrato versionado — existia só no E2E, ou
seja, a asserção mais forte estava no runner que não bloqueia merge. Const única
elimina a classe; provado por mutação (remover a forma singular derruba o caso
de 1 mês do Vitest).

## Correção de escopo (obrigatório para o painel)

Cinco correções ao escopo original. Onde lane e ADR divergiram, **a ADR venceu**.

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
   ROTULADO**.

   Medição (não estimativa) — varredura de
   `[data-chart-conclusion], [data-chart-context], .chart-context` no DOM
   renderizado da fixture `janela-divergente`, via Playwright contra `next dev`
   do próprio worktree (porta 3111), e conferida no PDF (`page.pdf` +
   `pdftotext -layout`): **8 textos derivados**, todos em S2. **4 declaram base
   e 4 não** — e os 4 que não são exatamente os dois cards que saíram para a
   [[A40.l15]]:

   | Texto | Cláusula de base impressa |
   | --- | --- |
   | `FluxoMensalChart` · contexto | os últimos 12 meses documentados |
   | `FluxoMensalChart` · conclusão (`fluxo_mensal`) | os últimos 12 meses documentados |
   | `ReceitaBarChart` · contexto | na janela exibida (jan/25 a dez/25) |
   | `ReceitaBarChart` · conclusão (`receita_bar`) | todo o período analisado |
   | `DespesasDoughnutChart` · contexto | — (herdado pela [[A40.l15]]) |
   | `DespesasDoughnutChart` · conclusão (`despesas_doughnut`) | — (idem) |
   | `ReceitaDespesaMensalChart` · contexto | — (idem) |
   | `ReceitaDespesaMensalChart` · conclusão | — (idem) |

   Fora de S2 o relatório desta fixture não emite texto derivado.
   (A versão anterior desta linha dizia "4 / 2 / 2", depois "8 com cláusula,
   2 / 3 / 3" — as duas erradas, e a segunda descrevia um estado de código que
   saiu do escopo. Contagem em doc só entra com a varredura que a produziu.)
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
3. **O escopo listava 3 sites; o defeito apareceu em dois não listados — e o
   TEXTO dos dois saiu para a [[A40.l15]].**
   `ReceitaDespesaMensalChart` mensaliza a série inteira (36 meses) **sem
   rótulo** e emite uma **segunda** taxa de poupança, ao lado do texto corrigido,
   na mesma seção. `DespesasDoughnutChart` desenha as fatias ex-aporte da janela
   e o texto do mesmo card cita a base full. Os dois defeitos são **medidos e
   reais** (DOM + PDF), e as cinco tentativas de corrigi-los nesta lane
   produziram par (valor, rótulo) inconsistente em todas: a causa é estrutural —
   os dois citam bases legitimamente distintas (janela ex-aporte por [[ADR-333]]
   vs bruto de todo o período) e **escolher qual base cada texto declara é
   decisão de domínio**, que a [[A40.l15]] detém (ela nasceu para a base do
   Consumo Consciente). Ver §Residuais para os três defeitos herdados, com as
   medições.
   Consequência de método que **fica** nesta lane: a lane pediu "assert por
   componente rotulado" e é justamente esse formato que não detém o site
   não-listado — daí as camadas 1 e 2 da guarda acima, que continuam valendo
   para o resto da seção.
4. **O que a lane entrega no donut: a soma, não o texto.** As fatias vinham de
   duas fontes (soma de `despesa_datasets` dentro da janela renderizada quando
   existem; snapshot `despesas_por_categoria` de todo o bloco quando não), e a
   fonte efetiva agora sai declarada no MESMO objeto que carrega as fatias
   (`{rows, fonte, aporteExcluido}`) — infraestrutura para a [[A40.l15]] imprimir
   rótulo derivado da mesma expressão que somou os valores, em vez de inferir.
   Nenhum texto lê esses campos hoje; está registrado no docstring do tipo.

   Achado de **fixture** que fica corrigido aqui: o dataset de aporte usava o
   label `"Aporte em investimentos"`, que `isAporteInvestimentoKey` não casa e o
   produtor nunca emite (`cat.replace("_"," ").title()` ⇒ `"Aporte Investimento"`
   — `fluxo_caixa_enricher.py:404`, `analyze_finances.py:1345`). Com o label
   errado o aporte entrava no donut, os dois totais coincidiam e a exclusão da
   [[ADR-333]] não era exercitada: a fixture testava um mundo que não existe.
   Alinhada ao produtor; o assert do total desenhado (R$ 828.000 ex-aporte, não
   R$ 972.000) é o que prova que o filtro rodou. A [[A40.l15]] herda a fixture
   fiel — sem ela, a divergência de base ficaria invisível lá também.
5. **A verificação renderizada estava declarada como coberta por CI e não
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

**Contagem fabricada, medida no fechamento e corrigida.** `describeJanelaEscopo`
e `janelaBadgeLabel` faziam `rotulo.meses ?? 12` para `tipo === "12m"`: payload
com `janela: "12m"` e **sem** `janela_meses` renderizava "os últimos 12 meses
documentados" e o badge "últimos 12 meses documentados" — número que o payload
não afirma. É a mesma classe de defeito que a sprint persegue (afirmar precisão
que o dado não sustenta), na guarda que existe para impedi-la. Regra vigente: sem
contagem no payload, o texto não cita contagem — "na janela documentada" /
"a janela documentada" / badge "janela documentada". Medido no render (fixture com
`janela_meses` e `n_meses` removidos de `ratios`, `fluxo_caixa.janela_12m` e
`consumo_consciente`):

```
[Fluxo de Caixa Mensal · context]    No gráfico: 12 meses (jan/25 a dez/25). Média sobre a janela documentada: …
[Fluxo de Caixa Mensal · conclusion] Sobre a janela documentada: receita recorrente de R$ 92.000/mês …
BADGES: ["janela documentada","todo o período documentado","todo o período documentado",
         "janela documentada","janela documentada"]
```

Provado por mutação: restaurar `?? 12` derruba 2 asserts (prosa + badge). O
`12` da contagem de barras ("No gráfico: 12 meses") continua vindo do render, que
é onde ele é verdade.

**Verificação renderizada do fechamento** — 3 configurações da fixture, lidas no
DOM contra `next dev` do worktree (porta 3111) e o PDF conferido com
`pdftotext -layout`:

| Configuração | O que foi lido |
| --- | --- |
| completa | 4 textos no escopo da lane, todos com cláusula de base; hero + 4 KPIs de consumo com badge impresso; `/mês` só em `{92.000, 81.000}` |
| sem `despesa_datasets` | donut cai no agregado (R$ 1.116.000) com o texto neutro de `main`, sem rótulo de janela sobre número full — a lane não introduz par inconsistente aqui |
| `janela: "12m"` sem `janela_meses` | zero dígito de contagem nos rótulos (bloco acima) |

Observação medida na 2ª configuração, **pré-existente e fora do escopo**: sem
`despesa_datasets` o `ReceitaDespesaMensalChart` perde o stack de despesa inteiro
e passa a exibir "despesas (R$ 0)" + "Taxa de poupança de 100.0%". É
comportamento de `main` para payload degradado, não regressão desta lane — e é
mais um argumento para a [[A40.l15]] tratar o texto daquele card.

### Assimetria de rótulo que esta lane NÃO fecha (handoff)

Medido no substrato versionado (`backend/tests/snapshots/dogfood_view_model.json`,
varredura recursiva por chave `janela`): **8 blocos** a trazem —
`consumo_consciente`, `equilibrio_cerbasi`, `fluxo_caixa`,
`fluxo_caixa.janela_12m`, `orcamento_prospectivo`, `passive_income`, `ratios`,
`reserva_emergencia`. Depois desta lane:

- **4 com rótulo IMPRESSO lido do campo `janela`:** `ratios` (badge no hero),
  `consumo_consciente` (4 badges), `fluxo_caixa` + `fluxo_caixa.janela_12m`
  (cláusula de base na prosa dos charts — o resumo de S2 tem o mesmo rótulo, mas
  é inalcançável em produção, ver §Residuais conhecidos).
- **1 com rótulo impresso pela PROSA DO PRODUTOR, não pelo campo:**
  `orcamento_prospectivo`. `OrcamentoProspectivoCard` imprime
  `orcamento.legenda` — no substrato, "Orçamento prospectivo baseado na média dos
  últimos 1 meses…" — e, quando a tabela vem do endpoint de transações
  (`isLiveData`), imprime "Média mensal · 12M (N meses)", que é a janela do
  toggle. Ou seja: **há** base declarada em texto impresso, só não vem do campo
  `janela` do bloco. (A versão anterior desta seção classificava
  `orcamento_prospectivo` como "sem rótulo algum" — errado, medido no card e no
  substrato. De passagem: a `legenda` do produtor carrega o **mesmo** bug de
  plural que esta lane corrigiu no frontend — "últimos 1 meses" —, agora no E5;
  registrado abaixo.)
- **1 só com tooltip:** `reserva_emergencia` — `InfoTooltip` em
  `ReservaEmergenciaCard`, que por [[ADR-306]] §Emenda A40.l3 **não conta** como
  rótulo (não imprime no PDF).
- **2 sem rótulo algum:** `equilibrio_cerbasi` (`EquilibrioCerbasiCard` exibe
  classificação/presente/futuro, sem base) e `passive_income` (consumido em
  `S7IndependenciaSection` como `data.n`, com `janela: "irpf"` nunca exposto).

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

### Residuais conhecidos (medidos no fechamento, não corrigidos aqui)

#### Texto do donut e do `ReceitaDespesaMensalChart` → [[A40.l15]]

Decisão de escopo tomada no fechamento: **o texto de conclusão/contexto desses
dois cards sai desta lane.** Cinco rodadas tentaram fechar o par (valor, rótulo)
dos dois e todas produziram inconsistência nova, porque a causa é estrutural —
bases legitimamente distintas ([[ADR-333]] ex-aporte vs bruto full) e a escolha
de qual base cada texto declara é **domínio**, que a [[A40.l15]] detém. Os três
defeitos vão medidos, para a l15 não os re-descobrir:

1. **A rosca desenha 50,0% e a conclusão do MESMO card imprime 43%.** Medido na
   fixture: Moradia = 414.000 de 828.000 de consumo na janela (ex-aporte) ⇒
   **50,0%** da geometria do donut; `despesas_por_categoria` (bloco full, com
   aporte) dá 558.000 / 1.296.000 ⇒ **43,1%**, que é o que
   `deriveChartConclusion("despesas_doughnut")` imprime. Dois números para a
   mesma pergunta, no mesmo card.
2. **A conclusão do `ReceitaDespesaMensalChart` mensaliza a série inteira sem
   rótulo e emite uma SEGUNDA taxa de poupança.** Medido no DOM e no PDF:
   "Receita média de R$ 42.667/mês e despesa média de R$ 36.000/mês. Taxa de
   poupança de 15.6%." — ao lado do card irmão que declara a janela canônica, e
   com a taxa canônica (ex-aporte, 25,0%) já no hero. O contexto do mesmo card
   agrega 36 meses declarando só "Série temporal mensal (36 meses)". Nota de
   escopo para a l15: o texto que a l3 chegou a escrever ("Janela exibida —
   12 meses …") citava **a janela exibida** sobre um agregado que não é da janela
   quando `despesa_datasets` falta — não use aquela versão como ponto de partida
   sem re-medir o ramo degradado.
3. **A fixture escondia a divergência** porque o dataset de aporte usava um label
   que o produtor não emite — **já corrigido neste repo**, a l15 herda a fixture
   fiel (ver §Correção de escopo item 4). Sem essa correção o defeito 1 é
   invisível: os dois totais coincidiam.

Consequência na guarda: `CARDS_DA_L15` exclui os dois cards das varreduras de
seção (contract test + spec de render), com assert de que a exclusão não é vácuo.
Tudo mais em S2 segue coberto.

#### Demais residuais

- **`SECTION_SUMMARIES.S2` é inalcançável em produção.** Medido: os únicos
  chamadores de `deriveSectionSummary` são `S8`, `S9`, `S10` e `APP_A..E`
  (`rg deriveSectionSummary frontend/src`). `S2FluxoCaixaSection` usa
  `<SectionSummary narrativas … />`, que lê **só** `narrativas.S2` (E5.N) e não
  renderiza nada quando ausente — nenhum caminho chega ao template. As entradas
  `S1`, `S2`, `S3`, `S4` e `S7` de `SECTION_SUMMARIES` estão nessa condição. A
  lane manteve o template `S2` corrigido (lê `janela_12m` e rotula) porque
  removê-lo é decisão de outra natureza (dead code cross-seção, 5 entradas), com
  um teste de contrato como único consumidor. **Não inventar consumidor** — se a
  decisão for remover, remova as 5 e o assert junto.
- **Fixtures locais podem medir o checkout errado.** `playwright.config.ts` usa
  `reuseExistingServer: !CI`: com um `next dev` de outro checkout já em
  `127.0.0.1:3000`, `npm run test:e2e` num worktree mede **o código do outro
  checkout** e passa/falha por motivo alheio (aconteceu na primeira medição
  desta lane: o texto renderizado era o de `origin/main`). Em CI não ocorre
  (`reuseExistingServer` é false). Verificação local honesta: subir o servidor do
  próprio worktree em porta livre e apontar
  `PLAYWRIGHT_SKIP_WEB_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:<porta>`.
- **`humanizeLabel` do `ReceitaBarChart` capitaliza dentro da palavra**: a
  fixture emite `Salário`/`Bônus` e o DOM mostra `SaláRio`/`BôNus` (o `\b\w` casa
  depois do acento decomposto). Cosmético, pré-existente e fora do escopo de
  janela — mas visível em todo relatório com fonte de receita acentuada.
- **`janela-divergente` fora do smoke por fixture** (ver camada 4 acima): a
  fixture não tem `real_estate` nem `narrativas.S4` e `STRATEGIC_SECTIONS` exige
  `S4`, que é hide-when-empty. Duas saídas possíveis para quem quiser a fixture
  no smoke: popular `real_estate` (afasta a fixture do caso que ela representa) ou
  tornar `S4` opcional no smoke como já é `APP_C`. Nenhuma das duas é desta lane.
- **`DebtForm.test.tsx` é flaky em `origin/main`** — descoberto ao comparar
  baselines desta lane, **não** é regressão dela. Medido num checkout limpo de
  `origin/main` (`git archive` + `npx vitest run`): 6 execuções da suíte completa
  ⇒ **4 com falha** (1-2 testes) e 2 verdes; os alvos são sempre
  `mostra percentual_atribuicao_imovel quando property tem >1 cotitular` e
  `submete payload sem percentual quando property tem 1 cotitular`. Rodado
  isolado (`npx vitest run tests/components/DebtForm.test.tsx`) falha **2/3 de
  forma determinística**, o que aponta dependência de setup de outro arquivo
  (ordem/MSW), não corrida interna. Consequência prática: "suíte frontend verde"
  não é um baseline estável hoje — quem comparar contagens vai atribuir ao próprio
  PR uma falha que já existe. Candidato natural a [[ADR-210]] §Camada 1 (teste que
  custa CI e dá sinal errado).
- **Bug de plural no produtor.** `orcamento_prospectivo.legenda` do E5 emite
  "baseado na média dos últimos 1 meses" — o mesmo defeito de concordância que
  esta lane corrigiu no frontend, agora no gerador de prosa. Vale junto com o
  outro bug de formato já registrado na [[A40.l15]] (`f"R$ {v:,.0f}"` emitindo
  `R$ 250,000.00` en-US na frase do Consumo Consciente): são a mesma família
  (prosa do E5 sem locale pt-BR) e cabem no mesmo PR.
