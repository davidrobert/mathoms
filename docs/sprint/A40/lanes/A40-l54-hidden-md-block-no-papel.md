---
id: A40.l54
type: lane
title: "`hidden md:block` entrega ao papel a variante mobile: varredura dos call-sites e gate da classe (ADR-381 D1)"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1516
ship_date: "2026-08-18"
priority: P2
branch_slug: a40-l54-hidden-md-block-no-papel
adrs:
  - "[[ADR-381]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p2
  - area/frontend
  - area/report
---

# A40.l54 — `hidden-md-block-no-papel`

> **Aberta em 2026-08-12**, no fecho da [[A40.l45]] (decisão do dono: os
> follow-ups sem dono viram lanes na A40). A [[ADR-381]] D1 fixou a regra; esta
> lane executa a varredura que a l45 declarou fora de escopo.

## Problema

A caixa de página A4 tem **703px**, então `md:` (768px) **nunca casa no PDF** —
todo `hidden md:block` escrito como "isto é a variante desktop" entrega ao papel
a variante mobile, e o próximo call-site sem par mobile completo **some do PDF
sem erro e sem gate**.

Estado medido em 2026-08-11 (parecer do `product-designer` + verificação por
`pdftotext` na l45):

- `alocacaoCardParts.tsx` (`DesktopTable`/`MobileStack`) e
  `CoberturaSegurosCard.tsx`: a tabela desktop **não existe no PDF** hoje. O
  dado sobrevive porque a variante mobile carrega valor/atual/alvo/desvio —
  **por acidente, não por desenho**. São as colunas "Classe/Desvio (pp)" e
  "Status/Vigência" que a sonda de perda tela→PDF da l45 listou como ausentes.
- ~21 wrappers `overflow-x-auto` no relatório: no papel viravam clip silencioso
  até o `report-print.css` da l45 devolver `overflow: visible` — a quebra por
  rótulo cobre a classe, mas ninguém mediu tabela a tabela se todas cabem.

## Inventário — 2026-08-18

> Varredura [[ADR-381]] D1 em `frontend/src/components/report/`.
> Snapshot datado: não reescrever. Remedir → blockquote novo
> (precedente [[A40.l5]]).

| arquivo | padrão | papel recebe hoje | veredito |
| --- | --- | --- | --- |
| `cards/alocacaoCardParts.tsx` | `hidden md:block` / `md:hidden` | MobileStack | perda de header |
| `cards/CoberturaSegurosCard.tsx` | `hidden md:block` / `md:hidden` | cards mobile | perda de header |
| `cards/Top15AtivosCard.tsx` | `hidden md:table-cell` (Membro) | coluna some | perda de coluna |
| `cards/IrpfDedutiveisAplicadosCard.tsx` | `hidden … md:block` (barra) | barra some | perda de coluna |
| `ReportShell.tsx` + `shell/ReportActions.tsx` | `hidden md:block` / `md:inline-*` | ToC/`no-print` | chrome |
| `RealEstateBreakdownPanel.tsx` | `hidden md:grid` / `md:hidden` | dialog fechado | chrome |
| `VariacaoSection.tsx` | `hidden sm:table` / `sm:hidden` | tabela | já-conforme ([[A40.l45]]) |
| `cards/EstrategiaAporteCard.tsx` | `hidden sm:table-cell` | colunas no papel | já-conforme |
| `cards/ContrafluxoCard.tsx` | `hidden sm:table-cell` | colunas no papel | já-conforme |

**Veredito (conjunto fechado):** `dado completo` · `perda de header` ·
`perda de coluna` · `chrome` · `já-conforme` · `fora de escopo D2`.

Wrappers `overflow-x-auto` (~21): fora desta tabela — [[ADR-381]] D3,
já da [[A40.l45]]. `md:grid-cols-*` é [[ADR-381]] D2 — fora desta lane.

## Escopo

1. Inventariar todo `hidden md:block` / `md:hidden` / `hidden sm:*` sob
   `frontend/src/components/report/` e classificar cada um: a variante que o
   papel recebe carrega **todo** o dado da outra?
2. Converter os divergentes para o idioma da [[ADR-381]]: `sm:` como divisor
   papel/telefone, `@media print` para o que o papel faz de diferente.
3. Gate da classe: a sonda de perda tela→PDF da l45 (comparar frases visíveis
   do `<article>` com a camada de texto do `pdftotext`) vira spec permanente —
   derivada do DOM, não lista de componentes, com âncora anti-fail-open.

## Critério de aceite

- [x] Inventário com veredito por call-site commitado na lane (tabela).
- [x] O PDF real contém as colunas hoje ausentes (`Classe`, `Desvio (pp)`,
      `Status`, `Vigência`) — verificado por `pdftotext`, não por emulação.
- [x] Provado por mutação: um `hidden md:block` novo sem par completo deixa o
      gate vermelho.

## Entregue — 2026-08-18 · PR [#1516](https://github.com/davidrobert/mathoms/pull/1516)

Três peças, uma por linha do §Escopo:

1. **4 call-sites convertidos** para o idioma da [[ADR-381]] — os que a tabela
   do §Inventário marcou com perda de dado:
   `alocacaoCardParts.tsx:222` e `CoberturaSegurosCard.tsx:143`
   (`hidden overflow-x-auto sm:block`), `IrpfDedutiveisAplicadosCard.tsx:188`
   (`hidden flex-1 sm:block`) e `Top15AtivosCard.tsx:167,216`
   (`print:table-cell md:table-cell`). O `sm:` (640px) casa na caixa de 703px;
   o `md:` (768px) não casava.
2. **Gate da classe** — [`dev/check_hidden_md_on_paper.py`](../../../../dev/check_hidden_md_on_paper.py),
   hook `hidden-md-on-paper` no pre-commit com `pass_filenames: false`, e
   [`tests/dev/test_check_hidden_md_on_paper.py`](../../../../tests/dev/test_check_hidden_md_on_paper.py).
3. **Sonda de perda tela→PDF como spec permanente** —
   [`frontend/tests/e2e/reports/print-text.@critical.spec.ts:209-241`](../../../../frontend/tests/e2e/reports/print-text.@critical.spec.ts):
   colhe os `<th>` visíveis a 1280px (o `setupPrintReport` **não** chama
   `emulateMedia`, então a comparação não é circular), com 4 âncoras duras e
   `expect(ausentes).toEqual([])` genérico por cima.

Verificação do critério 3 no fecho (2026-08-27), importando o módulo do gate:
`line_offends('<table className="hidden md:block">')` → `True`;
com `print:block` no mesmo `className` → `False`; `md:hidden` isolado → `True`.

## Limite declarado do gate — 2026-08-27

Medido no fecho, executando o próprio gate. Nenhum é defeito vivo hoje; os três
são **latentes**, e o idioma que os ativa já vive na árvore.

| limite | medição | por que importa |
| --- | --- | --- |
| **polaridade invertida em `max-md:`** | `line_offends('max-md:hidden print:hidden')` → `False` (aprova o que some do papel); `line_offends('max-md:hidden print:block')` → `True` (reprova o remédio) | `SOME_NO_MD = re.compile(r"md:hidden")` casa por substring **dentro** de `max-md:hidden`. Hoje `max-md:` não aparece sob `components/report/`, mas o idioma `max-*` já está em `ReportCard.tsx:54,56,61` (`max-sm:`) |
| **`lg:` e `xl:` invisíveis** | `line_offends('hidden lg:block')` → `False`; `hidden xl:block` → `False` | `APARECE_NO_MD` fixa o literal `md:`. Já convive com um caso dentro do scan root: `ReportToc.tsx:132` (`hidden … lg:block`), salvo apenas por carregar `no-print` |
| **allowlist isenta o ARQUIVO, não a linha** | `ALLOWLIST = {RealEstateBreakdownPanel.tsx, ReportShell.tsx, shell/ReportActions.tsx}`, consumida antes de ler qualquer linha | `ReportShell.tsx` hospeda o `<article>` do relatório: um `hidden md:block` novo com dado dentro dele passa calado |

*Retomar quando:* aparecer o primeiro `max-md:` / `lg:` com **dado** (não
chrome) sob `frontend/src/components/report/`, ou quando a allowlist precisar
isentar uma 4ª linha. Dono: David Robert.

## Fecho — 2026-08-27 · `shipped` em #1516

Os 3 critérios foram verificados por execução, não por releitura, e as 3
caixas acima foram marcadas no fecho — o #1516 entregou a lane inteira em
2026-08-18 e o registro ficou 9 dias atrás do código. É a classe que a
[[A40.l59]] gateia desde então (`dev/check_lane_transition.py`); esta lane é
instância dela — o assunto do merge diz `(A40.l54)` e o frontmatter não tinha
`ship_pr`.
