---
id: ADR-242
type: adr
title: "LLM `category_hint` consumido no TransactionClassifier + sentinel `info_fiscal_anual`"
status: Decidido
phase: A17.incremental-correctness
date: "2026-05-21"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
  - "[[ADR-186]]"
  - "[[ADR-233]]"
  - "[[ADR-236]]"
  - "[[ADR-241]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 242"
  - "LLM category hint"
tags:
  - area/pipeline
  - area/llm
  - status/decidido
  - type/adr
size_lines: 144
---

# ADR-242 — LLM `category_hint` consumido no TransactionClassifier

**Status:** Decidido • **Data:** 2026-05-21 • **Relaciona** [[ADR-097]] (warnings tipados), [[ADR-137]] (category_template canônico), [[ADR-143]] (methodology=code), [[ADR-186]] (learned rules), [[ADR-233]] (prompt versioning), [[ADR-236]] (PJ labels), [[ADR-241]] (E2 workspace-scoped)

## Contexto

O stage `extract_with_llm` ([pipeline/stages/extract_with_llm.py:302](../../pipeline/stages/extract_with_llm.py:302)) escreve `categoria_sugerida` por transação no payload E2-llm. O campo é **dead code**: o classifier ([pipeline/domain/services/transaction_classifier.py](../../pipeline/domain/services/transaction_classifier.py)) não lê. Toda transação que regra determinística não casa cai em `nao_identificado`/`outras_receitas`, mesmo quando o LLM (que viu o documento inteiro) emitiu hint confiável.

Caso observado em relatório real (workspace `Campos`, run `c36c4baf-…`, dezembro/2025): informe de rendimentos Itaú extraído via LLM produziu 4 linhas:

- "Rendimento Bruto RDB/CDB" R$ 787,75 — `categoria_sugerida: "rendimento_investimento"` → caiu em `receita_investimento` (genérico)
- "Rendimento Líquido RDB/CDB (valor a declarar)" R$ 610,85 — `categoria_sugerida: "rendimento_investimento"` → **double-counting**: bruto = líquido + IRRF; somar ambos infla receita em ~78%
- "IRRF retido" R$ -176,90 — `categoria_sugerida: "imposto"` → caiu em `nao_identificado`
- "Parcelas pagas Crédito Imobiliário (ano 2025)" R$ -52.429,06 — `categoria_sugerida: "financiamento_imobiliario"` → caiu em `nao_identificado`. Esta linha é o **acumulado anual** do informe IR, não evento de dezembro; tratá-la como despesa mensal quebra `fluxo_mensal_detalhado` (taxa de poupança ficou em -3661% e despesa mensal média sobrenanceira).

Causa direta: classificador ignora o hint LLM. Causa estrutural: linhas anuais do informe IR não têm fronteira semântica no pipeline — entram como `transacoes` mensais e poluem todo cálculo de fluxo.

## Decisão

### D1. Consumir `category_hint` como fallback hierárquico

Hierarquia de categorização passa a ser (em ordem decrescente de precedência):

```
1. transferência interna (paridade legado)
2. PJ label (ADR-236 §D2)
3. learned_rule (ADR-186 §D5)
4. regra determinística (KeywordMatcher income/expense)
5. llm_hint (ADR-242 — preenche apenas quando 1-4 caem em default)
6. default (`nao_identificado` / `outras_receitas`)
```

**LLM hint é o último fallback antes do default**. Regra determinística sempre vence (determinismo + golden tests; manual override + learned rule sempre vencem por [[ADR-186]]).

Hint é traduzido para categoria canônica via tabela explícita em [pipeline/domain/services/llm_category_hint.py](../../pipeline/domain/services/llm_category_hint.py) — testável em unit, vocabulário rastreável.

### D2. Sentinel `info_fiscal_anual` exclui linha do fluxo

Vocabulário do hint inclui o sentinel `info_fiscal_anual` para marcar linhas que NÃO são eventos de caixa mensal: acumulados anuais do informe IR (parcelas pagas ano X, valor a declarar, etc.). O classifier **skipa** a transação inteira em [transaction_classifier.py `_classify_account_audit`](../../pipeline/domain/services/transaction_classifier.py) antes mesmo da hierarquia D1.

Trata o caso observado:
- "Parcelas pagas Crédito Imobiliário (ano 2025)" R$ -52.429,06 → `info_fiscal_anual` → excluída do fluxo. A despesa real está no extrato bancário, mês a mês.
- "Rendimento Líquido (valor a declarar)" → `info_fiscal_anual` quando há linha "Bruto" separada (evita double-counting). Visível no IRPF (E1.6) mas não como receita de caixa.

### D3. Vocabulário enum (20 valores) referendado pelo financial-planner

5 grupos:
- **Receitas (6)** — distinção ativa/passiva por classe (Bruno Perini): `salario`, `pro_labore_pj`, `aluguel_recebido`, `rendimento_renda_fixa`, `dividendo_jcp`, `ganho_capital_resgate`.
- **Moradia & vida (6)** — Cerbasi separa juros vs. amortização (juros = custo, amortização = patrimônio): `moradia_financiamento_juros`, `moradia_financiamento_amortizacao`, `moradia_aluguel_pago`, `moradia_outros`, `alimentacao`, `transporte`.
- **Discricionárias (4)**: `saude`, `educacao`, `lazer_assinatura`, `vestuario_pessoal`.
- **Futuro & passivos (4)**: `aporte_investimento`, `seguro_previdencia`, `imposto_pago`, `juros_divida_consumo`.
- **Operacional (2 — flag, não despesa)**: `transferencia_interna`, `info_fiscal_anual`.

Vocabulário exposto **no prompt LLM** ([pipeline/llm/prompts/e2_llm.py](../../pipeline/llm/prompts/e2_llm.py)) + **na description do Pydantic** ([pipeline/llm/schemas/e2_llm_extract.py](../../pipeline/llm/schemas/e2_llm_extract.py)). Pydantic `Literal[...]` estrito **não** é aplicado nesta lane (artifacts E2 antigos teriam `category_hint=null|""` e quebrariam `validate_dict` pós-write). Enum estrito vira follow-up quando o vocabulário consolidar.

Campo `category_hint` continua `Optional[str]`. Hints fora do vocabulário são silentemente ignorados pelo classifier (fallback ao default) — não rejeitam o artifact.

### D4. Audit trail via `categorization_origin`

Novo campo `categorization_origin: str | None` em `ClassifiedTransaction`. Valores: `"rule"`, `"learned"`, `"pj_label"`, `"llm_hint"`, `"default"`. Adapter backend pode telemetrar share de `llm_hint` em E4 / `pipeline_stage_logs.output_summary` para medir valor empírico da feature.

### D5. Prompt versionado

`PROMPT_VERSION` em `pipeline/llm/prompts/e2_llm.py` bumpa para `1.1.0` ([[ADR-233]] enforça via `dev/check_prompt_version_bumped.py`). Mudança é additive (description campo + regras explícitas no system prompt sobre informe IR + sentinel `info_fiscal_anual`).

## Alternativas consideradas

- **(a) Forçar Pydantic `Literal[...]` no `category_hint`.** Rejeitada nesta lane: artifacts E2 antigos teriam `category_hint=null` e quebrariam `validate_dict` em [DBArtifactStore.write](../../backend/app/services/db_artifact_store.py:200) pós-update do schema. Migração de backfill ("set category_hint='outros' where null") seria extra trabalho sem ROI imediato. Follow-up registrado.
- **(b) Hint LLM vence regra determinística.** Rejeitada: quebra determinismo (golden tests viram frágeis); LLM pode "errar com confiança" sobre transações que regra resolveria deterministicamente.
- **(c) Skip `info_fiscal_anual` upstream (no extractor).** Rejeitada: perde rastro auditável em E2/E3 (linha some sem registro). Skip no classifier preserva linha em E2/E3 (debugging/audit) e remove só do output E4.
- **(d) Separar juros vs. amortização do financiamento em duas categorias canônicas (Cerbasi puro).** Aceita parcialmente: vocabulário tem `moradia_financiamento_juros` E `moradia_financiamento_amortizacao` separados, mas ambos mapeiam para `moradia` canônica nesta lane. Follow-up: KPI Cerbasi "custo de moradia/renda" pede separação real — sai em lane dedicada (não bloqueia esta).

## Consequências

- ✅ **Fix observado**: linha "Parcelas pagas Crédito Imobiliário (ano 2025)" deixa de inflar despesa mensal em R$ 52k; taxa de poupança volta a faixa razoável.
- ✅ **Categorização incremental melhora** para qualquer documento que o LLM processou: descrições genéricas que keyword não cobre ganham categoria canônica via hint.
- ✅ **Audit trail explícito**: `categorization_origin` permite telemetrar quanto da classificação vem de cada camada — observável + medível.
- ⚠️ **Quality do hint depende do LLM** — se o LLM emite vocabulário fora do enum, hint silenciosamente vira `None` (no-op). Esperado e aceitável: regra + learned + default cobrem o resto. Monitorar via telemetria.
- ⚠️ **Linhas `info_fiscal_anual` somem de E4** — ainda visíveis em E2-llm (audit), mas não em fluxo/receitas/despesas. Decisão correta para fluxo de caixa mensal; mantém info para IRPF (E1.6) que tem semântica anual.
- ❌ **Não substitui melhor parsing de informe IR** — solução de superfície. A melhoria estrutural é o extractor distinguir transações mensais de acumulados anuais na fonte (parser determinístico para informe rendimentos). Tracked como follow-up.

## Gates de regressão

- **T1** — `tests/unit/pipeline/test_transaction_classifier.py::TestLLMCategoryHint` (já implementado): 7 testes cobrindo skip de `info_fiscal_anual`, fallback de hint, precedência regra > hint, hint inválido vira default, transferência via hint, audit origin.
- **T2** — Manual/dogfood: regerar o relatório real (workspace `Campos`, run sobre dezembro/2025) e validar que `total_receita` e `total_despesa` saem coerentes com os extratos bancários reais (não dos 4 lançamentos do informe IR).

## Follow-ups (débito registrado, não bloqueia merge)

1. **Enum estrito no Pydantic** — `Literal[...]` com migração de backfill para artifacts antigos.
2. **Separação juros/amortização no E5** — KPI Cerbasi "custo de moradia/renda" só com juros; amortização vira aporte ao patrimônio. Requer split na própria categorização (categoria canônica `moradia_juros` vs `moradia_amortizacao`).
3. **Parser determinístico de informe rendimentos** — eliminar dependência de LLM para o documento mais formal/estável que existe (Itaú/Santander/C6 todos seguem layout padrão). Reduz custo + variabilidade.
