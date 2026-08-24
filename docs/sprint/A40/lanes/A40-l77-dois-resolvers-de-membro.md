---
id: A40.l77
type: lane
title: "Dois resolvers de membro sobre o mesmo baseline: o fix do eixo de ano chegou em um e o cônjuge vale 110k e 0,00 no mesmo payload"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1684
ship_date: "2026-08-24"
priority: P0
branch_slug: a40-l77-dois-resolvers-de-membro
adrs:
  - "[[ADR-394]]"
  - "[[ADR-410]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
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

Rotas revalidadas no closeout de 2026-08-24 — lane `shipped` não hospeda
deferimento órfão.

- **DE-7** (`nao_atribuidos` = 61% sem linha de cobertura) — **dono:
  `data-engineer`**; arbitrado em 2026-08-21 para **janela J5 própria**, e
  rastreado no §Inventário dos achados do r7 do [`_README`](../_README.md), que
  é o registro vivo. Exige rebaseline de golden, do snapshot do view-model e
  re-derivação de `tests/test_e5_conservation_invariants.py` — nada disso foi
  preciso aqui, o que é a razão de as duas janelas serem separadas. Esta lane
  **destrava** o DE-7 (mudou o denominador dele) e lhe entrega a fixture pronta;
  nunca foi o hospedeiro.
- **DE-8** (top-up IRPF sem quantia declarada) — **dono: `data-engineer`**,
  mesma janela e mesmo registro do DE-7.
- **Idempotência do eixo de atribuição** (2 runs, 15 itens divergem) — **dono:
  `data-engineer`**, roteada para a [[A42]] pela arbitragem de 2026-08-21.
- Os três §Deferimentos da [[ADR-410]] (item `bens[]` tipado + VO por membro;
  proveniência do numerador da reserva; `autoridade` que não separa produtor de
  substring) carregam dono e condição de retomada na própria nota.

## Ataque — 2026-08-24

Medido sobre `origin/main` (`47c0988e`; os commits que entraram durante a sessão são
docs-only e não tocam os resolvers), em duas frentes: baseline sintético no shape do
**produtor real** — [`consolidate_baseline.py:246`](../../../../scripts/consolidate_baseline.py)
emite `investimentos_consolidados` como **lista** de itens com `proprietario` e
`valores_31_12: {ano: valor}` — e o **artefato guardado** do run `33514dc4`, lido com
`dev/dump_artifact.py`.

### A0 — a divergência é prospectiva; no payload guardado os dois lados dizem `0,00`

A tabela do §Problema apresenta `110.130,67` e `0,00` como dois valores **no mesmo
payload**. O artefato do run `33514dc4` (`data_analise: 2026-08-18`) não mostra isso:

| campo do artefato | valor |
| --- | --- |
| `patrimonio.investimentos_conjuge` | **0,0** |
| `investimentos.total_financeiro` | `1.225.224,28` (= só o titular) |
| `investimentos.instituicoes_por_membro[1]` | 3 instituições da cônjuge, **sem campo `n_posicoes`** |

O run é de **2026-08-18**; o #1578 mergeou em **2026-08-19 19:19Z**. Os dois resolvers
estavam no eixo do domicílio quando ele rodou, então **ambos** publicaram `0,00`. Os
`110.130,67` são o que `resolve_members` produz **hoje** ao reprocessar aquele baseline
— re-computação num commit posterior, não leitura do payload. E `n_posicoes` não existe
no artefato: as linhas de `instituicoes_por_membro` têm só `membro` e `instituicoes`.

Nada disso desfaz o defeito — o §Ataque A abaixo mede a divergência na `main` de hoje.
O que muda é **o que conta como prova**: a divergência aparece no **próximo run**, não
no `33514dc4`. O §Critério 1 ("no mesmo payload, cônjuge tem um valor") não é
verificável contra esse artefato — precisa de run novo. Isso reforça a ordem que o
[`_README`](../_README.md) já fixou (fechar o DE-10 antes de disparar o r8): o r8 seria
o **primeiro** run a exibir o split, não mais um que o remede.

Mesma família do §r7 da [[A40.l69]], onde a taxa declarada pela [[ADR-394]] era
projeção do mecanismo pretendido, não medição do código que shipou.

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
| top-up do titular | guardado por `mesmo_ano` ([`:587`](../../../../pipeline/domain/services/patrimonio_resolvers.py)) | **sem guarda** (`e5_member_resolver.py:317`) |

> Os `arquivo:linha` do lado B ficam **sem link**: `e5_member_resolver.py` foi
> deletado pelo PR2 desta lane ([[ADR-410]] D1). A medição continua válida — foi
> feita antes da deleção, sobre `47c0988e` —, mas o alvo não existe mais.

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

## Co-design — 2026-08-24 (fechado)

`data-engineer` + `senior-cto` em paralelo, com as premissas do §Ataque. Decisão
registrada em [[ADR-410]] (`Proposto`). O §Escopo 1 está **cumprido**; o que
resta da lane é execução.

**Convergiram:** produtor único, `patrimonio_resolvers` é o canônico, portar
`instituicao`, enterrar o resolver morto de `analyze_finances.py`, fixture de
dois membros em anos disjuntos como **precondição** de qualquer critério, prova
por mutação nos **dois** membros, sem backfill do corpus.

**Divergiram em três pontos; o `senior-cto` fechou** (anti-loop do CLAUDE.md):

| ponto | veredito |
| --- | --- |
| ADR nova vs. emenda à [[ADR-394]] | **ADR nova**, com restrição dura: não reenuncia o D10, cita-o como premissa. Teste de falseamento aplicado na escrita |
| `E5MemberResolver` sobrevive como costura de DI? | **Não** — concedeu ao `data-engineer`: `PatrimonioInputs.members` obrigatório move a costura para value object e mata a resolução por dentro do calculator, que é a violação de DIP real |
| forma do gate | estrutural + contradição (do `data-engineer`), **mais** conservação: o D1 unifica o produtor do *item*, não o da *agregação*, então "com um produtor duas superfícies não podem discordar" é falso |

### Três correções ao §Ataque

1. **O §C caçou fantasma já nomeado.** A [[ADR-406]] §D2 (2026-08-21, dono
   `data-engineer`) mediu o mesmo mecanismo no corpus do r7 — autoridades
   **idênticas** (`keyword` 25 · `sem_match` 3), "é dívida, não bug; registrado
   para o próximo agente não caçar fantasma". A medição do §C mostra o dano
   *possível*; a do r7, o *realizado* = zero. **`tipo` não é justificativa para
   nada nesta lane** — a única razão de portá-lo é unicidade de produtor.
2. **O mecanismo do §C estava impreciso.** `classify_asset_outcome` **concatena**
   `tipo` e `descricao` numa haystack única (`asset_classifier.py:256`); não há
   precedência de `tipo`, quem decide é `EVALUATION_ORDER`.
3. **A ordem do §Escopo 3 estava trocada.** O gate de valor não depende de
   unificação de campos — os dois lados publicam valor por membro. O bloqueio é
   a **fixture**: `minimal-baseline-1.5_consolidated.json` é solo, mono-ano e
   sem `investimentos_consolidados`. A fixture precede o gate.

### O que a lane ganhou de escopo

- **Não precisa da J5** — razão categórica em [[ADR-410]] §Consequências.
- **Três políticas de ano para o saldo da mesma dívida** no mesmo payload
  (§Contexto da ADR). Fechadas pelo D4.
- **O ramo dict do E1.5 v2** é dupla-contagem latente e sai dos resolvers (D5).
- **DE-9 (`frescor` sem leitor)** entra como D6 — o campo é alimentado por
  `ano_base`, que só o produtor sobrevivente emite.
- **Um quarto resíduo órfão**: `MemberAnalyzer` (`member_analyzer.py`) — zero
  instanciação viva, só docstrings, export e testes próprios. Confirmar que os
  helpers não são origem de `patrimonio_types.investimento_valor` antes de
  deletar.

### O que saiu de escopo

O `_dec(None) == 0` da reserva **não é achado** — é desenho datado, travado por
`test_reserva_conta_membro_nao_apurado_como_zero` ("Contrato, não
implementação"), com a ressalva de KPI já nomeada como follow-up da [[A40.l69]].
Vai para a lane P1 do §Deferimentos da [[ADR-410]], junto com a proveniência de
`_filter_liquid` — mesmo objeto de decisão.

### Execução (3 PRs, uma janela de rebaseline)

1. **PR1 — aditivo, nenhum consumidor flipa.** `instituicao` + `ano_base` por
   item nos entries do canônico; value object de membro; `PatrimonioInputs.members`
   obrigatório com afirmação de identidade. **Aceite: delta zero em cents** — e é
   por isso que a deleção do segundo resolver **não** cabe aqui: ela flipa os
   cinco consumidores e move `tabela_classes`. Razão do sequenciamento
   (`senior-cto`): *se o PR1 mover número, você achou um acoplamento que o PR2
   esconderia*.
2. **PR2 — o número se move, uma vez só.** Flipa os cinco consumidores do adapter
   para o canônico, deleta `E5MemberResolver` e os resolvers órfãos, entra a
   fixture de dois membros, `frescor` ganha leitor (DE-9), e o rebaseline
   não-monetário é provado com `dev/golden_diff.py` (`value_delta == 0` em todo
   campo monetário; diff restrito a `top_ativos[].autoridade`).
3. **PR3** — os três gates, com o denominador do gate de contradição declarado.

## Entregue — 2026-08-24

Quatro PRs sequenciais, recortados para o delta ser **atribuível**: os dois
primeiros fecharam com delta zero em cents provado, então qualquer movimento de
número no terceiro é imputável só ao flip.

| PR | o quê | delta |
| --- | --- | --- |
| [#1669](https://github.com/davidrobert/mathoms/pull/1669) | item carimba `instituicao` + `ano_base` do próprio item | **zero em cents** |
| [#1676](https://github.com/davidrobert/mathoms/pull/1676) | `PatrimonioInputs.members` obrigatório + coerência de identidade | **zero em cents** |
| [#1677](https://github.com/davidrobert/mathoms/pull/1677) | produtor único; 3 resolvers deletados; fixture de 2 membros | 1.409 linhas removidas |
| [#1684](https://github.com/davidrobert/mathoms/pull/1684) | os três gates no payload, com denominador declarado | — |

**Nenhum rebaseline de golden ou snapshot na lane inteira.** O dogfood é
domicílio de um membro, então o flip não move os números dele — o que reforça
que a fixture de dois membros era precondição, não acessório.

### Efeito medido — na fixture sintética, não em produção

**O substrato é `dois-membros-anos-disjuntos-1.5_consolidated.json`** rodado por
`run_e3_e4_e5`, não um run de dogfood. Os valores são os da fixture (900k / 110k),
não patrimônio de ninguém.

| | antes | depois |
| --- | --- | --- |
| `investimentos.total_financeiro` | 900.000 | **1.010.000** |
| `patrimonio.investimentos_conjuge` | 0,0 | **110.000** |
| `cobertura_investimentos` | só `titular` | `titular` `frescor:2025` + `conjuge` `frescor:2023` |
| `instituicoes_por_membro` | um membro com as duas instituições | um membro cada |

> **Não existe medição de produção pós-fix, e não é descuido.** O artefato E5 mais
> recente do corpus é de 2026-08-18; esta lane mergeou em 24/08 (#1686 registra a
> lacuna). O efeito em produção só se mede no **r8** — o mesmo run que o DE-7 e o
> DE-8 esperam. Ler esta tabela como número de produção é o erro que o §Ataque A0
> pegou um nível acima.

### O que a [[ADR-410]] decide e esta lane **não** executou

O §Escopo 2 era "executar a decisão". Executou D1, D2 e D3; **D4 ficou parcial,
D5 e D6 não começaram** — ver [[ADR-410]] §Emenda 2026-08-24, que traz a evidência
de cada um. Resumo, com dono:

| | estado | dono |
| --- | --- | --- |
| **D4** um eixo de ano para saldo de dívida | parcial — `_split_dividas` ainda faz ano-exato-senão-zero | **`data-engineer`**, janela J5 |
| **D5** ramo dict sai dos resolvers | não executado — dupla-contagem **latente** (sem produtor hoje) | **`data-engineer`**, janela J5 |
| **D6** `frescor` ganha leitor (DE-9) | não executado — o campo segue sem consumidor | **`data-engineer`** + `product-designer` (copy) |

Nenhum dos três bloqueia o fecho do **DE-10**, que era a tese da lane: o defeito
de dois produtores está morto, provado por mutação e por gate. Os três são
trabalho adjacente que a ADR decidiu de uma vez e a lane não coube.

### Três achados que a execução trouxe e o co-design não previu

1. **A estimativa do D2 estava errada por ~28×.** "Duas call-sites" eram **59**
   construções — 2 em produção (uma delas docstring) e 57 em teste. A decisão
   seguiu certa; só não coube junto da prova de delta zero.
2. **O D3 não era implementável como escrito.** VO tipado por membro descartaria
   as chaves que o layout flat usa como categoria de bem — perda silenciosa, a
   própria classe que a nota fecha. Ajustado pré-implementação; ver [[ADR-410]] §D3.
3. **`tipo` restaurado expôs uma regressão latente de rótulo.** `_fallback_nome`
   preferia `tipo`, e o `tipo` do dogfood é o default de ignorância
   `"investimento"` — virava o *"Investimento pelado"* que a [[ADR-337]] proíbe.
   Enquanto o resolver descartava o campo, `classe` vencia **por ausência**.
   Corrigido na raiz: sentinela de ignorância conta como `tipo` ausente.

### O que continua aberto, com dono

Os três §Deferimentos da [[ADR-410]]: item `bens[]` tipado + VO por membro
(bloqueados enquanto houver ramos de passthrough em `resolve_members`), a lane
P1 da proveniência do numerador da reserva (`_filter_liquid` + ressalva de KPI
do balde `None`), e o `autoridade` que não distingue produtor de substring
(território [[ADR-400]]).

**O DE-7 destrava.** Esta lane era o pré-requisito dele por mover
`total_financeiro`, que é o denominador da ressalva que ele publica — e o
denominador acabou de mudar de 900.000 para 1.010.000 no caso de dois membros. A
fixture construída aqui é reaproveitada inteira por ele.
