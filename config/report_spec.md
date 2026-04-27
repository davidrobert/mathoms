# Report Spec — Pipeline Ferreira Campos
## Versão: 5.3 — abr/2026

---

## ESPECIFICAÇÕES TÉCNICAS

- **Formato:** Um único arquivo `.html` autocontido
- **Bibliotecas via CDN:**
  - Chart.js 4.4.0: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`
  - chartjs-plugin-datalabels 2.2.0: `https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0`
  - Turndown.js 7.1.3 (HTML→Markdown export): `https://cdn.jsdelivr.net/npm/turndown@7.1.3/dist/turndown.min.js`
  - Google Fonts (Inter + Plus Jakarta Sans): `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap`

---

## PALETA DE CORES (CSS VARIABLES)

```css
/* Cores de texto (WCAG AA ≥ 4.5:1 contra branco) */
--color-primary:       #1A3A5C   /* Azul escuro — títulos (11.64:1) */
--color-secondary:     #1E6E8F   /* Azul médio — destaques (5.70:1) */
--color-accent:        #15803D   /* Verde — texto positivo (5.02:1) */
--color-accent-bg:     #2DC653   /* Verde vibrante — backgrounds, bordas, decorações */
--color-danger:        #B91C1C   /* Vermelho — alertas (6.47:1) */
--color-warning:       #F4A261   /* Laranja — fundos de atenção */
--color-warning-text:  #B45309   /* Laranja escuro — texto de atenção (5.02:1) */
--color-neutral:       #457B9D   /* Azul aço */
--color-light:         #A8DADC   /* Azul claro */
--color-bg:            #F8FAFC   /* Fundo */
--color-surface:       #FFFFFF   /* Cards */
--color-text:          #1E293B   /* Texto principal */
--color-text-muted:    #64748B   /* Texto secundário (4.76:1) */
--color-border:        #E2E8F0   /* Bordas */

/* Backgrounds semânticos */
--color-row-even:      #F8FAFC   /* Tabela: linhas pares */
--color-row-hover:     #EEF5FF   /* Tabela: hover */
--color-row-total:     #EDF2F7   /* Tabela: linha total */
--color-summary-bg:    #EFF6FF   /* Section summary */
--color-conclusion-bg: #F8FAFC   /* Conclusão */
--color-compare-neg:   #FEF2F2   /* Comparação negativa */
--color-compare-pos:   #F0FDF4   /* Comparação positiva */

/* Layout tokens */
--radius-card:         12px
--radius-badge:        10px
--space-card-sm:       16px
--space-card-md:       24px
--space-card-lg:       28px 32px
--shadow-card:         0 1px 3px rgba(0,0,0,0.06)
```

Paleta gráficos light: `['#1A3A5C', '#1E6E8F', '#15803D', '#F4A261', '#B91C1C', '#457B9D', '#A8DADC', '#8338EC']`
Paleta gráficos dark: `['#7EB8DA', '#5CC8F0', '#4ADE80', '#FBBF24', '#FB7185', '#7CA3BD', '#5B8FA8', '#A78BFA']`

---

## DESIGN SYSTEM

### Fontes
- **Títulos e KPIs:** Plus Jakarta Sans
- **Corpo:** Inter

### Escala tipográfica (10 tamanhos)
10px (micro) | 12px (notas, muted) | 13px (corpo cards) | 14px (corpo principal, summaries) | 15px (H3 dentro de cards) | 16px (H2) | 18px (dash-section H2 tático) | 22px (H1) | 24px (KPI value) | 38px (cover)

### Classes utilitárias CSS
- Tipografia: `.text-sm` (12px muted), `.text-base` (13px), `.text-lg` (14px), `.text-muted`, `.text-bold`
- Espaçamento: `.mt-2` (8px), `.mt-3` (12px), `.mt-4` (16px), `.mb-2`, `.mb-3`
- Layout: `.nowrap` (white-space), `.list-actions` (listas sem bullet com border-bottom)

### ⚠️ REGRAS DE DESIGN OBRIGATÓRIAS (E5)

**1. Espaçamento entre cards — NUNCA usar inline `margin-top` ou `margin-bottom`:**
O CSS usa seletores adjacentes (`.section .card + .card`, `.section .card + .chart-container`, etc.) que adicionam automaticamente `--space-section-gap: 20px` entre elementos. **É PROIBIDO** adicionar `style="margin-top:20px"` ou qualquer `margin` inline em cards, chart-containers, chart-rows ou alerts dentro de seções.

**2. Títulos dentro de cards — SEMPRE usar `<div class="card-title">`:**
Todo card DEVE ter `<div class="card-title">` como primeiro elemento filho. Usar `card-title-lg` para cards de destaque. **NUNCA** usar `<h3>` como primeiro filho direto de um card — usar `<div class="card-title">` no lugar. `<h3>` é permitido para sub-seções dentro de cards (ex: "3.1 Rentabilidade...") mas não como título principal do card.

**3. Cores — NUNCA hardcodar valores hex no HTML:**
Todas as cores devem usar tokens CSS: `var(--color-accent)`, `var(--color-danger)`, etc. Para backgrounds de alertas usar as classes `.alert-danger`, `.alert-warning`, `.alert-success`, `.alert-info`. **NUNCA** usar `style="background:#F0FDF4"` ou similar — quebra o dark mode.

**4. KPI cards com destaque — usar classe `.kpi-card-accent`:**
Em vez de `style="border-color:var(--color-accent)"`, usar `class="kpi-card kpi-card-accent"`.

**5. Grid inline — NUNCA sobrescrever grids com style inline:**
Não usar `style="grid-template-columns: repeat(4, 1fr)"` — o CSS já define o grid correto. Se precisar de grid diferente, usar classe CSS.

**6. Tabelas — linhas totais devem usar classe `.total-row`:**
Linhas de total devem usar `<tr class="total-row">` (background cinza + negrito + border-bottom 2px). Não usar `.td-total` em cells individuais.

**7. Tags vazias — NUNCA gerar `<p>` vazio:**
Se `chart-context` ou `chart-conclusion` não tiver texto, OMITIR a tag inteira. Não gerar `<p class="chart-context"></p>`.

**8. Contrafluxo card — usar classe `.card-primary` em vez de style inline:**
`<div class="card card-primary">` em vez de `<div class="card" style="border-left:4px solid var(--color-primary)">`.

### Card Variants (10 classes semânticas)

| Classe | Estilo | Uso |
|---|---|---|
| `.card-highlight` | border-left azul | Informação importante |
| `.card-feature` | gradiente azul + borda | Destaque com ação (ex: orçamento prospectivo) |
| `.card-success` | gradiente verde | Resultado positivo (ex: quitação) |
| `.card-warn` | border-left laranja | Atenção (ex: reserva oportunidade) |
| `.card-critical` | border-left vermelho | Problema |
| `.card-primary` | border-left azul escuro | Referência (ex: contrafluxo) |
| `.card-neutral` | border-left cinza-azul | Contexto |
| `.card-top-danger` | border-top vermelho | — |
| `.card-top-accent` | border-top verde | — |
| `.kpi-card-accent` | border verde (accent) | KPI com destaque (ex: rentabilidade) |

### Table Variants (3 estilos + total-row)
- **Padrão** — zebrado, alternating rows
- **`.table-steps`** — border-left azul, 1ª coluna bold nowrap (passo-a-passo)
- **`.table-compare`** — colunas centralizadas com backgrounds tinted (comparação)
- **`tr.total-row`** — background `--color-row-total`, font-weight 700, border-bottom 2px

### Componentes especiais
- **`.kpi-hero`** — 3 KPIs maiores: font-size 30px, border-top 4px solid primary
- **`.section-summary`** — box azul claro no topo de cada seção, 1 frase de conclusão
- **`.section-divider`** — hr com estilo diamante (◇) entre seções
- **`.nav-separator`** — divisor vertical antes dos apêndices na nav
- **`.icon-badge`** — substituto de emojis nos títulos de cards (24×24px, border-radius, cor)
- **`details.expandable`** — progressive disclosure para conteúdo técnico
- **`.back-to-top`** — botão fixo inferior direito, aparece após scroll 600px
- **`.export-md`** — botão Turndown.js HTML→Markdown, label "⬇"

---

## CABEÇALHO (COVER HERO)

- Gradiente `#0F2A44 → #1A3A5C → #2E5D85` com efeitos radial
- Badge "RELATÓRIO CONFIDENCIAL" translúcido
- Título 38px weight 800, subtítulo com gradiente `#A8DADC → #2DC653`
- **8 KPI cards** (3 com classe `kpi-hero`):
  1. Patrimônio Bruto
  2. **Patrimônio Investível (hero)**
  3. Renda Mensal
  4. Taxa Poupança (mostrar taxa REAL histórica, subtítulo "Meta projetada: X%")
  5. Meta Indep. Financeira
  6. Gap Indep. Financeira
  7. **Prazo Indep. Financeira (hero)**
  8. **Score Financeiro (hero)**
- **Labels:** "Independência Financeira" em headings; "Indep. Financeira" em label compacto. "IF" apenas em variáveis técnicas, no Apêndice A (glossário) e como fallback em viewport ≤320px. Regra completa em [docs/COPY_GUIDELINES.md §3.1](../docs/COPY_GUIDELINES.md).

---

## NAVEGAÇÃO (STICKY TOP)

- Gradiente `#0F2A44 → #152F4A`, brand à esquerda
- Links: 10 seções + separador `.nav-separator` + 5 apêndices (estilo mais sutil)
- Scroll horizontal em mobile
- Toggle modo dual à direita (📊 Estratégico / ⚡ Tático)
- Navegação muda conforme modo ativo (links S1-S10+Apps vs D1-D6)

---

## ESTRUTURA DE SEÇÕES

### ⚠️ Regra estrutural para `{{CONTENT_S*}}` e `{{CONTENT_APP_*}}`

O template HTML legado (removido em ADR-129) já continha para cada seção:
```html
<div class="section" id="secao-N">
  <div class="section-header"><h1>N. Título</h1></div>
  <div class="section-summary">{{SUMMARY_SN}}</div>
  {{CONTENT_SN}}
</div>
```

Portanto, ao gerar o conteúdo dos placeholders:
- **`{{SUMMARY_S*}}`** = texto inline do summary (pode conter `<strong>`, `<em>`, etc.), SEM tags wrapper
- **`{{CONTENT_S*}}`** NÃO deve incluir: `<h2>` com título da seção, `<p class="section-summary">`, nem `<div class="section">` wrapper
- **`{{CONTENT_S*}}`** começa diretamente com o corpo: `<div class="chart-container">`, `<div class="card">`, `<table>`, `<div class="kpi-grid">`, etc.
- Sub-seções internas (ex: 3.1, 3.2) usam **`<h3>`**, nunca `<h2>`
- Mesma regra para **`{{CONTENT_APP_*}}`** nos apêndices

**Violação desta regra gera título e summary duplicados no relatório final.**

### Modo Estratégico (`data-mode="strategic"`)

| ID | Seção | Conteúdo principal |
|---|---|---|
| `secao-1` | Visão Geral Patrimonial | Doughnut patrimônio (de `patrimonio-3_unified.json`: imóveis, veículos, investimentos, criptos, contas, empresas) + waterfall meta IF + card **Reserva de Emergência** (obrigatório — 3 critérios: mínimo, conforto, conservador; cálculos de `reserva_emergencia` do E4) + reserva oportunidade + card quitação + card **Endividamento** (obrigatório — relação dívida/patrimônio, composição, cronograma quitação; de `endividamento` do E4) |
| `secao-2` | Fluxo de Caixa e Orçamento | Receita 7 camadas + despesas doughnut + **Receita vs Despesa mês a mês** (stacked bar `chart-receita-despesa-mensal`: 3 stacks receita PJ/CLT/Aluguéis + 1 stack despesa s/ financeiro, período dinâmico do fluxo_mensal_detalhado, fonte: receitas + despesas E3 monthly_breakdown) + score gauge (5 faixas + needle) + **Orçamento Prospectivo** (card obrigatório `.card-feature`, tabela 13+ categorias com tetos de `definitions.md`, fonte: `orcamento_prospectivo` do E4) + **Consumo Consciente** (card obrigatório) + **Diagnóstico de Comportamento Financeiro** (card obrigatório, tabela Padrão/Evidência/Mudança, fonte: `diagnostico_comportamental[]` do E4) |
| `secao-3` | Investimentos e Rendimentos | 3.1 Rentabilidade (4 KPIs + benchmark acumulado) · 3.2 Estratégia aporte (R$22,3k: R$20k investimentos + R$1,8k PGBL + R$500 DCA Crypto + **Contrafluxo AUVP** — quadro didático Selic↑→Prefixado, Selic↓→IPCA+, regra prática + coluna liquidez + nota validação vs alocação alvo) · 3.3 Card **Ações Diretas — Rico** (tabela: Ativo/Qtd/PM/Cotação/Valor/P&L/Situação — dados de `rico_investimentosposicao`, PM de `lots` no E3 ou IRPF, total + notas de lote) · 3.4 Análise ativos (top 15 + fundamentalista PM/lotes + marcação mercado IPCA+ + crypto 1% + FIIs ref.) · 3.5 Consolidação corretoras |
| `secao-4` | Imóveis e Bens | Card **Patrimônio Imobiliário** (tabela #/Imóvel/Área/Dono/Compra/IRPF/Aluguel/Status + linha resumo com totais) + yield vs CDI + custo oportunidade + simulação Barão→FIIs + 5 FIIs referência com disclaimer. Fonte: `patrimonio-3_unified.json` / `imoveis-3_unified.json` + XLSX + IRPF |
| `secao-5` | F1/F2 EUA | Stacked bar custos USD + checklist status DECIDIDO/PENDENTE |
| `secao-6` | Green Card | Cenários cambiais + dolarização + proteção patrimonial 5 riscos |
| `secao-7` | Independência Financeira | TRS didática + rentabilidade 6% real + projeção 3 cenários + renda passiva por fonte + projeção 2035 8 fontes com disclaimer + card **Previdência PGBL** (obrigatório — portabilidade, benefício fiscal 12%, projeção acumulação, de `previdencia_pgbl` do E4) |
| `secao-8` | Tributário | DAS irregular + Simples vs LP + PGBL portabilidade + carnê-leão passo-a-passo 7 etapas + calendário |
| `secao-9` | Riscos e Proteção | Bubble chart (X=Probabilidade, Y=Impacto, Raio=Severidade) + **Seguros** (vida, DIT, residencial — cobertura atual vs recomendada, gap analysis) + top 3 mitigações + planejamento sucessório (testamentos BR + procuração duradoura + holding + guardianship EUA) |
| `secao-10` | Conclusão e Roadmap | Card **Pontos Fortes** (obrigatório — 5-7 destaques positivos, de `pontos_fortes[]` do E4) + card **Pontos Urgentes** (obrigatório — 5-7 ações críticas priorizadas, de `pontos_urgentes[]` do E4) + card **Equilíbrio Presente × Futuro** (obrigatório — análise Cerbasi gastos-presente vs investimentos-futuro, de `equilibrio_cerbasi` do E4) + top 5 decisões + timeline Abr split |
| `apendice-a` | Definições e Siglas | Glossário de termos (IF, TRS, CDI, IPCA+, DAS, etc.), siglas de corretoras, categorias patrimoniais. Leitura autônoma: leitor sem contexto consulta aqui. |
| `apendice-b` | Premissas e Metodologia | Inflação, câmbio, rentabilidade real, taxa desconto, horizonte, fonte de cada premissa. Metodologias: Bruno Perini (IF number), Cerbasi (equilíbrio), AUVP (contrafluxo/Cerrado). |
| `apendice-c` | Cenários de Sensibilidade | Tabela otimista/base/pessimista para IF, cambial, Selic, imóveis. Stress-test: "e se Selic cair a 8%?", "e se USD a 6,50?" |
| `apendice-d` | Referências e Recursos | Links, livros, ferramentas, contatos de assessores. Bruno Perini (Viver de Renda), Cerbasi (Casais Inteligentes), AUVP (plataforma). |
| `apendice-e` | Próximos Ciclos e Roadmap | Tarefas priorizadas (usar classes `priority-badge priority-{alta,media,baixa}` — ver "Regra obrigatória: Badges de Prioridade") + Viagens e Milhas (R$45k orçamento) + NCLEX Roadmap (7 etapas) + Simulação Mariana + calendário próximo ciclo |

### Card obrigatório: Orçamento Prospectivo (dentro de `secao-2` — OBRIGATÓRIO)

**Regra gauge:** O canvas do score gauge DEVE incluir `data-score="X.X"` com o valor numérico calculado pelo E4 (ex: `<canvas id="chart-score-gauge" data-type="gauge" data-score="6.8">`). O `<p class="chart-context">` antes do canvas pode ficar vazio ou com placeholder — o JS do template sobrescreve automaticamente com "Avaliação consolidada: X,X/10 (Classificação)." **NUNCA hardcodar o texto de avaliação manualmente.**

**Regra breakdown do score (obrigatória):** Logo abaixo do canvas do gauge, o template DEVE renderizar automaticamente uma tabela de decomposição com os 5 componentes do score. A fonte de dados é `REPORT_DATA_JSON.score.componentes[]` (gerado pelo E4). A tabela tem 4 colunas: Componente, Valor, Nota (com barra visual proporcional), Peso. Abaixo da tabela, exibir a fórmula resumida: "Score = Σ(nota × peso) / Σ(peso)". O JS do template gera esta tabela dinamicamente — o E5 NÃO deve hardcodar o breakdown no HTML. Se `REPORT_DATA_JSON.score.componentes` não existir ou estiver vazio, o breakdown não é renderizado (graceful degradation).

**Regra:** Este card DEVE ser gerado SEMPRE na secao-2 (Fluxo de Caixa e Orçamento), logo após os gráficos de receita/despesa e o score gauge. É o "painel de controle" da família. Mesmo na primeira execução (sem dados reais de gasto), gerar com a coluna "Média Real" vazia ou com "—".

**Posição no HTML:** Dentro de `secao-2`, antes do card de Consumo Consciente.

**Fonte de dados:**
- Tetos e categorias: `docs/methodology/definitions.md` seção "CATEGORIAS DE DESPESA (ORÇAMENTO PROSPECTIVO)" — **NUNCA hardcodar tetos**
- Média real: `report-data.orcamento_prospectivo.categorias[].media_real` (calculada no E4 a partir de `despesas-3_unified.json`)
- Renda total: `report-data.orcamento_prospectivo.renda_total`
- Período da média: `report-data.orcamento_prospectivo.periodo_meses` (ex: "11M")

**Estrutura HTML:**
```html
<div class="card card-feature">
  <div class="card-title card-title-lg">Orçamento Prospectivo — {{periodo_referencia}} em diante</div>
  <p class="text-sm text-muted">Tetos mensais por categoria, baseados na média real dos últimos {{periodo_meses}} meses com ajustes pós-quitação.
  Esse é o "painel de controle" da família: se cada linha ficar dentro do teto, o aporte de R$ {{aporte_if}} e a folga de R$ {{folga_mensal}} estão protegidos.</p>

  <table>
    <thead>
      <tr>
        <th style="text-align:left;">CATEGORIA</th>
        <th style="text-align:right;">MÉDIA REAL ({{periodo_meses}})</th>
        <th style="text-align:right;">TETO PROPOSTO</th>
        <th style="text-align:right;">% DA RENDA</th>
        <th style="text-align:left;">OBSERVAÇÃO</th>
      </tr>
    </thead>
    <tbody>
      <!-- Para cada item em orcamento_prospectivo.categorias[] (ordem do definitions.md) -->
      <tr>
        <td>{{emoji}} {{categoria}}</td>
        <td style="text-align:right;">R$ {{media_real}}</td>
        <td style="text-align:right;"><strong>R$ {{teto}}</strong></td>
        <td style="text-align:right;">{{pct_renda}}%</td>
        <td>{{observacao}}</td>
      </tr>
      <!-- Linha TOTAL DESPESAS -->
      <tr class="total-row">
        <td><strong>TOTAL DESPESAS</strong></td>
        <td style="text-align:right;"><strong>R$ {{total_media_real}}*</strong></td>
        <td style="text-align:right;"><strong>R$ {{total_tetos}}</strong></td>
        <td style="text-align:right;"><strong>{{total_pct_renda}}%</strong></td>
        <td></td>
      </tr>
      <!-- Linha Aporte IF (destaque) -->
      <tr>
        <td>📈 Aporte IF</td>
        <td style="text-align:right;">—</td>
        <td style="text-align:right; color: var(--color-danger);"><strong>R$ {{aporte_if}}</strong></td>
        <td style="text-align:right;">{{aporte_pct}}%</td>
        <td>Dia 5, automático (ver Seção 3)</td>
      </tr>
      <!-- Linha Impostos + contador -->
      <tr>
        <td>🟰 Impostos + contador</td>
        <td style="text-align:right;">R$ {{impostos_media}}</td>
        <td style="text-align:right;"><strong>R$ {{impostos_teto}}</strong></td>
        <td style="text-align:right;">{{impostos_pct}}%</td>
        <td>DAS + AccountTech + IRPF provisão</td>
      </tr>
      <!-- Linha Folga livre -->
      <tr>
        <td>▶ Folga livre</td>
        <td style="text-align:right;">—</td>
        <td style="text-align:right; color: var(--color-accent);"><strong>R$ {{folga_livre}}</strong></td>
        <td style="text-align:right;">{{folga_pct}}%</td>
        <td>Extras, imprevistos, aportes adicionais</td>
      </tr>
      <!-- Linha RENDA TOTAL -->
      <tr class="total-row">
        <td><strong>RENDA TOTAL</strong></td>
        <td></td>
        <td style="text-align:right;"><strong>R$ {{renda_total}}</strong></td>
        <td style="text-align:right;"><strong>100%</strong></td>
        <td></td>
      </tr>
    </tbody>
  </table>

  <p class="text-sm text-muted">* Média real inclui pontuais ({{pontuais_exemplos}}) que inflaram categorias. Tetos propostos refletem operação normalizada.</p>
  <p class="text-sm text-muted">** A folga livre real de R$ {{folga_livre}} resulta de: renda (R$ {{renda_total}}) − despesas (R$ {{total_tetos}}) − aporte IF (R$ {{aporte_if}}) − impostos (R$ {{impostos_teto}}).</p>
  <p class="text-sm"><strong>Como usar:</strong> No final de cada mês, compare o gasto real de cada categoria com o teto. Se uma categoria estourar, compense na folga — mas se 3+ categorias estourarem no mesmo mês, é sinal de que o padrão de vida está subindo e precisa de revisão.</p>
</div>
```

**JSON em `report-data` (exemplo — valores recalculados a cada ciclo E4):**
```json
"orcamento_prospectivo": {
  "periodo_referencia": "Abr/2026",
  "periodo_meses": "11M",
  "renda_total": 78611,
  "aporte_if": 20000,
  "impostos_teto": 6673,
  "impostos_media": 7275,
  "folga_livre": 20488,
  "folga_mensal": 26780,
  "total_tetos": 32950,
  "total_media_real": 37970,
  "total_pct_renda": 41.9,
  "aporte_pct": 25.4,
  "impostos_pct": 8.5,
  "folga_pct": 24.2,
  "pontuais_exemplos": "TV, Vivara, Awada",
  "categorias": [
    {"codigo": "moradia", "emoji": "🏠", "categoria": "Moradia (sem financiamento)", "media_real": 2405, "teto": 2500, "pct_renda": 3.2, "observacao": "SABESP + Enel + condos Mariana"},
    {"codigo": "alimentacao", "emoji": "🍽", "categoria": "Alimentação", "media_real": 4254, "teto": 4500, "pct_renda": 5.7, "observacao": "Super + restaurantes + delivery + padarias"},
    {"codigo": "saude", "emoji": "🏥", "categoria": "Saúde", "media_real": 4818, "teto": 3000, "pct_renda": 3.8, "observacao": "Normalizado (excl. Awada R$14,9k pontual)"},
    {"codigo": "servicos_domesticos", "emoji": "🧹", "categoria": "Serviços domésticos", "media_real": 3854, "teto": 4000, "pct_renda": 5.1, "observacao": "Suecia + Eliane + Nathalia"},
    {"codigo": "educacao", "emoji": "🎓", "categoria": "Educação", "media_real": 1463, "teto": 2000, "pct_renda": 2.5, "observacao": "Belt Academy + margem para cursos"},
    {"codigo": "transporte", "emoji": "🚗", "categoria": "Transporte", "media_real": 1563, "teto": 1700, "pct_renda": 2.2, "observacao": "Combustível + pedágio + estacionamento"},
    {"codigo": "lazer_viagens", "emoji": "✈", "categoria": "Lazer e viagens", "media_real": 7136, "teto": 3750, "pct_renda": 4.8, "observacao": "Teto R$ 45k/ano = R$ 3.750/mês"},
    {"codigo": "vestuario", "emoji": "👕", "categoria": "Vestuário e compras", "media_real": 3881, "teto": 2000, "pct_renda": 2.5, "observacao": "Normalizado (excl. TV, iPhone, Vivara)"},
    {"codigo": "assinaturas", "emoji": "📱", "categoria": "Assinaturas", "media_real": 279, "teto": 300, "pct_renda": 0.4, "observacao": "Spotify + Prime + Globoplay + Gympass"},
    {"codigo": "suporte_familiar", "emoji": "👨‍👩‍👦", "categoria": "Suporte familiar", "media_real": 3090, "teto": 5000, "pct_renda": 6.4, "observacao": "Rubens R$ 1.333 + Neusa R$ 1.500"},
    {"codigo": "financeiro", "emoji": "🏦", "categoria": "Financeiro pessoal", "media_real": 954, "teto": 200, "pct_renda": 0.3, "observacao": "Sem cheque especial = quase zero"},
    {"codigo": "melhoria_reforma", "emoji": "🔨", "categoria": "Melhoria/Reforma moradia", "media_real": null, "teto": 1500, "pct_renda": 1.9, "observacao": "NOVO: reparos, reformas, troca de móveis"},
    {"codigo": "reserva_desejos", "emoji": "🎁", "categoria": "Reserva de desejos", "media_real": null, "teto": 3000, "pct_renda": 3.8, "observacao": "NOVO: acumula para compras planejadas"},
    {"codigo": "seguros", "emoji": "🛡", "categoria": "Seguros", "media_real": null, "teto": 1500, "pct_renda": 1.9, "observacao": "Vida + invalidez + residencial + auto"}
  ]
}
```

**Se `media_real` for `null`**, exibir "—" na coluna.

**Regras de geração:**
- Os tetos e categorias DEVEM vir de `definitions.md` — nunca hardcodar valores no template ou no E5
- `pct_renda` = `teto / renda_total × 100`
- `folga_livre` = `renda_total − total_tetos − aporte_if − impostos_teto`
- Se `media_real` for `null` (categoria nova, sem histórico), exibir "—"
- A ordem das categorias segue a ordem do `definitions.md`

**Validação E5:** O HTML final DEVE conter uma tabela dentro de um `div.card-feature` com **todas** as categorias listadas em `definitions.md` (atualmente 14). Se alguma categoria estiver faltando, o E5 falhou e deve ser refeito. Os totais devem bater: `total_tetos + aporte_if + impostos_teto + folga_livre = renda_total`.

---

### Card obrigatório: Consumo Consciente — Oportunidade de Disciplina (dentro de `secao-2`)

**Fonte:** `report-data.consumo_consciente` (gerado no E4, item 7)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-2 (Fluxo de Caixa e Orçamento), mesmo que não haja gastos pontuais no período (nesse caso, exibir versão positiva).

**Estrutura HTML:**
```html
<div class="card card-warn">
  <div class="card-title">⚠ Consumo Consciente — Oportunidade de Disciplina</div>
  <p>Com folga mensal de R$ {{folga_mensal}} ({{folga_pct}}% da renda), a família tem espaço para viver bem <strong>e</strong> investir.
  O desafio não é cortar gastos — é garantir que os gastos grandes sejam escolhas conscientes, não impulsos.
  Os pontuais abaixo totalizam R$ {{total_pontuais}} em {{periodo_meses}} meses — <strong>se foram escolhas pensadas, ótimo</strong>. Se não foram, vale criar um filtro:</p>

  <table>
    <thead><tr><th>GASTO PONTUAL ({{ano}})</th><th>VALOR</th><th>OBSERVAÇÃO</th></tr></thead>
    <tbody>
      <!-- Para cada item em consumo_consciente.itens[] -->
      <tr><td>{{descricao}} ({{cartao}}, {{mes}})</td><td>R$ {{valor}}</td><td>{{observacao}}</td></tr>
      <!-- Linha de totais -->
      <tr class="total-row"><td><strong>Total desses {{n}} pontuais</strong></td><td><strong>R$ {{total_pontuais}}</strong></td><td><strong>Equivale a {{equivalente_meses_aporte}} meses de aporte IF</strong></td></tr>
    </tbody>
  </table>

  <p><strong>Sugestão prática:</strong> Antes de qualquer compra acima de R$ 2.000, aplicar o <strong>filtro de 48 horas</strong>: esperar 2 dias e perguntar "Essa compra me aproxima dos meus objetivos ou é um desejo passageiro?". Complementarmente, definir um <strong>teto mensal de despesas pessoais de R$ {{teto_sugerido}}</strong> (inclui média dos pontuais diluídos). Revisar trimestralmente — se a média de 3 meses ultrapassar o teto, revisar prioridades no mês seguinte.</p>
</div>
```

**Se `consumo_consciente.itens` estiver vazio**, substituir o conteúdo por versão positiva:
```html
<div class="card card-success">
  <div class="card-title">✅ Consumo Consciente — Disciplina Mantida</div>
  <p>Nenhum gasto pontual acima de R$ 2.000 identificado no período. A família mantém disciplina no consumo, com folga mensal de R$ {{folga_mensal}} ({{folga_pct}}% da renda) integralmente disponível para aportes e objetivos de longo prazo.</p>
</div>
```

**JSON em `report-data`:**
```json
"consumo_consciente": {
  "folga_mensal": 26780,
  "folga_pct": 33,
  "total_pontuais": 48302,
  "periodo_meses": 2,
  "equivalente_meses_aporte": 2.4,
  "teto_sugerido": 35000,
  "itens": [
    {"descricao": "TV Casas Bahia", "cartao": "C6 PF", "mes": "dez/25", "valor": 18233, "observacao": "Nova TV, PIX direto"},
    {"descricao": "Dra. Adriana Awada", "cartao": "C6 Carbon", "mes": "nov/25", "valor": 14874, "observacao": "Dermatologia estética"}
  ]
}
```

---

### Card: Diagnóstico de Comportamento Financeiro (secao-2 — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-2 (Fluxo de Caixa e Orçamento), logo após o card de Consumo Consciente. É alimentado pelo bloco `diagnostico_comportamental[]` do E4 analysis JSON. Mesmo que nenhum padrão seja detectado, exibir versão positiva.

**Posição no HTML:** Após o card de Consumo Consciente, antes do fechamento da secao-2.

**Estrutura HTML (quando há padrões detectados):**
```html
<div class="card card-highlight">
  <div class="card-title">Diagnóstico de Comportamento Financeiro</div>
  <p>Os extratos revelam padrões que não são sobre falta de dinheiro — são sobre organização do fluxo e consciência nas decisões. Identificar esses padrões é o primeiro passo para ajustá-los:</p>

  <table>
    <thead>
      <tr>
        <th>PADRÃO IDENTIFICADO</th>
        <th>EVIDÊNCIA NOS EXTRATOS</th>
        <th>MUDANÇA SUGERIDA</th>
      </tr>
    </thead>
    <tbody>
      <!-- Para cada item em diagnostico_comportamental[] -->
      <tr>
        <td><strong>{{padrao}}</strong></td>
        <td>{{evidencia}}</td>
        <td>{{mudanca_sugerida}}</td>
      </tr>
    </tbody>
  </table>

  <p>Nenhum desses padrões é "erro" — são hábitos que se formaram pela praticidade. O objetivo não é julgar, mas <strong>automatizar o fluxo</strong> para que o dinheiro vá para o lugar certo sem depender de decisão manual todo mês.</p>
</div>
```

**Se `diagnostico_comportamental[]` estiver vazio**, substituir por versão positiva:
```html
<div class="card card-success">
  <div class="card-title">✅ Comportamento Financeiro — Nenhum Padrão de Risco</div>
  <p>Nenhum padrão comportamental de risco identificado nos extratos do período. A família mantém fluxo organizado, impostos regulares e direcionamento adequado de receitas para investimentos.</p>
</div>
```

**JSON em `report-data`:**
```json
"diagnostico_comportamental": [
  {
    "padrao": "Cheque especial recorrente",
    "evidencia": "Saldo negativo na C6 PF em 6 de 11 meses (até -R$17k em nov/25), apesar de R$284k em liquidez. Juros pagos: R$1.453.",
    "mudanca_sugerida": "Configurar transferência automática de R$5k da C6 PJ para C6 PF no dia 1 de cada mês. Nunca operar no negativo novamente."
  },
  {
    "padrao": "Gastos grandes sem planejamento",
    "evidencia": "R$48.302 em pontuais concentrados em dez/25-jan/26 (TV, Vivara, Awada, iPhone). Não houve provisão prévia.",
    "mudanca_sugerida": "Criar uma \"reserva de desejos\": R$3.000/mês separados (da folga de R$26.780) para compras planejadas. Quando o saldo acumulado cobrir o item, comprar sem culpa."
  },
  {
    "padrao": "Impostos pagos de forma irregular",
    "evidencia": "DAS pago em 4 lotes irregulares (incluindo por contas pessoais), gerando multas. Carnê-leão David e Mariana: zero em 2025. QuintoAndar não retém IRRF.",
    "mudanca_sugerida": "AccountTech configurar DAS automático dia 20. Carnê-leão mensal para ambos via Carnê-Leão Web (ver Seção 8). Todo imposto sai da conta certa (PJ para PJ, PF para PF)."
  },
  {
    "padrao": "Aluguéis não reinvestidos",
    "evidencia": "R$9.452/mês em aluguéis entram nas contas e se misturam com despesas correntes, sem direcionamento para investimento.",
    "mudanca_sugerida": "Configurar débito automático dos aluguéis (BTG + Itaú) direto para os investimentos no dia seguinte ao crédito."
  }
]
```

---

### Blocos obrigatórios da Seção 3 — Investimentos e Rendimentos (`secao-3`)

A seção 3 contém **5 subsseções**, das quais **3 blocos são OBRIGATÓRIOS** e devem aparecer SEMPRE, mesmo que dados parciais estejam faltando. O E5 DEVE verificar a presença desses 3 blocos; se qualquer um estiver ausente, o relatório falhou e deve ser refeito.

---

### Card obrigatório: 3.1 KPIs de Rentabilidade + Tabela por Bloco (dentro de `secao-3` — OBRIGATÓRIO)

**Regra:** Este bloco DEVE ser gerado SEMPRE na secao-3, logo após o summary. Inclui 4 KPI cards de rentabilidade consolidada + tabela detalhada por bloco/instituição. Se algum bloco não tiver dados de retorno, exibir "N/D" na coluna correspondente — **nunca omitir o bloco inteiro**.

**Posição no HTML:** Primeiro conteúdo dentro de `secao-3`, após o `section-summary`.

**Fonte de dados:**
- KPIs consolidados: `report-data.investimentos.kpis` (calculados no E4 a partir de todos os extratos de investimento)
- Tabela por bloco: `report-data.investimentos.blocos[]` (cada instituição com saldo e retorno)
- CDI referência: `report-data.investimentos.cdi_anual` (taxa Selic vigente)

**Info bar (acima dos KPIs):**
⚠️ **NÃO usar `<div class="section-summary">` aqui** — o template já injeta o summary via `{{SUMMARY_S3}}`. Esta info bar deve ser um `<p>` simples dentro do conteúdo:
```html
<p class="text-sm text-muted">
  {{qtd_imoveis}} imóveis ({{qtd_renda}} para renda) · Yield médio {{yield_medio}}% · Custo de oportunidade R$ {{custo_oportunidade}}/ano · {{melhor_yield_nome}} melhor yield ({{melhor_yield_pct}}%).
</p>
```

**REGRA CRÍTICA — Rentabilidade: NUNCA hardcodar valores de rentabilidade (anual, mensal, % CDI, retorno real).** Esses KPIs DEVEM ser calculados a partir de dados reais de performance extraídos dos relatórios das corretoras. Se os dados de performance (valor aplicado, rentabilidade acumulada por ativo) não estiverem disponíveis nos extratos processados (E2/E3), os KPIs devem exibir "N/D" e um alerta amarelo deve ser renderizado abaixo do card informando: "Dados de performance por ativo indisponíveis. Incluir relatórios de rentabilidade das corretoras no inbox para calcular." Quando os relatórios de performance estiverem disponíveis, o E4 deve calcular: rentabilidade ponderada por valor de cada ativo, rentabilidade consolidada da carteira, retorno real (nominal − IPCA), e % do CDI.

**Estrutura HTML dos 4 KPIs:**
```html
<div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr);">
  <div class="kpi-card">
    <div class="kpi-label">RENTABILIDADE ANUAL</div>
    <div class="kpi-value">{{rent_anual}}%</div>
    <div class="kpi-sub">nominal bruta</div>
  </div>
  <div class="kpi-card kpi-card-accent">
    <div class="kpi-label">RENTABILIDADE MENSAL</div>
    <div class="kpi-value green">{{rent_mensal}}%</div>
    <div class="kpi-sub">ponderada por bloco</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">% DO CDI</div>
    <div class="kpi-value">{{pct_cdi}}%</div>
    <div class="kpi-sub">CDI atual: {{cdi_anual}}% a.a.</div>
  </div>
  <div class="kpi-card kpi-card-accent">
    <div class="kpi-label">RETORNO REAL</div>
    <div class="kpi-value green">{{retorno_real}}%</div>
    <div class="kpi-sub">acima da inflação</div>
  </div>
</div>
```

**Estrutura HTML da tabela 3.1:**
```html
<div class="card">
  <h3>3.1 Rentabilidade e Performance</h3>
  <table>
    <thead>
      <tr>
        <th style="text-align:left;">BLOCO</th>
        <th style="text-align:right;">VALOR</th>
        <th style="text-align:right;">RET. ANUAL</th>
        <th style="text-align:right;">RET. MENSAL</th>
        <th style="text-align:center;">% CDI</th>
      </tr>
    </thead>
    <tbody>
      <!-- Para cada item em investimentos.blocos[] -->
      <tr>
        <td>{{nome_bloco}}</td>
        <td style="text-align:right;">R$ {{valor}}</td>
        <td style="text-align:right;">{{ret_anual}}%</td>
        <td style="text-align:right;">{{ret_mensal}}%</td>
        <td style="text-align:center;">
          <span class="badge-{{cor_cdi}}">{{pct_cdi}}%</span>
        </td>
      </tr>
      <!-- Linha TOTAL -->
      <tr class="total-row">
        <td><strong>TOTAL</strong></td>
        <td style="text-align:right;"><strong>R$ {{total_investido}}</strong></td>
        <td style="text-align:right;"><strong>{{total_ret_anual}}%</strong></td>
        <td style="text-align:right;"><strong>{{total_ret_mensal}}%</strong></td>
        <td style="text-align:center;"><span class="badge-{{cor_cdi_total}}">{{total_pct_cdi}}%</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

**Badges de % CDI:** `badge-green` se ≥90%, `badge-yellow` se 60-89%, `badge-red` se <60%.

**JSON em `report-data` (exemplo):**
```json
"investimentos": {
  "cdi_anual": 13.75,
  "kpis": {
    "rent_anual": 11.1,
    "rent_mensal": 0.88,
    "pct_cdi": 81,
    "retorno_real": 6.0
  },
  "blocos": [
    {"nome": "Itaú (Cofrinhos + PGBL)", "valor": 225207, "ret_anual": 13.5, "ret_mensal": 1.07, "pct_cdi": 98},
    {"nome": "Santander (3 CDBs)", "valor": 299478, "ret_anual": 13.5, "ret_mensal": 1.07, "pct_cdi": 98},
    {"nome": "Rico (fundos + ações + caixa)", "valor": 278917, "ret_anual": 8.0, "ret_mensal": 0.64, "pct_cdi": 58},
    {"nome": "BTG Pactual (Mariana)", "valor": 375385, "ret_anual": 10.8, "ret_mensal": 0.86, "pct_cdi": 79},
    {"nome": "PicPay (RDB)", "valor": 53757, "ret_anual": 13.1, "ret_mensal": 0.59, "pct_cdi": 95},
    {"nome": "Caixa / USD", "valor": 51802, "ret_anual": 3.0, "ret_mensal": 0.25, "pct_cdi": 22}
  ],
  "total": {"valor": 1284546, "ret_anual": 11.1, "ret_mensal": 0.88, "pct_cdi": 81}
}
```

**Se `investimentos.blocos` estiver vazio ou ausente**, gerar tabela com uma linha: "Dados de investimentos não disponíveis neste ciclo — processar extratos de corretoras (E2) para popular." Os KPIs devem exibir "N/D".

---

### Card obrigatório: 3.2 Estratégia de Aporte e Alocação (dentro de `secao-3` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-3, logo após a tabela 3.1 Rentabilidade. Mostra a estratégia fixa de aporte mensal com destinos, valores, objetivos e liquidez. Os destinos e valores DEVEM vir de `docs/methodology/definitions.md` seção "ESTRATÉGIA DE APORTES MENSAIS" — **nunca hardcodar valores no template ou no E5**. Mesmo sem dados de retorno, o card aparece com os dados de `definitions.md`.

**Posição no HTML:** Após o bloco 3.1, antes dos cards de ações diretas.

**Fonte de dados:**
- Destinos e valores: `docs/methodology/definitions.md` seção "ESTRATÉGIA DE APORTES MENSAIS"
- Configuração: `report-data.investimentos.estrategia_aporte` (gerado no E4 lendo definitions.md)

**Estrutura HTML:**
```html
<div class="card card-feature">
  <h3>3.2 Estratégia de Aporte e Alocação</h3>
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
    <span style="font-size: 20px;">💰</span>
    <strong>Aporte Mensal — R$ {{total_aporte}} (todo dia {{dia_aporte}})</strong>
  </div>
  <p class="text-sm text-muted">A partir de {{periodo_inicio}}. Distribuição fixa entre {{qtd_destinos}} destinos, equilibrando liquidez, proteção contra inflação e dolarização.</p>

  <table>
    <thead>
      <tr>
        <th style="text-align:left;">DESTINO</th>
        <th style="text-align:right;">VALOR/MÊS</th>
        <th style="text-align:right;">%</th>
        <th style="text-align:left;">OBJETIVO</th>
        <th style="text-align:left;">LIQUIDEZ</th>
      </tr>
    </thead>
    <tbody>
      <!-- Para cada item em estrategia_aporte.destinos[] (ordem do definitions.md, apenas os 4 do aporte principal de R$20k) -->
      <tr>
        <td><strong>{{destino}}</strong></td>
        <td style="text-align:right;">R$ {{valor}}</td>
        <td style="text-align:right;">{{pct}}%</td>
        <td>{{objetivo}}</td>
        <td>{{liquidez}}</td>
      </tr>
      <!-- Linha TOTAL -->
      <tr class="total-row">
        <td><strong>TOTAL</strong></td>
        <td style="text-align:right;"><strong>R$ {{total_aporte}}</strong></td>
        <td style="text-align:right;"><strong>100%</strong></td>
        <td></td>
        <td></td>
      </tr>
    </tbody>
  </table>

  <!-- Resumo BRL vs USD -->
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px;">
    <div class="card card-success" style="padding: 12px;">
      <strong>💰 {{pct_brl}}% em BRL</strong> ({{destinos_brl}}): {{resumo_brl}}
    </div>
    <div class="card card-highlight" style="padding: 12px;">
      <strong>🇺🇸 {{pct_usd}}% em USD</strong> ({{destinos_usd}}): {{resumo_usd}}
    </div>
  </div>
</div>
```

**JSON em `report-data` (exemplo):**
```json
"estrategia_aporte": {
  "total_aporte": 20000,
  "dia_aporte": 5,
  "periodo_inicio": "abr/2026",
  "destinos": [
    {"destino": "CDB Cofrinhos Itaú", "valor": 10000, "pct": 50, "objetivo": "Reserva de emergência + liquidez", "liquidez": "D+0", "moeda": "BRL"},
    {"destino": "Tesouro IPCA+", "valor": 5000, "pct": 25, "objetivo": "Proteção inflação, RF longa", "liquidez": "D+1 (com marcação)", "moeda": "BRL"},
    {"destino": "IVVB11 (ETF S&P 500)", "valor": 3000, "pct": 15, "objetivo": "Dolarização indireta + RV global", "liquidez": "D+2", "moeda": "USD"},
    {"destino": "Wise USD", "valor": 2000, "pct": 10, "objetivo": "Dolarização direta (acumulação pré-EUA)", "liquidez": "Imediata", "moeda": "USD"}
  ],
  "pct_brl": 75,
  "pct_usd": 25,
  "destinos_brl": "Cofrinhos + IPCA+",
  "destinos_usd": "IVVB11 + Wise",
  "resumo_brl": "Reforça reserva e patrimônio em reais. Meta: reduzir concentração em imóveis de 65% para 55%.",
  "resumo_usd": "Exposição total ao dólar = R$ 5.000/mês. Wise gera ~US$ 340/mês. Meta pré-EUA: US$ 20.000 (~37 meses)."
}
```

**Se `estrategia_aporte` estiver ausente**, gerar card com dados lidos diretamente de `definitions.md` seção "ESTRATÉGIA DE APORTES MENSAIS". Este card NUNCA deve ficar vazio.

---

### Card obrigatório: Estratégia de Contrafluxo na Renda Fixa (dentro de `secao-3` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-3, logo após o card 3.2 Estratégia de Aporte. Explica a lógica de contrafluxo (comprar o que o mercado está evitando) com tabela de cenários por nível de Selic. Mesmo sem mudanças no cenário macro, o card aparece como referência educacional.

**Posição no HTML:** Após o card 3.2 Estratégia de Aporte, antes dos cards de ações diretas (3.3).

**Fonte de dados:**
- Cenário atual: `report-data.investimentos.contrafluxo` (gerado no E4 com base na Selic vigente)
- Selic vigente: `report-data.investimentos.cdi_anual`

**Estrutura HTML:**
```html
<div class="card card-primary">
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
    <span style="font-size: 18px;">↔</span>
    <strong>Estratégia de Contrafluxo na Renda Fixa</strong>
  </div>
  <p class="text-sm text-muted">A divisão do aporte (R${{valor_cdi}}/mês CDI + R${{valor_ipca}}/mês IPCA+) não deve ser estática — deve se adaptar ao ciclo de juros. O princípio do <strong>contrafluxo</strong>: compre o que o mercado está evitando, porque é onde estão as melhores taxas.</p>

  <table>
    <thead>
      <tr>
        <th style="text-align:left;">CENÁRIO DE JUROS</th>
        <th style="text-align:center;">SELIC</th>
        <th style="text-align:left;">O QUE FAZER</th>
        <th style="text-align:left;">POR QUÊ</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>🔴 Selic alta {{marcador_agora_alta}}</td>
        <td style="text-align:center;">{{selic_alta}}</td>
        <td><strong>Travar IPCA+ e pré-fixados longos</strong></td>
        <td>Taxas de IPCA+6-7% são excepcionais. Quando a Selic cair, essas taxas desaparecem. Quem travou ganha na marcação a mercado + taxa real alta.</td>
      </tr>
      <tr>
        <td>🟡 Selic em queda {{marcador_agora_queda}}</td>
        <td style="text-align:center;">{{selic_queda}}</td>
        <td>Manter IPCA+, começar CDI</td>
        <td>CDI ainda paga bem; IPCA+ já travado continua rendendo.</td>
      </tr>
      <tr>
        <td>🟢 Selic baixa {{marcador_agora_baixa}}</td>
        <td style="text-align:center;">{{selic_baixa}}</td>
        <td>CDI pós-fixado e pré-fixados</td>
        <td>IPCA+ paga pouco (IPCA+3-4%). CDI protege liquidez. Pré-fixados travam a taxa alta antes de cair mais.</td>
      </tr>
    </tbody>
  </table>

  <p style="margin-top: 12px;"><strong>Ação prática:</strong> {{acao_pratica}}</p>
</div>
```

**Marcador "(AGORA)":** O cenário correspondente à Selic vigente recebe `{{marcador_agora_X}} = "(AGORA)"`, os outros ficam vazios.

**JSON em `report-data` (exemplo):**
```json
"contrafluxo": {
  "cenario_atual": "alta",
  "selic_atual": 13.75,
  "selic_alta": "13,75%",
  "selic_queda": "10-12%",
  "selic_baixa": "6-8%",
  "valor_cdi": 10000,
  "valor_ipca": 5000,
  "acao_pratica": "Após a reserva de emergência atingir 12 meses (R$ 382k), redirecionar os R$ 10k dos Cofrinhos: R$ 5k para Cofrinhos (manutenção) + R$ 5k para Tesouro IPCA+ 2035/2040 (travando IPCA+7%). Isso aproveita o momento de Selic alta para travar taxas reais excelentes antes do ciclo virar."
}
```

**Se `contrafluxo` estiver ausente**, gerar card com cenário padrão usando a Selic de `cdi_anual`. Este card é educacional e NUNCA deve ser omitido.

---

### Validação E5 para Seção 3

O HTML final da `secao-3` DEVE conter obrigatoriamente:

1. **4 KPI cards** de rentabilidade (classes `kpi-card` dentro de `kpi-grid`)
2. **Tabela 3.1** com pelo menos 1 linha de bloco/instituição (ou mensagem "dados não disponíveis")
3. **Card 3.2** com tabela de destinos de aporte (deve ter todas as linhas de `definitions.md`)
4. **Card Contrafluxo** com tabela de 3 cenários de Selic

Se qualquer um desses 4 elementos estiver ausente, o E5 falhou e deve ser refeito. Os demais subsseções (3.3 Ações Diretas, 3.4 Análise Ativos, 3.5 Consolidação Corretoras) são condicionais — aparecem quando há dados disponíveis.

---

### Card obrigatório: Endividamento (dentro de `secao-1` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-1 (Visão Geral Patrimonial), após o card de quitação. Mostra a relação dívida/patrimônio, composição das dívidas e cronograma de quitação. Mesmo que não haja dívidas ativas, gerar versão positiva.

**Posição no HTML:** Dentro de `secao-1`, após o card de quitação, antes do fechamento da seção.

**Fonte de dados:**
- Dívidas ativas: `report-data.endividamento` (gerado no E4 a partir de `despesas-3_unified.json` + `patrimonio-3_unified.json`)
- Patrimônio bruto: `report-data.patrimonio.total_bruto`
- Categorias: financiamento imobiliário, consórcio, cartão parcelado, empréstimo, cheque especial

**Estrutura HTML (quando há dívidas):**
```html
<div class="card card-feature">
  <div class="card-title">Endividamento — Relação Dívida / Patrimônio</div>
  <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
    <div class="kpi-card"><div class="kpi-value">R$ {{total_dividas}}</div><div class="kpi-label">Dívidas Ativas</div></div>
    <div class="kpi-card"><div class="kpi-value">{{pct_divida_patrimonio}}%</div><div class="kpi-label">Dívida / Patrimônio Bruto</div></div>
    <div class="kpi-card"><div class="kpi-value">{{classificacao}}</div><div class="kpi-label">Classificação</div></div>
  </div>
  <table>
    <thead><tr><th>DÍVIDA</th><th>SALDO DEVEDOR</th><th>PARCELA</th><th>TAXA</th><th>TÉRMINO</th><th>AÇÃO</th></tr></thead>
    <tbody>
      <!-- Para cada item em endividamento.dividas[] -->
      <tr><td>{{descricao}}</td><td>R$ {{saldo}}</td><td>R$ {{parcela}}</td><td>{{taxa}}% a.a.</td><td>{{termino}}</td><td>{{acao_recomendada}}</td></tr>
    </tbody>
  </table>
  <p><strong>Recomendação:</strong> {{recomendacao_geral}}</p>
</div>
```

**Se `endividamento.dividas[]` estiver vazio:**
```html
<div class="card card-success">
  <div class="card-title">✅ Endividamento — Família Sem Dívidas Ativas</div>
  <p>Nenhuma dívida ativa identificada. A família opera 100% livre de financiamentos, o que maximiza a capacidade de aporte mensal de R$ {{aporte_mensal}} para independência financeira.</p>
</div>
```

**JSON em `report-data`:**
```json
"endividamento": {
  "total_dividas": 0,
  "pct_divida_patrimonio": 0.0,
  "classificacao": "Livre de Dívidas",
  "recomendacao_geral": "Manter disciplina atual.",
  "dividas": []
}
```

---

### Card obrigatório: Reserva de Emergência (dentro de `secao-1` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-1 (Visão Geral Patrimonial), após o waterfall meta IF e antes do card de quitação. Apresenta 3 critérios de reserva (mínimo, conforto, conservador) e compara com a liquidez imediata disponível. Metodologia: Bruno Perini (mínimo 6 meses) + Cerbasi (12 meses para famílias com dependentes).

**Posição no HTML:** Dentro de `secao-1`, após o waterfall e antes da reserva oportunidade.

**Fonte de dados:**
- Despesas mensais: `report-data.reserva_emergencia.despesa_mensal` (média de `despesas-3_unified.json`)
- Liquidez imediata: `report-data.reserva_emergencia.liquidez_imediata` (soma CDB liquidez diária + Selic + poupança + conta corrente)
- Cálculos dos 3 níveis: E4 calcula `minimo_6m`, `conforto_9m`, `conservador_12m`

**Estrutura HTML:**
```html
<div class="card card-feature">
  <div class="card-title">Reserva de Emergência — 3 Critérios</div>
  <p>Baseado na despesa mensal média de <strong>R$ {{despesa_mensal}}</strong>:</p>

  <!-- Tabela 1: Níveis de cobertura -->
  <table>
    <thead><tr><th>Critério</th><th>Meses</th><th>Valor Necessário</th><th>Liquidez Atual</th><th>Status</th></tr></thead>
    <tbody>
      <tr><td>Mínimo (Perini)</td><td>6</td><td>R$ {{minimo_6m}}</td><td rowspan="3">R$ {{liquidez_imediata}}<br><small>({{cobertura_meses}} meses)</small></td><td>{{status_minimo}}</td></tr>
      <tr><td>Conforto</td><td>9</td><td>R$ {{conforto_9m}}</td><td>{{status_conforto}}</td></tr>
      <tr><td>Conservador (Cerbasi)</td><td>12</td><td>R$ {{conservador_12m}}</td><td>{{status_conservador}}</td></tr>
    </tbody>
  </table>

  <!-- Tabela 2: Composição da liquidez imediata -->
  <p><strong>Composição da Liquidez Imediata:</strong></p>
  <table>
    <thead><tr><th>Componente</th><th>Valor (R$)</th><th>Liquidez (Resgate)</th></tr></thead>
    <tbody>
      <!-- Iterar sobre composicao_liquida do E4: cada ativo com valor > 0 -->
      <tr><td>{{nome_ativo}}</td><td>R$ {{valor}} ({{pct_do_total}}%)</td><td>{{prazo_resgate: D+0, D+1}}</td></tr>
      ...
      <tr style="font-weight:bold;"><td>Total</td><td>R$ {{total_liquido}}</td><td>—</td></tr>
    </tbody>
  </table>

  <!-- Rodapé: critérios de inclusão na reserva -->
  <p style="font-size:0.85em; color:#666;">
    <strong>Nota:</strong> Consideram-se reserva de emergência apenas ativos com liquidez D+0 ou D+1
    e sem volatilidade relevante: CDB liquidez diária, Tesouro Selic, poupança e contas remuneradas.
    Não se incluem: CDB com vencimento, fundos de ações, multimercado, criptomoedas ou imóveis.
  </p>
</div>
```

**JSON em `report-data`:**
```json
"reserva_emergencia": {
  "despesa_mensal": 32950,
  "periodo_meses": 11,
  "liquidez_imediata": 284000,
  "cobertura_meses": 8.6,
  "minimo_6m": 197700,
  "conforto_9m": 296550,
  "conservador_12m": 395400,
  "status_minimo": "✅ Coberto",
  "status_conforto": "⚠ Parcial",
  "status_conservador": "❌ Abaixo",
  "composicao_liquida": {
    "cofrinhos_itau": 180000,
    "cdb_santander": 74000,
    "conta_corrente": 30000,
    "total_liquido": 284000
  },
  "recomendacao": "Priorizar completar o nível conforto (9 meses) antes de aumentar posição em ativos ilíquidos."
}
```

---

## DETALHAMENTO DE SEÇÕES FALTANTES (S4, S5, S6, S8, S9, Apêndices)

As seções abaixo tinham apenas descrição de uma linha na tabela de seções. Para que o E-reset funcione sem ambiguidade, o E5 precisa de instruções explícitas de layout e dados.

---

### Seção 4 — Imóveis e Bens (`secao-4`)

**Fonte de dados:** `patrimonio-3_unified.json` (categoria `imoveis`), `imoveis-3_unified.json` / `dados_imoveis-2_extract.json`, XLSX original, IRPF.

**Card obrigatório: Patrimônio Imobiliário**

```html
<div class="card">
  <div class="card-title card-title-lg">Patrimônio Imobiliário</div>
  <table>
    <thead>
      <tr><th>#</th><th>IMÓVEL</th><th>ÁREA</th><th>DONO</th><th>COMPRA</th><th>VALOR IRPF</th><th>ALUGUEL</th><th>STATUS</th></tr>
    </thead>
    <tbody>
      <!-- Para cada imóvel em patrimonio.imoveis[] -->
      <tr><td>{{num}}</td><td>{{descricao}}</td><td>{{area_m2}}m²</td><td>{{titular}}</td><td>{{data_compra}}</td><td>R$ {{valor_irpf}}</td><td>R$ {{aluguel_mensal}}</td><td>{{status}}</td></tr>
      <!-- Linha total -->
      <tr class="total-row"><td colspan="5"><strong>TOTAL ({{qtd_imoveis}} imóveis)</strong></td><td><strong>R$ {{total_irpf}}</strong></td><td><strong>R$ {{total_aluguel}}</strong></td><td></td></tr>
    </tbody>
  </table>
</div>
```

**Blocos adicionais (condicionais — gerar quando dados disponíveis):**
- **Yield vs CDI:** gráfico `chart-yield-imoveis` (bar) + card com cálculo `(aluguel_anual / valor_estimado) × 100` por imóvel. **OBRIGATÓRIO:** incluir nota explicativa do conceito de yield antes do gráfico — "Yield (rentabilidade) é o retorno anual que o imóvel gera em aluguéis, expresso como % do valor estimado. Fórmula: (aluguel anual ÷ valor estimado) × 100. Comparar com CDI ajuda a avaliar se o capital imobilizado rende mais ou menos que aplicação de baixo risco."
- **Custo de oportunidade:** card mostrando quanto o capital imobilizado renderia se investido (CDI × valor_estimado)
- **Simulação Barão→FIIs:** card com cenário hipotético de venda do imóvel menos rentável e reinvestimento em 5 FIIs de referência, com disclaimer "cenário educacional"

**JSON em `report-data` (exemplo parcial):**
```json
"patrimonio": {
  "imoveis": [
    {"num": 1, "descricao": "Apt. Barão de Jaceguai 71m²", "area_m2": 71, "titular": "David", "data_compra": "2014-03", "valor_irpf": 297000, "valor_estimado": 550000, "aluguel_mensal": 3200, "yield_anual_pct": 6.98, "status": "Alugado"},
    {"num": 2, "descricao": "Apt. Sabiá 51m²", "area_m2": 51, "titular": "Mariana", "data_compra": "2017-06", "valor_irpf": 230000, "valor_estimado": 400000, "aluguel_mensal": 2500, "yield_anual_pct": 7.50, "status": "Alugado"}
  ],
  "total_irpf": 1200000,
  "total_estimado": 2100000,
  "total_aluguel_mensal": 9452,
  "imoveis_estimado": 2100000
}
```

---

### Seção 5 — F1/F2 EUA (`secao-5`)

**Fonte de dados:** `life_plan/life_plan_goals.md` (seção F1/F2), E4 cálculos de custos.

**Estrutura de conteúdo:**
1. **Stacked bar `chart-custos-eua`:** custos mensais em USD por categoria (tuition, moradia, saúde, transporte, alimentação), com tooltip mostrando equivalente BRL
2. **Checklist de status:** tabela com itens DECIDIDO/PENDENTE para cada etapa do processo F1/F2

```html
<div class="chart-container">
  <p class="chart-context">Custos mensais estimados da fase F1/F2, baseados no plano de vida atualizado em {{data_life_plan}}.</p>
  <canvas id="chart-custos-eua" data-type="bar-stacked"></canvas>
  <p class="chart-conclusion">{{conclusao_custos}}</p>
</div>

<div class="card">
  <div class="card-title">Checklist F1/F2 — Status das Decisões</div>
  <table>
    <thead><tr><th>ITEM</th><th>STATUS</th><th>DETALHE</th><th>PRAZO</th></tr></thead>
    <tbody>
      <!-- Para cada item em f1f2_checklist[] -->
      <tr><td>{{item}}</td><td><span class="priority-badge priority-{{cor}}">{{status}}</span></td><td>{{detalhe}}</td><td>{{prazo}}</td></tr>
    </tbody>
  </table>
</div>
```

---

### Seção 6 — Green Card (`secao-6`)

**Fonte de dados:** `life_plan/life_plan_goals.md` (seção Green Card), E4 cenários cambiais.

**Estrutura de conteúdo:**
1. **Gráfico `chart-cenarios-cambio`:** bar agrupado com sobra mensal por cenário cambial (USD 4.50 / 5.50 / 6.50), com e sem renda Mariana
2. **Card Dolarização:** estratégia de exposição ao dólar (Wise + IVVB11 + ativos USD)
3. **Card Proteção Patrimonial — 5 Riscos:** tabela com risco cambial, fiscal, migratório, saúde, e carreira + mitigações

```html
<div class="chart-container">
  <p class="chart-context">Simulação de fluxo de caixa mensal nos EUA em 3 cenários de câmbio.</p>
  <canvas id="chart-cenarios-cambio" data-type="bar-grouped"></canvas>
  <p class="chart-conclusion">{{conclusao_cambio}}</p>
</div>

<div class="card card-highlight">
  <div class="card-title">Proteção Patrimonial — 5 Riscos da Migração</div>
  <table>
    <thead><tr><th>RISCO</th><th>PROBABILIDADE</th><th>IMPACTO</th><th>MITIGAÇÃO</th></tr></thead>
    <tbody>
      <!-- Para cada item em riscos_migracao[] -->
      <tr><td><strong>{{risco}}</strong></td><td>{{probabilidade}}</td><td>{{impacto}}</td><td>{{mitigacao}}</td></tr>
    </tbody>
  </table>
</div>
```

---

### Seção 8 — Tributário (`secao-8`)

**Fonte de dados:** E4 análise tributária, `despesas-3_unified.json` (categoria impostos), `receitas-3_unified.json`.

**Estrutura de conteúdo (5 blocos):**

1. **DAS Irregular:** card `.card-critical` com status dos pagamentos DAS, meses atrasados, multas estimadas
2. **Simples vs Lucro Presumido:** card com tabela comparativa de carga tributária nos dois regimes
3. **PGBL Portabilidade:** card com análise de fundos disponíveis e recomendação (conecta com card PGBL da S7)
4. **Carnê-leão passo-a-passo:** card `.card` com tabela `.table-steps` de 7 etapas (site Receita Federal → login Gov.br → declarar aluguéis → gerar DARF → pagar)
5. **Calendário tributário:** tabela com datas de vencimento mensais (DAS dia 20, IRRF, IRPF provisão, etc.)
6. **Gráfico `chart-impostos-pj`:** bar comparando imposto pago mês a mês vs ideal

```html
<div class="card card-critical">
  <div class="card-title">DAS — Situação Irregular</div>
  <table>
    <thead><tr><th>MÊS</th><th>VALOR</th><th>STATUS</th><th>MULTA ESTIMADA</th></tr></thead>
    <tbody>
      <!-- Para cada mês em das_status[] -->
      <tr><td>{{mes}}</td><td>R$ {{valor}}</td><td><span class="priority-badge priority-{{cor}}">{{status}}</span></td><td>R$ {{multa}}</td></tr>
    </tbody>
  </table>
</div>

<div class="card">
  <div class="card-title">Carnê-Leão — Passo a Passo</div>
  <table class="table-steps">
    <thead><tr><th>ETAPA</th><th>AÇÃO</th><th>DETALHE</th></tr></thead>
    <tbody>
      <tr><td><strong>1</strong></td><td>Acessar Carnê-Leão Web</td><td>cav.receita.fazenda.gov.br → Login Gov.br</td></tr>
      <tr><td><strong>2</strong></td><td>Declarar aluguéis recebidos</td><td>Informar valor bruto mensal por imóvel</td></tr>
      <tr><td><strong>3</strong></td><td>Deduzir despesas permitidas</td><td>IPTU, condomínio pago pelo locador, comissão imobiliária</td></tr>
      <tr><td><strong>4</strong></td><td>Calcular imposto</td><td>Sistema aplica tabela progressiva automaticamente</td></tr>
      <tr><td><strong>5</strong></td><td>Gerar DARF</td><td>Código 0190 para pessoa física</td></tr>
      <tr><td><strong>6</strong></td><td>Pagar até último dia útil do mês seguinte</td><td>PIX, internet banking ou agência</td></tr>
      <tr><td><strong>7</strong></td><td>Exportar para IRPF anual</td><td>Na declaração de ajuste, importar dados do Carnê-Leão</td></tr>
    </tbody>
  </table>
</div>
```

---

### Seção 9 — Riscos e Proteção (`secao-9`)

**Fonte de dados:** E4 análise de riscos, `seguros` (chave #20 do JSON), `life_plan/life_plan_goals.md`.

**Estrutura de conteúdo (4 blocos):**

1. **Bubble chart `chart-mapa-riscos`:** X=Probabilidade (1-5), Y=Impacto financeiro (1-5), Raio=Severidade composta. Mínimo 8 riscos mapeados
2. **Card Seguros:** tabela cobertura atual vs recomendada (vida, DIT, residencial, auto), gap analysis com `.card-warn` para gaps
3. **Card Top 3 Mitigações:** ações prioritárias de mitigação de risco com custo estimado e impacto
4. **Card Planejamento Sucessório:** sub-blocos: testamentos BR (inventário vs testamento vital), procuração duradoura, holding familiar (análise custo/benefício), guardianship EUA (para filho menor)

```html
<div class="chart-container">
  <p class="chart-context">Mapa de riscos da família: cada bolha representa um risco, posicionado por probabilidade (X) e impacto financeiro (Y). O tamanho indica severidade composta.</p>
  <canvas id="chart-mapa-riscos" data-type="bubble"></canvas>
  <p class="chart-conclusion">{{conclusao_riscos}}</p>
</div>

<div class="card card-feature">
  <div class="card-title">Seguros — Cobertura Atual vs Recomendada</div>
  <table>
    <thead><tr><th>TIPO</th><th>SEGURADORA</th><th>COBERTURA ATUAL</th><th>RECOMENDADA</th><th>GAP</th><th>AÇÃO</th></tr></thead>
    <tbody>
      <!-- Para cada item em seguros.cobertura_atual[] + seguros.gap_analysis[] -->
      <tr><td>{{tipo}}</td><td>{{seguradora}}</td><td>R$ {{cobertura}}</td><td>R$ {{recomendada}}</td><td class="{{cor_gap}}">R$ {{gap}}</td><td>{{acao}}</td></tr>
    </tbody>
  </table>
</div>

<div class="card card-highlight">
  <div class="card-title">Planejamento Sucessório</div>
  <h3>Testamentos e Procuração (Brasil)</h3>
  <p>{{texto_testamento_br}}</p>
  <h3>Holding Familiar</h3>
  <p>{{texto_holding}}</p>
  <h3>Guardianship (EUA)</h3>
  <p>{{texto_guardianship}}</p>
</div>
```

---

## DETALHAMENTO DOS APÊNDICES (App A-E)

### Apêndice A — Definições e Siglas (`apendice-a`)

**Objetivo:** Glossário autocontido para leitor sem contexto prévio.

**Estrutura:** Tabela 3 colunas: Sigla/Termo, Significado, Seção de referência. Mínimo 20 termos: IF, TRS, CDI, IPCA+, DAS, PGBL, FII, ETF, DCA, Selic, IRPF, IRRF, CDB, RDB, Carnê-leão, Contrafluxo, Marcação a mercado, Yield, Gap IF, Score Financeiro.

```html
<div class="card">
  <div class="card-title">Glossário de Termos e Siglas</div>
  <table>
    <thead><tr><th>TERMO / SIGLA</th><th>SIGNIFICADO</th><th>SEÇÃO</th></tr></thead>
    <tbody>
      <!-- Alfabético, mínimo 20 termos -->
      <tr><td><strong>CDI</strong></td><td>Certificado de Depósito Interbancário — taxa de referência para renda fixa</td><td>S3</td></tr>
      <!-- ... -->
    </tbody>
  </table>
</div>
```

---

### Apêndice B — Premissas e Metodologia (`apendice-b`)

**Estrutura:** 2 cards.

Card 1 — Premissas: tabela com Premissa, Valor, Fonte (inflação IPCA, câmbio USD/BRL, rentabilidade real, taxa de desconto, horizonte, Selic).

Card 2 — Metodologias: 3 sub-seções (Bruno Perini: número IF = despesa anual / TRS; Cerbasi: equilíbrio presente×futuro; AUVP: contrafluxo + Cerrado).

---

### Apêndice C — Cenários de Sensibilidade (`apendice-c`)

**Estrutura:** Tabela otimista/base/pessimista para 4 variáveis (prazo IF, câmbio, Selic, imóveis) + gráfico `chart-cenarios-if` + stress-tests narrativos ("E se Selic cair a 8%?", "E se USD a 6,50?").

---

### Apêndice D — Referências e Recursos (`apendice-d`)

**Estrutura:** Lista organizada em 4 categorias: Livros (Perini, Cerbasi), Plataformas (AUVP, Kinvo, Status Invest), Ferramentas (Planilha simulação, Carnê-Leão Web), Contatos de assessores.

---

### Apêndice E — Próximos Ciclos e Roadmap (`apendice-e`)

**Estrutura (5 blocos):**
1. **Tarefas priorizadas:** tabela com colunas #, Tarefa, Prioridade (usar badges `priority-badge`), Responsável, Prazo, Status. Fonte: `tarefas[]`
2. **Viagens e Milhas:** gráfico `chart-viagens` + 3 mini-KPIs (orçamento anual R$45k, gasto confirmado, milhas acumuladas)
3. **NCLEX Roadmap:** 7 etapas com status (Mariana)
4. **Simulação Mariana:** gráfico `chart-mariana-cenarios` (aporte vs anos até IF)
5. **Calendário próximo ciclo:** tabela data/evento/responsável

---

### Card obrigatório: Previdência PGBL (dentro de `secao-7` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-7 (Independência Financeira), após a projeção de renda passiva por fonte. Aborda o benefício fiscal do PGBL (12% da renda tributável), portabilidade, e projeção de acumulação. Metodologia: Bruno Perini (PGBL como "imposto que volta") + AUVP (usar PGBL como alavanca, não como investimento principal).

**Posição no HTML:** Dentro de `secao-7`, após o bloco de renda passiva por fonte, antes do fechamento da seção.

**Fonte de dados:**
- Renda tributável: `report-data.previdencia_pgbl.renda_tributavel_anual`
- Limite dedução: 12% da renda tributável
- Aporte atual: `report-data.previdencia_pgbl.aporte_mensal_atual`
- Projeção: E4 calcula acumulação em 10/15/20 anos com taxa real de 6%

**Estrutura HTML:**
```html
<div class="card card-feature">
  <div class="card-title">Previdência PGBL — Benefício Fiscal + Acumulação</div>
  <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr);">
    <div class="kpi-card"><div class="kpi-value">R$ {{renda_tributavel_anual}}</div><div class="kpi-label">Renda Tributável Anual</div></div>
    <div class="kpi-card"><div class="kpi-value">R$ {{limite_pgbl_anual}}</div><div class="kpi-label">Limite PGBL (12%)</div></div>
    <div class="kpi-card"><div class="kpi-value">R$ {{aporte_mensal_atual}}</div><div class="kpi-label">Aporte Mensal Atual</div></div>
    <div class="kpi-card"><div class="kpi-value">R$ {{economia_ir_anual}}</div><div class="kpi-label">Economia IR/Ano</div></div>
  </div>
  <h3>Projeção de Acumulação (taxa real 6% a.a.)</h3>
  <table>
    <thead><tr><th>HORIZONTE</th><th>APORTE MENSAL</th><th>ACUMULADO</th><th>RENDA MENSAL (4% a.a.)</th></tr></thead>
    <tbody>
      <tr><td>10 anos</td><td>R$ {{aporte_mensal_atual}}</td><td>R$ {{acumulado_10a}}</td><td>R$ {{renda_10a}}</td></tr>
      <tr><td>15 anos</td><td>R$ {{aporte_mensal_atual}}</td><td>R$ {{acumulado_15a}}</td><td>R$ {{renda_15a}}</td></tr>
      <tr><td>20 anos</td><td>R$ {{aporte_mensal_atual}}</td><td>R$ {{acumulado_20a}}</td><td>R$ {{renda_20a}}</td></tr>
    </tbody>
  </table>
  <p><strong>Portabilidade:</strong> {{status_portabilidade}}</p>
  <p><strong>Recomendação:</strong> {{recomendacao}}</p>
</div>
```

**JSON em `report-data`:**
```json
"previdencia_pgbl": {
  "renda_tributavel_anual": 0,
  "limite_pgbl_anual": 0,
  "aporte_mensal_atual": 1800,
  "economia_ir_anual": 0,
  "acumulado_10a": 0,
  "acumulado_15a": 0,
  "acumulado_20a": 0,
  "renda_10a": 0,
  "renda_15a": 0,
  "renda_20a": 0,
  "status_portabilidade": "Pendente — avaliar fundos disponíveis",
  "recomendacao": "Calcular renda tributável real (CLT Mariana + pro-labore David) e confirmar se aporte atual atinge o teto de 12%."
}
```

---

### Card obrigatório: Pontos Fortes (dentro de `secao-10` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-10 (Conclusão e Roadmap), como primeiro conteúdo após o summary. Lista 5-7 destaques positivos da situação financeira da família. Tom: celebrativo e motivacional.

**Posição no HTML:** Primeiro conteúdo dentro de `secao-10`, após o `section-summary`.

**Fonte de dados:** `report-data.pontos_fortes[]` (gerado no E4, lista de strings)

**Estrutura HTML:**
```html
<div class="card card-success">
  <div class="card-title">✅ Pontos Fortes — O Que Já Funciona</div>
  <ul>
    <!-- Para cada item em pontos_fortes[] -->
    <li><strong>{{titulo}}</strong> — {{descricao}}</li>
  </ul>
</div>
```

**JSON em `report-data`:**
```json
"pontos_fortes": [
  {"titulo": "Taxa de poupança elevada", "descricao": "33% da renda líquida direcionada a investimentos — acima dos 20% recomendados por Cerbasi."},
  {"titulo": "Patrimônio diversificado", "descricao": "6 imóveis + carteira financeira em 8+ instituições reduz risco de concentração."},
  {"titulo": "Sem dívidas de consumo", "descricao": "Zero financiamentos ativos — toda renda disponível para acumulação."}
]
```

---

### Card obrigatório: Pontos Urgentes (dentro de `secao-10` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-10 (Conclusão e Roadmap), logo após o card Pontos Fortes. Lista 5-7 ações críticas priorizadas por impacto. Tom: direto e acionável (sem ser alarmista).

**Posição no HTML:** Após Pontos Fortes, antes do card Equilíbrio Cerbasi.

**Fonte de dados:** `report-data.pontos_urgentes[]` (gerado no E4, lista de objetos com prioridade)

**Estrutura HTML:**
```html
<div class="card card-warn">
  <div class="card-title">⚠ Pontos Urgentes — Ações Prioritárias</div>
  <table>
    <thead><tr><th>#</th><th>AÇÃO</th><th>IMPACTO</th><th>PRAZO SUGERIDO</th></tr></thead>
    <tbody>
      <!-- Para cada item em pontos_urgentes[], ordenados por prioridade -->
      <tr><td>{{prioridade}}</td><td><strong>{{acao}}</strong></td><td>{{impacto}}</td><td>{{prazo}}</td></tr>
    </tbody>
  </table>
</div>
```

**JSON em `report-data`:**
```json
"pontos_urgentes": [
  {"prioridade": 1, "acao": "Regularizar DAS e carnê-leão", "impacto": "Evitar multas + juros acumulados", "prazo": "Abril/2026"},
  {"prioridade": 2, "acao": "Completar reserva de emergência (9 meses)", "impacto": "Proteção contra imprevistos", "prazo": "Junho/2026"},
  {"prioridade": 3, "acao": "Eliminar uso de cheque especial", "impacto": "Economia R$1.400+/ano em juros", "prazo": "Imediato"}
]
```

---

### Card obrigatório: Equilíbrio Presente × Futuro — Cerbasi (dentro de `secao-10` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE na secao-10 (Conclusão e Roadmap), após o card Pontos Urgentes. Aplica o framework de Gustavo Cerbasi: equilibrar qualidade de vida presente com construção de patrimônio futuro. Analisa a proporção gastos-presente vs investimentos-futuro e classifica o equilíbrio.

**Posição no HTML:** Após Pontos Urgentes, antes do bloco "Top 5 Decisões".

**Fonte de dados:** `report-data.equilibrio_cerbasi` (gerado no E4)

**Estrutura HTML:**
```html
<div class="card card-highlight">
  <div class="card-title">Equilíbrio Presente × Futuro (Cerbasi)</div>
  <p>Gustavo Cerbasi defende que finanças saudáveis equilibram <strong>viver bem hoje</strong> com <strong>construir segurança amanhã</strong>. Nem só poupar, nem só gastar — encontrar o ponto ótimo para a fase de vida da família.</p>
  <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
    <div class="kpi-card"><div class="kpi-value">{{pct_presente}}%</div><div class="kpi-label">Gastos Presente</div></div>
    <div class="kpi-card"><div class="kpi-value">{{pct_futuro}}%</div><div class="kpi-label">Investimentos Futuro</div></div>
    <div class="kpi-card"><div class="kpi-value">{{classificacao}}</div><div class="kpi-label">Equilíbrio</div></div>
  </div>
  <p><strong>Análise:</strong> {{analise}}</p>
  <p><strong>Recomendação Cerbasi:</strong> {{recomendacao}}</p>
</div>
```

**Classificações possíveis:** "Equilibrado", "Pendendo para Futuro", "Pendendo para Presente", "Desequilibrado".

**JSON em `report-data`:**
```json
"equilibrio_cerbasi": {
  "pct_presente": 67,
  "pct_futuro": 33,
  "classificacao": "Equilibrado",
  "analise": "A família destina 33% ao futuro (acima dos 20% mínimos) mantendo R$32.950/mês para qualidade de vida presente. Com filho pequeno e plano migratório ativo, o equilíbrio está adequado à fase de vida.",
  "recomendacao": "Manter proporção atual. Quando custos EUA cessarem (~2028), redirecionar a diferença para acelerar IF sem sacrificar qualidade de vida."
}
```

---

### Regra obrigatória: Badges de Prioridade em tabelas (TODAS as seções)

Sempre que o E5 gerar uma tabela com coluna "Prioridade" (tarefas, pontos urgentes, ou qualquer lista priorizada), usar as **classes CSS do template** — NUNCA estilos inline com `background-color: inherit` ou cores hardcoded.

**Classes disponíveis no template:**
- `priority-badge priority-alta` → fundo vermelho, texto branco
- `priority-badge priority-media` → fundo azul escuro, texto branco
- `priority-badge priority-baixa` → fundo cinza, texto branco

**HTML correto para a célula de prioridade:**
```html
<td style="text-align:center; padding:6px 4px;"><span class="priority-badge priority-alta">Alta</span></td>
<td style="text-align:center; padding:6px 4px;"><span class="priority-badge priority-media">Média</span></td>
<td style="text-align:center; padding:6px 4px;"><span class="priority-badge priority-baixa">Baixa</span></td>
```

**Mapeamento do JSON do E4:** `tarefas[].p` → `"alta"` / `"media"` / `"baixa"`.

**NUNCA fazer:** `background-color: inherit`, `background-color: var(--color-bg-alt)`, ou qualquer cor inline. As classes CSS garantem contraste correto em light/dark mode.

---

### Schema JSON: `tarefas[]` (chave #18)

**Fonte:** E4 item 9 — geradas a partir de 12 critérios de gatilho (ver `e4_categorize.py`).

```json
"tarefas": [
  {
    "id": 1,
    "descricao": "Regularizar DAS atrasados",
    "categoria": "tributario",
    "p": "alta",
    "prazo": "2026-04-15",
    "responsavel": "David",
    "status": "pendente",
    "secao_ref": "S8",
    "gatilho": "DAS irregular detectado em E3"
  }
]
```

**Campos obrigatórios:** `id` (int sequencial), `descricao` (string), `categoria` (uma de: `tributario`, `investimentos`, `seguros`, `fluxo_caixa`, `patrimonio`, `planejamento`, `documentos`, `emergencia`), `p` (prioridade: `alta`/`media`/`baixa`), `prazo` (ISO date ou `"imediato"`), `responsavel` (`"David"`, `"Mariana"`, `"Ambos"`), `status` (`"pendente"`, `"em_andamento"`, `"concluida"`), `secao_ref` (seção do relatório), `gatilho` (critério que gerou a tarefa).

---

### Schema JSON: `tarefas_status` (chave #19)

**Fonte:** Agregação de `tarefas[]` para exibição no dashboard tático D3.

```json
"tarefas_status": {
  "total": 40,
  "concluidas": 12,
  "em_andamento": 8,
  "pendentes": 20,
  "pct_completo": 30,
  "por_categoria": {
    "tributario": {"total": 8, "concluidas": 2},
    "investimentos": {"total": 10, "concluidas": 4},
    "seguros": {"total": 5, "concluidas": 1},
    "fluxo_caixa": {"total": 6, "concluidas": 3},
    "patrimonio": {"total": 4, "concluidas": 1},
    "planejamento": {"total": 4, "concluidas": 1},
    "documentos": {"total": 2, "concluidas": 0},
    "emergencia": {"total": 1, "concluidas": 0}
  }
}
```

---

### Schema JSON: `seguros` (chave #20)

**Fonte:** E4 — extraído de `seguros-3_unified.json` (faturas e holerites que indicam prêmios de seguro).

```json
"seguros": {
  "cobertura_atual": [
    {
      "tipo": "vida",
      "seguradora": "Prudential",
      "titular": "David",
      "premio_mensal": 350,
      "cobertura": 500000,
      "vencimento": "2026-12-01",
      "status": "ativo"
    },
    {
      "tipo": "residencial",
      "seguradora": "Porto Seguro",
      "titular": "David",
      "premio_mensal": 120,
      "cobertura": 800000,
      "vencimento": "2026-08-15",
      "status": "ativo"
    }
  ],
  "gap_analysis": [
    {
      "tipo": "DIT (invalidez temporária)",
      "status": "sem_cobertura",
      "recomendacao": "Contratar DIT com cobertura de R$ 30.000/mês (renda mensal)",
      "impacto": "Risco crítico: sem renda PJ em caso de incapacidade"
    }
  ],
  "premio_total_mensal": 470,
  "pct_renda": 0.6
}
```

**Consumido por:** secao-9 (Riscos e Proteção) — tabela de seguros, gap analysis, e recomendações.

---

### Schema JSON: `tactical` (chave #17)

**Fonte:** E4 — agregação de dados para as 6 seções do modo tático (D1-D6).

```json
"tactical": {
  "despesas_por_categoria": [
    {
      "categoria": "Alimentação",
      "emoji": "🍽",
      "gasto_quinzena": 2100,
      "teto_mensal": 4500,
      "pct_consumido": 46.7,
      "status": "ok"
    }
  ],
  "aportes": [
    {
      "destino": "CDB Cofrinhos Itaú",
      "valor_planejado": 10000,
      "valor_realizado": 10000,
      "status": "concluido",
      "data": "2026-04-05"
    }
  ],
  "investimentos_delta": [
    {
      "instituicao": "Itaú",
      "saldo_anterior": 220000,
      "saldo_atual": 225207,
      "delta": 5207,
      "delta_pct": 2.4
    }
  ],
  "alertas": [
    {
      "severidade": "alta",
      "mensagem": "DAS março não pago — vence em 20/04",
      "categoria": "tributario",
      "acao": "Pagar via Simples Nacional"
    }
  ],
  "proximos_15d": [
    {
      "data": "2026-04-05",
      "acao": "Aporte mensal R$ 20k",
      "status": "agendado"
    }
  ],
  "notas": "Quinzena sem eventos extraordinários. Manter plano."
}
```

**Consumido por:** D1 (Fluxo Quinzena), D2 (Aportes), D3 (Checklist — via `tarefas_status`), D4 (Alertas), D5 (Próximos 15 dias), D6 (Notas).

---

### Schemas de Datasets de Gráficos Faltantes

**Chart #17 — `cenarios_mariana` (canvas: `chart-mariana-cenarios`):**
```json
"cenarios_mariana": {
  "labels": ["R$ 5k/mês", "R$ 10k/mês", "R$ 15k/mês", "R$ 20k/mês"],
  "data": [28, 19, 14, 11],
  "meta_label": "Anos até IF",
  "premissa_retorno": 6.0,
  "meta_patrimonio": 2000000
}
```

**Chart #18 — `performance_ativos` (canvas: `chart-performance-ativos`):**
```json
"performance_ativos": {
  "ativos": [
    {
      "nome": "CDB Santander 120% CDI",
      "valor": 150000,
      "retorno_acumulado_pct": 14.2,
      "retorno_benchmark_pct": 13.75,
      "delta_benchmark": 0.45,
      "tipo": "RF"
    }
  ],
  "benchmark": {"nome": "CDI", "retorno_pct": 13.75}
}
```

**Chart #19 — `viagens` (canvas: `chart-viagens`):**
```json
"viagens": {
  "teto_anual": 45000,
  "gasto_confirmado": 18500,
  "gasto_planejado": 12000,
  "disponivel": 14500,
  "detalhes": [
    {"destino": "Portugal", "valor": 18500, "status": "confirmado", "data": "2026-06"},
    {"destino": "EUA (visita)", "valor": 12000, "status": "planejado", "data": "2026-10"}
  ],
  "milhas_acumuladas": 85000,
  "milhas_meta": 150000
}
```

---

### Sempre visível (`data-mode="both"`)
- Cover hero + 8 KPIs estratégicos
- Card Perfil da Família
- Toggle modo dual na nav
- Rodapé

---

### Card obrigatório: Perfil da Família (`data-mode="both"` — OBRIGATÓRIO)

**Regra:** Este card DEVE ser gerado SEMPRE, em modo estratégico E tático. O E5 DEVE usar o formato abaixo como template literal, substituindo apenas os valores dinâmicos entre `[colchetes]`. O formato, a ordem dos parágrafos e o estilo de escrita são FIXOS — nunca reorganizar, nunca usar tabela, nunca usar bullet points, nunca omitir parágrafos.

**Posição no HTML:** Dentro do bloco `<!-- PERFIL DA FAMÍLIA -->`, populando `{{PERFIL_FAMILIA_LEFT}}` e `{{PERFIL_FAMILIA_RIGHT}}` (ou `{{PERFIL_FAMILIA}}` se template com coluna única).

**Fonte de dados:**
- Dados pessoais e profissionais: `members/members-1c_enriched.md`
- Plano de vida e metas: `life_plan/life_plan_goals.md`
- Patrimônio imobiliário: `patrimonio-3_unified.json` / `dados_imoveis-2_extract.json`
- Instituições financeiras: `investimentos-3_unified.json` / extratos reconciliados

**Formato obrigatório (6 parágrafos, nesta ordem exata):**

```
[Nome titular] ([idade] anos) — [cargo principal] e [atividade secundária]. [Detalhes profissionais: empresas, advisory, etc.]. [Formação acadêmica].

[Nome cônjuge] ([idade] anos) — [profissão e especialidade], [regime trabalho] no [empregador] há [tempo]. [Formação acadêmica].

[Nome filho(s)] ([idade]) — [local nascimento, cidadania]. [Plano de saúde].

[Animais de estimação] — [nomes]. [Nota sobre plano de saúde se relevante].

Plano de vida: [Resumo do plano migratório/vida em 1-2 frases, incluindo visto, universidade, cidade, objetivos].

Meta financeira: Independência Financeira — renda passiva de R$ [meta_renda]/mês (patrimônio de R$ [meta_patrimonio]), estimada para [ano_meta], quando [titular] terá [idade_no_ano] anos.

Patrimônio: [N] imóveis em [cidade(s)] + carteira financeira diversificada em [N]+ instituições ([lista das principais]).
```

**Regras de preenchimento:**
- Idades: calcular a partir da data de nascimento (de `members-1c_enriched.md`) e da data atual do relatório
- Meta IF: ler de `life_plan_goals.md` — campo `meta_renda_passiva` e `meta_patrimonio`. Se `meta_patrimonio` não estiver calculado, exibir "R$ ???M"
- Contagem de imóveis: contar de `patrimonio-3_unified.json` categoria `imoveis`
- Contagem de instituições: contar instituições distintas nos extratos reconciliados
- Se um membro não existir (ex: sem filhos, sem animais), OMITIR o parágrafo correspondente — não gerar parágrafo vazio
- Se `members-1c_enriched.md` não tiver dados suficientes para um campo, usar "—" como placeholder

**Distribuição LEFT/RIGHT (quando template usa 2 colunas):**
- `{{PERFIL_FAMILIA_LEFT}}`: parágrafos 1 a 4 (membros da família)
- `{{PERFIL_FAMILIA_RIGHT}}`: parágrafos 5 a 7 (plano de vida, meta, patrimônio)

**Validação E5:** O card DEVE conter no mínimo o parágrafo do titular e o parágrafo de meta financeira. Se `members-1c_enriched.md` não existir, o E5 deve falhar com erro explícito.

---

## SEÇÕES TÁTICO (D1-D6)

| ID | Seção | Conteúdo | Fonte de dados |
|---|---|---|---|
| `dash-kpis` | KPIs operacionais | Δ patrimônio, aportes X/4, categorias acima teto, tarefas X/40, alerta 1, alerta 2 | `report-data.tactical` |
| `dash-fluxo` | D1 — Fluxo da Quinzena | 13 categorias: gasto vs teto + barra progresso + badge | `tactical.despesas_por_categoria` |
| `dash-aportes` | D2 — Aportes e Investimentos | 6 cards (Cofrinhos/IPCA+/IVVB11/Wise/PGBL/DCA Crypto) + tabela saldos Δ | `tactical.aportes` + `tactical.investimentos_delta` |
| `dash-tarefas` | D3 — Checklist de Tarefas | 40 tarefas com status + barra progresso + filtros | `tactical.tarefas_status` |
| `dash-alertas` | D4 — Alertas e Pendências | Lista alertas com badges severidade | `tactical.alertas` |
| `dash-proximos` | D5 — Próximos 15 Dias | Timeline vertical data/ação/status | `tactical.proximos_15d` |
| `dash-notas` | D6 — Notas da Quinzena | Textarea readonly com notas livres | `tactical.notas` |

---

## MODO DUAL — MECANISMO CSS

```css
body.mode-strategic [data-mode="dashboard"] { display: none; }
body.mode-tactical [data-mode="strategic"] { display: none; }
[data-mode="both"] { display: block; }
```

Toggle alterna `document.body.className` entre `mode-strategic` e `mode-tactical`.

Modo padrão definido em `report-data.meta.modo_padrao`:
- Sessão quinzenal → `"tactical"`
- Sessão trimestral → `"strategic"`

---

## 19 GRÁFICOS OBRIGATÓRIOS

| # | Tipo | Descrição |
|---|---|---|
| 1 | Doughnut | Composição patrimônio investível |
| 2 | Bar horizontal (waterfall) | Patrimônio atual → Meta IF |
| 3 | Bar vertical (8 camadas empilhadas + barra vermelha) | Receita por 8 fontes separadas vs Despesa mês a mês |
| 4 | Doughnut | Distribuição despesas por categoria |
| 5 | Doughnut (gauge, 5 faixas + needle) | Score Financeiro — **OBRIGATÓRIO:** `<canvas id="chart-score-gauge" data-type="gauge" data-score="X.X">` onde X.X é o score calculado pelo E4. O JS do template lê `data-score` para posicionar a agulha e atualiza automaticamente o `<p class="chart-context">`. **NÃO** escrever texto "Avaliação consolidada: X/10" manualmente — o JS gera sozinho. |
| 6 | Doughnut | Alocação ATUAL — **conclusion DEVE exibir retorno real calculado vs meta 6% quando dados disponíveis; caso contrário exibir "não calculado" + alerta amarelo** |
| 7 | Doughnut | Alocação ALVO |
| 8 | Bar horizontal | Top 15 ativos financeiros por valor |
| 9 | Bar | Yield anual por imóvel vs CDI |
| 10 | Bar stacked | Custos mensais fase F1/F2 (tooltip R$8.919 BR) |
| 11 | Bar agrupado | Sobra mensal por cenário cambial (Green Card) |
| 12 | Line (3 séries) | Projeção patrimonial 3 cenários (começa R$3,65M) |
| 13 | Bar | Renda passiva atual vs meta (por fonte + gap) |
| 14 | Bar | Impostos PJ mês a mês vs ideal |
| 15 | Bubble | Mapa de riscos (X=Probabilidade, Y=Impacto, Raio=Severidade) |
| 16 | Bar horizontal | Top 5 decisões impacto 1 ano vs 10 anos |
| 17 | Bar + Line | Cenários IF Mariana (aporte vs anos) |
| 18 | Table/Chart | Performance dos Top Ativos (top 5-10 com nome, valor, retorno acumulado, retorno vs benchmark, indicador visual) |
| 19 | Bar horizontal stacked | Viagens: gasto confirmado vs disponível + 3 mini-KPIs |

**Todos os gráficos devem ter parágrafo de contexto antes E conclusão depois. Não deixar gráficos órfãos.**

### Mapeamento Canvas ID ↔ Chave JSON do Dataset

| # | Canvas ID (HTML) | Chave JSON em `charts` | Seção |
|---|---|---|---|
| 1 | `chart-patrimonio-doughnut` | `patrimonio_doughnut` | S1 |
| 2 | `chart-waterfall-if` | `waterfall_if` | S1 |
| 3 | `chart-receita-despesa-mensal` | `receita_despesa_mensal` | S2 |
| 4 | `chart-despesas-doughnut` | `despesas_doughnut` | S2 |
| 5 | `chart-score-gauge` | `score_gauge` | S2 |
| 6 | `chart-alocacao-atual` | `alocacao_atual` | S3 |
| 7 | `chart-alocacao-alvo` | `alocacao_alvo` | S3 |
| 8 | `chart-top-ativos` | `top_ativos` | S3 |
| 9 | `chart-yield-imoveis` | `yield_imoveis` | S4 |
| 10 | `chart-custos-eua` | `custos_f1f2` | S5 |
| 11 | `chart-cenarios-cambio` | `cenario_cambial` | S6 |
| 12 | `chart-projecao-patrimonial` | `projecao_if` | S7 |
| 13 | `chart-renda-passiva` | `renda_passiva` | S7 |
| 14 | `chart-impostos-pj` | `impostos_pj` | S8 |
| 15 | `chart-mapa-riscos` | `riscos_bubble` | S9 |
| 16 | `chart-decisoes-impacto` | `decisoes` | S10 |
| 17 | `chart-mariana-cenarios` | `cenarios_mariana` | App E |
| 18 | `chart-performance-ativos` | `performance_ativos` | S3 |
| 19 | `chart-viagens` | `viagens` | App E |

⚠️ O JS do template busca dados em `REPORT_DATA_JSON.charts[chave_json]`. Se a chave não existir, o canvas fica em branco (graceful degradation). O `chart-receita-camadas` é alias de `chart-receita-despesa-mensal` — mesmo dataset, mesmo canvas.

---

## 20 CHAVES TOP-LEVEL DO `REPORT_DATA_JSON`

Tabela consolidada de todas as chaves obrigatórias no JSON embutido no relatório. O E5.3 DEVE gerar TODAS elas. Cada chave tem schema detalhado mais abaixo neste documento ou nos scripts correspondentes (E4/E5).

| # | Chave | Fonte principal | Seção que consome | Schema neste doc? |
|---|---|---|---|---|
| 1 | `meta` | Fixo + E4 | Cover, Footer | ✅ (workflow) |
| 2 | `kpis` | E4 racios/patrimonio/goals/score | Cover KPIs | ✅ (E5.1 manual) |
| 3 | `patrimonio` | E4 patrimonio | S1, S7 (projeção IF) | ✅ (manual E5.3) |
| 4 | `charts` | E4 + E3 + life_plan | Todos os 19 gráficos | ✅ (tabela acima) |
| 5 | `orcamento_prospectivo` | E4 + definitions.md | S2 — Card Orçamento | ✅ |
| 6 | `consumo_consciente` | E4 | S2 — Card Consumo | ✅ |
| 7 | `diagnostico_comportamental` | E4 | S2 — Card Diagnóstico | ✅ |
| 8 | `investimentos` | E4 + E3 | S3 — KPIs + tabela 3.1 | ✅ |
| 9 | `estrategia_aporte` | definitions.md / E4 | S3 — Card 3.2 | ✅ |
| 10 | `contrafluxo` | E4 / Selic vigente | S3 — Card Contrafluxo | ✅ |
| 11 | `reserva_emergencia` | E4 | S1 — Card Reserva | ✅ |
| 12 | `endividamento` | E4 | S1 — Card Endividamento | ✅ |
| 13 | `previdencia_pgbl` | E4 | S7 — Card PGBL | ✅ |
| 14 | `pontos_fortes` | E4 | S10 — Card Pontos Fortes | ✅ |
| 15 | `pontos_urgentes` | E4 | S10 — Card Pontos Urgentes | ✅ |
| 16 | `equilibrio_cerbasi` | E4 | S10 — Card Equilíbrio | ✅ |
| 17 | `tactical` | E4 tarefas/alertas | D1-D6 (modo tático) | ✅ (abaixo) |
| 18 | `tarefas` | E4 | S10, App E, D3 | ✅ (abaixo) |
| 19 | `tarefas_status` | E4 | D3 — Checklist | ✅ (abaixo) |
| 20 | `seguros` | E4 + faturas/holerites | S9 — Seguros | ✅ (abaixo) |

---

## REGRA DE MAPEAMENTO E5 → SEÇÃO (ANTI-DESALINHAMENTO)

**Problema resolvido:** Na geração E5, o conteúdo injetado em `{{CONTENT_SN}}` DEVE corresponder ao H1 e ao summary que já existem no template para aquela seção. A tabela abaixo é a referência canônica — o E5 DEVE consultá-la antes de gerar cada bloco.

| Placeholder | Seção (H1 no template) | Conteúdo que DEVE ser injetado | Canvas IDs nesta seção |
|---|---|---|---|
| `{{CONTENT_S1}}` | Visão Geral Patrimonial | Doughnut patrimônio + waterfall + reserva emergência + reserva oportunidade + quitação + endividamento | `chart-patrimonio-doughnut`, `chart-waterfall-if` |
| `{{CONTENT_S2}}` | Fluxo de Caixa e Orçamento | Receita camadas + despesas doughnut + receita vs despesa mensal + score gauge + orçamento prospectivo + consumo consciente + diagnóstico comportamental | `chart-receita-camadas`, `chart-despesas-doughnut`, `chart-receita-despesa-mensal`, `chart-score-gauge` |
| `{{CONTENT_S3}}` | Investimentos e Rendimentos | 3.1 KPIs rentabilidade + 3.2 estratégia aporte + contrafluxo + 3.3 ações diretas + 3.4 análise ativos + 3.5 consolidação | `chart-alocacao-atual`, `chart-alocacao-alvo`, `chart-top-ativos`, `chart-performance-ativos` |
| `{{CONTENT_S4}}` | Imóveis e Bens | Patrimônio imobiliário tabela + yield vs CDI + custo oportunidade + simulação FIIs | `chart-yield-imoveis` |
| `{{CONTENT_S5}}` | F1/F2 EUA | Custos USD stacked bar + checklist | `chart-custos-eua` |
| `{{CONTENT_S6}}` | Green Card | Cenários cambiais + dolarização + proteção 5 riscos | `chart-cenarios-cambio` |
| `{{CONTENT_S7}}` | Independência Financeira | TRS + projeção 3 cenários + renda passiva + projeção 2035 + previdência PGBL | `chart-projecao-patrimonial`, `chart-renda-passiva` |
| `{{CONTENT_S8}}` | Tributário | DAS + Simples vs LP + PGBL portabilidade + carnê-leão + calendário | `chart-impostos-pj` |
| `{{CONTENT_S9}}` | Riscos e Proteção | Bubble chart riscos + seguros + top 3 mitigações + sucessório | `chart-mapa-riscos` |
| `{{CONTENT_S10}}` | Conclusão e Roadmap | Pontos fortes + pontos urgentes + equilíbrio Cerbasi + top 5 decisões + timeline | `chart-decisoes-impacto` |
| `{{CONTENT_APP_A}}` | Definições e Siglas | Glossário termos, siglas, categorias | — |
| `{{CONTENT_APP_B}}` | Premissas e Metodologia | Premissas + metodologias (Perini/Cerbasi/AUVP) | — |
| `{{CONTENT_APP_C}}` | Cenários de Sensibilidade | Tabela otimista/base/pessimista + stress-tests | `chart-cenarios-if` |
| `{{CONTENT_APP_D}}` | Referências e Recursos | Links, livros, ferramentas, contatos | — |
| `{{CONTENT_APP_E}}` | Próximos Ciclos e Roadmap | Tarefas + viagens + NCLEX + simulação Mariana + calendário | `chart-viagens` |

**REGRA CRÍTICA:** Se o E5 detectar que o conteúdo gerado para `{{CONTENT_SN}}` não corresponde ao tema do H1 da seção N (conforme tabela acima), DEVE parar e corrigir o mapeamento antes de continuar. Nunca injetar conteúdo de uma seção no placeholder de outra.

---

## SISTEMA DE EXPORTAÇÃO

### Export Markdown (⬇)
- Turndown.js converte HTML→Markdown
- Regras customizadas para tabelas, badges, KPI cards e alertas
- Filtra por `data-mode` do modo ativo (exporta só o modo visível)
- Substitui canvas por placeholder `[Gráfico: nome]`

### Botões flutuantes — posicionamento
Os 2 `<button>` HTML (Export MD + Back to Top) ficam FORA do `<script>`. Visibilidade controlada por scroll (>600px).

---

## OTIMIZAÇÃO PARA IMPRESSÃO

```css
@media print {
  .nav-sticky { display: none; }
  .cover-hero { print-color-adjust: exact; }
  .section { page-break-before: auto; }
  .card, table, .alert, .kpi-grid, .chart-row { page-break-inside: avoid; }
  canvas { display: none !important; } /* usar chart.toBase64Image() antes de print */
  .section-summary, .badge, .icon-badge { print-color-adjust: exact; }
}
```

---

## RESPONSIVIDADE

| Breakpoint | Ajustes principais |
|---|---|
| ≤1024px (tablet) | KPI grid 4 colunas, gap reduzido, tabelas menores |
| ≤768px (mobile landscape) | Cover compacto, nav sem texto (só números), KPI grid 2 colunas, chart-row 1 coluna, two-col 1 coluna, tabelas scroll horizontal |
| ≤480px (mobile portrait) | Cover mínimo, KPI grid 1×2, cards padding reduzido, font-size 13px |
| Dashboard KPIs | ≤768px: grid 3 colunas (em vez de 6) |

---

## RODAPÉ

```
Planejamento Financeiro Pessoal — Família Ferreira Campos
Gerado em: [DATA às HORA] (Brasília) | Período: Mai/2025–Mar/2026 | Versão Manual Operações: 3.2
⚠️ Caráter educacional/informativo. Não constitui consultoria financeira (CVM/CFP), jurídica ou tributária.
```

---

## WORKFLOW DE GERAÇÃO (8 BLOCOS SEQUENCIAIS)

O relatório HTML é gerado em 8 blocos sequenciais para respeitar limites de output:

1. **Bloco 1:** `<head>` completo (CSS + meta) + Cover hero + 8 KPIs + Perfil família + KPIs Táticos
2. **Bloco 2:** Nav sticky + Seções 1-2 (Patrimônio + Fluxo)
3. **Bloco 3:** Seção 3 (Investimentos completa)
4. **Bloco 4:** Seções 4-6 (Imóveis + F1/F2 + Green Card)
5. **Bloco 5:** Seções 7-9 (IF + Tributário + Riscos)
6. **Bloco 6:** Seção 10 + Apêndices A-E
7. **Bloco 7:** Seções Táticas D1-D6 (HTML skeleton) + `report-data` JSON
8. **Bloco 8:** JavaScript (Chart.js charts + dashboard builder + mode toggle + export functions) + Footer + botões flutuantes

Aguardar confirmação entre cada bloco antes de prosseguir.

### Notas importantes para geração:
- **COVER_DATA_HORA** deve ser atualizado a cada geração com data/hora atual
- **COVER_VERSAO_MANUAL** deve ler `report_version` de `config/pipeline.json`
- **COVER_PERIODO** deve ser atualizado quando novos arquivos financeiros são processados
