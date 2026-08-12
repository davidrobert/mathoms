---
id: A40.l53
type: lane
title: "Gate visual de seções está cego: S2 varia 5–6% entre tentativas do mesmo commit e `main` puro reprova em 6 baselines"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l53-gate-visual-secoes-cego
adrs:
  - "[[ADR-210]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/frontend
  - area/ci
---

# A40.l53 — `gate-visual-secoes-cego`

> **Aberta em 2026-08-12**, no fecho da [[A40.l45]] (decisão do dono: os
> follow-ups sem dono viram lanes na A40). **Vizinha, não duplicata, da
> [[A40.l46]] item 1**: aquela cobre o job `frontend-print-visual` (página 1 do
> PDF, baseline única); esta cobre o job `Frontend visual snapshots`
> (`sections.snapshots.visual.spec.ts`, 28 baselines por seção × tema).

## Problema

O job `Frontend visual snapshots` não distingue regressão de ruído. São dois
defeitos independentes, medidos na execução da [[A40.l45]] (PR #1387):

### 1. O snapshot da S2 é flaky no próprio runner

As **três tentativas do mesmo job** — mesmo commit, mesmo runner Linux — diferem
**entre si** em 5,1%, 5,6% e 6,3% (S2-dark, run 31576243325). A tolerância do
spec é `maxDiffPixelRatio: 0.025`. O snapshot reprova sozinho, sempre, em
qualquer PR que aplique o label `visual`.

Causa provável, medida: `setupReport` captura após `waitForTimeout(500)`, e o
conteúdo do canvas do Chart.js só estabiliza entre **~900ms e ~1200ms** (hash de
`getImageData` em instantes crescentes). `animations: "disabled"` do Playwright
cobre CSS, não canvas.

**Tentativa que JÁ FALHOU** (não repetir): trocar o timeout por espera até o
hash do canvas estabilizar — o hash amostrado estabiliza antes de o desenho
terminar; a variação intra-run persistiu. Candidato seguinte: desligar a
animação do Chart.js no ambiente de teste (opção de chart, não de Playwright).

### 2. `main` puro já reprova em 6 baselines

Controle rodado **duas vezes** (branch cortada de `origin/main` + dispatch com
`run_visual=true`): `S2` ×2, `S3` ×2, `APP_A-light` e `S-parecer-retido-dark`
falham em `main` sem nenhum diff de PR. O job é **label-only** ([[ADR-210]]
§camada 1), então PRs sem o label envelhecem as baselines em silêncio — mesma
mecânica que deixou a baseline de print sendo um crash por 4 meses.

Consequência prática: o job é **fail-open por ruído** — vermelho permanente que
todo autor aprende a ignorar. Na l45 ele escondeu uma regressão real minha
(S2-light a 9,9%) atrás do próprio ruído; só a triagem manual separou.

## Método de triagem que funcionou (usar até o fix)

Nunca comparar captura local × baseline (macOS × Linux domina o diff), nem
comparar PNGs por bytes. Comparar **`actual` × `actual` de dois runs no mesmo
runner** — o do PR e o de um controle cortado de `origin/main` — por pixel,
limiar ~8/255. Foi isso que provou que 5 das 6 falhas eram herdadas (0 px de
diferença) e uma era da lane.

## Escopo

1. **Matar a variação na fonte** — animação do Chart.js desligada (ou concluída
   de forma determinística) no ambiente de teste. Prova: 3 execuções do job no
   **mesmo commit** com diffs intra-run < 0,5% em todas as seções.
2. **Rebaseline das 6 baselines podres**, em runner Linux, **com os PNGs
   olhados** um a um antes do commit (a lição da baseline que era um error
   boundary) — só depois do item 1, senão congela um frame arbitrário.
3. Registrar em `TESTING.md` o método de triagem `actual`×`actual`.

## Critério de aceite

- [ ] 3 runs consecutivos do job `Frontend visual snapshots` no mesmo commit de
      `main`: 0 falhas, e nenhum par de tentativas difere > 0,5% em pixel.
- [ ] As 6 baselines regeneradas têm justificativa individual (o que mudou e por
      quê), com inspeção visual registrada no PR.
- [ ] Provado por mutação: uma mudança real de layout numa seção (ex.: retirar o
      `grid-cols-1` da [[A40.l45]]) deixa o job vermelho.
