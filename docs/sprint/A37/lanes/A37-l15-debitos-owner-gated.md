---
id: A37.l15
type: lane
title: "Débitos com gate: fonte de dados de milhas (decisão owner) + remoção do alias deprecated de caixa"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l15-debitos-owner-gated
adrs: ["[[ADR-147]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/pipeline
  - area/dados
---

# A37.l15 — `debitos-owner-gated` (DE-05 + CTO-08) — prioridade operacional P3

> Frontmatter marca P2 por limite do schema; tratar como **cauda** (W3).
> DE-05 é **owner-gated** (decisão de produto); CTO-08 tem janela própria.

## DE-05 — fonte de dados de milhas (evidência 2026-07-20 @ c61c1c29)

O card de milhas está vazio por **ausência de fonte**, não por bug de leitura:
o artifact E4 `pontos_milhas` é um placeholder `{"dados": []}` **por design**
(`pipeline/domain/services/e4_serialization.py:122`); o E5 lê
`<workspace>/notes/milhas.md` (`scripts/analyze_finances.py:1791`, decisão
[[ADR-147]]) que não existe no workspace; e a entidade DB (`MileageProgram`,
fase A8.1 da ADR-147) nunca foi entregue.

**Ação:** apresentar ao owner as opções — (a) entregar A8.1 (entity DB +
deprecar `parse_milhas_md`), (b) manter notes como fonte e **sunset** do
placeholder E4 (produtor inútil), (c) descontinuar o card. Executar a escolhida.

## CTO-08 — remoção do alias deprecated (evidência idem)

`patrimonio_calculator.py:220-227` emite `caixa_total_brl` + alias deprecated
`caixa_moeda_estrangeira` ("mantido por 1 ciclo", R3.4b/#986) — e o mesmo nome
de chave significa caixa ME **real** em `reserva_liquidez.py:60-70`. Sem
consumidor vivo lendo o significado errado (verificado: fallbacks usam
semântica de total; frontend só tipa), mas a colisão semântica não deve
sobreviver à janela.

**Ação:** ciclo seguinte ao R3.4b → remover o alias do produtor + schema
(`e5_analysis.schema.json:99-101`) + tipos do frontend; varrer consumidores;
**não reusar** o nome com outro significado.

## Critério de aceite

- DE-05: decisão do owner registrada (emenda ADR-147 ou nota) + implementação
  da opção escolhida com teste (card com dado renderiza / placeholder removido
  sem quebrar E4).
- CTO-08: grep sem hits de `caixa_moeda_estrangeira` em `patrimonio.*`
  (produtor, schema, tipos); payload golden atualizado; CVs verdes.

## Risco

Baixo; CTO-08 é mudança de contrato — mesma disciplina da [[A37.l7]]
(varredura de consumidores no PR).
