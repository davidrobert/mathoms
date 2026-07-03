---
id: PLAN-tributario-pj
type: plan
title: "Tributário PJ — Cascata Fiscal canônica (modelo de domínio + narrator correto)"
status: done
sprint_origem: A16
sprint_atual: A16
sprints_envolvidas: [A16]
created_at: "2026-05-20"
last_review: "2026-07-03"
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-236]]"
tags:
  - type/plan
  - status/draft
  - area/methodology
  - area/pipeline
  - area/persistence
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - sprint/a16
---

# Tributário PJ — Cascata Fiscal canônica

> Plano multi-fase para substituir o card S8 "Tributário PJ — Cascata Fiscal" hoje renderizado com texto canned conceitualmente errado por uma cascata real, alimentada por modelo de domínio expandido, narrator condicionado a regime, e card UI com decomposição em camadas. Decisão arquitetural canônica em [[ADR-236]].

## Origem

Sessão 2026-05-20 — usuário (CEO, workspace dogfood) abriu `/reports/...` e identificou no card S8 "Tributário PJ — Cascata Fiscal":

```
Carga tributária da PJ de David Robert: receita anualizada de
R$ 189,1k, enquadrada no  (alíquota efetiva 6%).

DAS estimado em R$ 945,58/mês (R$ 11,3k/ano). Lucro presumido (32%)
define base tributável de R$ 60,5k para cálculo do PGBL (dedução
de até 12%). Contador  em funcionamento. Avaliação de holding
patrimonial pendente para .
```

Investigação revelou **três problemas em três níveis**:

### N1 — Renderização (strings vazias)

Template em `pipeline/domain/services/narrativas/charts_narrator.py::impostos_pj` (linha ~255) referencia `{M['regime_obs']}`, `{M['contador_nome']}`, `{M['holding_prazo']}` — todos defaultam para `""` no render. Resultado: lacunas literais no copy.

### N2 — Wiring (`tributario` nunca chega ao bundle)

Sprint A10.7 ([[A10.7]] / migration `b1a2c3d4e5f7`) criou `Workspace.business_profile_json` com `{contador, regime, holding_prazo_meses}` e modelo Pydantic `BusinessProfile`. Mas `backend/app/services/pipeline_adapter.py::build_goals_payload_sync` (linhas 293-316) nunca lê esse campo nem injeta chave `"tributario"` no `GoalsBundle`.

Resultado: `trib_cfg = goals_cfg.get("tributario", {})` em `scripts/e5n_narrativas.py:338` sempre devolve `{}`, todos os campos caem no default `""`. **Dead-data wiring** — a migração A10.7 deixou a outra ponta nunca conectada.

Além disso, os nomes de campo não casam mesmo se propagado:

| Narrator espera | `BusinessProfile` tem |
|---|---|
| `contador_nome` | `contador` |
| `contador_mensal` | — |
| `contador_canal_pagamento` | — |
| `regime_obs` (string livre) | `regime` (enum) |
| `holding_avaliacao_prazo` (string ano) | `holding_prazo_meses` (int) |

### N3 — Imprecisão conceitual (independe de dados)

Mesmo com tudo preenchido, o texto canned está **errado pelo lado do planejamento financeiro**, conforme co-design `financial-planner` 2026-05-20:

1. **Mistura de regimes incompatíveis** — "DAS" só existe em Simples Nacional/MEI; "Lucro presumido (32%)" é fator de presunção IRPJ/CSLL do regime *Lucro Presumido*. PJ não está nos dois. O texto cola um sobre o outro.

2. **Base PGBL está errada** — Limite 12% PGBL incide sobre **renda tributável da pessoa física** (pró-labore + aluguéis + ganhos tributáveis), **não** sobre `receita_pj × 32%`. Lucros distribuídos pela PJ ao sócio são **isentos** e **não contam** para a base. Se sócio tira pró-labore mínimo + distribui resto como lucros, base PGBL pode ser ~R$ 18k/ano independente da receita PJ ser R$ 500k. Declaração simplificada **anula** PGBL (desconto simplificado substitui deduções legais). Referência: Perini "Viver de Renda" cap. previdência; AUVP módulo previdência (PGBL só faz sentido em completa + IR marginal ≥ 22,5%).

3. **"Cascata Fiscal" não entrega o que o título promete** — Sem decomposição em camadas (receita → tributos federais → ISS → pró-labore tributável → lucros isentos → carga total %), sem fator-R, sem comparativo Simples vs Presumido (que é a decisão real do consultor).

Co-design 2026-05-20 com `financial-planner` produziu validação metodológica completa (5 perguntas: cascata canônica, base PGBL, inputs mínimos, decisões/folclore, limites CRC). Síntese consumida em [[ADR-236]] §Decisão e §Alternativas.

## Objetivo

Após este plano, o card S8 "Tributário PJ — Cascata Fiscal" do relatório premium:

- **Decompõe em camadas reais** — receita bruta PJ → tributos federais (DAS no Simples; PIS+COFINS+IRPJ+CSLL no Presumido) → ISS (municipal) → lucro contábil PJ → pró-labore + INSS patronal + IRRF → lucros distribuídos isentos → renda PF total.
- **Calcula fator-R real** quando regime=simples — folha + pró-labore / receita 12m, com badge "Anexo III" / "Anexo V" + break-even explícito ("subir folha em R$ X migra de V para III").
- **Mostra base PGBL correta** — soma de pró-labore tributável + outras rendas tributáveis PF (de [[ADR-157]] E1.6), com flag "declaração simplificada anula PGBL".
- **Sinaliza decisões parametrizadas** (não pareceres) — gatilhos com break-even, copy "considere avaliar" / "sinal de atenção" + disclaimer "valores estimados — confirme com seu contador".
- **Sobrevive a workspace incompleto** — sem `business_profile_json` preenchido, card mostra estado "perfil tributário pendente" + CTA pro consultor preencher, **não** inventa "Lucro presumido (32%)".

## Não-objetivos (MVP V1)

- **Cálculo de imposto devido específico** — escolha de regime para o ano-calendário, enquadramento CNAE, conferência de DAS efetivo vs nominal. Linha CRC: requer contador. Mathoms fica em "planejamento patrimonial" (eficiência da estrutura existente, gatilhos de revisão), não em "execução fiscal".
- **Holding patrimonial — gatilhos sofisticados** — V1 mostra "avaliação pendente para X meses" se preenchido + 1 gatilho simples (>3 imóveis alugados). Gatilhos completos (ITCMD estadual, sucessão multi-herdeiro, PJ-aluguel) ficam em V2.
- **Suporte a múltiplas PJs por workspace** — V1 assume 1 PJ por workspace (caso ICP atual). Multi-PJ vira ADR follow-up.
- **Reforma tributária / PEC dividendos** — V1 modela cenário 2026 (lucros isentos). Quando reforma aprovar, abrir ADR de schema evolution.
- **Lucro Real** — V1 cobre Simples + Presumido + MEI (cobrindo >95% da ICP atual). Lucro Real entra em V2.

## Status executivo

> Atualizado 2026-07-03 (audit-vault r6) — o bloco anterior estava congelado
> em 2026-05-20 e declarava o plano como não-iniciado.

- **Co-design `financial-planner`** ✅ 2026-05-20 (síntese das 5 perguntas em [[ADR-236]])
- **ADR-236** ✅ `Decidido` (2026-05-21)
- **P1-P6** ✅ **entregues na Sprint A16.L2** (PRs #390-#398, 2026-05-21):
  modelo de domínio + calculator + serialização + triggers em
  `pipeline/domain/services/tributario/`, `CascataFiscalCard` no relatório,
  telemetria `mathoms.tributario.*` e FAQ do produto
  ([FAQ_cascata_fiscal_pj](../../reference/FAQ_cascata_fiscal_pj.md)).

Track operacional consumido: [[TRACK-a16-adr236-tributario-pj-cascata]].
Pendências V2 (Lucro Real, reforma tributária/PEC dividendos) seguem em
§Fora de escopo — abrir ADR de schema evolution quando o gatilho chegar.

## Decisões arquiteturais (resumo executivo)

Detalhe completo em [[ADR-236]]. Highlights:

1. **Rules-as-code (ADR-143)** — fórmula da cascata por regime vive em `pipeline/domain/services/tributario/`, ADR-236 é fonte canônica. Sem regra em YAML/JSON.
2. **Base PGBL** = soma de rendimentos tributáveis PF da ficha IRPF (pró-labore + aluguéis + outras tributáveis), **não** receita PJ × 32%. Confirmado por FP cap. previdência.
3. **Inputs derivados (E3/E4/E1.6) ≫ inputs declarados** — `pro_labore_mensal`, `lucros_distribuidos_mensal`, `folha_pj_mensal`, `outras_rendas_tributaveis_pf_anual` derivam de transações reconciliadas + IRPF parsed. Só `anexo_simples`, `iss_aliquota_pct`, `cnae_principal`, `tipo_declaracao_ir` são declarados em `BusinessProfile`.
4. **Fator-R calculado, não declarado** — narrator computa `(folha + pró-labore) / receita_12m`, mostra valor + faixa Anexo III/V + break-even.
5. **Decision triggers parametrizados** — gatilhos com break-even explícito ("subir folha em R$ X custa Y INSS, economiza Z DAS, payback W meses"). Sem "recomendamos".
6. **Hot-fix paralelo descartado** — usuário (sessão 2026-05-20) optou pela solução completa sem encurtar/esconder o card no meio-tempo. Card permanece errado em produção até P4 (~6d eng de hot-fix).

## Faseamento

Total estimado: ~9d eng em ~2 semanas calendário. Não-bloqueante de outras sprints.

| # | Fase | Effort | Gate principal | ADR |
|---|---|---|---|---|
| P1 | **Modelo de domínio + UI captura** — expandir `BusinessProfile` (anexo_simples, iss_aliquota_pct, cnae_principal, tipo_declaracao_ir) + Alembic + Pydantic + form no console interno | ~1d | Schema migration verde + form valida; modelo Pydantic com `model_config={"extra":"forbid"}` | [[ADR-236]] §D1 |
| P2 | **Derivação do pipeline** — classifier E4 para `pro_labore_mensal` / `lucros_distribuidos_mensal` / `das_pago` / `folha_pj_mensal` (labels novas em `category_template`); leitor de `outras_rendas_tributaveis_pf_anual` via [[ADR-157]] artifact E1.6 | ~2d | Workspace dogfood E4 classifica 100% das transferências PJ→sócio em pró-labore vs lucros; gate cruzar com IRPF declarado | [[ADR-236]] §D2 |
| P3 | **Calculator canônico** — `pipeline/domain/services/tributario/cascata_calculator.py` com regras por regime (Simples-Anexo III/V, Presumido, MEI), fator-R derivado, base PGBL correta, break-even Anexo III↔V, decision triggers parametrizados | ~2d | 4 goldens (1 por regime + 1 com workspace incompleto); paridade com cálculo manual de contador para dogfood | [[ADR-236]] §D3 |
| P4 | **Adapter + narrator** — `pipeline_adapter.build_goals_payload_sync` propaga `bundle["tributario"]` a partir de `business_profile_json + cascata_calculator.compute(...)`; reescrita de `charts_narrator.impostos_pj` ramificada por `regime`; remove "Lucro presumido (32%)" do template | ~1d | Card produção deixa de mostrar texto errado; copy correto por regime; teste de regressão pra "Lucro presumido" hard-coded sumir do output | [[ADR-236]] §D4 |
| P5 | **Card UI cascata real** — componente `<CascataFiscalCard/>` em `frontend/src/components/report/` com decomposição em camadas (waterfall ou steps), fator-R badge, base PGBL com flag declaração simplificada, decision triggers como callouts. Co-design `product-designer`. Substitui `NarrativeChartCard chartId="impostos_pj"` em `S8PrevidenciaSection` | ~2d | A11y AAA; mobile responsive; copy revisado por `financial-planner`; dogfood feedback positivo de 2 famílias | [[ADR-236]] §D5 |
| P6 | **Cutover + telemetria + flip ADR** — sunset do código canned (`charts_narrator.impostos_pj` texto livre vira mínimo); telemetria `mathoms.tributario.cascata_rendered` + `mathoms.tributario.trigger_shown` (zero PII fiscal); flip [[ADR-236]] → `Decidido (A16.tributario-pj-cascata)` | ~1d | Telemetria entrega; nenhum workspace dogfood mostra texto antigo; FAQ produto atualizado | [[ADR-236]] §D6 |

### Hot-fix paralelo (descartado pelo usuário)

Originalmente proposto (~2h, 1 PR) — esconder o card via `report_layout.yaml` OU encurtar pra só DAS + contador + "avaliação fiscal pendente", removendo a frase do PGBL/Lucro Presumido. Usuário optou pela solução completa sem hot-fix; card permanece errado em produção até P4. Trade-off aceito: card mentiroso em prod ~2 semanas vs débito de PR descartável.

## Riscos

| Risco | P | Mitigação |
|---|---|---|
| Classifier E4 confunde pró-labore com salário CLT do cônjuge | P1 | Label nova `pro_labore` em `category_template` exige `member_key=titular_pj` + origem conta PJ; teste com workspace dogfood multi-membro |
| Workspace dogfood não tem IRPF (E1.6) carregado — base PGBL fica 0 | P2 | Estado UI explícito "renda tributável PF não detectada — sem IRPF processado"; CTA upload IRPF |
| Fator-R cai abruptamente (ex.: férias coletivas) — break-even badge fica "à beira" | P2 | Janela 12m móvel suaviza; copy "fator-R móvel 12m" deixa explícito |
| Lucro Real fora de escopo — workspace de cliente avançado fica sem card | P3 | Estado UI "regime Lucro Real — cascata em desenvolvimento" + CTA para suporte; não inventa |
| LGPD: telemetria de "alíquota efetiva por workspace" vaza | P1 | Telemetria só registra `regime`, `event_type`, `trigger_kind` — nunca valores monetários ou nome PJ |
| Recomendação "subir pró-labore pra ocupar PGBL" mal-calibrada gera dívida fiscal | P0 | Copy patterns ADR-236 §D6: "considere avaliar"/"sinal de atenção" + disclaimer obrigatório; nunca "você deve" |
| ADR-236 fixa modelo 2026 — reforma tributária / PEC dividendos quebra cascata | P3 | ADR documenta gatilho de revisão; schema evolution previsível (lucros distribuídos viram tributáveis em camada nova) |
| Holding triggers V1 simplistas geram falso-positivo "abra holding" | P2 | V1 = 1 gatilho (>3 imóveis alugados); copy "considere avaliar com tributarista". V2 cobre completo. |

## Métricas / gates de validação

- **Correção do card** — texto produção não contém substring "Lucro presumido (32%)" em workspace dogfood (regression test).
- **Cobertura de regimes** — 4 goldens em `tests/test_cascata_calculator.py` (1 Simples-III, 1 Simples-V, 1 Presumido, 1 workspace_incompleto). MEI cobre como caso degenerado.
- **Paridade com contador** — dogfood workspace `5@5.com`: cascata calculada bate (±2%) com último DAS efetivo declarado + base PGBL bate (±5%) com IRPF declarado.
- **Decision triggers calibrados** — pelo menos 3 dos 5 gatilhos canônicos (otimização pró-labore × lucros, fator-R break-even, PGBL alíquota-dependente, holding ≥3 imóveis alugados, sublimite estadual Simples) shippam V1 com break-even computado, não copy genérico.
- **UI A11y** — `<CascataFiscalCard/>` passa em axe-core (zero violations) + Lighthouse a11y ≥ 95.
- **Tempo de carregamento** — pipeline_adapter + cascata_calculator adicionam <50ms ao stage E5.N (sem regression em `tests/test_e5n_*`).
- **Idempotência** — re-render do mesmo workspace produz output byte-idêntico (paridade golden).

## Referências

- **Sessão 2026-05-20** — diagnóstico do card S8 em sessão David Robert (workspace dogfood) + co-design `financial-planner` (5 perguntas Q1-Q5 validadas).
- **[[ADR-236]]** — fonte canônica das decisões D1-D6 deste plano.
- **[[ADR-143]]** — rules-as-code (regras de domínio = código + docstring + ADR, não YAML/JSON).
- **[[ADR-157]]** — `extract_irpf_full` E1.6 (fonte de renda tributável PF para base PGBL).
- **[[A10.7]]** — lane de origem do `BusinessProfile` (3 campos minimal) + migration `b1a2c3d4e5f7`.
- **[[ADR-097]]** — boundary pipeline↔backend (calculator vive em `pipeline/domain/services/` puro; adapter injeta dados).
- **[[ADR-102]]** R18 — endpoint JSON exige `response_model` (form de `BusinessProfile` PATCH já segue).
- **[[ADR-180]]** — `GoalsBundle` (estende com nova subchave `tributario`).
- **Perini** "Viver de Renda" cap. previdência privada — base PGBL = renda tributável PF.
- **AUVP** módulo previdência — PGBL só em declaração completa + IR marginal ≥ 22,5% + horizonte >10 anos.
- **Cerbasi** "Como organizar sua vida financeira" cap. renda variável PJ — otimização pró-labore × lucros.
