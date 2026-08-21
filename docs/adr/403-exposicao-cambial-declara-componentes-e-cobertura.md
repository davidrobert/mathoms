---
id: ADR-403
type: adr
title: "Exposição cambial declara seus componentes e a cobertura de cada um; veredito nunca excede a pior cobertura"
status: Decidido
phase: r7.FP-5B
date: "2026-08-19"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-193]]"
  - "[[ADR-209]]"
  - "[[ADR-224]]"
  - "[[ADR-379]]"
  - "[[ADR-390]]"
  - "[[ADR-394]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 403"
  - "componentes da exposição cambial"
  - "tier indeterminado"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - phase/r7
---

# ADR-403 — Exposição cambial declara seus componentes e a cobertura de cada um

## Contexto

No run r7 (`ws-1b9f2cf5`, run `33514dc4`), `exposicao_cambial.detalhes` tinha 4
entradas, **todas** `tipo == "caixa"`, e `pct_investivel_financeiro` = 6,98%
com `tier: "amarelo"`. O braço de carteira de `compute_exposicao_cambial`
contribuiu **zero**.

Não porque a carteira seja zero: o bucket `Internacional` vale **2,84% da
carteira financeira** na tabela de classes. As duas rotas leem **universos
diferentes** — `investimentos.fonte == "irpf_bens"` alimenta a tabela, enquanto
o card lê `investimentos_atuais["dados"]` (posições atuais do E4), vazio nesse
workspace. Um componente inteiro do KPI publicou zero silencioso sob semântica
de cobertura total.

Três fatos medidos que enquadram a decisão:

1. **Somar o bucket não muda o veredito.** 6,98% + o bucket ≈ 9,8% do
   investível financeiro — ainda dentro de "amarelo" (5–10%). O ganho da
   correção não é mudar de faixa; é parar de afirmar uma faixa sobre um
   numerador que o run não fechou.
2. **O risco de dupla contagem é real e realizado.** Na medição do r7,
   `classify_asset` ainda recebia `instituicao` no haystack e o bucket
   `Internacional` carregava keywords de custodiante — `wise`, `bofa`,
   `bank of america` — além de `moeda estrangeira` e `exterior`. Medição: **as
   4 linhas de caixa em ME seriam classificadas como `Internacional`**. A
   [[ADR-400]] depois separou as duas perguntas, mas **não** eliminou o risco:
   moveu o custodiante para `_CUSTODIA_ESTRANGEIRA` como gatilho independente
   neste módulo. Somar bucket e caixa sem de-dup infla o KPI e vira dano de
   sinal — antes e depois do #1571.
3. **O tier era lido como alvo de alocação.** O card rotulava `verde` como
   "adequado" e `vermelho` como "sub-alocado", enquanto a ADR-224 §6 recomenda
   20–30% USD para o ICP — dois alvos assinados e incompatíveis para o mesmo
   conceito. O card dizia "adequado" com 10% enquanto o comparativo de
   alocação prescrevia compra.

## Decisão

**D1 — Exposição ECONÔMICA, composta de componentes nomeados.**

```
exposicao_cambial.componentes = {
  caixa_fx:                    {valor_brl, cobertura},
  carteira_lastro_estrangeiro: {valor_brl, cobertura},
}
cobertura ∈ {apurado, parcial, indeterminado}
```

`total_brl` soma **apenas** os componentes `apurado`. Em v1 a carteira é
**observacional**: medida e publicada com a própria cobertura, fora do total.

**D2 — `∃ componente com cobertura ≠ apurado ⇒ tier = "indeterminado"`.**
A cobertura incompleta suprime o **veredito**, não a medida: `total_brl` e
`pct_investivel_financeiro` continuam publicados como **piso**. O erro aqui é
assimétrico — subestimar diz "compre proteção" a quem já tem; superestimar diz
"você está protegido" a quem não está, e esse é o lado caro.

**D3 — `definicao_versao ∈ {1, 2}`, emitido ANTES da mudança de definição.**
v1 = só caixa FX; v2 = caixa FX + carteira com lastro estrangeiro. O gate de
"série reiniciada" mora no **comparador** (`dev/serie_cambial.py`), não no
produtor: marcador que só o produtor emite é decorativo, porque nada impede o
leitor de subtrair tier de v1 contra tier de v2. Run pré-ADR-403 não declara
versão — comparar com v1 também é atravessar a fronteira.

**D4 — De-dup por construção.** `caixa_fx` e carteira são disjuntos:
`_pos_e_caixa_fx` recusa da carteira toda posição que já é caixa em ME.

**D5 — Custódia estrangeira é gatilho legítimo AQUI, e por isso o de-dup é
obrigatório.** A versão original desta nota decidia o oposto — que instituição
sairia da entrada deste caminho, porque é hint e não fato ([[ADR-394]]). A
[[ADR-400]] (DE-1, #1571) decidiu melhor e chegou primeiro em `main`: custódia
não responde **classe do ativo** (e por isso saiu do `asset_classifier`), mas
responde **lastro cambial**, que é a pergunta deste módulo. A lista vive
nomeada em `_CUSTODIA_ESTRANGEIRA`.

A consequência para esta ADR é o inverso de enfraquecer o D4: com custódia como
gatilho **independente** da keyword de classe, uma conta em ME num custodiante
estrangeiro passa a casar `_is_caixa_me` **e** os dois gatilhos de carteira.
Sem `_pos_e_caixa_fx`, ela entraria nos dois componentes. O de-dup ficou mais
necessário, não menos.

**D6 — `referencia_banda` declara contra o que o tier mede.** `tipo:
"piso_protecao"`, com os limiares e o dono da prescrição de alocação
(`acoes_int`). A banda **não muda** (verde ≥10%) — decisão do dono
2026-08-19 é separar os objetos e rotular, não recalibrar. O card cambial é
diagnóstico de **estoque** e deixa de prescrever aporte em classe.

**D7 — CV18 cruza conservação e cobertura.** Σ(apurados) == `total_brl`; e
`carteira.cobertura == apurado ⇒ carteira == bucket Internacional`. Divergir é
erro de conservação, não diferença tolerada — é o predicado que impede um v2
futuro de flipar a cobertura sem reconciliar os universos.

## Alternativas rejeitadas

- **Somar o bucket agora e seguir com tier numérico.** Sem de-dup infla ~42%;
  com de-dup ainda mistura dois universos sob um número só.
- **Manter o tier calculado sobre a soma parcial.** É a afirmação que o r7
  fez: "amarelo" sobre metade do numerador.
- **Recalibrar a banda para 20–30% (ADR-224 §6).** Fundiria diagnóstico de
  estoque com alvo de alocação. Decisão do dono: separar e rotular.
- **Coluna `protecao_cambial` em `asset_catalog`.** `lastro_moeda` já existe
  ([[ADR-224]]) e cobre o eixo; a elegibilidade por ativo é o escopo de v2 e
  vira follow-up, não meia-solução dentro deste PR.
- **Fechar por inspeção.** Precedente: RV2-08 fechou 2× e reincidiu. Os gates
  aqui são provados por mutação.
- **Manter o D5 original (instituição fora deste caminho).** A [[ADR-400]]
  chegou primeiro em `main` e a decisão dela é melhor: separa "quem guarda" de
  "o que é", em vez de descartar o sinal. Cedido.

## Consequências

- No r7: `tier` **"amarelo" → "indeterminado"**; `total_brl` e
  `pct_investivel_financeiro` **inalterados** (6,98%). Nada foi somado — o que
  mudou é o que passou a ser **declarado**.
- O card ganha o estado `indeterminado` e troca os rótulos de alvo de alocação
  ("adequado"/"sub-alocado") por linguagem de piso de proteção.
- Comparação de tier entre runs de versões distintas passa a emitir nota de
  série reiniciada, nunca delta.
