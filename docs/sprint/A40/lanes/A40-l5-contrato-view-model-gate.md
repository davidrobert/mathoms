---
id: A40.l5
type: lane
title: "Codegen do view-model + gate de contrato: mata a classe reader-lê-chave-que-ninguém-emite"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P1
branch_slug: a40-l5-contrato-view-model-gate
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p1
  - area/frontend
  - area/dx
---

# A40.l5 — `contrato-view-model-gate` (alavanca estrutural)

## Problema

Quatro achados independentes são **a mesma classe**: consumidor lê chave que o
payload não emite, **sem erro**, caindo em default/fallback silencioso.

| Achado | Consumidor lê | Payload emite |
|---|---|---|
| RV3-09 | `meses_cobertura` | `reserva_emergencia.cobertura_meses` |
| RV3-26 | `goals.trs_pct` | `goals.if_trs` (cai em default **hardcoded**) |
| RV3-12 | `d.valor` / `d.taxa` | `saldo_devedor` / `taxa_juros` |
| RV3-17 | `total_pontuais` | `total_pontuais_janela` existe e não é lido |

Dispersos, cada um recebe um fix pontual e **o quinto acontece na próxima
release**. `frontend/src/types/report-analysis.ts` é escrito à mão — é a exceção
que escapou ao [[ADR-076]], que já decidiu que codegen é a fonte de verdade para
contratos API↔UI.

RV3-26 tem um agravante que reabre item já fechado: o "aceite cumprido" do RV3-31
(duas taxas de retirada) foi verificado **contra a constante hardcoded**, não
contra o payload. Os números coincidem **por acidente** (ver §Decisões nº 7 do
sprint).

## Escopo

- `dev/codegen_report_analysis.py` (novo, padrão de `dev/codegen_report_layout.py`)
  gerando `frontend/src/generated/report-analysis.ts` a partir do DTO/schema E5.
- Substituir o `types/report-analysis.ts` manual pelo gerado.
- `dev/check_view_model_contract.py` (novo, pre-commit + CI) cruzando schema E5 ×
  tipos do frontend × readers Python.
- Corrigir os 4 readers como **consequência mecânica** do gate.
- **Vem antes** das lanes de correção individual de contrato ([[A40.l6]]).

## Critério de aceite

- KR-A: leituras órfãs conhecidas 5 → 0.
- **Gate de sincronia** no padrão `make update-openapi-snapshot`: regenerar e
  falhar se o commitado divergir.
- **Gate de consumo:** `tsc --noEmit` passa a falhar em leitura de campo não
  declarado — `d.valor` vira erro de compilação, e `frontend-checks` (que já roda
  `tsc --noEmit` em PR) bloqueia.
- Fixtures: **(1)** chave no schema sem consumidor ⇒ falha; **(2)** renomear
  `cobertura_meses`→`meses_cobertura` só no consumidor ⇒ falha (reproduz RV3-09
  exatamente); **(3)** allowlist com razão escrita ⇒ passa.
- RV3-31 re-verificado **contra o payload**, não contra a constante.

## Guarda anti-regressão

O gate **é** a guarda — única lane cujo entregável principal é impedir a classe
inteira, não corrigir instâncias. Removido o gate, a fixture (2) volta a verde e o
defeito retorna silencioso.
