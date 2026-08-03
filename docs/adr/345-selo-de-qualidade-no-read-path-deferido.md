---
id: ADR-345
type: adr
title: "Propagação do taint E2→E5 e selo de qualidade no read-path — adoção deferida"
status: Roadmap
phase: "A39 → REPORT_TRUST"
date: "2026-08-03"
relates_to:
  - "[[ADR-358]]"
  - "[[PLAN-report-trust]]"
supersedes: []
superseded_by: []
aliases: ["ADR 345", "selo de qualidade read-path", "taint E2 para E5"]
tags:
  - type/adr
  - status/roadmap
  - area/pipeline
  - area/frontend
  - phase/a39
---

# ADR-345 — Propagação do taint E2→E5 e selo de qualidade no read-path (adoção deferida)

**Status:** Roadmap • **Data:** 2026-08-03 • **Relaciona** [[ADR-358]] (governança
de decisão condicionada a evidência futura), [[PLAN-report-trust]] (destino do
trabalho).

> **Esta nota registra a decisão de DEFERIR, não o design.** O mecanismo do selo
> está **por decidir** e exige co-design de `product-designer` +
> `data-engineer` + `financial-planner` quando o trabalho abrir. Ler o escopo
> abaixo como delimitação do problema, não como solução escolhida.

## Contexto

A Sprint A39 fechou a certificação de ingestão: o dado **entra** correto. Mas o
KR-A daquela sprint garante o **E2**, não o KPI que o usuário lê — a qualidade
medida na ingestão não se propaga até a camada de apresentação. Registro original,
disperso em `docs/sprint/A39/_README.md` §Deferidos: *"Selo (E2→E5) = ADR-345 nova
(read-path) → deferida a REPORT_TRUST"*, e a ressalva do `financial-planner`:
*"até ADR-345 aterrissar, input escalado ainda pode"* chegar ao relatório sem
sinal de procedência degradada.

O gap concreto: quando um documento é parseado com cobertura parcial, checksum
divergente ou período implausível, o E2 sabe — e o E5 e o relatório não. O número
chega ao usuário indistinguível de um número de origem limpa.

Duas superfícies **distintas**, que não devem ser confundidas:

- **Esta ADR — qualidade de dado extraído.** O selo diz "este número vem de uma
  extração com ressalva". É propagação de metadado de procedência pelo read-path.
- **[[A40.l22]] — retenção de conselho gerado.** Declara que o parecer retirou N
  itens ou não foi publicado. É honestidade sobre geração LLM, não sobre extração.

Elas se parecem (ambas são "o relatório declara uma limitação") e por isso foi
tentador fundi-las. Não se fundem: a fonte do sinal, o produtor e o ciclo de vida
são diferentes.

## Decisão

**Deferir a adoção**, mantendo o problema registrado e endereçável. A ADR existe
para (a) tornar as referências da A39 resolvíveis por wikilink — antes eram texto
puro, invisível a `dev/check_doc_links.py`, e o ID ficava roubável; (b) delimitar
o escopo para que quem retomar não o confunda com a superfície da [[A40.l22]].

**Condição de retomada:** quando a frente 3 de [[PLAN-report-trust]]
("apresentação honesta") avançar para propagação de metadado, ou quando um achado
de revisão demonstrar número de origem degradada chegando ao usuário sem sinal.

**Nada aqui autoriza implementação.** Retomar exige promover esta nota a
`Proposto` com o design escolhido, per [[ADR-358]].

## Alternativas rejeitadas

- **Absorver a superfície de degradação da [[A40.l22]] nesta ADR** — foi a
  primeira sugestão de forma, e a rejeitamos: os escopos são distintos (ver
  §Contexto) e o encaixe forçado faria a ADR mentir sobre o próprio escopo.
- **Aposentar a reserva sem escrever a nota** — perderia o gancho: o trabalho do
  selo voltaria a não ter registro resolvível, e as 5 menções na A39 apontariam
  para o nada.

## Consequências

- As menções em prosa na A39 e em `SPRINTS-active` passam a ser wikilinks, logo
  protegidas por `dev/check_doc_links.py`.
- **Lição de forma, generalizada em [[ADR-358]] §Consequências e no CLAUDE.md:**
  **nunca reserve ID de ADR; reserve o trabalho.** O ID é recurso global
  monotônico alocado na escrita (`ls docs/adr/ | tail`); uma reserva só funciona
  se o alocador a consultar — logo ou ela vive **dentro** do namespace (o arquivo
  existe, que é o que esta nota faz) ou não existe. Trabalho deferido vive como
  §Deferimento datado com dono no plano, que é wikilink-ável. Precedente:
  [[ADR-356]].
- Débito aberto, **fora** desta nota: gate que exija que `ADR-\d{3}` citado em
  prosa (fora de wikilink e de code fence) resolva para arquivo existente. Toca
  `dev/` + `.pre-commit-config.yaml` e precisa de whitelist para o shim
  `DECISIONS.md` e `docs/archive/**` — lane [[A40.l23]].
