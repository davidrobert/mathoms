---
id: ADR-334
type: adr
title: "Dedup de imóvel: read-path deriva a chave inline (não confia na coluna persistida)"
status: Proposto
date: "2026-07-14"
relates_to:
  - "[[ADR-246]]"
  - "[[ADR-271]]"
  - "[[ADR-225]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
---

# ADR-334 — Dedup de imóvel deriva a chave inline

> Cluster **G** (P1) da re-review dogfood 2026-07-13 · PLAN-dogfood-report-fix.
> **Destravada** pela auditoria empírica de 2026-07-14 (ver §Evidência), que **inverteu**
> a hipótese de causa-raiz.

## Contexto

`real_estate.excluded_properties` mostra 1 matrícula 4× ("Classificação pendente") e 2
imóveis simultaneamente em `imoveis` (ativo) **e** em `excluded`. Narrativa diz "6
imóveis", tabela tem 4. Um imóvel pode aparecer em várias declarações (co-declarado por
cônjuges + repetido ano a ano); cada ocorrência é uma row de `property_identity`. Deduplicar
exige uma chave de identidade estável.

## Evidência (auditoria read-only sobre o DB do dogfood, 2026-07-14)

A hipótese da verificação adversarial — "`_extract_matricula` provavelmente não casa o
fantasma" — foi **refutada** pela medição:

- **11 rows vivas** (`superseded_at IS NULL`) + 4 superseded.
- **Matrícula extraível em 11/11 (100%)** das rows vivas; `canonicalize()` (cascata
  via+número > matrícula > QA > IPTU, [[ADR-225]]) devolve chave para **100%**.
- As 11 rows colapsam em **6 chaves canônicas derivadas distintas** — que batem exatamente
  com os "6 imóveis" da narrativa (e com 6 matrículas distintas). **Deduplicar pela chave
  derivada produz o resultado correto.**
- Mas a **coluna persistida `endereco_canonical` está fragmentada: 9 distintas + 2 NULL.**
- O fantasma "1 matrícula 4×" é **um grupo de 4 rows** com a **mesma** matrícula e a
  **mesma** chave derivada — das quais **2 têm a coluna `endereco_canonical` NULL**. O
  read-path agrupa pela **coluna** (fragmentada/NULL), não pela chave derivada → não junta
  as 4 → elas vazam como a mesma casa 4×.

**Conclusão:** a extração **não** é o gargalo (é 100%). O bug é o read-path confiar na
**coluna persistida** (estilhaçada e às vezes NULL) em vez da **chave derivável do texto**.

## Decisão

1. **Read-path deriva a chave inline.** O passe de dedup/resolver deve agrupar por
   `canonicalize(descricao_sample)` (ou por uma coluna **backfilled** a partir dela), nunca
   pela coluna persistida crua que pode estar NULL/fragmentada. Isso já colapsaria 11→6 no
   dogfood.
2. **Backfill idempotente** da `endereco_canonical` para as rows onde está NULL/divergente
   de `canonicalize(descricao_sample)` — reconciliando coluna ↔ derivada.
3. **Invariante de render:** um imóvel **nunca** em `imoveis` (ativo) E em
   `excluded_properties` ao mesmo tempo. Aplicar na projeção E5 (`real_estate_e5_integration`).
4. **Sem fallback de endereço como justificativa primária** — a matrícula está presente em
   100% das rows vivas; a cascata `canonicalize()` já a cobre. Endereço permanece só como
   nível da cascata existente ([[ADR-225]]), não como novo mecanismo.

## Rationale

Medir mudou a direção: a proposta original ("identidade estruturada + fallback de endereço
porque a matrícula falta") atacava um problema **inexistente** — a matrícula não falta. O
defeito real é de **persistência/leitura** (coluna estilhaçada), não de extração. Derivar
inline é mais barato, não exige nova coluna nem migration de dados, e conserta justamente as
2 rows NULL que geram o fantasma. `codigo_rfb` é invariante imutável (não sofre upgrade
in-place, [[ADR-225]]).

## Alternativas consideradas

- **Nova chave estruturada + fallback de endereço (proposta original).** Rejeitada: a
  auditoria mostrou matrícula 100% presente e `canonicalize()` já correto (6 chaves) — a
  chave não é o problema.
- **Backfill da coluna sem mudar o read-path.** Insuficiente sozinho: sem derivar inline, a
  próxima row com coluna NULL reintroduz o fantasma. Backfill é reconciliação, derivação
  inline é a defesa.

## Consequências

- Bump: nenhum de versão de payload; se houver coluna nova de reconciliação, migration
  Alembic como head único (não toca Parecer/Score/Narrativa/Schema).
- O número de imóveis no relatório passa a 6 (correto); o contraditório "ativo E excluído"
  desaparece.

## Critério de aceite (4 lentes)

- **Completude** — read-path de dedup não lê `endereco_canonical` cru sem fallback para
  `canonicalize(descricao_sample)`; `rg` cobre resolver + projeção E5.
- **Corretude** — golden red-before-green: fixture com um grupo de rows de mesma matrícula,
  ≥1 com coluna NULL, colapsa de N→1; "6 imóveis" bate lista renderizada.
- **Consistência** — invariante testável: interseção `imoveis ∩ excluded == ∅`.
- **Precisão** — chave derivada == chave persistida pós-backfill (reconciliação verificada);
  `codigo_rfb` inalterado.
