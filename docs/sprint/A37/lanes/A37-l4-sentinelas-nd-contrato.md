---
id: A37.l4
type: lane
title: "Sentinela \"N/D\" tratada como dado presente: guardrail suprime field_request legítimo + contrato sub-especificado"
sprint: A37
status: open
priority: P1
branch_slug: a37-l4-sentinelas-nd-contrato
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/open
  - priority/p1
  - area/llm
  - area/dados
---

# A37.l4 — `sentinelas-nd-contrato` (CTO-02 + DE-07)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **Guardrail (CTO-02):** `_classify_campo`
   (`backend/app/services/parecer_pos_llm_guardrails.py:119-120`) marca como
   `spurious` qualquer field_request cujo path resolve para valor não-None.
   A string sentinela `"N/D"` em `endividamento.dividas[0].taxa_juros` fez um
   pedido **legítimo** do LLM (o próprio motivo dizia "ausente (N/D)") ser
   removido de `campos_faltantes_pediria_se_iterasse` — suprime sinal do
   learning loop de expansão do manifest e emite telemetria falsa
   (`field_requests_spurious=1`).
2. **Contrato (DE-07):** no schema E5, `properties.endividamento` é
   `{"type": "object"}` opaco (`config/schemas/e5_analysis.schema.json`) —
   `"N/D"` string e `parcela_mensal=0.0` (sentinela ambígua: zero real vs
   desconhecido) são válidos. O produtor emite string em campo numérico.

## Escopo

- `_classify_campo` trata sentinelas de ausência como ausentes — preferir
  **normalizar no boundary** (produtor E5 emite `null` em vez de `"N/D"`/`0.0`
  sentinela) e, como defesa em profundidade, o guardrail reconhece a lista de
  sentinelas remanescentes do vocabulário real do E5.
- Tipar `endividamento.dividas[]` no schema E5 (`taxa_juros: ["number","null"]`,
  `parcela_mensal: ["number","null"]`); frontend já renderiza "—" para ausente
  (`EndividamentoCard.tsx` lê campo numérico).
- Varredura curta por outras sentinelas string em campos numéricos do E5
  (grep `"N/D"` nos produtores) — corrigir na mesma janela ou registrar.

**Coordenação com [[A37.l1]]:** a normalização de sentinelas no boundary deve aterrissar **antes** (ou junto) do PR que expande o contexto do parecer — senão a seção restaurada pela l1 renderiza `"N/D"` como dado presente (o distiller só pula `None`).

## Critério de aceite

- Teste de regressão (antes do fix): field_request para campo com `"N/D"` →
  hoje `spurious`; depois → mantido como genuíno no output e na telemetria.
- Schema: payload com `taxa_juros: "N/D"` **falha** validação (unit no
  validate_dict); produtor emite `null` e payload real valida.
- Parecer de run fresco lista o pedido de taxa de juros em
  `campos_faltantes_pediria_se_iterasse` (é genuinamente indisponível no IRPF).

## Risco

Baixo/Médio: mudar shape de `taxa_juros` (string→null) pode tocar consumidor
tipado — verificar `frontend/src/types` e o distiller do parecer no mesmo PR.
