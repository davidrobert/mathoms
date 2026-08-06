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
| ~~**`s1` publica "residência própria de R$ 0,00"**~~ | **Movido para [[A40.l6]]** em 2026-08-05 (decisão do dono, §Pendência nº 6 "Relacionado" do [[A40]]; registrado em [[ADR-356]] §Emenda 2026-08-05): é classe zero-como-valor (RV3-27), o arquivo é `summaries_narrator.py` (pipeline) e a regra já está decidida na §D7 da ADR-356 — não é leitura órfã nem contrato de frontend |
| **Sufixo de changelog da [[ADR-148]] não renderiza em seção nenhuma** | `get_report_data.py:78` usa `SnapshotChangelogConfig()` default, cujo `sections_to_compare` (`M_PL`, `M_TAXA_POUPANCA`, `M_RESERVA_MESES`, `M_AUVP_DESVIO`) não contém nenhum id de seção do layout, e o casamento é por `section_id`. A composição decidida na §D10 é contrato, não preservação de comportamento visível |
| **C11 — `ratios.autonomia_financeira_meses` = 16,72 sem consumidor** | Runway canônico ([[ADR-335]]) calculado e nunca renderizado; o alias colide de nome com cobertura da reserva. É campo do view-model, não de narrativa — nenhum dos 7 destinos entregues o cita |
| **C36 — blocos que não movem decisão** | A parte narrativa (duplicação no empty state da S9) foi corrigida na l4. O que sobra são **cards**: orçamento 44m, premissas 10/10 indisponíveis, checklist de sucessão todo negativo |
| **`renda_passiva_estimada_4pct` cristaliza "4" no nome do campo** | O SWR 4% e o yield-alvo 5% são conceitos distintos sob [[ADR-191]] §Emenda FP-03 e **não se harmonizam**. Um número no nome do campo trava a taxa no contrato — é exatamente o tipo de acoplamento que o codegen desta lane deveria expor |

Os 4 restantes entram no numerador de "leituras órfãs" **se e somente se** o gate
os classificar como tal (o do changelog foi roteado para
[[PLAN-snapshot-changelog-v3]] §Residual W3 em 2026-08-05 — era resíduo daquele
plano). `renda_passiva_estimada_4pct` provavelmente não é órfão (tem consumidor);
é defeito de **contrato**, que é o objeto desta lane. Não presuma que "5 → 0" já
os cobre.

## Escopo herdado da [[A40.l10]] — o gate cross-stack não dispara

Registrado aqui em 2026-08-05 **pelo destino**, na convenção que esta lane já
declara acima. A l10 mediu, ao regravar a fixture de entrega:

| Herdado | O que foi medido na l10 |
|---|---|
| **Mudança na fixture compartilhada Py↔TS não dispara o job que a consome** | `frontend/tests/components/report/sectionSummaryDelivery.test.tsx` lê `../../../../tests/fixtures/narrativas/e5n_delivery.json`, **fora** de `frontend/`. O filtro `filter.frontend` (`.github/workflows/ci.yml`) casa `frontend/**`, `design-tokens/**`, `config/report_layout.yaml` e o workflow — **não** `tests/fixtures/narrativas/**`. Medido: *Frontend checks* saiu `skipping` num PR que regravou a fixture 2×. Quebrar o contrato cross-stack deixaria o CI **verde** |

É a mesma classe desta lane — par produtor↔consumidor existente cujo gate não
fecha —, só que na camada de **disparo** em vez da de contrato. O `tsc --noEmit`
que a l5 quer usar como gate de consumo tem o mesmo problema: só roda quando o
filtro deixa. **Não corrigido na l10 por custo**: acrescentar o path faz
*Frontend checks* rodar em todo diff de fixture do pipeline, e a A40 tem histórico
de orçamento de Actions estourado por contagem de jobs — é decisão com gatilho
`sre-devops`, não carona de PR de narrativa.

## Guarda anti-regressão

O gate **é** a guarda — única lane cujo entregável principal é impedir a classe
inteira, não corrigir instâncias. Removido o gate, a fixture (2) volta a verde e o
defeito retorna silencioso.
