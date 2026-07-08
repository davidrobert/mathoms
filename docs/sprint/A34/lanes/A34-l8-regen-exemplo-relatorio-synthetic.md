---
id: A34.l8
type: lane
title: "Regenerar EXEMPLO_DE_RELATORIO.html sintético"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: regen-exemplo-relatorio-synthetic
adrs: ["[[ADR-320]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/report
---

# A34.l8 — `regen-exemplo-relatorio-synthetic` (W1 · Saneamento)

## Problema

`docs/plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html` (~10.106 linhas) é o
**relatório real do casal** — nome de titular/cônjuge, CPFs, endereço
residencial, patrimônio nominal e transações reais renderizados por extenso.
No flip público (camada-1 do [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md))
é PII de terceiro em arquivo tracked, servida como "exemplo" do produto.

O caminho ingênuo (redigir campo a campo em 10k linhas) é frágil e não
verificável. O caminho errado oposto (deletar o arquivo) perderia o único
artefato que documenta a **cobertura estrutural completa** do renderer Report
Premium — todas as seções 1–9, cards, charts e IDs de âncora.

Restrição herdada do co-design ([[PLAN-public-release]] §Registro de decisões):
**nenhum golden/teste carrega o `.html` em runtime** (nenhuma asserção lê o
arquivo). A única referência viva é uma **docstring** em
`tests/unit/pipeline/test_financial_score_calculator.py:402` que cita linhas
físicas do HTML (`EXEMPLO_DE_RELATORIO.html L1809-1811`) como nota humana de
paridade. Regenerar desloca essas linhas e torna a citação stale — não quebra
CI (é docstring, não assert), mas mente para o próximo leitor se não for
atualizada no mesmo PR.

## Escopo

1. Regenerar `docs/plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html` a partir da
   **fixture dogfood PII-zero** já existente (`tests/fixtures/pipeline_golden/dogfood/`),
   substituindo os dados reais por sintéticos (`Titular`/`Cônjuge`, CPF
   `123.456.789-09`, "Rua Exemplo, 100", valores `R$ X`) e **preservando
   integralmente** a estrutura: todas as seções 1–9, cards, charts e IDs de
   âncora (`id="secao-1"`..`id="secao-9"` e equivalentes).
2. Atualizar a docstring em `tests/unit/pipeline/test_financial_score_calculator.py:402`
   no mesmo PR: (a) o próprio número de linha muda com a regeneração; (b) a
   citação `EXEMPLO_DE_RELATORIO.html L1809-1811` precisa apontar para as novas
   linhas OU — preferível — de-acoplar (citar o `id` de seção/âncora em vez do
   número físico de linha, que é frágil por construção).
3. Adicionar, no topo do `.html` e no [_README do REPORT_PREMIUM](../../../plan/REPORT_PREMIUM/_README.md),
   nota explícita de que o exemplo é **sintético (fixture dogfood, PII-zero)** e
   não representa cliente real — source-of-truth do renderer segue sendo
   `frontend/src/components/report/` ([[ADR-129]]).
4. **NÃO** abrir onda de re-paridade do renderer React nem tocar goldens de
   execução — fora de escopo por decisão do co-design.

## Critério de aceite (verificável)

- `git grep` no `.html` regenerado = zero para nome real de titular/cônjuge,
  CPF real, endereço real, placa e patrimônio nominal do casal (padrões da
  auditoria camada-1).
- **Invariante de paridade estrutural ([[ADR-320]] §B):** o conjunto de
  seções/cards/charts/IDs de âncora do `.html` regenerado é **igual** ao do
  original — zero seção removida, só dados sintéticos. Diff estrutural
  (contagem e IDs) documentado no PR.
- Docstring em `tests/unit/pipeline/test_financial_score_calculator.py:402`
  atualizada (line-ref próprio + citação HTML); `pytest tests/unit/pipeline/test_financial_score_calculator.py -q` verde.
- Gates de doc verdes: `check_doc_links` + `check_adr_anchors` (o `.html` em
  `docs/plan/<X>/` é anexo, ignorado pelos gates de MD — confirmar que nenhum
  wikilink canônico aponta para dado real removido).
- Gates PII/sigilo de [[A34.l4]]/[[A34.l5]]/[[A34.l6]] (W2) **verdes** no HEAD
  após o commit — pré-condição de merge desta lane.

## Rollback

Toca código/teste → **CI obrigatório**. Rollback: revert do PR restaura o
`.html` original e o line-ref anterior. Como o arquivo original contém PII, o
revert só é aceitável **antes** do flip público (janela W1); após W3 (rewrite
de histórico) o blob original não existe mais e o revert falha por design —
esperado. Backup off-site de W0 ([[A34.l2]]) é a rede de recuperação de última
instância.

## Referências

- Plano: [[PLAN-public-release]] §W1 · §Registro de decisões (EXEMPLO_DE_RELATORIO).
- Anexo de auditoria (camada-1): [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
- ADR de paridade estrutural: [[ADR-320]].
- Renderer canônico ([[ADR-129]]): `frontend/src/components/report/`.
- Fixture PII-zero: `tests/fixtures/pipeline_golden/dogfood/`.
- Pares W1: [[A34.l7]] (deletar `_archive/`) · [[A34.l10]] (purgar CPFs+endereço).
