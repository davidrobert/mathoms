---
id: ADR-274
type: adr
title: "Contrato de ano no consolidador E1.5c→E5: chave de resumo em ano-base 31/12, não exercício"
status: Decidido
phase: A21.patrimonio-ano-base
date: "2026-05-30"
relates_to:
  - "[[ADR-271]]"
  - "[[ADR-215]]"
  - "[[ADR-097]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 274"
  - "Patrimonio ano-base vs exercicio"
tags:
  - area/pipeline
  - area/methodology
  - status/proposto
  - type/adr
---

# ADR-274 — Contrato de ano no consolidador E1.5c→E5: resumo em ano-base 31/12, não exercício

**Status:** Decidido (Sprint A21) • **Data:** 2026-05-30 • **Relaciona** [[ADR-271]] (year-stamping por-item — precedente direto), [[ADR-215]] (classification de imóveis), [[ADR-097]] (warnings tipados)

## Contexto

Semântica IRPF tem dois anos distintos:

- **Exercício** — ano da declaração (ex.: 2025).
- **Ano-calendário / ano-base** — ano da foto patrimonial em 31/12 (ex.: 2024).

A posição patrimonial declarada é sempre o snapshot de **31/12 do ano-base**. O ano canônico do patrimônio é, portanto, o ano-base (2024), não o exercício (2025).

[[ADR-271]] corrigiu o **year-stamping por-item** em `consolidate_from_itens`: cada item passou a carimbar `valores_31_12` com seu próprio `item.ano` (ano-base), para que IRPFs de anos diferentes produzam série temporal em vez de colapsar num falso conflito de mesmo-ano. **Mas o resumo não foi alinhado.** Permaneceram em exercício:

- `scripts/e15_consolidate.py::consolidate_from_itens` linhas 446-447: `ano_ref = resumo.get("ano_referencia")` (exercício) → chave de `patrimonio_por_ano`.
- Linha 494: `entry["ano_referencia"] = ano_ref` (exercício) por imóvel.

Resultado: itens chaveados em `"2024"`, `patrimonio_por_ano` chaveado em `"2025"`.

No lado de leitura (E5), `pipeline/domain/services/patrimonio_resolvers.py`:

- `_resolve_ano_ref` deriva `ano_ref` das chaves de `patrimonio_por_ano` → `"2025"`.
- `_resolve_item_valor(item, "2025")` busca `valores_31_12.get("2025")` → **miss** (item está em `"2024"`) → fallback `item.get("valor", 0)` → **0.0**.
- `_split_dividas` (linha 441) sofre o mesmo miss via `saldo_31_12.get("2025")` → dívidas por-membro também zeram.

**Sintoma de produção** (relatório `d0da8f4a…`, workspace `1b9f2cf5`): 6 imóveis + 4 veículos resolvem para R$ 0,00; "Composição Patrimonial" e seção "Real Estate" erradas. Investimentos aparecem porque vêm de outro caminho (`has_current_positions` via E2-llm current positions, que não passa por `_resolve_item_valor`).

## Decisão

O **ano-base 31/12 é a chave canônica** do resumo consolidado, alinhado a `valores_31_12` dos itens. Duas camadas:

### Layer 1 — self-heal no resolver (corrige artefatos já persistidos)

`pipeline_artifacts` guarda conteúdo Fernet-encrypted ([[ADR-231]]); **não há backfill destrutivo**. O resolver endurece a leitura:

- Novo helper `_max_value_year(baseline)`: maior ano numérico (regex `(19|20)\d{2}`, exclui sentinel `999999` e lixo) entre as chaves de `valores_31_12`/`saldo_31_12` de **todos** os itens consolidados. Aceita formato `"YYYY"` e legado `"31_12_YYYY"`. `None` se nenhum ano válido.
- `_resolve_ano_ref` passa a retornar dataclass explícita `AnoResolution(value_year, summary_year, total_bens, total_dividas)` — **desacopla** o ano de resolução por-item (`value_year` = máximo global dos itens) do ano-chave do resumo (`summary_year` = chave de `patrimonio_por_ano`). `total_bens`/`total_dividas` continuam lidos do resumo pela chave própria.
- Quando `value_year != summary_year`, emite **warning tipado** `AnoReferenciaDivergenceWarning` ([[ADR-097]]) via `logging.getLogger("mathoms.pipeline.patrimonio")`. O warning é o sinal de que a origem (Layer 2) regrediu — em artefato pós-Layer-2 ele **não** dispara.
- **Não** se adiciona fallback de "máximo por-item" em `_resolve_item_valor` — usar o máximo *por-item* ressuscitaria ativo vendido (veto explícito do financial-planner). O `value_year` é **global** do baseline.

### Layer 2 — corrige a consolidação na origem (artefatos novos)

`consolidate_from_itens` chaveia `patrimonio_por_ano` e `entry["ano_referencia"]` por `max(item.ano numérico ≠ 999999)` presente nos itens — não por `resumo.ano_referencia`. `summary_year == value_year` daqui pra frente; o warning de divergência deixa de disparar.

## Contrato e schema

`config/schemas/baseline_patrimonial.schema.json` define `patrimonio_por_ano` como `additionalProperties` com **chave-ano livre** (sem `pattern`/`enum`). Mudar a semântica da chave de exercício → ano-base **não viola o schema** — qualquer string-ano valida. **Sem bump de versão.** Esta ADR é a fonte de verdade do contrato semântico: a chave de `patrimonio_por_ano` e o campo `entry.ano_referencia` são **ano-base 31/12**, alinhados a `valores_31_12`.

Consumidor downstream `pipeline/domain/services/property_identity_enricher.py:36` (`first_seen_year = int(entry.get("ano_referencia") or 0)`): passa de 2025 → 2024. É **melhoria** (ano-base é o first-seen correto), não regressão.

## Consequências

- **Positivo:** imóveis/veículos/dívidas voltam a resolver com valor correto sem reprocessar artefatos antigos; `first_seen_year` correto; contrato de ano documentado.
- **Negativo:** `_resolve_ano_ref` ganha assinatura nova (`AnoResolution`) — toca o call-site em `build_members_from_consolidated`. Custo trivial, ganho de clareza (nome explícito vs. `ano_ref` sobrecarregado).
- **Risco — multi-ano legítimo** (IRPF 2023 + 2024 no mesmo `itens[]`): `value_year` = `max` = 2024 (foto mais recente); `_resolve_item_valor` seleciona só o valor 2024 de cada série, sem dobrar 2023 + 2024. Travado por golden multi-ano.

## Alternativas consideradas

1. **Só backfill destrutivo dos artefatos** — rejeitado: viola não-destruição de `pipeline_artifacts` encrypted; re-run E1.5c fica opcional por workspace, não obrigatório.
2. **Fallback por-item em `_resolve_item_valor`** — rejeitado: ressuscita ativo vendido (item presente só em ano antigo voltaria a somar).
3. **Sobrecarregar `ano_ref` (às vezes value-year, às vezes summary-year)** — rejeitado pelo senior-cto: acoplamento implícito é exatamente o que gerou o bug; assinatura explícita `AnoResolution`.

## Critério de aceite

- Teste-unit do off-by-one (`patrimonio_por_ano` keyed 2025 ≠ itens keyed 2024 → valor ≠ 0 + warning tipado dispara) + `_max_value_year` (sentinel 999999, lista vazia, legado `31_12_YYYY`) + assert de que o warning **não** dispara em artefato alinhado pós-Layer-2.
- Golden E5 re-baselinado (regressão do zero); golden multi-ano (2023 + 2024) travando `value_year=max` e total não-dobrado. E4 não tocado.
- Script de auditoria read-only de blast radius (loga só `workspace_id` + contagem, nunca valores).
- Warning tipado [[ADR-097]] no path divergente.
