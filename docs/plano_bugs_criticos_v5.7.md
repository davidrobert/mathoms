# Plano de Correção — Bugs Críticos v5.7

**Data:** 2026-04-08
**Escopo:** 3 bugs identificados no E-full-reset de 08/abr/2026

---

## Bug 1: Patrimônio E1.5 → E5 (schema mismatch)

### Problema
O `e5_analyze.py._resolve_members()` não reconhecia o formato E1.5 do baseline patrimonial. O campo `membros` é uma lista de strings (nomes), mas o código esperava lista de dicts com chave `nome` ou dict com sub-chaves `david`/`mariana`. Resultado: patrimônio zerado no relatório.

### Fix já aplicado (paliativo)
Adicionada função `_build_members_from_declarations()` que converte `declarations[].bens_direitos[]` em member dicts usando classificação por grupo IRPF (G01=imóveis, G02=veículos, G03/04/07=investimentos, G06=contas).

### O que falta (fix definitivo)

**1a. Normalizar schema do baseline na geração (E1.5)**

O problema raiz é que o `baseline_patrimonial-1.5_consolidated.json` não tem schema enforcement. A LLM que gera o E1.5 pode produzir qualquer formato. O fix definitivo seria:

- Criar um **JSON Schema** formal para o baseline (`config/schemas/baseline_patrimonial.schema.json`)
- Adicionar validação pós-geração no E1.5 que rejeite baseline fora do schema
- Schema deve exigir: `patrimonio_por_ano`, `investimentos_consolidados`, `imoveis_consolidados`, `veiculos_consolidados`, `dividas` — o formato que `_build_members_from_consolidated()` já sabe ler

**Arquivos a alterar:**
- `config/schemas/baseline_patrimonial.schema.json` (NOVO)
- Script/prompt do E1.5 (adicionar validação pós-geração)
- `config/manual_operacao.md` (documentar schema obrigatório)

**Estimativa:** 1-2h

**1b. Manter _build_members_from_declarations como fallback**

O fix paliativo já aplicado deve permanecer como fallback defensivo caso o baseline venha em formato inesperado. Adicionar log warning quando este path é usado:

```python
print("  [WARN] Baseline em formato E1.5 declarations — usando fallback. Considere regenerar E1.5.")
```

**Arquivos a alterar:**
- `scripts/e5_analyze.py` (apenas adicionar warning)

**Estimativa:** 5min

**1c. Testes de regressão**

Criar um test que valide os 4 formatos suportados por `_resolve_members()`:
1. Dict format (`members.david`)
2. List-of-dicts (`membros: [{nome: "DAVID..."}]`)
3. E1.5 declarations (lista de strings + declarations[])
4. Consolidated v1.5 (`patrimonio_por_ano`, `investimentos_consolidados`)

**Arquivos a criar:**
- `tests/test_e5_patrimonio_formats.py` (NOVO)

**Estimativa:** 30min

---

## Bug 2: E4 investimentos-4_unified.json sempre vazio

### Problema
O `e4_categorize.py` (linhas 646-649) cria `investimentos-4_unified.json` como `{"dados": []}` em TODAS as execuções. Os extratos de posição de investimentos gerados pelo E2-llm (BTG, Rico, Itaú, C6, Santander — 37 posições totais, R$ 985k) nunca são incorporados.

Consequência: o patrimônio investível no E5 usa apenas dados do IRPF 2024 (base 31/12/2024), defasados ~15 meses. Os CDBs e fundos nas declarações IRPF têm valores de dez/2024, não de mar/2026.

### Solução proposta

**2a. Criar loader de posições de investimento no E4**

Adicionar ao `e4_categorize.py` uma função que:
1. Procura todos os `*_investimentosposicao_*-2_extract.json` e `*_carteira*-2_extract.json` e `*_cdb*-2_extract.json` em `E2_extracts/`
2. Unifica em schema padronizado:
```json
{
  "dados": [
    {
      "nome": "CDB AGIBANK 116.65% CDI",
      "tipo": "CDB",
      "instituicao": "BTG Pactual",
      "membro": "mariana",
      "valor_atual": 29353.39,
      "data_referencia": "2026-03-31",
      "taxa": "116.65% do CDI",
      "vencimento": "2026-11-10"
    }
  ],
  "total_david": 609717.48,
  "total_mariana": 375384.56,
  "total_geral": 985101.04,
  "data_consolidacao": "2026-04-08"
}
```

**Arquivos a alterar:**
- `scripts/e4_categorize.py` — nova função `build_investimentos_unified()`, substituir placeholder
- `config/manual_operacao.md` — documentar que E4 agora popula investimentos

**Estimativa:** 1h

**2b. E5 usa investimentos-4_unified.json para patrimônio ATUAL**

Modificar `e5_analyze.py.analyze_patrimonio()` para:
1. Ler `investimentos-4_unified.json` se não vazio
2. Se populado: usar como fonte primária dos investimentos (mais recente que IRPF)
3. Se vazio: fallback para baseline IRPF (comportamento atual)
4. Na composição patrimonial, substituir investimentos IRPF pelos atuais

Lógica de merge:
- `patrimonio.bruto` = imóveis (IRPF) + veículos (IRPF) + investimentos (posições atuais) + contas bancárias
- Sinalizar no JSON que patrimônio usa mix de fontes (IRPF para imóveis, posições atuais para investimentos)

**Arquivos a alterar:**
- `scripts/e5_analyze.py` — nova lógica em `analyze_patrimonio()`
- `config/manual_operacao.md`

**Estimativa:** 1.5h

**2c. Impacto esperado no score**

Com posições atuais (R$ 985k vs ~R$ 834k do IRPF), o patrimônio investível sobe ~18%, o que melhora:
- Progresso IF: ~34% (vs 31.6%)
- Score: ~5.8-6.0 (vs 5.6)
- Cobertura: ~27 meses (vs 23.3)

---

## Bug 3: e0_audit.py crash em JSONs tipo lista

### Problema
A função `check_filename_vs_content()` (linha 177) chama `data.get("banco", "")` assumindo que todo JSON do E2 é um dict. Quando o JSON é uma lista (ex: arquivos de fatura que contêm array de transações), `data.get()` falha com `AttributeError: 'list' object has no attribute 'get'`.

### Solução proposta

**3a. Guard clause para tipo de dados**

Adicionar verificação de tipo logo após o `json.load()`:

```python
data = json.load(f)

# Skip non-dict E2 files (e.g., fatura arrays, tombstones)
if not isinstance(data, dict):
    continue  # or: log as INFO and skip

if "_tombstone" in data:
    continue
```

**Arquivos a alterar:**
- `scripts/e0_audit.py` — guard clause em `check_filename_vs_content()` (após linha 163)

**Estimativa:** 10min

**3b. Auditoria de robustez nas demais funções**

Verificar que `check_saldo_gaps()`, `check_hash_duplicates()`, e `check_name_collisions()` também lidam corretamente com JSONs não-dict. Adicionar guards similares onde necessário.

**Arquivos a alterar:**
- `scripts/e0_audit.py` — verificar e corrigir funções check_3 a check_7

**Estimativa:** 20min

**3c. Adicionar check para 0-byte files**

Após E-full-reset, os arquivos truncados (0 bytes) geram falsos positivos no audit. Adicionar um check específico que:
- Detecta 0-byte JSON files em E2_extracts/
- Reporta como INFO (não ERROR) com mensagem explicativa
- Sugere cleanup quando filesystem suportar delete

**Arquivos a alterar:**
- `scripts/e0_audit.py` — nova verificação no início de `check_filename_vs_content()`

**Estimativa:** 15min

---

## Priorização e Sequência

| Ordem | Item | Impacto | Esforço | Risco |
|-------|------|---------|---------|-------|
| 1 | 3a. Guard clause e0_audit | Evita crash | 10min | Baixo |
| 2 | 1b. Warning no fallback | Observabilidade | 5min | Zero |
| 3 | 2a. Loader investimentos E4 | Patrimônio atualizado | 1h | Médio |
| 4 | 2b. E5 usa investimentos atuais | Score correto | 1.5h | Médio |
| 5 | 3b. Robustez demais checks | Evita crashes futuros | 20min | Baixo |
| 6 | 3c. Check 0-byte files | UX do audit | 15min | Baixo |
| 7 | 1a. Schema enforcement E1.5 | Prevenção estrutural | 2h | Baixo |
| 8 | 1c. Testes de regressão | Proteção contra regressão | 30min | Zero |

**Tempo total estimado:** ~5.5h

**Sugestão de execução:** Itens 1-4 numa primeira sessão (~2.5h), itens 5-8 numa segunda sessão (~3h).

---

## Changelog v5.7 (draft)

| Mudança | Motivo |
|---|---|
| **Fix: e5_analyze.py suporta formato E1.5 declarations** | Baseline com `membros` como lista de strings + `declarations[]` agora é corretamente parseado via classificação por grupo IRPF (G01-G99). Fallback defensivo mantido. |
| **Fix: e0_audit.py robusto a JSONs não-dict** | Guard clause impede crash em `check_filename_vs_content()` quando E2 JSON é lista ou 0 bytes. |
| **Novo: E4 popula investimentos-4_unified.json** | Extratos de posição (BTG, Rico, Itaú, C6, Santander) agora consolidados no E4. Patrimônio investível usa posições atuais (mar/2026) ao invés de IRPF (dez/2024). |
| **Novo: E5 patrimônio com fontes mistas** | Imóveis/veículos do IRPF + investimentos das posições atuais. JSON sinaliza data_referencia de cada fonte. |
| **Novo: Schema validation para baseline E1.5** | JSON Schema formal impede baseline em formato incompatível. |
| **Novo: tests/test_e5_patrimonio_formats.py** | Testes para 4 formatos suportados por _resolve_members(). |
