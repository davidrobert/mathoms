---
id: MOC-sprint-a34
type: moc
title: "Sprint A34 — Public Release: tornar o repo público in-place com segurança e qualidade de referência"
aliases: ["A34", "Sprint A34"]
sprint_status: paused
date: "2026-07-08"
theme: "public-release"
---

# Sprint A34 — Public Release: tornar o repo público in-place

> **Status:** `paused` — as ondas **decisão-independentes** (W2 gates ·
> W1 saneamento · W5 hardening) foram executadas e mergeadas em `main`
> (2026-07-09). Restam as ondas **owner-gated**: W0 (decisões [[ADR-313]]–[[ADR-318]]
> + backup + Fernet), [[A34.l12]] ([[ADR-314]] IP competitivo), [[A34.l15]] (GHAS),
> [[A34.l16]] (LICENSE [[ADR-313]]), W3 (rewrite), W4 (metadados), W8 (flip) — e o
> dilema **in-place × repo-novo** ([[ADR-316]]). Nada disso abre sem o owner.
>
> **Plano canônico:** [[PLAN-public-release]]
> (`docs/plan/PUBLIC_RELEASE/_README.md`) — fonte única de ondas, gates, KRs e
> registro de decisões. Inventário mascarado da auditoria:
> [audit-2026-07-08.md](../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
>
> **Origem:** co-design multi-agente 2026-07-08 (`product-manager` +
> `information-architect` + `sre-devops` + `senior-cto` + `gtm-strategist` +
> síntese de fechamento). Semente: auditoria de PII/segredos de 2026-07-08.

## Progresso de execução (2026-07-09)

**Mergeado em `main` (decisão-independente de [[ADR-316]]):**

- **W2 gates anti-regressão** — [[A34.l6]] (`_archive/`/`archive/` em
  forbidden-paths + gitleaks como gate de merge) · [[A34.l4]] (`lint_no_real_pii`
  estendido ao superset público + detectores CPF/endereço/placa/contrato/homedir
  + baseline burn-down) · [[A34.l5]] (`check_sigilo_terms` ao superset
  docs/prompts/README/migrations + baseline). ADRs [[ADR-319]]/[[ADR-320]] →
  `Decidido`.
- **W1 saneamento do HEAD** — [[A34.l7]] (deleta `_archive/`, 100 arquivos) ·
  [[A34.l8]] (EXEMPLO_DE_RELATORIO 100% sintético) · [[A34.l10]] (CPF+endereço) ·
  [[A34.l11]] (seed+report_spec+paths) · [[A34.l9]] (anonimização in-body de ADRs
  + placas/matrículas/nomes + rename `seed_tasks`).
- **W5 hardening** — [[A34.l13]] (permissions mínimos por job) · [[A34.l14]]
  (SHA-pin das actions de terceiros).

**Registro G2 (prova de detecção antes do saneamento):** os gates de W2 foram
instalados e provados **VERMELHOS** no HEAD contaminado antes de W1
(`lint_no_real_pii --no-baseline` = exit 1 com 158 hits: 94 ENDERECO, 51 PLACA,
8 CONTRATO, 3 HOMEDIR, 2 CPF; `check_sigilo_terms --all --no-baseline` = exit 1
listando os prompts de produto com atribuição nominal). Commit-teste sintético
(CPF DV-válido + endereço + atribuição) é **BARRADO** pelos gates; placeholders
canônicos passam verdes. Mensagens exibem só `path:linha+tipo`, nunca o valor.

**Superfície residual descoberta durante a l9 (NÃO no audit original):** sobrenome
da família em ~15 arquivos de teste + um schema + ADRs 126/141/243/268, nomes de
terceiros em prompts/fixtures, e resíduo baixo-confiança no seed. Os gates
**baselineiam** esses hits (não bloqueiam), mas o flip (W8) os exporia →
consolidada na lane residual [[A34.l24]] (decisão-independente; toca assertions
de teste + contrato de schema, então owner-visível antes de varrer).

## Tese

Tornar o Mathoms público expõe **3 camadas de contaminação** (HEAD · histórico git ·
metadados GitHub imutáveis) + uma superfície de **IP/negócio** (prompts com atribuição
metodológica nominal, playbook competitivo, pricing) + a **apresentação mínima** ausente
(sem `LICENSE`). O MLP desta sprint é **"público seguro"**, não "projeto de referência":
o must-have bloqueia o flip só quando sua ausência causa vazamento de PII, dano legal ou
exposição de segurança. Polish de percepção é *should* pós-flip.

Duas objeções foram registradas contra a restrição in-place (a Camada 3 é irredutível por
git; "referência open-source" não é alavanca GTM validada) — ver
[[PLAN-public-release]] §"Objeções registradas".

## Ondas (execução serial, gate irreversível adjacente ao flip)

Ordem: **W0 → W2 → W1 (∥ W5) → W6-min → W3 (∥ W4) → W8**; W7 + polish são *should*
pós-flip (P2). Detalhe, gates e critério de aceite em [[PLAN-public-release]].

| Onda | Tema | Lanes |
|------|------|-------|
| **W0** Gate de decisões (owner) | 8 ADRs `Proposto` + backup + Fernet | [[A34.l1]] · [[A34.l2]] · [[A34.l3]] |
| **W2** Gates anti-regressão | lint PII + sigilo + forbidden-paths + gitleaks | [[A34.l4]] · [[A34.l5]] · [[A34.l6]] |
| **W1** Saneamento do HEAD | `_archive/`, EXEMPLO, ADRs, CPFs, seed, IP | [[A34.l7]] · [[A34.l8]] · [[A34.l9]] · [[A34.l10]] · [[A34.l11]] · [[A34.l12]] · [[A34.l24]] (residual, follow-up) |
| **W5** Hardening CI/CD | permissions + SHA-pin + GHAS | [[A34.l13]] · [[A34.l14]] · [[A34.l15]] |
| **W6** Apresentação (mín.) | LICENSE + README EN; polish P2 | [[A34.l16]] · [[A34.l17]] |
| **W3** Rewrite de histórico (irreversível) | filter-repo + freeze + bypass Ruleset | [[A34.l18]] · [[A34.l19]] · [[A34.l20]] |
| **W4** Metadados GitHub | triagem T1 | [[A34.l21]] |
| **W8** Flip + verificação | flip + smoke pré-flip | [[A34.l22]] |
| **W7** i18n docs-EN (should) | docs EN + cross-link PLAN-i18n | [[A34.l23]] |

## Lanes

Ver `docs/sprint/A34/lanes/`. Runbooks das operações destrutivas são tracks
self-contained: [[TRACK-public-release-history-rewrite]] ([[A34.l18]]) e
[[TRACK-public-release-flip]] ([[A34.l22]]).
