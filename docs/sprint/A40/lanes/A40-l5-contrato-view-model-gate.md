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

## Escopo herdado da [[A40.l4]]

A l4 **shipou** (`6c5d9814`, #1139) e roteou 5 residuais medidos para esta lane,
na coluna Dono de sua §Residual medido. Até este registro (2026-08-05) o handoff
existia no emissor e no §Inventário do [[A40]] —
`rg -n 'autonomia_financeira|ADR-148|renda_passiva_estimada' docs/sprint/A40/`
não batia neste arquivo. Handoff só existe quando a lane de destino o registra
(o par l3→l15 já pratica o padrão):

| Herdado | O que foi medido na l4 |
|---|---|
| **`s1` publica "residência própria de R$ 0,00"** | Mesma classe do "R$ 0,00 em campo fiscal" (lê-se como "sua casa não vale nada"). No `s4` a parcela zerada foi suprimida na l4; no `s1` não, porque o `s1` estava fora da lista fechada. **Ver §Pendências de decisão nº 6 do [[A40]]:** é classe zero-como-valor, que é a RV3-27 da [[A40.l6]] — o dono decide se fica aqui ou move |
| **Sufixo de changelog da [[ADR-148]] não renderiza em seção nenhuma** | `get_report_data.py:78` usa `SnapshotChangelogConfig()` default, cujo `sections_to_compare` (`M_PL`, `M_TAXA_POUPANCA`, `M_RESERVA_MESES`, `M_AUVP_DESVIO`) não contém nenhum id de seção do layout, e o casamento é por `section_id`. A composição decidida na §D10 é contrato, não preservação de comportamento visível |
| **C11 — `ratios.autonomia_financeira_meses` = 16,72 sem consumidor** | Runway canônico ([[ADR-335]]) calculado e nunca renderizado; o alias colide de nome com cobertura da reserva. É campo do view-model, não de narrativa — nenhum dos 7 destinos entregues o cita |
| **C36 — blocos que não movem decisão** | A parte narrativa (duplicação no empty state da S9) foi corrigida na l4. O que sobra são **cards**: orçamento 44m, premissas 10/10 indisponíveis, checklist de sucessão todo negativo |
| **`renda_passiva_estimada_4pct` cristaliza "4" no nome do campo** | O SWR 4% e o yield-alvo 5% são conceitos distintos sob [[ADR-191]] §Emenda FP-03 e **não se harmonizam**. Um número no nome do campo trava a taxa no contrato — é exatamente o tipo de acoplamento que o codegen desta lane deveria expor |

Os 5 entram no numerador de "leituras órfãs" **se e somente se** o gate os
classificar como tal. `s1` e `renda_passiva_estimada_4pct` provavelmente não são
órfãos (têm consumidor); são defeitos de **contrato**, que é o objeto desta lane.
Não presuma que "5 → 0" já os cobre.

## Guarda anti-regressão

O gate **é** a guarda — única lane cujo entregável principal é impedir a classe
inteira, não corrigir instâncias. Removido o gate, a fixture (2) volta a verde e o
defeito retorna silencioso.
