---
id: ADR-135
type: adr
title: "Versionamento temporal de séries fiscais e câmbio"
status: Decidido
phase: "Sprint A7"
date: "2026-04-26"
amended_at: ["2026-07-07", "2026-08-15", "2026-08-24"]
relates_to: ["[[ADR-090]]", "[[ADR-238]]", "[[ADR-389]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 135"]
tags:
  - area/money
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 101
---

> **Emenda (2026-07-07):** `rate` para pares `*/BRL` é PTAX de **compra** —
> ver §"Emenda — lado da PTAX em pares */BRL (2026-07-07)".
>
> **Emenda (2026-08-15):** `ir_brackets` ~~deixa de existir~~ **deixará de
> existir** — a mensal e a anual são duas publicações importadas, não duas
> escalas ([[ADR-389]]). Ver §"Emenda — ir_brackets vira duas tabelas
> importadas (2026-08-15)".
>
> **Correção (2026-08-24):** a contração **não aconteceu** — a coluna segue
> viva e nullable. Ver §"Correção — a contração de `ir_brackets` está deferida
> (2026-08-24)" antes de agir sobre o campo.

# ADR-135 — Versionamento temporal de séries fiscais e câmbio

**Status:** Decidido (Sprint A7) • **Data:** 2026-04-26 • **Relaciona**
[ADR-090](#adr-090--decimal-para-valores-monetários),
[ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy),
[ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend).

**Contexto:** `config/parametros_fiscais.json` (tabela IRPF, limite PGBL,
teto INSS, alíquota lucro presumido) e `config/taxas.json` (câmbio
USD/BRL, EUR/BRL, indexadores) são lidos pelo pipeline em
`pipeline/domain/services/previdencia_analyzer.py`,
`cenarios_conjuge_analyzer.py`, `patrimonio_types.py`. Hoje:

1. Arquivos vivem em disco, sem DB, sem API, sem UI.
2. **Não têm vigência temporal.** Atualizar IR para 2026 sobrescreve
   2025. Re-renderizar relatório de 2025 hoje produz números diferentes
   dos originais.
3. São **globais a todos workspaces** — não pertencem a "config de
   cliente"; são tabela de mercado.
4. Migrar "para um workspace" (instinto inicial do produto) cria N
   cópias divergentes na primeira mudança fiscal — anti-padrão.

Reproducibilidade é requisito não-negociável para fintech: o relatório
de fev/2025 gerado em 2027 deve produzir os mesmos números do gerado em
mar/2025. Sem vigência por data, isso é falha silenciosa.

Alternativas:

- **(a) JSON na raiz com versão por arquivo (`fiscal_2025.json`).**
  Resolve vigência mas continua read-from-disk; multiplica arquivos.
- **(b) Tabela única `fiscal_parameters(year, ...)` sem
  `effective_from`.** Simples, mas não captura mudanças intra-ano (ex.:
  reforma tributária mid-year).
- **(c) Tabela `fiscal_parameters` com `(year, effective_from,
  effective_to)` + `market_rates(pair, observed_at)` com chave única
  por par+data.** Suporta vigência fina e séries históricas de câmbio.

**Decisão:** Adotar (c).

Schema:

```sql
fiscal_parameters (
  id UUID PK,
  year INT NOT NULL,
  ir_brackets JSONB NOT NULL,        -- tabela IRPF progressiva
  pgbl_limit_brl_cents BIGINT NOT NULL,
  inss_ceiling_brl_cents BIGINT NOT NULL,
  lucro_presumido_aliquota DECIMAL(5,4) NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NULL,             -- null = vigente
  source TEXT NOT NULL,               -- "Receita Federal Lei 14.973/2024"
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

market_rates (
  id UUID PK,
  pair TEXT NOT NULL,                 -- "USD/BRL", "EUR/BRL"
  rate DECIMAL(20,10) NOT NULL,
  observed_at DATE NOT NULL,
  source TEXT NOT NULL,               -- "BCB PTAX"
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (pair, observed_at)
);
```

Regra de seleção de período (escrita aqui para não virar folclore):

- `get_fiscal_for_period(period)`: retorna a row com
  `effective_from <= period.start AND (effective_to IS NULL OR
  effective_to >= period.end)`. Se múltiplas rows cobrem o período (ex.:
  reforma mid-year), pipeline aborta com erro tipado
  `FiscalParameterAmbiguous` — relatório precisa ser explícito sobre qual
  vigência usa.
- `get_market_rate(pair, observed_at)`: retorna a row com
  `pair = ? AND observed_at <= ? ORDER BY observed_at DESC LIMIT 1`.
  Câmbio é "última cotação conhecida na data ou antes".

Cache Redis com invalidação por evento (`fiscal_parameter.published`,
`market_rate.published`). Sem `@lru_cache`.

Money continua [ADR-090](#adr-090--decimal-para-valores-monetários):
`*_brl_cents` em `BIGINT`, `rate` em `DECIMAL`, wire em string.

**Consequências:**
- ✅ Reproducibilidade histórica: relatório de qualquer período
  re-renderiza com parâmetros vigentes naquele período.
- ✅ Tabela é **global** — não duplica por workspace.
- ✅ Auditoria: cada row tem `source` + timestamp; admin sabe quem
  publicou.
- ⚠️ Atualização de IR/PGBL/INSS/câmbio é operação de produto
  (admin/ops UI em F7F-Local) — não git commit. Custo aceito; impede
  drift.
- ⚠️ Cache invalidation é por evento. Bug de invalidação produz drift
  de até `tempo entre published e refresh`. Mitigação: mensagem de
  evento dispara refresh ativo, não passivo.
- ❌ Reforma tributária mid-year exige duas rows de
  `fiscal_parameters` no mesmo ano + lógica do pipeline em decidir qual
  usar. Resolvido via `effective_from/to` exclusivo.

## Emenda — lado da PTAX em pares */BRL (2026-07-07)

Co-design `data-engineer` + `financial-planner` (A33.l2, [[ADR-238]] §D1):

- **Invariante:** `market_rates.rate` para pares `*/BRL` é PTAX de
  **compra** (boletim de fechamento) — mesma base que a RFB usa para
  bens/direitos em ME e para o GCAP. Consumidores: `WisePtaxConverter`
  (snapshot 31/12 dos informes financeiro PF).
- **Lado venda exige schema evolution futura** (ex.: coluna `side` ou
  source-discriminator) — **não** reinterprete rows existentes; `source`
  é reforço de auditoria apenas, não é contrato parseável.
- **Guard anti-bootstrap:** o seed A7.2b (`y3z4a5b6c7d8`) replicou a
  cotação de 2026 em `observed_at=2024-01-01`; `get_latest_on_or_before`
  cairia nessa row silenciosamente para lookups de 31/12. Consumidores
  de snapshot anual só aceitam cotação observada em **dezembro do
  ano-base** (senão degradam para `None` + warning). Cotações reais de
  31/12 (2023-2025, USD/EUR/GBP) seedadas em `a33l2ptax3112` com fonte
  BCB Olinda (boletim "Fechamento PTAX", cotação de compra).

## Emenda — `ir_brackets` vira duas tabelas importadas (2026-08-15)

Esta ADR pôs os parâmetros fiscais no DB versionados por data, mas tratou a
tabela progressiva do IRPF como **um** objeto. Medido na [[A40.l56]]: a RFB
publica **duas** — a progressiva mensal (IRRF na fonte) e a do Anexo IV da
IN 1.500/2014 (ajuste anual da DAA) —, com bases legais e atos de publicação
distintos, e a anual **não é ×12 da mensal** (mistura ponderada por mês em ano
de transição; divergência de arredondamento mesmo em ano limpo).

Tratá-las como uma só produziu uma row com faixas anuais e parcelas mensais,
cujo degrau de R$ 11,04 bloqueou o D5 da [[ADR-375]] por três meses.

`ir_brackets` é substituído por `ir_brackets_anual` + `ir_brackets_mensal`,
cada um verbatim da publicação e com proveniência própria; o nome antigo deixa
de resolver. Contrato, invariantes e política de cache em [[ADR-389]].

## Correção — a contração de `ir_brackets` está deferida (2026-08-24)

Auditoria de vault r10 (F17 · [[ADR-302]]). A emenda de 2026-08-15 anuncia em
tempo presente que `ir_brackets` "deixa de existir" e que "o nome antigo deixa
de resolver". Isso descreve o **estado-alvo**, não o presente.

Fonte de verdade — `backend/app/models/fiscal_parameter.py:42-45`:

```python
# Legado do seed A7.2b — escalas misturadas (tetos anuais, parcelas mensais).
# Mantido nullable durante a janela expand/contract; leitores novos usam os
# dois campos acima. Contract em lane própria.
ir_brackets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
```

A [[ADR-389]], dona do contrato, ainda é `Proposto`, e a lane do contract
([[A40.l37]]) está aberta. O campo tem leitores hoje:

```
$ rg -n "ir_brackets\b" --include="*.py" . | grep -v alembic | grep -v _anual | grep -v _mensal
backend/app/models/fiscal_parameter.py:45
backend/tests/test_fiscal_market_repos.py:48
pipeline/domain/services/irpf_faixa_marginal.py:3
```

**Consequência da leitura errada nos dois sentidos:** quem confia na emenda
não trata row legada com `ir_brackets` populado, ou escreve migration de drop
antes do contract; quem percebe a divergência tende a descartar a ADR inteira.
O gatilho para reescrever esta seção é a [[ADR-389]] virar `Decidido` com a
[[A40.l37]] entregue.
