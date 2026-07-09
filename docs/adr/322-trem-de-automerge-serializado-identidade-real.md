---
id: ADR-322
type: adr
title: "Trem de auto-merge serializado com identidade real (aposenta autoupdate-action)"
status: Decidido
date: "2026-07-09"
relates_to:
  - "[[ADR-210]]"
  - "[[ADR-320]]"
supersedes: []
superseded_by: []
aliases: ["ADR 322", "automerge train", "auto-update PRs"]
tags:
  - type/adr
  - status/decidido
  - area/ci
---

# ADR-322 — Trem de auto-merge serializado com identidade real

**Status:** Decidido • **Data:** 2026-07-09 • **Relaciona** [[ADR-210]], [[ADR-320]].

## Contexto

O Ruleset `main-protection` exige branch up-to-date com main
(`strict_required_status_checks_policy: true`). Com N PRs de agentes em
paralelo, cada merge invalida os demais. O workflow `auto-update-prs.yml`
resolvia isso atualizando **todos** os PRs com auto-merge a cada push em
main (`chinthakagodawita/autoupdate-action`, Docker tag flutuante,
`GITHUB_TOKEN`) — com dois defeitos compostos, medidos em 2026-07-08:

1. **Atribuição**: update-branch com `GITHUB_TOKEN` é push de
   `github-actions[bot]`; os runs `pull_request` resultantes nascem
   `action_required` (0 jobs) e nunca executam. Auto-merge espera um check
   que jamais reporta → PR congela → intervenção manual do owner
   (empty-commit push). Em 2026-07-09 01:15 UTC, 1 merge órfão-ou 6 PRs
   de uma vez (18 runs `action_required`).
2. **Custo quadrático**: 28 merges/dia × até 9 PRs abertos → 57 runs do
   workflow CI num dia (32 verdes, 9 `action_required`, 12 cancelados).
   Só o primeiro merge de cada onda aproveita a atualização; o resto vira
   run cancelado/supersedido — que ainda dispara o defeito conhecido do
   agregador stale (run superseded falha `All checks green` → GitHub
   desabilita auto-merge silenciosamente).

Co-design com subagente `sre-devops` (2026-07-09); achado central: corrigir
só a atribuição **sem** serializar un-suprime o custo quadrático que hoje
morre grátis em `action_required` — estouraria o budget de Actions.

## Decisão

- **D1 — Serialização.** O workflow atualiza **exatamente 1 PR por run**:
  o mais antigo (FIFO por `createdAt`) com auto-merge habilitado, não-draft,
  sem label `wip`/`do-not-merge`/`blocked`. Conflito (`DIRTY`) e required
  check `FAILURE` saem do trem; **pending nunca é pulado** (pular quebra o
  FIFO e pode livelock). Lógica em `dev/ci_advance_automerge_train.py`
  (executável localmente com `gh auth` próprio). Custo cai de O(merges×PRs)
  para O(merges).
- **D2 — Identidade real.** Update-branch roda com secret `AUTOUPDATE_PAT`
  (fine-grained PAT: Contents + Pull requests + Issues write, Actions
  read, só este repo,
  expiração ≤90d). **Sem o secret o workflow não faz fallback para
  `GITHUB_TOKEN`** — loga warning e sai. Regressão ruidosa (trem
  visivelmente parado + issue do watchdog) > órfãos silenciosos. Alvo
  estrutural: migrar para GitHub App (token efêmero, identidade própria
  fora da bypass list); PAT é stopgap aceito.
- **D3 — Watchdog.** `automerge-watchdog.yml` (schedule 30min) remedia os
  três estados presos: (a) re-habilita auto-merge derrubado pelo agregador
  stale quando o head atual está verde (opt-out: labels de exclusão);
  (b) kicka runs órfãos `action_required` com empty commit via Git Data
  API — só com PAT; (c) mantém issue de sinalização quando a cabeça do
  trem trava >60min, fechando-a quando anda.
- **D4 — `strict` permanece.** Desligar o up-to-date resolveria o custo,
  mas é load-bearing para [[ADR-210]]: o CI de `push:main` foi removido
  porque strict garante que squash-de-PR-verde ≡ main verde.
- **D5 — Supply chain.** A action Docker de tag flutuante é deletada
  (alinha com hardening de [[ADR-320]]); os jobs required `All checks
  green` e `Title (Conventional Commits)` não podem ser renomeados — o
  Ruleset referencia por nome.

## Alternativas rejeitadas

- **Merge queue nativo**: indisponível (repo private em conta User;
  exige Organization). Reavaliar pós-PUBLIC_RELEASE (A34) — repo público
  em org aposentaria este workflow.
- **PAT em lote (manter action, trocar token)**: resolveria atribuição
  mas manteria O(N²) — inaceitável com budget finito de Actions.
- **Fallback `GITHUB_TOKEN` quando PAT ausente/expirado**: recriaria
  exatamente a classe de confusão que motivou esta ADR, de forma
  silenciosa. Rejeitado em favor de no-op ruidoso.

## Consequências

- Owner tem 1 ação pendente: criar o PAT e `gh secret set AUTOUPDATE_PAT`.
  Até lá o trem só anda manualmente (`python3
  dev/ci_advance_automerge_train.py`) — comportamento intencional (D2).
- Expiração do PAT degrada para trem parado **com** issue de watchdog e
  warning no Actions — não para órfãos silenciosos.
- Runbook operacional: [automerge_train](../reference/runbooks/automerge_train.md).
