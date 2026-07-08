---
id: A34.l19
type: lane
title: "Freeze de merges + deletar 85 branches agent/*"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: freeze-merges-delete-agent-branches
adrs: ["[[ADR-315]]"]
depends_on: ["[[A34.l18]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/ci
---

# A34.l19 — `freeze-merges-delete-agent-branches` (W3 · Rewrite)

## Problema

O rewrite de histórico da [[A34.l18]] (`git-filter-repo` sobre clone `--mirror`)
reescreve **todo** SHA de `origin/main`. Duas superfícies contaminam o resultado
se não forem congeladas/zeradas antes do force-push:

- **Merges concorrentes na janela W3→W8.** Qualquer PR mergeado (ou nova lane
  aberta) em `main` **entre o rewrite e o flip** cria um commit cuja base
  (`merge-base`) diverge dos SHAs reescritos. O merge re-suja `main` via
  histórico não-reescrito e **força um novo ciclo de rewrite** — desperdiça
  W3 inteira e reabre a janela irreversível de maior blast-radius do plano
  ([[PLAN-public-release]] §Riscos).
- **85 branches `origin/agent/*`.** São branches efêmeras de execução de lanes
  ([[ADR-315]] §escopo: 1.862 commits · 85 branches · 75 worktrees). Carregam
  a **mesma PII** dos commits de `main` (fixtures/docs pré-saneamento) e, por
  divergirem da base reescrita, **não são fast-forwardáveis** pós-rewrite. Se
  não deletadas antes do flip, mantêm a Camada 1/2 recuperável no repo público
  — o rewrite de `main` não as alcança.
- **PRs abertos ficam órfãos.** Pós-rewrite o base SHA de todo PR aberto some;
  o GitHub marca o PR como não-mergeável. Resolver depois = re-abrir contra
  base reescrita, atrito e risco de merge sujo.

Esta lane é a **pré-condição de sequência** do force-push: sem freeze anunciado
e branches zeradas, a [[A34.l18]] entrega um resultado que volta a contaminar.

## Escopo

1. **Anunciar o FREEZE a todos os agentes** (canal de coordenação + nota no
   topo de [docs/_MOC/SPRINTS-active.md](../../../_MOC/SPRINTS-active.md)):
   janela `W3 → W8`, curta e alinhada ao schedule sábado 03:00 do
   `security.yml` (fim de semana minimiza feature parada). Durante o FREEZE:
   **zero merge em `main`, zero nova lane, zero branch `agent/*` nova.**
2. **Resolver PRs abertos ANTES do rewrite** — para cada PR aberto contra
   `main`: mergear (se verde e dentro do escopo saneado) ou fechar/abandonar
   explicitamente com nota. Nenhum PR aberto pode cruzar o rewrite.
3. **Deletar as 85 branches `origin/agent/*` em lote** após o merge/abandono
   dos PRs e imediatamente antes (ou como parte de) o force-push da [[A34.l18]]:
   ```bash
   git fetch origin --prune
   git for-each-ref --format='%(refname:short)' refs/remotes/origin/agent/ \
     | sed 's#^origin/##' \
     | xargs -n1 -I{} git push origin --delete {}
   ```
4. **Descartar ~75 worktrees locais** (`.claude/worktrees/**`, incl. o worktree
   desta lane): **push-ou-perde** — qualquer trabalho não-pushado antes do
   FREEZE é abandonado. `git worktree list` + `git worktree remove` após
   confirmar que nada pendente sobrevive ao rewrite.
5. **Manter o FREEZE ativo até o flip** da [[A34.l22]] (W8); só então liberar
   merges/lanes.

## Critério de aceite

- `git for-each-ref refs/remotes/origin/agent/ | wc -l` = **0** após o `--prune`
  (85 branches zeradas; nenhuma `agent/*` remota sobrevive).
- FREEZE **anunciado** no canal de agentes + nota datada no topo de
  `SPRINTS-active.md`, com janela `W3→W8` explícita.
- `gh pr list --state open --base main` = vazio (todos os PRs abertos mergeados
  ou fechados com nota antes do rewrite).
- FREEZE permanece ativo até [[A34.l22]]; nenhum commit novo em `origin/main`
  entre o force-push da [[A34.l18]] e o flip (verificável por
  `git log origin/main --since=<início-W3>`).
- Ordem verificada: PRs resolvidos → branches deletadas → force-push
  ([[A34.l18]]) — nunca force-push antes de zerar as branches.

## Rollback

Operação **destrutiva sobre refs remotas** (branch deletion + force-push
downstream). A rede é o backup off-site + tag `pre-public-flip-backup` da
[[A34.l2]] (pré-condição de G0). Se o rewrite falhar após a deleção:

- Branches `agent/*` deletadas **não** são restauradas — são efêmeras e
  contaminadas por design; recriá-las reintroduziria PII. O rollback restaura
  **`main`** do mirror de backup, não as branches.
- Levantar o FREEZE só após confirmar backup íntegro (G3) ou após rollback
  bem-sucedido de `main`.

**CI obrigatório:** não — lane de **coordenação + operação git** (branch
deletion, anúncio, resolução de PR), **não toca código/testes**. Mergeia sem
CI (docs-only para a nota de FREEZE; as operações git rodam manualmente na
janela W3). A execução ordenada do rewrite em si é o track
[[TRACK-public-release-history-rewrite]] ([[A34.l18]]).

## Referências

- Estratégia de rewrite: [[ADR-315]] · runbook [[TRACK-public-release-history-rewrite]] ([[A34.l18]]).
- Backup/tag (pré-condição da rede de segurança): [[A34.l2]].
- Ruleset bypass + hash-refs (par de W3): [[A34.l20]].
- Flip que encerra o FREEZE: [[A34.l22]].
- Plano canônico e §Riscos & invariantes: [[PLAN-public-release]].
