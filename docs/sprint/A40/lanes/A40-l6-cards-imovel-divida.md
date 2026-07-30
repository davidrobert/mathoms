---
id: A40.l6
type: lane
title: "Cards de imóvel e dívida: PII cartorial, contrato de campo e zero-como-valor"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P1
branch_slug: a40-l6-cards-imovel-divida
adrs: ["[[ADR-337]]"]
depends_on: ["[[A40.l5]]"]
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p1
  - area/frontend
  - area/backend
---

# A40.l6 — `cards-imovel-divida` (RV3-06, RV3-12, RV3-27)

## Problema

**PII (RV3-06).** Descrição cartorial crua do IRPF é interpolada **verbatim** em
`RealEstateYieldCard.tsx:194,303,373` e `EndividamentoCard.tsx:75`: identificador
de terceiro em claro, matrícula, inscrição municipal, endereço com CEP. A
[[ADR-337]] é escopada a `top_ativos[].nome` e seu **critério 4 (gate de PII no
view-model) não existe**. O pior vetor (egresso ao LLM) já está fechado pelo
sanitizer; o residual é minimização violada em **artefato exportável**.

**Contrato (RV3-12).** O card lê `d.valor`/`d.taxa`; o E5 emite
`saldo_devedor`/`taxa_juros`/`parcela_mensal`. Sem adapter no boundary → a linha da
dívida exibe `—` no valor.

**Zero-como-valor (RV3-27).** Valor de imóvel `0` renderiza como zero real, contra
a regra de copy (ausência ⇒ `—`).

## Escopo

- UI exibe rótulo curto derivado (`endereco_canonical`), não `descricao` bruta.
  Descrição completa, se necessária, atrás de disclosure **com redação**.
- Emenda [[ADR-337]]: criar o critério 4 — gate de PII sobre o view-model.
- Alinhar o tipo ao contrato E5 (consequência da [[A40.l5]]).
- Valor ausente ⇒ `—`, e **não** calcular derivados sobre base ausente.
- Tabela → cards abaixo de `md` (descrição longa quebra a tabela em mobile).

## Critério de aceite

- KR-D: gate bloqueia fixture sintética com identificador de terceiro + matrícula +
  endereço no campo de descrição, citando o dot-path ofensor.
- **Teste do gate:** removê-lo faz a fixture passar — senão o teste não testa o gate.
- Três casos no teste do card: valor `null` ⇒ `—` e **sem** derivado; `0` ⇒ decisão
  explícita enquanto a origem não for saneada; valor real ⇒ renderiza.
- **Verificação renderizada:** gerar o PDF e rodar `pdftotext` procurando os
  identificadores da fixture. O bloco de excluídos provavelmente não sai no PDF (o
  print CSS não força `details[open]`), **mas está no HTML servido** — conferir as
  duas superfícies.
