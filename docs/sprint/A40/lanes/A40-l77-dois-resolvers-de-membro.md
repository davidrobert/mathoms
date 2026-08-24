---
id: A40.l77
type: lane
title: "Dois resolvers de membro sobre o mesmo baseline: o fix do eixo de ano chegou em um e o cônjuge vale 110k e 0,00 no mesmo payload"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l77-dois-resolvers-de-membro
adrs:
  - "[[ADR-394]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l77 — Dois resolvers de membro (DE-10)

> **O primeiro entregável é a decisão, não o código.** Dois resolvers paralelos
> sobre o mesmo baseline é escolha arquitetural — unificar, declarar um
> autoritativo, ou manter os dois com contrato explícito. Co-design
> `data-engineer` + `senior-cto` **antes** de escrever o fix. Copiar
> `anos_base_por_membro` para o segundo resolver fecha o número e deixa a classe
> viva: dois produtores da mesma verdade continuam podendo divergir no próximo fix.

> **Precede o DE-7 e a janela J5.** Corrigir este resolver move `total_financeiro`,
> que é o **denominador** da ressalva de cobertura que o DE-7 vai publicar. Construir
> a linha de cobertura antes calibra limiar, copy e teste contra um número prestes a
> mudar. Ver §Inventário dos achados do r7 sem hospedeiro no [`_README`](../_README.md).

## Problema

O fecho do **RV6-04** ([[A40.l69]], #1578 / [[ADR-394]] §Emenda (c)) corrigiu o eixo
de ano-base em **um** dos dois resolvers de membro. No mesmo payload, a mesma pessoa
tem dois valores:

| Superfície | Resolver | Cônjuge |
| --- | --- | --- |
| `patrimonio.investimentos_conjuge` | `resolve_members` (`patrimonio_resolvers.py`) | `n=9` · **R$ 110.130,67** |
| `total_financeiro` / `tabela_classes` / `top_ativos` | `E5MemberResolver` (`e5_member_resolver.py`) | `n=9` · **R$ 0,00** |

Medido em `207fca00` sobre o run `33514dc4`; `git show --stat 11b90a4e` não lista
`e5_member_resolver.py`.

**O mecanismo, nomeado.** O defeito é do **eixo**, não da pessoa. O ano-base era do
**domicílio** — `_max_value_year` (`patrimonio_types.py:99`) sobre o baseline
inteiro. Com os cônjuges declarando em anos disjuntos, quem não tem item no ano
escolhido cai no fallback e vira `0,00` — a conflação `null`↔`0,00` que a
[[ADR-394]] proíbe um andar acima. O #1578 instalou `anos_base_por_membro`
(`patrimonio_resolvers.py:341`), que dá a cada membro o maior ano que **ele próprio**
declarou. O `E5MemberResolver` **não recebeu nada**: segue importando
`resolve_value_year` (`patrimonio_types.py:111`), que é a função do eixo antigo.

**Consequência visível.** `instituicoes_por_membro` publica **3 instituições dela com
`n_posicoes=9` e valor zero** — a assinatura literal do RV6-04 original, na superfície
que o fecho não alcançou. Os consumidores do resolver não-corrigido são
`InvestimentosClassesAnalyzer`, `TopAtivosAnalyzer` e `InstituicoesPorMembroAnalyzer`,
via `e5_analyzer_adapter.py`.

> ⚠️ **Lista incompleta — medido em 2026-08-24.** São **cinco**, não três: a reserva
> de emergência e o endividamento também leem `members` do `E5MemberResolver`. Ver
> §Ataque abaixo, item **B**.

## Escopo

1. **Co-design da autoridade** — decidir e registrar (emenda à [[ADR-394]] ou ADR
   nova) qual resolver é fonte de verdade do eixo membro→ano, e o que acontece com o
   outro. Sem isso o resto é remendo.
2. **Executar a decisão** nos consumidores do `E5MemberResolver`.
3. **Gate da classe, não da instância** — um teste que falhe quando **qualquer** par
   de superfícies publicar valores diferentes para o mesmo (membro, conceito) no mesmo
   payload. O fix pontual fecha o número de hoje; o gate fecha a família.

## Critério de aceite

- No mesmo payload, cônjuge tem **um** valor: `patrimonio.investimentos_conjuge` e a
  soma de `tabela_classes`/`top_ativos` concordam. Prova por mutação — reverter o fix
  do eixo no resolver corrigido deixa o teste vermelho **nos dois lados**.
  > ⚠️ **Satisfazível com o payload ainda errado — medido em 2026-08-24.** O critério
  > fala só do **cônjuge**; sob o remendo que a epígrafe desaconselha o cônjuge
  > concorda e o **titular** passa a divergir em 110k. Critério de instância
  > contradiz o §Escopo 3, que pede a classe. Ver §Ataque, item **C**.
- `instituicoes_por_membro` não publica linha com `n_posicoes>0` e valor `0,00` sem
  razão declarada (`sem_haystack`/`sem_match`, vocabulário da [[ADR-406]]).
  > ⚠️ **Campo inexistente — medido em 2026-08-24.** `MembroInstituicoes.to_dict()`
  > publica `membro`/`instituicoes`/`n_posicoes`/`posicoes_sem_identidade`
  > ([`instituicoes_por_membro_analyzer.py:53`](../../../../pipeline/domain/services/instituicoes_por_membro_analyzer.py)).
  > Não há `valor` na linha — o critério é medível, mas precisa nomear de onde o
  > valor é derivado.
- O gate da classe existe e **tem chamador** — CI ou pre-commit, não só unit test.
  Precedente negativo na mesma sprint: `scan_view_model_pii` shipou sem chamador e a
  KR-D não fechou (ver [`_README`](../_README.md) §KRs).
- A decisão do item 1 está numa ADR, com o resolver perdedor removido **ou** com o
  contrato dos dois escrito. "Os dois existem e agora concordam" não é desfecho.

## Fora de escopo

- **DE-7** (`nao_atribuidos` = 61% sem linha de cobertura) — arbitrado em 2026-08-21
  para **janela J5 própria**; exige rebaseline de golden, do snapshot do view-model e
  re-derivação de `tests/test_e5_conservation_invariants.py`. Esta lane é o
  pré-requisito dele, não o hospedeiro.
- **DE-8** (top-up IRPF sem quantia declarada) — mesma janela do DE-7.
- **Idempotência do eixo de atribuição** (2 runs, 15 itens divergem) — roteada para a
  [[A42]] pela arbitragem de 2026-08-21.

## Ataque — 2026-08-24

Medido sobre `origin/main` (`47c0988e`; os commits que entraram durante a sessão são
docs-only e não tocam os resolvers). Baseline sintético no shape do **produtor real**
— [`consolidate_baseline.py:246`](../../../../scripts/consolidate_baseline.py) emite
`investimentos_consolidados` como **lista** de itens com `proprietario` e
`valores_31_12: {ano: valor}`. Zero PII, zero DB. O decrypt do run `33514dc4` exigiria
a `MATHOMS_FERNET_KEY`; a instância já estava medida na triagem, então o que se mede
aqui é a **classe**.

### A — a instância confere, a premissa não

Reproduzido: mesmo baseline, cônjuge vale **R$ 110.130,67** por `resolve_members` e
**R$ 0,00** por `E5MemberResolver`; `tabela_classes` total move `1.335.354,95` →
`1.225.224,28`. `git show --stat 11b90a4e` lista 13 arquivos e **nenhum** é
`e5_member_resolver.py`. Tudo isso se sustenta.

O que **não** se sustenta é a leitura de que o delta seja o eixo de ano. Com o ano
**forçado idêntico** dos dois lados — neutralizando o #1578 — o item publicado ainda
diverge:

| campo do item | `resolve_members` (A) | `E5MemberResolver` (B) |
| --- | --- | --- |
| `instituicao` | **ausente** | presente |
| `tipo` | presente | **ausente** |
| `ano_base` (topo do membro) | presente | **ausente** |
| top-up do titular | guardado por `mesmo_ano` ([`:587`](../../../../pipeline/domain/services/patrimonio_resolvers.py)) | **sem guarda** ([`:317`](../../../../pipeline/domain/services/e5_member_resolver.py)) |

**Nenhum dos dois é superset do outro.** Isso muda o §Escopo 1: "declarar um
autoritativo e remover o outro" perde dado nos **dois** sentidos, e os dois desfechos
óbvios têm custo medido —

- **E5 passa a usar `resolve_members`** → `instituicoes_por_membro` perde a instituição
  de toda posição e `posicoes_sem_identidade` vira **falso positivo**: no mesmo item,
  A publica `instituicoes=[]` + `sem_identidade=1`, B publica `['Btgpactual']` + `0`.
  Os dois resolvers emitem **vereditos [[ADR-406]] opostos** sobre a mesma posição — e
  isso é ressalva, não valor, então o §Critério (escrito sobre valores) não alcança.
- **Copiar `anos_base_por_membro` para o B** → o top-up sem guarda **subtrai
  R$ 110.130,67 do titular** (`1.225.224,28` → `1.115.093,61`). A epígrafe diz que o
  remendo "fecha o número"; medido, ele **abre um número novo**, na mesma família
  `unattributed → titular` que a [[ADR-394]] §D8 cortou.

### B — o raio de alcance é cinco, não três

Além dos 3 analyzers, `members` do `E5MemberResolver` alimenta em
[`e5_analyzer_adapter.py`](../../../../pipeline/domain/services/e5_analyzer_adapter.py):

- **Reserva de emergência** (`:655`). Pior: `_liquidez_membro`
  ([`reserva_liquidez.py:139`](../../../../pipeline/domain/services/reserva_liquidez.py))
  mistura os **dois** resolvers no mesmo membro — `aggregate` vem do corrigido, `bens`
  do não-corrigido. E item zerado **não** é item ausente: `_filter_liquid` pula
  `valor<=0`, então sai `LiquidezMembro(0, 0, fonte="irpf")` — proveniência fabricada —
  em vez de cair no ramo `agregado_sem_itens`, que usaria o agregado **correto**. O
  defeito desarma justamente a rede de segurança feita para dado faltante.
- **Endividamento** (`:686`), inclusive `ano_ref=members.reference_year` (`:694`).
  `ResolvedMembers.reference_year` é **singular por construção** — com anos disjuntos
  não existe valor certo. Copiar o eixo por membro nem fecha nesse boundary: o
  contrato do dataclass precisa mudar junto.

### C — dropar `tipo` miscategoriza, não só perde campo

`InvestimentosClassesAnalyzer._classify_investments` passa `tipo` **primeiro** a
`classify_asset_outcome`; sem ele sobra o matcher de **substring** da descrição. Com 3
descrições opacas (texto livre de IRPF é o caso comum):

| | Renda Fixa | Ações BR | FIIs | Outros | `nao_classificado_brl` |
| --- | --- | --- | --- | --- | --- |
| A (com `tipo`) | 300k | 250k | 180k | — | R$ 0 |
| B (o que a E5 usa) | — | **300k** | — | 430k | **R$ 430.000** |

Os 300k em "Ações BR" são renda fixa: `"Aplicacao 4412"` ⊃ `"acao"`, keyword de Ações
BR ([`asset_classifier.py:61`](../../../../pipeline/domain/services/asset_classifier.py)).
A colisão é construída, mas "APLICAÇÃO" é palavra banal em descrição de IRPF.

### D — um terceiro resolver existe, morto

[`scripts/analyze_finances.py`](../../../../scripts/analyze_finances.py):
`_resolve_members` (`:368`) + `_build_members_from_consolidated` (`:531`), chamados só
por `analyze_patrimonio` (`:919`) e `analyze_endividamento` (`:1488`) — **nenhuma das
duas tem chamador**, dentro ou fora do arquivo. A decisão do §Escopo 1 deve enterrá-lo
junto, senão volta.

### E — por que os testes não pegam

[`test_patrimonio_ano_base_adr274.py:145`](../../../../tests/unit/pipeline/test_patrimonio_ano_base_adr274.py)
tem seção literal **"E5MemberResolver — segundo path com o mesmo bug"**, com 1 teste
verde que exercita só o off-by-one exercício↔ano-base ([[ADR-274]]) de **um** membro.
O bloco novo do #1578 ("Eixo de ano POR MEMBRO", 5 testes) exercita **só**
`build_members_from_consolidated` — não estendeu a seção que já nomeava o gêmeo.
98 testes verdes nos 3 arquivos de resolver.

### Consequência para o §Escopo 3

O gate "qualquer par de superfícies concorda no mesmo (membro, conceito)" **não é
implementável hoje**: A e B não publicam os mesmos campos, então `instituicao` e `tipo`
são incomparáveis por construção. Ou o gate cobre só o subconjunto comum — e perde os
dois eixos de drift acima —, ou a **unificação de campos vem antes do gate**. Isso é
input do co-design do §Escopo 1, não substituto dele: a decisão de autoridade continua
sendo o primeiro entregável.
