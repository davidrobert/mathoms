---
id: ADR-315
type: adr
title: "Estratégia de rewrite de histórico git para release pública"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[ADR-171]]", "[[A34.l18]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/seguranca
  - area/ci
---

# ADR-315 — Estratégia de rewrite de histórico git para release pública

**Status:** Proposto · **Data:** 2026-07-08 · Owner-gated (gate **G0** do
[[PLAN-public-release]]). Decisão da operação de **maior blast-radius e única
irreversível** do plano. O runbook operacional passo-a-passo é
[[TRACK-public-release-history-rewrite]] ([[A34.l18]]); esta ADR fixa a
**estratégia e as rejeições**, não os comandos.

## Contexto

O saneamento do HEAD (Onda 1) zera a Camada 1, mas a **Camada 2 — histórico
git — permanece recuperável de `origin/main`** mesmo com o HEAD limpo. O
escopo é `1.862` commits, `85` branches `origin/agent/*` e `75` worktrees. O
histórico contém PII em blobs e mensagens (inventário mascarado em
[audit-2026-07-08.md](../plan/PUBLIC_RELEASE/audit-2026-07-08.md)):

- **Blobs deletados no HEAD, vivos no histórico:** `config/family_members.json`
  (CPFs, filho menor), `members/` (holerite), `processed/` (transações reais),
  `.env` com a chave Fernet (adicionada em `ae340c60`, removida em `90279c68`).
- **Mensagens de commit:** patrimônio nominal em ~100 mensagens.
- **Identidade de autoria:** e-mail Gmail pessoal em `813` commits — tratado
  por [[ADR-317]] (mailmap), aplicado nesta mesma passada.

A operação é **irreversível na prática** (força reescrita de todos os hashes) e
adjacente ao flip. Ela **não** alcança a Camada 3 (metadados GitHub imutáveis —
855 PRs/issues/logs de CI), tratada por triagem em [[ADR-316]].

## Decisão

**Ferramenta: `git-filter-repo`**, executado sobre um clone `--mirror` (não o
working tree), numa **única passada ordenada**:

1. `--path` / `--invert-paths` — remove os caminhos contaminados por
   construção (`config/family_members.json`, `members/`, `processed/`, `.env`).
2. `--replace-text` — captura resíduo textual (blobs que escaparam do passo 1).
3. `--replace-message` — neutraliza patrimônio nominal em ~100 mensagens.
4. `--mailmap` — reescreve autoria conforme identidade decidida em [[ADR-317]].

Pré-condições (gate **G0**, herdadas de W0):

- **Backup bare off-site ANTES** (lane [[A34.l2]]) + tag `pre-public-flip-backup`
  no HEAD de `main`. É a **única rede** — sem ela, force-push mal-sequenciado =
  perda permanente.
- Rotação Fernet ([[ADR-171]], lane [[A34.l3]]) confirmada em produção — passe
  completo da task `rotate_fernet_secrets` com `failed=0` somado nos targets.
  O rewrite remove o blob da chave, mas a chave só é **inócua** se a rotação já
  rodou — não verificável do repo.

Validação e reativação (gate **G3**):

- **Validação DUPLA** com `gitleaks`: árvore de trabalho **E** histórico
  completo, ambos = 0 achados.
- Deletar as `85` branches `origin/agent/*` e limpar worktrees.
- Atualizar/anotar hash-refs invalidados em ~10 ADRs (ver Consequências) +
  **nota de rewrite** no changelog.
- **Bypass owner-gated** do Ruleset `main-protection` (`non_fast_forward`) para
  o force-push, seguido de **reativação verificada** (lane [[A34.l20]]).
- **FREEZE de merges** ativo do início do W3 até o flip (W8) — evita drift
  entre o mirror reescrito e `main`.

## Alternativas consideradas

- **BFG Repo-Cleaner — REJEITADO.** Não reescreve mensagens de commit nem
  aplica mailmap; deixaria patrimônio nominal em ~100 mensagens e o Gmail em
  813 commits intactos. Cobre só um dos quatro passos.
- **Squash-to-genesis (achatar tudo num commit inicial) — REJEITADO.** Destrói
  a arqueologia de ADR (âncoras históricas, supersedure, datas de decisão) —
  viola diretamente [[ADR-182]]. A rastreabilidade de decisão é ativo do
  projeto, não ruído a descartar.
- **Shallow-truncate (cortar histórico antigo) — REJEITADO.** Blobs continuam
  recuperáveis via reflog/objetos soltos até GC; falsa sensação de limpeza e
  não trata mensagens.
- **Repo novo (push do HEAD saneado) — fora do escopo desta ADR.** Zeraria as
  três camadas de uma vez sem rewrite/bypass, mas colide com a restrição
  in-place do owner. A reabertura dessa restrição é decisão de [[ADR-316]]
  (cláusula de incompatibilidade lógica), não desta.

## Consequências

- **Hashes invalidados em ~10 ADRs** que referenciam commits por hash (e refs
  correlatas): atualizar para os novos hashes OU anotar como pré-rewrite. Uma
  **nota de rewrite** no changelog documenta a descontinuidade para arqueologia
  futura.
- **FREEZE de merges (W3→W8)** congela error-budget de feature — aprovado pelo
  owner na janela do G0.
- **Irreversibilidade:** após o force-push, o estado anterior só existe no
  backup off-site (W0). O backup deve permanecer íntegro por ≥30d pós-flip.
- **Camada 3 permanece:** o rewrite não toca metadados GitHub — risco residual
  aceito em [[ADR-316]].
- **Identidade pública** de autoria passa a ser a decidida em [[ADR-317]] em
  todo o histórico reescrito.

## Decisão do owner

Esta ADR fica `Proposto` até o owner aprovar a estratégia **e** a janela de
FREEZE. Assinalar:

- [ ] **Aprovar `git-filter-repo`** com a sequência de 4 passos e a validação
      dupla (recomendação leading).
- [ ] Aprovar a **janela de FREEZE** de merges (W3→W8) e sua duração anunciada.
- [ ] Confirmar backup off-site + tag `pre-public-flip-backup` como
      pré-condição bloqueante ([[A34.l2]]).
- [ ] Confirmar rotação Fernet em prod (`failed=0`) antes do
      rewrite ([[ADR-171]] / [[A34.l3]]).
- [ ] Autorizar o **bypass do Ruleset** `non_fast_forward` na janela, com
      reativação verificada ([[A34.l20]]).
- [ ] _(Alternativo)_ Reabrir a restrição in-place para **repo novo** — nesse
      caso esta ADR é dispensada (decisão migra para [[ADR-316]]).

Ao decidir, flippar para `Decidido (A34)` e referenciar o PR de aprovação.
