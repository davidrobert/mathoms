---
id: A42.l9
type: lane
title: "Vocabulário do checksum de fatura: separar dívida acionável de teto estrutural"
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

> **Origem:** [[PARSE-CERTIFY-active]] §r2 2026-08-04 — PC12.

> **Depende de [[A42.l2]]**, que é dona do arquivo de validação e do schema de
> extração. Mesmos arquivos, ondas diferentes — serializar.

> **Correção de premissa (2026-08-04).** Uma versão anterior desta lane dizia que
> ela destravava o resíduo deferido de [[A39.l3]]/[[A39.l8]], travado na identidade do
> checksum de fatura. **Isso está errado e foi verificado:** a
> [[ADR-342]] §Emenda 2026-07-24 já decidiu a identidade (é **por seção**, com `escopo`
> declarado no schema) e já ligou os dois parsers — `parse_santander_unique` e o novo
> `parse_itau_fatura` — com o corpus real **fechando a cent e zero falso-fire**. A
> decisão de domínio **foi tomada**, com co-design de `financial-planner`. O texto de
> blocker que eu havia copiado é da §Deferido da A39, escrita em 2026-07-23 — **um dia
> antes** do fix aterrissar. Esta lane não destrava nada da A39; ela resolve PC12, que
> é um defeito próprio e posterior.

## Problema

O checksum de fatura **funciona** onde há total independente: a identidade por seção
está decidida e dois parsers estão ligados, fechando a cent. O defeito que resta não
é de wiring nem de domínio — é de **vocabulário**, e ele trava o *rollout* do gate.

O §r2 mediu: em **31 de 41** documentos de fatura do corpus, o total impresso **é a
soma das próprias linhas**. Um parser que o consumisse estaria comparando um número
com ele mesmo. O comentário de um dos parsers já declara isso em prosa — não faz
opt-in porque o checksum seria tautológico e "daria selo falso". Ligar o checksum ali
**violaria a [[ADR-342]]**, que proíbe check tautológico, e produziria exatamente o
falso-verde que a emenda de 2026-07-27 fechou.

O estado atual conflacia duas coisas incompatíveis sob o mesmo rótulo:

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
2. **Teto é veredito, não dívida.** Para esses 31, a resposta não é "descobrir o que o
   total inclui" (a identidade por seção já está decidida na [[ADR-342]] §Emenda
   2026-07-24) e sim "esta fonte não declara total independente algum" — o veredito
   correto é teto declarado. Nenhuma decisão de domínio nova é necessária.
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
- **Nenhuma alegação sobre resíduo da [[A39]]:** o opt-in dos dois parsers e a
  identidade por seção já estão entregues ([[ADR-342]] §Emenda 2026-07-24). Reivindicar
  aqui seria colher trabalho de outra sprint — o mesmo erro que o §Fora do sprint da
  [[A42]] existe para evitar.
