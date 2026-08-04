---
id: A42.l2
type: lane
title: "Parsers line-oriented: âncora de fidelidade e supressão que vira verdict do gate"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l2-ancora-fidelidade-e-verdict-do-gate
adrs:
  - "[[ADR-342]]"
  - "[[ADR-090]]"
depends_on:
  - "[[A42.l3]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
---

# A42.l2 — `ancora-fidelidade-e-verdict-do-gate` (PC08, PC09, PC10, PC14, PC15, PC16)

> **Origem:** [[PARSE-CERTIFY-active]] §r2 2026-08-04 — PC09 (Crítico), PC08, PC10
> (ambos Alto), PC14, PC15, PC16 · [[PIPELINE-REVIEWS-active]] §r4 — RV4-07 (Alto).
> Todos com evidência verificada; PC10 foi provado por **mutação em runtime**.

## Problema

Três defeitos que se compõem num único ponto cego:

1. **Sem âncora de fidelidade.** Três parsers de caminho line-oriented — 29% do
   corpus — nunca emitem a contagem de linhas de origem. Em formato line-oriented
   essa contagem é **exata** (não é heurística de texto como no caminho PDF), e é a
   única medida que discrimina *o parser perdeu linha* de *a fonte não fecha*.
2. **Gate suprimido por conclusão do parser.** Quando a cadeia de âncoras diárias
   quebra em dois ou mais pontos, o parser **retira a própria verificabilidade** e o
   gate obedece. Isso inverte a polaridade: mais evidência de perda produz menos
   sinal. É regressão de **forma** contra a emenda de 2026-07-23 da [[ADR-342]], que
   rejeitou nominalmente a flag-conclusão — "o parser emitia uma conclusão e o gate
   acreditava, a mesma classe de erro que este gate existe para matar" — sem que a
   ADR fosse emendada.
3. **Três descartes silenciosos vivos** no laço de linha (linha curta, data que não
   casa, valor ausente) e um risco **declarado em prosa e nunca gateado** noutro
   parser ("uma linha malformada some com o total junto").

Com (1) ausente e (2) suprimindo, o fail-safe anti-silêncio não tem por onde
disparar: o caminho fica com **zero** âncora de completude — e é onde está o maior
volume de lançamentos do corpus.

Compõe-se ainda: o token de tipo do lançamento que a fonte fornece é reconhecido e
depois descartado, deixando um evento patrimonial cair em não-identificado (RV4-07);
o caminho PDF do mesmo banco deixa candidatas datadas não convertidas com **delta
constante** em documentos de tamanhos muito diferentes — assinatura sistemática
(PC15); e o classificador que alimenta o gate compara **float** com tolerância de
centavos, contra [[ADR-090]] (PC16).

**Por que é uma lane e não seis:** todos escrevem o mesmo conjunto de arquivos.
Seis lanes serializariam ou dariam merge hell. Precedente de lane multi-PR sobre
hotspot: [[A40.l2]] (5 PRs).

## Decisão

Seis PRs em ordem obrigatória. **Invertê-la produz fix sem detecção.**

1. **Âncora de fidelidade** nos três parsers line-oriented + gate
   `linhas_de_origem > emitidas ⇒ escalação HARD`. Contar no filtro **mais precoce**
   (o campo de data casa) **antes** do descarte por linha curta — contar depois
   herda o próprio drop que se quer detectar. **Não** reusar o contador de texto do
   caminho PDF: em line-oriented a contagem é exata, e exato supera heurístico.
2. **Supressão vira verdict do gate**, computado sobre observações e não sobre
   conclusão do parser. Fechamento independente dos extremos igual a zero é
   **suficiente para afirmar** verificabilidade; fechamento diferente de zero **não
   é suficiente para escalar** — âncora terminal defasada produz falso-positivo, e
   escalar exclui a chave inteira do razão, o que é pior que hoje.

   **O terceiro estado é representado por valor, não por ausência** (correção do
   `senior-cto`, 2026-08-04). A primeira versão desta lane pedia "código de aviso
   próprio"; isso deixaria o estado legível como *"marca de escalação ausente"* —
   indistinguível de "extraiu e fechou", e todo leitor novo herdaria o **default
   otimista**. É o mesmo defeito de sentinela indecidível que a [[A42.l5]] está
   consertando (LC04): esta lane criaria um LC04 novo enquanto a l5 fecha o antigo.
   Portanto: **enum fechado** de verificabilidade no payload E2 (`provada` /
   `nao_verificavel(motivo)` / `falhou`), validado no boundary, `additionalProperties`
   fechado, e schema em modo estrito. O code de aviso continua existindo — mas como
   telemetria do motivo, não como o portador do estado. E **não** reusar o code que já
   serve três ramos.

   A lane declara também se o **piso de materialidade** ([[ADR-344]]) se aplica a esta
   classe. Hoje a supressão retorna **antes** do cálculo do gap, então a classe nunca
   chega ao piso; com o gate computado sobre observações, um gap material passa a cair no
   piso e **escalaria** — contradizendo a assimetria decidida acima. Ambiguidade no ponto
   exato onde a materialidade importa; resolver na ADR, não no PR.
3. **Dormência exige o par:** zero candidatas **e** saldo presente. Hoje um export
   sem nenhuma linha datada não escala por **acidente de limiar de tamanho**, não por
   decisão. Armadilha do fix óbvio: tratar zero candidatas como dormência converte
   acidente em silêncio **justificado** — pior que o estado atual.
4. **Preservar o token de tipo** do lançamento até o razão (RV4-07).
5. **Delta constante do caminho PDF** (PC15): identificar o que são as candidatas
   não convertidas. Escala honesto hoje, logo não é silêncio — o custo é LLM
   recorrente e a exposição ao modo sem LLM da [[A42.l8]].
6. **Cents e tolerância zero** no classificador (PC16) — cauda, ver DoD.

**Emenda datada à [[ADR-342]]**, não ADR nova: é a mesma decisão com o eixo
refinado. Heading **sem wikilink** e `amended_at` no frontmatter, no mesmo commit.
Registrar também, na [[ADR-345]] (`Roadmap`), que o §r2 é o gatilho de retomada
declarado dela — docs-only; promover a nota exige design ([[ADR-358]]) e está fora
desta lane.

## Critério de aceite

- **Piso de DoD = PRs 1 e 2.** Se a lane travar, queremos detecção em `main`, não
  nada. PRs 3–6 são trailing declarado, e **PC16 é cauda** (P3 não pertence ao DoD
  de uma lane P1).
- **Prova por mutação, por parser:** remover uma linha de dados da fixture faz o
  gate disparar em **3 de 3** parsers. Hoje é 0 de 3.
- **Fixture que exercita o mecanismo, não o resultado:** o golden que hoje justifica
  a supressão tem fechamento zero, então a asserção de não-escalação sobrevive à
  remoção integral do mecanismo (provado por mutação no §r2). São obrigatórias duas
  fixtures novas: âncora **terminal** defasada (fechamento diferente de zero com
  todas as linhas presentes) e perda de linha (âncora de fidelidade maior que
  emitidas ⇒ escalação HARD). Nenhuma asserção nova pode sobreviver à remoção do
  mecanismo que ela nomeia.
- `--compare` do harness verde, com rebaseline **manifestado** (disciplina de
  `dev/golden_diff.py`). **A cláusula de ratchet que aceita código de aviso estruturado
  como alternativa honesta à escalação é entregue pela [[A42.l3]]**, que é dona de
  `dev/certify_parse_local.py` — esta lane **consome** e não edita esse arquivo. Colisão
  declarada; as duas são da mesma onda e não são disjuntas.
- Zero chamada de LLM adicional no corpus, exceto o export sem linha datada.
- Validação de schema em modo estrito sobre o corpus com os campos novos declarados.
