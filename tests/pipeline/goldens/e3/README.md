# Goldens E3 — fixtures sintéticas (Sessão A1)

Cenários determinísticos para testar o `E3ReconcilerAdapter` end-to-end sem
depender de workspace real. Cada arquivo `*.json` é uma fixture autocontida com:

- `description`: o que o cenário cobre
- `e2_extracts`: lista de `{stage, key, payload}` para `store.seed`
- `baseline` (opcional): payload do baseline IRPF (E1.5c)
- `institutions` (opcional): dict para `BankCanonicalizer.from_institutions`
- `expected`: contagens e chaves esperadas no resultado do adapter

## Cenários atuais

| Arquivo | Cobertura |
|---|---|
| `cenario_extratos.json` | 2 extratos sobrepostos (mesma conta), duplicata cross-file detectada e merge → 1 artefato E3 |
| `cenario_fatura_sem_periodo.json` | Fatura sem `periodo`, com `data_vencimento` + transações anachronic; valida síntese do período + drop |
| `cenario_baseline_diff.json` | Extrato C6 fechando 2024-12-31 + baseline IRPF com saldo divergente; valida `BaselineValidator` integrado ao adapter |

Estas fixtures **não** capturam o output do `main()` legado de
`scripts/reconcile_transactions.py` — esse golden de paridade real fica para a Sessão A2,
quando `main_with_store(config, store)` for introduzido. Aqui validamos apenas o
comportamento do adapter (Caminho B foundation).
