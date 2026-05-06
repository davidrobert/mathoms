# Methodology — Pipeline Ferreira Campos
## Versão: 5.3 — abr/2026

---

## PERSONA E ABORDAGEM

Consultor financeiro especialista em independência financeira e planejamento patrimonial para famílias brasileiras de alta renda com contexto internacional. Abordagem baseada nas três metodologias-pilar:

- **Bruno Perini / Viver de Renda** — independência financeira via taxa de retirada segura (TRS), patrimônio-alvo pelo múltiplo de custo de vida (regra dos 300 / TRS 4-5%), foco em renda passiva sustentável e reinvestimento disciplinado na fase de acumulação.
- **Gustavo Cerbasi / Inteligência Financeira** — comportamento financeiro, ciclos de vida, orçamento por percentuais (essenciais / estilo de vida / futuro), proteção (seguros, previdência), diálogo financeiro em casal.
- **Raul Sena / AUVP — A Única Verdade Possível** — alocação multi-classe estratégica entre renda fixa pós-fixada, prefixada e IPCA+, ações BR, ações internacionais, FIIs e caixa; **rebalanceamento por aporte** (aporta na classe mais defasada — princípio do Diagrama do Cerrado); análise fundamentalista com sistema de notas 0-10 por ativo; contrafluxo (alocar contra o ciclo de juros vigente).

Combinações obrigatórias:

1. Diagnóstico financeiro completo (receitas, despesas, patrimônio)
2. Cálculo do "Número da Independência" — patrimônio necessário para gerar renda passiva via TRS
3. Aceleração patrimonial — quanto guardar por mês e onde alocar
4. Orçamento Consciente — categorização de gastos, padrões comportamentais, tetos por categoria com "reserva de desejos"
5. Simulação de cenários (otimista, realista, pessimista)
6. Planejamento Tributário Anual — previsão, provisão IRPF, carnê-leão, otimização fiscal
7. Planejamento Sucessório — testamentos, procurações, proteção patrimonial BR+EUA
8. Análise fundamentalista de ativos — PM, P/L, benchmark por ativo, custo de oportunidade imobiliário
9. Plano de ação mensal com metas concretas e checkpoints trimestrais

Análise baseada em dados reais de extratos bancários, faturas de cartão e declaração de IR — fatos, não estimativas.

---

## REGRA DE OURO — COMPORTAMENTO DURANTE A ANÁLISE

Ao final de cada etapa concluída, antes de avançar para a próxima, obrigatoriamente:

- (a) Apresentar um resumo dos dados utilizados naquela etapa
- (b) Listar explicitamente quaisquer dados ausentes, ambíguos ou estimados
- (c) Fazer perguntas específicas de confirmação/esclarecimento ao usuário
- (d) Aguardar a resposta antes de continuar

**Somente avançar para a próxima etapa após confirmação explícita do usuário.**

---

## PIPELINE DE DADOS (E0 a E3)

O pipeline de dados é executado por qualquer ambiente (Cowork ou Chat). Ver scripts em `scripts/` e configs em `config/` para detalhes completos.

| Etapa | Objetivo | Input | Output |
|---|---|---|---|
| E0.A | Rotear e renomear arquivos do inbox | `inbox/*` | Arquivos em `data/`, `members/` |
| E1 | Mapeamento de membros | Currículos, holerites, docs pessoais | `members-1c_enriched.md` |
| E1.5 | Baseline patrimonial | IRPF + XLSX imóveis/veículos + informes QA | `baseline_patrimonial-1.5_consolidated.json` |
| E2 | Extração de extratos financeiros | PDFs de extratos, faturas, posições | `-2_extract.json` por arquivo |
| E3 | Reconciliação por conta | Todos os `-2_extract.json` | `-3_reconciled.json` por conta |

---

## PIPELINE DE ANÁLISE (E4 a E7) — 10 SEÇÕES DO RELATÓRIO

Cada seção do relatório abre com um `section-summary` (1 frase resumindo a conclusão principal).

### E4 — Enriquecimento e Unificação
- **Objetivo:** Categorizar transações, consolidar por tipo, enriquecer com contexto do baseline patrimonial.
- **Inputs:** Todos os `-3_reconciled.json` + `baseline_patrimonial-1.5_consolidated.json` + `dados_imoveis-2_extract.json` + `dados_veiculos-2_extract.json` (se houver) + `definitions.md`
- **Outputs:** `receitas-4_unified.json`, `despesas-4_unified.json`, `investimentos-4_unified.json`, `patrimonio-4_unified.json`, `seguros-4_unified.json`, `pontos_milhas-4_unified.json`
- **Nota v5.0:** `patrimonio-4_unified.json` substitui `imoveis` e `veiculos` unificados — consolida TODOS os ativos (imóveis, veículos, investimentos, criptos, contas, empresas) com dados de compra do XLSX e valores declarados do IRPF.

### E5 — Análise (gera JSON `analise_financeira-5_analysis.json` que alimenta as 10 seções do relatório)

**E5.1 — Saúde Financeira (→ seção 1 do relatório: Visão Geral Patrimonial)**
- **Objetivo:** Score Financeiro (0-10), patrimônio total incluindo todos os ativos do `patrimonio-4_unified.json`.
- **Inputs:** `patrimonio-4_unified.json`, `receitas-4_unified.json`, `despesas-4_unified.json`, `baseline_patrimonial-1.5_consolidated.json`
- **Outputs:** Bloco `saude_financeira` no E5 JSON — Score com 5 critérios, patrimônio bruto vs investível, reserva emergência.

**E5.2 — Fluxo de Caixa e Orçamento (→ seção 2 do relatório)**
- **Objetivo:** Receitas vs despesas, taxa de poupança, orçamento prospectivo com tetos, diagnóstico comportamental.
- **Inputs:** `receitas-4_unified.json`, `despesas-4_unified.json`, `definitions.md` (categorias e tetos), `investimentos-4_unified.json` (para cruzamento de liquidez)
- **Outputs:** Bloco `fluxo_de_caixa` no E5 JSON — Fluxo, projeção pós-quitação, 13 categorias vs tetos, consumo consciente, **diagnóstico comportamental** (`diagnostico_comportamental[]` no E5 JSON — array de padrões detectados com evidência e mudança sugerida; ver regras de detecção em `e5_analyze.py`).
- **Atenção:** NÃO confundir despesas PJ com pessoais. Incluir "reserva de desejos" R$3k/mês.
- **Diagnóstico comportamental:** OBRIGATÓRIO em todo ciclo. Mesmo sem padrões detectados, gerar bloco com array vazio e nota positiva. Tom não-julgamental — foco em automatização de fluxo.

**E5.3 — Independência Financeira (→ seção 7 do relatório)**
- **Objetivo:** Número da IF, gap, prazo em 3 cenários.
- **Inputs:** `patrimonio-4_unified.json`, `config/goals.json`
- **Outputs:** Bloco `independencia_financeira` no E5 JSON — Projeção 3 cenários, renda passiva 2035 por 8 fontes com disclaimer, card TRS didático.
- **Terminologia:** Usar "Independência Financeira" (não "IF") nos títulos. Regra completa de capitalização e abreviação em [docs/COPY_GUIDELINES.md §3.1](../docs/COPY_GUIDELINES.md).

**E5.4 — Estratégia Tributária (→ seção 8 do relatório)**
- **Objetivo:** Otimizações tributárias, carnê-leão, PGBL, Simples vs LP.
- **Inputs:** `receitas-4_unified.json`, `baseline_patrimonial-1.5_consolidated.json` (dados de IRPF), `decisions.md`
- **Outputs:** Bloco `estrategia_tributaria` no E5 JSON — Simples vs LP, PGBL portabilidade, Carnê-Leão passo-a-passo, calendário tributário.

**E5.5 — Estratégia de Investimentos (→ seção 3 do relatório)**
- **Objetivo:** Performance por ativo, rentabilidade ponderada, benchmark, alocação.
- **Inputs:** `investimentos-4_unified.json`, `patrimonio-4_unified.json`
- **Outputs:** Bloco `estrategia_investimentos` no E5 JSON — Rentabilidade, benchmark acumulado, fundamentalista, contrafluxo, consolidação corretoras.

**E5.6 — Imóveis e proteção patrimonial (→ seção 4 do relatório)**
- **Objetivo:** Yield de imóveis vs CDI + 5 riscos proteção patrimonial.
- **Inputs:** `patrimonio-4_unified.json`, `config/goals.json`, `decisions.md`
- **Outputs:** Bloco `protecao_patrimonial` no E5 JSON — Yield imóveis vs CDI + matriz de riscos. (Seções USA — F1/F2, Green Card, NCLEX — removidas em A8.4 PR4 / ADR-168.)

**E5.7 — Riscos e Seguros (→ seção 9 do relatório)**
- **Objetivo:** Mapear 10 riscos, bubble chart, tabela seguros.
- **Inputs:** `seguros-4_unified.json`, `patrimonio-4_unified.json`, `members-1c_enriched.md`
- **Outputs:** Bloco `riscos_seguros` no E5 JSON — Bubble chart, top 3 riscos, prioridade vida + invalidez.

**E5.8 — Lista de Tarefas (→ seção 10 + apêndices do relatório)**
- **Objetivo:** Lista de tarefas priorizadas, timeline, pontos fortes e urgentes.
- **Inputs:** Blocos anteriores do E5 JSON, `decisions.md`
- **Outputs:** Bloco `lista_de_tarefas` no E5 JSON — Equilíbrio presente×futuro (Cerbasi), top 5 decisões, timeline.

### E5.N — Narrativas
- **Objetivo:** Gerar todos os textos analíticos e narrativos (perfil, summaries, contexts/conclusions de gráficos).
- **Inputs:** `analise_financeira-5_analysis.json` (dados completos do E5), `members-1c_enriched.md`, `config/goals.json`
- **Outputs:** Chave `narrativas` adicionada ao E5 JSON com `perfil_familia`, `summaries`, `charts`.

### Renderização do relatório (pós-[ADR-129](../docs/DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side))
- **Objetivo:** Apresentar todas as análises em relatório consultivo completo.
- **Renderer único:** rota React `/reports/[id]` no frontend Next.js, consumindo `GET /reports/{id}/data` (E5 JSON via `Report.analysis_artifact_id` — FK para `pipeline_artifacts`, [ADR-131](../docs/DECISIONS.md#adr-131--report-referencia-pipeline_artifact-por-fk-drop-analysis_json_path)). 100% determinístico — sem LLM no render.
- **Inputs:** `analise_financeira-5_analysis.json` (E5 JSON com dados + narrativas + refinamentos do E7).
- **Export server-side:** PDF via Playwright (`backend/app/services/pdf_renderer.py`) sobre a mesma rota — único export server-side.
- **Stages E6 / E6-final removidos:** o pipeline não gera mais HTML standalone. Re-renders após E7 são automáticos (a rota lê o E5 JSON atualizado).

### E7 — Review & Refine (LLM — pós-relatório)
- **Objetivo:** Revisão final do relatório usando a persona e abordagem desta methodology. Retroalimenta narrativas, summaries, chart descriptions, lista de tarefas e prioridades com base na visão completa do relatório renderizado.
- **Comando:** `python scripts/e7_review.py` (cross-validation) → LLM review → `python scripts/e7_review.py --apply review.json`. O re-render é automático na próxima abertura de `/reports/[id]`.
- **Inputs:** `analise_financeira-5_analysis.json` (E5 JSON com narrativas), `methodology.md` (persona).
- **Outputs:** E5 JSON atualizado com refinamentos + `review_metadata` + `strategic_insights`.
- **Cross-validation:** 14 checks determinísticos verificam consistência entre score, patrimônio, fluxo, IF, endividamento, reserva, narrativas e tarefas.
- **Princípio:** Uma única passagem de review (sem recursão). Se refinamentos significativos forem necessários, re-executar com `python scripts/e_reset.py --from E7`.

---

## SCORE FINANCEIRO (v5.4)

O score é uma média ponderada de 5 componentes em escala **0-10** com 1 decimal,
**fonte única em `config/scoring.json`** (consumido por `e5_analyze.py`).

Cada componente é interpolado linearmente entre `range_min` (nota 0) e `range_max`
(nota 10); componentes marcados `invertido: true` invertem a escala. A justificativa
metodológica (Perini/Cerbasi/AUVP) por critério está em `scoring.json:_metodologia`.

**Fórmula:**

```
score = Σ(componente_i × peso_i) / Σ(peso_i)
```

**Faixas (em `scoring.json:score_classificacao`):**
0–2 Crítico · 2–4 Atenção · 4–6 Regular · 6–8 Bom · 8–10 Excelente.

**Regras operacionais:**

- Salvar componentes individuais em `score.componentes[]` para transparência.
- Receita one-time (rescisão, FGTS, venda de ativo, infoproduto pontual) **não entra**
  em `taxa_poupanca_recorrente` — usar receita recorrente.
- Cobertura de despesas usa **custo essencial mensal** (definição em §RESERVA DE EMERGÊNCIA).
- Endividamento mede comprometimento mensal de renda com dívida onerosa,
  excluindo financiamento imobiliário em quitação programada.

Detalhes de implementação: `pipeline/domain/services/financial_score_calculator.py` e `scripts/e5_analyze.py`.

> Decisões 2026-04-27 que consolidaram o score:
> (i) `scoring.json` é fonte única; `methodology.md` e `methodology_template.md` apenas referenciam.
> (ii) Escala 0-10 com 1 decimal vence; escala 0-100 do template antigo descontinuada.
> (iii) Componente "Controle de gastos variáveis" (template fantasma) não entra — sem série temporal estável o suficiente.

---

## RESERVA DE EMERGÊNCIA

Fórmula canônica:

```
reserva_alvo      = custo_essencial_mensal × meses_alvo
cobertura_atual   = reserva_liquida_disponivel ÷ custo_essencial_mensal
```

**Custo essencial mensal:** média trimestral das categorias `moradia,
alimentacao, transporte, saude, seguros, servicos_domesticos, educacao,
suporte_familiar, financiamentos`. Impostos não-PJ entram (IPTU, IPVA,
IRPF); impostos PJ saem (DAS, GPS INSS PJ — cessam se a operação cessar).
Lista canônica em `scoring.json:reserva_emergencia._base_calculo`.

**Meses-alvo por composição de renda familiar** (proxy: % da receita
recorrente vinda de `receita_pj`):

| Perfil | receita_pj_% | meses-alvo | Justificativa |
|---|---|---|---|
| CLT estável (≥2 fontes) | < 10% | 6 | Cerbasi: 6 meses cobre dispensa + recolocação típica. |
| CLT única fonte | < 10% | 12 | Sem rede de cônjuge — Perini sobe para 12. |
| Renda mista | 10–30% | 12 | PJ é volatilidade material — convergência Cerbasi + Perini. |
| PJ relevante | 30–60% | 12 | Volatilidade alta; CLT residual ainda ancora. |
| PJ dominante | ≥ 60% | 18 | Perini cita 12-24 para autônomos; produto adota 18 como meio termo defensável. |

**Faixas de classificação** (sobre `cobertura_atual` em meses):
< 3 Insuficiente · 3-6 Mínima · 6-12 Adequada · 12-24 Robusta · > 24
Excessiva.

A faixa "Excessiva" (>24 meses) **não é convergência canônica** — Cerbasi
e Perini não escrevem teto. Adotada pelo produto com fundamentação AUVP
(custo de oportunidade de caixa: R$ 100k acima do alvo em CDI 14% ≈ R$ 14k/ano
de retorno-real perdido vs. carteira diversificada). Recomendação "realocar
excedente" só dispara quando há excedente material **e** alocação efetiva
está abaixo do alvo (ver `goal.alocacao_alvo:desvio_max_pct`).

**Modulador para dependentes** (recomendação Cerbasi para famílias com
filhos pequenos / idosos dependentes — não codificado em `meses_alvo_por_perfil_renda`
mas deve ser aplicado pelo planejador):

- Bebê / criança ≤6 anos (dependência total): **multiplicar `meses_alvo` por 1,3**
  (ex.: CLT estável + bebê = 8 meses, não 6).
- Idoso dependente (custo médico não-coberto pelo plano): **multiplicar por 1,2**.
- Família com 2+ filhos em idade escolar: **multiplicar por 1,15**.

Trade-off: scoring puramente algorítmico não captura — fica como ajuste
consultivo. Lane futura: estender `scoring.json:reserva_emergencia._base_calculo`
com `modulador_dependentes`.

**Reserva ≠ patrimônio investível.** Reserva mora em ativos com liquidez
D+0 a D+1 e baixíssimo risco (Tesouro Selic, CDB liquidez diária ≥ FGC,
caixa). Não confundir com Cofrinhos atrelados a CDI longo.

---

## TRS EFETIVA (Métrica core · A8.3)

**TRS efetiva** = renda passiva anual observada / patrimônio investido
(carteira de renda) × 100. Renda passiva agrega dividendos isentos
(cod RFB 09), JCP exclusiva (10), aplicações exclusiva (12), ganho de
capital exclusiva (06), rendimentos exterior e aluguéis (rendimentos
PF/PJ classificados como aluguel) — fonte: IRPF analyzer (último
ano-base disponível). **Aluguéis foram realocados de trabalho para
capital** para coerência metodológica (Perini classifica aluguel como
capital imobiliário; AUVP idem) — ver
[ADR-164](../docs/DECISIONS.md#adr-164--carteira-de-renda-e-taxa-de-retirada-efetiva)
§Re-classificação.

**Carteira de renda** (chave interna `patrimonio_gerador_brl`) exclui
residência principal, veículos, derivativos e parcela de caixa
correspondente à reserva de emergência. Inclui (mesmo com yield
observado zero): cripto, ações growth e PGBL/VGBL em acumulação —
yield 0% explícito é o sinal pedagógico, não erro.

Confronto com **TRS meta** (5% Perini realista / 4% Trinity pessimista
— decisão D15) sinaliza adequação da carteira como geradora de renda
**na fase atual**: warning visual condicionado a `progresso ≥ 50%`
(em acumulação, yield baixo é esperado).

> **Mitigação obrigatória do erro #1 do iniciante** (Perini): TRS
> efetiva exibida sem contexto induz a vender growth para perseguir
> DY, sacrificando retorno total. Por isso S7 exibe (i) renda passiva
> em R$/mês antes do %, (ii) caption permanente em acumulação, (iii)
> banner explicativo quando >40% da carteira de renda está em
> acumuladores (BOVA11, IVVB11, IVV…), (iv) tom condicionado à fase.

---

## PREMISSAS ECONÔMICAS

| Variável | Pessimista | Realista (base) | Otimista | Atual (abr/2026) |
|---|---|---|---|---|
| Inflação (IPCA 12m) | 6,0% | 4,5% | 3,5% | 4,14% |
| Retorno real carteira | 4,0% | 6,0% | 8,0% | ~6,0% |
| CDI / Selic | 8,0% | 14,5% | 15,0% | 14,75% |
| Câmbio BRL/USD | R$ 7,50 | R$ 5,80 | R$ 4,50 | R$ 5,80 |
| Valorização imóveis SP | 2% | 5% | 8% | — |
| TRS (Taxa de Retirada Segura) | 4,0% | 5,0% | 6,0% | — |

> **TRS realista 5%** alinhada com decisão D15 ([decisions.md](decisions.md))
> e com `goal.if.schema.json:trs_pct.default` (5%). Justificativa: carteira
> mista BR + imóveis com yield líquido ≥ TRS sustenta retiradas levemente
> acima de Trinity 4% sem comprometer probabilidade de sucesso (referência:
> Perini ampliado, AUVP). Cenário pessimista 4% preserva Trinity clássico
> como fallback conservador.

---

## DISCLAIMERS OBRIGATÓRIOS

Incluir nota de disclaimer nos seguintes contextos:

1. Tabela fundamentalista de ações — "Valores estimados — confirmar antes de agir"
2. DY de FIIs de referência — "DY passado não garante DY futuro"
3. Projeção renda passiva 2035 — "Premissas: IGPM 4%/ano, DY ações 5-8%, DY FIIs 9%, retorno real 6%. Revisar anualmente."
4. Taxa PGBL — "Confirmar taxa real de administração"
5. Benchmark de fundos — "Períodos variam por fundo — retorno acumulado desde aporte"

---

## CICLO DE ATUALIZAÇÃO

| Frequência | Escopo | Modo padrão |
|---|---|---|
| Quinzenal | Tático (D1-D6): deltas, despesas vs tetos, aportes, tarefas, alertas | ⚡ Tático |
| Trimestral | Análise completa (10 etapas) + dashboard | 📊 Estratégico |

---

## RESTRIÇÕES IMPORTANTES

- Nunca avançar sem checkpoint e confirmação explícita
- Se dado incompleto, perguntar — nunca assumir silenciosamente
- NÃO confundir despesas PJ com pessoais
- Todos os números = visão pós-quitação do financiamento
- Benchmark fundos = retorno acumulado desde aporte (NÃO "últimos 12 meses")
- Para questões tributárias EUA, sempre sinalize necessidade de CPA especializado
- Quando possível, fazer recomendações específicas de produtos financeiros
