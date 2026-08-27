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

É a imagem espelhada do invariante anti-dupla-contagem da [[ADR-142]], que só estava escrito
na `description` de um campo do `goal.if.v2.schema.json` — schema **candidato**, nunca em
produção. O lado que produção de fato exercita nunca teve enunciado nem gate.

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

### D2 — O termo excluído deriva do toggle, não de um campo novo

Hoje o único eixo que move ativo para fora de `investivel_efetivo` é `imoveis_no_if`. Então
`renda_passiva_fora_do_investivel_mensal` é o balde `alugueis` de `passive_income` quando o
toggle é `false`, e `0` quando é `true`. Sem input novo, sem migração, sem pedir à família um
número que o pipeline já observa.

Quando um segundo eixo de exclusão aparecer, ele entra **aqui** — o termo é o ponto de
extensão, e um eixo novo que não passe por ele reabre o defeito.

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
