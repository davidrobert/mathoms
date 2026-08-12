---
id: A40.l46
type: lane
title: "Follow-ups órfãos da A40.l43: o que o co-design achou na vizinhança e ninguém está atacando"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l46-followups-orfaos
adrs:
  - "[[ADR-356]]"
  - "[[ADR-319]]"
  - "[[ADR-236]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/frontend
  - area/pipeline
---

# A40.l46 — `followups-orfaos-da-l43`

> **Aberta em 2026-08-12**, a pedido do dono: *"todos os follow-ups (ou achados que
> estão em aberto) que não estão sendo atacados deveriam estar documentados em uma
> nova lane no fim do sprint A40"*. Cumpre a convenção que o §Inventário de
> follow-up já declara — **um item ou tem lane, ou tem disposição escrita; item que
> tem só descrição evapora no fim da sprint**.
>
> **Prioridade e onda são propostas, não decididas.** Colocação, prioridade final e
> agrupamento em onda são gatilho de `product-manager` — a lane existe para que os
> itens paremde evaporar, não para pautar a sprint.

## O que esta lane é (e o que não é)

O co-design da [[A40.l43]] rodou com `prompt-engineer` + `financial-planner` +
`product-designer` e escalou ao `senior-cto`. Os quatro apontaram defeitos
**vizinhos** ao escopo, que a l43 deliberadamente não atacou para não virar lane
guarda-chuva. Aqueles que **têm dono** foram roteados e estão escritos na lane
receptora — [[A40.l6]] (contagem de imóveis, quitada por remoção), [[A40.l15]]
(política de diversificação), [[A40.l29]] (premissas de IF + forma do ramo de prazo
ausente). **Esta lane recebe só o que sobrou sem dono.**

Cada item abaixo diz **o que foi medido** (com arquivo:linha) e **o que não foi**.
Item não medido está marcado como tal — não escrevo achado alegado como fato.

## Itens

### 1. As 5 fixtures E2E restantes têm o contrato morto — os estados vazios da seção de identidade nunca foram vistos

**Medido em 2026-08-12** (`frontend/tests/e2e/fixtures/reports/*.json`):

| fixture | shape de `narrativas.perfil_familia` |
|---|---|
| `medium.json` | `{left}` ✅ (corrigida pelo #1382) |
| `degraded.json` | `str` ❌ |
| `janela-divergente.json` | `str` ❌ |
| `large-values.json` | `str` ❌ |
| `long-strings.json` | `str` ❌ |
| `sparse-data.json` | `str` ❌ |

`PerfilFamiliaSection` lê `perfil?.left` de um objeto; com string, `parseParagraphs`
recebe `undefined` e a narrativa não renderiza. Nessas 5 a seção só aparece se o
roster tiver membro com CPF — logo **os estados vazios por metade** (só roster / só
narrativa / `null` quando ambos faltam), que são o desenho declarado da seção,
**nunca apareceram** em baseline visual, print ou axe.

- **Por que importa mais agora:** a l43 mudou o layout da prosa (`sm:columns-2` com
  fallback de 1 coluna em ≤2 parágrafos). O caso de 1 parágrafo — workspace de uma
  pessoa, que o PRODUCT.md admite — não tem baseline.
- **Fix:** corrigir as 5 para `{left: "<p>…</p>"}` com conteúdo coerente com o
  cenário de cada uma (`degraded` degradado, `sparse-data` curto, `long-strings`
  longo), e rodar `print.@critical` + visual + axe. **Primeira baseline do bloco tem
  de ser olhada, não commitada às cegas.**
- **Trava:** a fixture é escrita à mão, então descreve o que o produtor **não**
  necessariamente emite. O #1382 caiu nisso: pôs em `right` um parágrafo de "Plano
  de vida centrado na consolidação patrimonial…" que o narrador nunca produziu.
  Derive o conteúdo do produtor (a fixture do E5.N em
  `tests/fixtures/narrativas/e5n_delivery.json` é gerada) em vez de inventar.

### 2. Heading order do relatório: h1 → h3 → h2, e o Sumário Executivo não tem heading

**Medido em 2026-08-12:**

- `frontend/src/components/report/ReportCard.tsx:45` emite `<h3>` **fixo**, sem
  prop de nível.
- `frontend/src/components/report/ExecutiveSummarySection.tsx:30` tem apenas
  `aria-label="Sumário Executivo — Indicadores-chave"` — **nenhum heading**.
- Sequência real do documento: `h1` (capa) → `h3` (card de nível de documento) →
  `h2` (S1).
- O gate roda `critical+serious` (`frontend/tests/e2e/reports/a11y.@critical.spec.ts`),
  e `axe` classifica `heading-order` como **`moderate`** — então **não pega**.

Duas consequências distintas: a ordem quebrada é violação de WCAG 1.3.1 que o gate
não vê; e o bloco protagonista do relatório não tem âncora navegável para leitor de
tela.

- **Fix:** prop de nível no `ReportCard` (`titleAs?: "h2" | "h3"`) + `h2` nos cards
  de nível de documento + heading visível ou `sr-only` no Sumário Executivo.
  Rebaseline visual esperado.
- **Decisão embutida:** alargar o gate axe além de `critical+serious` para pegar
  `heading-order`, ou adicionar assert dedicado de ordem de heading? Alargar traz
  o resto do `moderate` junto — medir o backlog antes.
- **Cuidado:** [[ADR-236]] declara "A11y AAA" e **todos** os gates medem AA — o
  helper do axe monta `withTags` até `wcag21aa`, registrado em
  [A11Y_CHECKLIST §Nível AAA](../../../plan/REPORT_PREMIUM/A11Y_CHECKLIST.md).
  Débito distinto deste; não fundir os dois.

### 3. As 6 lanes que estão fora da tabela §Lanes — o §Gate de saída não as vê

**Medido em 2026-08-12:** `ls docs/sprint/A40/lanes/*.md` dá **44**; a tabela
§Lanes do `_README` lista **38**. Ausentes: **l38** (caixa canônico, #1391),
**l39** (posição corrente/fiscal), **l40** (identidade institucional CNPJ raiz),
**l41** (frescor cross-pool), **l42**, **l44** (janela declarada, #1397/#1398).

O contador foi corrigido no #1405 para declarar os dois números em vez de escolher
um, e as ausentes ficaram **nomeadas por id** numa nota datada. Mas isso registra a
dívida, não a paga: o **§Gate de saída lê esta tabela**, e lane fora dela é
invisível ao encerramento.

- **Fix:** uma linha na tabela por lane, com rótulo curto + prioridade + deps. Não
  foi feito na l43/#1405 porque a coluna Título é **rótulo editorial** e quem escreve
  precisa do contexto da lane — inventar rótulo produziria a divergência que a
  própria convenção da tabela adverte.
- **Nota de processo:** 3 colisões de id de lane numa sessão (l38→l41→l43, e o l45
  já reivindicado pelo #1387, que esta lane evitou indo para l46). A causa é a
  mesma: a tabela e o disco divergem, então "próximo id livre" medido na tabela
  mente. Meça sempre no **disco** e cruze com títulos e arquivos de **PR aberto** —
  o precedente da sprint é a renumeração l25→l26→l27 em #1167/#1170.

### 4. Substrato declarado de plano de vida — feature deferida, com escopo pronto

Não é débito: é a **feature que o pedido original da l43 queria** e que não pôde ser
feita porque não existe onde a família declarar projeto de vida (`FamilyMember` tem
JSON livre de biografia; `Goal` é numérico; `Decision` é plano de ação financeiro).

Escopo mínimo anti-campo-lixo, especificado pelo `financial-planner` no co-design:

| Campo | Shape | Número que muda |
|---|---|---|
| Evento de liquidez previsto | `{tipo: enum, ano, valor_estimado_brl, confianca: enum}` | trajetória IF, `meta_aporte_mensal`, prazo |
| Mudança de país/cidade | `{pais_destino, ano, custo_transicao_brl}` | alvo de reserva, `goal.dolarizacao`, residência fiscal |
| Novo dependente previsto | `{ano}` | custo essencial projetado, reserva, dependentes IRPF |
| Alteração de renda prevista | `{membro_id, ano, natureza: enum}` | `perfil_renda` ⇒ `meses_alvo`, taxa de poupança projetada |

Critérios que o `financial-planner` travou: **todo campo declarado tem de mudar um
número que já existe** (campo que só alimenta prosa é decoração, e prosa sobre campo
livre é superfície de fabricação); **vocabulário fechado + ano + valor, nunca texto
livre**; ausência silenciosa ([[ADR-356]] §D7); coletado onde o número é editado;
**máx. 5 campos**, cada um com consumidor nomeado antes de existir. **Não coletar
horizonte** — `goal.if.horizonte_anos` já existe.

- **Exige ADR `Proposto` própria, e o gatilho é PII**, não a forma do narrador: um
  campo de texto livre autorado pelo usuário caindo **verbatim** num artefato
  entregue e no PDF é nova superfície das classes que [[ADR-356]] §D9 e [[ADR-319]]
  removeram deste exato card (endereço, nome completo de adulto e de menor). A ADR
  decide contrato de redação/consentimento **e** a exclusão explícita do campo de
  qualquer contexto LLM (manter a exclusão DE-I.8 e fora do enum de `get_e5_section`).
- **Trava histórica:** "mudança de país" declarada por família é legítima; **modo de
  relatório** por país não é — foi o que a [[ADR-168]] matou. Um campo, não um modo.
- **Onde aterrissa:** o slot da prosa do perfil, o mesmo que a l43 esvaziou. Por isso
  esta feature **depende** de a [[A40.l29]] §Escopo 2 ter decidido o que vai no par
  número-projetado/premissa — sem isso, não há onde pousar sem recriar a duplicação.

## Critério de aceite

Esta é uma lane de **registro + execução opcional**. O aceite mínimo é que nenhum
item evapore:

- Cada item acima tem **fix mínimo escrito** e **medição citada com caminho de
  re-medição** — não "descrição solta" (a convenção do §Inventário).
- Item executado sai desta lane para o histórico com sha de merge; item não
  executado ao fim da sprint tem disposição escrita (`§Fora do sprint` ou lane da
  sprint seguinte), **nunca** deleção silenciosa.
- Itens 1 e 2 têm prova por mutação quando executados: reverter o fix deixa o teste
  vermelho. Item 1 exige **baseline olhada** — o card nunca esteve em imagem
  nenhuma, então a primeira é a primeira vez que alguém vê.

## Fora de escopo

- **Tudo que já tem dono**: contagem de imóveis ([[A40.l6]]), política de
  diversificação/concentração ([[A40.l15]]), premissas de IF e forma do ramo de
  prazo ausente ([[A40.l29]]). Repetir aqui criaria segunda fonte de verdade.
- **O que a l43 entregou** — remoção de `perfil_familia.right`, transferência da
  declaração de ausência para a S7, `today` de `data_analise`, gates de classe.
  Entregue em `849e372b`.
