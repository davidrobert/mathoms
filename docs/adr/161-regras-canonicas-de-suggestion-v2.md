---
id: ADR-161
type: adr
title: "Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos)"
status: Decidido
phase: "Onda 8"
date: "2026-05-04"
relates_to: ["[[ADR-153]]", "[[ADR-156]]", "[[ADR-240]]", "[[ADR-365]]"]
supersedes: []
superseded_by: []
amended_at: ["2026-08-11"]
aliases: ["ADR 161"]
tags:
  - area/pipeline
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 111
---

# ADR-161 — Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos)

**Status:** Decidido (Onda 8) • **Data:** 2026-05-04 • **Relaciona** [ADR-153](#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples), [ADR-156](#adr-156--patrimônio-em-plano-é-single-source-via-patrimonio_snapshot-direção-e--onda-7).

> **Emenda (FP-010, 2026-08-11):** a regra `seguros_insuficientes` foi
> **removida**. Os inputs que a tabela abaixo declara (`fluxo_caixa.renda_pj_mensal`,
> `seguros.vida_invalidez`) nunca existiram no schema E5 — o enriquecimento
> previsto no Follow-up #1 foi **superseded** pela [[ADR-240]], que entregou
> `protecao_patrimonial.gap_qualitativo` com predicado mais estreito e correto.
> As outras 5 regras v2 e as sub-decisões 2-5 (cap=8, `category`, defensividade)
> permanecem vigentes. Detalhe em §Emenda 2026-08-11 ao final.

**Contexto:** ADR-153 entregou 5 regras determinísticas no `SuggestionGenerator` (TRS desalinhada, reserva insuficiente, alocação fora de alvo, aporte abaixo da meta, dolarização atrasada). Revisão de produto 2026-04-29 (sign-off financial-planner) identificou que essas 5 regras cobrem **AUVP+Perini puros**, mas faltam 6 sinais consagrados em Cerbasi (proteção/comportamental/endividamento) e Perini "300" (renda passiva real) para o produto endereçar família alta-renda PJ por completo. Cap de 6 sugestões/relatório força exclusão prematura quando regras escalam.

**Decisão:** Adicionar 6 regras canônicas v2 no gerador determinístico, subir `SUGGESTION_CAP` de 6 → 8, e introduzir campo `category` (string, nullable) para agrupamento semântico cross-kind.

**Sub-decisões:**

1. **6 regras v2** (todas defensivas — snapshot incompleto ⇒ skip silencioso, sem warning):

   | Kind | Trigger | Severity | Methodology | Snapshot fields |
   |---|---|---|---|---|
   | `endividamento_perigoso` | `endividamento.percentual_patrimonio > 30%` OR `custo_medio_pct_aa > goals.retorno_esperado_pct_aa` | `danger` | Cerbasi/AUVP | `endividamento.{percentual_patrimonio, total_dividas, custo_medio_pct_aa}`, `goals.retorno_esperado_pct_aa` |
   | `taxa_poupanca_caindo` | 2 quedas trimestrais consecutivas >5pp | `warning` | Cerbasi · comportamental | `fluxo_caixa.taxa_poupanca_trimestral_historico: list[float]` |
   | ~~`seguros_insuficientes`~~ | ~~`renda_pj_mensal > R$50k` AND `seguros.vida_invalidez != True`~~ | ~~`danger`~~ | Cerbasi · proteção | **Removida — FP-010, 2026-08-11** (ver §Emenda) |
   | `concentracao_instituicao` | algum banco com `>40%` do investível | `warning` | AUVP | `patrimonio.por_instituicao` ou `investimentos.por_instituicao: dict[str, float]` |
   | `lifestyle_creep` | despesa essencial cresce >1.5x inflação acumulada por 6m | `warning` | Cerbasi/Perini | `fluxo_caixa.despesa_essencial_historico: list[float]`, `inflacao.acumulada_pct_no_periodo` |
   | `renda_passiva_real_baixa` | `progresso_if > 50%` AND `renda_passiva/custo_vida < 30%` | `info` | Perini "300" | `goals.progresso_if_pct`, `fluxo_caixa.{renda_passiva_mensal_atual, despesa_mensal_media}` |

2. **Cap revisado: 6 → 8.** Com 11 regras candidatas, cap=6 forçaria exclusão de itens relevantes. 8 mantém densidade controlada da UI e dá folga para ranking.

3. **Campo `category`** (`alvo_if`, `carteira`, `protecao`, `comportamental`, `endividamento`, `usa_plano`) auto-derivado via `KIND_TO_CATEGORY` em `pipeline/domain/types/suggestion.py`. Persistido em `suggestions.category` (String(32) nullable, migration `d9e0f1a2b3c4`). Habilita:
   - Sumário por categoria (`SuggestionsSummaryResponse.by_category` — Onda 8 #5).
   - Futura dedup cross-kind (TRS desalinhada + aporte_abaixo_meta são ambos `alvo_if`).
   - Filtros UI/relatório por dimensão metodológica.

4. **Defensividade reforçada.** Cada regra verifica presença de **todos** os campos antes de derivar. Falha graciosamente: rule retorna `None`, generator continua com as outras. Pipeline pode evoluir snapshot (adicionar `por_instituicao`, `seguros`, `inflacao`, `taxa_poupanca_trimestral_historico`) sem coordenação com generator — regras passam a disparar automaticamente.

5. **Não-mudanças:** dedup_key continua **per-kind** (não cross-kind por category). Mudar isso é semântica frágil — dispensa para Onda 9+.

**Consequências:**

- ✅ Cobertura metodológica completa (Cerbasi/AUVP/Perini) sem dependência LLM — gerador continua determinístico, testável, idempotente.
- ✅ Backward-compatible: `category` é nullable; campos novos no snapshot são opcionais (skip silencioso). Migration aditiva sem backfill.
- ✅ 6 testes determinísticos por regra v2 (`tests/test_suggestion_generator.py`) + smoke test 11-regras-coexistindo. Total: 39 testes verdes.
- ⚠️ Pipeline E5 ainda não popula `taxa_poupanca_trimestral_historico`, `por_instituicao`, `seguros`, `inflacao`, `despesa_essencial_historico`, `renda_passiva_mensal_atual`. Regras v2 ficam latentes até enriquecimento — débito documentado em Follow-ups #1.
- ⚠️ Ranking só por `(severity, amount)` — não considera category. Casos onde 4 regras `protecao` aparecem juntas pode dominar. Refinamento opcional (Onda 9): boost para 1ª de cada category.
- ❌ Ranking baseado em LLM/contexto fica fora — v2 deliberadamente determinístico.

**Follow-ups:**

1. **Pipeline E5 enrichment** — popular os 6 campos snapshot novos a partir de séries históricas E3/E4 e configs (institutions snapshot, IRPF income, inflation index Brapi). Track separado: cada campo é independente.
   - ✅ **FP-001** (W1-T02 · 2026-05-06) — `rule_renda_passiva_real_baixa` ganha alias defensivo `if_pct ↔ progresso_if_pct` + `goals.renda_passiva_mensal_observada_brl` (snapshot real expõe `if_pct`, paridade com `IFProjection.to_legacy_dict`).
   - ✅ **FP-002** (W1-T02 · 2026-05-06) — `e5_analyzer_adapter` agora passa `goals={"if_pct": if_projection.if_pct}` para `PontosFortesAnalyzer`; ponto forte "Caminho para IF" dispara para `if_pct ≥ 20`.
   - ✅ **FP-003** (W1-T02 · 2026-05-06) — `rule_dolarizacao_atrasada` removida (dead rule pós-ADR-168 USA modo removal). `KIND_TO_CATEGORY` + `VALID_SUGGESTION_KINDS` + `VALID_SUGGESTION_CATEGORIES` purgados de `usa_plano`.
   - ✅ **FP-009** (W1-T07 · 2026-05-06) — `IFProjection.to_legacy_dict` emite `retorno_esperado_pct_aa` (== `IFProjectorConfig.retorno_real_anual_pct`); `rule_endividamento_perigoso` ativa carry-trade trigger via `CARRY_TRADE_MARGIN_PP=1.0` (Cerbasi · Equilíbrio Financeiro). Refinamento ADR-161 (FP-004) alinhará retorno esperado com retorno ponderado da carteira atual.
   - ✅ **FP-010** (2026-08-11) — `rule_seguros_insuficientes` **removida**: o
     enriquecimento previsto neste follow-up não vinha para ela (o E5 nunca teve
     `seguros` nem `renda_pj_mensal`; a chave canônica virou
     `protecao_patrimonial`, [[ADR-240]]), e o conselho já tem produtor vivo com
     predicado mais estreito. Ver §Emenda 2026-08-11.
2. **Cross-kind dedup por category** — quando 2+ regras de mesma `category` disparam, ranking pode escolher só a mais severa OU agregar copy.
3. **UI badges de category** — chip colorido na SuggestionCard mostrando "Proteção" / "Carteira" / etc. (Onda 9 polish).

## Emenda 2026-08-11 — FP-010: `seguros_insuficientes` removida (não latente: sem destino)

**O que se descobriu.** O Follow-up #1 classificou 6 regras como "latentes até
enriquecimento do E5" e as tratou como equivalentes. Não são. Para
`seguros_insuficientes`, o enriquecimento **não vinha** — e a prova é dupla:

- `config/schemas/e5_analysis.schema.json` não tem `seguros` nem
  `fluxo_caixa.renda_pj_mensal`; a chave canônica de proteção é
  `protecao_patrimonial` (ADR-240, 2026-07);
- zero rows com essa `kind` em `suggestions` no DB de dogfood, contra ~450 rows
  das outras seções.

**Por que remover em vez de re-apontar para `protecao_patrimonial`.** O conselho
já tem **produtor vivo**: `pontos_urgentes_analyzer._seguro_vida_item`, reescrito
na A40.l10 ([[ADR-365]] §D4) para mapear o predicado canônico da [[ADR-240]]
(KPI F — `gap_qualitativo` com `categoria == "vida"`). Esse predicado é
**mais estreito e mais correto** que o desta ADR: exige dependente econômico,
enquanto o desta usava renda PJ alta como proxy. O comentário da l10 é explícito
sobre o defeito que isso causava — "Contratar seguro de vida" era emitido para
titular solteiro sem dependente, *conselho errado, não default conservador*.
Re-apontar a regra exigiria replicar `_GAP_VIDA_TAXONOMIA` (com seus ramos
`degenerada` / `pendente_de_dado`) dentro de `suggestion_rules` — que é
literalmente o modo de falha que a [[ADR-365]] §Estado-alvo previu ("passamos de
cinco representações para seis").

**Consequência que fica aberta, com condição de retomada.** O gap de vida
**merece** ser promovível a `Decision` (Cerbasi: proteção é decisão de casal,
com custo recorrente e revisão por evento de ciclo de vida) — mas não enquanto
não puder ser **dimensionado**: `renda_propria_brl` é fixo em `0`
(ADR-240 §D3 → `degenerada`) e `gross_estate_brl_cents` é `0` hardcoded
(ADR-240 §Deferido). `Decision` de proteção sem capital declarado é o checkbox
que o método critica, agora com persistência event-sourced. **Retomada:** quando
os dois campos tiverem produtor real, escreva uma regra nova que **chame** o
predicado da ADR-240 (~15 linhas) — nenhuma linha vem do corpo removido.

**O que sobrevive.** `seguros_insuficientes` continua em `KIND_TO_CATEGORY`
(pipeline), em `VALID_SUGGESTION_KINDS` (backend) e na union TS: é vocabulário
de **leitura**. Kind sem produtor é inerte; kind removido tornaria row histórica
ilegível — mudança de contrato com custo próprio e zero ganho.

**Gate que impede a re-criação silenciosa.** `VALID_SECTION_IDS` em
`SuggestionDraft.__post_init__` + varredura AST em
`tests/unit/pipeline/test_suggestion_rules.py` (PR anterior, mesma sessão) —
a regra removida emitia `section_id="S6"`, seção **queimada por design**, e
nenhum gate via. Revisão: `financial-planner` + `senior-cto`, 2026-08-11.
