---
id: A40.l92
type: lane
title: "A trilha de progresso ignora a polaridade do operador e enche conforme a métrica piora"
sprint: A40
plan: PLAN-deterministic-authority
status: in_progress
priority: P0
branch_slug: a40-l92-polaridade-do-comparador
owner: product-designer
depends_on: []
adrs:
  - "[[ADR-399]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
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
  Piso: "Mínimo atingido" / "Abaixo do mínimo", com a barra como codificação secundária.
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
2. **Doutrina do limiar** — predicado único `conforme_ao_limiar`; concentração `<=`;
   `KpiTarget` recusa operador estrito; despesas vira órfã por (b), com a base = soma das
   categorias ([[ADR-353]] D2); o tier de despesas julga o share que publica. Mergeado
   **antes** do veredito, por condição do `financial-planner`.
3. **O veredito** — `comparador` no artefato, no DTO e no TS; status na tabela; barra só no
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
- Reserva 5,6 contra ≥ 6 meses mostra "Abaixo do mínimo".
- Despesas não identificadas **nunca** mostram "Acima do limite": a situação é o tier do
  produtor, e a célula Alvo diz "Não afirmamos um alvo".
- Bruto 20,04 contra ≤ 20 é exibido com duas casas ("20,04%").
- Parecer congelado sem `comparador` não exibe barra nem status — zero `<progress>`.
- Trocar o operador da fixture para `>=` faz a barra aparecer (o gate discrimina a direção).
- Zero regex sobre string renderizada no TSX.
