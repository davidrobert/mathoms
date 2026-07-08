---
id: A34.l18
type: lane
title: "Runbook operacional: git-filter-repo rewrite (self-contained)"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: history-rewrite-runbook
adrs: ["[[ADR-315]]", "[[ADR-317]]"]
depends_on: ["[[A34.l2]]", "[[A34.l3]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/seguranca
  - area/ci
---

# A34.l18 — `history-rewrite-runbook` (W3 · Rewrite)

## Problema

Saneamento do HEAD (Onda 1) zera a **camada 1**, mas a **camada 2** — PII
recuperável do histórico de `origin/main` — permanece: `config/family_members.json`
(CPFs, filho menor), `members/` (holerite), `processed/` (transações reais),
patrimônio nominal em ~100 mensagens de commit, Gmail pessoal em 813 commits, e a
Fernet key em blobs históricos (commit `ae340c60` / removida em `90279c68`, mas
recuperável). Deletar do HEAD não alcança nada disso — só um **rewrite de todo o
histórico** ([[ADR-315]]) remove os blobs e reescreve as mensagens.

Esta é a **única operação irreversível do plano** e a de maior blast-radius: 1.862
commits, 85 branches `origin/agent/*`, 75 worktrees, `--force`-push contra um
Ruleset de `non_fast_forward`. Errar aqui sem rede = perda permanente ou vazamento
não-detectado no repo público.

Escopo desta lane: ela é o **ponteiro + critério de aceite** da operação. O passo-a-passo
executável (comandos exatos, ordem dos filtros, validação, rollback) vive no track
self-contained [[TRACK-public-release-history-rewrite]] — mantido separado porque um
runbook destrutivo precisa ser lido inteiro e seguido literalmente, não fatiado numa
lane. Coordena com [[A34.l19]] (freeze + delete de branches) e [[A34.l20]] (bypass do
Ruleset + hash-refs).

## Escopo

1. **Ferramenta fixa: `git-filter-repo`.** [[ADR-315]] rejeita BFG (não reescreve
   mensagens nem faz replace-text arbitrário), squash-to-genesis (perde arqueologia de
   ADR) e shallow clone (não remove blobs do histórico). Não substituir por outra
   ferramenta sem reabrir [[ADR-315]].
2. **Clone `--mirror` isolado.** O rewrite roda num `git clone --mirror` recém-clonado,
   NUNCA no working tree ativo nem no worktree da lane. O mirror original permanece
   intacto como rede secundária (o backup off-site de [[A34.l2]] é a rede primária).
3. **Sequência canônica de filtros** (ordem fixa, cada passo verificado antes do
   próximo — detalhe no track):
   1. `--path` / `--invert-paths` — remove árvores inteiras do histórico
      (`_archive/`, `members/`, `processed/`, `config/family_members.json`).
   2. `--replace-text` — redige padrões residuais em blobs sobreviventes (CPF, endereço,
      patrimônio nominal, Fernet key) via arquivo de expressões **fora do repo**.
   3. `--replace-message` — reescreve mensagens de commit que citam valores/nome reais.
   4. `--mailmap` — normaliza identidade de autoria conforme [[ADR-317]] (tratamento do
      Gmail pessoal em 813 commits + co-authors).
4. **Validação DUPLA** — árvore E histórico, não só o HEAD:
   - `gitleaks detect` no working tree do mirror reescrito.
   - `gitleaks detect --log-opts="--all"` sobre todo o histórico reescrito.
   - `git log --all -S<padrão>` e `git grep` dos padrões PII/atribuição em toda a
      história, referindo achados por path:linha + tipo (nunca colar o valor real).
5. **Atualização de hash-refs.** O rewrite muda todos os SHAs; ~10 ADRs citam commits
   por hash (Fernet: `ae340c60` / `90279c68`, e outros). Coordenar com [[A34.l20]] para
   atualizar OU anotar cada hash citado ("hash pré-rewrite; ver mailmap") — sem isso,
   wikilinks de arqueologia apontam para commits inexistentes.

## Critério de aceite

- `gitleaks detect` **árvore** = 0 achados no mirror reescrito.
- `gitleaks detect --log-opts="--all"` **histórico** = 0 achados.
- `git log --all -S` dos padrões de CPF / endereço / placa / nome-de-terceiro /
  patrimônio-nominal / Fernet key = zero ocorrências em toda a história.
- Mailmap aplicado conforme [[ADR-317]]: identidade pública consistente, Gmail pessoal
  tratado, co-authors preservados/normalizados por decisão do owner.
- Hashes citados em ADRs (~10) atualizados para os novos SHAs OU anotados como
  pré-rewrite; `check_doc_links` + `check_adr_anchors` verdes após o ajuste.
- O mirror de backup ([[A34.l2]]) permanece íntegro e restaurável (teste de clone) —
  não foi tocado pela operação.
- FREEZE de merges ([[A34.l19]]) ativo do início do rewrite até o flip ([[A34.l22]]);
  nenhuma branch nova mergeada na janela.

## Rollback

Operação **destrutiva e irreversível por natureza** (reescreve toda a história e faz
`--force`-push). Não há "desfazer" via git — o rollback é **restauração completa** a
partir do backup mirror de [[A34.l2]]:

1. Confirmar que o `--force`-push AINDA NÃO ocorreu (rewrite validado só no mirror
   local) → basta descartar o mirror e reclonar; `origin/main` intocado.
2. Se o `--force`-push já ocorreu e há regressão → restaurar `origin/main` do backup
   mirror off-site + tag `pre-public-flip-backup`, reativar o Ruleset e reabrir a janela
   de FREEZE. Detalhe operacional do restore no track [[TRACK-public-release-history-rewrite]].

Pré-condição de segurança (herdada de [[A34.l2]] e [[A34.l3]]): backup restaurável +
tag `pre-public-flip-backup` + rotação Fernet confirmada em prod **antes** de qualquer
comando de rewrite. Sem a rede, um force-push mal-sequenciado é perda permanente.

**CI obrigatório** não se aplica no sentido usual — a operação roda fora do fluxo de PR
(clone `--mirror` + bypass owner do Ruleset em [[A34.l20]]). A validação é o gate G3 do
plano (gitleaks dupla), não o CI de PR.

## Referências

- Track operacional (passo-a-passo): [[TRACK-public-release-history-rewrite]].
- Plano canônico: [[PLAN-public-release]] §"W3 — Rewrite de histórico" (gate G3).
- ADRs: [[ADR-315]] (estratégia de rewrite) · [[ADR-317]] (mailmap/identidade).
- Dependências: [[A34.l2]] (backup mirror off-site) · [[A34.l3]] (rotação Fernet).
- Coordena com: [[A34.l19]] (freeze + delete de 85 branches `agent/*`) ·
  [[A34.l20]] (bypass do Ruleset + hash-refs).
- Anexo de auditoria (mapa mascarado da camada 2): [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
