---
id: MOC-sprint-a27
type: moc
title: "Sprint A27 — Data Lineage Onda 6 (conclusão): citação confiável do parecer, ponta a ponta"
aliases: ["A27", "Sprint A27"]
sprint_status: candidate
date: "2026-06-19"
theme: "data-lineage"
---

# Sprint A27 — Data Lineage Onda 6 (conclusão): citação confiável do parecer, ponta a ponta

> **Status:** `candidate` (rascunho 2026-06-19) — sucede [[MOC-sprint-a26]] (`current`).
> **Não vira `current` enquanto a A26 viver** — promoção só no PR que flippa A26→`done`
> + A27→`current` (gate `build_doc_index --check` proíbe dois MOCs `current`). 6ª e
> **última** janela do plano [[PLAN-data-lineage]]: encerra a **Onda 6** (cobertura de
> citação E5→E6) fechando a *raiz* que a A26 só contornou — o LLM para de autorar o
> número — e materializa a citação do parecer no **grafo de lineage**. Co-design
> 2026-06-19: `product-manager` (priorização/ondas/KR/corte) + `information-architect`
> (forma/frontmatter/MOC/wikilinks) + os 6 do co-design da [[ADR-296]].

## Tese

A A26 (consolidação) atingiu a propriedade que **protege o usuário** — "zero citação
errada publicada" — via enforcement per-item ([[ADR-295]]) e fecha o flip strict
([[A26.l2]]) com o gate **redefinido** ("0 falso publicado + budget de `needs_review`"),
sem depender da citação determinística. Mas o gate per-parecer continua em ~22%
`needs_review` (eval 1.8.0) porque **o LLM digita o número à mão** e faz duas escolhas
que precisam casar (número X, path Y) — divergem em ~22%/parecer (`wrong_pairing`). A
A27 fecha a **raiz**: o LLM emite `(claim sem número, evidencia_path, rótulo)` e o
pipeline renderiza o valor da folha — `value_mismatch` por transcrição vira impossível
por construção ([[ADR-296]]). Em paralelo, a citação verificada deixa de viver só em
`_meta.evidencia_verification` e passa a ser **edge de lineage por chave natural**
([[ADR-293]]), fazendo o reverse-lineage e o drill-down de produto responderem "de onde
veio este R$ do parecer?" — hoje a camada mais user-facing fica cega.

## Lanes nativas (co-design 2026-06-19)

| Lane | Slug | Status | Dep / Gate | ADR |
|---|---|---|---|---|
| [[A27.l1]] | `evidencia-lineage-edge` | planned | edge slices 1+3 ∥ [[A26.l9]]; slices 2+4 após o merge da l9 | [[ADR-293]] `Proposto` |

## Lanes executadas nesta janela (origem A26 — referência, sem migração de id)

> Padrão de forma (co-design `information-architect`, 2026-06-19): lane nasce ancorada na sprint
> de **origem** (`sprint:` = planejamento) e é referenciada por wikilink na janela de
> **execução**. `git mv`/renumeração quebraria `[[A26.l9]]`/`[[A26.l5]]` em cascata
> (MOC A26 + ADRs). O `status:` da lane reflete execução; o `sprint:`, a origem.

- **Must (núcleo — nunca cortar):** [[A26.l9]] `citacao-deterministica` ([[ADR-296]]
  `Proposto`) — decidida no co-design da A26, **executada A27/Onda 6**. É a única lane
  que fecha a raiz do gate strict que a A26 contornou. **Slice 0 (pré-requisito não
  opcional): ✅ entregue** ([#679](https://github.com/davidrobert/mathoms/pull/679)) —
  harness de eval paralelo promovido ao committed em
  [`dev/run_parecer_eval_parallel.py`](../../../dev/run_parecer_eval_parallel.py)
  (6 workers, ~13 min). O eval sequencial (~1,7h) sofria kill; sem ele a l9 não fecha
  seu critério de aceite (re-eval holdout). Resta só `ANTHROPIC_API_KEY` no ambiente.
- **Condicional (carry-over A26, só ativa se o gate de tráfego não fechar na janela
  A26):** [[A26.l5]] `m2-override-drop` ([[ADR-282]] `Proposto`, DESTRUTIVO
  IRREVERSÍVEL) — cortada da A26 sob gate apertado; executa A27 **somente** com G1/G2/G3
  + PITR confirmado + go/no-go do owner. **Herda o gate verbatim da A26** — não reescreve.

## Carry-overs condicionais — Regime B da A26 (só se gates não fecharem)

Não criar arquivo de lane A27 para estes — entram **só** se, na promoção da A27 a
`current`, a A26 ainda os tiver `blocked`. Herdam gate e id de origem:

- [[A26.l2]] `evidencia-flip-strict` — espera-se que **feche na A26** (gate redefinido,
  independe da l9). Carry-over improvável.
- [[A26.l3]] `drop-dedup-v1-shim` — M2-A reversível; baixo custo rodando dual-read.
- [[A26.l4]] `override-v2-on-instrumentacao` — habilita o gate da [[A26.l5]].

> **[[A26.l8]] `evidencia-value-mismatch` NÃO é carry-over A27.** É superseded pelo
> plano de ataque da [[A26.l9]] (`value_mismatch` → impossível por construção;
> `value_mismatch` → `pairing_mismatch`). Fecha na A26 como enforcement per-item
> reusável ([[ADR-295]]); não aparece como lane A27.

## Ordem de execução (paralelismo parcial recupera a serialização de contrato)

A [[A26.l9]] muda o contrato da âncora (`evidencia_path: str` → `ancoras:
[{path, rótulo, valor_renderizado}]`); a [[A27.l1]] serializa o **path de citação**.
Construir o edge sobre o contrato v1 e depois mergear a l9 = writer do edge aponta para
campo morto + retrabalho (mesmo padrão "F3-sobre-sujo" que o plano rejeitou). Mas nem
todo o edge depende do contrato:

- **edge slices 1+3 ∥ l9** — slice 1 (resolver chave natural a partir do path) e slice 3
  (coexistência com DELETE-por-produtor, retenção N=1) dependem da estrutura do E5
  (`top_ativos`/`alocacao_por_classe`) e do `lineage_edge_writer`, **não** da forma do
  contrato de citação. Rodam em paralelo com a l9.
- **edge slices 2+4 após o merge da l9** — slice 2 (emitir edge a partir do path de
  citação) e slice 4 (reverse-lineage/drill-down cobrem o parecer) travam até a l9
  cravar `ancoras[].path`.

## Precedência de corte (squeeze — de baixo para cima)

1. **Primeiro a cortar:** condicionais ([[A26.l5]] + Regime B A26) — "cortáveis sem dó";
   nunca forçar drop irreversível sob gate apertado.
2. **Depois:** edge slices 2+4 (reverse-lineage cobre parecer) — a citação fica confiável
   (l9) mesmo sem estar no grafo; o drill-down do parecer escorrega p/ A28 se preciso.
   Slices 1+3 entregam a fundação reutilizável.
3. **Nunca cortar:** [[A26.l9]] `citacao-deterministica` — é o motivo de existir da A27.

## KRs da janela

- **KR1** — `number_in_prose_violation` (contrato: o LLM nunca digita `R$` na prosa) **==
  0** sobre todas as gerações do holdout. Prova binária de que o contrato da [[ADR-296]]
  foi adotado. (l9) · **Status 2026-07-02 ([[ADR-304]]):** fix de prompt levou 61→7 (↓88%,
  mediana 0, densidade↑) — resíduo estocástico de ~4%. `==0` estrito é **enforcement**
  (espelha [[ADR-295]]), follow-up adiado p/ promoção da A27 + tráfego real.
- **KR2** — `anchor_section_incoherence` per-parecer **UB IC95 < 5%** (ground-truth =
  catálogo l1, automatizável) **E** densidade de âncoras **não regride** vs. baseline
  [[A26.l6]] (anti-sub-citação — senão o LLM "ganha" o KR citando menos). Baseline:
  22% `needs_review` no eval 1.8.0. (l9)
- **KR3** (= G6 do plano, verbatim) — edge `parecer_citation` **reproduzível cross-run**
  (chave natural resolve o ativo certo após reordenação de `top_ativos`) **E** coexiste
  com DELETE N=1 (E5→doc + E6→E5 sobrevivem); reverse-lineage responde "de onde veio este
  R$ do parecer?". (l1)

## Decisões herdadas (sem ADR nova)

- **[[ADR-296]]** `Proposto` (citação determinística, render value-from-path) — flippa
  `Decidido (A27)` no merge da [[A26.l9]]; emenda [[ADR-279]] §E registrada lá.
- **[[ADR-293]]** `Proposto` (citação como edge por chave natural) — flippa
  `Decidido (A27)` no merge da [[A27.l1]]. Gate de discovery **já RESOLVIDO**
  analiticamente — não recriar discovery.
- **[[ADR-295]]** `Decidido` (enforcement per-item) — **coexiste** com a l9 (máquina de
  decisão drop vs `needs_review`); a l9 só troca o sinal que a alimenta.
- **[[ADR-282]]** `Proposto` — flippa `Decidido` no merge da [[A26.l5]], se executada.
- **`phase:` dos ADRs (282/293/296) não é normalizado** até o merge da implementação —
  atualizado por ADR, no PR que flippa para `Decidido (A27)`.

- **Plano dono:** [[PLAN-data-lineage]] ([plan/DATA_LINEAGE/_README.md](../../plan/DATA_LINEAGE/_README.md)) §Onda 6 (linha 365 · gate G6).
- **Carry-overs de origem:** [[A26.l9]] ([[ADR-296]]) · [[A26.l5]] ([[ADR-282]] §Cutover) · [[A26.l2]]/[[A26.l3]]/[[A26.l4]] (Regime B, condicionais).
