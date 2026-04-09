# Plano de Correção — Texto Narrativo do e5n_narrativas.py

**Data:** 2026-04-08
**Versão:** 1.0
**Objetivo:** Eliminar todo texto hardcoded do `build_narrativas()`, substituindo por dados de fontes dinâmicas (E5 JSON, config, members, life_plan, ou LLM).

---

## Diagnóstico

O `build_narrativas()` contém ~70 trechos de texto hardcoded que se dividem em 3 categorias:

| Cat. | Descrição | Qtd | Fonte correta |
|---|---|---|---|
| **A** | Percentuais e números que deveriam ser computados | ~25 | `METRICS[]` + cálculo |
| **B** | Fatos biográficos/institucionais | ~15 | `config/`, `members/`, `life_plan/` |
| **C** | Análises estratégicas e recomendações | ~30 | LLM-generated ou `config/decisions.md` |

---

## Arquitetura-alvo

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  E5 JSON     │     │  Config      │     │  LLM (E5.N)  │
│  (computed)  │     │  (curated)   │     │  (generated) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│           build_narrativas(e5_data, llm_texts)          │
│                                                         │
│  1. METRICS (já refatorado) ← E5 + goals.json          │
│  2. FACTS   ← members-1c + life_plan + family.json     │
│  3. ANALYSIS ← llm_texts dict (gerado pelo LLM)        │
│  4. COMPUTED ← percentuais derivados de METRICS         │
│                                                         │
│  Template f-strings usam apenas variáveis dinâmicas     │
└─────────────────────────────────────────────────────────┘
```

---

## Fase 1 — Percentuais computados (Cat. A)

**Impacto:** Alto — são dados factuais incorretos quando os números mudam.
**Esforço:** Baixo — cálculo direto a partir de METRICS já existentes.

Adicionar ao dict de `load_metrics_from_e5()`:

| Metric nova | Cálculo | Texto que substitui |
|---|---|---|
| `pct_investivel` | `investivel / bruto * 100` | "65% investível" |
| `pct_imoveis_bruto` | `imoveis_invest / bruto * 100` | "71% do total" |
| `pct_receita_pj` | `receita_pj / receita_total * 100` | "78% proveniente de PJ" |
| `pct_receita_aluguel` | `receita_aluguel / receita_total * 100` | "9% de aluguel" |
| `pct_receita_clt` | `receita_clt / receita_total * 100` | "8,6% de CLT" |
| `pct_receita_outras` | `100 - pj - aluguel - clt` | "4,3% de outras" |
| `pct_despesas_nao_id` | `nao_id / despesa_total * 100` | "34% do total" / "52%" |
| `pct_das_receita_pj` | `das_anual / receita_pj * 100` | "~6% da receita PJ" |
| `pct_renda_passiva_meta` | `renda_passiva_4pct / 30000 * 100` | "33,5% da meta" |
| `aportes_acum_20anos` | `meta_aporte * 12 * prazo_anos` | "R$ 4,92M em 20 anos" |
| `wise_usd` | do E3 reconciled Wise USD | "US$ 4,7k em Wise" |
| `bofa_usd` | do E3 reconciled BofA USD | "US$ 2,6k em Bank of America" |
| `renda_mariana_eua_brl` | `projetada_usd * cambio` | "R$ 27,5k/mês" |
| `pct_renda_eua_vs_clt` | `1 - (renda_eua_brl / salario_mariana)` | "30% menor que CLT" |

**Ação:** Adicionar esses campos no return de `load_metrics_from_e5()` e substituir os strings hardcoded nos templates por `{fmt_percent(METRICS['pct_*'])}`.

---

## Fase 2 — Fatos biográficos/institucionais (Cat. B)

**Impacto:** Médio — dados estáticos mas que podem mudar (ex: anos de experiência, empresa atual).
**Esforço:** Médio — requer ler de fontes já existentes.

### 2a. Dados de `members-1c_enriched.md` (parse no load)

| Texto hardcoded | Fonte real | Campo a extrair |
|---|---|---|
| "Mais de 23 anos em tecnologia" | members-1c | "24 anos de experiência" → computar de `david.primeiro_emprego` |
| "passagens por Elo7, Loft e Kiwify" | members-1c | `david.historico_empresas` (top 3-4 relevantes) |
| "Especialista em Cardiologia..." | members-1c | `mariana.especializacoes` |

**Opção A (recomendada):** Expandir `config/family_members.json` com campos adicionais:

```json
{
  "membros": {
    "david": {
      "anos_experiencia_inicio": 2002,
      "empresas_destaque": ["Elo7", "Loft", "Kiwify", "Arvo"],
      "especializacoes": ["Software Architecture", "IA/ML", "Cloud"]
    },
    "mariana": {
      "especializacao": "Cardiologia e Hemodinâmica (UNIFESP)",
      "mestrado": "Enfermagem (USP)",
      "nclex_status": "Perfil competitivo para NCLEX nos EUA"
    }
  }
}
```

**Opção B:** Fazer parse do `members-1c_enriched.md` no load — mais frágil (depende de formato MD).

### 2b. Dados de `life_plan/life_plan_goals.md` → já estão em `config/goals.json`

| Texto hardcoded | Campo em goals.json |
|---|---|
| "Anderson University, SC" | `fase_f1f2.universidade` ✓ |
| "EB2-NIW" | `fase_f1f2.green_card_via` ✓ |
| "retorno real de 6% a.a." | `independencia_financeira.retorno_real_anual_pct` ✓ |
| "TRS 5%" | `independencia_financeira.trs_pct` ✓ |
| "renda passiva de R$ 30k/mês" | `independencia_financeira.renda_passiva_meta_mensal` ✓ |

### 2c. Instituições e plataformas

| Texto hardcoded | Fonte sugerida |
|---|---|
| "AccountTech" | `config/goals.json` → `tributario.contador_nome` |
| "QuintoAndar" | derivar do E3 reconciled (labels nos extratos) |
| "Living Wish", "Living Concept" | `config/imoveis.json` (a criar) ou derivar do E4 patrimônio |
| "CDBs Santander, fundos Rico..." | derivar do E4 investimentos (top instituições) |
| "BTG Pactual" | derivar do E4 investimentos |

---

## Fase 3 — Textos analíticos/estratégicos (Cat. C)

**Impacto:** Alto — são as opiniões e recomendações do relatório.
**Esforço:** Alto — requer decisão arquitetural.

### Opções de arquitetura:

**Opção 1 — Templates parametrizados (recomendada para v1):**
Manter templates no Python mas substituir TODOS os dados por variáveis. As frases de análise ficam como templates parametrizáveis — o "tom" é fixo mas os dados são dinâmicos.

Exemplo antes:
```python
"Imóveis respondem por 71% do patrimônio — acima do ideal de 50%."
```

Exemplo depois:
```python
f"Imóveis respondem por {fmt_percent(M['pct_imoveis_bruto'])} do patrimônio"
+ (f" — acima do ideal de {fmt_percent(THRESHOLDS['imovel_alvo_pct'])}." 
   if M['pct_imoveis_bruto'] > THRESHOLDS['imovel_alvo_pct'] else ".")
```

**Vantagem:** Determinístico, validável, sem custo de LLM.
**Limitação:** Frases rígidas, sem variação de estilo.

**Opção 2 — LLM gera conclusions/contexts (futuro, v2):**
O LLM recebe o dict de METRICS + FACTS e gera os textos de `charts.*.conclusion` e `summaries.s*`. O script valida formato, tamanho e dados numéricos após geração.

```python
def build_narrativas(e5_data, llm_texts=None):
    # ...template perfil (parametrizado, sem LLM)...
    
    if llm_texts:
        # LLM gerou os texts — usar diretamente (já validados)
        narrativas["summaries"] = llm_texts["summaries"]
        narrativas["charts"] = llm_texts["charts"]
    else:
        # Fallback: templates parametrizados
        narrativas["summaries"] = _build_summaries_template(METRICS, FACTS)
        narrativas["charts"] = _build_charts_template(METRICS, FACTS)
```

**Vantagem:** Textos naturais, adaptativos, mais ricos.
**Custo:** Depende de LLM a cada execução, precisa de validação robusta.

**Opção 3 — Híbrida (recomendada para v2):**
- `perfil_familia` → template parametrizado (Cat. B, sempre determinístico)
- `summaries` → template parametrizado com fallback (Cat. A + B)
- `charts.*.context` → template parametrizado (sempre determinístico — são descrições do gráfico)
- `charts.*.conclusion` → LLM-generated (Cat. C — são insights acionáveis)

---

## Fase 4 — Riscos e decisões prioritárias

| Texto | Fonte ideal |
|---|---|
| 5 riscos prioritários (FBAR, Estate Tax...) | `config/riscos.json` (a criar) com prob/impacto |
| 5 decisões estratégicas (s10, top5_decisoes) | `config/decisions.md` D01-D15 (já existe, precisa de parser) |
| Seguros inexistentes — urgentes | `config/seguros.json` ou `pontos_urgentes` do E5 JSON |
| Timeline "T4/2026", "T2 2026" | `config/goals.json` → `timeline_acoes` |

---

## Plano de execução (ordem recomendada)

| # | Fase | Escopo | Estimativa | Dependências |
|---|---|---|---|---|
| 1 | **Percentuais computados** | +14 METRICS derivadas, ~25 substituições nos templates | 1 sessão | Nenhuma |
| 2a | **family_members.json expandido** | +6 campos, ~12 substituições | 1 sessão | Nenhuma |
| 2b | **goals.json expandido** | +5 campos (contador_nome, timeline_acoes...) | 30 min | goals.json já existe |
| 2c | **Instituições do E4** | Função helper que extrai top instituições/ativos do E4 | 1 sessão | E4 JSON |
| 3 | **Lógica condicional nos templates** | if/else para frases tipo "acima do ideal" | 1 sessão | Fase 1 |
| 4 | **Parser decisions.md** | Extrair D01-D15 como dict | 1 sessão | decisions.md |
| 5 | **Validação e re-run E5.N** | Rodar pipeline, conferir output | 30 min | Fases 1-4 |

**Total estimado: 4-5 sessões** para eliminar todos os hardcodes.

---

## Critério de sucesso

Após a correção completa, o `build_narrativas()` não deve conter **nenhum** número, percentual, nome de instituição, ou afirmação analítica que não venha de:
1. `METRICS[key]` (E5 JSON + goals.json)
2. `FACTS[key]` (family_members.json + members-1c)
3. `GOALS[key]` (goals.json + life_plan)
4. `llm_texts[key]` (quando implementado)
5. Cálculo derivado de (1)-(4)

Strings permitidas como hardcode: conectores ("é", "de", "com"), HTML tags, labels de seção.
