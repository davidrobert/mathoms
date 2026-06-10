---
id: TRACK-a6g-eslint-max-lines-ratchet
type: track
title: "Track A6g.RATCHET — max-lines-per-function warn→error com ratchet de disables"
sprint: A6
status: ready
created_at: "2026-06-09"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a6
  - status/ready
  - priority/p2
  - area/frontend
  - area/ci
---

# Track A6g.RATCHET — `max-lines-per-function` warn→error com ratchet de disables

> **Follow-up da lane A6g.6b ([[ADR-114]]).** Em 2026-04-22 a regra ficou em
> `warn` com 64 offenders e a promoção foi adiada para "sweep dedicado (lane
> futura)". Medição de 2026-06-09: **129 offenders em 116 arquivos** — o débito
> dobrou em ~7 semanas porque `warn` não bloqueia nada. Esta lane **para a
> hemorragia**; não tem como meta zerar os 129 (refactor é boy-scout posterior).
> Prioridade/aceite revisados por product-manager em 2026-06-09.

## Contexto

- Regra em [`frontend/eslint.config.mjs`](../../../../frontend/eslint.config.mjs)
  (~linha 99): `max-lines-per-function: ["warn", { max: 60, skipBlankLines:
  true, skipComments: true, IIFEs: true }]`.
- O comentário do config ainda diz "59 arquivos (64 offenders)" — **stale**,
  atualizar no PR1.
- Concentração: components React de `tasks/`, `report/`, `config/`.
- Medir offenders: `cd frontend && npx eslint src/` e contar
  `max-lines-per-function`.

## Estratégia (decidida — não reabrir)

**Disable-inline + ratchet**, rejeitada a alternativa "promover por diretório
limpo" (deixaria o resto do repo desprotegido até o último diretório):

1. Promover a regra a `error` no `eslint.config.mjs`.
2. Inserir `// eslint-disable-next-line max-lines-per-function` em cada um dos
   ~129 offenders atuais (mecânico — scriptável a partir do JSON do ESLint).
   Débito fica explícito e grep-able; regressão fica bloqueada **imediatamente
   em todo o repo**.
3. **Gate ratchet:** baseline pinada em arquivo versionado (ex.:
   `frontend/.eslint-ratchet.json` com a contagem) + check (pre-commit e/ou CI
   frontend) que conta as ocorrências do disable em `frontend/src/` e **falha
   se o número subir**. Baixar o número atualiza a baseline no mesmo PR
   (one-way ratchet).

## Tarefas (PR1 — fecha a lane)

- [ ] `eslint.config.mjs`: `max-lines-per-function` `warn` → `error`; comentário
  atualizado (64 → contagem real do dia, apontando para este track).
- [ ] Script mecânico insere os disables (rodar ESLint `--format json`, inserir
  a linha acima de cada função ofensora). Sem refactor de conteúdo no PR1.
- [ ] Baseline versionada + check ratchet (falha se contagem subir; mensagem
  inclui valor ofensor + esperado).
- [ ] Hook no `.pre-commit-config.yaml` (ou job frontend do CI) rodando o check.
- [ ] `cd frontend && npm test -- --run` + `npx eslint src/` verdes.

## Critério de aceite (product-manager, 2026-06-09)

- `max-lines-per-function` em `error`; zero warnings de lint no CI.
- Offenders atuais com disable inline; contagem congelada em baseline versionada.
- Gate falha se a contagem **subir**; baixar exige atualizar baseline (ratchet).
- PR mergeado em `main` com CI verde.
- **Fora do escopo da lane:** refatorar os offenders. PRs de refactor por
  diretório (`tasks/`, `report/`, `config/`) são boy-scout/oportunísticos,
  rastreados pelo contador decrescente da baseline.

## Branch e PR

- Branch: `agent/a6g-eslint-ratchet/<yyyyMMdd-HHmm>`.
- Conventional commit: `frontend(lint): promove max-lines-per-function a error + ratchet (A6g.RATCHET)`.
- Diff grande porém mecânico (1 linha por offender) — anunciar no PR que é
  sweep mecânico sem mudança de lógica.
