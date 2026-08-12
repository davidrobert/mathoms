---
id: ADR-380
type: adr
title: "Nenhum card afirma ausência a partir de falha de carregamento"
status: Decidido
phase: A40
date: "2026-08-12"
relates_to:
  - "[[ADR-357]]"
  - "[[ADR-224]]"
  - "[[ADR-365]]"
  - "[[ADR-129]]"
supersedes: []
superseded_by: []
aliases: ["ADR 380", "sem base ≠ zero", "indisponível ≠ vazio"]
tags:
  - type/adr
  - status/decidido
  - area/frontend
  - area/report
---

# ADR-380 — Nenhum card afirma ausência a partir de falha de carregamento

## Contexto

O card "Exposição Cambial" exibiu, para o workspace de dogfood, o badge
`0% sem exposição` e a frase **"Seu patrimônio está 100% denominado em real"**
— sobre um patrimônio com R$ 83.869,92 (6,45% do investível) em quatro contas
em USD e EUR. No mesmo relatório, o parecer do planejador dizia
`exposicao_cambial_pct=6.45%` e recomendava ampliar a exposição.

A causa imediata foi um endpoint que lia chave inexistente e devolvia zero
([[ADR-224]] §5; corrigido em 2026-08-12). Mas o zero só virou **mentira na
tela** por causa de um defeito de modelagem independente, que sobrevive a
qualquer correção de leitura:

1. `tier: "empty"` era emitido tanto para *"calculei e deu zero"* quanto para
   *"não consegui calcular"*. Um valor do enum de veredito carregava um estado
   que não é veredito.
2. O card cedia ao provedor read-time por ele **ter respondido**, não por ter
   dado. Uma resposta vazia substituía um valor correto já em mãos.
3. Um segundo caminho produzia contradição interna: com denominador zero e
   total positivo, o card renderizava o valor cheio ao lado de
   `0,0% · sub-alocado`.

O produto já decidiu esta regra uma vez, para o banner de qualidade de dados
([[ADR-357]], A40.l18: *"o desfecho gateia apenas a AFIRMAÇÃO positiva;
incompleto ≠ falso"*). Ela não havia sido propagada para os cards. Três
instâncias do mesmo mecanismo — banner, parecer, card — fazem classe.

## Decisão

**Frase categórica sobre a composição do patrimônio só pode ser emitida por um
cálculo que declarou ter base.** Ausência de base nunca é inferida de um valor
numérico igual a zero, e nunca compartilha o enum do veredito.

Amarras, porque a regra escrita não fecha classe sozinha:

1. **Campo irmão, não membro do enum.** O provedor declara `base_disponivel`
   (ou equivalente) ao lado de `tier`. Membro do enum permite que o consumidor
   esqueça no `default`; campo irmão obriga a decidir.
2. **Sem base, os campos de valor vêm `null`** — nunca `0`. Mesmo princípio do
   `MonetaryValue value={null}` → `—`: torna o zero falso *infabricável* no
   consumidor, em vez de proibido por convenção.
3. **Presença da chave, não veracidade do conteúdo.** A base é considerada
   ausente quando a chave esperada não existe no payload; lista vazia é dado
   legítimo. Foi a confusão entre as duas que produziu o silêncio.
4. **Precedência por dado, não por resposta.** Provedor read-time só substitui
   o valor materializado do relatório quando declara ter base.
5. **Degradar não é alarmar.** Quando o valor do relatório está correto e só a
   função interativa caiu, o card mostra o número e sinaliza no lugar onde o
   controle estaria — sem contaminar o contador de qualidade de dados, que mede
   pendências que afetam a *leitura* do relatório.

## Consequências

- Todo card com estado "vazio" precisa distinguir os três estados: sem base,
  zero medido, valor. O gate por card é barato — fixture "sem base" que asserta
  a **não-ocorrência** da frase categórica.
- Copy de empty state passa a ser auditável: uma frase que afirma composição
  ("100% em real", "sem dívidas", "nenhum seguro contratado") é um contrato com
  o leitor, e precisa de base declarada para ser emitida.
- O PDF herda o estado do fetch (Playwright espera `networkidle`), então um
  estado degradado **congela no documento que chega a terceiros**. Skeleton é
  proibido em card de relatório por esse motivo: vira retângulo cinza impresso.
- Não cobre divergência semântica com base válida (unidade, moeda, escala) nem
  chave presente sempre vazia. Para o primeiro caso, o gate é
  `dev/check_artifact_read_keys.py`; o segundo exige assert de não-trivialidade
  no golden.

## Alternativas consideradas

- **Adicionar `"indisponivel"` ao enum de `tier`.** Rejeitada: mantém o estado
  no vocabulário do veredito, e todo `switch (tier)` novo reintroduz a classe.
- **Silêncio total (não renderizar o card sem base).** Rejeitada: o usuário
  conclui que o produto não tem a função, e o card some do PDF sem explicação.
- **Alarmar sobre o número do relatório quando o read-time falha.** Rejeitada:
  o valor materializado está correto; desconfiar dele seria a mentira simétrica.
