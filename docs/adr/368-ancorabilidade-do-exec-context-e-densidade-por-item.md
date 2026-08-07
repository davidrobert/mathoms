---
id: ADR-368
type: adr
title: "Ancorabilidade do exec context: todo valor monetário visível é ancorável, e densidade mede-se por item e por delta de versão"
status: Proposto
date: "2026-08-07"
phase: A40
relates_to:
  - "[[ADR-341]]"
  - "[[ADR-296]]"
  - "[[ADR-358]]"
  - "[[ADR-279]]"
  - "[[ADR-304]]"
  - "[[ADR-366]]"
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
  - phase/a40
---

# ADR-368 — Ancorabilidade do exec context e densidade por item

## Contexto

#1004 bumpou `PROMPT_VERSION` 2.1.0→2.2.0 e **a suíte inteira ficou verde**. O commit
mexeu no distiller (158 linhas) e no manifest (127); na persona, 14 linhas — só recovery
de eviction e o bump. Nenhuma regra de ancoragem foi tocada. Ainda assim a [[A40.l16]]
mediu densidade de âncoras 9→5 e prosa monetária 0→3,5 em 8 runs.

O gerador não mudou; **o input dele mudou**. Medido in-process (US$ 0): os valores `R$`
que o modelo vê no corpo dobraram (9→18 tokens médios) e o conjunto ancorável ficou
igual. Enquanto isso `_CATALOG_INSTRUCTION` manda literalmente *"Conceito ausente daqui
→ não ancore"*. Digitar o número na prosa é o comportamento que sobra.

**Nenhum teste assere o invariante.** `tests/test_parecer_citation_catalog.py` prova
round-trip, prioridade e cap; `tests/test_parecer_distiller_catalog.py` prova posição.
Nenhum prova *"valor R$ renderizado no corpo ⇒ path no catálogo"*. Foi essa lacuna que
deixou #1004 passar.

## Decisão

### D1 — Ancorabilidade é invariante do par (corpo projetado, catálogo renderizado)

Toda folha monetária que o modelo **vê no corpo** do exec context tem de ter path no
catálogo que o modelo **recebe**. Três pinagens de definição, sem as quais um instrumento
futuro mede o teto e fica verde-falso:

1. **Catálogo renderizado, não construído.** `build_citation_catalog` devolve 29 entries
   no corpus sintético; `max_bytes: 1600` deixa 20 passar. Contra o construído a cobertura
   é 94%; o que o modelo tem é 78%. "Ancorável" significa *"o modelo tem a linha na mão"*.
2. **Corpo pré-catálogo.** O bloco do catálogo imprime `path → R$ valor`: são tokens R$
   ancoráveis **por construção** (41 no exec context inteiro contra 18 no corpo). Varrer o
   contexto todo produziria verde estrutural medindo a camada errada.
3. **Seções sobreviventes à eviction.** Seção evictada não é visível. Sob `_hard_cut` a
   atribuição por seção deixa de ser exata e o instrumento declara-se **degradado** em vez
   de reportar número que não sustenta.

Respostas de tool (`get_e5_section`) ficam **fora de escopo**: ancoráveis por construção
([[ADR-341]] D5) e imensuráveis in-process.

### D2 — O gate é o diff de um conjunto, não um threshold

O baseline é o **conjunto ordenado de paths inancoráveis**, versionado em
`dev/snapshots/parecer_ancorabilidade.json`, junto dos **parâmetros que o geraram**
(`max_bytes`, `max_entries`, `_MAX_LIST_ITEMS`, `_PRIORITY_ROOTS`, `manifest_version`).

Threshold percentual está **rejeitado**: perde exatamente o caso #1004 (18 folhas a mais,
percentual quase estável) e move-se por dois motivos ao mesmo tempo quando o corpus ganha
bloco. Sem os parâmetros, o diff não distingue *"manifest cresceu"* de *"budget
encolheu"* — remediações opostas. Paths **legíveis**, nunca hash: aqui a legibilidade é o
produto (um #1004 futuro tem de ser lido em segundos no PR).

**Condição que legitima o snapshot:** regeneração determinística, in-process, **US$ 0**.
É o que separa este caso do contra-precedente no mesmo diretório —
`dev/snapshots/lineage_eval_baseline.json` está `pending_first_real_run` até hoje porque
preenchê-lo exige run owner-gated. Snapshot cuja regeneração custa dinheiro vira
placeholder eterno.

### D3 — Hard sobre o que o HEAD satisfaz; soft sobre o que ele viola

Os ratchets do **instrumento** (o conjunto cresce quando projeto R$ fora do catálogo?
limpa quando removo? cresce se `max_bytes` encolhe? encolhe se a seção é evictada?) e o
change-detector do snapshot são **hard** — nenhum é vermelho no HEAD, logo nenhum bloqueia
trabalho alheio. O alvo `inancoraveis == 0` é **soft**: é vermelho hoje e gateá-lo no PR
que introduz a métrica é o antipadrão que a [[ADR-358]] condena.

O flip **converge sozinho**: quando o conjunto esvaziar, "snapshot inalterado" e `== 0`
passam a ser o mesmo predicado. Não há decisão a drenar, há um estado. E o flip **não pode
ocorrer** na lane que instala a métrica: `tabela_classes[5]` só sai por `_MAX_LIST_ITEMS`↑
ou `max_rows`↓, ambos model-visible ⇒ eval-gated.

A barra da [[ADR-358]] §2 (budget de produção medido) **não se aplica** a este check: ele
é CI sobre fixture, e o pior caso é PR bloqueado, não conselho apagado. Herdar essa barra
travaria indevidamente a lane do gerador.

### D4 — `EVIDENCIA_VERIFICATION_VERSION` é alavanca de cache, não versão de schema

Acrescentar chave **aditiva** de telemetria ao summary **não** bumpa. O critério de bump é
*"um cache hit serviria conteúdo errado, mutilado ou ilegível"* — o denominador comum dos
bumps 2→6. Duas chaves novas não qualificam, e o bump invalidaria o envelope
([[ADR-366]] §D7) forçando geração cobrada: efeito colateral de política de cache, que a
própria ADR-366 rejeitou (re-geração é o retry **explícito** do usuário).

O estratificador é uma chave própria (`prose_inventory_version`). **Contrato de leitor,
obrigatório: ausência ⇒ `unknown`, excluído do agregado, nunca 0.** Lida como 0, uma
janela pré-instrumento produz densidade zero e um delta de drift falso. O antipadrão já
vive no repo (`tests/test_parecer_evidencia_llm_eval.py:84` faz `.get(..., 0)`) e **não
deve ser copiado** pelos sinais de drift.

### D5 — Duas populações, dois denominadores

Densidade mede-se sobre itens **ancoráveis** (os que o schema dota de `ancoras`); pureza
de prosa mede-se sobre **campos de prosa inventariados**. Nunca no mesmo loop: `diagnostico_geral`
e `notas_metodologicas[]` não podem carregar `ancoras`, então incluí-los no denominador
faria a densidade cair **por razão instrumental** — o #1004 reproduzido dentro do
instrumento.

### D6 — Densidade sem denominador não é medida

`itens_total` + `itens_sem_ancora` no summary. Sem eles "densidade" conflacia *menos
âncoras por item* com *menos itens*, e o estratificador é `(prompt_version,
manifest_version)` — não `prompt_version` sozinho, que conflacia mudança de prompt com
drift de payload (#1006, #1010).

## Evidência (66 execuções reais, US$ 0)

`dev/measure_parecer_ancoragem.py` sobre `pipeline_stage_logs.output_summary`:

| prompt / manifest | n útil | âncoras | itens | âncoras/item | prosa/item | dropped |
|---|---|---|---|---|---|---|
| 2.1.0 / 1.6 | 1 | 13 | 19 | 0,684 | 0,000 | 0 |
| 2.1.0 / 1.8 | 15 | 9 | 18 | 0,500 | 0,000 | 0 |
| 2.1.0 / 1.9 | 2 | 7 | 18,5 | 0,380 | 0,028 | 1 |
| **2.2.0 / 2.0.2** | 9 | **5** | **19** | **0,278** | **0,190** | **15** |

**O "9→5" decompõe-se: é inteiramente menos âncoras por item.** O número de itens é
praticamente constante (18→19). E a queda **começa antes de 2.2.0** — sob a *mesma*
`prompt_version` 2.1.0 a densidade cai 0,684 → 0,500 → 0,380 conforme o manifest anda.
`prompt_version` sozinho atribuiria ao prompt um declínio dirigido pelo manifest: o
confounder de D6 está **medido**, não hipotetizado.

**Mecanismo do resíduo.** `_PRIORITY_ROOTS` não contém `consumo_consciente` nem
`exposicao_cambial` ⇒ rank último ⇒ primeiros cortados por `max_bytes`. E as 127 linhas de
manifest do #1004 acrescentaram campos `format: brl` exatamente em `fluxo_caixa` e
`consumo_consciente`. Dois parâmetros independentes, em dois arquivos, sem invariante
ligando-os. Some-se a cardinalidade: o corpo renderiza `max_rows` (10/15) e o catálogo
pega `_MAX_LIST_ITEMS = 5` **por maior valor**, não por posição — há linha visível sem rota
por *ranking*, que nenhum ajuste de bytes resolve.

## Consequências

- Instrumento determinístico, US$ 0, sem geração nova; o eval de ~US$ 26 continua
  owner-gated e **não** é gate de entrada.
- Pisos de drift derivam da medição, não de estimativa: o Δ real é −0,222 âncora/item, e
  um piso calibrado no denominador do golden (~7 itens) ficaria **verde com a regressão
  viva**. Régua tem de vir da população medida.
- Tornar o corpus de eval fiel ao que produção projeta **derruba** a ancorabilidade
  medida de 77,8% para 42,9% e faz `max_entries` morder (29→30): a inanição de catálogo
  antes tida como impossível nesse corpus é real.

## Alternativas rejeitadas

- **Threshold percentual** em vez de diff de conjunto — perde o caso #1004 (D2).
- **Bumpar `EVIDENCIA_VERIFICATION_VERSION`** por chave aditiva — custa geração cobrada e
  compra 7 dias de TTL (D4).
- **Mover `_PRIORITY_ROOTS`/`_MAX_LIST_ITEMS` para o manifest agora** — é a remediação
  certa e é **model-visible**, logo eval-gated. Ver §Deferimento.
- **Re-baselinar `_DENSITY_FLOOR` para 5** — erro de categoria: o piso gateia o holdout
  **sintético** (onde a [[ADR-296]] §Re-eval mediu mediana 11); o "5" é do **dogfood em
  produção**. É o defeito nº 2 da [[ADR-358]] (gate medido num plano, aplicado em outro).

## Deferimento datado com dono

**2026-08-07 → [[A40.l31]]** (owner `prompt-engineer`). Os 5 parâmetros que determinam
conjuntamente a ancorabilidade — `format: brl` no manifest, `_PRIORITY_ROOTS`,
`max_bytes`, `max_entries`, `max_rows` vs `_MAX_LIST_ITEMS` — não têm dono único. A direção
decidida é **dono único no manifest**, e a execução espera a l31 porque muda o que o
modelo vê. **Condição de retomada:** quando a l31 abrir. Precedente de forma: [[ADR-356]].

Também deferidos, medidos e nomeados aqui: o cabeçalho órfão de `_render_table` com
`rows == []` (`_render_key_value` se protege, `_render_table` não), e rota de citação para
moeda estrangeira (`FormatHint` não tem `usd`, então `US$` na prosa é fabricação sem rota
possível) — pré-requisito de qualquer gate sobre `money_tokens_usd`.
