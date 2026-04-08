# Plano de Correção — E2 Extract Faturas

**Data:** 2026-04-05
**Escopo:** 10 achados da revisão de `scripts/e2_extract_faturas.py` + Seção 7.1 do manual
**Arquivos afetados:** `scripts/e2_extract_faturas.py`, `config/manual_operacao.md`
**Risco downstream:** Baixo — E3/E4 já consomem o schema flat do script (não o schema do manual)

---

## FASE 1 — Bugs em produção (prioridade máxima)

### 1.1 — Santander: fallback de vencimento pega data errada

**Achado:** Fatura 202503 tem `data_vencimento: "2026-03-15"` (ano errado). O fallback (L386-390) pega a primeira data DD/MM/YYYY do PDF inteiro, sem validar contra `ref_year`.

**Arquivo:** `e2_extract_faturas.py`, função `parse_santander_unique`

**Mudança:**
```python
# ANTES (L385-390):
if result["data_vencimento"] is None:
    m = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)
    if m:
        venc_parts = m.group(1).split("/")
        if len(venc_parts) == 3:
            result["data_vencimento"] = f"{venc_parts[2]}-{venc_parts[1]}-{venc_parts[0]}"

# DEPOIS:
if result["data_vencimento"] is None and ref_year and ref_month:
    # Fallback: construir vencimento a partir de ref_year/ref_month
    # Santander vence tipicamente dia 15
    candidates = re.findall(r'(\d{2})/(\d{2})/(\d{4})', full_text)
    for dd, mm, yyyy in candidates:
        if int(yyyy) == ref_year and int(mm) == ref_month:
            result["data_vencimento"] = f"{yyyy}-{mm}-{dd}"
            break
    # Se nenhuma data do mês correto, usar ref_year-ref_month-15 como estimativa
    if result["data_vencimento"] is None:
        result["data_vencimento"] = f"{ref_year}-{ref_month:02d}-15"
        log("WARN", f"  Vencimento estimado (sem match exato): {result['data_vencimento']}")
```

**Teste:** Reprocessar `santander_faturaunique_202503-0_original.pdf` e verificar que vencimento é `2025-03-15`.

---

### 1.2 — Santander/Itaú: alerta para faturas completamente vazias

**Achado:** `santander_faturaunique_202501` e `202502` têm todos os campos zero/vazio. Nenhum warning emitido.

**Arquivo:** `e2_extract_faturas.py`, após cada parser retornar (no `main()` ou em helper)

**Mudança:** Adicionar função de validação pós-parse:
```python
def validate_parse_result(result: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Adiciona metadata de qualidade ao resultado."""
    tipo = result.get("tipo", "")

    # Checar se resultado está completamente vazio
    saldo = result.get("saldo_atual") or 0
    txns = len(result.get("transacoes", []))
    itens = len(result.get("itens", []))
    venc = result.get("data_vencimento", "")

    if saldo == 0 and txns == 0 and itens == 0 and not venc:
        result["parse_quality"] = "empty_result"
        log("WARN", f"  Resultado completamente vazio para {filename} — verificar PDF")
    elif saldo > 0 and txns == 0 and itens == 0:
        result["parse_quality"] = "missing_transactions"
        log("WARN", f"  Saldo R$ {saldo:.2f} mas 0 transações para {filename}")
    else:
        result["parse_quality"] = "ok"

    return result
```

Chamar em `main()` logo após `identify_and_parse()`:
```python
result = identify_and_parse(pdf_path)
if result and not result.get("requires_llm_fallback"):
    result = validate_parse_result(result, filename)
```

**Impacto E3:** Nenhum — E3 ignora chaves desconhecidas. O campo `parse_quality` fica como metadata informativa.

---

### 1.3 — Itaú: transações perdidas em faturas com saldo > 0

**Achado:** `itau_faturapaoacucar_202507` (R$ 154,57) e `202602` (R$ 257,54) têm `transacoes: []`.

**Arquivo:** `e2_extract_faturas.py`, função `parse_itau_paoacucar`

**Diagnóstico necessário:** Antes de corrigir o regex, precisamos ver o texto bruto do PDF para entender o formato exato que está falhando.

**Mudança (etapa 1 — diagnóstico):**
```python
# Adicionar debug logging temporário quando transacoes está vazio mas saldo > 0
if not result["transacoes"] and result.get("saldo_atual", 0) > 0:
    log("WARN", f"  0 transações mas saldo={result['saldo_atual']} — dump de linhas do PDF:")
    for i, line in enumerate(full_text.split('\n')):
        if re.search(r'\d{2}/\d{2}', line):
            log("DEBUG", f"    L{i}: {line[:120]}")
```

**Mudança (etapa 2 — após diagnóstico):** Ajustar `tx_simple` regex ou adicionar terceiro pattern para cobrir o formato faltante. A causa mais provável é que as transações têm formato `DD/MM DESCRICAO VALOR` onde DESCRICAO é muito curta e o lazy `(.+?)\s+` captura apenas parte dela, deixando o VALOR como parte da descrição.

**Mudança (etapa 2 — alternativa conservadora):** Se o regex não conseguir cobrir todos os formatos, adicionar fallback: quando `transacoes == []` e `saldo_atual > 0`, marcar `"parse_quality": "missing_transactions"` (já coberto por 1.2) e emitir texto bruto das linhas com data para facilitar debug manual.

---

### 1.4 — Outputs duplicados `itau_*-0_original-2_extract.json`

**Achado:** Existem pares de arquivos como `itau_faturapaoacucar_202505-2_extract.json` e `itau_faturapaoacucar_202505-0_original-2_extract.json` com conteúdo diferente.

**Arquivo:** `e2_extract_faturas.py`, função `main()`, linha 888

**Mudança:**
```python
# ANTES (L887-890):
out_name = re.sub(r'-0_original\.pdf$', '-2_extract.json', filename)
if out_name == filename:
    out_name = filename.replace('.pdf', '-2_extract.json')

# DEPOIS — regex mais robusto que cobre variações:
out_name = re.sub(r'(-0_original)?\.pdf$', '-2_extract.json', filename, flags=re.IGNORECASE)
```

**Ação adicional:** Apagar os arquivos duplicados `*-0_original-2_extract.json` do diretório `processed/E2_extracts/` e reprocessar para gerar os nomes corretos.

---

## FASE 2 — Inconsistências de dados

### 2.1 — Convenção de sinal para `pagamentos`

**Achado:** C6 grava negativo (-98.0), Santander grava positivo (124.69).

**Arquivo:** `e2_extract_faturas.py`

**Convenção escolhida:** Pagamentos SEMPRE negativos (reduzem o saldo da fatura).

**Mudanças:**

Em `parse_santander_unique` (L403-405):
```python
# ANTES:
m = re.search(r'Total de pagamentos\s+([\d.,]+)', full_text)
if m:
    result["pagamentos"] = parse_brl(m.group(1))

# DEPOIS:
m = re.search(r'Total de pagamentos\s+([\d.,]+)', full_text)
if m:
    val = parse_brl(m.group(1))
    result["pagamentos"] = -abs(val) if val else None  # Sempre negativo
```

Em `parse_c6_carbon` — já está correto (L205: `result["pagamentos"] = -parse_brl(...)`).

Em `parse_itau_paoacucar` — verificar: atualmente usa o valor bruto do PDF com regex que pode capturar sinal. Adicionar `result["pagamentos"] = -abs(val)` para garantir.

**Impacto E3:** E3 lê `saldo_anterior` e `saldo_final` (não pagamentos diretamente), portanto sem impacto.

---

### 2.2 — Itaú `tx_simple` descarta créditos/estornos (valor < 0)

**Achado:** Linha 668: `if valor is not None and valor > 0:` exclui qualquer transação negativa.

**Arquivo:** `e2_extract_faturas.py`, função `parse_itau_paoacucar`

**Mudança:**
```python
# ANTES (L668):
if valor is not None and valor > 0:

# DEPOIS:
if valor is not None and valor != 0:
```

**Nota:** O filtro `> 0` provavelmente foi adicionado para evitar capturar lixo de right-column merge (números de encargos). Precisamos validar que a mudança não introduz false positives. Alternativa mais conservadora:
```python
if valor is not None and (valor > 0 or valor < -1.0):
    # Aceita negativos reais (estornos), rejeita zeros e micro-valores de junk
```

---

## FASE 3 — Robustez (edge cases)

### 3.1 — `resolve_date` e `resolve_date_ddmm` crasham com `ref_month=None`

**Arquivo:** `e2_extract_faturas.py`, funções `resolve_date` e `resolve_date_ddmm`

**Mudança:**
```python
def resolve_date(day: int, month_str: str, ref_year: int, ref_month: int) -> str:
    if ref_year is None or ref_month is None:
        # Fallback: sem referência, usar mês do texto + ano corrente
        month_num = int(MESES_BR.get(month_str.lower().strip(), '0'))
        if month_num == 0:
            return f"0000-00-{day:02d}"  # placeholder — será capturado pela validação
        return f"{ref_year or datetime.now().year}-{month_num:02d}-{day:02d}"
    # ... resto igual

def resolve_date_ddmm(dd: int, mm: int, ref_year: int, ref_month: int) -> str:
    if ref_year is None or ref_month is None:
        return f"{ref_year or datetime.now().year}-{mm:02d}-{dd:02d}"
    # ... resto igual
```

---

### 3.2 — Validação de datas impossíveis

**Arquivo:** `e2_extract_faturas.py`

**Mudança:** Adicionar função validadora:
```python
def safe_date(year: int, month: int, day: int) -> str:
    """Retorna data ISO válida ou ajusta dia para último dia do mês."""
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    if day > max_day:
        log("WARN", f"  Data ajustada: {year}-{month:02d}-{day:02d} → dia {max_day}")
        day = max_day
    if day < 1:
        log("WARN", f"  Data inválida: {year}-{month:02d}-{day:02d} → dia 1")
        day = 1
    return f"{year}-{month:02d}-{day:02d}"
```

Usar `safe_date()` no return de `resolve_date` e `resolve_date_ddmm` em vez de f-string direto.

---

### 3.3 — `parse_brl` não reconhece formato contábil `(1.234,56)`

**Arquivo:** `e2_extract_faturas.py`, função `parse_brl`

**Mudança:**
```python
# ANTES (L80-83):
negative = False
if text.startswith("(-)") or text.startswith("-"):
    negative = True
    text = text.lstrip("(-)").strip()

# DEPOIS:
negative = False
if text.startswith("(-)") or text.startswith("-"):
    negative = True
    text = text.lstrip("(-)").strip()
elif text.startswith("(") and text.endswith(")"):
    # Formato contábil: (1.234,56) = negativo
    negative = True
    text = text[1:-1].strip()
```

---

### 3.4 — Arquivos não-renomeados ignorados sem warning

**Arquivo:** `e2_extract_faturas.py`, função `main()`, linhas 851-855

**Mudança:**
```python
# ANTES (L851-855):
for p in sorted(INBOX_DIR.glob("*fatura*.pdf")):
    if "-0_original" not in p.name and p not in files:
        pass  # We only process -0_original versions

# DEPOIS:
non_standard = []
for p in sorted(INBOX_DIR.glob("*fatura*.pdf")):
    if "-0_original" not in p.name:
        non_standard.append(p.name)
if non_standard:
    log("WARN", f"{len(non_standard)} arquivo(s) fatura sem sufixo -0_original (ignorados):")
    for name in non_standard:
        log("WARN", f"  → {name}")
```

---

### 3.5 — QuintoAndar skip-list descarta itens legítimos

**Arquivo:** `e2_extract_faturas.py`, função `parse_quintoandar`

**Mudança:** Inverter a lógica — tentar o match *antes* de aplicar a skip-list:
```python
# ANTES (L746-766):
for line in full_text.split('\n'):
    if any(s in line for s in ['Total de', ...]):   # skip primeiro
        continue
    item_m = item_pattern.match(line.strip())       # match depois
    ...

# DEPOIS:
for line in full_text.split('\n'):
    stripped = line.strip()
    # Tentar match primeiro
    item_m = item_pattern.match(stripped)
    if item_m:
        desc = item_m.group(1).strip()
        valor_str = item_m.group(2).strip()
        valor = parse_brl(valor_str)
        # Só pular se descrição for claramente um header (sem valor monetário real)
        if valor is not None and desc and len(desc) > 3:
            # Rejeitar linhas que são claramente headers/footers
            if desc.lower() in ('total de', 'subtotal', 'você recebe'):
                continue
            result["itens"].append({"descricao": desc, "valor": valor})
```

---

## FASE 4 — Alinhamento do manual (Seção 7.1)

### 4.1 — Atualizar schema de fatura no manual

**Arquivo:** `config/manual_operacao.md`, Seção 7.1

**Mudança:** Substituir o schema de fatura (L2157-2189) pelo schema real gerado pelo script:

```json
{
  "banco": "C6 Bank | Santander | Itaú",
  "tipo": "faturacarbon | faturaunique | faturapaoacucar",
  "cartao": "Carbon | Unique | Pão de Açúcar",
  "titular": "NOME COMPLETO DO TITULAR",
  "moeda": "BRL",
  "data_vencimento": "YYYY-MM-DD",
  "saldo_anterior": 0.00,
  "total_compras_nacionais": 0.00,
  "total_compras_internacionais": 0.00,
  "pagamentos": -0.00,
  "saldo_atual": 0.00,
  "limite_total": 0.00,
  "parse_quality": "ok | empty_result | missing_transactions",
  "transacoes": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "[conforme documento]",
      "valor": 0.00,
      "cartao": "[identificação do cartão/titular]",
      "parcela": "3/12",
      "forex": {
        "moeda_original": "USD | EUR",
        "valor_original": 0.00,
        "cotacao": 0.00
      },
      "tipo_lancamento": "iof"
    }
  ],
  "cartoes": [
    { "cartao": "[nome]", "subtotal": 0.00 }
  ]
}
```

Adicionar nota: *"Schema atualizado em v4.9.1 para refletir output real de `e2_extract_faturas.py`. Campos `forex`, `tipo_lancamento`, `cartoes` e `parse_quality` são opcionais. O campo `pagamentos` é SEMPRE negativo por convenção."*

Adicionar schema separado para QuintoAndar:
```json
{
  "banco": "QuintoAndar",
  "tipo": "faturaaluguel",
  "propriedade": "[nome curto]",
  "moeda": "BRL",
  "periodo_referencia": "YYYY-MM",
  "total_recebido": 0.00,
  "data_recebimento": "YYYY-MM-DD",
  "endereco": "[endereço completo]",
  "parse_quality": "ok | empty_result",
  "itens": [
    { "descricao": "[item]", "valor": 0.00 }
  ]
}
```

---

## ORDEM DE EXECUÇÃO

| Passo | Fase | O que fazer | Tempo est. |
|-------|------|-------------|-----------|
| 1 | 1.1 | Fix fallback vencimento Santander | 10 min |
| 2 | 1.4 | Fix regex de output name (duplicatas) | 5 min |
| 3 | 2.1 | Normalizar sinal de pagamentos | 5 min |
| 4 | 2.2 | Permitir valores negativos no Itaú tx_simple | 5 min |
| 5 | 3.1 | Guard ref_month=None | 5 min |
| 6 | 3.2 | Validação de datas impossíveis (safe_date) | 10 min |
| 7 | 3.3 | parse_brl formato contábil | 5 min |
| 8 | 3.4 | Warning para arquivos não-renomeados | 5 min |
| 9 | 3.5 | QuintoAndar skip-list invertida | 10 min |
| 10 | 1.2 | validate_parse_result (qualidade) | 10 min |
| 11 | 1.3 | Diagnóstico Itaú PDFs com 0 txn (dump texto) | 15 min |
| 12 | 1.3 | Fix regex Itaú baseado no diagnóstico | 15 min |
| 13 | 4.1 | Atualizar Seção 7.1 do manual | 15 min |
| — | — | **Reprocessar todas as faturas** (`--dry-run` primeiro) | 5 min |
| — | — | **Re-executar E3→E4→E5→E6** via `e_reset.py --from E3` | ~30s |
| — | — | **Verificação final:** diff dos JSONs antes/depois | 10 min |

**Tempo total estimado:** ~2h (incluindo diagnóstico Itaú e verificação)

---

## PRÉ-REQUISITOS

1. Antes de mexer no código: `git commit` do estado atual (safety snapshot)
2. Após cada fase: `--dry-run` para validar que outputs mudaram como esperado
3. Após todas as fases: `e_reset.py --from E2-faturas` para reprocessar pipeline completo
4. Verificação final: contar transações totais antes/depois — o número deve subir (não cair)

---

## RISCOS

| Risco | Mitigação |
|-------|-----------|
| Regex novo captura false positives no Itaú | Comparar txn count antes/depois por arquivo |
| Mudança de sinal em pagamentos quebra E3 | E3 não usa `pagamentos` — usa `saldo_anterior`/`saldo_final` |
| Fallback de vencimento com dia fixo 15 | Santander historicamente vence dia 15; log("WARN") emitido |
| QuintoAndar nova lógica captura header como item | Filtro explícito por `desc.lower()` em lista de headers |
