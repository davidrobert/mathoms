---
id: A40.l92
type: lane
title: "A trilha de progresso ignora a polaridade do operador e enche conforme a métrica piora"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 2065
ship_date: "2026-10-08"
priority: P0
branch_slug: a40-l92-polaridade-do-comparador
owner: product-designer
depends_on: []
adrs:
  - "[[ADR-399]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/frontend
  - area/relatorio
---

# A40.l92 — `polaridade-do-comparador`

> **Origem:** painel de fecho da [[A40.l89]] em 2026-08-28 (`financial-planner` +
> `senior-cto`). Condição nomeada para a l89 poder fechar: residual sem lane vira
> inventário órfão, e **este publica falsidade hoje**.

## O fato

`ParecerMetricasTable.tsx` calcula a trilha como `clamp(atual / alvo × 100, 0, 100)`, sem
noção de direção. Para as **4 chaves com operador de teto** (`<` / `<=`) —
`concentracao_imobiliaria`, `taxa_endividamento`, `alocacao_renda_fixa`,
`despesas_nao_categorizadas` — **a barra enche conforme a métrica piora**.

> **Correção de escopo recebida da [[A40.l93]], 2026-08-28 — são 3, não 4.**
> `alocacao_renda_fixa` deixou de publicar alvo: virou órfã por decisão de domínio
> ([[ADR-399]] §Emenda 2026-08-28), porque desvio de alocação é bidirecional e nenhum
> operador escalar o exprime. Sem `target` não há trilha, então a chave sai da lista
> desta lane. **As 3 que ficam são as que importam** — `concentracao_imobiliaria`,
> `taxa_endividamento`, `despesas_nao_categorizadas` —, e o caso medido abaixo é uma
> delas. O diagnóstico da lane (o `operador` não viaja no wire e o front re-deriva por
> regex sobre a string renderizada) **não muda**.

Caso medido: `taxa_endividamento` 45% contra `≤ 20%` ⇒ `extractNumber("≤ 20,0%") = 20` ⇒
`pct = min(100, 225) = 100` ⇒ **trilha 100% cheia sobre uma violação de 25pp**. Barra cheia
é a gramática visual universal de "meta atingida".

## Por que é P0 e por que agora

O defeito é **anterior** à [[A40.l89]], mas ela o **agravou**: antes, a barra visualizava
um alvo autorado pelo LLM; agora visualiza `limiar_canonico` com procedência declarada — o
selo do produto. É o gêmeo desenhado do `"6 meses ≥ 6 meses"` que a l89 consertou por
escrito, e consertar o texto deixando a figura mentindo é incoerente. Num `<table>` a 12px
o gráfico é lido antes dos dígitos.

## O diagnóstico é de CONTRATO, não de CSS

`operador` existe no `KpiTarget` (`<`, `<=`, `>=`) e **não viaja no wire**. O front
re-deriva por `extractNumber` — regex sobre a string renderizada — e a regex
`[^0-9,.-]` **come o glifo**: `"≤ 20,0%"` e `"≥ 20,0%"` são indistinguíveis para ela.

Isso é a mesma classe do defeito que a [[ADR-399]] fecha, um andar acima: **autoridade
determinística perdida na serialização**. Não se conserta com regex melhor.

## Escopo

1. **Mitigação imediata** (pode sair antes do resto): suprimir a trilha quando o operador
   for de teto. Trilha vazia lê "não medimos" — falso-menor; barra cheia lê "atingido" —
   falso-invertido com o selo do produto.
2. O finalize publica a polaridade: `operador` e/ou `progresso_pct` já computado
   server-side. DTO, snapshot OpenAPI e tipo TS acompanham.
3. Read-path **subtrativo** para pareceres congelados sem o campo — a leitura só remove
   afirmação, nunca acrescenta número a documento entregue ([[A40.l89]] §Escopo 3).
4. O front deixa de fazer regex sobre string renderizada.

## Decisão de produto que a lane precisa (não é de engenharia)

O que "progresso" significa contra um **teto**? Encher ao contrário (100% = folga máxima)?
Binário conforme/violado? Faixa com zona de atenção? A resposta muda o campo que o backend
publica — decidir antes de implementar.

**Decidida em 2026-10-08** — ver §Co-design abaixo: **binário**, com a barra só no piso.

## Co-design 2026-10-08 — o que "progresso" significa contra um teto

Painel `product-designer` (dono) + `financial-planner` + `data-engineer`, em paralelo.

- **Progresso contra teto não existe** nas três metodologias (`financial-planner`): abaixo
  do teto nenhuma delas trata "menor" como "melhor" — dívida barata não é meta a quitar,
  imóvel zero não é meta de concentração. Barra invertida induziria a quitar financiamento
  barato ou vender imóvel para "encher a barra". **Binário é o honesto.**
- **Status em TODA linha com operador**, inclusive o piso: reserva de 5,6 contra 6 meses vira
  barra a 93%, que a 12px se lê "atingido" — o gêmeo do `"6 meses ≥ 6 meses"`.
  Piso: "Alvo atingido" / "Abaixo do alvo", com a barra como codificação secundária
  (a 1ª rodada dizia "mínimo"; a revisão adversarial mostrou que é falso para a reserva —
  ver §O que foi entregue).
  Teto: "Dentro do limite" / "Acima do limite", **sem barra**. Cabeçalho "Trilha" →
  "Situação". O status afirma **só o comparador** — "dentro do limite" não é "dívida
  saudável".
- **Violação em âmbar, nunca vermelho** (`product-designer`): o comparador licencia
  conforme/não conforme, não severidade — a severidade é do canal de risco.
- **Despesas não identificadas não comporta veredito de conformidade** (`financial-planner`):
  o número fala da leitura do relatório, não da família. O status é o
  `diagnostico_confianca.nivel` do produtor, na tríade da própria [[ADR-353]] — "Cobertura
  alta" / "Cobertura parcial" / "Cobertura insuficiente" —, nunca "acima do limite". E a
  célula **Alvo** também sai (`product-designer`): `≤ 10,0%` devolveria o veredito, porque o
  leitor faz a conta e 12% vira violação da família; e o 10 sozinho apagaria o degrau de 30.
  No catálogo ela vira **órfã por (b)**, com o motivo "mede a leitura do relatório, não a
  família".
- **Fronteira:** o limiar é o último valor conforme, nas duas direções. Concentração e
  despesas publicavam `<` e afirmavam violação no ponto exato em que agregador, red-line e
  registro de risco diziam conforme; o veredito publicado contradiria o canal de risco.
  Corrige-se **o catálogo**, não só o veredito ([[ADR-399]] §Emenda 2026-10-08):
  concentração passa a `<=`, e despesas sai do comparador. Por isso esta lane **muta E5**
  (ver §Fora de escopo).
- **Contrato** (`data-engineer`): `comparador = {operador cru, conforme, progresso_pct}`
  estampado pelo finalize, `conforme` sobre o bruto pelo predicado único
  `conforme_ao_limiar`, `progresso_pct` só no piso e 100 **só se** conforme. O front desenha;
  não julga e não faz regex.
- **Precisão:** número e status não podem se contradizer na mesma linha — se 1 casa faz o
  observado cair sobre o limiar, mostra-se a 2ª ("20,04%"). Arredondar na direção do
  veredito fabricaria número.

## Sequência de PRs

1. ✅ **#2042** (`23b7f0b4`) — o enum `metrica_key` do schema do parecer tinha perdido
   `imobilizacao_patrimonial`; todo `Literal` de `Metrica` fica gateado por igualdade de
   conjunto. Saiu **antes** porque esta lane muda o mesmo `$defs/metrica`.
2. ✅ **#2048** (`131e04d0`) **Doutrina do limiar** — predicado único `conforme_ao_limiar`; concentração `<=`;
   `KpiTarget` recusa operador estrito; despesas vira órfã por (b), com a base = soma das
   categorias ([[ADR-353]] D2); o tier de despesas julga o share que publica. Mergeado
   **antes** do veredito, por condição do `financial-planner`.
3. ✅ **#2065** **O veredito** — `comparador` no artefato, no DTO e no TS; status na tabela; barra só no
   piso; despesas com o nível do produtor; read-path subtrativo; baseline de print com linha
   de teto. Inclui o furo medido pelo `data-engineer`: o ramo sem catálogo do estampador
   **preserva** `target`/`valor_atual` que o LLM emita (`SkipJsonSchema` só esconde o campo).

## Fora de escopo

- ~~A polaridade das **regras determinísticas de risco** → [[A40.l90]]~~ — **rota morta
  desde 2026-08-29**: a l90 fechou (`shipped`). O trabalho **volta para esta lane**, que é
  a dona do assunto; rota de trabalho futuro aponta para dono vivo, nunca para uma lane só
  porque o tema nasceu lá.
  **O que a l90 deixou pronto como substrato** (#1813/#1814): a polaridade do gatilho
  virou **dado tipado** — `RiskTrigger.operador` com `conforme()`/`rompido()` em
  [`risk_trigger_registry.py`](../../../../pipeline/domain/services/risk_trigger_registry.py),
  e a §Fronteira registra que `<=` e `<` divergem em 50,00 exato para o mesmo conceito.
  **O que falta é exatamente o §Critério desta lane:** esse operador **não chega ao
  front** — o wire ganhou `kpi_key`, não `operador`. Então "a polaridade chega ao front
  como dado, não por parsing da string" segue aberto, agora com o produtor já tipado.
- ~~Não muta E5 ⇒ **não entra na janela de rebaseline** e não zera o contador de 2
  re-runs.~~ **Falso desde o co-design de 2026-10-08:** a doutrina do limiar muta
  `kpi_targets` (o operador da concentração; a entrada de despesas, que vira órfã) e
  `diagnostico_confianca` (o tier na faixa de arredondamento) — nenhum número publicado se
  move, mas o E5 muda, e a lane **entra na cláusula de reinício** do contador. Custo zero em 2026-10-08: a [[A40.l113]] segue
  `in_progress`, logo o contador não começou.

## Critério de aceite

- Nenhuma métrica com operador de teto renderiza trilha que cresce com a piora.
- Prova por mutação: `taxa_endividamento` 45% contra `≤ 20%` **não** pode produzir trilha cheia.
- A polaridade chega ao front **como dado**, não por parsing da string renderizada.
- Baseline visual de print rebaselinada com ≥1 linha de teto, **olhada antes de commitar**.
- Concluído = PR mergeado em `main` com CI verde.

**Acrescido no co-design de 2026-10-08:**

- Concentração 50,00 e endividamento 20,00 saem **conformes**, pareados por comportamento a
  `RiskTrigger.conforme()`.
- Reserva 5,6 contra ≥ 6 meses mostra "Abaixo do alvo" (era "mínimo"; ver §O que foi entregue).
- Despesas não identificadas **nunca** mostram "Acima do limite": a situação é o tier do
  produtor, e a célula Alvo diz "Não afirmamos um alvo".
- Bruto 20,04 contra ≤ 20 é exibido com duas casas ("20,04%").
- Parecer congelado sem `comparador` não exibe barra nem status — zero `<progress>`.
- Trocar o operador da fixture para `>=` faz a barra aparecer (o gate discrimina a direção).
- Zero regex sobre string renderizada no TSX.

## O que foi entregue (2026-10-08)

Três PRs, na ordem que o co-design impôs (o enum antes do schema mudar; a doutrina antes do
veredito). Os critérios de aceite, um a um:

| Critério | Como fechou |
|---|---|
| Teto não renderiza trilha que cresce com a piora | a barra só existe quando o backend publica `progresso_pct`, que é nulo no teto por construção (`veredito_do_comparador`) e por contrato (validador de `Comparador`, `if/then` do JSON schema) |
| 45% contra `≤ 20%` não produz trilha cheia | o 1º commit do #2065 é o teste vermelho contra o componente antigo (`<progress value="100">`); a mesma regressão, reintroduzida numa sonda visual, reprova |
| A polaridade chega como dado | `comparador.operador`, cru do catálogo; zero regex no componente e na lib |
| Baseline de print com linha de teto, olhada | `parecer-metricas-print` (703×483, runner Linux), olhada antes do commit |
| 50,00 e 20,00 conformes, pareados ao `RiskTrigger` | #2048 — paridade por comportamento em volta do limiar |
| Reserva 5,6 contra ≥ 6 → "Abaixo do alvo" | estampador + componente; o veredito julga o piso conservador |
| Despesas nunca "Acima do limite" | órfã no catálogo + nível do produtor + componente + e2e |
| Parecer sem `comparador`: zero `<progress>` | read-path subtrativo + componente |

**O que a medição mudou no caminho:**

- **A baseline da seção não servia de gate.** Na sonda (run 37845587590), a regressão de
  origem reprovou o snapshot novo por 1.135 px e **passou** pelo `S_parecer-parcial` — a
  folga de 2,5% num recorte de ~1,4 Mpx engole uma barra inteira. A tolerância do snapshot
  novo (0.0003) foi medida nos dois extremos, como a do `cover`.
- **Um controle mentiu antes de dizer a verdade.** O primeiro run de controle sobre a
  `main` pura devolveu a baseline do `S_parecer-parcial` "idêntica" — era o arquivo
  comparado consigo mesmo, porque `--update-snapshots` só reescreve quando a comparação
  falha e a deriva da `main` cabia na folga. Com a baseline apagada (run 37846259546), a
  `main` real difere da commitada em ~19,8k px; a deste PR difere da `main` real só na
  faixa dos botões flutuantes.
- **Um furo de canal apareceu no co-design, não no enunciado:** o ramo sem catálogo do
  estampador preservava `target`/`valor_atual` que o LLM emitisse (`SkipJsonSchema` só
  esconde o campo). Fechado no #2065, com teste que parte do tool output.
- **`_SCHEMA_VERSION` não tinha gate**, e o `section_id` estampado da [[A40.l117]] havia
  entrado sem bump. O par (versão, campos estampados) agora é gateado por introspecção.

**Custo declarado:** no dogfood local, 4 pareceres da janela `schema_version='1.1'` perdem a
situação pelo read-path subtrativo (os 61 de 1.0 já não tinham alvo servido). Regenerar o
parecer a restaura; nada a recalcula sobre documento entregue.

**A revisão adversarial antes do merge achou 2 P1 e 4 P2 no meu código** — todos fechados no
#2065, cada um com teste que reprova sem o conserto:

- **P1 — em produção o veredito da concentração e da exposição cambial nunca saía.** O
  resolver do parecer aplica os `format_hints` do manifest: o observado chegava "62,50%"
  (`percent2`) e o comparador não tinha o que comparar. Todo teste montava o drill SEM
  hints — teste e código com a mesma crença sobre o formato do dado. O veredito passa a
  julgar o valor cru (`PlannerDrillDown.valor_bruto`), e os testes usam o drill de produção.
- **P1 — a reserva contradizia o canal de risco.** A tabela julgava a medida cheia
  (`cobertura_meses`); os pontos urgentes julgam o piso com titular identificado. Com alvo
  6, cobertura 6,4 e piso 5,2: "atingido" na tabela, "abaixo do mínimo de 6" no risco.
  Decisão do `financial-planner` — a regra geral da [[ADR-412]] §E3: veredito no extremo
  conservador, medida como intervalo ("5,2 a 6,4 meses"). E "mínimo" era falso para o alvo
  por perfil (6/12/18): o piso passou a dizer "alvo" (`product-designer`).
- **P2:** despesas regenerado sobre E5 antigo voltava a ter alvo ao lado do nível; o JSON
  schema recusava `comparador: null`; a leitura não reaplicava "teto sem progresso"; e
  limiar com vírgula, nível que não é string e valor inválido do modelo nos campos
  estampados derrubavam o stage depois de pagar o LLM (agora coerce, como a [[ADR-294]]).

## Deferido (2026-10-08)

**A natureza do limiar (alvo, mínimo ou limite) como dado por chave no catálogo.** Proposta
do `financial-planner` na 2ª rodada: a exposição cambial é um *mínimo*, a reserva um *alvo*.
O `product-designer` rejeitou copy por KPI como escopo que a coluna "Alvo" já entrega — e a
copy adotada ("alvo" no piso) é verdadeira para os três pisos, porque nomeia a coluna, não a
natureza. **Dono:** `financial-planner` + `product-designer`. **Retomada:** quando um piso
novo tornar "alvo" enganoso (ex.: um mínimo regulatório), ou quando a tabela precisar
distinguir mínimo de alvo na mesma linha.

## Achados adjacentes, fora desta lane

- **`S2` diverge da baseline visual desde 2026-08-14** (2970 → 2946 px). A `main` pura gera
  a mesma imagem que este trabalho (0 px), então não é desta lane. Sugerida ao dono como
  tarefa separada em 2026-10-08, **sem lane**: qualquer PR com label `visual` reprova nela
  até alguém atribuir e rebaselinar.
- **Os botões flutuantes da nav caem dentro do recorte das seções** (visível em
  `S_parecer-parcial`): o helper `snapshotSection` não usa o `floatingNavMask` que `cover`
  e `sumario-executivo` usam. Pré-existente; não tocado.
