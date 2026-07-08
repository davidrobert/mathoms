---
id: A34.l2
type: lane
title: "Backup bare mirror off-site + tag pre-public-flip-backup"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: backup-mirror-offsite
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/seguranca
---

# A34.l2 — `backup-mirror-offsite` (W0 · Gate)

## Problema

A Onda 3 do [[PLAN-public-release]] executa um **rewrite de histórico
irreversível** (`git-filter-repo` sobre 1.862 commits + 85 branches
`agent/*`), seguido de force-push com bypass do Ruleset `main-protection`.
É a única operação do plano sem desfazer: um force-push mal-sequenciado,
um `filter-repo` com regra de replace errada, ou uma branch deletada por
engano **perde histórico permanentemente** — `origin/main` deixa de ter a
versão pré-rewrite e não há reflog remoto que a recupere.

Hoje não existe rede de segurança fora do próprio remote. A decisão de
co-design `[backup/Fernet]` do plano é explícita: o backup off-site + tag
são **pré-condição de W0**, não de W3 — precisam existir e ser provados
**restauráveis** antes de qualquer lane destrutiva (W1+) abrir. Sem a rede
antes, o gate G0 não pode ser assinado.

Esta lane é **puramente operacional** (git + armazenamento off-site); não
toca código nem docs versionados. É pré-requisito do gate G0.

## Escopo

1. **Bare mirror completo** — `git clone --mirror` do repo `davidrobert/mathoms`
   para armazenamento **off-site** (fora do host do repo primário e fora de
   qualquer worktree de agente). O mirror captura **todas** as refs:
   `refs/heads/*`, `refs/remotes/origin/agent/*` (85 branches), tags e
   `packed-refs` — a árvore completa que o rewrite de W3 vai reescrever.
   ```bash
   git clone --mirror git@github.com:davidrobert/mathoms.git \
     mathoms-pre-public-flip.git
   ```
2. **Tag imutável no HEAD de `main`** — criar `pre-public-flip-backup`
   apontando para o commit atual de `origin/main`, empurrada ao remote
   **antes** do FREEZE de W3. Marca o ponto-âncora de rollback e serve de
   verificação rápida ("o HEAD que reescrevi era este").
   ```bash
   git tag pre-public-flip-backup origin/main
   git push origin pre-public-flip-backup
   ```
3. **Prova de restaurabilidade** — clonar o mirror para um diretório de
   teste **descartável** (não um worktree do repo) e confirmar integridade:
   `git fsck --full` sem erro, contagem de commits ≥ 1.862, presença das 85
   branches `agent/*` e da tag `pre-public-flip-backup`. Um mirror que não
   restaura não é backup.
   ```bash
   git clone mathoms-pre-public-flip.git _scratch/restore-check
   cd _scratch/restore-check && git fsck --full && \
     git rev-list --count --all && \
     git for-each-ref refs/remotes/origin/agent/ | wc -l
   ```
4. **Retenção documentada ≥ 30 dias pós-flip** — janela de rollback do plano
   (KR "backup íntegro por ≥30d"). Registrar em local que sobreviva à sessão:
   local do mirror (host/bucket off-site, **sem credencial no doc**), data de
   criação, hash do HEAD arquivado, e data-limite de expurgo. Este registro é
   docs-only e pode ir ao anexo do plano ou ao track de rewrite
   [[TRACK-public-release-history-rewrite]].

> **PII:** o mirror contém as 3 camadas de contaminação (é justamente o
> estado pré-saneamento). Armazenar em local **privado e controlado pelo
> owner**; nunca em bucket público, nunca commitado. O clone de teste vai em
> `_scratch/` (gitignored) e é apagado após a verificação.

## Critério de aceite (verificável)

- **Mirror clonável de teste:** `git clone <mirror>` + `git fsck --full`
  retornam sem erro; `git rev-list --count --all ≥ 1862`; as 85 branches
  `refs/remotes/origin/agent/*` presentes no clone de teste.
- **Tag presente:** `git ls-remote --tags origin pre-public-flip-backup`
  resolve para o hash do HEAD de `main` no momento da criação (mesmo hash
  registrado na doc de retenção).
- **Retenção documentada:** entrada com local off-site (sem credencial),
  data de criação, hash arquivado e data de expurgo (≥ 30d após o flip de
  [[A34.l22]]) registrada e commitada.
- **Rede pronta para W3:** esta lane fecha antes de qualquer lane W1+ abrir
  — é insumo direto do gate **G0** e da verificação de W3
  ([[A34.l18]] só executa com backup íntegro confirmado).

## Rollback

Lane não-destrutiva e aditiva (cria mirror + tag; não altera árvore nem
histórico). "Desfazer" = apagar o mirror off-site e `git push --delete
origin pre-public-flip-backup` — só cabível se o plano inteiro for abortado
**antes** de W3. Durante e após W3, o mirror é a rede que **não** se remove
até o fim da janela de retenção.

**Mergeia sem CI** — docs-only (o registro de retenção); os artefatos
operacionais (mirror, tag) vivem fora do repo e são verificados por comando,
não por suíte.

## Referências

- Plano canônico: [[PLAN-public-release]] — §W0 (gate G0), §Verificação (G0),
  decisão `[backup/Fernet]`, §Riscos & invariantes ("W3 é a única irreversível;
  backup off-site é a única rede").
- Gate irmão de W0: [[A34.l1]] (ADRs do gate) · [[A34.l3]] (confirmar rotação
  Fernet em prod).
- Consumidores da rede: [[A34.l18]] (runbook `git-filter-repo`, valida backup
  íntegro) · [[A34.l19]] (freeze + delete das 85 branches) · [[A34.l22]]
  (flip — retenção conta a partir daqui).
- ADR de estratégia de rewrite (contexto): [[ADR-315]].
