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
- **Verificação renderizada** — spec com fixture contendo identificadores
  **sintéticos** (PII-zero: documento fictício, matrícula e endereço inventados) no
  campo de descrição. Assere que não aparecem em `page.inner_text('body')` **nem** no
  PDF (padrão de `print.@critical.spec.ts` + `pdftotext -layout`). As duas superfícies
  divergem: o print CSS não força `details[open]`, então o bloco colapsado pode não
  sair no PDF **e ainda assim** estar no DOM servido — testar as duas.

## Itens adotados (2026-08-05)

### `s1` publica "residência própria de R$ 0,00" (movido da [[A40.l5]])

Mesma classe do RV3-27 (zero-como-valor) que esta lane já é dona; a l5 registrou o
item em §Escopo herdado e devolveu a decisão ao dono, que o moveu para cá em
2026-08-05 (ver [[ADR-356]] §Emenda 2026-08-05).

- **Arquivo é `pipeline/`, não frontend:** o f-string do `s1` em
  `pipeline/domain/services/narrativas/summaries_narrator.py` (a parcela
  `residência própria de {…}`). A regra já está decidida — [[ADR-356]] §D7 ("ou o
  número vem do payload, ou não é afirmado") — e a implementação-precedente é
  `_S4_VALOR_TEMPLATES` + `_s4_portfolio_head`, no mesmo módulo: parcela
  condicional a `> 0`. **Não** é redecisão de produto; é aplicar a regra à parcela
  que ficou fora da lista fechada da l4.
- **Independe do `depends_on: [[A40.l5]]`** desta lane: o item não passa pelo
  codegen nem pelo gate de contrato. Pode ir em PR próprio, antes da l5.
- **Coordenar com a [[A40.l15]]**, que também edita esse módulo (decisão do `s3`).
  Hunks disjuntos (`s1` vs `_summary_s3`); quem chegar depois rebaseia.
- Aceite: fixture com `residencia = 0` ⇒ a parcela **não é afirmada** (nem
  "R$ 0,00", nem `—` dentro da frase); com valor real ⇒ afirmada. Prova por
  mutação: restaurar o f-string incondicional deixa o teste vermelho.

### `perfil_familia.right` publica `n_imoveis` (da [[A40.l4]] §Residual)

Follow-up órfão da [[A40.l4]] §Residual: `perfil_familia.right` publica
`{n_imoveis} imóvel/imóveis` de forma independente do card S4 — a mesma contagem
que a l4 deixou de afirmar na tabela da S4 por já estar sob suspeita (fonte que não
é a da seção). Contradição **cross-seção**, não intra-seção, e pré-existente à l4.

- Fonte única: `perfil_familia.right` passa a ler a mesma contagem canônica que a
  tabela da S4 usa — não reabre o cálculo, só corrige o consumo.
- Critério de aceite: fixture com a S4 suprimindo a contagem (fonte suspeita) ⇒
  `perfil_familia.right` também suprime, não afirma número órfão.
- Verificação renderizada: card de perfil e tabela S4 no mesmo payload mostram o
  mesmo número, ou os dois ausentes.
