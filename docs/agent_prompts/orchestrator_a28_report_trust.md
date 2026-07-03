# Orquestrador — Sprint A28 "Report Trust"

> Prompt self-contained para atacar a A28 em **nova sessão**. Sprint `current` desde
> 2026-07-03. Plano dono: [[PLAN-report-trust]] (`docs/plan/REPORT_TRUST/_README.md`).
> Origem: revisão completa do relatório dogfood `72883bde` (2026-07-03). Pré-revisado
> em co-design 2026-07-03: `product-manager` + `information-architect` +
> `data-engineer` + `prompt-engineer` (+ `financial-planner` e `product-designer` no
> parecer de origem).
>
> **Quando arquivar:** sprint A28 `done` (Onda 0 inteira shipped no mínimo; Ondas 1-2
> conforme corte) — `git mv` para `archive/` com data.

## 0. Antes de qualquer coisa (protocolo de início)

```bash
git fetch origin && git status && git log --oneline origin/main..HEAD -10
git log --oneline -5 -- CLAUDE.md
git worktree list && git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' refs/remotes/origin/agent/ | head -15
```

Leia `CLAUDE.md`, `docs/sprint/A28/_README.md` (MOC desta sprint) e a lane que for
atacar. Crie branch `agent/a28-<branch_slug-da-lane>/<yyyyMMdd-HHmm>` ANTES de editar
(worktree `.claude/worktrees/` reverte edits uncommitted entre turnos).

## 1. Tese da sprint

O relatório dogfood contém três recomendações que, se seguidas, **pioram** a situação
do cliente: desacelerar aporte (TRS fictícia 22,63% a.a.), desmobilizar carteira
produtiva (reserva "Excessiva" com numerador = todo o investível) e cortar gasto errado
(rótulo Cerbasi "Gastador" sobre R$ 401k de despesa opaca). Duas são **violação de
contrato escrito** ([FORMULAS.md](../reference/FORMULAS.md) §Reserva · [[ADR-191]]).
A sprint fecha o gap entre o que o relatório *afirma* e o que os dados *sustentam*:
fórmulas (Onda 0) → loop de dados (Onda 1) → apresentação honesta (Onda 2).

## 2. As 11 lanes — ondas, corte e ordem

| Lane | Onda | Corte | Dep / gate |
|---|---|---|---|
| [[A28.l4]] `mensalizacao-base-unica` | 0 | Must | T0 = ADR `Proposto` · **antes de l1** |
| [[A28.l1]] `reserva-formula-canonica` | 0 | Must | l4 mergeada |
| [[A28.l2]] `trs-universo-consistente` | 0 | Must | — (∥) |
| [[A28.l3]] `pgbl-ano-base-unico` | 0 | Must | T0 = ADR `Proposto` (∥) |
| [[A28.l5]] `nao-identificado-learning-loop` | 1 | Should | código autônomo; KR2 pós-`G-owner-reclassify` |
| [[A28.l6]] `protecao-apolices-flow` | 1 | Should | alvo = `compute_protecao` ([[ADR-240]]), não só balde E4 |
| [[A28.l7]] `imoveis-excluidos-dedup` | 1 | Should | dedup tático; re-medição pós-`G-owner-label` |
| [[A28.l8]] `higiene-ingestao-periodos` | 1 | Should | NÃO tocar `generate_legacy_filename` |
| [[A28.l10]] `ancoras-formatter-curadoria` | 2 | Should | **∥ desde o dia 1** |
| [[A28.l9]] `report-data-quality-banner` | 2 | Should | skeleton ∥ · merge após Onda 0 |
| [[A28.l11]] `parecer-guardrails-pos-llm` | 2 | Should | consome flag TRS da l2 · merge após Onda 0 |

**Ordem:** Onda 0 = `[l4 → l1] ∥ l2 ∥ l3`. Onda 1 toda paralela. Onda 2: l10 livre;
l9/l11 seguram merge até Onda 0 mergear. **Nunca cortar l1/l2.**

## 3. Regras que as lanes NÃO podem violar

- **ADR `Proposto` antes de PR de implementação** em l4 (política de base temporal,
  co-design `financial-planner` + `senior-cto`) e l3 (regra de ano-base PGBL, co-design
  `financial-planner`). l1/l2 conformam contrato existente — sem ADR nova.
- **Dinheiro nunca é float** ([[ADR-090]]); goldens re-snapshotados com diff explicado
  no PR (nunca rebaseline silencioso); função nova → teste; fixtures PII-zero.
- **Parecer:** coerce no boundary, nunca raise ([[ADR-292]]/[[ADR-294]]); nenhum
  guardrail novo marca `needs_review` (budget ≤15% do gate [[A26.l2]]); `PROMPT_VERSION`
  bump se tocar prompt/manifest.
- **Frontend:** `tsc --noEmit` local antes do push (PR-CI não roda typecheck);
  cores via tokens; valores monetários via `<MonetaryValue/>`.

## 4. Gates de ação-do-owner (fila do owner)

1. **`G-owner-reclassify`** — reclassificar os maiores ofensores de
   `nao_identificado` (pós-código da l5). Destrava avaliação do KR2 (<5%).
2. **`G-owner-label`** — rotular os imóveis pendentes em Configurações (pós-dedup da
   l7, ~7-8 CTAs). Destrava re-medição da concentração.
3. **Contínuo:** re-gerar o parecer a cada marco (Onda 0 mergeada; Onda 1 mergeada) —
   acumula as ≥20 gerações que destravam [[A26.l2]]/[[A26.l4]] (sinergia; NÃO é KR).

## 5. KRs (ver MOC para definição completa)

KR1 conformidade de fórmula (reserva/TRS) · KR2 `nao_identificado` <5% pós-gate ·
KR3 zero contradição cross-seção (PGBL único; rótulo de janela; Cerbasi coerente) ·
KR4 honestidade de apresentação (teste de honestidade; fallback com ressalva; âncoras
tipadas).

## 6. Definition of done

PR mergeado em `main` via squash com CI verde por lane; lane flippada
`planned → in_progress → shipped` no frontmatter (com `ship_pr`/`ship_date`);
`python3 dev/build_doc_index.py --inline` regenerado no mesmo PR de docs; ADRs de
l3/l4 flippadas `Decidido (A28)` no merge da implementação; ao fim da sprint,
reavaliar retomada da A26 (`paused → current`) se as gerações qualificadas ≥20.
