---
id: A34.l13
type: lane
title: "permissions read-all default + elevação por-job"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: actions-permissions-readonly
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

# A34.l13 — `actions-permissions-readonly` (W5 · Hardening)

## Problema

O `GITHUB_TOKEN` padrão dos workflows do Actions herda o escopo de permissões
configurado no repositório. Em repo **privado** isso é aceitável (superfície de
ataque interna). No flip para **público** ([[PLAN-public-release]]), qualquer PR
de fork dispara workflows com um token cujo escopo default não está explicitado
no YAML — princípio do menor privilégio **não é aplicado por workflow**.

Estado atual (do co-design 2026-07-08): **só o job `changes` declara `permissions`
explicitamente**; os demais workflows/jobs rodam com o escopo implícito herdado do
repo. Em público, o vetor concreto é o **fork-PR malicioso**: um contribuidor de
primeira viagem abre PR que dispara workflow com token de escopo amplo (ex.:
`contents:write`) e exfiltra ou grava. A action de auto-update
(`chinthakagodawita/autoupdate-action`, tratada em [[A34.l14]]) já precisa de
`contents:write` + push em `main` — evidência de que o default hoje é permissivo.

Sem `permissions` no topo de cada workflow, o público herda um token mais poderoso
que o necessário, e o setting do repositório vira o único ponto de controle — não
versionado, não revisável em PR.

## Escopo

1. Adicionar `permissions: read-all` no **topo** de **todos** os workflows em
   `.github/workflows/**` (escopo default de menor privilégio, aplicado antes de
   qualquer job).
2. **Elevar por-job** apenas onde necessário, com o escopo mínimo do job (ex.:
   `permissions: { pull-requests: write }` num job que rotula PR; `contents: write`
   somente no job que precisa gravar). Nunca elevar no nível de workflow o que só
   um job usa.
3. Ativar, nas **Actions settings** do repositório, *require approval for all
   outside collaborators / first-time contributors* — fork-PR de contribuidor novo
   não roda workflow sem aprovação de mantenedor.
4. Documentar no header de cada workflow (comentário curto) o par escopo→motivo
   quando um job elevar acima do default, para revisão futura.

Fora de escopo (lanes irmãs de W5): SHA-pin das actions de terceiros ([[A34.l14]]);
GHAS + secret Fernet dummy ([[A34.l15]]); `CODEOWNERS` em `.github/workflows/**`
(gate G5 do plano, coordenar com [[A34.l15]]).

## Critério de aceite (verificável)

- `git grep -L "^permissions:" .github/workflows/*.yml .github/workflows/*.yaml`
  retorna **vazio** — todos os workflows declaram `permissions` no topo.
- Nenhum workflow declara `contents: write` (ou outro escopo de escrita) **no nível
  de workflow**; escritas existem apenas em jobs específicos que as justificam.
- O setting *require approval for first-time contributors* está **confirmado como
  ativo** nas Actions settings (screenshot/registro no PR, pois não é versionável no
  repo).
- Suíte de CI verde no próprio PR (o PR exercita os workflows editados com o novo
  escopo — se algum job foi sub-provisionado, quebra aqui).
- Contribui para o gate **G5** ([[PLAN-public-release]] §Ondas): "permissions
  mínimas em todos os workflows".

**CI obrigatório** — a lane toca `.github/workflows/**` (config executável). Um
escopo mal-elevado é detectado pelo próprio CI ao rodar os workflows editados; não
mergeia sem verde.

## Rollback

Reversível por revert de PR — restaura o escopo herdado anterior. Risco operacional
da elevação errada é **quebra de CI no próprio PR** (job sem permissão suficiente),
detectada antes do merge, não em produção. O setting de *require approval* é
revertido manualmente nas Actions settings (não versionado). Sem blast-radius de
runtime de produto (mudança confinada à superfície CI/CD).

## Referências

- Plano canônico: [[PLAN-public-release]] (Onda W5 · gate G5 · KR4).
- ADR de hardening CI/CD: [[ADR-320]].
- Lanes irmãs de W5: [[A34.l14]] (SHA-pin das 4 actions de terceiros) ·
  [[A34.l15]] (GHAS + Fernet dummy → secret).
- Contrato negativo de gates anti-regressão: [[ADR-319]].
