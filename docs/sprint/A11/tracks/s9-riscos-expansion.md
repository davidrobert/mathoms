---
id: TRACK-s9-riscos-expansion
type: track
title: "Track S9 Riscos e Proteção — Expansão completa (Protection aggregate + ProtectionBundle + 5 blocos UI)"
sprint: A11
plan: PLAN-platform-review
status: ready
created_at: "2026-05-11"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a11
  - status/ready
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
> **Plano canônico:** [docs/plan/PLATFORM_REVIEW/_README.md](../../../plan/PLATFORM_REVIEW/_README.md) §W5
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

### S9-T01 — Hotfix narrativa (≤1 dia, 1 PR, **destrava produção**)

**Owner sugerido:** `senior-cto`. **Paralelo com:** T02, T03 (zero overlap em files).

Mata o sintoma feio sem aguardar a expansão completa. Cliente que abre relatório hoje **não** pode ver `"R$ 0-0M"` em prosa default.

- [ ] Guard early-return em `_narrate_riscos_decisoes` ([pipeline/domain/services/narrativas/charts_narrator.py:355-368](../../../../pipeline/domain/services/narrativas/charts_narrator.py)) quando `_riscos_top3 == []`: emite `context`/`conclusion` com copy degradada coerente ("Sem riscos críticos cadastrados. Mapeie suas exposições no Console para destravar análise de cobertura.") + sinal `data_state: "empty"` no payload de narrativas.
- [ ] Remover string hardcoded `"CPA expatriado + seguro term R$ X-Y M"` da narrativa default. Compliance USA aparece **apenas** quando `payload.has_us_exposure == True` (flag temporária computada no `pipeline_adapter` a partir de `family_members.residencia` e ativos USD — promovida ao `ProtectionBundle.has_us_exposure` em T02).
- [ ] Default `seguro_vida_minimo`/`seguro_vida_maximo` em formatter helpers para `None` quando ausente; render `"a definir"` em vez de `"R$ 0-0M"`.
- [ ] Teste regressão `tests/pipeline/domain/services/narrativas/test_charts_narrator.py::test_riscos_decisoes_empty_list`: fake `riscos_top3=[]` + bag sem `seguro_vida_*` → assert que `context`/`conclusion` **não** contém `": ."`, `"R$ 0-"`, `"CPA expatriado"`.
- [ ] Teste regressão `::test_riscos_default_no_us_assumption`: fake bag sem `has_us_exposure` → assert que `"CPA"`/`"FBAR"`/`"FATCA"` ausentes da narrativa default.
- [ ] Renderer `S9RiscosSection` ([frontend/src/components/report/sections/S9RiscosSection.tsx](../../../../frontend/src/components/report/sections/S9RiscosSection.tsx)) lê `data_state` do payload e, se `"empty"`, renderiza `<EmptyStateCard/>` com CTA "Cadastrar riscos no Console" em vez do `NarrativeChartCard` quebrado. Componente `<EmptyStateCard/>` reusa estilo de `ReportCard variant="warn"`.
- [ ] Goldens E5 atualizados em PR de paridade dedicado se shape `bubble_riscos.context/conclusion` mudar — diff explícito no body do PR.

**Gate de saída T01:** ciclo Ferreira-Campos + workspace vazio rodam sem regressão de narrativa.

### S9-T02 — `Protection` aggregate + `ProtectionBundle` skeleton (~2-3 dias, 1 PR, **gate para T03-T05**)

**Owner sugerido:** `senior-cto` co-design com `data-engineer` (schema/migration). **Paralelo com:** T01 (zero overlap), T03 (T03 depende deste PR mergeado).

Cria a fundação DDD da expansão. Sem este PR mergeado, T03/T04/T05 não destravam.

- [ ] `backend/app/models/protection.py`: aggregate `Protection` conforme ADR-192 §D1. FK `workspace_id`, FK `holder_family_member_id` opcional, FK `policy_ref` campo opaco (vault Fernet em T03 se confirmado uso).
- [ ] Alembic migration (single revision): cria `protections` com índices `(workspace_id)`, `(workspace_id, status)`, `(workspace_id, category)`; adiciona `risks.mitigation_protection_ids JSONB NULL`.
- [ ] Repo `ProtectionRepository` em `backend/app/repositories/` + 6 use cases em `backend/app/application/protections/` (`create_protection`, `update_protection`, `change_status`, `link_to_risk`, `unlink_from_risk`, `archive_protection`).
- [ ] Endpoints `POST/GET/PATCH /protections` + `GET /workspaces/{id}/protection-bundle` com `response_model` Pydantic explícito (ADR-102 R18).
- [ ] OpenAPI snapshot regerado (`make update-openapi-snapshot`).
- [ ] `ConfigStore` Protocol ([backend/app/services/config_store.py](../../../../backend/app/services/config_store.py)) ganha `get_protection_bundle(workspace_id) -> ProtectionBundle`. Implementação `DBConfigStore` consulta `ProtectionRepository` + `RiskRepository` + `BaselineSnapshot`.
- [ ] `ProtectionBundle` TypedDict em [pipeline/domain/types/protection_bundle.py](../../../../pipeline/domain/types/protection_bundle.py) (módulo novo) — sem import de SQLAlchemy. Adapter em `backend/app/services/pipeline_adapter.py` monta via `_project_protection_bundle_sync`/`_async` (mesmo padrão de `build_goals_payload_sync` ADR-180).
- [ ] Testes `backend/tests/test_protection_aggregate.py` (~25 specs): CRUD por workspace, tenancy isolada, link/unlink com Decision e Risk, transições de status, vencimento (`ends_at < hoje` → `status="Vencida"` em job futuro, mas modelo aceita).
- [ ] Gate `dev/check_pipeline_boundaries.py` verde — `pipeline/**` não importa `sqlalchemy`.

**Gate de saída T02:** ADR-192 flippa de `Proposto` para `Decidido (Sprint A11.W5)` quando este PR mergeia.

### S9-T03 — 5 calculators determinísticos + auto-inferência (~3 dias, 1 PR)

**Owner sugerido:** `data-engineer` co-design com `financial-planner` (revisão fórmulas). **Depende de:** T02 mergeado. **Paralelo com:** T04 (T04 só consome o bundle público; pode esboçar em paralelo).

Implementa as 5 regras de domínio (rules-as-code, ADR-143) que ADR-192 §D3 define.

- [ ] Módulo `pipeline/domain/services/protection/` com 5 calculators puros (sem `@lru_cache` — ADR-111). Cada um aceita value object tipado e retorna dataclass de output:
  - `life_insurance_coverage_ideal(inputs: LifeInsuranceInputs) -> CoverageRecommendation`
  - `emergency_reserve_target(inputs: EmergencyReserveInputs) -> ReserveTarget`
  - `disability_coverage_gap(inputs: DisabilityInputs) -> CoverageGap`
  - `itcmd_estimated(inputs: ITCMDInputs) -> ITCMDEstimate` (alíquota por estado: SP 4%, RJ até 8%, MG 5%, demais conforme tabela ICMS atualizada).
  - `compliance_risk_us_person(inputs: USExposureInputs) -> list[ComplianceFlag]` — emite FBAR/FATCA/Estate Tax flags **apenas** se sinal explícito.
- [ ] Cada calculator emite `RiskInferred(category, name, rationale, estimated_impact_brl_cents, source_calculator)` quando o gap material existir. Lista entra em `ProtectionBundle.auto_inferred_risks`. **Não persiste** — UI futura confirma com 1-click "Aceitar como Risco" (cria `Risk` via repo existente).
- [ ] Adapter `_project_protection_bundle_sync` ([backend/app/services/pipeline_adapter.py](../../../../backend/app/services/pipeline_adapter.py)) injeta os 5 calculators no bundle (DIP) — pipeline consome lista de `auto_inferred_risks` já materializada.
- [ ] 5 notas Domain Rule em `docs/reference/rules/` (uma por calculator), cada uma com frontmatter:
  ```yaml
  id: RULE-life-insurance-coverage
  type: domain-rule
  concept: "Cobertura ideal de seguro de vida"
  methodology: ["cerbasi", "perini"]
  canonical_adr: "[[ADR-192]]"
  enforcer_modules:
    - "pipeline/domain/services/protection/life_insurance_calculator.py"
  ```
- [ ] Testes `tests/pipeline/domain/services/protection/test_<calculator>.py` para os 5 — cada um cobre 3+ perfis: solteiro sem deps, casado com 2 deps em minoridade, expatriado USA com ativos > thresholds FBAR/FATCA.
- [ ] Atualizar [docs/reference/ARCHITECTURE.md §4.1 Domain glossary](../../../reference/ARCHITECTURE.md) com 5 conceitos novos apontando para enforcer + ADR.

**Gate de saída T03:** auto-inferência verde em workspace Ferreira-Campos: dependentes minoridade + ausência de apólice de vida → `RiskInferred("falta_seguro_vida")` aparece no bundle com `estimated_impact_brl_cents` calculado.

### S9-T04 — Codegen `report_layout.yaml` + `S9RiscosSection` expandido (~2 dias, 1 PR)

**Owner sugerido:** `product-designer` co-design com frontend dev. **Depende de:** T02 mergeado (bundle público disponível). **Paralelo com:** T03 (T04 pode usar bundle mock até T03 entregar dados reais).

Materializa os 5 blocos visuais consensuais entre os 3 agentes especialistas.

- [ ] `config/report_layout.yaml` §S9 expandido para 5 blocos (formato YAML deste arquivo é a fonte de verdade — ADR-076):
  ```yaml
  9:
    title: "Riscos e Proteção — Seguros Críticos"
    summary: "Mapa de exposições, cobertura atual e ações de mitigação."
    cards:
      - id: "hero_gap_protecao"
      - id: "cobertura_seguros"
      - id: "sucessao"
      - id: "acoes_mitigacao"
    chart_components:
      - id: "bubble_riscos"
  ```
- [ ] `python3 dev/codegen_report_layout.py` re-rodado; commitar `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py` regenerados **no mesmo PR**.
- [ ] 4 cards novos em `frontend/src/components/report/cards/`:
  - `HeroGapProtecaoCard.tsx` — KPI único "Capital segurado R$ X / recomendado R$ Y · gap R$ Z" via `<MonetaryValue/>` + ícone `AlertOctagon` quando gap > 0.
  - `CoberturaSegurosCard.tsx` — tabela: categoria × contratado (✓/✗) × capital × prêmio/mês. Padrão tipográfico de `PrevidenciaPgblCard`.
  - `SucessaoCard.tsx` — checklist (testamento, beneficiários previdência, holding, ITCMD estimado por estado). `ReportCard variant="warn"` quando há gap.
  - `AcoesMitigacaoCard.tsx` — lista priorizada (ação, prazo, custo/mês estimado). Reusa estilo de `PontosUrgentesCard`.
- [ ] `S9RiscosSection.tsx` consome `ProtectionBundle` via codegen layout e compõe os 4 cards + bubble re-enquadrado (bubble agora plota apenas riscos compliance/sucessório, **não** seguros — esses viram tabela).
- [ ] `bubble_riscos` ganha 3ª dimensão (cor) = `mitigation_status` (verde coberto / amarelo parcial / vermelho descoberto) via prop nova em `NarrativeChartCard`.
- [ ] Visual regression tests Playwright (fluxo `@critical` do report) atualizados para os 5 blocos.
- [ ] A11y: `axe-core` verde — contraste AA mínimo, AAA no KPI de gap; `role="region"` + `aria-labelledby` em cada card; tabela ganha `<caption>` ou `aria-label`.
- [ ] Responsive: mobile (`<md`) — tabela de seguros vira cards empilhados; bubble colapsável.
- [ ] Disclaimer fiduciário em cada card que cite cobertura recomendada (ex.: "Estimativa metodológica baseada em Cerbasi/Perini; não constitui recomendação fiduciária. Consultar corretor habilitado.").

**Gate de saída T04:** screenshot da S9 em workspace Ferreira-Campos paritário em densidade com S10; export PDF via Playwright OK.

### S9-T05 — UI mínima de cadastro de apólice (`/protecao`) (~1-1.5 dias, 1 PR)

**Owner sugerido:** `product-designer` co-design com frontend dev. **Depende de:** T02 mergeado (endpoints `/protections` disponíveis). **Paralelo com:** T03, T04.

Sem UI de cadastro, cliente não tem como popular `Protection` — auto-inferência cobre o gap inicial, mas dado real precisa entrar.

- [ ] Página dedicada `/protecao` ou módulo expandido em `/plano` (TBD com `product-designer` — opção A: página própria com listagem por categoria; opção B: tab dentro de `/plano` ao lado de Decisions/Risks).
- [ ] Form mínimo: categoria (select), titular (select de `family_members`), capital, prêmio/mês, vigência (start/end), seguradora, número da apólice (campo opcional, sob vault Fernet).
- [ ] Listagem com filtros: status (ativa/vencida/cancelada), categoria. Total de cobertura agregado por categoria.
- [ ] Botão "Aceitar como Risco" no card de cada `RiskInferred` do bundle — 1-click cria `Risk` via `RiskRepository` (use case existente ADR-178) com `code` derivado do calculator que inferiu.
- [ ] PII: `policy_ref` no vault Fernet (ADR-109 §"Auth portability"); display mascarado por default, "Mostrar" expande com confirmação.
- [ ] Logs estruturados (ADR-110) `mathoms.protection.*` com `policy_ref` redatado em `INFO`; `coverage_brl_cents` aparece como faixa (`R$ 1-5M`, `R$ 5-10M`) em logs, valor exato apenas em `DEBUG`.
- [ ] Smoke E2E Playwright em `frontend/tests/e2e/`: cliente cadastra apólice → bundle recalcula gap → S9 atualiza Hero card.

**Gate de saída T05:** workspace Ferreira-Campos cadastra 3 apólices reais via UI; gap card mostra valor coerente; PII em logs verificado.

### S9-T06 — Goldens E5 reset + paridade narrativa (~0.5-1 dia, 1 PR de paridade dedicado)

**Owner sugerido:** `data-engineer`. **Depende de:** T01–T05 mergeados.

Fecha o ciclo: goldens E5/E5.N atualizados refletindo nova narrativa S9 + bundle protection.

- [ ] Rodar ciclo Ferreira-Campos completo (`pytest tests/test_e{3,4,5}_golden_execution.py -q`); inspecionar diffs.
- [ ] Atualizar goldens em `tests/data/goldens/` com diff explícito justificado no PR body.
- [ ] Validar visualmente PDF do relatório vs. anterior (regressão de não-S9 deve ser zero).
- [ ] Schema E5 (`config/schemas/e5.schema.json`) — verificar se `mapa_riscos`/`bubble_riscos` permanecem; adicionar campos do bundle se necessário.
- [ ] `config/pipeline.json` — bump `report_version` se shape do relatório mudou de forma incompatível (ADR-077 territory).

**Gate de saída T06:** CI verde + smoke humano (rodar `make smoke-test-human` se aplicável) OK.

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

## Critério de aceite consolidado (encerra o track)

- [ ] ADR-192 flippada para `Decidido (Sprint A11.W5)` no merge de T02.
- [ ] Renderer S9 paritário em densidade com S10 (5 blocos + bubble).
- [ ] Workspace vazio renderiza checklist de 6 categorias + auto-inferência, sem texto quebrado.
- [ ] Compliance USA aparece **apenas** com flag explícita; default não vaza assunção.
- [ ] 5 Domain Rule notes publicadas em `docs/reference/rules/`.
- [ ] Disclaimers fiduciários em todos os cards de cobertura recomendada.
- [ ] PII: `policy_ref` no vault; logs estruturados redatados; teste assertando ausência de raw em `INFO`.
- [ ] OpenAPI snapshot + codegen layout + DB_SCHEMA_REFERENCE regenerados e commitados.
- [ ] Goldens E5 atualizados com diff justificado.
- [ ] `pre-commit run --all-files` + `pytest backend/tests -q` + `pytest tests -q` + `cd frontend && npm test -- --run` + `npm run test:e2e` verdes.
- [ ] Track `s9-riscos-expansion.md` flippado para `status: consumed` + `consumed_at`.

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
- **R5 — Goldens E5 mudando em vários PRs.** Reset rigoroso no T06 evita drift acumulado. Mitigação: T01-T05 **não** reset goldens; cada um marca `pytest.mark.golden_drift_expected` em casos afetados; T06 reset único com diff justificado.
- **R6 — Alembic heads collision** com migrations paralelas. Mitigação: T02 abre primeiro, seedando head; T05 (se mexer em schema) rebase explícito antes do push.
- **R7 — Cliente piloto vê regressão estética** em PDF de relatório enquanto T04 não fecha. Mitigação: T01 entrega empty state digno; ciclo Ferreira-Campos durante onda 2 usa flag de feature `MATHOMS_S9_EXPANSION` para mostrar versão antiga até T04 mergear.

## Ligações

- ADR canônica: [[ADR-192]] · [docs/adr/192-protection-aggregate-protectionbundle-secao-9.md](../../../adr/192-protection-aggregate-protectionbundle-secao-9.md)
- ADRs relacionadas (consumo): [[ADR-076]] (codegen layout) · [[ADR-090]] (Money decimal) · [[ADR-097]] (services ISP) · [[ADR-101]] (DDD/SOLID) · [[ADR-109]] (auth/vault) · [[ADR-110]] (logging estruturado) · [[ADR-111]] (stateless) · [[ADR-129]] (renderer React único) · [[ADR-134]] (ConfigStore) · [[ADR-143]] (rules-as-code) · [[ADR-178]] (Risk aggregate) · [[ADR-180]] (GoalsBundle)
- Plano canônico: [PLAN-platform-review §W5](../../../plan/PLATFORM_REVIEW/_README.md)
- Sprint MOC: [docs/sprint/A11/_README.md](../_README.md)
- Revisão multi-agente origem: 2026-05-11 (`product-designer` + `financial-planner` + `senior-cto`)
