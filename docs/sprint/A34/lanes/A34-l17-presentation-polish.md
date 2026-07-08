---
id: A34.l17
type: lane
title: "Polish de apresentação (should, pós-flip / A35)"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P2
branch_slug: presentation-polish
adrs: []
depends_on: ["[[A34.l16]]", "[[A34.l8]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p2
  - area/docs
---

# A34.l17 — `presentation-polish` (W6 · Apresentação)

## Problema

O marco de **público-seguro** (caminho crítico W0→W2→W1/W5→W6-min→W3/W4→W8)
entrega LICENSE + README com disclaimer ([[A34.l16]]) — o mínimo que, ausente,
causa dano legal ou expectativa falsa. Mas o repo público fica **cru de
percepção**: sem código de conduta, sem screenshot do relatório, sem badges de
CI/licença, sem diagrama de arquitetura, e com um `CONTRIBUTING.md` que **assume
o fluxo de agentes internos** (branches `agent/<slug>/<ts>`, worktrees,
protocolo de pickup do BACKLOG) — ininteligível para um contribuidor externo.

Nada disso move a agulha de **risco** — é cosmético. Por isso é `should`
pós-flip (janela A35), P2, e **não bloqueia o marco de segurança**. O único
invariante que herda do plano: nenhum artefato de polish pode **reintroduzir
PII ou atribuição nominal metodológica** que W1/W2 removeram.

## Escopo

1. **`CODE_OF_CONDUCT.md`** — Contributor Covenant (versão estável), com
   contato de report apontando para o canal já definido em `SECURITY.md` (não
   inventar e-mail novo, não expor conta pessoal).
2. **Screenshot sintético** — captura do `EXEMPLO_DE_RELATORIO` **regenerado em
   [[A34.l8]]** (fixture dogfood PII-zero,
   `tests/fixtures/pipeline_golden/dogfood/`). **NUNCA** o relatório real. Todo
   valor visível na imagem é sintético (`Titular`/`Cônjuge`, `R$ X`,
   `Rua Exemplo, 100`).
3. **Badges** — CI (status do workflow) + licença (coerente com [[ADR-313]]) no
   topo do README. Badges apontam para o repo público já flipado.
4. **Diagrama de arquitetura** — visão de alto nível (pipeline E0→E7, backend,
   frontend). Gerado de fonte versionada (ex.: bloco Mermaid no `.md`), sem
   embutir nomes/paths de terceiros. Diagrama é apresentação, não source of
   truth — a fonte canônica permanece [ARCHITECTURE.md](../../../reference/ARCHITECTURE.md).
5. **Adaptar `CONTRIBUTING.md`** — seção para contribuidor externo (fork → PR,
   Conventional Commits, rodar a suíte, gates de pre-commit) **sem** vazar o
   protocolo interno de agentes/worktrees/pickup do BACKLOG. Manter o fluxo
   interno numa seção separada e claramente rotulada, ou mover para doc interno.

## Critério de aceite (verificável)

- `CODE_OF_CONDUCT.md`, screenshot sintético (arquivo de imagem + referência no
  README), badges de CI+licença no README, diagrama de arquitetura e
  `CONTRIBUTING.md` adaptado — **todos presentes**.
- **Nenhum artefato reintroduz PII/atribuição:** os gates estendidos de W2
  passam verdes sobre os novos arquivos — `python3 tests/utils/lint_no_real_pii.py`
  + `python3 dev/check_sigilo_terms.py` (superset público, [[A34.l4]]/[[A34.l5]])
  = zero hit no diff desta lane.
- Screenshot: verificação manual de que toda label/valor é sintético; a imagem
  deriva do EXEMPLO de [[A34.l8]], não do original.
- `CONTRIBUTING.md` externo não menciona `agent/<slug>`, worktrees, nem pickup
  do BACKLOG na seção voltada ao contribuidor externo.
- `python3 dev/check_doc_links.py` verde (links do README/CONTRIBUTING/COC
  resolvem).

## Rollback

Docs-only + asset de imagem — **mergeia sem CI** (regra docs-only do CLAUDE.md;
nenhum runtime tocado). Rollback = `git revert` do PR; remove COC/badges/diagrama
sem afetar o marco de público-seguro (que já fechou em W6-min/[[A34.l16]]). O
screenshot é asset estático; deletá-lo não quebra teste algum (nenhum golden
carrega o EXEMPLO — só docstring line-ref, tratada em [[A34.l8]]).

## Notas

- **Pós-flip (A35).** Depende de [[A34.l16]] (LICENSE+README como base a
  enriquecer) e de [[A34.l8]] (EXEMPLO sintético como fonte do screenshot).
  Abrir só após o flip ([[A34.l22]]) — antes disso não há repo público para os
  badges apontarem.
- **Fronteira de idioma:** artefatos de apresentação em EN seguem [[ADR-318]];
  o vault permanece PT-BR. `CONTRIBUTING.md`/COC em EN são refinados na
  [[A34.l23]] (W7) — esta lane pode nascer PT-BR e a l23 reconcilia.
- Par natural com o `product-designer` (visual do screenshot, hierarquia do
  README) — mas cosmético, sem co-design bloqueante.

## Referências

- Plano canônico: [[PLAN-public-release]] (§Ondas — W6 Apresentação).
- Base a enriquecer: [[A34.l16]] (LICENSE + README + disclaimer).
- Fonte do screenshot: [[A34.l8]] (EXEMPLO regenerado sintético).
- Gates anti-regressão: [[A34.l4]] · [[A34.l5]] (superset público).
- Fronteira de idioma / docs-EN: [[ADR-318]] · [[A34.l23]].
- Licença (badge): [[ADR-313]].
