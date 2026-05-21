---
id: TRACK-a17-l2-financeiro-pj
type: track
title: "Track A17 L2 — Financeiro PJ (C6 PJ, Stone, adquirentes): sub-schema + InformeQuery integration com ADR-236"
lane: "[[A17.l2]]"
sprint: A17
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: data-engineer
tags:
  - type/track
  - sprint/a17
  - status/ready
  - area/pipeline
  - area/methodology
  - methodology/cerbasi
---

# Track A17 L2 — Financeiro PJ

> **Lane:** [[A17.l2]] · **ADR canônica:** [[ADR-238]] D1-D5 · **Pré-requisito:** [[A17.l1]] mergeada (valida padrão) · **Sinergia obrigatória:** [[TRACK-a16-adr236-tributario-pj-cascata]] L2 — coordenação síncrona antes do PR (gate G3 de [[ADR-238]])
> · **Branch prefix:** `agent/a17-l2-financeiro-pj/*` · **Tamanho estimado:** ~4-5d eng em 3 PRs

## Briefing

L1 já estabeleceu padrão arquitetural completo (schema-base polimórfico, stage único, classifier extensível, `FiscalAnalyzer`, `InformeQuery` service). Esta lane **estende** o padrão para `tipo_informe="financeiro_pj"` — sem reinventar.

**Sinergia [[ADR-236]]:** a cascata fiscal PJ depende hoje exclusivamente de E1.6 via [`irpf_renda_tributavel.py`](../../../../pipeline/domain/services/tributario/irpf_renda_tributavel.py). Esta lane refatora para consumir `InformeQuery` (criado em L1 P4) — assim cascata funciona para workspace sem E1.6 mas com informes PJ.

## Decisões já fechadas (não reabrir)

- Tipo canônico `financeiro_pj` — [[ADR-238]] D1.
- Schema-base polimórfico — [[ADR-238]] D2 (sub-schema `informe_pj.schema.json` em P1).
- `tax_regime` no catálogo evita explodir entries PF/PJ — [[ADR-238]] D7.
- Pegadinhas Stone/Cielo (vendas brutas ≠ receita), retenção CSLL/PIS/COFINS só em Lucro Real — registradas no co-design `financial-planner` ([[ADR-238]] §Implementação).

## Plano (esqueleto — refinar no pickup)

- **P1** — `informe_pj.schema.json` (Pydantic + JSON) + prompt LLM + golden sintético.
- **P2** — Classifier `informe_financeiro_pj` (regex: "Comprovante de Rendimentos PJ", "CSLL retida", CNPJ adquirente).
- **P3** — Refatorar `irpf_renda_tributavel.py` para consumir `InformeQuery` em vez de E1.6 direto (sinergia [[ADR-236]] D2). Coordenar com agente A16 L2.

## Critério de aceite (lane completa)

Em [[A17.l2]] §Critério de aceite. Cobre C6 PJ + Stone PJ do batch.
