---
id: A42.l25
type: lane
title: "A mesma linha do razão publica o delta com dois sinais opostos, e o sinal observado é o único que nenhuma perda de pipeline produz"
sprint: A42
status: in_progress
priority: P1
branch_slug: a42-l25-delta-com-dois-sinais-e-mecanismo-de-instrumento
owner: data-engineer
depends_on: []
adrs: ["[[ADR-416]]", "[[ADR-426]]", "[[ADR-433]]"]
tags: [type/lane, sprint/a42, status/in-progress, priority/p1, area/dados]
---

# A42.l25 — `delta-com-dois-sinais-e-mecanismo-de-instrumento`

> **Origem:** `LC9-06` + `LC9-07` da rodada unificada **U5**
> ([[LEDGER-CERTIFY-active]] §r9). Sucessora direta da [[A42.l18]], que **ligou** a perna
> de valor: o número que ela destravou é o objeto desta lane.

## O que a linha publica

Na transição E3→E4, o campo `Δvalor` sai **negativo** e o detalhe da **mesma linha** sai
**positivo**, porque `dev/ledger_conservation.py:220` calcula `value_in - value_out`
apenas para o texto. **A direção do viés é irresolvível a partir da saída** — dois leitores
honestos da mesma linha chegam a conclusões opostas, e foi o que aconteceu no painel desta
rodada.

## E o delta provavelmente NÃO é perda

O sinal observado — destino **maior** que origem — é **o único que nenhuma perda de
pipeline produz**: perda encolhe o destino. Dois mecanismos candidatos, ambos de
instrumento:

- **Dois parsers para o mesmo campo.** O agrupador lê `"1.234"` como mil duzentos e trinta
  e quatro; a origem lê como um vírgula dois três quatro — fator **1000×** num subconjunto.
- **Quatro termos com duas convenções de sinal.** O delta é **líquido de opostos**, então
  compensações silenciosas cancelam parcelas que deveriam somar.

## Por que não é P0

Nada aqui muda número publicado ao usuário — é **instrumento**. Mas enquanto o sinal for
ambíguo, a perna de valor destravada pela [[A42.l18]] **não sustenta veredito**, e o razão
volta a `coberto-sem-verificação-de-valor` na prática.

## Critério de aceite

1. Um único produtor do delta; campo e detalhe **impossíveis** de divergir (mesma
   expressão, não duas).
2. Convenção de sinal declarada por termo, e o delta publicado **bruto por termo** além do
   líquido.
3. Um parser por campo, com o contrafactual: string ambígua no formato brasileiro produz o
   mesmo valor nos dois lados.
4. Controle positivo: mutação de 1 centavo em 1 termo move o delta em 1 centavo, com sinal
   correto — hoje isso não é verificável.

---

## Entregue 2026-09-01 — PR #TBD · [[ADR-433]] + emenda datada na [[ADR-426]]

**O eixo fecha ao centavo no corpus real.** Re-derivação in-process em `ws-1b9f2cf5`:

| | antes (U5) | depois |
| --- | ---: | ---: |
| `Δvalor(destino−origem)` | −1.998.772 | **0** |
| veredito da perna | `coberto-sem-verificação-de-valor` | **`conservado`** |

Termos brutos publicados: `despesas=229.916.766 + receitas=492.121.431 +
transferencias=1.079.573.726 + dedup_removido=273.826.171 = 2.075.438.094`, idêntico à
origem. Ponte `abs == assinado + 2 × negativas` fecha nos dois baldes.

### Os 4 critérios

1. **Produtor único** ✅ `dev.ledger_verdicts.delta_cents`, e `DELTA_LABEL` põe a direção
   no rótulo. Campo e detalhe passaram a ser impossíveis de divergir.
2. **Convenção por termo + bruto além do líquido** ✅ Quatro sinais novos, todos Σ|valor|;
   a linha do razão publica os termos e a origem.
3. **Um parser por campo** ✅ `_soma_cents`/`_collapsed_cents` migraram de `cents_int`
   para `decimal_cents`.
4. **Controle positivo** ✅ +1 centavo em qualquer termo declarado move o Δ em 1 centavo
   com o sinal do rótulo; e o dual — 1 centavo numa receita **negativa** move o Δ em 0,
   onde a fórmula antiga movia 2.

### O que a medição REFUTOU do próprio enunciado

**A §"E o delta provavelmente NÃO é perda" citava o sinal errado.** O enunciado afirma
*"o sinal observado — destino **maior** que origem"*. Medido: o campo publicava
`out − in = −1.998.772`, ou seja destino **MENOR** — exatamente a assinatura que perda
produz. O `LC9-07` leu o **detalhe** (`+1.998.772`) como se fosse o campo. Ele é, portanto,
**vítima direta do `LC9-06`**: o achado nasceu falso por causa da ambiguidade que o achado
irmão denuncia. A **conclusão** ("não é perda") sobrevive — mas por medição de mecanismo,
não pelo argumento de sinal, que era inválido.

**Mecanismo 1 ("dois parsers, fator 1000×") — refutado na magnitude, procede na classe.**
Não há fator 1000× em lugar nenhum: o resíduo de despesas é 0 e o de receitas é 100%
explicado pelo mecanismo 2. Mas *dois conversores* existiam mesmo — o produtor usava
`cents_int` (`int(round(float(v)*100))`) e o harness `Decimal(str(v))`, que discordam no
**meio-centavo**, não em 1000×. Fechado assim mesmo (critério 3), com teste que falha sob
mutação do conversor.

**Mecanismo 2 ("quatro termos, duas convenções") — confirmado e quantificado.** 48 receitas
negativas, Σ|v| = 999.386 cents; `2 × 999.386 = 1.998.772`, o gap inteiro.

### O que a medição ACRESCENTOU, e é mais grave que o enunciado

**O Δ não era resíduo; era offset constante.** O destino subestimava em `2 × Σ|negativas|`
**sempre**, por construção. Logo uma perda real de R$ 19.987,72 publicaria `Δ = 0` com
veredito `conservado`: **canal de mascaramento**, não ambiguidade cosmética. A prioridade
P1 não muda (nada publicado ao usuário se move), mas a perna não estava "ambígua" — estava
**cancelável**.

**A [[ADR-429]] fará o mesmo defeito reaparecer em `despesas`.** Ela declara que
`despesas.dados[*].valor` deixa de ser ≥ 0. Quando entrar, `despesas.total_geral` deixa de
ser Σ|valor| pelo mesmo mecanismo — mudando de **valor**, não de forma, portanto em
silêncio. Por isso os termos de despesa foram declarados agora, mesmo sendo hoje idênticos
ao `total_geral`: há teste que simula o mundo pós-[[ADR-429]] e exige que o eixo continue
fechando.

### Roteado, não consertado aqui

- **Evidência de produção para a [[ADR-429]] / [[A40.l102]]:** as 48 receitas negativas
  (R$ 9.993,86 em `ws-1b9f2cf5`) são `PAGAMENTO EFETUADO`/estorno virando receita. A ADR
  hoje só tem fixture; o fenômeno é regra de domínio e não foi tocado aqui.
- **`golden_diff` lê folha `*_cents` como monetária** por marcador de nome — esta lane
  **amplia de 2 para 6** as chaves nessa condição. Sem efeito sobre número publicado; o
  conserto certo é tratar `_lineage.` como namespace não-monetário, escopo próprio.
