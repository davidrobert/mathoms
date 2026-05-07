---
id: ADR-161
type: adr
title: "Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos)"
status: Decidido
phase: "Onda 8"
date: "2026-05-04"
relates_to: ["[[ADR-153]]", "[[ADR-156]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 161"]
tags:
  - area/pipeline
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 52
---

# ADR-161 — Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos)

**Status:** Decidido (Onda 8) • **Data:** 2026-05-04 • **Relaciona** [ADR-153](#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples), [ADR-156](#adr-156--patrimônio-em-plano-é-single-source-via-patrimonio_snapshot-direção-e--onda-7).

**Contexto:** ADR-153 entregou 5 regras determinísticas no `SuggestionGenerator` (TRS desalinhada, reserva insuficiente, alocação fora de alvo, aporte abaixo da meta, dolarização atrasada). Revisão de produto 2026-04-29 (sign-off financial-planner) identificou que essas 5 regras cobrem **AUVP+Perini puros**, mas faltam 6 sinais consagrados em Cerbasi (proteção/comportamental/endividamento) e Perini "300" (renda passiva real) para o produto endereçar família alta-renda PJ por completo. Cap de 6 sugestões/relatório força exclusão prematura quando regras escalam.

**Decisão:** Adicionar 6 regras canônicas v2 no gerador determinístico, subir `SUGGESTION_CAP` de 6 → 8, e introduzir campo `category` (string, nullable) para agrupamento semântico cross-kind.

**Sub-decisões:**

1. **6 regras v2** (todas defensivas — snapshot incompleto ⇒ skip silencioso, sem warning):

   | Kind | Trigger | Severity | Methodology | Snapshot fields |
   |---|---|---|---|---|
   | `endividamento_perigoso` | `endividamento.percentual_patrimonio > 30%` OR `custo_medio_pct_aa > goals.retorno_esperado_pct_aa` | `danger` | Cerbasi/AUVP | `endividamento.{percentual_patrimonio, total_dividas, custo_medio_pct_aa}`, `goals.retorno_esperado_pct_aa` |
   | `taxa_poupanca_caindo` | 2 quedas trimestrais consecutivas >5pp | `warning` | Cerbasi · comportamental | `fluxo_caixa.taxa_poupanca_trimestral_historico: list[float]` |
   | `seguros_insuficientes` | `renda_pj_mensal > R$50k` AND `seguros.vida_invalidez != True` | `danger` | Cerbasi · proteção | `fluxo_caixa.renda_pj_mensal`, `seguros.vida_invalidez` |
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
2. **Cross-kind dedup por category** — quando 2+ regras de mesma `category` disparam, ranking pode escolher só a mais severa OU agregar copy.
3. **UI badges de category** — chip colorido na SuggestionCard mostrando "Proteção" / "Carteira" / etc. (Onda 9 polish).
