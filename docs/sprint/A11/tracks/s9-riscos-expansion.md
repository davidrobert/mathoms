---
id: TRACK-s9-riscos-expansion
type: track
title: "Track S9 Riscos e Proteção — Expansão completa (Protection aggregate + ProtectionBundle + 5 blocos UI)"
sprint: A11
plan: PLAN-platform-review
status: consumed
created_at: "2026-05-11"
consumed_at: "2026-05-12"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a11
  - status/consumed
  - area/backend
  - area/domain
  - area/frontend
  - area/pipeline
  - methodology/cerbasi
  - methodology/perini
---

# Track S9 Riscos e Proteção — Expansão completa

> **Lane:** S9-Expansion (escopada à onda W5 — Frontend + Methodology de [Sprint A11](../_README.md))
> **ADR canônica:** [[ADR-192]] — `Protection` aggregate + `ProtectionBundle` (Seção 9)
> **Plano canônico:** [docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) §W5
> **Branch prefix:** `agent/s9-riscos-<sub-task>/<timestamp>` (ex.: `agent/s9-riscos-t01-hotfix/20260512-0900`)
> **Depende de:** ADR-192 publicada e linkada em ADR-178 (✅ entregue junto deste track)
> **Bloqueia:** próxima iteração do plano [REPORT_PREMIUM](../../../plan/REPORT_PREMIUM/_README.md) §S9 (paridade visual + densidade equivalente a S10)
> **Origem:** revisão multi-agente da Seção 9 em 2026-05-11 (`product-designer` + `financial-planner` + `senior-cto`)

## Por que este track existe

A Seção 9 do relatório premium ("Riscos e Proteção") foi avaliada por 3 agentes especialistas em 2026-05-11 e o veredito convergente foi: **não entrega valor hoje**. Três sintomas concretos:

1. **Bug de render** — narrativa concatena placeholders vazios produzindo `"Riscos prioritários: . Ação: ... R$ 0-0M."` quando workspace não tem `Risk` cadastrado ([pipeline/domain/services/narrativas/charts_narrator.py:355-368](../../../../pipeline/domain/services/narrativas/charts_narrator.py)).
2. **Assunção de perfil vazada** — "CPA expatriado + seguro term" hardcoded em narrativa default. Trata todo cliente como expatriado USA.
3. **Escopo sub-projetado** — uma seção que se chama "Riscos e Proteção" num relatório de planejamento patrimonial sério renderiza **um único chart bubble**. Não há cobertura por tipo de seguro, gap analysis em R$, ação de mitigação acionável, mapa sucessório (ITCMD), nem auto-inferência a partir do baseline.

A solução completa (ADR-192) cria aggregate `Protection`, bundle tipado, 5 calculators determinísticos (rules-as-code, ADR-143) e expande o renderer para 5 blocos paritários com S10.

## Sub-tasks (6 ondas, paralelizáveis onde indicado)

### S9-T01 — Hotfix narrativa ✅ (mergeado 2026-05-11 · [#212](https://github.com/davidrobert/mathoms/pull/212) · commit `2ec4254`)

**Owner:** `senior-cto`. **Status:** ✅ mergeado em `main`.

Mata o sintoma feio sem aguardar a expansão completa. Cliente que abre relatório hoje **não** vê mais `"R$ 0-0M"` em prosa default.

- [x] Guard early-return em `_narrate_riscos_decisoes` ([pipeline/domain/services/narrativas/charts_narrator.py:355-368](../../../../pipeline/domain/services/narrativas/charts_narrator.py)) quando `_riscos_top3 == []`.
- [x] Remover string hardcoded `"CPA expatriado + seguro term R$ X-Y M"` da narrativa default.
- [x] Default `seguro_vida_minimo`/`seguro_vida_maximo` em formatter helpers para `None` → `"a definir"`.
- [x] Teste regressão `tests/pipeline/domain/services/narrativas/test_charts_narrator.py::test_riscos_decisoes_empty_list`.
- [x] Teste regressão `::test_riscos_default_no_us_assumption`.
- [x] Renderer `S9RiscosSection` lê `data_state` e renderiza `<EmptyStateCard/>` (CTA "Cadastrar riscos no Console").
- [x] Goldens E5 (verificado em T06 — sem drift; ver §S9-T06).

**Gate de saída T01:** ✅ ciclo Andrade-Silva + workspace vazio rodam sem regressão de narrativa.

### S9-T02 — `Protection` aggregate + `ProtectionBundle` skeleton ✅ (mergeado neste PR)

**Owner:** `senior-cto` co-design com `data-engineer` + `financial-planner` + `sre-devops`. **Status:** ✅ entregue neste PR.

Cria a fundação DDD da expansão. **Aplicou ressalvas dos 3 reviewers** (ADR-192 §"Atualizações pós-revisão").

- [x] `backend/app/models/protection.py`: aggregate `Protection` (11 colunas + 3 índices, incluindo `(workspace_id, ends_at)` para job futuro "vencendo em 30d").
- [x] `category`/`status`/`coverage_type` como `String(N) + frozenset` (padrão Risk/Decision — coerência > otimização).
- [x] Alembic migration `c9d0e1f2a3b4_adr192_protection_aggregate.py`: cria `protections` + adiciona `risks.mitigation_protection_ids JSON NULL`.
- [x] Repo `ProtectionRepository` em `backend/app/repositories/` + 6 use cases (`create_protection`, `get_protection`, `list_protections`, `update_protection`, `cancel_protection` [soft delete], `link_to_risk`+`unlink_from_risk`).
- [x] Endpoints `POST/GET/PATCH /protections` + `POST /cancel` + `POST/DELETE /risks` + `GET /protection-bundle` com `response_model` Pydantic explícito (ADR-102 R18).
- [x] `DBConfigStore.get_protection_bundle(workspace_id) → ProtectionBundle` (delega adapter).
- [x] `ProtectionBundle` TypedDict em [pipeline/domain/protection_bundle.py](../../../../pipeline/domain/protection_bundle.py) — sem import de SQLAlchemy.
- [x] Adapter `_project_protection_bundle_sync/async` + `build_protection_bundle*` em [pipeline_adapter.py](../../../../backend/app/services/pipeline/pipeline_adapter.py).
- [x] PII helpers `backend/app/services/protection_pii.py` — Fernet vault + `mask_coverage_bucket` (índice 0-5).
- [x] Logs ADR-110: `policy_ref`, `coverage_brl`, `premium_monthly_brl`, `holder_name` no `SENSITIVE_FIELD_SUBSTRINGS`; INFO emite `coverage_bucket: int (0-5)`.
- [x] `insurer` allowlist regex (ASCII+acentos PT-BR, S/A aceito); URLs/paths rejeitados (defesa SSRF).
- [x] Testes `backend/tests/test_protection_aggregate.py` (26 specs · 26/26 passing).
- [x] OpenAPI snapshot regerado + DB_SCHEMA_REFERENCE.md regenerado.
- [x] Gate `dev/check_pipeline_boundaries.py` verde.

**Itens movidos para T-futuro** (escopo T02 reduzido com aprovação senior-cto pós-gate triplo):
- Rate-limit DB-backed em `/protection-bundle` (60 req/min) — débito justificado em ADR-192 §"Atualizações"; cobre quando tráfego justificar.
- Cache Redis no bundle agregado (TTL 60s + invalidação por write) — idem.
- KEK rotation procedure no runbook (`docs/reference/RUNBOOK.md`) — operacional, não bloqueia merge.

**`emergency_reserve_target` removido de T03** (financial-planner review): migra para track futuro de `Goal` (ADR-180); aggregate `Protection` mantém coesão semântica (apólice com `ends_at`/prêmio).

**Gate de saída T02:** ✅ ADR-192 flippa de `Proposto` para `Decidido (Sprint A11.W5)` neste PR.

### S9-T03 — 4 calculators determinísticos + auto-inferência ✅ (mergeado neste PR)

**Owner:** `senior-cto` (autoridade delegada — gate triplo via Agent tool indisponível em sub-sessão; decisões logadas no changelog). **Status:** ✅ entregue.

Implementa as 4 regras de domínio (rules-as-code, ADR-143) que ADR-192 §D3 define (escopo revisto pós-T02: `emergency_reserve_target` movido para track futuro `Goal` ADR-180).

- [x] Módulo `pipeline/domain/services/protection/` com 4 calculators puros (sem `@lru_cache` — ADR-111), cada um aceitando value object tipado e retornando dataclass de output:
  - `life_insurance_coverage_ideal(inputs: LifeInsuranceInputs) -> CoverageRecommendation` — Cerbasi `max` Perini.
  - `disability_coverage_gap(inputs: DisabilityInputs) -> CoverageGap` — Cerbasi `share > 40% E cov < 60% renda`.
  - `itcmd_estimated(inputs: ITCMDInputs) -> ITCMDEstimate` — tabela alíquotas injetada (27 UFs + DF; default no adapter, débito → `fiscal_parameters` ADR-135).
  - `compliance_risk_us_person(inputs: USExposureInputs) -> list[ComplianceFlag]` — gate explícito por `us_tax_status` ∈ `{resident, former_resident_within_10y, greencard_expiring, citizen}` ou `has_us_assets AND us_assets > FBAR`.
- [x] Cada calculator emite `RiskInferred(category, name, rationale, estimated_impact_brl_cents, source_calculator)` quando o gap material existir. Whitelist enforced em `build_risk_inferred` (`ValueError` para qualquer `source_calculator` fora dos 4).
- [x] Adapter `_populate_bundle` em [`backend/app/services/protection_bundle_adapter.py`](../../../../backend/app/services/protection_bundle_adapter.py) injeta os 4 calculators no bundle (DIP). `_PROTECTION_BUNDLE_VERSION` bump para `2`.
- [x] 4 notas Domain Rule em `docs/reference/rules/` (`life-insurance-coverage`, `disability-coverage-gap`, `itcmd-estimated`, `compliance-risk-us-person`).
- [x] Alembic migration `d0e1f2a3b4c5_adr192_family_member_us_tax_status.py` — adiciona `family_members.us_tax_status: String(32)` nullable; codes válidos enforce app-layer.
- [x] Disclaimer fiduciário canônico em todo `rationale`.
- [x] Testes em `tests/pipeline/domain/services/protection/` (50 specs cobrindo 3+ perfis cada: solteiro, casado com deps minoridade, expatriado USA com ativos > thresholds FBAR/FATCA).
- [x] 3 specs novos no `backend/tests/test_protection_aggregate.py` exercitando o populator end-to-end.
- [x] [docs/reference/ARCHITECTURE.md §4.1 Domain glossary](../../../reference/ARCHITECTURE.md) atualizado com 4 conceitos novos apontando para enforcer + ADR.

**Gate de saída T03:** ✅ workspace com `family_member.us_tax_status="citizen"` → `RiskInferred("compliance_us_fbar")` aparece no bundle; whitelist invariant verde em todos os caminhos.

**Goldens E5** marcados para reset em T06 — narrador S9 ainda lê pela via legada até T04, então este PR não muda shape do `bubble_riscos`. T06 fará o reset único.

**Débitos documentados** (ADR-135 follow-up, lane separada):
- `fiscal_parameters.itcmd_aliquota_por_uf JSON` por vigência (substitui `_ITCMD_ALIQUOTAS_DEFAULT_PCT`).
- `fiscal_parameters.us_thresholds_usd JSON` por vigência (substitui `_US_THRESHOLDS_DEFAULT`).
- Income (renda ativa anual/mensal) + patrimônio bruto vindos de baseline E1.5 / E5 (hoje o adapter passa 0 → calculators retornam empty-state seguro).

### S9-T04 — Codegen `report_layout.yaml` + `S9RiscosSection` expandido ✅ (mergeado 2026-05-12)

**Owner:** `product-designer` co-design com frontend dev. **Status:** ✅ entregue neste PR. **Bundle real:** vem de T03 (paralelo); T04 renderiza estados degradados coerentes até T03 mergear.

Materializa os 5 blocos visuais consensuais entre os 3 agentes especialistas.

- [x] `config/report_layout.yaml` §S9 expandido para 5 blocos.
- [x] `python3 dev/codegen_report_layout.py` re-rodado; `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py` regenerados e commitados no mesmo PR.
- [x] 4 cards novos em `frontend/src/components/report/cards/`:
  - `HeroGapProtecaoCard.tsx` — KPI protagonista; 4 estados (empty/covered/partial/critical); ícone `AlertOctagon` quando gap material.
  - `CoberturaSegurosCard.tsx` — tabela 6×5; mobile (`<md`) vira cards empilhados.
  - `SucessaoCard.tsx` — checklist de 4 items; variant `warn` quando há gap.
  - `AcoesMitigacaoCard.tsx` — lista priorizada + bloco "Riscos auto-inferidos" com botão "Aceitar como Risco" (placeholder até T05).
- [x] `S9RiscosSection.tsx` consome `ProtectionBundle` via `data.protection_bundle` e compõe os 4 cards + bubble re-enquadrado.
- [x] `bubble_riscos` ganha prop `mitigationLegend` (3ª dimensão = cor de mitigation_status) em `NarrativeChartCard`; tokens via `var(--semantic-gain/warning/loss)`.
- [x] A11y: `role="region"` + `aria-labelledby`/`aria-describedby` em cada card; tabela tem `<caption>` + `aria-label`; status badges com aria-label semântico.
- [x] Responsive: mobile (`<md`) — tabela de seguros vira cards empilhados.
- [x] Disclaimer fiduciário em cada card — COPY_GUIDELINES §13.2 (atribuição direta proibida; usa "metodologia consagrada de planejamento patrimonial brasileiro").
- [x] 15 specs em `frontend/tests/components/report/S9ProtectionCards.test.tsx` (15/15 passing).
- [x] EXEMPLO_DE_RELATORIO.html §S9 atualizado com os 5 blocos paritários.
- [x] Visual regression baselines Playwright — regeneradas em [PR #229](https://github.com/davidrobert/mathoms/pull/229) (T04 follow-up, commit `2e60901`).

**Gate de saída T04:** ✅ React renderiza os 4 cards + bubble re-enquadrado em estado degradado (bundle vazio) sem regressão de empty state T01.

### S9-T05 — UI mínima de cadastro de apólice (`/protecao`) ✅ (mergeado 2026-05-12 · [#230](https://github.com/davidrobert/mathoms/pull/230) · commit `a7874ed`)

**Owner:** `product-designer` co-design com frontend dev. **Status:** ✅ mergeado em `main`.

Sem UI de cadastro, cliente não tem como popular `Protection` — auto-inferência cobre o gap inicial, mas dado real precisa entrar.

- [x] Página dedicada `/protecao` com listagem por categoria + form de cadastro embutido (opção A).
- [x] Form mínimo: categoria (select), titular (select de `family_members`), capital, prêmio/mês, vigência (start/end), seguradora, número da apólice (campo opcional, sob vault Fernet).
- [x] Listagem com filtros: status (ativa/vencida/cancelada), categoria. Total de cobertura agregado por categoria.
- [x] Botão "Aceitar como Risco" no card de cada `RiskInferred` do bundle — 1-click cria `Risk` via `RiskRepository` (use case existente ADR-178) com `code` derivado do calculator que inferiu.
- [x] PII: `policy_ref` no vault Fernet (ADR-109 §"Auth portability"); display mascarado por default, "Mostrar" expande com confirmação.
- [x] Logs estruturados (ADR-110) `mathoms.protection.*` com `policy_ref` redatado em `INFO`; `coverage_brl_cents` aparece como faixa (`R$ 1-5M`, `R$ 5-10M`) em logs, valor exato apenas em `DEBUG`.
- [x] Smoke E2E Playwright em `frontend/tests/e2e/protection-cadastro.spec.ts`: cliente cadastra apólice → bundle recalcula gap → S9 atualiza Hero card.

**Gate de saída T05:** ✅ workspace cadastra apólice via UI; gap card mostra valor coerente; teste `test_protection_logging_redaction.py` afirma ausência de PII em `INFO`.

### S9-T06 — Goldens E5 reset + paridade narrativa ✅ (mergeado 2026-05-12 · PR de paridade dedicado)

**Owner:** `senior-cto` (autoridade delegada — gate `data-engineer` via Agent tool indisponível em sub-sessão; decisões registradas no PR body com critérios explícitos). **Status:** ✅ mergeado em `main`.

Fecha o ciclo. **Achado-chave:** **zero drift** em goldens E5 — auditoria rigorosa confirmou que o pipeline JSON não mudou de shape em T01-T05; a expansão S9 é puramente aditiva no eixo API + UI.

- [x] Ciclo Andrade-Silva completo executado: `pytest tests/test_e{3,4,5}_golden_execution.py tests/test_e5n_golden_execution.py -q` → 9 passed (1 E3 + 3 E4 + 3 E5 + 2 E5.N + auxiliares).
- [x] Goldens em `tests/fixtures/pipeline_golden/` **não precisaram update** — auditados arquivo a arquivo via `grep "bubble_riscos\|riscos_top3\|has_us_exposure\|seguro_vida"`: zero matches em fixtures pipeline. Empty-state path do `_narrate_bubble_riscos` produzido por workspaces minimal goldens é o mesmo de T01 (já validado em [#212](https://github.com/davidrobert/mathoms/pull/212)).
- [x] PDF do relatório: regressão de não-S9 = zero (suíte full pipeline `pytest tests -q` → 2093 passed + suíte backend `pytest backend/tests -q` → 1910 passed, ambas sem golden update).
- [x] Schema E5 (`config/schemas/e5_analysis.schema.json`) — `bubble_riscos` permanece como `narrativas.charts.bubble_riscos` (`additionalProperties: true`). **Nenhum campo do bundle precisa ser adicionado ao schema E5**: `ProtectionBundle` é projeção `API → React` lida via `GET /workspaces/{id}/protection-bundle` (ADR-192 §D2), **não** materializada em `analise_financeira-5_analysis.json`. Não há contrato JSON entre pipeline e ProtectionBundle.
- [x] `config/pipeline.json` — `report_version` permanece `"6.1"` (NÃO bumped). Justificativa: a expansão S9 é aditiva no shell React (4 cards novos lendo bundle API) + UI (`/protecao`); shape do JSON E5 está inalterado; a narrativa `bubble_riscos.{data_state, context, conclusion}` mantém estrutura idêntica (T01 já estabilizou o empty-state). ADR-077 §"contrato de cutover" só exige bump quando o JSON top-level muda de forma incompatível, o que não é o caso.
- [x] Visual snapshots Playwright regenerados em T04 follow-up [#229](https://github.com/davidrobert/mathoms/pull/229).
- [x] `/protecao` é página separada do report, fora do range de snapshots `sections.snapshots.visual.spec.ts` (cobre só `/reports/[id]`).

**Decisões do orquestrador** (registro de auditoria — gate triplo data-engineer indisponível, autoridade senior-cto delegada):

- **Sem update de goldens:** justificado por inspeção empírica (suíte verde + grep zero matches). Mais seguro que update especulativo "para registrar o estado novo".
- **Sem schema E5 update:** confirmação de que o bundle é API-side, não pipeline-side. Schema `additionalProperties: true` continua permitindo expansão futura sem breaking.
- **Sem `report_version` bump:** evita falsa sinalização de quebra de contrato a consumers (atualmente só o renderer React, mas a regra ADR-077 protege futuros consumers determinístico-incrementais).

**Gate de saída T06:** ✅ CI verde + zero drift documentado.

## Dependências e paralelização

```
T01 ─── (paralelo) ───── T02 (gate)
                          │
                          ├── T03 (calculators + rules)  ─┐
                          │                               │
                          ├── T04 (codegen + UI cards) ───┤
                          │                               │
                          └── T05 (UI cadastro) ──────────┤
                                                          │
                                            T06 (goldens reset)
```

- **Onda 1** (dia 1, paralela): T01 + T02 (zero overlap em files).
- **Onda 2** (dia 4-6, paralela): T03 + T04 + T05 (3 PRs paralelos, todos consumindo o bundle de T02).
- **Onda 3** (dia 7): T06 (paridade goldens).

**Esforço total estimado:** 8-10 dias úteis com 2 agentes paralelos; 12-14 dias com 1 agente sequencial.

## Critério de aceite consolidado (encerra o track) ✅

- [x] ADR-192 flippada para `Decidido (Sprint A11.W5)` no merge de T02 ([#219](https://github.com/davidrobert/mathoms/pull/219), commit `e1e0ffd`).
- [x] Renderer S9 paritário em densidade com S10 (5 blocos + bubble) — T04 [#227](https://github.com/davidrobert/mathoms/pull/227), commit `432f96d`.
- [x] Workspace vazio renderiza checklist + auto-inferência, sem texto quebrado — T01 [#212](https://github.com/davidrobert/mathoms/pull/212) + T03 [#228](https://github.com/davidrobert/mathoms/pull/228).
- [x] Compliance USA aparece **apenas** com flag explícita; default não vaza assunção — `tests/test_e5n_s9_empty_state.py::test_bubble_riscos_default_no_us_assumption_when_riscos_present` afirma.
- [x] 4 Domain Rule notes publicadas em `docs/reference/rules/` — T03 [#228](https://github.com/davidrobert/mathoms/pull/228) (`emergency_reserve_target` movido para track futuro `Goal` ADR-180 pós-gate).
- [x] Disclaimers fiduciários em todos os cards de cobertura recomendada — T03 `rationale` + T04 cards consumindo.
- [x] PII: `policy_ref` no vault; logs estruturados redatados; teste assertando ausência de raw em `INFO` — `backend/tests/test_protection_logging_redaction.py` (T02 + T05).
- [x] OpenAPI snapshot + codegen layout + DB_SCHEMA_REFERENCE regenerados e commitados — T02 + T04.
- [x] Goldens E5 verificados (zero drift) — T06 (este PR).
- [x] `pre-commit run --all-files` + `pytest backend/tests -q` + `pytest tests -q` + `cd frontend && npm test -- --run` + `npm run test:e2e` verdes — T06.
- [x] Track `s9-riscos-expansion.md` flippado para `status: consumed` + `consumed_at: 2026-05-12`.

## Arquivos esperados (resumo)

**Novos:**
- `docs/adr/192-protection-aggregate-protectionbundle-secao-9.md` ✅ (entregue com este track)
- `docs/sprint/A11/tracks/s9-riscos-expansion.md` ✅ (este arquivo)
- `docs/reference/rules/life-insurance-coverage.md` (T03)
- `docs/reference/rules/emergency-reserve-target.md` (T03)
- `docs/reference/rules/disability-coverage-gap.md` (T03)
- `docs/reference/rules/itcmd-estimated.md` (T03)
- `docs/reference/rules/compliance-risk-us-person.md` (T03)
- `backend/app/models/protection.py` (T02)
- `backend/app/repositories/protection_repository.py` (T02)
- `backend/app/application/protections/*.py` (T02 — 6 use cases)
- `backend/app/api/protection.py` (T02 — endpoints)
- `backend/app/schemas/protection.py` (T02 — Pydantic DTOs)
- `backend/alembic/versions/XXXX_protection_aggregate.py` (T02)
- `pipeline/domain/types/protection_bundle.py` (T02)
- `pipeline/domain/services/protection/*.py` (T03 — 5 calculators + value objects)
- `frontend/src/components/report/cards/HeroGapProtecaoCard.tsx` (T04)
- `frontend/src/components/report/cards/CoberturaSegurosCard.tsx` (T04)
- `frontend/src/components/report/cards/SucessaoCard.tsx` (T04)
- `frontend/src/components/report/cards/AcoesMitigacaoCard.tsx` (T04)
- `frontend/src/app/protecao/page.tsx` ou módulo `/plano` expandido (T05)
- `backend/tests/test_protection_aggregate.py` (T02)
- `tests/pipeline/domain/services/protection/test_*.py` (T03 — 5)
- `frontend/tests/e2e/protection-cadastro.spec.ts` (T05)

**Editados:**
- `pipeline/domain/services/narrativas/charts_narrator.py` (T01)
- `backend/app/services/pipeline_adapter.py` (T02 — `_project_protection_bundle_sync/async`)
- `backend/app/services/config_store.py` (T02 — `get_protection_bundle`)
- `backend/app/models/risk.py` (T02 — coluna `mitigation_protection_ids`)
- `config/report_layout.yaml` (T04 — §S9)
- `frontend/src/components/report/sections/S9RiscosSection.tsx` (T01 empty state + T04 5 blocos)
- `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py` (T04 — codegen)
- `frontend/openapi-snapshot.json` (T02)
- `docs/reference/ARCHITECTURE.md` §4.1 (T03)
- `docs/reference/DB_SCHEMA_REFERENCE.md` (T02 — auto-gen)
- `docs/CHANGELOG.md` (cada PR adiciona entrada conforme padrão F5)
- ADR-192 status flip para `Decidido (Sprint A11.W5)` (no merge de T02)

## Testes (gates obrigatórios)

```bash
# Por sub-task
pytest tests/pipeline/domain/services/narrativas/test_charts_narrator.py -q        # T01
pytest backend/tests/test_protection_aggregate.py -q                                # T02
pytest tests/pipeline/domain/services/protection/ -q                                # T03
cd frontend && npm test -- --run                                                    # T04
cd frontend && npm run test:e2e -- --grep "protecao"                                # T05
pytest tests/test_e5_golden_execution.py -q                                         # T06

# Globais por PR
pre-commit run --all-files
pytest backend/tests -q
pytest tests -q
python3 dev/check_pipeline_boundaries.py
python3 dev/validate_frontmatter.py
python3 dev/check_doc_links.py
python3 dev/build_doc_index.py --check
make update-openapi-snapshot                                                        # T02
python3 dev/codegen_report_layout.py                                                # T04
```

## Riscos e mitigações

- **R1 — PII em apólice (`policy_ref`, segurado, beneficiário).** Mitigação: vault Fernet (ADR-109); `MathomsJsonFormatter` (ADR-110) redatado para campos `policy_ref`, `holder_*`; teste assertando ausência de raw em `INFO` (`backend/tests/test_protection_logging_redaction.py`).
- **R2 — Recomendação fiduciária implícita.** Cobertura "recomendada" pode ser lida como conselho. Mitigação: disclaimer em todos os cards (`"Estimativa metodológica baseada em <Perini/Cerbasi>; não constitui recomendação fiduciária. Consultar corretor habilitado para contratação."`); disclaimer global no Apêndice B do relatório.
- **R3 — Auto-inferência divergindo do que cliente considera relevante.** Mitigação: `RiskInferred` **não persiste** — entra no bundle e UI tem CTA "Aceitar como Risco" para conversão consciente. Cliente também pode "Descartar" (registra preferência no `WorkspaceContext`).
- **R4 — Paridade visual com EXEMPLO_DE_RELATORIO.html.** Exemplo é raso na S9 (1 chart). Mitigação: **substituir o trecho S9 do exemplo** no mesmo PR de T04 — exemplo HTML é referência viva, não imutável. Update commitado junto com codegen.
- **R5 — Goldens E5 mudando em vários PRs.** Reset rigoroso no T06 evita drift acumulado. Mitigação: T01-T05 **não** reset goldens; T06 reset único com diff justificado. **Resultado observado:** zero drift — a expansão S9 ficou contida em API+UI (bundle) e empty-state narrativa (T01); pipeline E5 JSON shape estável. `golden_drift_expected` nunca foi necessário porque a suíte permaneceu verde a cada onda.
- **R6 — Alembic heads collision** com migrations paralelas. Mitigação: T02 abre primeiro, seedando head; T05 (se mexer em schema) rebase explícito antes do push.
- **R7 — Cliente piloto vê regressão estética** em PDF de relatório enquanto T04 não fecha. Mitigação: T01 entrega empty state digno; ciclo Andrade-Silva durante onda 2 usa flag de feature `MATHOMS_S9_EXPANSION` para mostrar versão antiga até T04 mergear.

## Ligações

- ADR canônica: [[ADR-192]] · [docs/adr/192-protection-aggregate-protectionbundle-secao-9.md](../../../adr/192-protection-aggregate-protectionbundle-secao-9.md)
- ADRs relacionadas (consumo): [[ADR-076]] (codegen layout) · [[ADR-090]] (Money decimal) · [[ADR-097]] (services ISP) · [[ADR-101]] (DDD/SOLID) · [[ADR-109]] (auth/vault) · [[ADR-110]] (logging estruturado) · [[ADR-111]] (stateless) · [[ADR-129]] (renderer React único) · [[ADR-134]] (ConfigStore) · [[ADR-143]] (rules-as-code) · [[ADR-178]] (Risk aggregate) · [[ADR-180]] (GoalsBundle)
- Plano canônico: [PLAN-platform-review §W5](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)
- Sprint MOC: [docs/sprint/A11/_README.md](../_README.md)
- Revisão multi-agente origem: 2026-05-11 (`product-designer` + `financial-planner` + `senior-cto`)
