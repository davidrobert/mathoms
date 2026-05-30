---
id: MOC-sprint-a21
type: moc
title: "Sprint A21 — Launch Trust: número confiável + gates de F3/LGPD abertos"
aliases: ["A21", "Sprint A21"]
sprint_status: done
date: "2026-05-30"
theme: "confiabilidade"
---

# Sprint A21 — Launch Trust: número confiável + gates abertos

> **Status:** `done` — **9/9 lanes mergeadas em `main`** em 2026-05-30
> (kickoff e fechamento no mesmo dia). Os dois gates de F3 (F1-O0 verde +
> defesa de injeção em `main`) e o pré-requisito de LGPD ficaram verdes;
> A22 está livre para fechar F3. Transição `current → done`; corrente passa
> a ser [[MOC-sprint-a22]].
>
> **Plano dono:** [[PLAN-launch-trust]] ([plan/LAUNCH_TRUST/_README.md](../../plan/LAUNCH_TRUST/_README.md)).
> Esta sprint foi a **primeira janela de execução** do plano.

## Resumo

Primeira janela do plano LAUNCH_TRUST. Restrição de design do owner:
**zero passo humano externo, zero deploy em produção** — tudo executável só
com engenharia. Sob essa restrição, A21 entrega a **frente F1 inteira**
(confiabilidade do número) e **abre os gates** que destravam as outras duas
frentes para A22:

- **Gate de F3** (Parecer): F3 está duplamente bloqueada — precisa de (a)
  F1-O0 verde [A21 entrega via l1] **e** (b) defesa de injeção em `main`
  [A21 entrega via l5+l6]. Ao fim da A21, **os dois gates ficam verdes** e
  A22 vira sprint de F3 limpa.
- **Gate de LGPD** (produção): audit log Art.37 + export/deleção Art.18 são
  puro código/schema (sem prod, sem humano) — entram na A21 para fechar o
  pré-requisito legal do launch.

**O que NÃO entra (e por quê):** deploy GHCR/Trivy (exige PAT/Coolify +
toca prod — viola a restrição; permanece represado na A20) · backup off-site
real R2 (exige bucket/credencial — A21 entrega só o mecanismo testável em CI)
· núcleo de F3 (F3-O0/O1/O2 — desbloqueado pela A21, executado na A22).

## Sprint goal

> Tornar o número confiável (F1 inteira) e abrir os gates de F3 (injeção em
> `main`) e de LGPD, deixando A22 livre para fechar F3 — tudo só com
> engenharia, sem tocar produção.

## KRs da janela (nenhum depende de humano externo ou prod)

| KR | Métrica | Meta | Mapeia | Resultado |
|---|---|---|---|---|
| A21-KR1 | Suíte INV-1..9 verde em CI, sem skip (INV-9 = filtro PJ, [[ADR-268]]) | 9/9 | KR1 (F1) | ✅ atingido (l1 · #524) |
| A21-KR2 | `fn_rate` no golden multi-ano anotado | ≤ 5% | KR2 (F1) | ✅ atingido (l2 · #533) |
| A21-KR3 | `fp_rate` no golden (red line) | **0%** | KR3 (F1) | ✅ atingido (l2 · #533) |
| A21-KR4 | Previdência cross-axis: plano conta 1× como ativo, dedução não soma ao PL (teste verde) | shipped | F1-O4 | ✅ atingido (l4 · #535, ADR-277) |
| A21-KR5 | ADR-175 `Decidido` em `main` + `test_prompt_injection_defense.py` verde (≥1 fixture por vetor) | shipped | **gate (b) de F3** | ✅ atingido (l5 · #525 + l6 · #527) |
| A21-KR6 | LGPD: audit log Art.37 grava acesso a CPF/financeiro + rota Art.18 export/deleção testada | shipped | KR6 (F2) | ✅ atingido (l7+l8 · #529, ADR-275) |
| A21-KR7 | `restore_drill` recupera Postgres efêmero em CI, RTO medido ≤ 30min | drill local verde | KR4 parcial (F2) | ✅ parcial atingido (l9 · #538 — mecanismo CI; off-site R2 → A22) |

> KR5 hard-block é o teste **mockado/determinístico** em PR; LLM-real nightly
> fica como Should (depende de orçamento de provider). KR7 é **parcial** —
> "mecanismo verde em CI" ≠ "drill off-site executado" (esse fecha na A22).

## Lanes

Hard-rank por **destravamento** (não por frente). Ordem de must-merge:
`l1 → l5 → l6 → l7 → l8` (abrem gates) antes de `l2/l3/l4/l9`. Se a sprint
apertar, l3/l4/l9 escorregam para A22 sem perder os gates.

| Lane | Frente | Prioridade | Effort | Depende de | Owner | Status |
|---|---|---|---|---|---|---|
| [[A21.l1]] | F1-O0 | P0 | M | — | data-engineer | ✅ #524 |
| [[A21.l2]] | F1-O1 | P0 | M | l1 | data-engineer | ✅ #533 |
| [[A21.l3]] | F1-O2 | P1 | L | l1, l2 | senior-cto | ✅ #534 (ADR-276) |
| [[A21.l4]] | F1-O4 | P1 | M | l3 | financial-planner | ✅ #535 (ADR-277) |
| [[A21.l5]] | F3-O3 | P0 | XS | — | senior-cto + prompt-engineer | ✅ #525 |
| [[A21.l6]] | F3-O3 | P0 | M | l5 | prompt-engineer + data-engineer | ✅ #527 |
| [[A21.l7]] | F2-G2 | P0 | M | — | senior-cto + data-engineer | ✅ #529 (ADR-275) |
| [[A21.l8]] | F2-G3 | P0 | M | — | senior-cto + data-engineer | ✅ #529 (ADR-275) |
| [[A21.l9]] | F2-2.1 | P1 | S | — | sre-devops | ✅ #536 + #538 |

> **Colateral:** durante a l9, descoberto bug latente na allowlist do
> gitleaks (`[[allowlists]]` plural inerte com `useDefault = true`).
> Corrigido fora de lane em #541 + #542 (paridade local↔CI), [[ADR-230]] §D3.

## Sequenciamento — 4 trilhas paralelas no dia 1

```
F1:   l1 (INV) ─→ l2 (golden) ─→ l3 (contrato, ADR) ─→ l4 (previdência, ADR)
F3:   l5 (decide ADR-175) ─→ l6 (W3-T05 impl)
LGPD: l7 (Art.37, ADR) ∥ l8 (Art.18, ADR)
F2:   l9 (backup/restore CI)
```

- 4 trilhas arrancam no dia 1 — não compartilham código.
- Único gate interno: l5 (ADR decidido) antes de l6 (impl) — política
  CLAUDE.md, ~30min de overhead, não humano.
- **Nenhuma lane tem `depends_on` em ato do owner.**
- l3, l4, l7, l8 abrem **ADR Proposto antes do PR** (escopo arquitetural).

## Federação (regra anti-drift)

- **l5/l6** implementam fisicamente **W3-T05** do [[PLAN-platform-review]]
  (F3-O3 do plano LAUNCH_TRUST federa essa task). No merge de l6, o checkbox
  W3-T05 em PLATFORM_REVIEW flippa `blocked → shipped` — **não** se
  re-implementa em A22. Owner real é `prompt-engineer` (Layers 2/4 são
  LLM/prompt), corrigindo o `sre-devops` que consta no plano dono.
- **l9** entrega a **metade CI-testável** de W4-T01 (mecanismo backup/restore
  + runbook). O drill off-site real (R2) permanece em PLATFORM_REVIEW/A22.

## Pré-requisitos

- [[PLAN-launch-trust]] mergeado em `main` (PR #517). ✅
- ADR-175 existe como `Proposto` (criado em A11/W1-T06, PR #94). ✅ — l5 só **decide**.

## Bloqueios externos

**Nenhum** — por design. Tudo é engenharia interna ao Mathoms.

## Não-objetivos

- Deploy real em `app.mathoms.ai` / GHCR push / Coolify (viola restrição;
  represado na A20).
- Backup off-site real (R2 bucket + drill em staging) — A22.
- Núcleo de F3 (24 goldens, validação 3 camadas, fallback `needs_review`) —
  A22, agora desbloqueado.
- F1-O3 (dívida cross-year) e F1-O5 (veículo) — Should/Defer no plano dono.
- F2-G1 (HA / SPOF single-host) — Defer (aceite explícito de RTO no launch).
- LLM-real nightly como gate de fechamento de KR5 — Should.

## Follow-ups (A22+)

- **F3 completa** sobre os dois gates abertos pela A21.
- **W4-T01 off-site** — apontar `restore_drill` para R2 real, fechar KR4 full.
- **Deploy** — retomar A20.l4/l5/l9 quando o owner liberar PAT/Coolify.
- **F1-O3 / F1-O5** — novas `EntityDedup` policies sobre o contrato de l3.
