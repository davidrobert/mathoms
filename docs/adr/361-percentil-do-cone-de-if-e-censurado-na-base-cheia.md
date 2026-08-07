---
id: ADR-361
type: adr
title: "Percentil do cone de IF é quantil da base cheia com censura declarada, não mediana dos bem-sucedidos"
status: Decidido
phase: "A40"
date: "2026-08-03"
amended_at: ["2026-08-05"]
relates_to:
  - "[[ADR-360]]"
  - "[[ADR-237]]"
  - "[[ADR-217]]"
  - "[[ADR-292]]"
  - "[[ADR-306]]"
supersedes: []
superseded_by: []
aliases: ["ADR 361", "censura do cone de IF", "P50 condicional"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
  - phase/a40
---

# ADR-361 — Percentil do cone de IF é quantil da base cheia com censura declarada

> **Emenda 2026-08-05 (decisão do dono):** flip `Proposto` → `Decidido`, na mesma
> passada da [[ADR-360]]. Código em `main` desde 2026-08-03 (`790c1c5f`/#1162),
> gateado por teste; a nota one-shot que cobre a variação desta ADR (maior que a
> do reseed — ver §Consequências) ganha especificação em [[ADR-360]] §Nota
> one-shot, para não duplicar o mecanismo em duas ADRs.

## Contexto

`_simular_caminhos` calculava os percentis do ano de IF sobre
`primeiro_true[alguma_vez] + 1` — **só as simulações que atingem a meta dentro do
horizonte de 40 anos** — enquanto `_prob_ate_meta` usava `n` cheio no
denominador. As duas estatísticas tinham populações diferentes e eram publicadas
na mesma frase pelo narrador determinístico.

O "P50" publicado era, portanto, a mediana **dos bem-sucedidos**: otimista por
construção. E o viés cresce quanto pior é o plano — quanto menos cenários atingem
a meta, mais selecionada é a amostra que gera o percentil. Quem mais precisa de
alerta recebia o número mais otimista.

Medição sobre 120 cenários (meta R$ 10 M, retorno real 5%, sigma 11%, n = 50k):

| taxa de sucesso em 40a | viés médio do P50 | viés máx | P50 é ficção | P90 é ficção |
| --- | --- | --- | --- | --- |
| < 50% | — | — | 4/4 | 4/4 |
| 50–70% | +6,9a | +10a | 0/9 | 9/9 |
| 70–90% | +2,8a | +5a | 0/22 | 22/22 |
| 90–99% | +0,4a | +1a | 0/34 | 0/34 |
| ≥ 99% | +0,0a | +1a | 0/51 | 0/51 |

Três leituras decidiram o desenho:

1. **A perna adversa era a mais corrompida.** O P90 só é definível na base cheia
   se a taxa de sucesso ≥ 90%; em 29% dos cenários o produto publicava um "P90 =
   36 anos" cujo valor verdadeiro está fora do horizonte. A perna que existe para
   mostrar risco era incapaz, por construção, de mostrar fracasso.
2. **O gráfico contradizia a própria legenda.** `caminho_p50` é o percentil 50 de
   *patrimônio* sobre `n` cheio — incondicional. Com sucesso 43,6% o relatório
   desenhava uma linha central que nunca cruza a meta, legendada "meta em 2059";
   com 61,8%, a linha cruzava 8 anos depois do ano rotulado.
3. **O gate lia o número enviesado.** `_GATE_P50_MAX = 35` decidia
   `exibir_cone` a partir do P50 otimista, então deixava passar plano que
   deveria suprimir — e, quando suprimia, entregava o achado mais grave no tom
   mais fraco que o produto tem (rodapé cinza de 12px com ícone `Info`).

O invariante que define a semântica: **P(atingir a meta até o ano rotulado `Pk`)
tem de ser k%**. O cálculo condicional errava até 26 pp no P50 e 49 pp no P90.

> **Reconciliação com o #1158.** Durante a execução desta lane o #1158 mergeou em
> `main` a aposentadoria da sentinela 999 — item 5 do §Deferimento da
> [[ADR-360]]. Isso tornou `prob_if_ate_idade_meta` e `idade_meta_usada`
> nulláveis, o que esta ADR absorve: o contrato v3.0 preserva a nulabilidade, e o
> guard do narrador lê `if_ano is None` em vez do valor legado.

## Decisão

Co-design com `financial-planner` (semântica), `product-designer` (copy) e
`data-engineer` (contrato). A opção "condicional explícito" — manter o cálculo e
rotular "entre os cenários em que a meta é atingida" — foi **rejeitada**: rotular
não conserta uma estatística de seleção na variável dependente, e uma métrica
cujo otimismo cresce quando o plano piora é defeito de produto independentemente
da legenda.

**D1 — Percentil é quantil empírico da base cheia, com censura à direita.**
`inverted_cdf` sobre `np.where(alguma_vez, primeiro_true + 1, inf)`. Como o
quantil é uma estatística de ordem sobre anos inteiros, não há interpolação para
`int()` truncar — o viés sistemático de ~meio ano para baixo do
`int(np.percentile(...))` acaba como efeito colateral.

**D2 — `Pk` só é publicável como ano se a taxa de sucesso o sustenta com folga de
5 pp.** Piso de definibilidade é aritmética (`Pk` existe ⟺ sucesso ≥ k%); a folga
existe porque `P50` com sucesso 50,2% é o ano dos últimos caminhos a cruzar —
instável ao horizonte e ao seed, e o relatório reemitido pularia anos. Na
prática: P10 exige 15%, P50 exige 55%, P90 exige 95%.

**D3 — Guarda de assimetria: a perna favorável não sai sem a central.** A censura
morde primeiro o lado adverso, então publicar só o P10 trocaria o viés otimista
por um pior — sobraria apenas a boa notícia. Com P50 censurado, P10 também é
suprimido.

**D4 — A censura é publicada, não inferida.** `pXX_censurado` por percentil, e
`prob_if_ate_horizonte` (taxa de sucesso na base cheia) no payload. `null`
sozinho significaria tanto "cone não simulado" quanto "percentil além do
horizonte", e o consumidor que **não pode** derivar a diferença é o parecer:
`$.if_monte_carlo` é path citável ([[ADR-292]] / [[ADR-306]]) e o distiller injeta
o bloco cru, sem o schema. As três flags derivam de **um** predicado sobre
`prob_if_ate_horizonte`, logo são monótonas (P50 censurado ⇒ P90 censurado).

**D5 — Flags intercaladas com o percentil que qualificam.** O corte do distiller
é prefixal; agrupá-las depois dos três anos abriria uma janela em que o LLM lê o
ano sem saber que é censurado. Consequência medida: o prefixo escalar passou de
300 chars (320 com cone, 369 com o cone suprimido, onde `motivo_sem_cone` é
string longa), então o bloco declara `max_chars: 380` no manifest — sem o knob a
correção de honestidade entraria cortando dado de domínio do contexto do LLM.

**D6 — `_GATE_P50_MAX` deletado.** Sobra apenas a supressão que é sobre **dado**
(`if_pct < 15%`), não sobre notícia ruim. Plano ruim passa a renderizar o cone
com o diagnóstico na copy. Entre os dois erros possíveis, maquiar é pior que
esconder — esconder é omissão que o usuário percebe (há um motivo escrito),
maquiar é comissão indetectável sobre a qual ele decide.

**D7 — `mc_version` 2.0 → 3.0.** Versão do **contrato** publicado, não do RNG
(padrão `score_version` / [[ADR-217]] §D3). O mesmo `p50_ano_if` significa números
não-comparáveis entre as versões: ausente = v1 (não-seedado, n=10k, percentil dos
sobreviventes); `"2.0"` = seedado, percentil dos sobreviventes; `"3.0"` = seedado,
percentil censurado.

**D8 — `pv >= fv` retorna cedo.** O horizonte-meta degenerado (`prazo = 0` →
`primeiro_true < 0` nunca verdadeiro) publicava "0% de chance de atingir IF" para
a família que já é independente. Agora: sem cone, `motivo_sem_cone = "meta já
atingida"`, probabilidade 1,0. Converge com o #1158, que pela mesma razão trocou
`0.0` por `null` quando não há idade-meta — "0%" afirma "nenhuma simulação
atinge", que é diferente de "a pergunta não se aplica". Quando `idade_meta` é
`None`, `prob_if_ate_idade_meta` continua `null` mesmo neste caminho.

**D9 — A mediana censurada tem frase própria.** Sem isso a correção **pioraria** o
relatório: o narrador testava `if p50 and prob is not None` e `p50 = None` caía na
frase determinística ("a trajetória projetada aponta a meta para {if_ano}"), a
mais otimista do relatório e sem incerteza declarada — passaria a disparar
exatamente quando a mediana não atinge a meta, movendo a mentira do número para a
prosa, que o `golden_diff` não audita. Quatro estados, um por regra de copy;
rótulo de percentil sai do texto user-facing porque o sufixo `p10` é favorável no
ano e adverso na série de patrimônio.

## Consequências

- **Números que o cliente já viu mudam**, na mesma release da [[ADR-360]]: a nota
  one-shot que aquela ADR pede ("recalibração do modelo — a variação vem do
  modelo, não da sua carteira") cobre também esta mudança. Aqui a variação é
  maior que a do reseed, e é sempre no sentido de piorar a data publicada — sem a
  nota, a inferência racional do cliente é "meu plano piorou".
- **Planos ruins ganham um cone que antes era suprimido.** Mudança visível de
  produto: onde havia um rodapé cinza passa a haver gráfico + diagnóstico
  explícito.
- **`p50_censurado = true` com `exibir_cone = true` é estado novo e observável.**
  Antes, `pXX_ano_if is None` ⟺ `exibir_cone is False`.
- O estado "central existe, adverso censurado" produz a frase mais valiosa da
  feature, hoje impossível de emitir: no cenário central a meta é alcançada; no
  adverso, não dentro do horizonte.
- Sem backfill de artefato histórico: E5 é output imutável de modelo versionado, e
  reescrevê-lo destruiria o rastro do que o cliente viu. `mc_version` é a defesa.
- `prob_if_ate_horizonte` **não** entra no catálogo de citação: `_is_money_key`
  ainda formata valor citável como R$, e `prob_if_ate_idade_meta` já sofre disso.
  Não replicar o acidente — corrigir a classe é lane do `prompt-engineer`.

## Deferimento datado — 2026-08-03

Levantado no co-design, fora do escopo desta ADR, com dono no owner:

1. ~~**`idade_meta_usada` é output do modelo, não pergunta da família.**~~
   **Fechado pela [[ADR-369]] D2** (#1269, 2026-08-07): a probabilidade passou a
   medir o prazo que a família declarou, e `prob_if_ate_idade_meta` /
   `idade_meta_usada` foram **removidas**, não reaproveitadas. A premissa deste
   item — *"exige campo novo (`idade_meta_if`, default 65, editável)"* — era
   **falsa**: `horizonte_anos` já é `required` no `goal.if` v1 e o wizard já o
   pergunta; o campo era **descartado** por `_serialize_if_goal`. E o diagnóstico
   de amplitude estava certo pelo motivo errado: os 14,8 pp vinham de os oito
   planos terem **folga zero** (prazo declarado == determinístico), não da fonte
   do alvo — com a folga variando, a amplitude medida foi de ~85 pp.
2. ~~**`p10`/`p90` apontam para lados opostos no mesmo payload.**~~
   **Fechado pela [[ADR-369]] D1** (#1268, 2026-08-07): `mc_version` 4.0,
   rename-only. Os **três** anos foram renomeados (não só p10/p90 — deixar
   `p50_ano_if` no meio da família recriaria a confusão dentro dela), junto das
   flags de censura e do par `horizonte_simulado_anos` /
   `prob_if_ate_horizonte_simulado`. `caminho_p10/p50/p90` ficaram como estavam.
3. ~~**A sentinela 999 do determinístico vaza em outras superfícies.**~~
   **Resolvido pelo #1158**, mergeado em `main` durante a execução desta lane:
   `prazo_anos_realista`, `ano_if`, `idade_titular_if`, `idade_meta_usada` e
   `prob_if_ate_idade_meta` passaram a emitir ausência (`null` +
   `motivo_prazo_indefinido`) em vez da sentinela, e o schema fechou
   `idade_meta_usada` com `maximum: 120`. Esta ADR foi reconciliada: o guard do
   narrador lê `if_ano is None` em vez de `if_prazo_anos >= 999`, e
   `prob_if_ate_idade_meta` é `float | None` no contrato v3.0.
4. **Dois anos de IF concorrentes na mesma seção.** O determinístico ocupa dois
   slots de destaque (`SectionSummary` e KPI) e o probabilístico um de rodapé — a
   precisão falsa no lugar nobre. Recomendação do `product-designer`: rebaixar o
   determinístico a premissa enunciada como aritmética. É o item 1 do
   §Deferimento da [[ADR-360]].
5. **Probabilidade em faixa de 5 pp** ("cerca de 30%") — mantida em inteiro aqui
   porque exige paridade com `formatProbability` no TS e é sobre a precisão da
   probabilidade, não sobre a população do percentil.
6. **Inversão de eixo: publicar "quanto", não "quando".** O patrimônio mediano na
   idade-meta já é calculado (`caminho_p50`), é incondicional por construção e
   sempre existe; convertido pela TRS vira renda passiva mensal. Torna a censura
   sustentável em vez de fazer o produto emudecer no plano ruim.
7. **Componente de faixa na UI.** Os anos do MC não são renderizados hoje —
   chegam ao leitor só pela frase do narrador e pelo parecer. O
   `product-designer` especificou um `IFFaixaAnos` com intervalo de extremo
   aberto ("2049 — após 2066") e a regra de que `—` fica reservado a "não
   simulamos".

## Referências

- Implementação: `pipeline/domain/services/if_monte_carlo.py`,
  `pipeline/domain/services/narrativas/projecao_if_narrator.py`
- Gates: `tests/test_if_monte_carlo_censura.py`,
  `tests/test_e5n_projecao_if_censura.py`,
  `backend/tests/test_parecer_exec_context_mc_budget.py`
- Origem: [[ADR-360]] §Deferimento datado, item 3
