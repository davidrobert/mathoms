# Diagnóstico: Despesas "Não Identificado" — 82,3% do Total

**Data:** 2026-04-07
**Escopo:** 409 transações classificadas como `nao_identificado` em `despesas-4_unified.json`, totalizando R$1.801.165,13 de R$2.187.748,81 em despesas (82,3%).

---

## Síntese

O problema tem **3 camadas** de causas raiz com origens distintas no pipeline:

| Camada | Causa | Impacto | Onde corrigir |
|--------|-------|---------|---------------|
| **E4 — Bug de código** | Comparação de acento no `tipo` | R$1.426.215 (79,2%) | `e4_categorize.py` (**já corrigido**) |
| **E4 — Keywords faltando** | Padrões de transferência interna ausentes | R$322.386 (17,9%) | `categorization.json` |
| **E2 — Qualidade LLM** | Descrições concatenadas do Bradesco | Afeta precisão de matching | Prompt E2 / pós-processamento |

Após o E-reset com as correções já aplicadas, a taxa de `nao_identificado` cairá de **82,3% para ~1,1%** (R$19.379 de ~R$761.500 em despesas reais).

---

## Causa #1 — Bug de Acento (79,2% — R$1.426.215,25)

**258 transações de crédito caíram no branch de despesas** por causa do mismatch `"crédito" ≠ "credito"` no `e4_categorize.py`. Após a correção (já aplicada), essas transações migrarão para o arquivo `receitas-4_unified.json` no próximo E-reset.

**Status:** CORRIGIDO — `normalize_text(tipo).lower()` aplicado no `e4_categorize.py` v5.3.

Essas 258 transações contêm receitas PJ (ARVO, BRANDLOVERS, CNRY, BARTE), salários CLT (Einstein/Mariana), aluguéis (GRPQA), rendimentos, e resgates que estavam inflando artificialmente as despesas.

---

## Causa #2 — Keywords de Transferência Interna Faltando (17,9% — R$322.385,74)

Três padrões de movimentação entre contas próprias da família não estão na lista `internal_transfer_patterns`:

### 2a. `bx Aut Cta Cor*` — Bradesco baixa automática (R$104.394,04 — 27 txs)

"bx Aut Cta Cor" = "baixa automática conta corrente". É o débito automático que o Bradesco faz quando transfere dinheiro da conta corrente para poupança, investimento, ou pagamento de fatura. São movimentações internas, não despesas reais.

**Correção:** Adicionar `"bx Aut Cta Cor"` a `internal_transfer_patterns`.

### 2b. Itaú "Reserva" — poupança automática (R$206.491,70 — 1 tx)

A descrição `"Reserva - Seu dinheiro guardado rende todo dia! Valor guardado: R$ 206.491,70"` é o produto de reserva automática do Itaú (similar ao "cofrinhos" do Nubank). É uma transferência da conta corrente para a reserva — não é uma despesa.

**Correção:** Adicionar `"Reserva - Seu dinheiro guardado rende"` a `internal_transfer_patterns`.

### 2c. `PAGAMENTO CARTAO CREDITO` — C6 Bank (R$11.500,00 — 3 txs)

Pagamento da fatura do cartão de crédito via extrato C6 Bank. É transferência interna (conta → cartão). Já existe o padrão `"Pagamento de fatura"` e `"PGTO CARTAO"`, mas `"PAGAMENTO CARTAO CREDITO"` (sem "de fatura") não é capturado.

**Correção:** Adicionar `"PAGAMENTO CARTAO CREDITO"` a `internal_transfer_patterns`.

---

## Causa #3 — Qualidade do E2 LLM para Bradesco (impacto indireto)

O LLM do estágio E2 está **concatenando múltiplas transações em uma única descrição** ao parsear os PDFs do Bradesco. Exemplos:

```
"tr Sal p/poup Sociedade Beneficente Israelita Rendimentos Poup Facil-depos a Partir 4/5/12 bx Aut Cta Cor* -"
```

Isso na verdade são 3 transações separadas:
1. `tr Sal p/poup Sociedade Beneficente Israelita` (salário → poupança)
2. `Rendimentos Poup Facil-depos a Partir 4/5/12` (rendimento poupança)
3. `bx Aut Cta Cor* -` (baixa automática conta corrente)

O E2 LLM falha em separar linhas do extrato Bradesco porque o PDF tem layout complexo com múltiplas colunas e linhas de continuação.

**Impacto:** As descrições compostas dificultam o keyword matching — uma descrição pode conter keywords de salário, rendimento E transferência simultaneamente. A primeira keyword encontrada "vence". Em muitos casos o valor associado pertence a apenas uma das transações embutidas, mas é impossível saber qual sem os dados originais do PDF.

**Correção:** Melhorar o prompt E2 para Bradesco ou adicionar pós-processamento que detecte e separe descrições compostas. Este é um fix de maior complexidade e requer re-execução do E2 (estágio LLM).

---

## Causa #4 — Transações Residuais Genuínas (0,7% — R$12.930,44 — 26 txs)

Após aplicar todas as correções acima, restam 26 transações genuinamente sem keyword. Classificação sugerida:

| Descrição | Txs | Valor | Categoria sugerida |
|-----------|-----|-------|--------------------|
| TRANSFERENCIA INTERNACIONAL (C6) | 1 | R$3.840 | transferência interna |
| PIX ENVIADA - TRANSFERENCIA PESSOAL | 1 | R$2.000 | transferência interna |
| LEARNTOEIV DESENVOLVIMENTO HUMANO | 2 | R$2.250 | receita_pj |
| SALDO DO DIA (Itaú) | 2 | R$1.827 | transferência interna |
| RESORT FLORIDA / DISNEY RESORT / BOUTIQUE MIAMI | 3 | R$1.204 | lazer_viagens |
| TARGET LOJA | 2 | R$281 | reserva_desejos |
| GOOGLE FI COBRANCA | 5 | R$417 | assinaturas |
| AMAZON COMPRA | 2 | R$114 | reserva_desejos |
| PIX ENVIADA - PAGUE AQUI ELETROTEC | 2 | R$300 | melhoria_reforma |
| RESTAURANTE ORLANDO | 1 | R$125 | alimentacao |
| PIX TRANSF EDER | 1 | R$90 | transferência interna |
| BLOQUEIO PIX | 1 | R$333 | financeiro |
| Rem: Samuel Dias da Costa (Bradesco) | 2 | R$40 | suporte_familiar |

---

## Causa #5 — Faturas com Merchants Sem Keyword (0,4% — R$6.448,80 — 58 txs)

55 transações de fatura C6 Bank Carbon + 2 Santander Unique + 1 Itaú Pão de Açúcar com descrições de pequenos merchants não mapeados (4MS, GARCIARODASE, J S THENORIO, BRUNOMARTINS, etc.). Valor médio por transação: R$111.

**Correção:** Adicionar os merchants mais recorrentes às categorias correspondentes em `expense_keywords`, ou aceitar que um pequeno percentual ficará como `nao_identificado` (meta <10%).

---

## Resumo de Correções Necessárias

### Já aplicadas (aguardando E-reset):
- [x] `e4_categorize.py` — normalização de acento em `tipo`, `tipo_conta`, `banco`

### Correções em `categorization.json` → `internal_transfer_patterns`:
- [ ] Adicionar `"bx Aut Cta Cor"` (R$104.394)
- [ ] Adicionar `"Reserva - Seu dinheiro guardado rende"` (R$206.491)
- [ ] Adicionar `"PAGAMENTO CARTAO CREDITO"` (R$11.500)
- [ ] Adicionar `"SALDO DO DIA"` (R$1.827)
- [ ] Adicionar `"TRANSFERENCIA INTERNACIONAL"` (R$3.840)
- [ ] Adicionar `"TRANSFERENCIA PESSOAL"` (R$2.000)

### Correções em `categorization.json` → `expense_keywords`:
- [ ] Adicionar `"GOOGLE FI"` a `assinaturas` (R$417)
- [ ] Adicionar `"AMAZON COMPRA"` a `reserva_desejos` (R$114)
- [ ] Adicionar `"RESORT FLORIDA"`, `"DISNEY RESORT"`, `"BOUTIQUE MIAMI"`, `"RESTAURANTE ORLANDO"` a `lazer_viagens` (R$1.329)

### Correções em `categorization.json` → `income_keywords`:
- [ ] Adicionar `"LEARNTOEIV"` a `receita_pj` (R$2.250)

### Correção de maior complexidade (E2 LLM):
- [ ] Melhorar parsing de extrato Bradesco para não concatenar descrições

---

## Projeção Após Todas as Correções

| Métrica | Antes | Depois |
|---------|-------|--------|
| Despesas `nao_identificado` | 409 txs (82,3%) | ~58 txs (~7,6%) |
| Valor `nao_identificado` | R$1.801.165 | ~R$6.449 |
| Total despesas real | R$2.187.749 | ~R$761.534 (após remover créditos e transferências) |
| Taxa `nao_identificado` real | — | **~0,8%** (meta <10% atingida) |
