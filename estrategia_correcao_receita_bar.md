# Estratégia de Correção — Gráfico "Receita Bar" e Integridade de Receitas

**Data:** 2026-04-04
**Versão:** 1.0
**Escopo:** Correções duráveis no pipeline E2→E3→E4→E5→E6 para que o gráfico `receita_bar` (e dados de receita em geral) sejam determinísticos, verificáveis e corretos a cada reprocessamento do zero.

---

## DIAGNÓSTICO — 5 PROBLEMAS ENCONTRADOS

### P1 — E2: Extração de faturas QuintoAndar falha para 2026

**Evidência:** Os arquivos `quintoandar_faturaaluguelcalixto_202602-2_extract.json` e `quintoandar_faturaaluguelmajorfreire_202602-2_extract.json` existem mas contêm `renda_bruta: 0, renda_liquida: 0`. Os arquivos reconciliados correspondentes estão vazios (`{}`).

**Impacto:** Zero receita de aluguel em 2026. O YTD perde ~R$ 24.540 (estimativa: 3 meses × R$ 8.180/mês).

**Causa provável:** O passo E2 item 5 ("Para cada fatura de aluguel QuintoAndar") extraiu os campos mas não conseguiu ler os valores do PDF. Possíveis razões: formato do PDF mudou, OCR falhou, ou o LLM não recebeu instrução adequada para interpretar o layout da fatura. O arquivo reconciliado (E3) correspondente está vazio (`{}`).



### P2 — E3: Dois conjuntos de reconciled com nomes diferentes

**Evidência:** Existem 44 arquivos em `E3_reconciled/`. Os 15 com dados reais usam formato `banco_tipo_MOEDA_DDMM-DDMM-3_reconciled.json` (ex: `bradesco_extratoconta_BRL_0101-0329`). Os 29 vazios usam formato `banco_tipo_MOEDA_YYYYMM_YYYYMM-3_reconciled.json` (ex: `bradesco_conta_BRL_202501_202603`).

**Impacto:** Se o E4 ler os arquivos do formato novo (vazios), perde todos os dados. Se ler os do formato antigo, tem dados parciais mas inconsistentes.

**Causa provável:** Duas execuções do pipeline geraram arquivos com convenções de nomenclatura diferentes. A execução mais recente não produziu dados nos reconciled.

### P3 — E4: Dados de aluguel 2025 são sintéticos

**Evidência:** Todos os 12 meses de 2025 têm exatamente R$ 8.180,17 de aluguel, compostos por 4 transações idênticas repetidas (R$ 5.073,38 + R$ 1.413,97 + R$ 1.203,15 + R$ 489,67) × 12. Aluguéis reais variam com reajustes, vacância, taxas de administração e IRRF.

**Impacto:** Médias e totais de receita são inflados ou deflados vs. realidade. Não se sabe se esses valores vieram de extrato bancário (Bradesco GRPQA) ou foram projetados.

**Causa provável:** A execução do E4 provavelmente usou dados das faturas QuintoAndar (E2 item 5) que são por propriedade, e os replicou para meses sem dados no extrato bancário — ou usou uma estimativa flat. As faturas QuintoAndar só cobrem alguns meses; os extratos bancários (Bradesco CC com GRPQA) cobririam todos os meses, mas talvez não tenham sido a fonte primária.

### P4 — E4: Transferência interna de R$ 40.000 classificada como receita

**Evidência:** Em mar/2026, no BTG Pactual, aparece: "RECEBIMENTO TRANSFERENCIA - Mariana Teixeira" → R$ 40.000 classificado como `receita_outra`.

**Impacto:** Infla receita de março em R$ 40.000. YTD 2026 mostra R$ 215.818 quando deveria ser ~R$ 175.818.

**Causa:** O E4 deveria aplicar as regras de transferência interna do `definitions.md` (seção "MAPA DE TRANSFERÊNCIAS INTERNAS"). BTG é conta de Mariana → Mariana transferindo para si mesma entre contas, ou David→Mariana. Em ambos os casos, é `transferencia_interna` e deveria ser excluída do fluxo de caixa. A regra 1 do mapa diz: "TED/PIX entre contas [do casal] → transferencia_interna". O nome "Mariana Teixeira" deveria ter sido detectado como titular.

### P5 — E5: `por_fonte` é estimativa manual, desconectada do E4

**Evidência:** O E5 JSON contém:
```json
"por_fonte": {
  "PJ David (Arvo+BrandLovers+Arbitralis)": 59959.0,
  "CLT Mariana (Einstein)": 8000.0,
  "Aluguéis David": 3422.0,
  "Aluguéis Mariana": 5149.0,
  "Rendimentos financeiros": 1200.0
}
```
Esses valores não correspondem a nenhum cálculo sobre o E4. O schema do manual (linha 2275) define a chave como `receitas_por_fonte` com keys `pj`, `clt`, `alugueis`, `rendimentos_financeiros`, `outros` — diferente do que foi gerado.

**Impacto:** O gráfico `receita_bar` mostra números que não têm lastro nos extratos. Impossível validar.

---

## ESTRATÉGIA DE CORREÇÃO — 5 AÇÕES

Cada ação é localizada numa etapa do pipeline e formulada como **regra durável** que funciona em qualquer reprocessamento futuro.

### AÇÃO 1 — E2: Corrigir extração de faturas QuintoAndar

**Onde:** Stage E2, item 5 — "Para cada fatura de aluguel (QuintoAndar)" — E2 output → E2_extract/

**Regra a adicionar no `manual_operacao.md`, após a linha 861:**

> **Validação obrigatória para faturas QuintoAndar:**
> Após extração, verificar que `renda_bruta > 0`. Se `renda_bruta == 0` e o PDF não é uma fatura de mês sem locação (vacância), registrar em `logs/qa_log.md` como "EXTRAÇÃO FALHOU — reler PDF" e marcar o extract como `"status": "extraction_failed"`. O E3 deve ignorar extracts com `status: extraction_failed` e não gerar transações sintéticas para compensar.

**Ação imediata:** Re-extrair as faturas QuintoAndar de 2026 (Calixto e Major Freire). Se os PDFs originais existirem em `data/financial_statements/` ou `data/income_tax_br/`, reprocessar.

**Ação complementar — fonte primária de aluguéis via extrato bancário:**
Os aluguéis QuintoAndar também aparecem como "RECEB PAGFOR GRPQA" nos extratos do Bradesco CC (Mariana) e Itaú Personnalité (David). Esses são mais confiáveis que as faturas QuintoAndar (que podem ter formato variável). O E4 já tem regra para isso no `definitions.md` linha 254: `GRPQA` → `receita_aluguel`. O problema é que o extrato reconciliado do Bradesco para 2026 está vazio (P2). Corrigir P2 resolve P1 para aluguéis.

### AÇÃO 2 — E3: Resolver duplicidade de arquivos reconciliados

**Onde:** Stage E3 — Reconciliação por conta (input E2_extract/ → output E3_reconciled/)

**Diagnóstico necessário antes de corrigir:**
Identificar qual dos dois conjuntos de reconciled tem os dados corretos:
- Formato antigo (com dados): `bradesco_extratoconta_BRL_0101-0329-3_reconciled.json` — 22 KB, tem transações
- Formato novo (vazio): `bradesco_conta_BRL_202501_202603-3_reconciled.json` — 2 bytes, vazio

**Regra a adicionar no `manual_operacao.md`, seção E3:**

> **Convenção de nomenclatura E3 (OBRIGATÓRIA):**
> Arquivos reconciliados DEVEM seguir o padrão:
> `[banco]_[tipo]_[MOEDA]_[YYYYMM]_[YYYYMM]-3_reconciled.json`
> Exemplo: `bradesco_extratoconta_BRL_202501_202603-3_reconciled.json`
>
> **Validação pós-reconciliação:**
> Todo arquivo `-3_reconciled.json` DEVE ter pelo menos uma transação. Se o arquivo resultante tem 0 transações, isso indica falha no merge dos extracts — registrar em `logs/qa_log.md` e não sobrescrever o arquivo anterior.

**Ação imediata:** Limpar os 29 arquivos reconciliados vazios. Renomear os 15 com dados para o formato padrão. Ou melhor: re-rodar E3 do zero garantindo que leia os extracts corretos.

### AÇÃO 3 — E4: Fortalecer detecção de transferências internas

**Onde:** Stage E4, item 1 — categorização de transações (input E3_reconciled/ → output E4_unified/)

**Problema específico:** "RECEBIMENTO TRANSFERENCIA - Mariana Teixeira" no BTG não foi detectado como `transferencia_interna`.

**Regra a adicionar no `definitions.md`, seção "Regras de detecção" de transferências internas:**

> **Regra 6 — Detecção por nome de titular:**
> Qualquer transação de crédito cuja descrição contenha o nome completo ou parcial de um titular do casal (David Robert Camargo, David Robert, Mariana Teixeira Ferreira Campos, Mariana Teixeira) E esteja em uma conta de outro titular → `transferencia_interna`.
> Exceções: se a descrição contém "ARVO" ou outro nome PJ → `receita_pj` (tem precedência).

**Regra complementar — proteção contra "receita_outra" inflada:**

> **Validação E3 para `receita_outra`:**
> Qualquer transação individual classificada como `receita_outra` com valor > R$ 5.000 deve ser re-verificada manualmente. Gerar alerta em `logs/qa_log.md`: "RECEITA_OUTRA > R$ 5k — verificar se é transferência interna ou receita legítima."

### AÇÃO 4 — E5: `receitas_por_fonte` calculado deterministicamente do E4

**Onde:** Stage E5, item 1 — Fluxo de caixa (input E4_unified/ → output E5_analysis/)

**Problema:** O campo `por_fonte` atual é uma estimativa manual. O schema do manual define `receitas_por_fonte` com 5 chaves padronizadas.

**Regra a adicionar no `manual_operacao.md`, seção E5 item 1:**

> **Item 1e — Receitas por fonte (OBRIGATÓRIO — alimenta gráfico `receita_bar`):**
>
> **Input:** `processed/E4_unified/receitas-4_unified.json`
>
> **Lógica:**
> 1. Ler `totais_por_categoria` do E4:
>    - `receita_pj` → chave `pj`
>    - `receita_clt` → chave `clt`
>    - `receita_aluguel` → chave `alugueis`
>    - `receita_investimento` → chave `rendimentos_financeiros`
>    - tudo restante (exceto `transferencia_interna`, `receita_resgate`) → chave `outros`
> 2. Determinar período: contar meses únicos com pelo menos 1 transação de receita
> 3. Calcular: `media_mensal = total / n_meses`
>
> **Output — duas chaves obrigatórias no E5 JSON:**
>
> ```json
> "receitas_por_fonte": {
>   "pj": {"total": 477463.00, "media_mensal": 31831.00, "n_meses": 15},
>   "clt": {"total": 143145.00, "media_mensal": 9543.00, "n_meses": 15},
>   "alugueis": {"total": 98162.04, "media_mensal": 8180.17, "n_meses": 12},
>   "rendimentos_financeiros": {"total": 3245.82, "media_mensal": 405.73, "n_meses": 8},
>   "outros": {"total": 0.00, "media_mensal": 0.00, "n_meses": 0}
> },
> "receitas_por_fonte_ytd": {
>   "ano": 2026,
>   "meses_cobertos": ["2026-01", "2026-02", "2026-03"],
>   "pj": 141627.00,
>   "clt": 28629.00,
>   "alugueis": 0.00,
>   "rendimentos_financeiros": 1572.90,
>   "outros": 3989.60,
>   "total": 175818.50
> }
> ```
>
> **Regra:** `receitas_por_fonte_ytd.ano` = ano corrente (derivado de `consolidation_date` do E4 ou data de execução). Filtrar transações do E4 com `data >= YYYY-01-01`.
>
> **NUNCA estimar ou hardcodar valores. Sempre derivar dos totais do E4.**

### AÇÃO 5 — E6: Gráfico `receita_bar` usa YTD e tem título explicativo

**Onde:** `scripts/e6_render.py`, função que monta `charts_data["receita_bar"]` e `build_content_s2()`

**Mudança no `e6_render.py`:**

```python
# ANTES (estimativa manual):
"receita_bar": {
    "labels": list(f["por_fonte"].keys()),
    "datasets": [{"data": list(f["por_fonte"].values()), ...}]
}

# DEPOIS (YTD determinístico):
ytd = f.get("receitas_por_fonte_ytd", {})
receita_bar_labels = ["PJ", "CLT", "Aluguéis", "Rendimentos", "Outros"]
receita_bar_data = [
    ytd.get("pj", 0),
    ytd.get("clt", 0),
    ytd.get("alugueis", 0),
    ytd.get("rendimentos_financeiros", 0),
    ytd.get("outros", 0),
]
"receita_bar": {
    "labels": receita_bar_labels,
    "datasets": [{"data": receita_bar_data, "backgroundColor": PALETTE[:5]}]
}
```

**Mudança no título do card (em `build_content_s2()`):**

```python
# ANTES:
html += '<div class="card-title">Receita por Fonte (11 meses)</div>'

# DEPOIS:
ano = ytd.get("ano", "")
n = len(ytd.get("meses_cobertos", []))
html += f'<div class="card-title">Receita Acumulada por Fonte — YTD {ano} ({n} meses)</div>'
html += f'<div class="card-subtitle">Soma real de todas as receitas de jan a mar/{ano}, extraída dos extratos bancários.</div>'
```

**Mudança na narrativa E5.N (`charts.receita_bar.context`):**

> Context deve refletir o YTD: "Receitas acumuladas de jan a mar/2026 por fonte. Total YTD: R$ {total}. PJ corresponde a {pct}% do total."

---

## ORDEM DE EXECUÇÃO

Para um reprocessamento do zero, as correções se aplicam nesta ordem:

| Passo | Etapa | O que fazer | Pré-requisito |
|---|---|---|---|
| 1 | Config | Atualizar `definitions.md` com Regra 6 (detecção por nome de titular) | — |
| 2 | Config | Atualizar `manual_operacao.md` com regras das Ações 1-5 | — |
| 3 | E2 | Re-extrair faturas QuintoAndar 2026 com validação `renda_bruta > 0` | PDFs originais |
| 4 | E3 | Limpar reconciled vazios, re-rodar reconciliação | E2 completo |
| 5 | E4 | Re-rodar E4 com regra de transferência interna fortalecida | E3 limpo + definitions.md atualizado |
| 6 | E5 | Gerar `receitas_por_fonte` e `receitas_por_fonte_ytd` do E4 (nunca hardcodar) | E4 limpo |
| 7 | E5.N | Atualizar narrativa de `receita_bar` para refletir YTD | E5 item 1e |
| 8 | E6 | Atualizar `e6_render.py` para usar `receitas_por_fonte_ytd` + título explicativo | E5 completo |
| 9 | Validação | Verificar que soma de `receitas_por_fonte_ytd` == soma E4 filtrado por 2026 | E6 gerado |

---

## CHECKLIST DE VALIDAÇÃO PÓS-CORREÇÃO

- [ ] `receitas-4_unified.json` não contém transações com "Mariana Teixeira" como `receita_outra` (R$ 40k deve ter sido filtrado como `transferencia_interna`)
- [ ] `receitas-4_unified.json` contém transações de `receita_aluguel` em 2026 (GRPQA no Bradesco/Itaú OU faturas QuintoAndar com renda_bruta > 0)
- [ ] `analise_financeira-5_analysis.json` contém `receitas_por_fonte_ytd` com valores derivados do E4
- [ ] `receitas_por_fonte_ytd.total` == soma de transações E4 com data >= 2026-01-01, excluindo `transferencia_interna` e `receita_resgate`
- [ ] Gráfico `receita_bar` no HTML final tem título "Receita Acumulada por Fonte — YTD 2026 (3 meses)"
- [ ] Nenhum arquivo `-3_reconciled.json` está vazio (`{}`)
- [ ] Valores de aluguel em 2025 variam mês a mês (não são flat R$ 8.180,17 × 12)

---

## NOTAS

1. **Sobre os aluguéis 2025 sintéticos (P3):** A correção ideal seria re-extrair os extratos Bradesco e Itaú de 2025 para obter os créditos GRPQA reais. Se os PDFs originais existirem, basta re-rodar E2+E3+E4. Se não, os valores flat podem ficar como estimativa *documentada* — adicionar flag `"estimado": true` nas transações de aluguel que são réplicas.

2. **Sobre propriedades QuintoAndar:** O E4 de 2025 mostra 4 propriedades (Calixto, Major Freire, Alberto Augusto Alves, João Dias). O E2 de 2026 só tem faturas de 2 (Calixto e Major Freire). Pode significar que 2 imóveis foram vendidos/desocupados. Verificar com David.

3. **Sobre o campo `por_fonte` legado no E5:** Após implementar `receitas_por_fonte` e `receitas_por_fonte_ytd`, o campo `por_fonte` antigo pode ser removido ou mantido como deprecated. O `e6_render.py` deve ser atualizado para ler as novas chaves.
