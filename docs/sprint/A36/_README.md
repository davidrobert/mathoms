---
id: MOC-sprint-a36
type: moc
title: "Sprint A36 — Follow-up da auditoria r4: itens de mérito sem rastreio"
aliases: ["A36", "Sprint A36"]
sprint_status: paused
date: "2026-07-09"
theme: "audit-followup"
---

# Sprint A36 — Follow-up da auditoria r4

> **Status:** `paused` — backlog de remediação priorizável pelo owner. São os
> cinco achados de **mérito** da auditoria externa `repo-audit` r4 (2026-07-09)
> que **não tinham lane/plano** no repo. Os achados **gating/críticos** já vivem
> em [[A34]] (W3 rewrite de história), [[ADR-228]] (W4-T01 backup + drill) e
> [[ADR-085]] (materializer) — esta sprint **não** os duplica.
>
> **Origem:** auditoria de repositório r4 @ `c004742b` (confidencial, fora do
> repo). Cada lane referencia o ID do achado (ARQ-/SEC-/DAT-/QUAL-) e traz
> âncoras `arquivo:linha` do próprio código — nenhum dado sensível.

## Por que esta sprint existe

A r4 observou que a org **captura os grandes achados conhecidos** (PII em
histórico, backup, BYOK) em sprints/ADRs, mas **os de mérito médio escapam do
backlog** (achado MAT-03). Estas cinco lanes fecham essa lacuna: são baratas
(~4-5 dias somados), sem dependência externa, e nenhuma bloqueia a nota gated —
são **dívida de qualidade/segurança que impede a nota de subir de "sólido" para
"maduro"**.

## Lanes

| Lane | Achado(s) | Tema | Prioridade | Esforço |
|---|---|---|---|---|
| [[A36.l1]] `boundary-lint-backend` | ARQ-02 · ARQ-01 | Fronteira pipeline↔backend guardada no CI | P1 | S+M |
| [[A36.l2]] `stderr-pii-redaction` | SEC-09 | PII em log via forward de stderr (Go) | P1 | S |
| [[A36.l3]] `e7-conservation-gate` | DAT-01 | Invariante de conservação pausa o run | P1 | M |
| [[A36.l4]] `go-toolchain-cve-bump` | SEC-07 | CVE Go alcançável (GO-2026-5856) | P1 | S |
| [[A36.l5]] `narrow-broad-excepts` | QUAL-01 · QUAL-02 | `except` largos em cripto/validação | P1 | S |

## Ordem sugerida

Do mais barato/isolado ao que exige coordenação de CI:
**[[A36.l4]] → [[A36.l5]] → [[A36.l3]] → [[A36.l2]] → [[A36.l1]]**.

- [[A36.l3]] é o de maior **valor de correção** (invariante financeira violada
  hoje pode chegar ao cliente sem flag).
- [[A36.l1]] é o de maior **valor estrutural** (fecha a causa-raiz da
  dependência circular que sobreviveu 4 auditorias) — deixar por último porque
  exige inversão + coordenação de CI.

## Fora de escopo (já rastreado)

- **SEC-01** (PII no histórico) → [[A34.l18]]–[[A34.l20]] (W3), [[ADR-315]].
- **REL-01** (backup + drill) → [[ADR-228]] W4-T01 + gate G2.
- **SEC-03** (BYOK plaintext) → [[ADR-085]] (decisão registrada, execução pendente).
- **DAT-03** (schema `warn`→`strict`) → PLATFORM_REVIEW W6-T01.
- **TEST-03** (paridade Go↔Py) → [[PLAN-go-shell]] F2 cutover ([[ADR-323]]).
