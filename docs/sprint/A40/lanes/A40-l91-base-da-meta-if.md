---
id: A40.l91
type: lane
title: "A meta de independência é composta pela fórmula bruta e consumida nos slots líquidos"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l91-base-da-meta-if
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-416]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l91 — `base-da-meta-if` (PV9-16)

> **Origem:** rodada unificada **U1** 2026-08-26 ([[ADR-416]]) ·
> [[PIPELINE-REVIEWS-active]] §r9 — **PV9-16** (Alto, P0).
> Cru + síntese: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

> **Muta E5 ⇒ zera o contador de 2 re-runs.** É a **cabeça** da janela única de rebaseline
> da onda 2: número errado com o maior peso do score, e não depende do catálogo de limiar.
> Ordem: esta → [[A40.l89]] → [[A40.l90]].

## O fato, medido (2026-08-26)

Três campos publicados fecham **ao centavo** a identidade da fórmula **bruta** documentada em
[FORMULAS.md](../../../reference/FORMULAS.md): a renda-alvo mensal, capitalizada pela taxa de
retirada, dá a meta publicada.

Mas os dois consumidores são as fórmulas **líquidas**: o gap é `meta − investível` e o
progresso é `investível ÷ meta` — as duas exigem descontar a renda passiva **observada**
(que o payload publica) antes de capitalizar.

Consequência aritmética entre campos já publicados, sem depender de nenhum balde: o
progresso sai **subdeclarado** e o gap **sobredeclarado**. E `progresso_if` carrega o
**maior peso do score**.

## O que a medição já descartou

- ~~"é defeito de balde ou de denominador amputado"~~ — **não**: a discrepância é entre
  campos já publicados e sobrevive a qualquer viés de base.
- **O que NÃO se afirma:** o valor corrigido do progresso. Se a meta for **declarada pelo
  dono** e não derivada, o número publicado é o frame da família e está certo — só que aí a
  coincidência ao centavo com a fórmula bruta precisa ser explicada.

## A pergunta que esta lane decide

**A meta é declarada ou derivada?** A medição de 1 comando está escrita no §Critério.

- **Declarada** ⇒ o defeito é de **rótulo**: os slots líquidos consomem uma meta bruta sem
  dizer. Fix = nomear a base em cada consumidor.
- **Derivada** ⇒ o defeito é de **fórmula**: a composição usa L24 e o consumo usa L26–27.
  Fix = uma base só, com delta de golden declarado.

Co-design `financial-planner` (a decisão de domínio) antes de escrever o fix.

## Escopo

1. Medir se a meta é declarada ou derivada (comando no §Critério).
2. Aplicar o fix da leitura que a medição selecionar.
3. O card de independência **nomeia o denominador** que a meta financia — hoje o relatório
   publica três custos mensais diferentes e nenhuma superfície diz qual deles a meta cobre
   (achado irmão `RR5-09`, mesmo eixo, dono `product-designer`).

## Fora de escopo

- O editorial do ano de independência (dois anos concorrentes) → [[A40.l29]].
- A honestidade do cone e o percentil → [[A40.l25]].

## Critério de aceite

- A medição do item 1 está escrita no PR, com o comando que a reproduz.
- Se o veredito for "derivada": a identidade `gap = meta_líquida − investível` fecha ao
  centavo, e o delta de golden é declarado `↑`/`↓`/`=`.
- Se for "declarada": nenhuma superfície publica gap ou progresso sem nomear a base.
- Prova por mutação: alterar a renda passiva observada move o progresso na direção certa.
- Concluído = PR mergeado em `main` com CI verde.
