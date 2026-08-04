---
id: A42.l9
type: lane
title: "Identidade do checksum de fatura: separar dívida acionável de teto estrutural"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l9-identidade-do-checksum-de-fatura
adrs:
  - "[[ADR-342]]"
depends_on:
  - "[[A42.l2]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
---

# A42.l9 — `identidade-do-checksum-de-fatura` (PC12 + resíduo deferido da A39)

> **Origem:** [[PARSE-CERTIFY-active]] §r2 2026-08-04 — PC12 · adota o resíduo
> deferido de [[A39.l3]] (opt-in do parser) e [[A39.l8]] (parser determinístico).

> **Depende de [[A42.l2]]**, que é dona do arquivo de validação e do schema de
> extração. Mesmos arquivos, ondas diferentes — serializar.

## Problema

A [[A39]] deferiu duas frentes com o mesmo blocker declarado: a soma dos lançamentos
**não fechava contra o total impresso em nenhuma** das faturas reais testadas, e a
decisão de domínio ("o que o total impresso inclui") ficou pendente. Sem ela, o
opt-in seria aviso permanente e um parser novo seria não-verificável.

**O §r2 destravou o blocker mudando a pergunta.** Em 31 de 41 documentos de fatura do
corpus, o total impresso **é a soma das próprias linhas** — o parser que o
consumisse estaria comparando um número com ele mesmo. O comentário de um dos
parsers já declara isso em prosa: não faz opt-in porque o checksum seria tautológico
e "daria selo falso". Ligar o checksum ali **violaria a [[ADR-342]]**, que proíbe
check tautológico, e produziria exatamente o falso-verde que a emenda de 2026-07-27
fechou.

Logo o defeito **não é falta de wiring** — é de **vocabulário**. O estado atual
conflacia duas coisas incompatíveis sob o mesmo rótulo:

- **dívida acionável** — o parser tem total independente disponível e não fez opt-in;
- **teto estrutural** — a fonte não declara total independente algum.

Consequência operacional: a condição de promoção do gate a modo estrito ("um sprint
de corpus verde por parser") é **inalcançável por construção** para esses 31
documentos. Não travou o gate — travou o *rollout* do gate, e ninguém sabia dizer se
31 era dívida ou era teto.

## Decisão

1. **Forma tripla no vocabulário**, com precedente direto na própria [[ADR-342]]
   (emenda de 2026-07-27, no caminho de investimento, que já distingue "checou e
   passou" de "não havia total"): separar `sem_opt_in` (dívida) de
   `sem_total_independente` (teto).
2. **A pergunta de domínio deixa de ser bloqueante.** Para os documentos de teto, a
   resposta não é "descobrir o que o total inclui" e sim "esta fonte não tem
   testemunha independente" — o veredito correto é teto declarado, não dívida aberta.
   A decisão de domínio segue **necessária apenas** para os documentos que **têm**
   total independente impresso, e aí é escopo de `financial-planner`.
3. **A âncora de completude correta para os 31 é a da [[A42.l2]]** — em fonte
   line-oriented com total derivado, "converti toda linha datada?" é o único check
   não-tautológico disponível. É por isso que esta lane depende dela e não o contrário.
4. **Não** ligar checksum tautológico em nenhum parser, em nenhuma circunstância,
   mesmo que isso mantenha a contagem de "verificados" mais baixa.

## Critério de aceite

- Todo documento de fatura recebe um dos três estados; **nenhum** documento de teto
  aparece como dívida aberta, e vice-versa.
- Grep prova que nenhum parser faz opt-in de checksum cujo total seja derivado das
  próprias linhas. Teste que **falha** se alguém religar um deles.
- A condição de promoção do gate a estrito é recalculada **apenas sobre a classe de
  dívida** — e passa a ser alcançável.
- O KR-A da sprint conta este resultado na linha `teto_estrutural`, **não** em
  `fidelidade_provada`: reclassificar vocabulário não é progresso de verificação e o
  KR foi desenhado para não deixar essa contagem escapar.
- A disposição do resíduo das [[A39.l3]] e [[A39.l8]] é declarada como fechada por
  esta lane no `_README` da [[A42]] — nenhum resíduo de sprint fechada fica sem destino.
