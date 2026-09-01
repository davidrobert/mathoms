---
id: A40.l113
type: lane
title: "A identidade de imóvel churna entre runs e os dois classificadores falham FECHADOS: residência e imóvel gerador são publicados como zero"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l113-identidade-de-imovel-churna-classificador-falha-fechado
owner: data-engineer
depends_on: []
adrs: ["[[ADR-215]]", "[[ADR-246]]", "[[ADR-394]]"]
tags: [type/lane, sprint/a40, status/open, priority/p0, area/pipeline, area/financial-planning]
---

# A40.l113 — `identidade-de-imovel-churna-classificador-falha-fechado`

> **Origem:** `RR9-01` (Cadeia A) da rodada unificada **U5**
> ([[REPORT-REVIEWS-active]] §r9). **CONFIRMADO** por medição A/B entre dois runs
> sobre **corpus documental idêntico**.

## O que está medido

Sem um documento novo entre os dois runs, **95 de 400** escalares numéricos do payload
publicado se moveram. No eixo desta lane:

| campo publicado | antes | depois |
|---|---|---|
| `patrimonio.bruto` | — | **−48,1%** |
| `patrimonio.residencia` | valor cheio | **zero** |
| `patrimonio.imoveis_geradores` | valor cheio | **zero** |
| `real_estate.valor_total_imoveis` | valor cheio | **zero** |
| `investimentos.total` | — | **−57,0%** |
| `goals.if_gap` | — | **+27,3%** |
| itens em `imoveis_consolidados` | 7 | **9** (3 pares duplicados) |
| itens com `property_id` | 5 de 7 | **1 de 9** |

O run terminou `completed`, com **2** avisos de pausa e **nenhum** sinal bloqueante. Nas
três rodadas unificadas anteriores o mesmo corpus produzia a coluna da esquerda — é
**regressão de 2 dias**, não dívida antiga.

## A cadeia, elo a elo

1. A descrição de um imóvel **ganhou um caractere duplicado** entre os runs — churn de
   extração LLM, a mesma classe que a [[A42.l15]] atacou em `investment_id`.
2. A canonicalização de endereço deriva da descrição ⇒ `endereco_canonical` e
   `property_id` colapsam **juntos**. Os 9 campos produzidos pela **consolidação** seguem
   9/9 — só os **dois do enricher** caem, o que prova que ele **rodou e falhou em
   resolver** (se não tivesse rodado, seriam 0 de 9, não 1).
3. `pipeline/domain/services/patrimonio_imovel_classifier.py:58-62` —
   `if pid and overrides_by_property_id.get(pid) == RESIDENCIA_PRINCIPAL: residencia += …`
   **else** `imoveis_outros += …`. Com `pid` nulo a residência **não recebe nada**.
4. `:76-78` — `cls = overrides.get(pid) if pid else None` ⇒ tudo cai no ramo
   não-gerador ⇒ `imoveis_geradores` zera.
5. `pipeline/domain/services/investimentos_classes_analyzer.py:266` —
   `isinstance(pid, str) and pid in residencia_ids` **falha ABERTO**: a residência entra em
   imóveis-investimento, `total_financeiro` encolhe e `nao_classificado_pct` **sobe sem o
   numerador crescer** (3,93 → 5,61 pp, com os ativos caindo de 3 para 1).
6. Sem `property_id` o dedup cross-IRPF ([[ADR-246]], passo 3b de `consolidate_baseline`)
   **vira no-op** ⇒ 3 pares duplicados sobrevivem ao patrimônio publicado.

## Por que é P0

O produto publica que a família **não tem casa própria** e **não tem imóvel de renda**, e
não emite aviso: nenhum dos dois classificadores distingue *"não é residência"* de *"não
sei qual é"*. Todo consumidor a jusante herda o zero — meta de IF, alocação alvo, próximo
aporte, cap rate, concentração.

## O eixo do defeito, e o que NÃO consertá-lo

O churn de descrição é sintoma; a doença é **identidade derivada de free-text**. Duas
correções distintas, e a lane precisa das duas:

- **Falhar fechado é errado nos dois classificadores.** `pid` ausente não é
  *"não é residência"* — é **desconhecido**, e o balde do desconhecido tem de existir e
  ser publicado como supressão declarada, no espírito da [[ADR-431]] (zero publicado é
  afirmação sobre o patrimônio da pessoa).
- **A âncora de identidade tem de sair da prosa.** A [[A42.l15]] resolveu isso para
  investimento ancorando em `cnpj_emissor` — campo estruturado — e o efeito é medido: no
  mesmo run, `proprietario` passou a vir preenchido em 55 de 58 e a população de
  investimentos estabilizou com D2=0 e D3=0. **A população de imóveis não recebeu
  tratamento equivalente.**

## Medição de 1 comando que refuta

Re-rodar `consolidate_baseline` sobre os mesmos E1.5a com a descrição churnada revertida à
forma do run anterior. Se `property_id` voltar a 5+ e a população cair a 7, a cadeia está
confirmada ponta a ponta e o eixo é a canonicalização.

## Critério de aceite

1. `property_id` nulo **não** cai no balde de "não é residência" nem no de "não gerador":
   existe terceiro estado, publicado como supressão com motivo.
2. Gate que reprova quando a **contagem** de `property_id` resolvidos cai entre dois runs
   sobre o mesmo corpus — o sinal que este run tinha e ninguém leu.
3. A identidade de imóvel ancora em campo **estruturado** (não na descrição), com o
   contrafactual medido: reverter a âncora reproduz o colapso.
4. Regressão: fixture com `property_id` nulo em 8 de 9 itens; asserção de que `residencia`
   **não** é zero por ausência de id.

## Medição de 2026-09-01 — a cadeia acima está **parcialmente refutada**

> Rodada de medição sobre o artefato `consolidate_baseline` do próprio run `40d1af2a`
> (o do `U5`), executando os produtores reais contra o payload real. O publicado foi
> **reproduzido ao centavo**: `split_imoveis_with_overrides` devolve `(0.0, 701170.57)`,
> idêntico a `patrimonio.residencia` / `patrimonio.imoveis_investimento` publicados.

### O que se confirma

- `property_id` resolvido em **1 de 9** itens de `imoveis_consolidados` ✅
- os dois classificadores mandam `pid` nulo para o `else` (`:58-62`, `:76-78`) ✅
- `investimentos_classes_analyzer.py:266` falha **aberto** ✅
- 3 pares duplicados sobrevivem ao publicado ✅
- o balde do desconhecido não existe e o zero é publicado sem aviso ✅

### O que se refuta

**1. O caractere duplicado não é a causa.** A descrição churnada é a do item `EDIFICIOO` (era `EDIFICIO`). Mas **8** itens falharam a canonicalização, e o motivo é
estrutural, não churn: `canonicalize` exige via+número, e as descrições de IRPF em que ela
falha são **nome de condomínio** (`CONDOMINIO <nome> - APTO <n>`) ou **narrativa
de compra** (`COMPRA E VENDA DE CASA - ADQUIRIDO DE CPF … EM <data>`). Nenhuma delas
canonicaliza com ou sem o typo. O único item que resolveu — do tipo `Rua Exemplo, 100` —
é o único que **tem via+número**. Reverter a descrição, como a §"Medição de 1 comando"
prescrevia, **não** faria `property_id` voltar a 5+.

**2. O eixo do churn é o `codigo_rfb`, não a descrição.** Os 3 pares duplicados diferem
**só** na grafia do código RFB: `01-11` na declaração de 2025 contra `11` nas de 2024/2023
(idem `01-12`/`12`). Como `codigo_rfb` é componente da `PropertyLookupKey`, a mesma
propriedade não casa consigo mesma entre anos.

**3. `patrimonio.residencia = 0` NÃO é causado por `pid` nulo.** A residência é o item que
**tem** `property_id` (`20f938a2…`) e **tem** override `residencia_principal` gravado em
`workspace_property_overrides`. Ela sai zero porque o **valor** projeta em zero:

`anos_base_por_membro` resolve o ano-base do membro como `max()` sobre **todas** as classes
de ativo juntas. O titular tem 3 posições de investimento datadas de **2026** (CDB,
cofrinho e previdência — saldo bancário corrente, dado legítimo); seus imóveis, veículos e
dívidas param em 2025. `max` = 2026, e esse ano único é aplicado a cada lista;
`_resolve_item_valor_e_ano` faz `valores_31_12.get("2026")`, não acha, e cai em
`safe_float(item.get("valor", 0))` → **0,00**.

É o **mesmo defeito** que o comentário em `patrimonio_resolvers.py:348-351` diz ter
corrigido ao mover o eixo de *domicílio* para *membro* — um nível abaixo: de membro para
**classe de ativo**.

### Contrafactuais medidos

| | ano-base atual (`max` global = 2026) | ano por classe (imóveis do titular = 2025) |
|---|---|---|
| `residencia` | **0,00** | **996.821,46** |
| cat_2 (outros imóveis) | 701.170,57 | 1.343.876,81 |
| `imoveis_geradores` | **0,00** | **0,00** ← não se move |
| `total_dividas` (titular) | **0,00** | **230.459,13** |

`imoveis_geradores` **não se move** com o ano corrigido: os 4 imóveis `locado` estão sem
`property_id` neste run. **Os dois defeitos são necessários** — nenhum sozinho fecha o
eixo da lane.

### Alcance maior que a lane: a [[A40.l114]] tem o mesmo dono

`patrimonio.veiculos` (0,00) e `endividamento.total_dividas` (0,00 com 4 financiamentos
listados, logo `liquido == bruto`) caem pela **mesma linha**. Isso refuta duas afirmações:

- o §r9 de [[REPORT-REVIEWS-active]] declara `RR9-01` e `RR9-02` **"duas cadeias
  independentes"**. Elas compartilham a raiz.
- a [[A40.l114]] atribui o zero da dívida ao `ano_referencia` cru do LLM. **Contrafactual:**
  passar `1999` — ou a string `zzz` — como `ano_domicilio` produz o **mesmo** resultado
  (`('2026','2023')`), porque `anos_base_por_membro` só consulta `ano_domicilio` quando o
  membro **não tem ano nenhum**. O titular tem. O critério 1 da l114 (reconciliar o ano do
  LLM contra os documentos) **não moveria** `total_dividas` neste corpus. E o 2026 tem
  documento atrás: são as 3 posições de investimento.
