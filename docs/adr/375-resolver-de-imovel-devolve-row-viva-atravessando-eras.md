---
id: ADR-375
type: adr
title: "Resolver de imóvel devolve row viva atravessando as eras do canonicalizador"
status: Proposto
phase: A40
date: "2026-08-11"
relates_to:
  - "[[ADR-215]]"
  - "[[ADR-225]]"
  - "[[ADR-246]]"
  - "[[ADR-265]]"
  - "[[ADR-282]]"
  - "[[ADR-324]]"
  - "[[ADR-376]]"
supersedes:
  - "[[ADR-334]]"
superseded_by: []
aliases: ["ADR 375", "identidade de imovel cross-era", "cascata descricao_sample"]
tags:
  - type/adr
  - status/proposto
  - area/persistence
  - area/pipeline
---

# ADR-375 — Resolver de imóvel atravessa a supersessão em vez de ignorá-la

> Origem: investigação de 2026-08-11 sobre imóveis repetidos na tela de
> Configurações do workspace de dogfood. Fecha o write-path; o passivo já
> acumulado é colapsado pela [[ADR-376]].

## Contexto

A tela de Configurações lista as `property_identity` vivas. No dogfood eram 11
para 6 imóveis reais (clusters de 4, 2 e 2). Um dos overrides do usuário estava
preso numa row que os runs correntes não resolvem mais, e o relatório exibia esse
imóvel como linha de valor zero enquanto o imóvel de verdade constava como
"classificação pendente".

Duas causas estruturais, ambas no write-path:

1. O resolver era o único read-site de `PropertyIdentity` que **nunca mencionava
   `superseded_at`**. As três queries do cascade podiam devolver uma row já
   supersedida, e nenhuma seguia `superseded_by_id`.
2. Quando `canonicalize()` devolve `None`, `_cascade_match` retornava `None` sem
   tentar match algum, e o resolver **inseria row nova a cada run**. Esse
   comportamento estava testado como correto, apoiado na [[ADR-225]] §3 ("o
   backfill cuida disso pós-cutover") — mas o backfill era revertido pelo run
   seguinte ([[ADR-376]]).

### Tabela de eras

O canonicalizador mudou de saída três vezes, e cada mudança deixou vivas as rows
gravadas na forma anterior. O corpus do gate deriva desta tabela, não da memória
de quem escreve.

| Era | Forma gravada em `endereco_canonical` | Mecanismo | Fechada por |
| --- | --- | --- | --- |
| 1 | `<dígito> <dígito>` (prefixo monetário lido como logradouro) | regex de via casava o `r` de um prefixo de moeda; e o predicado do resolver incluía `titular_key`, que variava de grafia entre declarações | `9c0047a1` (fix-B1) |
| 2 | `None` | descrição sem prefixo de via deixa de canonicalizar, e canonical ausente vira insert por run | aberta até esta ADR |
| 3 | `mat:<N>` / `qa:<N>` / `iptu:<N>` | cascata de identificadores fortes ([[ADR-225]]) — forma nova que não casa as anteriores | `feeb977e` |
| 4 | `<via> <número>` | forma corrente | — |

## Decisão

1. **A supersessão resolve-se por travessia, nunca por filtro.** O cascade carrega
   vivas e supersedidas e segue `superseded_by_id` até a row viva. Filtrar seria
   pior que não filtrar: logo após um sweep, a perdedora (que é quem casa o
   input) sumiria do cascade, a vencedora tem outra descrição-fonte, nenhum nível
   casaria, e o resolver voltaria a inserir a cada run.
2. **O follow fica dentro do loop de candidatos de cada nível**, não no exit do
   cascade. Com `LIMIT 1` + follow no exit, um candidato de ponteiro órfão faria o
   nível "acertar" com resultado nulo e cair no insert.
3. **Ponteiro órfão pula o candidato.** `superseded_at` setado com
   `superseded_by_id` nulo (a vencedora foi deletada, `ON DELETE SET NULL`)
   significa row morta sem sucessora; devolvê-la seria ressuscitar — a classe da
   [[ADR-282]] §5. Idem para ciclo e cadeia mais funda que o cap.
4. **Quarto nível do cascade: amostra bruta byte-exata.** Quando o lookup não tem
   canonical, casa por `descricao_sample` idêntica dentro de
   `(workspace_id, codigo_rfb)`. Byte-exato de propósito: normalizar criaria uma
   segunda função de identidade competindo com `canonicalize()`, que é a classe de
   bug sendo fechada. `titular_key` fica fora do predicado — incluí-lo foi o
   mecanismo da era 1. Substitui o passe fuzzy de low-confidence que a
   [[ADR-225]] §3 deixou de fora.
5. **`descricao_sample` é a descrição-fonte íntegra da primeira observação.**
   Apesar do nome, não é amostra nem truncagem, e passa a ser load-bearing para
   identidade. Gate anti-truncagem no lugar; o rename da coluna fica para depois,
   porque renomear junto com mudar semântica destrói a capacidade de bisect.
6. **Sem índice único parcial.** `UNIQUE(workspace_id, codigo_rfb,
   endereco_canonical)` codificaria como invariante uma proposição falsa: a
   normalização remove o complemento, então duas unidades distintas do mesmo
   prédio produzem canonical idêntico legitimamente. O índice faria o INSERT do
   segundo apartamento real estourar dentro do E1.5c — perda de dado por
   constraint, pior que a duplicata que ele previne.
7. **O canonical recomputado não é persistido nem vira nível do cascade.**
   Recomputar no match é migração implícita a cada run e **flipa a identidade**:
   sob `ORDER BY created_at ASC`, a row mais antiga passaria a vencer e a que
   detém o valor do baseline viraria zumbi. Recomputar é insumo de eleição
   in-memory no sweep ([[ADR-376]]), só.

## Disposição da [[ADR-334]]

A ADR-334 (`Proposto`, 2026-07-14) mediu o mesmo corpus e chegou à mesma
constatação — `canonicalize(descricao_sample)` devolve chave para 11/11 rows
vivas e colapsa nos 6 imóveis reais. A medição foi **refeita em 2026-08-11 e
confirmada**. O que muda é o remédio:

- §Decisão 1 (derivar a chave inline no read-path) — **adotada em parte**: a
  derivação é insumo de eleição do sweep, não do read-path. Derivar a cada
  leitura mascararia a duplicata em 5 read-sites em vez de corrigir o dado uma vez.
- §Decisão 2 (backfillar a coluna) — **rejeitada** pela Decisão 7 acima.
- §Decisão 3 (invariante `imoveis ∩ excluded == ∅`) — **não supersedida**, segue
  vigente e não aplicada.
- §Decisão 4 (endereço só como nível da cascata) — supersedida pela Decisão 4.

## Consequências

- O quarto nível é **piso para a classe futura, não o fix do passivo**: ele só
  dispara quando `canonicalize()` devolve `None`, o que hoje não acontece em
  nenhuma das rows vivas do dogfood. Quem colapsa o passado é o sweep.
- O nível de amostra bruta só casa quando a string-fonte se repete byte-idêntica
  entre anos. Se a extração variar uma vírgula, insere row nova — e a próxima
  duplicata dessa forma **não** é regressão deste fix.
- Rows envenenadas de eras antigas continuam candidatas no nível fuzzy, então
  candidatas vivas são ordenadas antes das supersedidas e o log distingue o hit
  que veio por travessia.
- [[ADR-215]] §5 ("heurística fuzzy é assist, nunca decide sozinha") governa a
  **sugestão de UI**, não o dedup do pipeline — a [[ADR-265]] já pusera fuzzy na
  cascata automática.
- [[ADR-225]] §2 item 3 (reconciliation read pós-insert contra corrida) **nunca
  foi implementada** e o gate que ela cita não existe no repo. Fica revogada pela
  emenda datada, não deferida.

## Critério de aceite

- **Completude** — nenhuma query do resolver filtra `superseded_at`; a travessia é
  função pura com cap, guard de ciclo e semântica de órfão testados sem DB.
- **Corretude** — para cada forma da tabela de eras, seedada como row viva, o
  resolver a alcança direta ou pelo ponteiro. Com o desenho de filtro, 6 dos 19
  casos caem.
- **Consistência** — resolver duas vezes o mesmo lookup sem canonical devolve o
  mesmo `property_id`; descrição vazia nunca casa outra vazia.
- **Precisão** — descrição maior que 255 chars sobrevive sem truncagem.
