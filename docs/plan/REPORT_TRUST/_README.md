---
id: PLAN-report-trust
type: plan
title: Report Trust — o relatório não pode afirmar precisão que os dados não sustentam
status: in_progress
created_at: 2026-07-03
last_review: 2026-07-03
sprint_origem: A28
sprint_atual: A28
sprints_envolvidas: [A28]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-191]]"
  - "[[ADR-240]]"
  - "[[ADR-186]]"
tags:
  - type/plan
  - status/in-progress
  - area/e5
  - area/pipeline
  - area/frontend
  - area/llm
---

# Report Trust — o relatório não pode afirmar precisão que os dados não sustentam

> **Origem:** revisão completa do relatório dogfood `72883bde` (2026-07-03) —
> parecer do orquestrador + `financial-planner` + `product-designer`, seguido de
> co-design de sprint com `product-manager` + `information-architect` +
> `data-engineer` + `prompt-engineer`. Owner (CEO) priorizou explicitamente os
> P0 de fórmula/consistência e pediu sprint corrente.

## Tese

O relatório dogfood afirma completude e precisão que os dados não sustentam:
duas violações de fórmula canônica ([FORMULAS.md](../../reference/FORMULAS.md)
§Reserva · [[ADR-191]]), duas contradições cross-seção (PGBL com recomendações
opostas; duas bases de mensalização 2× diferentes sem rótulo), 23% das despesas
sem categoria, dados extraídos que não fluem (3 apólices presas no
`extract_comprovantes_bens` com balde E4 `seguros` vazio e `compute_protecao`
de [[ADR-240]] dead code), e apresentação sem sinalização agregada de qualidade.

**Três recomendações do relatório atual, se seguidas, PIORAM a situação do
cliente:** desacelerar aporte por TRS fictícia de 22,63% a.a. (dividendos da
própria PJ no numerador, só imóveis no denominador); desmobilizar carteira
produtiva por reserva "Excessiva" de 31,6 meses (numerador = todo o investível);
cortar gasto errado por rótulo Cerbasi "Gastador" (97,5% presente) sobre despesa
opaca — no mesmo relatório que celebra 28% de poupança. Para um produto
fiduciário em dogfood com critério de saída "refinar até perfeito antes de
abrir", isso bloqueia a saída do dogfood.

## Frentes

1. **Conformidade de fórmula (E5)** — reserva, TRS, PGBL, base de mensalização.
   Duas são bug contra contrato escrito (FORMULAS.md / ADR-191); duas exigem
   ADR `Proposto` (política de base temporal; regra de ano-base PGBL).
2. **Loop de dados (pipeline)** — categorização (`nao_identificado` 23% → <5%
   via Learning Loop [[ADR-186]]), proteção patrimonial (wire apólices →
   `compute_protecao`, ativa [[ADR-240]]), dedup da lista de imóveis excluídos
   ([[ADR-246]] na projeção), higiene de ingestão (períodos 1899/2100, banco
   vazio em keys E3).
3. **Apresentação honesta (frontend + E6)** — banner agregado de qualidade de
   dados, ressalva de fallback no Monte Carlo, formatador de âncoras por tipo,
   guardrails pós-LLM do parecer (confiança sob premissa fallback; filtro
   3-vias de `campos_faltantes`).

## Sinergia com [[PLAN-data-lineage]] (A26 `paused`)

Cada iteração desta frente re-gera o parecer E6 → produz as **≥20 gerações
reais** que destravam [[A26.l2]] (flip strict do `evidencia_path`) e exercita o
override v2 ([[A26.l4]]). Corrigir os inputs (TRS, reserva, mensalização)
**antes** de flipar o strict evita travar pareceres em massa por dados ruins.
A A26 retoma quando os gates de tráfego fecharem — esta frente é a máquina que
gera esse tráfego.

## Janelas

- **A28** ([sprint/A28/_README.md](../../sprint/A28/_README.md)) — 11 lanes em
  3 ondas: Onda 0 (fórmula, Must) → Onda 1 (dados) ∥ Onda 2 (apresentação,
  com trava de merge pós-Onda 0). Detalhe de corte e gates no MOC da sprint.
- Follow-ups candidatos a A29+ (fora do escopo A28): poda estrutural de
  `PropertyIdentity` órfãs (migration + backfill), saída do dogfood
  (gate de abertura), fuzzy dedup de investimentos cross-IRPF.

## Critério de done do plano

Re-run dogfood completo sem: violação de fórmula canônica, contradição
cross-seção, categoria dominante sem rótulo, dado extraído ausente do relatório,
projeção precisa sobre premissa fallback sem ressalva — verificado por goldens
+ testes de invariante + teste de honestidade de UX (ver KRs da A28).
