---
id: ADR-419
type: adr
title: "O gatilho de risco deriva de doutrina, nunca de alvo declarado; a regra nomeia a chave do KPI"
status: Proposto
date: "2026-08-29"
relates_to:
  - "[[ADR-191]]"
  - "[[ADR-340]]"
  - "[[ADR-365]]"
  - "[[ADR-367]]"
  - "[[ADR-387]]"
  - "[[ADR-399]]"
  - "[[ADR-412]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/dominio
aliases:
  - "ADR 419"
---

# ADR-419 — O gatilho de risco deriva de doutrina, nunca de alvo declarado

## Contexto

`PontosUrgentesAnalyzer` é a superfície **determinística** de risco do relatório — a
lista que o cliente lê como plano de ação, e a única que não depende do LLM. Ela tem
quatro regras e **nenhuma** consulta o catálogo canônico de limiar (`kpi_targets`,
[[ADR-399]]). Medido no dogfood: `concentracao_imobiliaria` em 82,19% contra limiar
canônico de 50% ([[ADR-340]]) e **zero** ponto urgente sobre isso.

A [[ADR-399]] §D4 **renuncia** a este escopo (*"o escopo é essa rota, não o repo"*) — não
o proíbe. Estendê-lo é decisão nova, não emenda: emendar a 399 para "estreitar uma isenção
que ela não deu" poria descrição falsa no registro permanente.

## Decisão

**D1 — O gatilho de risco lê o canal `risco`, nunca o canal `target`.** A precedência
*alvo da família vence doutrina* da [[ADR-399]] §D2 governa o `target` publicado; o mesmo
parágrafo fecha com *"quando o declarado viola um limiar canônico, publica-se o declarado
como `target` e **o limiar vira `risco`**"*. Esta superfície **é** o canal risco. Logo o
gatilho vem de doutrina, e alvo declarado nunca o move.

Não reencodamos a gradação: a [[ADR-367]] §D2 já decidiu que *o alvo gradua sem mover o
gatilho*. Esta ADR apenas nomeia qual canal a superfície lê.

**D2 — A regra nomeia a chave do KPI (`kpi_key`), não um mapa paralelo.**
`PontoUrgenteItem` ganha `kpi_key: Optional[str]`, declarado **por quem lê o limiar**.
Alternativa recusada: mapa `code → kpi_key` mantido ao lado — tabela paralela apodrece em
silêncio, e `code` já carrega duas cargas (identidade de regra, [[ADR-365]] §D3; chave
natural de `dev/golden_diff.py`). Com `kpi_key` no item, uma regra que pare de derivar do
catálogo perde o campo e o invariante fica vermelho sozinho.

**D3 — Elegibilidade é `limiar is not None`, e o produtor é quem decide.** Não há
predicado composto no consumidor. Cobertura ausente, procedência ausente e ausência de
doutrina são **todas** condição de existência do limiar, resolvidas no
`kpi_target_catalog` ([[ADR-399]] §D3 + §Emenda 2026-08-27). Consumidor que reimplementa
o predicado é o defeito que a [[ADR-399]] existe para impedir, um andar abaixo.

**D4 — Invariante por chave, e gate estático de cobertura.** Dois instrumentos, porque um
só não pega:

- **Por chave:** para todo limiar de doutrina que emite item, rompê-lo sem emitir o item
  correspondente ⇒ vermelho. **Nunca** a forma existencial `count(rompidos) > 0 ⟹
  len(itens) > 0`: medida no dogfood, ela **passa com o defeito inteiro presente**, porque
  o consequente é satisfeito por `rentabilidade_nao_medida`, que não compara limiar
  nenhum.
- **Gate estático:** `{chaves elegíveis} ⊆ {chaves com regra} ∪ {chaves dispensadas com
  motivo}`. É ele — não o invariante de payload — que pega "o catálogo ganhou chave nova e
  ninguém leu", que é como este catálogo nasceu órfão. A válvula do motivo é obrigatória:
  gate que força regra para todo limiar responde por conta própria uma pergunta de
  domínio.

O invariante lê o **artefato E5**, nunca o snapshot do view-model.

## Consequências

- Regra nova de risco = `code` novo + `kpi_key` + entrada no gate. Chave nova no catálogo
  sem regra e sem dispensa **reprova**.
- `seguro_vida` e `rentabilidade_nao_medida` seguem **sem** `kpi_key`: mapeiam órfãos por
  decisão de domínio ([[ADR-387]]; [[ADR-191]] §D5) e não são threshold — um é predicado
  booleano de gap, o outro é sentinela `== "N/D"`. Pôr número neles seria regressão.
- `endividamento_alto` é **número-neutro**: já lê a mesma chave do `scoring.json` que o
  catálogo usa. Derivar não move o golden.
- A polaridade da [[ADR-412]] §D7 é preservada: o item de reserva autoriza **aumentar**
  liquidez, então o conservador é o extremo inferior — morre a magnitude, nunca o item.

## Alternativas consideradas

- **Emenda à [[ADR-399]]** — recusada: o D4 renuncia escopo, não isenta. A emenda
  descreveria errado a decisão que emenda, e o `check_adr_amendment_signal` passaria,
  porque ele vê forma, não verdade.
- **Emenda à [[ADR-340]]** — recusada: ela fixa o limiar de concentração; *qual superfície
  o lê* é decisão diferente. Duas notas para um fato.
- **Nenhuma ADR** — recusada: são três contratos novos (canal, campo no wire, gate).
- **Invariante sobre `kpi_targets[].procedencia`** — recusada: o rótulo já esteve errado
  uma vez (`reserva_cobertura_meses` carimbada `goal_declarado` sobre número de
  `scoring.json`, corrigido no #1779), e consertá-lo quebraria o invariante que dependesse
  dele.
