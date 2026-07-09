---
id: A34.l14
type: lane
title: "SHA-pin das 4 actions de terceiros por tag flutuante"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: sha-pin-third-party-actions
adrs: ["[[ADR-320]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/ci
  - area/seguranca
---

# A34.l14 — `sha-pin-third-party-actions` (W5 · Hardening)

## Problema

Quatro GitHub Actions de terceiros são referenciadas por **tag flutuante**
(`@v<N>`) nos workflows de `.github/workflows/`. Tag é ponteiro mutável: o
mantenedor (ou um atacante que comprometa a conta do mantenedor) pode
reapontá-la para um commit malicioso sem que o repo consumidor perceba —
o vetor de supply-chain que materializou o **CVE-2025-30066** (`tj-actions`,
já mitigado neste repo). Enquanto o repo é privado o raio de exposição é
menor; ao tornar-se **público** ([[PLAN-public-release]]), o workflow vira
alvo de estudo e a superfície precisa estar fechada antes do flip.

As quatro actions e o motivo de cada uma ser risco:

- **`chinthakagodawita/autoupdate-action`** — o pior caso: roda com
  `contents: write` e faz `push` em `main`. Uma tag reapontada aqui tem
  permissão de escrever no branch protegido.
- **`amannn/action-semantic-pull-request`** — valida título do PR
  (Conventional Commits); executa no contexto do PR.
- **`actions/labeler`** — aplica labels; requer token com escrita em issues/PRs.
- **`CodelyTV/pr-size-labeler`** — idem, escrita de label por tamanho de diff.

Nenhuma está pinada por SHA nem coberta por Dependabot, então bumps hoje
seriam manuais e silenciosos — o oposto do que um repo público de referência
deve exibir.

## Escopo

1. Substituir cada `uses: <owner>/<action>@v<N>` por
   `uses: <owner>/<action>@<sha-completo-40-hex>  # v<N>` nos workflows de
   `.github/workflows/`. O comentário `# v<N>` preserva legibilidade humana
   do que o SHA representa (padrão recomendado pela documentação de
   hardening do GitHub).
2. Fixar o SHA correspondente à tag **atualmente resolvida** de cada action
   (resolver via `git ls-remote https://github.com/<owner>/<action> refs/tags/v<N>`
   ou pela API de tags) — sem trocar de versão nesta lane; é pin, não upgrade.
3. Adicionar/estender `.github/dependabot.yml` com o ecossistema
   `github-actions` (diretório `/`) para que bumps futuros do SHA venham em
   PR auditável, com changelog e revisão — restaura atualização segura sem
   reintroduzir tag flutuante.
4. Confirmar que actions **oficiais** (`actions/checkout`, `actions/setup-*`
   etc.) seguem a política vigente do repo; esta lane trata apenas das **4 de
   terceiros**, mas o Dependabot passa a cobrir todas as `github-actions`.

Alinha-se ao invariante de hardening de [[ADR-320]] e reforça a fronteira de
supply-chain do CI/CD do superset público (Onda W5).

**CI obrigatório** — toca `.github/workflows/**`; o próprio workflow precisa
rodar verde com os SHAs fixados antes do merge.

## Critério de aceite (verificável)

- `git grep -n "uses:.*@v[0-9]" .github/workflows/` retorna **zero** linhas
  para as 4 actions de terceiros (nenhuma tag flutuante remanescente).
- Cada `uses:` das 4 actions aponta para um SHA de 40 hex, com comentário
  `# v<N>` na mesma linha.
- `.github/dependabot.yml` contém uma entrada `package-ecosystem: "github-actions"`
  cobrindo `/` — validável por `git grep -n "github-actions" .github/dependabot.yml`.
- O SHA fixado **resolve para a mesma versão** que a tag flutuante apontava no
  momento do pin (comportamento inalterado; só a mutabilidade some).
- CI verde no PR: os workflows que usam as 4 actions executam sem erro de
  resolução de referência.
- Gate G5 desta onda contempla este item (ver [[PLAN-public-release]] §Ondas,
  linha "G5"): "4 actions SHA-pinned + Dependabot".

## Rollback

Reversível por revert do PR: reverter para as tags flutuantes restaura o
comportamento anterior (menos seguro, porém funcional). A entrada de
`dependabot.yml` é aditiva e inócua — pode permanecer mesmo após revert do
pin sem efeito colateral. Como só toca config de CI (nenhum runtime de
produto), não há migração de dados nem estado a desfazer.

## Referências

- Plano canônico: [[PLAN-public-release]] (Onda W5 · Hardening CI/CD).
- ADR de hardening: [[ADR-320]].
- Contrato de gates anti-regressão relacionado: [[ADR-319]].
- Lanes irmãs da W5: [[A34.l13]] (permissions read-all default) ·
  [[A34.l15]] (GHAS + Fernet dummy → secret).
- Precedente de supply-chain no repo: mitigação do CVE-2025-30066
  (`tj-actions`) — mesmo vetor de tag flutuante que esta lane fecha.
