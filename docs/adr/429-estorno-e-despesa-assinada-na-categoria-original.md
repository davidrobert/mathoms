---
id: ADR-429
type: adr
title: "Estorno é despesa assinada na categoria original, no mês do estorno — nunca receita"
status: Proposto
phase: A40
date: "2026-08-31"
relates_to:
  - "[[ADR-333]]"
  - "[[ADR-351]]"
  - "[[ADR-350]]"
  - "[[ADR-425]]"
  - "[[ADR-242]]"
  - "[[ADR-390]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/dominio
  - sprint/a40
aliases: ["ADR 429", "estorno", "reembolso"]
---

# ADR-429 — Estorno é despesa assinada, não receita

**Status:** Proposto • **Data:** 2026-08-31 • Regra de domínio do
`financial-planner`; contrato de dados do `data-engineer`. Origem: `RR7-02` item 2,
cujo **mecanismo enunciado não procedia** — medido no fecho da [[A40.l98]].

## O defeito, medido

Todo crédito vira receita: `transaction_classifier._classify_one` roteia
`tipo == "credito"` para `_classify_credito` → `kind="receita"`. Não existe noção de
estorno. **E o sinal do erro depende de qual documento carregou o estorno.**

Medido E3→E5 sobre as fixtures deste repo (`tests/fixtures/pipeline_golden/e3/estorno-*`,
renda de R$ 240.000 em 12 meses, compra de R$ 48.000):

| mundo | `receita_total` | `despesa_total` | `fluxo_liquido` | `equivalente_meses_poupanca` |
| --- | ---: | ---: | ---: | ---: |
| sem par (controle) | 240.000 | 0 | 240.000 | 0,0 |
| só a compra (conta) | 240.000 | 48.000 | 192.000 | 3,0 |
| **compra + estorno na CONTA** | **288.000** | 48.000 | 240.000 | **2,4** |
| só a compra (fatura) | 240.000 | 48.000 | 192.000 | 3,0 |
| **compra + estorno na FATURA** | **192.000** | 48.000 | 144.000 | **4,0** |
| compra + **pagamento** da fatura | 192.000 | 48.000 | 144.000 | 4,0 |

Na **conta** o estorno infla a receita e o par fica mais **otimista** (3,0 → 2,4). Na
**fatura** ele entra como receita **negativa** e o par fica mais **pessimista**
(3,0 → 4,0) — a despesa continua lá, e a receita cai pelo mesmo valor: o cancelamento
é contado duas vezes contra a família.

**E o pagamento da fatura sofre do mesmo mal:** a linha `PAGAMENTO EFETUADO` também é
crédito, e também deflaciona a receita em R$ 48.000. `_classify_credito` é o **único**
ramo do classificador sem `abs()`, então `por_fonte[*]` negativo é publicável hoje.

> ⚠️ **Convenção de sinal, e ela mordeu na primeira versão desta ADR.** Em
> `faturacartao` o **positivo é compra** e o negativo é crédito
> (`categorize_transactions.py:733`); em `extratoconta` é o inverso. A tabela original
> desta nota vinha de uma sonda em scratchpad e **não era reproduzível** pelas fixtures
> que o mesmo PR entregou — elas modelavam a fatura com sinal de extrato, o que fazia a
> renda virar despesa. Corrigido no closeout: renda vive no extrato, compra e estorno na
> fatura, e cada mundo é um **conjunto de documentos**, como no dogfood real.

## Duas causas-raiz, e a segunda é uma armadilha

**C1 — O E3 destrói o sinal.** `e3_serialization` emite allowlist fechada, e
`Transaction` não tem campo `tipo`. Logo `tipo` e `parcela` que o E2 já produz **nunca
chegam ao E4**, e toda fatura é classificada por inferência de sinal.

**C2 — De-leak ingênuo DOBRA a despesa.** `scripts/e2/banks/santander.py` grava
`"tipo"` com vocabulário `{compra, pagamento, estorno, iof}` — nenhum canônico.
Propagar `tipo` cru faz `"estorno"` falhar o teste `tipo == "credito"` e cair em
`_classify_debito`, que aplica `abs()`: **a despesa dobra**. Defeito **latente** — hoje
inalcançável só porque C1 mata o campo. Quem consertar C1 sem normalizar o vocabulário
introduz C2 no mesmo commit.

## Decisão

**D1 — Estorno é despesa assinada negativa, na categoria original, no mês do estorno.**
`kind="despesa"`, `valor` negativo, categoria pela hierarquia da [[ADR-242]],
`categorization_origin="estorno"`. Estorno é a **anulação de um evento de consumo**, não
um evento de renda — mesma forma de raciocínio da [[ADR-333]] (aporte não é consumo) e
da [[ADR-351]] (retorno de principal não é receita recorrente).

**D2 — `receita_estorno` one-time é rejeitada.** Ela tira do recorrente e **mantém**
`receita_total` e `despesa_total` inflados: não restaura a conservação, e cria um balde
de "receita" que não é renda.

**D3 — Não existe identificador forte do par, e a regra não precisa dele.** Parear com
uma linha só seria necessário para **aniquilar** o par — e aniquilar é errado por motivo
independente: compra em janeiro com estorno em março exigiria reescrever janeiro, contra
"mês fechado imutável" ([[ADR-186]]/[[ADR-188]]). *"Categoria original"* não exige o
par: exige a tabela de keywords de **despesa** em vez da de receita. `ESTORNO MAGAZINE
XYZ` resolve `MAGAZINE → lazer` sem conhecer a compra. **O identificador que falta não é
da transação-par; é do balde.**

**D4 — O discriminador é positivo, nunca o sinal em fatura.** `tipo` explícito do E2
normalizado ao vocabulário canônico `{credito, debito, estorno, pagamento}`, ou regex de
descrição. Medido: numa fatura, a linha negativa é dominada por **pagamento**, não por
estorno — roteá-la para despesa negativa zeraria a fatura contra o próprio pagamento
(`despesa_total` cai de 96.000 para 0).

**D5 — Sem categoria resolvida ⇒ `nao_identificado` negativo.** A residual já tem casa:
a [[ADR-425]] §D1 a tira de todo numerador que prescreve e a §D2 a declara em
`base_pontuais.excluidos`.

**D6 — Forward-only, sem backfill.** `f` muda, não `f(x)`; `pipeline_artifacts` é
imutável por run. Sem bump de artefato E4 (o shape não muda). A chave nova é no **E3**
(`transacoes[].tipo`), fora de `required`, e a leitura da [[ADR-390]] §D2 vale ali:
ausência = artefato pré-conserto. Backfill seria impossível de qualquer forma — o E3
antigo não tem o campo. Re-run é o caminho, e ele invalida cache do parecer
([[ADR-173]]) e das section summaries ([[ADR-144]]).

## Nenhum witness existente pega isto — e é o ponto

Os quatro invariantes de conservação **passam** sobre o payload defeituoso
(`−28.000 − 48.000 = −76.000` fecha). Eles são identidades algébricas sobre o **mesmo**
payload: detectam total que não fecha com as partes, nunca lançamento no balde errado.
Reforçá-los não adianta — precisa de witness de outra natureza.

Três asserções, cents int, tolerância zero, **nos dois regimes** (fatura e conta):

- **G1 (anulação)** — o mundo com compra+estorno ≡ o mundo **sem o par** (cenário A,
  não B) nos 7 campos.
- **G2 (não-vacuidade)** — a compra sozinha move os 7. Sem isto, G1 passa sobre fixture
  vazia.
- **G3 (não-inércia)** — `PAGAMENTO EFETUADO` na mesma fatura **não** entra em
  `despesas_por_categoria`. Sem isto, G1 é satisfeito pelo **remédio errado** (mandar
  toda linha negativa de fatura para despesa negativa).

Mais um gate estrutural que pega a classe inteira: `receita_total ≥ 0 ∧ ∀ por_fonte[*] ≥ 0`.
Reprova hoje.

## Faseamento

- **F1 — sinal primeiro, zero linha de produção.** Fixture E3 com os 5 cenários +
  G1 sob `@pytest.mark.xfail(strict=True)`. Verde no CI, e o `strict` **falha** no dia
  em que o conserto entrar sem remover o xfail: o xfail vira o gate.
- **F2 — o conserto, um PR.** E3 de-leak **normalizado** + ramo `estorno` em
  `_classify_one` antes do ramo crédito + membro `estorno` em `VeredictoPontual` + os
  três `abs(tx.valor)` de `consumo_pontuais.py`. As metades **não são separáveis** (C2).
- **F3 — opcional.** `EstornoPairCrossChecker` measure-only em E3, protocolo da
  [[ADR-350]], só se alguém quiser o lineage do par.

**Coordenação:** a [[A40.l102]] é dona de `VeredictoPontual` e de `consumo_pontuais.py`
— F2 invade o escopo dela em 2 pontos. `python3 dev/lane_pickup.py A40.l102` antes de
abrir lane.

## Consequências

- `despesas.dados[*].valor` deixa de ser `≥ 0`. Consumidores a auditar, **enumeráveis**:
  `_relevantes` (o estorno viraria pontual negativo), os três `abs()` de
  `consumo_pontuais.py`, `_build_chart_datasets` e `_compute_essencial_mensal`.
- **Nenhum golden E3 tem estorno**, então o conserto passaria **verde e mudo** por todos
  eles: `golden_diff` daria zero `value_delta` e o manifesto seguiria `[]`. A fixture
  nova é **bloqueante** — mesma classe da [[A40.l95]], onde nenhum golden tinha
  `imoveis_geradores > 0`.
