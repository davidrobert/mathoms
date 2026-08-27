---
id: ADR-418
type: adr
title: "A meta de IF desconta exatamente a renda passiva que o numerador não conta"
status: Decidido
phase: A40
date: "2026-08-27"
relates_to:
  - "[[ADR-142]]"
  - "[[ADR-222]]"
  - "[[ADR-223]]"
  - "[[ADR-140]]"
  - "[[ADR-412]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 418"
  - "base da meta de independência financeira"
  - "anti-dupla-penalidade do progresso IF"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
---

# ADR-418 — A meta de IF desconta exatamente a renda passiva que o numerador não conta

**Status:** Decidido (A40.l91) • **Data:** 2026-08-27 • **Relaciona** [[ADR-142]], [[ADR-222]], [[ADR-223]], [[ADR-140]], [[ADR-412]] • **Lane:** [[A40.l91]]

## Contexto

`progresso_if` é `investivel_efetivo ÷ meta` e carrega peso 2,0 no score — 25% da nota,
o maior peso, empatado com `taxa_poupanca_recorrente`. `if_gap` é `meta − investivel_efetivo`.
Os dois leem **uma** meta, produzida por `compute_if_derived`
(`backend/app/services/goal_service.py`) e transportada como `goals.if_meta`.

A rodada unificada **U1** ([[ADR-416]], PV9-16) mediu que essa meta fecha ao centavo a
fórmula **bruta** — `renda_alvo_mensal × 12 ÷ TRS` — enquanto
[FORMULAS.md](../reference/FORMULAS.md) documentava a **líquida** como *"a métrica usada em
`progresso_if`"*. A medição desta lane resolveu a pergunta que a U1 deixou aberta — a meta é
declarada pelo dono ou derivada? — e achou uma terceira coisa.

**A meta é derivada** (resíduo R$ 0,00 contra a identidade bruta; nenhum input do Goal a
declara). Mas a base bruta **não é errada por si**: ela é a base certa quando o numerador
contém todos os ativos que geram renda passiva. `investivel_efetivo × TRS = renda_alvo`
⟺ `investivel_efetivo = renda_alvo × 12 ÷ TRS`. O que decide é o **par**, não a fórmula.

E o par depende de um toggle. [[ADR-222]] tornou `imoveis_no_if` per-workspace; [[ADR-223]]
flipou o **default para `false`** — conservadorismo do padrão consagrado de planejamento
patrimonial brasileiro. Com `false`, cat_2 (imóveis de renda) sai do numerador — **e a meta
não muda**. A família deixa de contar o imóvel como
patrimônio *e* continua tendo de acumular do zero a renda que aquele imóvel já paga. A
exclusão é cobrada duas vezes.

**Esta ADR não decide metodologia nova — ela liga uma regra decidida há quatro meses.** A
[[ADR-142]] §Decisão já dizia, em 2026-04-27, no corpo de uma ADR `Decidido`: *"Se
`imoveis_no_if = false`: (…) `renda_passiva_atual_mensal_brl` **deve incluir aluguéis
líquidos** (são a renda passiva real e não há contagem dupla)"*. O que faltou nunca foi a
decisão — foi o **produtor**. A metade `true` do invariante (não descontar) tinha enforcer;
a metade `false` (descontar) não tinha nenhum, e o único lugar onde ela aparecia operacional
era a `description` de um campo do `goal.if.v2.schema.json`, schema **candidato** que nunca
entrou em produção.

### O que a medição mostrou

Workspace de dogfood, run da U1 (comandos e forma em [[A40.l91]]; valores off-git):

| Regime | cat_2 no numerador | Renda passiva fora do numerador | Publicado hoje |
| --- | --- | --- | --- |
| `imoveis_no_if = true` (o run medido) | sim | **zero** — todo o gerador está dentro | **correto** |
| `imoveis_no_if = false` (**default** de produto) | não | os aluguéis (75,45% da renda passiva observada) | meta **9,56%** alta; progresso **1,74 pp** baixo; gap **×1,119** |

O regime defeituoso é o **default**: 6 dos 7 workspaces do ambiente medido estão em `false`,
nenhum por escolha explícita (`imoveis_no_if_set_at` nulo em 7/7).

## Decisão

**Uma base só, e ela desconta exatamente a renda passiva produzida por ativos que o
numerador exclui.**

```
meta = MAX(0, (renda_alvo_mensal − renda_passiva_fora_do_investivel_mensal) × 12 ÷ TRS)
```

### D1 — O invariante é o par, não a fórmula

Renda passiva de ativo **dentro** do numerador **não** desconta a meta (seria contar o ativo
duas vezes — [[ADR-142]]). Renda passiva de ativo **fora** do numerador **desconta**
(não descontar cobra a exclusão duas vezes). As duas metades são o mesmo invariante lido nos
dois sentidos, e nenhuma vale sozinha.

### D2 — O termo é a renda do ativo EXCLUÍDO, não a renda quando o toggle está `false`

A distinção não é sutil: é a diferença entre corrigir o defeito e inverter o sinal dele.

O balde `alugueis` de `passive_income` é **residual** (`_renda_passiva_observada`: o que
sobra do split de capital do IRPF depois de tirar os buckets explícitos) e carrega
`_alugueis_pf = Σ rendimentos_pf` — **todo o carnê-leão PF→PF**, que no ICP inclui renda de
trabalho autônomo recebida de pessoa física. Ler só o toggle faria a família **sem imóvel de
renda**, no default `false`, ver a meta cair por renda que não vem de ativo nenhum que tenha
sido excluído. Isso **infla** o KPI de maior peso sobre premissa falsa — e a §Motivação da
[[ADR-223]] é explícita em que superestimar progresso de IF é mais danoso que subestimar.

Três guardas, nesta ordem:

1. **Exclusão real.** `patrimonio.imoveis_geradores > 0`, senão o termo é `0` com origem
   `sem_gerador_excluido`. Sem ativo excluído não há o que creditar.
2. **Líquido, não bruto.** A [[ADR-142]] diz "aluguéis **líquidos**" nos dois ramos. O termo
   é capitalizado por `12 ÷ TRS` (25× a 4%), então erro no termo é erro do mesmo tamanho no
   desconto inteiro. O haircut usa as **mesmas** constantes de `RealEstateConfig` que a seção
   de imóveis (IR carnê-leão, vacância, manutenção) — segundo conjunto de premissas de
   vacância num segundo módulo é como o próximo defeito de base nasce. É **conservador**:
   IPTU, condomínio e taxa de administração ficam de fora, então desconta menos que o real.
3. **Procedência publicada.** `renda_passiva_fora_origem` diz de qual das três situações o
   número saiu, porque "descontei X" é indistinguível de "descontei X vindo de um balde
   residual contaminado".

Quando um segundo eixo de exclusão aparecer, ele entra **aqui** — o termo é o ponto de
extensão, e um eixo novo que não passe por ele reabre o defeito.

**§Deferido (2026-08-27, dono `financial-planner`) — teto por imóvel.** O termo ideal é
`min(residual, Σ aluguel_líquido dos geradores excluídos)`, com o líquido por-imóvel que
`real_estate_metrics.calculate_property_metrics` já computa (com `aluguel_origem` e
`confidence`). Não entra nesta lane porque `calculate_real_estate_metrics` vive em
`backend/app/services/` e `pipeline/**` não importa `backend/` (ADR-089). Retomada: qualquer
lane que leve as métricas de imóvel para dentro do domínio do pipeline.

### D3 — A base vai publicada, em dados

Precedente [[ADR-412]]: *"uma base é o conjunto de termos que forma um denominador, não o
número"*. `goals` passa a publicar `if_meta_bruta` e `if_meta_base` (enum fechado)
**sempre**, e `renda_passiva_fora_do_investivel_mensal_brl` **quando o termo foi apurado**.
Auditar de que base o progresso saiu passa a ser possível **só pelo payload** — que é como a
U1 chegou a este achado e não conseguiu fechá-lo.

O termo é **ternário**, não um número com zero implícito: `None` = a renda passiva não foi
apurada (a chave não sai), `0.0` = foi apurada e não há nada fora do numerador, `>0` =
desconta. Publicar `0` sem apuração afirmaria ausência que ninguém mediu — e seria campo
mensalizado sem rótulo de janela ([[ADR-306]]), já que a janela do IRPF só existe em `goals`
quando a renda passiva está `ok`.

`if_meta` continua sendo a meta **operacional** (a que os dois consumidores usam), agora
nomeada. `if_trs_monthly_value` segue sendo a renda-alvo **declarada**, e passa a derivar
explicitamente de `if_meta_bruta` — mesmo valor, procedência agora dita.

### D4 — A identidade da composição vira check, e o CV5 deixa de ser tautologia

`CV5` afirmava `if_meta × TRS ÷ 12 == if_trs_monthly_value` sobre dois campos em que o
segundo **deriva do primeiro** — não podia falhar. Passa a afirmar a composição:
`|if_meta − (if_meta_bruta − termo_excluído × 12 ÷ TRS)| ≤ ε`, que cruza três campos de
produtores independentes (o Goal, o toggle e o IRPF).

### D5 — Meta clampada em zero publica ausência de progresso, não 100%

Se o termo capitalizado cobre a meta bruta inteira, `if_meta` clampa em zero e
`investivel_efetivo ÷ 0` deixa de ser mensurável. `if_pct` sai **`null`**, com
`if_meta_base = renda_externa_cobre_alvo` nomeando o caso.

Nem 0% nem 100% servem. **0%** contradiz `if_gap` e `prazo_anos_realista`, que já dizem
"chegou". **100%** concederia a banda de topo de um componente de **peso 2,0** a uma família
cuja carteira financeira pode ser **zero** — a renda que cobre o alvo vem de ativo que o
próprio workspace excluiu alegando que ele não sustenta retirada a TRS, exposto a vacância e
não perpétuo. É o número mais perigoso que o produto poderia emitir sobre independência.

Ausência propaga, como em [[ADR-373]] e [[ADR-369]]: o produto não escolhe a premissa em nome
da família. O consumidor de render passa a exibir traço + o motivo — o `?? 0` que existia
renderizaria "0,0%", o modo de falha que a [[ADR-412]] §D7 já nomeava para o piso.

### D6 — O piso lê a mesma meta

`if_projection_piso` ([[A40.l80]]) media o extremo conservador do numerador contra a meta
**bruta**. A queda do piso deixava de ser atribuível: parte vem da fatia sem dono (o que o
piso existe para mostrar) e parte da base da meta (o que ele não deveria misturar). Passa a
receber o mesmo termo — é o §D2 aplicado a um eixo que já existia.

## Alternativas rejeitadas

- **Só corrigir a FORMULAS.md** (declarar que a base de produção é a bruta). Fecharia a
  divergência doc↔código e deixaria viva a dupla-penalidade no regime default. O doc estava
  errado *e* o código estava errado — em regimes diferentes.
- **Ligar `goal.if` v2** ([[ADR-140]]), pedindo `renda_passiva_atual_mensal_brl` à família.
  Um input declarado cuja corretude depende de a família conhecer o valor do toggle, e cuja
  regra anti-dupla-contagem é prosa num schema. O pipeline já **observa** a renda passiva e
  já **sabe** o toggle; perguntar seria transferir à família a conciliação que é nossa.
- **Descontar a renda passiva observada inteira** (a leitura literal da FORMULAS.md). No
  regime `true` isso dupla-conta 93% do patrimônio gerador — infla o progresso em 4,68 pp
  sem que nada tenha mudado no patrimônio da família.
- **Manter a meta bruta no regime `false`, tratando a exclusão como "ignoro o imóvel
  inteiro — patrimônio E renda".** É a leitura conservadora, e ela cai no que a [[ADR-223]]
  §Contexto de fato decide: *"capital que não bate a TRS não é capital de FIRE"*, com a copy
  do banner falando em cap rate. É juízo sobre a **capitalização do ativo**, não sobre a
  **existência do fluxo** — o aluguel é fato observado no IRPF, e suprimi-lo por desconfiar
  do múltiplo confunde avaliação com observação. A objeção legítima que sobra é de
  **magnitude e durabilidade**, e a resposta dela é o haircut do §D2, não o zero: zerar é o
  haircut de 100% aplicado ao componente de maior peso do score.

## Desvio de protocolo, declarado

O CLAUDE.md §"ADR `Proposto` antes de PR P0/P1" pede ADR `Proposto` **num PR anterior** ao de
implementação, flipando a `Decidido` no merge. Esta nasceu `Decidido` dentro do próprio PR de
implementação (#1753). O desvio teve custo mensurável **nesta lane**: entre a escrita e o
merge, o co-design `financial-planner` inverteu o §D2 (o predicado lia o toggle, não a
exclusão) e criou o §D5 — exatamente a janela que o estado `Proposto` existe para sinalizar.
Registrado para que o próximo P0 de invariante não repita.

## Consequências

- Golden do dogfood: delta **`=`** (o workspace medido está em `imoveis_no_if = true`, onde o
  termo é zero e a meta não se move ao centavo). O rebaseline é de **forma** — duas chaves
  novas em `goals` (`if_meta_bruta` e `if_meta_base`; a terceira não sai porque a fixture não
  tem IRPF) —, não de valor.
- Workspaces em default (`false`) com aluguel observado passam a ver progresso **maior** e
  gap **menor**. É correção, e move o score.
- `alugueis` é balde **residual** em `_renda_passiva_observada` (absorve o que o split
  IRPF não classifica). No regime `false` o termo herda essa imprecisão — por isso ele é
  publicado com nome próprio em vez de embutido no número, e a meta é clampada em zero.
- Segundo eixo de exclusão futuro sem passar por D2 reabre o defeito. O check do D4 é o que
  o denuncia.
- **Existe uma intenção para a qual o zero seria correto** — *"vou vender esse imóvel; ele
  não faz parte do meu plano de IF"*. Essa intenção **não** é o que `imoveis_no_if` captura
  hoje (o toggle é sobre cap rate, [[ADR-223]]). Se for capturada um dia, é campo
  **diferente**, e entra pelo ponto de extensão do §D2 com termo = 0. Escrito aqui para o
  próximo não relitigar.
- **O aluguel não é perpétuo nem cresce com a carteira**, e capitalizá-lo à mesma TRS trata
  contrato com prazo como retirada perpétua. É herdado da fórmula bruta (que já assume
  perpetuidade sobre a renda-alvo), então esta ADR não piora — mas fica nomeado. TRS separada
  para a perna de aluguel é follow-up, não esta lane.
