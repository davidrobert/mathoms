---
id: ADR-343
type: adr
title: "Estado durável da pipeline-review: baseline off-git + registro de defeito git-canônico"
status: Decidido
date: "2026-07-23"
amended_at: ["2026-08-05"]
relates_to:
  - "[[ADR-302]]"
  - "[[ADR-247]]"
  - "[[ADR-319]]"
  - "[[ADR-362]]"
aliases:
  - "ADR 343"
  - "pipeline-review registry"
  - "PIPELINE-REVIEWS-active"
  - "review baseline"
tags:
  - type/adr
  - status/decidido
  - area/docs
  - area/tooling
  - area/dados
---

# ADR-343 — Estado durável da pipeline-review

**Status:** Decidido · **Data:** 2026-07-23

> **Emenda 2026-08-05 (limite de garantia, não mudança de decisão):** o
> `--compare` desta ADR comparava dois runs **sem saber se rodaram no mesmo
> código**, e três dos seus predicados davam verde sem medir. O split de zona de
> confiança permanece intacto; o que muda é o contrato do snapshot e a correção
> de um falso-verde ativo. Ver §Emenda 2026-08-05.

> ADR >150 linhas: uma decisão (o split de zona de confiança) com dois mecanismos
> acoplados — registro editorial + baseline `--compare` — que repousam na mesma
> bifurcação sistêmico/instância. Split produziria peças órfãs; densidade legítima
> (precedente [[ADR-302]]).

## Contexto

A skill [[ADR-302]] `pipeline-review` roda o pipeline completo de um workspace e
produz uma revisão priorizada do relatório final. Hoje o entregável salva **só
em `_scratch/`** (efêmero, gitignored). Duas consequências:

1. **Achado se perde entre runs.** É o mesmo modo de falha que fundou a
   [[ADR-302]] — "um relatório efêmero se perdeu e teve de ser reconstruído da
   trilha". As rodadas de revisão de dogfood já vivem espalhadas em `_scratch/`
   e são re-descobertas a cada iteração.
2. **Não há baseline.** O dogfood é iterativo (fix → re-run → melhorou?), mas a
   skill gera um relatório fresco toda vez, sem forma de responder se o run
   regrediu vs. o anterior. A skill-irmã `parse-certify` já tem
   `--baseline`/`--compare` (baseline em `storage/<uuid>/certify/`); a
   `pipeline-review` não.

O precedente de registro é o `docs/_MOC/AUDITS-active.md` (registro editorial da
skill `audit-vault`): cobertura 100%, taxonomia de disposição, dedup semântico,
cadência anti-zumbi. **A diferença que domina a decisão:** achados de
`audit-vault` são sobre docs (PII-zero); achados de `pipeline-review` referenciam
dados reais de um workspace (patrimônio, fluxo, nomes) — PII. Um registro que
**acumula** achados por workspace vira dossiê re-identificável do household.

## Decisão

O estado durável da `pipeline-review` repousa sobre **um split de zona de
confiança**, ancorado numa bifurcação da natureza do achado.

### Bifurcação sistêmico ↔ instância

Todo achado da revisão é de uma de duas classes:

- **Sistêmico / defeito** — afirmação sobre o **pipeline** (código, contrato de
  stage, schema, render, prompt, metodologia). Ex.: "checksum X lê campo morto".
  **Recorre** entre runs/workspaces e é **PII-free por construção** (fala de
  código, não do household).
- **Instância / dado** — afirmação sobre os **números deste workspace neste
  run**. Ex.: "o documento Y do titular perdeu ~50% das transações". **Não
  recorre** (um run corrige ou é idiossincrático) e **carrega PII**.

O que se quer acumular e deduplicar (sistêmico) é exatamente o que é seguro
commitar; o que carrega PII (instância) é o que não recorre.

### Split de zona de confiança

| Camada | Onde | Conteúdo | Git? |
|---|---|---|---|
| Cru / insumo | `storage/<uuid>/reviews/<ts>-<run8>/` | `report_data.json` cru + `review_snapshot.json` + síntese crua | não (path proibido — mesma zona do DB/artifacts/`certify/`) |
| Citável / durável | `docs/_MOC/PIPELINE-REVIEWS-active.md` | só achados **sistêmicos/defeito**, deduplicados | sim (canônico, editorial) |

**Três destinos por run** (espelha o split working/durável do `parse-certify`,
com um tier extra justificado pela assimetria de PII): `_scratch/` (working
durante o run) → `storage/<uuid>/reviews/…` (síntese crua durável, off-git) →
append da seção scrubbed em `docs/_MOC/PIPELINE-REVIEWS-active.md`.

### `PIPELINE-REVIEWS-active.md` (forma)

MOC editorial, molde 1:1 do `AUDITS-active.md` (a spec detalhada mora no próprio
arquivo): frontmatter mínimo `type: moc` (sem schema novo — `_MOC` é excluído de
`validate_frontmatter`; criar `note-moc.schema.json` migraria os 4 MOCs
existentes), fora de `_generated`, mas link-checado. Arquivo **único**, seções
`## rN — ws-<uuid8>-<data>`. Reusa a taxonomia de disposição; mantém a
**severidade própria da skill** (Crítico–Baixo + P0–P3), **não** a `DOC-*`
(ancorada em consequência-de-doc; `pipeline-review` é runtime).

**Garantia de commit-safe:** seção curada só com afirmações de defeito, keyed por
`(dimensão, evidência-âncora, regra)` — âncora = `campo.dot.path` ou
`arquivo:linha`, nunca um valor. A chave PII-free é necessária mas não suficiente:
o **título** também tem de ser defeito, não dado (hook de PII do pre-commit é
backstop, não garantia primária).

### `--compare` (contrato)

`collect_review_inputs.py` passa a emitir um `review_snapshot.json` PII-safe
(drift de valor como **%-band assinado**, nunca R$) + persiste o baseline cru em
`storage/<uuid>/reviews/<ts>-<run8>/`. "Regressão de relatório" tem **três
pernas**, porque CV sozinho é cego a drift de magnitude (CV2 passa mesmo se o
patrimônio despencar — bruto e composição caem juntos): **conservação** (transições
de CV `pass→fail` **e** `present→absent`), **drift de valor** (via `golden_diff`
sobre os dois `report_data.json` crus — a perna que CV não vê) e **saúde de
execução** (status, `transacoes_total`, seções, custo).

Princípios (a spec fica na SKILL/PR2): reusa **engines, não gates**
(`golden_diff.diff_golden` e `run_cross_validation`, nunca `check_manifest` — no
dogfood quer-se ver o número mexer); hard-fail só no conjunto de conservação
numérica + status + queda de `transacoes_total` + headline fora de banda, o resto
soft (`--strict`); e **suppressors** obrigatórios contra falso-fail — **tier
downgrade** (`skip_llm`/[[ADR-173]]) e **corpus cresceu** (ratchet só sobre o
subconjunto estável, como o `parse-certify`).

## Alternativas consideradas

### A — Só git-canônico (todos os achados, mesmo scrubbed)

**Rejeitada.** Com ~1 workspace de dogfood, o arquivo vira "os problemas de dados
do household X ao longo do tempo" — re-identificável. Aceitar achados de
instância no git é o risco de PII que a bifurcação existe para eliminar.

### B — Só off-git per-workspace (como o `parse-certify`)

**Rejeitada.** Elimina o julgamento de triagem, mas re-aceita o modo de falha que
fundou a [[ADR-302]]: relatório não-descobrível, perdido, re-reconstruído. O
precedente `parse-certify` não governa aqui: o artefato durável dele é um
*baseline de diff de dados* (PII-pesado, off-git correto); o da `pipeline-review`
é um *ledger triado de defeitos do pipeline* — que o loop inteiro precisa ver.

### C — Emendar a [[ADR-302]]

**Rejeitada.** A 302 é sobre `audit-vault`, já tem >150 linhas e 2 emendas. Um 3º
adendo sobre outra skill viola atomicidade ([[ADR-182]]). A decisão nova (split
de zona de confiança + bifurcação para PII) tem peso próprio.

## Consequências

### Positivas

- Achado de defeito sobrevive ao run e é descobrível/deduplicável — fecha o modo
  de falha de origem da [[ADR-302]] para a `pipeline-review`.
- `--compare` destrava o loop iterativo de dogfood (fix → re-run → regrediu?).
- Vault permanece PII-free por construção, não por confiança no scrub.
- Reuso de engines existentes (`golden_diff`, `run_cross_validation`) — zero
  duplicação de lógica de diff/conservação.

### Negativas

- A bifurcação exige julgamento na triagem ("defeito de código ou dado do
  workspace?") — custo humano recorrente, como os goldens.
- Um tier extra de persistência (`storage/<uuid>/reviews/`) vs. o `audit-vault`.
- Manter o snapshot PII-safe alinhado à evolução do view-model E5.

## Validação (critério de aceite — satisfeito no flip)

> **Flip 2026-07-23:** PR1 (docs) mergeado (#1044); PR2 implementa
> `build_snapshot`/`compare_reviews` em `dev/compare_reviews.py` + emissão em
> `collect_review_inputs.py`, com 11 testes cobrindo os critérios abaixo
> (`tests/dev/test_compare_reviews.py`, verdes) e smoke de CLI (exit 0/1/2).


- `docs/_MOC/PIPELINE-REVIEWS-active.md` criado; `check_doc_links` verde;
  `build_doc_index --check` sem diff em `_generated/`; `validate_frontmatter`
  verde (nenhum schema exigido).
- `--baseline` grava `review_snapshot.json` com **zero** literal monetário/CPF
  (grep limpo); `report_data.json` cru fica só na zona gitignored.
- `--compare` de um re-run idêntico sai 0 (sem falso-positivo por volátil/tier).
- `--compare` de um run `skip_llm=true` contra baseline premium sai 0 (suppressor
  de tier), reportando "tier downgrade".
- Regressão injetada (zerar 1 balde de composição ou 1 seção) → exit 1 com a
  linha `FAIL:` correta; run incremental que reusa narrativa (CV9/CV10 falham)
  **não** falsa-falha em modo default.
- Passo 5 da SKILL reescrito para os três destinos.

## Emenda 2026-08-05 — contrato do snapshot e falso-verde do supressor

Três defeitos medidos no próprio instrumento, todos da classe "dá verde sem
medir". Nenhum altera o split de zona de confiança; todos alteram o que o
`--compare` consegue afirmar.

### 1. Cache hit se passava por downgrade de tier (falso-verde ativo)

`_suppressors` ligava `tier_downgrade` quando o run atual tinha zero chamadas
LLM, e `tier_downgrade` faz `_parecer_regressions` retornar lista vazia. Parecer
servido do cache (TTL de 7 dias) tem zero chamadas e continua íntegro e
comparável ⇒ **toda regressão de parecer era descartada em silêncio**.

O predicado passa a exigir ausência de `cache_hit`, que entra no snapshot lido
de `_meta.cache_hit` do artefato do parecer — campo emitido desde sempre e sem
nenhum leitor até aqui.

### 2. O parecer não era run-scoped

O coletor buscava o parecer por `workspace_id` com `ORDER BY id DESC LIMIT 1`.
Run que não produziu parecer (tier free, `skip_llm`, falha do stage) carregava o
de um run **anterior**: o snapshot afirmava `status: ok` e o `--compare` media
run A contra run B. Passa a filtrar por `pipeline_run_id`.

### 3. O read-path era SQLite-only

`julianday()` e `needs_review = 1` quebram em Postgres, e a produção roda
Postgres ⇒ **nenhuma afirmação da review sobre produção era verificável**. A
duração passa a ser calculada em Python (helper `elapsed_minutes`, testado nos
dois dialetos) e o predicado booleano vira `IS TRUE`.

### 4. Contrato do snapshot: contexto não é supressor nem perna

O snapshot ganha `parecer.cache_hit` agora, e — quando a [[ADR-362]] aterrissar
— `executor_revision`, `escopo` e `ancestry` como chaves **top-level de
contexto**, explicitamente **fora** do `run_health`: os 9 campos de `run_health`
são todos consumidos por perna de regressão ou supressor, e um campo
não-comparável ali seria assumido comparável pelo próximo leitor.

Regras duras que saem daqui:

- **`executor_revision` jamais é supressor.** No loop de dogfood "o código
  mudou" é o caso quase sempre; supressor sempre-ligado troca este gate por
  verde vazio.
- **Nenhuma perna nova de regressão** por divergência de revisão. O amplificador
  "zero commits + drift ⇒ severidade sobe" foi **medido como dead code**: as três
  janelas reais entre rodadas consecutivas tiveram 52, 15 e 24 commits nos paths
  de cálculo. E a inferência seria inválida, porque config em DB move número
  monetário sem commit. Fica `NOTE:` que **nomeia a dimensão cega**.
- **`SCHEMA_VERSION` não é bumpado**; ganha **leitor**. Hoje tem zero leitores em
  código e nos testes — bump sem leitor é ritual. O leitor avisa em divergência e
  reusa o exit code 2 já reservado para "baseline inutilizável". Compat
  verificada: os três acessos não-guardados são todos a `base["run_health"]`, que
  existe em v1 ⇒ baseline antigo **degrada, não explode**.

### Dimensão cega declarada

A tabela de atribuição de drift tem uma dimensão sem observável: **config em
DB** (categorização, overrides, parâmetros fiscais, câmbio, metas, `date.today()`).
Enquanto ela for cega, **nenhuma conclusão de "não-determinismo" é válida** — o
veredito correto é `NOTE:`, nunca `FAIL:`.

## Referências

- [[ADR-302]] — classe skill (audit-vault); precedente de registro editorial.
- [[ADR-247]] — MD canônico, HTML derivado.
- [[ADR-319]] — sigilo/PII em docs versionados.
- [[ADR-173]] — hard-stop de budget LLM (fonte de tier downgrade).
- `docs/_MOC/AUDITS-active.md` — molde do registro.
