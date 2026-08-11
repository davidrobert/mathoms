---
id: A40.l34
type: lane
title: "Base do limite PGBL: duas seções publicam 12% sobre bases que o relatório declara incompatíveis"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l34-base-do-limite-pgbl
adrs:
  - "[[ADR-196]]"
  - "[[ADR-277]]"
  - "[[ADR-236]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l34 — `base-do-limite-pgbl`

> **Aberta em 2026-08-11**, spun off da [[A40.l7]] enquanto se media o RV3-28.
> Decisão de abrir: do dono. Colocação, prioridade e onda: `product-manager`.
> Severidade de domínio: `financial-planner` — *"a única parte deste achado que
> pode custar dinheiro à família"*.

## Problema

O relatório publica **"Limite PGBL (12%)" em duas seções, sobre bases que ele
mesmo declara incompatíveis**:

| Superfície | Base do limite |
|---|---|
| **S7**, `PrevidenciaPgblCard` (`previdencia_analyzer.py:62`) | `receita_pj_anual × **32%** (lucro presumido)` |
| **S8**, `PgblBlock` (`CascataFiscalCard.pgbl.tsx:38`) | *"pró-labore + outras rendas tributáveis IRPF. **Lucros distribuídos não entram na base PGBL**"* |

A S8 **afirma explicitamente que a base da S7 está errada**, uma seção adiante,
no mesmo documento.

Para o arquétipo central do produto — **PJ alta renda, pró-labore pequeno,
distribuição grande** — a S7 **superestima o espaço dedutível por um múltiplo**
e imprime *"Economia de IR/ano"* em `--semantic-gain`. O dano não é de leitura:
a família aporta acima do teto dedutível sobre um número que o relatório
apresentou como ganho.

**A polaridade da prescrição está invertida.** `getPgblCardStrategy`
(`pgbl-card-strategy.ts:103`) devolve `DEFAULT_STRATEGY` — o modo que
**prescreve** aporte sugerido + economia de IR — quando **não há IRPF
processado**; com IRPF autoritativo ele degrada para `informative-*`, que
**suprime** as duas prescrições ([[ADR-196]] §D5). **O card prescreve justamente
quando a evidência é mais fraca.**

> ### ⚠️ Isto falsifica um `Decidido` — não é lacuna, é contradição
>
> A [[ADR-196]] §1 **caso 4** afirma que o Card A ***subestima*** o espaço fiscal
> frente à fonte autoritativa. A medição diz o **oposto** para o arquétipo PJ.
> Corrigir o código sem registrar a falsificação deixa um `Decidido` assinado
> contradizendo `main` — a classe que esta sprint cataloga.
>
> E a [[ADR-196]] §D6 declara *"backend inalterado"*, o que **deixou de valer**:
> a mesma polaridade vive no Python (`PrevidenciaAnalyzer.analyze`,
> `previdencia_analyzer.py:219-229`, só cai em `_analyze_via_proxy` quando
> `capacidade_irpf is None` · [[ADR-277]]). A lane tem perna Python obrigatória.

## Escopo

A S7 deixa de publicar um segundo limite PGBL: a base passa a ser a **mesma da
cascata fiscal da S8** (renda tributável IRPF — pró-labore + demais tributáveis,
sem lucros distribuídos), a prescrição de aporte/economia de IR deixa de sair
quando a evidência é mais fraca, e o card sai da S7 com cross-link — o que fecha
também a **metade de hospedagem do RV3-28**, herdada da [[A40.l7]].

**ADR nova `Proposto` antes de qualquer PR de implementação** (política do
CLAUDE.md), com **supersedure parcial declarada da [[ADR-196]]** e bidirecional.
Emenda não é veículo suficiente: muda a **base** (regra de domínio), **inverte a
polaridade** de quando prescrever (§D1/§D5), **falsifica o §1 caso 4**, e pode
**remover o card** que a ADR-196 desenhou em 6 modos. **Co-design
`financial-planner` + `senior-cto`.**

## Herdado da [[A40.l7]] (2026-08-11)

A **metade de hospedagem** do RV3-28. A l7 entregou a metade de **nome** (heading
e índice derivam da mesma fonte, #1355) e retitulou a S8; *mover* o card para a
S8 pressupõe que o card deve existir com a base atual — e **é esta lane que
decide isso**. Os 2 cross-links que a l7 entregou são **mitigação declarada**,
não solução.

## Critério de aceite

- A S7 e a S8 publicam **um único** limite PGBL, sobre a base da renda tributável
  IRPF — ou a S7 deixa de publicar limite.
- A prescrição (aporte sugerido, economia de IR) **não** sai quando a evidência é
  mais fraca. Teste que exercita o caminho sem IRPF.
- **Sinal do delta declarado: `↓`** no espaço dedutível publicado (§Decisões do
  painel nº 5), conferido por `dev/golden_diff.py`.
- **A fórmula entra em `docs/reference/FORMULAS.md`** — hoje `rg 'PGBL|dedu'` dá
  zero ocorrências, e é número **prescritivo**. É achado independente do fix.
- [[ADR-196]] recebe a supersedure parcial **nos dois arquivos**, e o §1 caso 4
  ganha a correção datada da direção do erro.
- **Verificação renderizada** (§Débito de método da sprint).

## Colisão declarada

`S7IndependenciaSection.tsx` é tocado também pela [[A40.l25]] e pela [[A40.l29]].
Quem mergear depois rebaseia. Não há dependência de conteúdo.
