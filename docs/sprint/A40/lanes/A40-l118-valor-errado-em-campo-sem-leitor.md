---
id: A40.l118
type: lane
title: "Campo emitido sem consumidor pode carregar valor errado, e o gate de classe mede existência do leitor — nunca a corretude do número"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l118-valor-errado-em-campo-sem-leitor
owner: data-engineer
depends_on: []
adrs: ["[[ADR-416]]"]
tags: [type/lane, sprint/a40, status/open, priority/p2, area/pipeline, area/frontend]
---

# A40.l118 — `valor-errado-em-campo-sem-leitor`

> **Origem:** decisão de classe tomada em 2026-09-01 ao triar o `RR8-04` sob a §6.1 do
> [runbook da rodada unificada](../../../reference/runbooks/unified_certify_review.md).
> A lane **não** é a instância — é a classe que a instância revelou.

## O caso que a abriu, medido

`fluxo_caixa_enricher.py:592` tem `if v > 0:` e **descarta o mês negativo** ao somar a
janela de 12 meses por fonte. Reproduz **ao centavo** em três rodadas unificadas
consecutivas, em 1 de 12 fontes.

Ele ficou em `P3` por três rodadas — *"magnitude pequena"* — e a régua nova mostra que
`P3` e `P1` estão **os dois errados**:

| | medido |
|---|---|
| o campo embarca no payload publicado? | **sim** — `fluxo_caixa.por_fonte_detalhado`, 12 chaves |
| algo o renderiza? | **não** — o único hit no frontend é a **declaração de tipo** em `report-fluxo.ts:155` |
| o valor está errado? | **sim**, e reproduz |

⇒ `P2` **latente**: não falsifica nada hoje, e falsifica **no instante** em que alguém
ligar um leitor. E o tipo declarado é exatamente **como** alguém liga: quem for construir
o card encontra o campo pelo tipo, confia nele, e publica o número errado sem sinal.

## Por que é lane de classe, e não de instância

Consertar o `if v > 0:` custa uma linha e resolve **um** campo. A pergunta que fica sem
resposta é **quantos outros campos emitidos-sem-leitor carregam valor errado** — e hoje
nada responde:

- a [[A40.l88]] entregou gate de **existência de consumidor** (campo emitido tem quem o
  leia). Ele mede o **leitor**, nunca o **número**.
- o schema valida **forma** (tipo, obrigatoriedade), nunca invariante de valor.
- os cross-checks da rodada unificada comparam **entre stages**; campo sem leitor conserva
  perfeitamente o próprio erro.

Um campo sem leitor é o **pior lugar** para um valor errado: nenhuma superfície o contradiz,
nenhum usuário reclama, e nenhum gate o mede. Ele espera.

## Escopo

1. **Regra de agregador com sinal.** Agregador de janela/período **não descarta valor por
   sinal** silenciosamente: ou soma com sinal, ou declara a exclusão
   (`itens_excluidos` + motivo, no molde da [[ADR-431]]). Gate sobre a classe do padrão
   `if v > 0` / `if valor > 0` em somatório de janela.
2. **Inventário dos campos sem leitor, com o valor conferido.** Cruzar o payload publicado
   contra os consumidores reais (o substrato da [[A40.l88]] já enumera os dois lados) e,
   para cada campo **sem** leitor, aplicar a invariante de conservação que o campo declara.
   O inventário publica contagem e não-conferidos — nunca só "existe/não existe".
3. **Decisão por campo:** ligar o leitor, ou **remover** o campo. Campo que embarca sem
   leitor e sem decisão é dívida que cresce em silêncio (é a doutrina da [[A40.l88]],
   estendida do leitor para o valor).

## Critério de aceite

1. O `if v > 0:` de `fluxo_caixa_enricher.py:592` cai, com **contrafactual medido**: fixture
   com mês negativo reprova antes e passa depois, e o Δ publicado bate ao centavo.
2. Gate que reprova agregador de janela descartando valor por sinal sem declarar a exclusão.
   O gate nomeia o **ofensor por igualdade de conjunto**, não por whitelist derivada dos
   paths que ele mesmo vai testar.
3. Inventário publicado: `n_campos_sem_leitor` / `n_conferidos` / `n_com_valor_divergente`.
   **Zero conferidos ⇒ `INAPLICÁVEL`**, nunca ✅.
4. Cada campo sem leitor tem decisão escrita: leitor ligado, ou removido, ou deferimento
   datado com dono.

## Limite declarado

A prevalência **não está medida** — a evidência é **um** campo. Se o inventário do item 2
achar zero outros casos, a lane fecha com o item 1 entregue e o gate de classe de pé, e
isso **é** resultado: o gate impede a próxima instância, que é o que ele existe para fazer.
