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
