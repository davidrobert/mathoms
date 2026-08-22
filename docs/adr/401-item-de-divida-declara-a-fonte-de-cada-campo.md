---
id: ADR-401
type: adr
title: "Item de dívida declara a fonte de cada campo (fontes por chave, enum próprio)"
status: Decidido
phase: A40 · RV6-15
date: "2026-08-19"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-129]]"
  - "[[ADR-137]]"
  - "[[ADR-209]]"
  - "[[ADR-212]]"
  - "[[ADR-227]]"
  - "[[ADR-301]]"
  - "[[ADR-343]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 396"
  - "fontes por campo em endividamento"
  - "taxa_juros_aa"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - phase/a40
---

# ADR-401 — Item de dívida declara a fonte de cada campo

**Status:** Proposto • **Data:** 2026-08-19 • Origem: achado **RV6-15** da
revisão r7 (`endividamento.dividas[]` fabrica `descricao` e publica
parcela/taxa sempre nulas).

## Contexto

`endividamento.dividas[]` do E5 tem quatro campos e três defeitos encadeados:

1. **O item não é uma dívida.** `EndividamentoAnalyzer` ignora
   `baseline_patrimonial.dividas[]` — que **já é itemizado** desde a
   [[ADR-301]], com `credor`, `numero_contrato`, `tipo`, `indexador` — e
   fabrica um item por **membro** a partir de `member_data["total_dividas"]`.
   Daí a `descricao` inventada `"Financiamento imobiliário (<nome>)"`: é um
   rótulo sobre um agregado por pessoa, não sobre um contrato.
2. **Parcela e taxa são `null` em todo run medido** (r5, r6, r7). O agregado
   `Debt` — que tem `parcela_mensal_cents` e `taxa_juros_aa` preenchidos pelo
   usuário na UI — não é lido pelo E5. A coluna "Taxa" do card renderiza "—"
   para todo cliente, e a red line RL2 ("dívida cara precede risco") é
   **inalcançável por construção**.
3. **Nada no item diz de onde o número veio.** Quando parcela/taxa passarem a
   existir, o leitor não distinguirá "declarado pelo usuário" de "estoque de
   31/12 do IRPF" de "medido no extrato" — e essas três coisas têm validades
   temporais diferentes.

O terceiro é o que trava os outros dois: sem discriminador de origem, popular
o item a partir de uma segunda fonte é uma afirmação silenciosa.

## Decisão

### D1 — A origem é declarada **por campo**, em `fontes`, com enum próprio

```json
"fontes": {
  "saldo_devedor": "baseline_irpf",
  "parcela_mensal": "declarado"
}
```

`fontes` é objeto `additionalProperties: false`, `required: ["saldo_devedor"]`,
e **cada chave tem o seu próprio enum** — as origens legítimas *daquele*
campo:

| chave | enum |
| --- | --- |
| `saldo_devedor` | `baseline_irpf` \| `declarado` |
| `parcela_mensal` | `declarado` |
| `taxa_juros_aa` | `declarado` |
| `desembolso_mensal_observado_brl` | `observado_e4` |

O enum por chave é o que faz a precedência de fonte virar **contrato** em vez
de convenção. Fonte nova entra como um membro no enum da chave onde ela é
legítima; declarar `parcela_mensal: "observado_e4"` passa a ser erro de
schema, não bug de leitura.

**Alternativas recusadas:** escalar único no item (`fonte: "declarado"`) —
mistura campos de validade diferente sob um rótulo só; sufixo por campo
(`parcela_mensal_fonte`) — dobra a superfície e não dá enum por chave;
`contract_version` no bloco — versão sem leitor é o defeito **RV6-12**, aberto
no mesmo run, e a versão seria por bloco quando a origem é **por item** (um
payload pode ter uma dívida `declarado` e outra `baseline_irpf`).

### D2 — Bijeção valor ↔ fonte é invariante do produtor

```
∀ c ∈ {saldo_devedor, parcela_mensal, taxa_juros_aa,
       desembolso_mensal_observado_brl}:
    item[c] is not None  ⟺  c ∈ item["fontes"]
```

O dialeto de schema que o codegen interpreta não tem `dependentRequired` nem
`dependentSchemas`, então o schema trava a **forma** e o gate
`tests/test_endividamento_fontes_bijecao.py` trava a **correspondência**. No
produtor a bijeção é por construção: `DividaItem._fontes` deriva o dicionário
do próprio item, não de disciplina de call-site.

### D3 — `taxa_juros` → `taxa_juros_aa`

Duas razões, ambas mecânicas:

- **Unidade.** 12,5% a.m. e 12,5% a.a. levam a decisões opostas, e o card
  imprimia `%` nu. O nome carrega a unidade; o card passa a imprimir
  `12,50% a.a.` sob o cabeçalho `Taxa (a.a.)`.
- **Classificação monetária.** `dev/golden_diff.py` é monetário-por-default;
  `is_monetary("taxa_juros")` é `True` e o snapshot do view-model normalizaria
  `12.5 → 1250` cents. O sufixo `_aa` já está em `_NON_MONETARY_SUFFIXES`, ou
  seja **o rename conserta a classe por construção**, sem entrada de
  allowlist.

O custo é mínimo agora e só cresce: o campo é `null` em r5/r6/r7 — **nenhum
leitor jamais viu um valor ali**. O repo já usa `taxa_juros_aa` no agregado
`Debt`, no DTO e no formulário do frontend; o E5 era o outlier.

`saldo_ano_referencia` não tem sufixo que o classificador reconheça e é um
ano inteiro — entra em `_NON_MONETARY_EXACT` com a justificativa, que é o
remédio já estabelecido nesse arquivo.

### D4 — `descricao` é rótulo derivado; identificador cru fica fora do payload

Por [[ADR-129]] a rota React é a fonte do PDF, então `descricao` é **artefato
exportado**. O E5 publica `TIPO_LABEL[tipo]`, desambiguado por código
canônico do `institution_catalog` ([[ADR-137]]) ou por ordinal. Discriminação
crua de documento fiscal (número de contrato, credor por extenso) **não entra
no payload**, e nome de pessoa sai da string para o campo tipado `membro` —
mesma fonte de exibição de `investimentos[].membro`.

### D5 — Zero observado é medição; zero atribuído a um item é ambiguidade

`desembolso_mensal_observado_brl` tem `exclusiveMinimum: 0`. No **bloco**
agregado, `0,0` com `cobertura == "observado"` é um zero medido e é sinal. No
**item**, `0,0` seria indistinguível de "não consegui atribuir a esta dívida"
— ausência ali é `null`, e sem chave em `fontes`.

### D6 — Backfill de artefato histórico é proibido

Artefato de pipeline é derivado: o backfill é o re-run. `UPDATE` em
`pipeline_artifacts` apagaria a evidência de que parcela/taxa eram nulas em
r5/r6/r7 e envenenaria o compare de três pernas da [[ADR-343]]. O schema E5 é
validado **no write** (hook em `DBArtifactStore.write`, [[ADR-212]]), nunca no
read — runs antigos seguem legíveis sem cláusula de compat.

## Consequências

- A tabela de dívidas passa a ter **uma linha por dívida**, não por membro —
  mudança visível ao cliente, com nota no changelog do relatório.
- A RL2 passa a poder **disparar**: era inalcançável enquanto a taxa fosse
  sempre `null`. A taxa de disparo precisa ser medida antes de tratar a red
  line como ativa.
- `additionalProperties: false` vale **só no item**. O flip global do
  top-level de `e5_analysis` é o débito W6-T01 e continua fora deste escopo.
- Popular a partir de `Debt` exige filtrar `source == "user_declared"`: rows
  de `baseline_irpf_migration` (backfill da Onda 2 da [[ADR-227]]) não são
  declaração do usuário, e marcá-las `"declarado"` seria afirmação falsa.
- Os dois enums de `tipo` (`Debt` e baseline) **não casam** — `cdc`,
  `emprestimo_pessoal`, `outro`×`outros`. O join exige tabela de mapeamento
  explícita com gate de totalidade; `dict.get(t, "outros")` é o mesmo silêncio
  com outra sintaxe.
