---
id: ADR-431
type: adr
title: "Valor impossível em item de ativo físico vira `null` declarado, não zero nem passivo"
status: Decidido
phase: A40
date: "2026-08-31"
relates_to:
  - "[[ADR-394]]"
  - "[[ADR-346]]"
  - "[[ADR-097]]"
  - "[[ADR-272]]"
  - "[[ADR-090]]"
tags:
  - type/adr
  - status/decidido
  - area/e5
  - area/dominio
  - sprint/a40
aliases: ["ADR 431", "valor não apurado", "valor_nao_apurado"]
---

# ADR-431 — Valor não apurado em item de ativo físico

**Status:** Decidido (A40.l111) • **Data:** 2026-08-31 • Co-design `financial-planner`,
com a regra de domínio confirmada contra fonte externa (RFB). **Dono:** `financial-planner`.

## Contexto

Um item de `imoveis_consolidados` chegava ao relatório com **valor negativo**
(`tipo: imovel`, `codigo_rfb: "11"` — apartamento). Ninguém pegou, e as três razões
são estruturais:

- a guarda de sinal da [[ADR-394]] §Emenda **D6** opera no **balde agregado**. O
  agregado é positivo enquanto o item negativo for menor que a soma dos irmãos —
  ela é estruturalmente cega a defeito de sinal **no item**;
- o schema tem `minimum: 0` e **pega**, mas roda em `warn`: loga e grava;
- o classificador silenciava o par `secao` + negativo. Corrigido pela emenda
  2026-08-31 da [[ADR-394]] — é o que tornou este achado visível.

## A regra de domínio (RFB)

Apartamento financiado é declarado **em Bens e Direitos, pelo valor pago** — nunca a
mercado — e o **saldo devedor não vai em Dívidas e Ônus Reais**. Os dados da
instituição vão na *discriminação* da linha do bem.

Três consequências que invertem a leitura intuitiva:

1. **`instituicao` presente não é evidência de dívida** — é o campo que a Receita
   manda preencher na linha do **ativo** financiado.
2. **Não existe contraparte** a "devolver ao lugar certo".
3. **O contribuinte não consegue digitar negativo** em Bens e Direitos: o PGD não
   aceita. O sinal **não veio da declaração** — é nosso.

Logo: defeito de **medição do valor**, com o **eixo correto**.

## Decisão

**D1 — O item fica, o valor sai.** O apartamento existe; apagá-lo esconde um bem da
família. O **valor** vira `null`, sai da soma, e carrega `review_reason`
(`domain.valor_nao_apurado`). Escopo: **item de ativo físico**
(`imoveis_consolidados`, `veiculos_consolidados`), onde negativo é impossível por
definição. Investimento fica de fora — lá negativo é saldo devedor legítimo (conta
margem, cheque especial) e a D6 já o reclassifica.

Erro publicado no patrimônio líquido, com `V` = valor real do bem e `X` = o saldo
devedor que o extrator leu no lugar dele:

| saída | erro | declarado? |
|---|---|---|
| publicar o negativo (status quo ante) | `−(V + X)` | não |
| mover para dívidas | `−(V + X)`, e fabrica passivo que a RFB proíbe declarar | não |
| **`null` + fora da soma** | `−V` — de um lado só | **sim** |

`abs()` está fora: publicaria a **dívida como se fosse o valor do bem** — plausível,
auditável só contra a declaração, e o pior desfecho possível. Zerar em silêncio está
fora: zero é afirmação sobre o patrimônio da pessoa ([[ADR-346]], [[ADR-394]]
§Emenda (b) D7).

**D2 — O contrato muda no produtor.** `valores_31_12[<ano>]` passa a
`["number", "null"]` para as duas coleções físicas, e o item ganha
`valor_nao_apurado: {anos, motivo}`. É contrato de produtor entre E1.5c → E4 → E5:
o leitor precisa distinguir "não medimos" de "vale zero", e `null` sozinho não faz
isso — `valores_31_12[ano] is None` é indistinguível de ano ausente, e a cascata de
chaves alternativas cairia em `valor_<ano>`/`valor`, **ressuscitando** um valor de
outra data no lugar do que não foi medido.

**D3 — O saneamento roda em dois pontos, com a mesma função.** No **item**, dentro do
loop de consolidação, e no **boundary** do stage, antes do write. Os dois são
necessários e nenhum basta:

- só no boundary: `patrimonio_por_ano.total_bens` fica com o negativo, e o E5 credita
  a diferença `resumo − sintético` ao titular — o valor recém-removido **reentra pelo
  resíduo**;
- só no item: dedup e merge de informe rodam depois e podem trazer o negativo de volta.

**D4 — A supressão herda o canal da D6, um grão abaixo.** A guarda de sinal ganha
`itens_sem_valor`, e `motivo_supressao` compõe os dois eixos. Não se cria canal novo:
as prescrições que dependem de cat_2 (desvio vs. alocação alvo, próximo aporte,
concentração imobiliária) já leem `motivo_supressao_do_patrimonio`. Descritivos
publicam inteiros — a [[ADR-394]] §Emenda já decidiu que suprimir a descrição esconde
o defeito onde o leitor confere.

**D5 — Não flipar o schema para `strict` como conserto.** Viraria abort de run e
violaria o WARN-first do D6. Com o valor virando `null`, o schema **aceita** e o
domínio carrega a decisão.

## Consequências

- A conservação ano-cega do E1.5c cala quando há item retirado da soma, na mesma forma
  já usada para `pj_skipped` ([[ADR-268]]): a divergência é construída por nós e já tem
  código próprio; publicá-la como `baseline_divergence` daria ao operador o código
  errado para o mesmo fato.
- `imovel_valor`/`veiculo_valor` retornam `0,0` para o item declarado. Isso é
  **exclusão da Σ**, não afirmação de zero — o que se **publica** no item é `null`.
- `S4`: o imóvel sai do cap rate, do peso da média ponderada e do denominador do
  pro-rata da renda, com motivo declarado em `excluded_properties` (que a UI já
  renderiza). Entrar com `valor_imovel = 0` publicaria como carteira inteira o que é
  só a parte medida dela.
- A ressalva de família precisa dizer **a direção do erro**. Sem o "para que lado", o
  leitor assume que o número publicado é o teto — e aqui é o piso.

## Não decide

- **Não desce a guarda de sinal ao grão da linha genericamente.** A §Taxa de disparo
  do D6 já mediu o modo de falha (6/6 runs por centavos que se anulam dentro do caixa).
- **Não renomeia `low_confidence`.** O nome é sobrecarregado — lê-se "extração fraca" e
  significa "identidade não canonicalizada" ([[ADR-246]]). Renomear é breaking; janela
  própria, dono `data-engineer`.
- **Não corrige a origem do sinal.** A hipótese medida é que o extrator leu o saldo
  devedor da discriminação em vez da coluna "situação em 31/12"; confirmá-la exige o
  documento, e esta ADR decide o que publicar enquanto isso.
