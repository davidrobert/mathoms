# Relatório de Problemas — E-full-reset 2026-04-08

## Resumo da Execução

| Etapa | Status | Observação |
|---|---|---|
| Passo 1: Git snapshot | OK | Commit bem-sucedido |
| Passo 2: Move data/+members/ → inbox/ | PARCIAL | Permissões impediram deleção de artefatos |
| Passo 3: E0-unlock | OK | 86 PDFs abertos, 0 protegidos |
| Passo 4: E0-audit | OK | 0 erros, 0 avisos |
| Passo 5: E0 roteamento | OK | 154 arquivos roteados, inbox vazio |
| Passo 6a: E1 membros | OK | 5 artefatos gerados |
| Passo 6b: E1.5 baseline | OK | 9 JSONs + baseline consolidado |
| Passo 6c: E2-extratos-llm | OK | 11 JSONs de investimentos/CDBs |
| Passo 7: E2-faturas | PARCIAL | 53/53 OK após correção de conflito CSV |
| Passo 7: E2-extratos | PARCIAL | 60 processados, 4 erros de validação (XLS Santander) |
| Passo 7: E3→E6 cascata | OK | V1-V19 PASS |
| Passo 8: E5.N narrativas | PARCIAL | V19 falhou na 1ª tentativa (formato monetário) |
| Passo 9: E7 review | OK | 10/12 checks, 2 issues menores |
| Passo 10: Git commit | PARCIAL | Lock file exigiu permissão extra |
| Passo 11: E0-audit final | OK | 0 erros, 20 avisos (sobreposições esperadas) |

---

## Problemas Encontrados (por gravidade)

### ALTA — Impactaram dados ou exigiram intervenção manual

#### 1. CSVs Santander sobrescreveram extrações PDF

**Etapa:** E2-faturas (Passo 7)
**O que aconteceu:** Os arquivos `fatura-YYYYMMDD.csv` do Santander foram roteados como `santander_faturaunique_YYYYMM-0_original.csv`. Quando o `e2_extract_faturas.py` processou, os CSVs (sem parser Santander CSV) geraram JSONs com 0 transações e SOBRESCREVERAM os JSONs válidos que haviam sido extraídos dos PDFs homônimos.
**Impacto:** 14 meses de faturas Santander Unique ficaram com 0 transações até a correção.
**Correção aplicada:** Movi os CSVs para `data/financial_statements/csv_alternate/` e re-executei o script.
**Sugestão para o processo:**
- O script `e2_extract_faturas.py` deveria verificar se já existe um JSON com transações antes de sobrescrever com um JSON vazio.
- Alternativa: adicionar um parser CSV para Santander Unique (formato simples: `data,lançamento,valor`).
- No manual, documentar que CSVs de fatura Santander não devem compartilhar o mesmo nome-base que os PDFs.

#### 2. Permissões de arquivo impediram limpeza completa no --move-to-inbox

**Etapa:** Passo 2 (e_reset.py --move-to-inbox --clean-only)
**O que aconteceu:** O script não conseguiu deletar os artefatos em `processed/E2_extracts/`, `processed/E3_reconciled/`, `processed/E4_unified/`, `processed/E5_analysis/`. Em vez de deletar, truncou para 0 bytes.
**Impacto:** JSONs truncados (0 bytes) causaram erros de parsing nas fases 1.5/1.6 do script. Também impediu o e0_audit de validar os JSONs (187 infos de "arquivo 0 bytes").
**Sugestão para o processo:**
- O `e_reset.py` deveria ter uma flag `--force-delete` que solicita permissão elevada ao sistema operacional.
- Alternativa: o script poderia reescrever os JSONs com `{}` ao invés de truncar para 0 bytes, evitando erros de parsing.

### MÉDIA — Dados parciais ou funcionalidade reduzida

#### 3. Parser XLS Santander (planilhaExtrato) não extrai transações

**Etapa:** E2-extratos (Passo 7)
**O que aconteceu:** 4 arquivos `santander_extratoconta_*-0_original.xls` (formato planilhaExtrato do internet banking Santander) retornaram 0 transações. O parser tenta ler como CSV mas o formato é XLS binário com layout proprietário (7 colunas: Data, Descrição, Docto, Situação, Crédito, Débito, Saldo).
**Impacto:** Dados de conta corrente Santander de out/2024 a jan/2026 ficaram sem transações nos extratos XLS. O período parcialmente coberto pelos PDFs (nov/2025 a mar/2026) compensou.
**Sugestão para o processo:**
- Implementar parser XLS dedicado no `e2_extract_extratos.py` usando `xlrd` (já disponível) para o formato planilhaExtrato.
- O formato tem header na row 5 (Data, Descrição, Docto, Situação, Crédito, Débito, Saldo) e dados começam na row 6.

#### 4. Arquivos CDB Santander em HTML disfarçado de .xls

**Etapa:** E2-extratos-llm (Passo 6c)
**O que aconteceu:** `ExtratoMensal-CDB METAS E RSERVAS.xls` e `ExtratoMensal-CDB-DI.xls` são na verdade HTML exportado do internet banking Santander com extensão .xls. O `xlrd` falha com "Expected BOF record; found b'<html xm'".
**Sugestão para o processo:**
- Detectar automaticamente arquivos HTML disfarçados de XLS (verificar primeiros bytes) no E0-unlock ou E0-audit.
- Converter para formato real usando BeautifulSoup para extrair tabelas HTML.

#### 5. Extratos com 0 transações (Bank of America, Wise BRL, Santander CC 202511)

**Etapa:** E2-extratos (Passo 7)
**O que aconteceu:** 3 PDFs retornaram 0 transações:
- `bankofamerica_extratoconta_202602_202603`: Parser BoA provavelmente não conseguiu ler o layout.
- `wise_extratocontabrl_202501_202603`: Parser Wise BRL falhou (o USD funcionou com 31 txns).
- `santander_extratoconta_202511_202512`: Parser Santander não extraiu transações.
**Sugestão:** Revisar e aprimorar os parsers desses bancos.

### BAIXA — Cosméticas ou resolvidas automaticamente

#### 6. V19 falhou na primeira renderização E6 (formato monetário)

**Etapa:** E5.N + E6 render (Passo 8)
**O que aconteceu:** As narrativas geradas pela LLM continham `R$ 2.5k` e `R$ 3.5k` (ponto decimal ao invés de vírgula).
**Correção:** Regex automático substituiu por `R$ 2,5k` e `R$ 3,5k`. V19 passou na segunda tentativa.
**Sugestão:** Incluir exemplos explícitos de formato correto no prompt do E5.N, ou adicionar pós-processamento automático de formatação monetária.

#### 7. CV14 no E7: espaço entre valor e sufixo monetário

**Etapa:** E7 cross-validation (Passo 9)
**O que aconteceu:** Uma narrativa em summaries.s5 tinha espaço entre valor e sufixo k/M.
**Sugestão:** Mesmo tratamento do item 6 — pós-processamento automático.

#### 8. Git lock files persistentes

**Etapa:** Passo 10 (commit)
**O que aconteceu:** O primeiro commit falhou com "HEAD.lock exists" e depois "index.lock exists" — resíduos de operações git anteriores que não puderam ser limpos sem permissão de deleção.
**Sugestão:** O `e_save.py` poderia verificar e limpar lock files antes de executar git operations.

#### 9. 15 arquivos Itaú XLS com períodos sobrepostos

**Etapa:** E0 roteamento (Passo 5)
**O que aconteceu:** Os 15 XLS do Itaú cobrem períodos que se sobrepõem completamente (todos terminam em abr/2026, com início progressivamente mais antigo). Isso gerou 20 avisos de sobreposição no e0_audit final.
**Sugestão:** Documentar no manual que downloads trimestrais do Itaú geram sobreposição, e que o E3 (reconciliação) deve deduplicar transações entre eles.

---

## Métricas de Execução

| Métrica | Valor |
|---|---|
| Arquivos roteados (E0) | 154 |
| Faturas processadas (E2-faturas) | 53 |
| Transações de fatura extraídas | 3.161 |
| Extratos processados (E2-extratos) | 60 |
| Transações de extrato extraídas | 3.872 |
| Investimentos/CDBs processados (LLM) | 11 |
| Relatório HTML final | 254,5 KB |
| Validações E6 (V1-V19) | 19/19 PASS |
| E0-audit final | 0 erros |
| Tempo total estimado | ~25 min (LLM) + ~2 min (determinístico) |

---

## Recomendações Prioritárias para Aprimorar o Processo

1. **Parser CSV Santander Unique** — Implementar no `e2_extract_faturas.py`. O formato é trivial (3 colunas: data, lançamento, valor). Isso evita o conflito CSV/PDF e adiciona redundância.

2. **Parser XLS planilhaExtrato** — Implementar no `e2_extract_extratos.py` usando `xlrd`. Formato bem definido com 7 colunas.

3. **Proteção contra sobrescrita** — O script de faturas não deve gerar JSON com 0 transações se já existe um JSON válido para o mesmo período/banco.

4. **Pós-processamento monetário** — Adicionar sanitização automática de `R$ X.Yk` → `R$ X,Yk` após geração de narrativas (antes do E6 render).

5. **Detecção de HTML-as-XLS** — No E0-unlock ou audit, verificar se arquivos .xls são na verdade HTML.
