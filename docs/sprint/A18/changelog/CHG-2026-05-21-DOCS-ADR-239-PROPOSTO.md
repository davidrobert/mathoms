---
id: CHG-2026-05-21-DOCS-ADR-239-PROPOSTO
type: changelog-entry
date: "2026-05-21"
sprint: A18
lane: "[[A18.l1]]"
adrs: ["[[ADR-239]]"]
summary: |
  docs(adr-239): Proposto — Comprovantes de Bem (CRLV) + Apólices polimórficas
  + FIPE refresh assíncrono. Sprint A18 reservada com 3 lanes coordenadas
  (L1 CRLV gateway, L2 apólice combinada V1, L3 BrasilAPI cron anual).
tags:
  - type/changelog-entry
  - sprint/a18
  - status/proposto
  - area/pipeline
  - area/persistence
  - area/methodology
---

# docs(adr-239): Proposto — Comprovantes de Bem + Apólices + FIPE (Sprint A18)

PR docs-only que registra [[ADR-239]] como `Proposto` e reserva Sprint A18 com 3 lanes coordenadas. Nenhum código de runtime ainda.

## Origem

Sessão dogfood 2026-05-21 com **6 PDFs de exemplo**: 3 CRLV-e (moto XYZ9A87, moto ABC1D23, carro ABC1234) + 3 apólices de seguro (Tokio Marine Moto, Porto Moto, Porto Proteção Combinada — multi-bem). Todos caem em `.other` silencioso hoje.

Owner explicitamente questionou acoplamento `veiculo.apolice_id` — co-design `data-engineer` + `financial-planner` confirmou padrão **inverso**: `apolice.bens_segurados[]` polimórfico com FK opcional para entidade canônica. Escala para vida/saúde/PJ V2.

## Decisões canônicas (do co-design)

| # | Tema | Decisão |
|---|---|---|
| D1 | Identidade canônica veículo | Tabela `vehicles` com `(workspace_id, placa, renavam)` imutável tipo [[ADR-225]] |
| D2 | Schema apólice | Discriminated Union em `bens_segurados[]` + `coberturas[]`; antecipa V2 (vida/saúde/AP) |
| D3 | FK polimórfica | Opcional + reconciliação assíncrona idempotente |
| D4 | Dedupe | Chave forte placa; colisão placa↔renavam = `needs_review`; FIPE só enriquecimento |
| D5 | FIPE | BrasilAPI open-source; lookup **sempre assíncrono** via Celery; cron anual Janeiro |
| D6 | LLM | Cascata Haiku→Sonnet com gate (multi-bem ou confidence<0.7) |
| D7 | Histórico apólices | Imutável temporal por vigência; retenção 5 anos pós-vigência |
| D8 | Stage | Único `extract_comprovantes_bens` com despacho por `tipo_comprovante` |
| D9 | Catálogo | Migration: `insurance_carrier`, `insurance_broker`, `reference_data` categories |

## O que entra neste PR

- [docs/adr/239-comprovantes-bens-apolices-fipe.md](../../../adr/239-comprovantes-bens-apolices-fipe.md) — ADR canônica
- `docs/sprint/A18/_README.md` — MOC da sprint com 3 lanes
- `docs/sprint/A18/lanes/A18-l{1,2,3}-*.md` — 3 lanes
- `docs/sprint/A18/tracks/a18-l1-crlv-veiculos.md` — track operacional completo (5 fases P1-P5)
- `docs/sprint/A18/tracks/a18-l{2,3}-*.md` — esqueletos `ready`
- Este changelog entry

## Próximo passo

Lane [[A18.l1]] (`open`) pickup-ready após este PR mergear. PRs de implementação começam quando agente puxar L1.

A18 conecta com Sprint A19 ([[ADR-240]]) — card S_PROTECAO depende de A18 inteira em `main`.
