---
id: RULE-ordem-do-plano-por-irreversibilidade
type: domain-rule
concept: "Ordem dos itens do plano de ação por tier de irreversibilidade"
canonical_adr: "[[ADR-367]]"
enforcer_modules:
  - pipeline/domain/services/pontos_urgentes_analyzer.py
formula_ref: null
tags:
  - type/domain-rule
  - area/report
---

# RULE — Ordem do plano por irreversibilidade

**Conceito.** Os itens de `pontos_urgentes` são ordenados por **tier de
irreversibilidade**, constante por regra e indexado pelo `code` do item. Dentro do
mesmo tier, a ordem de escrita é preservada (sort estável).

| Tier | Critério | `code` |
| --- | --- | --- |
| **T0** | dano **irreversível** — não recuperável por disciplina | `seguro_vida` |
| **T1** | fragilidade — abaixo do piso, um choque força crédito caro | `reserva_insuficiente` |
| **T2** | alavancagem | `endividamento_alto` |
| **T3** | otimização | `rentabilidade_nao_medida` |

**Por quê.** Até 2026-08-07 a ordem era a sequência literal das linhas
`out.append` no analyzer — sequência de escrita, não critério. Dano irreversível
vem antes de dano recuperável por disciplina: é onde as metodologias de
planejamento patrimonial brasileiras convergem, e é o único eixo que não depende
de calibragem de threshold.

**Piso ≠ alvo (reserva).** O item `reserva_insuficiente` é **emitido** por
`cobertura < piso` (6 meses) e **graduado** pelo alvo do perfil: `Alta/Imediato`
abaixo do piso, `Média/Próximo trimestre` entre o piso e `meses_alvo`. Piso é
sobrevivência (irreversível); alvo é acumulação (reversível). Colapsar os dois
alertaria "Imediato" a toda família com 6–12 meses de cobertura, porque
`_perfil_por_pct` nunca retorna `clt_estavel` e o piso real de `meses_alvo` é
**12**. A copy nomeia o perfil, não só o número.

**T0 declarado e vazio.** O gatilho de carry-trade (custo do passivo > retorno
esperado) **não é encodado**: `endividamento.custo_medio_pct_aa` não tem produtor.
Tier que nunca dispara ensina que "não apareceu dívida cara" = "não há dívida
cara" — falso-negativo silencioso. Fica declarado como inerte por falta de
produtor.

**Doutrina canônica.** Decidida em
[ADR-367](../../adr/367-ordem-do-plano-por-irreversibilidade.md), que também
registra por que **não** há helper compartilhado com `suggestion_rules` (eixo de
severidade ≠ eixo de irreversibilidade; e `rule_reserva_insuficiente` está
dormente por `meses_cobertura` × `cobertura_meses`, RULE de outra lane).

**Enforcer.**
- [`pipeline/domain/services/pontos_urgentes_analyzer.py`](../../../pipeline/domain/services/pontos_urgentes_analyzer.py) —
  mapa `code → tier`, o `sorted` estável no `return` de `analyze`, e a gradação
  da reserva.

**Manutenção.** Regra nova = `code` novo + entrada no mapa de tier + linha nesta
nota. Sem entrada no mapa, o teste de cobertura do vocabulário falha.
