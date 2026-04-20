# Goldens E4 — fixtures sintéticas (Sessão A4a)

Cenários determinísticos para testar o `E4CategorizerAdapter` end-to-end sem
depender de workspace real. Cada arquivo `*.json` é uma fixture autocontida
com:

- `description`: o que o cenário cobre
- `categorization`: payload parcial do `categorization.json` (apenas as
  keywords relevantes para o cenário)
- `family`: payload parcial do `family_members.json` (transferencias_internas,
  banco_membro)
- `e3_accounts`: lista de `{key, payload}` para `store.seed("E3", ...)`
- `baseline` (opcional): payload para `store.seed("E1.5c", "baseline_patrimonial", ...)`
- `e2_positions` (opcional): lista de `{stage, key, payload}` para seed de
  posições de investimento
- `expected`: contagens e asserts principais

## Cenários atuais

| Arquivo | Cobertura |
|---|---|
| `cenario_receitas_despesas_simples.json` | Receitas CLT + despesas categorizadas; sem transferências |
| `cenario_transferencia_interna.json` | Transferências PIX entre membros da família; não contam como receita/despesa |
| `cenario_baseline_investimentos.json` | Baseline IRPF v1 + posições BTG/Rico consolidadas; valida consolidador |

Os goldens validam o comportamento do adapter (Caminho B foundation) — não
são paridade com `main()` legado. Esse golden de paridade completo vem na
Sessão A4b, junto com o serializer E4 e o switch do wrapper.
