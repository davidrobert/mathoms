---
id: MOC-sprint-a37
type: moc
title: "Sprint A37 — Qualidade do relatório: achados do pipeline-review 2026-07-20"
aliases: ["A37", "Sprint A37"]
sprint_status: candidate
date: "2026-07-20"
theme: "report-quality"
---

# Sprint A37 — Qualidade do relatório (pipeline-review 2026-07-20)

> **Status:** `candidate` — pronto para execução; W0 tem lanes `open`.
> **Origem:** revisão profunda do run completo `6659d62c` (workspace dogfood,
> 2026-07-20, primeiro run com a onda R3 ativa) via skill `pipeline-review`:
> 5 revisores especialistas + 5 verificadores adversariais. Todos os achados
> abaixo **sobreviveram à verificação adversarial com evidência re-derivada
> empiricamente** (incl. medição sobre o artefato E5 real decriptado), no
> mesmo commit em que este sprint foi escrito (`c61c1c29`) — as âncoras
> `arquivo:linha` desta sprint são verificáveis in-repo. O relatório da
> revisão vive em `_scratch/` (gitignored, contém PII); **as lanes são
> self-contained** e não dependem dele.
>
> **Exclusão deliberada:** FIN-06 (repriorização do "não identificado" no
> parecer) ficou **fora** por decisão do owner (2026-07-20). Refutados na
> verificação (CTO-10, FIN-04-núcleo) não viraram lane.

## North Star e KRs

**North Star:** o relatório gerado pelo pipeline fica mensuravelmente mais
**correto** (números certos na base certa), **consistente** (mesmo valor em
todas as superfícies), **completo** (parecer enxerga 100% do contexto; docs
substantivos não morrem sem processamento) e **preciso** (rótulos dizem o que
o número é).

Medição: **re-rodar a skill `pipeline-review` no dogfood ao final da W2**
(run fresco, worker reiniciado — gotcha conhecido).

- **KR-A (completude do parecer):** distiller entrega 10/10 seções do manifest
  no exec context; parecer não sugere explorar dedução de previdência quando o
  E5 informa limite anual = 0, nem alega "ausência de dados de proteção" com
  apólices presentes no E5. Identificadores (nº de apólice, dígitos longos sem
  máscara) **ausentes** do contexto entregue ao LLM.
- **KR-B (consistência):** zero label snake_case cru nas superfícies do
  relatório (orçamento prospectivo + gastos pontuais); narrativa de alocação
  na mesma taxonomia da tabela (v2).
- **KR-C (corretude gateada):** CV17 (conservação de renda passiva) ativo e
  verde em run real; dict de fontes passivas auto-conservativo.
- **KR-D (completude de ingestão):** docs parkados re-tentáveis reclassificados;
  retry não retorna `no_file` para arquivo movido a `inbox_processed/`.
- **KR-E (não-regressão):** re-run da skill sem achado novo Crítico/Alto;
  CVs existentes 15/15 verdes.

## Lanes por onda

Ondas ordenadas por **dependência**, não por tema. Uma lane só abre quando
suas `depends_on` estão `shipped`.

### W0 — destrava (independentes, esforço S; `open`)

| Lane | Achados | Prio | Escopo em 1 linha |
|---|---|---|---|
| [[A37.l1]] (fase ADR) | A: PE-01+DE-02+PE-09+PE-08 · DE-06 · OBS-1 | P0 | **ADR Proposto** do contrato de contexto do parecer (budget, formato por bloco, hints, recovery, redação de identificadores) |
| [[A37.l2]] | PD-01 | P1 | Narrativa da síntese: guard de distribuição vazia + keys dinâmicas |
| [[A37.l5]] | PII-01 | P1 | Exemplo sintético no prompt de apólice (higiene pré-repo-público) |
| [[A37.l6]] | PD-03+PD-08 | P1 | Labels de categoria humanizadas (mapa único compartilhado) |

### W1 — núcleo P0/P1 (depende da ADR da l1)

| Lane | Achados | Prio | Escopo |
|---|---|---|---|
| [[A37.l1]] (fase impl) | idem | P0 | Implementação do pacote: manifest 2.0 + distiller + sanitizer + re-baseline do eval golden |
| [[A37.l3]] | DE-03 | P1 | Self-heal de docs parkados (stored_path drift + gate de key + reclassify) |
| [[A37.l4]] | CTO-02 + DE-07 | P1 | Sentinelas "N/D": guardrail trata como ausência + contrato tipado |
| [[A37.l7]] | CTO-01 + DE-04 | P1 | Conservação de renda passiva: CV17 runtime + shape do dict (compõe com [[A36.l3]]) |

### W2 — coerência e resiliência (P2)

| Lane | Achados | Prio | Escopo |
|---|---|---|---|
| [[A37.l8]] | FIN-03 + FIN-05 + FIN-08 | P2 | Narrativas coerentes (aluguel, alocação v2, IF probabilística) — co-design `financial-planner` |
| [[A37.l9]] | FIN-07+CTO-09 + CTO-04+PE-05 | P2 | Bases/denominadores canônicos (concentração, exposição internacional) — co-design `financial-planner` |
| [[A37.l10]] | PD-09 + PD-04 | P2 | Apêndices: stress card (mapper+copy) e premissas (empty-state) |
| [[A37.l11]] | PD-05 | P2 | Canonicalização de seguradora (code do catálogo + count + display) |
| [[A37.l12]] | CTO-06 + EXEC-01 | P2 | Resiliência: heartbeat in-stage + idempotência de stage LLM em redelivery |
| [[A37.l13]] | CTO-07 | P2 | `pipeline_artifacts.schema_version`/`byte_size`: popular ou dropar (ADR) |

### W3 — cauda (P3 operacional; frontmatter P2 por limite do schema)

| Lane | Achados | Prio | Escopo |
|---|---|---|---|
| [[A37.l14]] | PD-02/06/07/11/12 + PD-10 | P3 | Batch cosmético de copy/labels + decisão de agrupamento do aporte (`financial-planner`) |
| [[A37.l15]] | DE-05 + CTO-08 | P3 | Débitos: fonte de milhas (owner-gated) + remoção do alias deprecated |

## Regras de execução (completude · corretude · consistência · precisão)

1. **Corretude:** bug → **teste de regressão antes do fix**. Toda lane lista o
   teste. Dinheiro nunca é float ([[ADR-090]]); conservação com tolerância zero
   em cents.
2. **Consistência:** mudanças em narrativa/parecer/frontend que citam o mesmo
   número devem apontar para o **mesmo campo SSOT do E5** — se a lane cria um
   segundo produtor do número, ela está errada.
3. **Completude:** critério de aceite de cada lane é **testável e binário**;
   nenhuma lane fecha com "melhorou" sem medição. O sprint fecha só com KR-A..E
   medidos em run fresco.
4. **Precisão:** rótulo declara a base (ex.: "% da carteira produtiva" ≠
   "% da carteira financeira"); sentinelas de ausência viram `null`, não string.
5. **Segurança de execução:** "concluído" = PR **squash-merged em `main` com CI
   verde**. Diff >300 linhas → quebrar em PRs sequenciais. `l1` exige ADR
   `Proposto` **antes** do PR de implementação (invariante de contexto do
   parecer). Zero PII em lane/ADR/commit (papéis, faixas; nunca nº de
   apólice/documento). Gate de sigilo de metodologia se aplica a docs novos.
6. **Co-design:** l8/l9/l14 têm decisão de domínio — 1 rodada com o
   especialista indicado; objeção persistente → `senior-cto` decide e fecha.
7. **Pickup:** protocolo padrão (worktrees + branches `agent/*` <24h; slug da
   lane = `branch_slug` do frontmatter).

## Riscos do sprint

- **l1 muda o conteúdo do parecer por design** (mais contexto ⇒ texto diferente).
  Mitigação: re-baseline do eval golden na própria lane + KR-A medido em run real.
- **l7/l9 tocam campos consumidos por parecer/manifest** — coordenar bump de
  `manifest_version` com a l1 para evitar dois bumps concorrentes.
- **Owner-gated:** l15 (decisão de fonte de milhas) e parte da l14 (decisão de
  agrupamento do aporte) não bloqueiam as demais.
