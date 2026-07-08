---
id: MOC-sprint-a34
type: moc
title: "Sprint A34 — Public Release: tornar o repo público in-place com segurança e qualidade de referência"
aliases: ["A34", "Sprint A34"]
sprint_status: candidate
date: "2026-07-08"
theme: "public-release"
---

# Sprint A34 — Public Release: tornar o repo público in-place

> **Status:** `candidate` — sprint proposta, **gated por decisões do owner** (G0).
> Nenhuma lane abre antes das 8 ADRs `Proposto` ([[ADR-313]]–[[ADR-320]]) serem
> decididas. Não executa nesta sessão.
>
> **Plano canônico:** [[PLAN-public-release]]
> (`docs/plan/PUBLIC_RELEASE/_README.md`) — fonte única de ondas, gates, KRs e
> registro de decisões. Inventário mascarado da auditoria:
> [audit-2026-07-08.md](../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
>
> **Origem:** co-design multi-agente 2026-07-08 (`product-manager` +
> `information-architect` + `sre-devops` + `senior-cto` + `gtm-strategist` +
> síntese de fechamento). Semente: auditoria de PII/segredos de 2026-07-08.

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
| **W1** Saneamento do HEAD | `_archive/`, EXEMPLO, ADRs, CPFs, seed, IP | [[A34.l7]] · [[A34.l8]] · [[A34.l9]] · [[A34.l10]] · [[A34.l11]] · [[A34.l12]] |
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
