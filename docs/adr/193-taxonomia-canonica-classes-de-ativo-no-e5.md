---
id: ADR-193
type: adr
title: "Taxonomia canônica de classes de ativo no E5 (10 buckets)"
status: Decidido
date: "2026-05-11"
relates_to:
  - "[[ADR-141]]"
  - "[[ADR-143]]"
  - "[[ADR-097]]"
  - "[[ADR-160]]"
supersedes: []
superseded_by: []
aliases: ["ADR 193", "Asset classifier taxonomy"]
tags:
  - area/pipeline
  - area/money
  - methodology/auvp
  - methodology/perini
  - methodology/cerbasi
  - status/decidido
  - type/adr
---

# ADR-193 — Taxonomia canônica de classes de ativo no E5 (10 buckets)

**Status:** Decidido · **Data:** 2026-05-11 · **Implementação:** `pipeline/domain/services/asset_classifier.py` (`classify_asset`, `BUCKETS`, `EVALUATION_ORDER`, `OutrosExcessivoWarning`); refatora `InvestimentosClassesAnalyzer` e `TopAtivosAnalyzer`; atualiza `config/scoring.json::asset_class_keywords` e `config/schemas/e5_analysis.schema.json` (enum em `top_ativos.classe` + `tabela_classes.categoria`); propaga `OutrosExcessivoWarning` para `alertas[]` via `build_alertas` em [`e5_serialization.py`](../../pipeline/domain/services/e5_serialization.py).

## Contexto

Card "Investimentos por Classe" do relatório E5 (S3) é hoje opaco: dogfood real apresenta R$ 4,08M total com 76,9% em `Imóveis Investimento` e **23,1% (R$ 944k) em `Outros`** — máscara absoluta para o tipo de ativo. Inspecionando o baseline, "Outros" contém ações (PETR4/ITSA4/BRKM5), RDB/CDB/LCI de 5 bancos, fundos multimercado, criptos (Hashdex), poupança Caixa/Bradesco, US$ em conta XP. Todos classificáveis.

Quatro fontes de verdade conflitavam:

1. **`InvestimentosClassesAnalyzer`** (hardcoded) iterava só sobre 4 classes (`Ações`, `Renda Fixa`, `Cripto`, `Contas Bancárias`) + `Imóveis Investimento` + `Outros` = 6 buckets.
2. **`config/scoring.json::asset_class_keywords`** tinha 7 classes (adicionando `Fundos`, `Internacional`, `Previdência`), mas o analyzer **ignorava** as 3 novas (iterava só sobre defaults de 4).
3. **`config/schemas/e5_analysis.schema.json`** enum de `top_ativos.classe` fixava 6 valores; `tabela_classes.categoria` era string aberta — sem garantia de consistência entre ranking e agregado.
4. **ADR-141 (Roadmap)** definia 7 classes AUVP autênticas com sub-buckets RF (`rf_pos/rf_pre/rf_ipca/acoes_br/acoes_int/fiis/caixa`) para o **Goal alocação alvo** — granularidade maior que (1)-(3) mas só descida ao schema de goal, não ao card de leitura.

**Bug raiz** no algoritmo legado: classificação lia `bens.investimentos[].tipo` (que vem do IRPF E1.5 como código agregado: `investimento`, `renda_fixa`, `participacao_societaria`, `fundo_investimento`, `poupanca`, `conta_bancaria`, `outros`) e aplicava `keyword in tipo_lower`. Keyword `"renda fixa"` (espaço) **não casava** com `tipo="renda_fixa"` (underscore). A `descricao` (que carregava "ACOES ITSA4", "CDB BTG", "RDB Nubank", "LCI Opea", "HASHDEX NASDAQ CRYPTO", "FIC FIM Alaska", "POUPANCA Caixa") era **ignorada**.

Sign-off do `financial-planner` (2026-05-11) consolidou Perini + Cerbasi + AUVP para o público ICP (PJ/CLT alta renda, R$ 4M+ patrimônio): subconjunto pragmático do ADR-141, sem sub-buckets RF (que dependem de indexador upstream ainda não-entregue pelo E1.5).

## Decisão

**10 buckets canônicos** em `BUCKETS` (8 financeiros + Imóveis + Outros):

| Bucket | Inclui | Metodologia dominante |
|---|---|---|
| `Cripto` | BTC, ETH, Hashdex, exchanges | Perini |
| `Previdência` | PGBL, VGBL | Cerbasi |
| `FIIs` | Fundos imobiliários (tijolo + papel; ticker XXXX11) | Perini + ADR-160 |
| `Internacional` | IVVB, ETFs globais, USD/Wise/BofA, moeda estrangeira | AUVP |
| `Renda Fixa` | CDB, RDB, LCI, LCA, Tesouro, debênture, CRI, CRA, poupança | AUVP + Cerbasi |
| `Ações BR` | Ações brasileiras, ETFs BR, participação societária listada | Perini + AUVP |
| `Fundos` | FIC, FIM, FIA, fundos multimercado/ações abertos | AUVP |
| `Caixa` | Conta-corrente, saldo bancário operacional | AUVP `caixa_pct` |
| `Imóveis Investimento` | Imóveis não-residência (já tratado por `residencia_keyword`) | Cerbasi + Perini |
| `Outros` | Fallback **com gate** (warning se > 5%) | — |

**Ordem de avaliação** (`EVALUATION_ORDER`, especialização → fallback):

```
Cripto → Previdência → FIIs → Internacional → Renda Fixa
    → Ações BR → Fundos → Caixa → Outros
```

Especializações primeiro garantem que keywords genéricas (e.g. "fundo" em "Fundos Imobiliários", "participacao societaria" em "LCI via BTG") não roubem o ativo da classe mais específica. **Renda Fixa antes de Ações BR** porque suas keywords (LCI/CDB/RDB/Tesouro) são muito específicas e devem vencer quando o tipo IRPF agregado diz `participacao_societaria` mas a descrição contém `LCI ...` (caso real do dogfood).

**Algoritmo:** `classify_asset(tipo, descricao, instituicao)` concatena os 3 campos, normaliza separadores `_` e `-` para espaço (corrige o bug raiz), lowercase, e bate keywords em `EVALUATION_ORDER`. Sinal forte adicional: ticker FII pattern `\b[a-z]{4}11\b` → `FIIs` imediatamente.

**Função única** em `pipeline/domain/services/asset_classifier.py` é consumida por `InvestimentosClassesAnalyzer._classify_investments` **e** `TopAtivosAnalyzer._build_inv_candidate` — agregado e ranking nunca divergem para o mesmo ativo.

## Sub-decisões

1. **Previdência separada de Renda Fixa.** Atuarialmente é RF longo (AUVP); semanticamente é proteção/aposentadoria (Cerbasi). Para o público ICP, Cerbasi vence. Quando ADR-141 v2 entrar pra valer no Goal, o mapeador soma Previdência ao `rf_pos/pre/ipca` conforme produto subjacente (decisão postergada).
2. **FIIs separados de Imóveis físicos.** Perini + ADR-160. FII é renda passiva isenta (DY); imóvel direto carrega vacância e tributação. Misturar engana qualquer leitura de "renda passiva".
3. **Caixa separado de Internacional.** Conta-corrente BRL operacional ≠ USD em Wise (decisão de proteção cambial). Renomeia `Contas Bancárias` → `Caixa` (bucket escalar `bens.contas_bancarias` continua somando, agora em `Caixa`).
4. **Sub-buckets RF (pos/pre/IPCA) ficam para depois.** E1.5 não entrega indexador hoje; forçar 3 buckets RF produziria `rf_outros` cheio. Roadmap em ADR-141 § v2 — quando o parser de indexador existir, `Renda Fixa` se expande em 3 linhas e o resto fica intacto.
5. **Cripto como bucket próprio mesmo se < 1%.** AUVP debate; público real tem Hashdex/BTC e quer ver. Custo = 1 linha do enum.
6. **`Outros` com gate (`OutrosExcessivoWarning`, threshold 5%).** Dataclass tipada (ADR-097 D1) emitida pelo analyzer; propagada para `alertas[]` do E5 via `build_alertas`. Outros > 5% sinaliza cobertura incompleta de keywords ou descrição ausente — vira `needs_review` operacional, não mascarado.
7. **Schema E5 fecha `tabela_classes.categoria` no mesmo enum de `top_ativos.classe`.** Antes `categoria` era string aberta — permitia divergência silenciosa entre ranking e agregado. Pós-ADR-193 os dois compartilham 10 valores.

## Migração

- Code-only — sem migration DB. Schema E5 atualizado in-place. Goldens regerados.
- `analyze_investimentos_classes` em [`scripts/e5_analyze.py:1761`](../../scripts/e5_analyze.py) é dead code (legacy duplicado pré-A5b extraction); **não removido neste PR** para limitar surface — cleanup separado.
- Goal `alocacao_alvo` v1 (4 buckets) continua intacto — esta ADR não touch ADR-141 v2 adoption.

## Consequências

- **+:** Card "Investimentos por Classe" no dogfood passa de 6 linhas (76,9% Imóveis + 23,1% Outros) para distribuição com Ações BR / Renda Fixa / Fundos / Cripto / Caixa / Internacional / Imóveis Investimento, `Outros` ≤ 5%. Top 15 ativos ganha classes corretas (era zero ativos classificados antes — `top_ativos: []` em produção).
- **+:** Methodology-as-code (ADR-143) — taxonomia + ordem de avaliação vivem no docstring de `classify_asset`; rationale aqui.
- **+:** Schema strict no enum protege contra introdução acidental de classe nova sem ADR.
- **−:** Adicionar classe nova (e.g. quando ADR-141 v2 entrar) requer mudar simultaneamente `BUCKETS`, `EVALUATION_ORDER`, `_DEFAULT_KEYWORDS`, schema E5 enum e tokens do frontend. Custo aceito (5 arquivos), preferível a divergência.
- **−:** Workspace com Outros > 5% pós-deploy gera `alertas[]` permanente até que keywords/descrições sejam refinadas. Funcionalmente correto, operacionalmente ruidoso até o catalog ser estabilizado.

## Critério de aceite

- [x] Enum único em [config/schemas/e5_analysis.schema.json](../../config/schemas/e5_analysis.schema.json) — `tabela_classes.categoria` deixa de ser string aberta e vira o mesmo `enum` 10-valores de `top_ativos.classe`.
- [x] `InvestimentosClassesAnalyzer` itera sobre todos os 10 buckets, classifica via `classify_asset(tipo, descricao, instituicao)`.
- [x] `TopAtivosAnalyzer._classify` usa a mesma função compartilhada.
- [x] `config/scoring.json::asset_class_keywords` ganha entradas `FIIs` e `Caixa`; `Ações` renomeado para `Ações BR`; `Contas Bancárias` removido (subsumido por `Caixa`).
- [x] `OutrosExcessivoWarning` emitida quando `bucket['Outros'].pct > 5.0`, propagada para `alertas[]` do E5 via `build_alertas`.
- [x] Frontend `Top15AtivosCard.tsx::CLASSE_TOKEN` cobre 10 buckets com tokens do design system (sem hex literal).
- [x] Tests: `tests/unit/pipeline/test_asset_classifier.py` (novo, cobertura de ordem/normalização/buckets/warning); `test_investimentos_classes_analyzer.py` + `test_top_ativos_analyzer.py` atualizados.
- [x] Pipeline + backend suites verdes pós-mudança.
- [ ] Smoke manual no workspace dogfood (`028125eb-…`): distribuição esperada Ações BR > 0, Renda Fixa > 0, Fundos > 0, Cripto > 0, Caixa > 0, Internacional > 0, Imóveis Investimento ≈ R$ 3,14M, **Outros ≤ 5%**.

**Relaciona-se a:** [[ADR-141]] (taxonomia AUVP autêntica para Goal — alinhamento parcial), [[ADR-143]] (methodology = code), [[ADR-097]] D1 (warnings tipados), [[ADR-160]] (eficiência tributária imóvel direto vs FII), [[ADR-089]]/[[ADR-097]] D3 (config tipado por value object). Origem: investigação de produto 2026-05-11 a partir de inspeção do card "Investimentos por Classe" no workspace dogfood.
