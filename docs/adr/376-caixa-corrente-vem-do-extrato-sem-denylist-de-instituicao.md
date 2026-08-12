---
id: ADR-376
type: adr
title: "Caixa corrente vem do último extrato reconciliado — sem denylist de instituição"
status: Proposto
phase: A40
date: "2026-08-11"
relates_to:
  - "[[ADR-238]]"
  - "[[ADR-245]]"
  - "[[ADR-346]]"
  - "[[ADR-089]]"
  - "[[ADR-097]]"
supersedes: []
superseded_by: []
aliases: ["ADR 376", "caixa canônico", "denylist investment_banks"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
---

# ADR-376 — Caixa corrente vem do último extrato reconciliado — sem denylist de instituição

## Contexto

O caixa da visão corrente (`_load_caixa_from_e3`,
[e5_analyzer_adapter.py:850-964](../../pipeline/domain/services/e5_analyzer_adapter.py))
exclui contas cujo `banco` esteja numa denylist hardcoded
(`_load_investment_banks`, linha 846):
`{"btg pactual", "rico", "picpay", "binance", "xp"}`. A intenção histórica era
evitar dupla contagem com posições de corretora no E4; o mecanismo, porém,
falha nos dois sentidos e foi medido no dogfood (run `ee124571`, 2026-08-11):

| Conta (E3) | `saldo_final` | Efeito da denylist |
|---|---|---|
| `picpay_extratoconta` (fim 2026-03-28) | R$ 53.756,56 | **some do bruto** — não há posição E4 PicPay que o contenha |
| `rico_extratoconta` (fim 2026-07-23) | R$ 35.365,24 | **some do bruto** — o report da Rico não traz o saldo em conta |
| `btgpactual_extratoconta` (fim 2026-03-29) | R$ 13.011,15 | **entra por acidente**: `"btg pactual"` (com espaço) nunca casa o código `btgpactual` |

Total suprimido: **R$ 89.121,80** (~2,25% do bruto). A assimetria é acidente de
string, não decisão. O teste que cobria o skip
(`test_load_caixa_skips_investment_banks`) usa `banco="BTG Pactual"` — com
espaço — compartilhando a crença errada do código: o filtro nunca foi
exercitado contra o código de catálogo real.

Duas vias tornam a denylist irrecuperável como config: a chave
`institutions.investment_banks` **nunca é servida** pelo override de DB —
`_institutions_override`
([pipeline_adapter.py:778-785](../../backend/app/services/pipeline/pipeline_adapter.py))
emite apenas `banco_canonical` — e nenhum investment report em produção emite
posição de saldo-em-conta ("cash-like") que justificasse o skip.

Co-design 2026-08-11: `financial-planner` (recência decide, conciliação
desempata; descarte só entre fontes que medem a mesma quantidade),
`senior-cto` (deletar o skip, não consertar a lista; presença-de-posição
como gatilho de skip cria não-monotonia — subir um report da corretora
**apagaria** saldo de conta do balanço), `data-engineer` (o guarda correto é
contra dupla contagem observável, não denylist por rótulo).

## Decisão

1. **Fonte canônica.** Na visão corrente, o caixa de cada conta vem
   exclusivamente do `saldo_final` do **último extrato reconciliado** (E3)
   daquela conta, contado **exatamente uma vez**. Recência decide; conciliação
   é o desempate — nunca o rótulo da instituição.
2. **A denylist morre.** `_investment_banks` e `_load_investment_banks` são
   removidos. Nenhuma conta é excluída do caixa por identidade do banco.
   A chave morta `institutions.investment_banks` entra no inventário de
   chaves órfãs (não é deletada em silêncio).
3. **Sem branch de descarte "cash-like".** Não existe produtor de posição
   cash-like no E4 hoje; escrever o consumidor criaria leitor de chave que
   ninguém emite. A premissa é vigiada por **invariante de conservação
   exclusiva** (gate, não código de produção): `caixa_total == Σ saldos
   elegíveis` **e** nenhum banco com extrato elegível aparece também como
   posição cash-like no E4. Se um produtor futuro emitir caixa em report, o
   gate acusa e a decisão de precedência é tomada aí (com produtor real).
4. **Exclusões nomeadas e observáveis.** As exclusões de domínio que
   permanecem (fatura, poupança, conta PJ, `saldo_final_unknown`) são cada
   uma uma razão tipada (dataclass com `.format()`, [[ADR-097]] D1) —
   nenhuma conta some do caixa sem deixar rastro estruturado.

## Consequências

- **O bruto do dogfood sobe R$ 89.121,80** (PicPay + Rico; Binance não tem
  extrato elegível). Rebaseline com manifesto (`dev/golden_diff.py`), causa
  nominal por linha, em commit isolado; o teste de conservação
  (`tests/test_e5_conservation_invariants.py`) não é editado no rebaseline.
- O card "Posição por Instituição e Moeda" passa a listar PicPay/Rico como
  linhas de extrato — coerente com o que o patrimônio conta.
- Propagação: bruto → líquido → investível → projeção de IF → composição.

## Deferimentos (datados, com dono)

- **2026-08-11 · Poupança e conta PJ no patrimônio corrente** — extrato de
  poupança é hoje excluído do caixa e não há consumidor que o leve ao bruto
  (medido: `bradesco_extratopoupanca` R$ 4.359,28 fora do PL). É decisão de
  domínio (poupança é caixa, reserva ou investimento?), não bug — dono:
  `financial-planner`; retomada junto da lane de frescor cross-pool.
- **2026-08-11 · Agência/conta estruturadas nos informes** — não existem em
  `e3_reconciled` nem em `saldoProduto` (`additionalProperties: false`);
  exigiria mudança de extração + prompt (dono: `prompt-engineer`).
