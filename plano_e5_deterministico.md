# Plano: E6 Determinístico

**Data:** 4 abr 2026
**Objetivo:** Tornar a etapa E6 100% determinística (script Python puro, sem LLM), movendo toda geração de texto narrativo para E5.

---

## Diagnóstico atual

A E6 hoje mistura duas naturezas de trabalho:

1. **Renderização de dados** — substituir placeholders no template HTML com números do E5 JSON, montar chart datasets, popular tabelas. Entrada fixa → saída fixa.
2. **Geração de narrativa** — escrever prosa (perfil da família, summaries, contextos de gráficos, diagnósticos). Requer LLM, produz saída variável.

Consequência: cada execução de E6 com os mesmos dados gera um relatório diferente. O manual tenta controlar isso com regras detalhadas (6 sub-etapas, validações), mas a variação é inerente ao uso de LLM.

---

## Arquitetura proposta

### Princípio

**E5 = Análise + Narrativa** (LLM-heavy, produz dados E texto)
**E6 = Renderização pura** (script Python, 100% determinístico)

### O que muda

| Componente | Hoje (E6, LLM) | Proposto (E5, LLM → E6, script) |
|---|---|---|
| Cover/KPIs/Footer | Script Python (já determinístico) | Sem mudança |
| Perfil da família (7 parágrafos) | LLM gera em E6.2 | LLM gera em E5 → salva HTML pronto no JSON |
| Report-data JSON (20 chaves, 19 charts) | LLM monta em E6.3 | Script Python monta em E6 (mapeamento puro) |
| Summaries S1-S10 (10 textos) | LLM gera em E6.4/E6.5 | LLM gera em E5 → salva no JSON |
| Cards obrigatórios (14 cards HTML) | LLM gera em E6.4/E6.5 | Script Python gera tabelas/cards em E6 |
| chart-context/chart-conclusion (~20 textos) | LLM gera em E6.4/E6.5 | LLM gera em E5 → salva no JSON |
| Diagnóstico comportamental | E5 gera dados, E6 formata | E5 gera dados + texto final |
| Pontos fortes/urgentes | E5 gera dados, E6 formata | E5 gera dados + texto pronto |
| Equilíbrio Cerbasi | E5 gera dados, E6 formata | E5 gera dados + texto pronto |
| Validação E6.6 | Script Python (já determinístico) | Sem mudança |

---

## Novo schema E5: chave `narrativas`

O E5 JSON ganha uma nova chave top-level `narrativas` que contém todo texto gerado por LLM, pronto para injeção no HTML.

```json
{
  "narrativas": {
    "perfil_familia": {
      "left": "<p>David Robert Ferreira Campos (45 anos) — CTO...</p><p>Mariana...</p><p>Theo...</p>",
      "right": "<p>Plano de vida: ...</p><p>Meta financeira: ...</p><p>Patrimônio: ...</p>"
    },
    "summaries": {
      "s1": "Patrimônio bruto de R$ 3,5M com 72% investível...",
      "s2": "Renda recorrente de R$ 79k/mês com taxa de poupança de 66%...",
      "s3": "Carteira diversificada em 10+ instituições...",
      "s4": "Dois imóveis com yield médio de X%...",
      "s5": "Custos F1/F2 projetados em USD X...",
      "s6": "Cenários cambiais entre R$ X e R$ Y...",
      "s7": "Projeção patrimonial indica IF em 9 anos...",
      "s8": "Carga tributária PJ com alíquota efetiva de X%...",
      "s9": "Cobertura securitária insuficiente em seguro de vida...",
      "s10": "Score 8.4/10 Excelente. 6 pontos fortes, 7 ações urgentes..."
    },
    "charts": {
      "patrimonio_doughnut": {
        "context": "Composição patrimonial mostrando concentração em imóveis (62%)...",
        "conclusion": "Rebalancear gradualmente para ativos financeiros..."
      },
      "waterfall_if": {
        "context": "Distância entre patrimônio investível atual e meta IF...",
        "conclusion": "Gap de R$ 4,7M requer aportes consistentes por 9 anos..."
      },
      "receita_bar": {
        "context": "Distribuição da receita por fonte...",
        "conclusion": "Concentração em PJ da Arvo (34%) — diversificação positiva via advisory..."
      },
      "despesas_doughnut": {
        "context": "...",
        "conclusion": "..."
      },
      "receita_despesa_mensal": {
        "context": "...",
        "conclusion": "..."
      },
      "score_gauge": {
        "context": "...",
        "conclusion": "..."
      },
      "alocacao_atual": {
        "context": "...",
        "conclusion": "..."
      },
      "alocacao_alvo": {
        "context": "...",
        "conclusion": "..."
      },
      "top15_ativos": {
        "context": "...",
        "conclusion": "..."
      },
      "yield_imoveis": {
        "context": "...",
        "conclusion": "..."
      },
      "custos_f1f2": {
        "context": "...",
        "conclusion": "..."
      },
      "cenario_cambial": {
        "context": "...",
        "conclusion": "..."
      },
      "projecao_if": {
        "context": "...",
        "conclusion": "..."
      },
      "renda_passiva": {
        "context": "...",
        "conclusion": "..."
      },
      "impostos_pj": {
        "context": "...",
        "conclusion": "..."
      },
      "riscos_bubble": {
        "context": "...",
        "conclusion": "..."
      },
      "decisoes": {
        "context": "...",
        "conclusion": "..."
      },
      "cenarios_mariana": {
        "context": "...",
        "conclusion": "..."
      },
      "viagens": {
        "context": "...",
        "conclusion": "..."
      }
    },
    "diagnostico_comportamental_html": "<table>...<tr><td>Gastos grandes sem planejamento</td>...</tr>...</table>",
    "pontos_fortes_html": "<div class='card card-feature'>...<ol>...</ol></div>",
    "pontos_urgentes_html": "<div class='card card-feature'>...<table>...</table></div>",
    "equilibrio_cerbasi_html": "<div class='card card-highlight'>...</div>",
    "previdencia_pgbl_html": "<div class='card card-feature'>...<table>...</table></div>",
    "apendices": {
      "a_glossario": "HTML do glossário de termos e siglas",
      "b_premissas": "HTML das premissas e metodologias",
      "c_cenarios": "HTML dos cenários de sensibilidade",
      "d_referencias": "HTML das referências e recursos",
      "e_proximos": "HTML das tarefas + viagens + NCLEX + simulação + calendário"
    }
  }
}
```

### Por que HTML pronto e não texto puro?

A E5 precisa injetar HTML no template. Se E4 entregar HTML pronto, E5 faz apenas `replace(placeholder, narrativas[key])` — zero decisão, zero formatação. Se entregasse texto puro, E5 teria que decidir como envolver em tags, que classes usar, etc. — introduzindo não-determinismo novamente.

A alternativa é um meio-termo: E4 entrega texto puro + metadados, e o script E5 aplica templates HTML fixos. Isso é mais limpo conceitualmente (separa conteúdo de apresentação), mas adiciona complexidade ao script E5. **Recomendação: começar com HTML pronto; refatorar para templates se necessário.**

---

## Plano de implementação — 5 fases

### Fase 1: Estender E5 para gerar narrativas

**O que fazer:**
- Adicionar sub-etapa **E5.N** (Narrativas) ao manual, executada após E5 calcular todos os dados
- E5.N lê: E5 JSON completo, members-1c_enriched.md, life_plan_goals.md, report_spec.md, definitions.md
- E5.N gera a chave `narrativas` no JSON com todas as sub-chaves acima
- Validação E5.N: todas as chaves de narrativas presentes e não-vazias

**Inputs para geração de cada narrativa:**

| Narrativa | Inputs necessários |
|---|---|
| `perfil_familia` | members, life_plan, patrimonio, goals |
| `summaries.s1` a `s10` | E5 JSON (seção correspondente) + report_spec (estrutura esperada) |
| `charts.*` (context/conclusion) | E5 JSON (dados do chart) + report_spec (o que cada chart mostra) |
| `diagnostico_html` | E5 `diagnostico_comportamental` array |
| `pontos_fortes_html` | E5 `pontos_fortes` array |
| `pontos_urgentes_html` | E5 `pontos_urgentes` array |
| `equilibrio_cerbasi_html` | E5 `equilibrio_cerbasi` |
| `previdencia_pgbl_html` | E5 `previdencia_pgbl` |
| `apendices.*` | E5 JSON + life_plan + definitions (glossário) |

**Regras de geração (herdadas do manual E5 atual):**
- Perfil: 7 parágrafos prosa em `<p>`, sem tabelas/bullets/strong-label
- Summaries: 1-2 frases por seção
- Charts: 1-2 frases de contexto + 1-2 frases de conclusão
- Cards HTML: seguir classes CSS do design system (`.card-feature`, `.card-highlight`, etc.)
- Nenhum `margin-top` inline, nenhuma cor hex hardcoded, `card-title` obrigatório

**Entregável:** manual_operacao.md atualizado com E5.N + schema JSON atualizado

---

### Fase 2: Reescrever E6 como script Python puro

**O que fazer:**
- Criar `scripts/e6_render.py` — script determinístico que:
  1. Copia template para output
  2. Lê E5 JSON (dados + narrativas)
  3. Substitui todos os placeholders por mapeamento direto
  4. Monta o report-data JSON (chave `charts`, `kpis`, etc.) por mapeamento campo-a-campo
  5. Gera HTML dos cards obrigatórios usando templates Python (f-strings com dados do E5)
  6. Injeta summaries, contexts, conclusions, perfil, apêndices
  7. Roda validação E6.6

**Mapeamento de placeholders (completo):**

```
E6.1 (Cover/KPIs/Footer):
  {{COVER_FAMILIA}}         → "Ferreira Campos"
  {{COVER_PERIODO}}         → e5["periodo_dados"]
  {{COVER_VERSAO_MANUAL}}   → regex no manual_operacao.md
  {{COVER_DATA_HORA}}       → datetime.now(SP)
  {{NOME}}                  → "David"
  {{KPI_*}}                 → e5["patrimonio"|"racios"|"goals"|"score"|"fluxo_caixa"]
  {{FOOTER_CONTENT}}        → template fixo

E6.2 (Perfil):
  {{PERFIL_FAMILIA_LEFT}}   → e5["narrativas"]["perfil_familia"]["left"]
  {{PERFIL_FAMILIA_RIGHT}}  → e5["narrativas"]["perfil_familia"]["right"]

E6.3 (Report-data JSON):
  {{REPORT_DATA_JSON}}      → json.dumps(build_report_data(e5))

E6.4/E6.5 (Seções):
  {{SUMMARY_S1..S10}}       → e5["narrativas"]["summaries"]["s1".."s10"]
  {{CONTENT_S1..S10}}       → build_section_html(e5, section_num)
  {{CONTENT_APP_A..E}}      → e5["narrativas"]["apendices"]["a".."e"]
```

**Função `build_section_html()`:**
- Para cada seção, monta o HTML combinando:
  - Charts: `<div class="chart-container"><div class="card-title">...</div><p class="chart-context">{narrativas.charts.X.context}</p><canvas id="chart-X"></canvas><p class="chart-conclusion">{narrativas.charts.X.conclusion}</p></div>`
  - Cards obrigatórios: templates Python fixos preenchidos com dados numéricos do E5
  - Cards narrativos: HTML pronto de `narrativas`

**Função `build_report_data()`:**
- Mapeia E5 JSON → estrutura report-data com 20 chaves
- Cada chart dataset construído por mapeamento explícito (não geração)
- Retorna dict Python, serializado com `json.dumps()`

**Entregável:** `scripts/e6_render.py` funcional + testes

---

### Fase 3: Testes de equivalência

**O que fazer:**
- Rodar E5.N para gerar narrativas no JSON existente
- Rodar novo `e6_render.py` para gerar relatório
- Comparar com relatório atual:
  - Estrutura HTML: mesmos IDs, mesmas seções, mesmos cards
  - Dados numéricos: idênticos (determinístico)
  - Narrativas: semanticamente equivalentes (geradas em E5 ao invés de E6)
  - Validação E6.6: 18/18 passing

**Critério de sucesso:** relatório gerado pelo script passa 18/18 validações e é visualmente equivalente ao atual quando aberto no browser.

---

### Fase 4: Atualizar manual_operacao.md

**Mudanças necessárias:**

1. **Nova sub-seção em E5: "E5.N — Narrativas"**
   - Inputs, outputs, regras de geração, validação
   - Schema completo da chave `narrativas`

2. **E6 reescrito como "Renderização"**
   - Remover toda referência a geração de texto por LLM
   - Sub-etapas E6.1-E6.6 simplificadas para descrever o que o script faz
   - E6 agora é: `python scripts/e6_render.py` + validação
   - Manter sub-etapas como documentação (o que cada uma faz), mas execução é um único comando

3. **E6-regen simplificado**
   - Se houve mudança apenas no template: `python scripts/e6_render.py` (mesmo comando)
   - Se houve mudança nos textos: re-rodar E5.N + `python scripts/e6_render.py`

4. **Tabela "Diagnóstico Rápido" atualizada**
   - "Texto de seção mal escrito" → corrigir em E5 (re-rodar E5.N) em vez de E6

5. **Versão do manual: 4.0**

---

### Fase 5: Eliminar scripts legados

**O que fazer:**
- Deprecar `execute_e6.py` (paths hardcoded, funcionalidade absorvida por `e6_render.py`)
- Deprecar `generate_e6_report.py` (mesmo motivo)
- Manter `scripts/e6_regen.py` apenas se houver funcionalidade de pós-processamento não coberta pelo novo script (dark mode toggle, collapse, etc.)
- Comitar via Git com mensagem descritiva

---

## Benefícios esperados

| Aspecto | Antes | Depois |
|---|---|---|
| Determinismo E6 | ~30% (apenas E6.1 e E6.6) | 100% |
| Tempo de execução E6 | 15-30 min (6 sub-etapas LLM) | < 5 segundos (script Python) |
| Variação entre execuções | Alta (toda execução diferente) | Zero (mesmos inputs = mesmo output) |
| Debugging | Difícil (qual sub-etapa errou?) | Fácil (é bug no script ou nos dados E5) |
| Re-runs | Caros (LLM a cada vez) | Grátis (script local) |
| Separação de concerns | Misturado | Limpo: E5 = inteligência, E6 = mecânica |

---

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| E5 JSON fica muito grande com narrativas | Narrativas são ~20-30KB de texto; JSON atual é 36KB. Vai para ~60-70KB. Aceitável. |
| HTML gerado em E5 acopla ao design do template | Se template mudar, E5.N precisa re-rodar. Mitigação: manter HTML semântico (classes CSS, não estilos inline). |
| Perda de "naturalidade" nos textos | E5.N usa o mesmo LLM e os mesmos inputs que E6 usava. Qualidade do texto não muda, apenas o momento da geração. |
| Scripts Python precisam de manutenção | Menos manutenção que manter LLM prompts consistentes. E script é testável com unit tests. |

---

## Ordem de execução recomendada

1. **Fase 1** primeiro — é a mudança conceitual mais importante e pode ser testada independente
2. **Fase 2** em paralelo com Fase 1, usando o schema como contrato
3. **Fase 3** assim que ambas estiverem prontas
4. **Fase 4** depois de validar que funciona
5. **Fase 5** por último (cleanup)

Estimativa total: 2-3 sessões de trabalho.
