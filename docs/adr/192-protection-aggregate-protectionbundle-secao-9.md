---
id: ADR-192
type: adr
title: "`Protection` aggregate + `ProtectionBundle` (Seção 9 — Riscos e Proteção)"
status: Decidido
phase: "Sprint A11.W5"
date: "2026-05-11"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-101]]"
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-129]]"
  - "[[ADR-134]]"
  - "[[ADR-143]]"
  - "[[ADR-178]]"
  - "[[ADR-180]]"
supersedes: []
superseded_by: []
aliases: ["ADR 192"]
tags:
  - area/backend
  - area/domain
  - area/persistence
  - area/pipeline
  - area/multitenancy
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
---

# ADR-192 — `Protection` aggregate + `ProtectionBundle` (Seção 9 — Riscos e Proteção)

**Status:** Decidido (Sprint A11.W5) • **Data:** 2026-05-11 • **Relaciona** [ADR-076](#adr-076--codegen-de-report-layout--single-source-yaml), [ADR-090](#adr-090--decimal-para-valores-monetários), [ADR-097](#adr-097--services-de-domínio-com-value-object-tipado-isp), [ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e), [ADR-110](#adr-110--logging-estruturado-json--otel-opt-in-a6f3), [ADR-111](#adr-111--backend-stateless-rigoroso-a6f6), [ADR-129](#adr-129--descontinuação-completa-do-renderer-html-server-side), [ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76), [ADR-178](#adr-178--risk-aggregate-workspace-scoped), [ADR-180](#adr-180--goalsjson-cutover-final-via-stageconfigconfig_store-extendido). **Origem:** revisão multi-agente da Seção 9 em 2026-05-11 (`product-designer` + `financial-planner` + `senior-cto`); enquadra-se na onda W5 (Frontend + Methodology) de [Sprint A11](../sprint/A11/_README.md).

## Atualizações pós-revisão (gate triplo T02, 2026-05-11)

Co-design dos 3 reviewers (`data-engineer`, `financial-planner`, `sre-devops`)
gerou estas ressalvas, aplicadas neste PR de T02:

- **`category`/`status` como `String(N) + frozenset`** (padrão `Risk`/`Decision`),
  não Enum Postgres nativo. Coerência > otimização; categoria nova = 1 linha em
  const, zero migration.
- **Soft delete via `status="Cancelada"`**; hard delete reservado para
  `/admin/lgpd-request` (T-futuro). Renomeado use case `archive_protection` →
  `cancel_protection`.
- **`emergency_reserve_target` removido de §D3** — é meta de liquidez, não
  apólice. Migra para track futuro de `Goal` (ADR-180). Mantém aggregate
  `Protection` coeso ("contrato com `ends_at` e prêmio"). Calculators T03
  ficam em 4 (em vez de 5): life, disability, ITCMD, US-person.
- **ITCMD/FBAR/Estate Tax thresholds vêm de `fiscal_parameters`** (ADR-135) por
  `effective_date` — calculator T03 não pode hardcodar.
- **`RiskInferred` lista branca**: apenas os 4 calculators determinísticos podem
  emitir (holding/D&O/fideicomisso são recomendação fiduciária, fora de escopo).
- **`coverage_type: Enum["term","whole","universal"]`** adicionado como **campo**
  do aggregate (não nova categoria) — afeta gap analysis (term encerra; whole
  acumula valor).
- **Índice novo**: `(workspace_id, ends_at)` viabiliza job futuro "vencendo
  em 30d" sem migration adicional.
- **PII**: `policy_ref`, `coverage_brl`, `premium_monthly_brl`, `holder_name`
  adicionados ao `SENSITIVE_FIELD_SUBSTRINGS` em
  [`backend/app/core/logging.py`](../../backend/app/core/logging.py); logs em
  INFO emitem `coverage_bucket: int (0-5)` via
  [`mask_coverage_bucket`](../../backend/app/services/protection_pii.py).
- **`insurer` allowlist regex** ASCII+acentos PT-BR + separadores comuns
  (S/A aceito); URLs/paths rejeitados explicitamente (defesa SSRF).
- **Disclaimer canônico T04** (texto canônico em §"Critério de aceite" abaixo):
  cita corretor habilitado pela Susep + planejador CFP® + data fiscal vigente.
- **Rate-limit/cache Redis no `/protection-bundle`** marcado como **débito
  T-futuro** (T05 ou follow-up dedicado) — escopo T02 fica focado em modelo +
  endpoints corretos; cache vira lane separada quando tráfego justificar.

## Contexto

A Seção 9 do relatório premium ("Riscos e Proteção — Seguros Críticos") renderiza hoje **um único `NarrativeChartCard`** ([frontend/src/components/report/sections/S9RiscosSection.tsx](../../frontend/src/components/report/sections/S9RiscosSection.tsx)) consumindo o chart `bubble_riscos`. O blueprint em [config/report_layout.yaml:377-388](../../config/report_layout.yaml) lista exatamente um chart para a seção, e o [EXEMPLO_DE_RELATORIO.html:2224-2235](../plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html) — fonte de paridade visual — é igualmente raso. **Não é dívida de implementação atrasada; é blueprint sub-projetado.**

Três sintomas concretos no rendering atual:

1. **Texto quebrado em workspace sem `Risk`** (ADR-178) cadastrado: [pipeline/domain/services/narrativas/charts_narrator.py:355-368](../../pipeline/domain/services/narrativas/charts_narrator.py) concatena f-string sem guard contra `_riscos_top3 == []` nem default para `seguro_vida_minimo/maximo` — vira `"Riscos prioritários: . Ação: ... R$ 0-0M."`.
2. **Assunção de perfil vazada** — "CPA expatriado + seguro term" hardcoded ([charts_narrator.py:366](../../pipeline/domain/services/narrativas/charts_narrator.py)) trata todo cliente Mathoms como expatriado USA. Compliance FBAR/FATCA/Estate Tax só faz sentido para perfis com exposição declarada nos EUA.
3. **Cobertura ausente das categorias críticas** de proteção patrimonial — vida, invalidez, saúde, patrimonial, RC profissional, sucessório. `Risk` (ADR-178) modela **exposição/evento incerto**; não há aggregate para **apólice contratada** (capital segurado, prêmio, vigência, beneficiário).

A revisão multi-agente 2026-05-11 (`product-designer`, `financial-planner`, `senior-cto`) convergiu em três conclusões:

- a S9 atual **não entrega valor** ao cliente — é um heatmap sem ações com narrativa que vaza assunção de perfil;
- a expansão para 5 blocos (gap de proteção, cobertura por tipo, mapa re-enquadrado, sucessão, ações prioritárias) exige modelagem de apólice + bundle tipado + 5 regras de domínio (rules-as-code, ADR-143);
- separar `Risk` de `Protection` é a forma DDD-correta (ciclos de vida distintos; apólice tem vencimento, Risk não).

ADR-180 padronizou `GoalsBundle: TypedDict` exposto via `ConfigStore.get_goals_bundle()` — pipeline lê tipado sem importar `sqlalchemy`/`fastapi`/`celery` (ADR-101 R5). Replicar o padrão para proteção é a evolução natural.

## Decisão

Quatro sub-decisões coesas. Implementação faseada em 3 ondas (hotfix → MVP → completude), detalhada no [track de expansão da S9](../sprint/A11/tracks/s9-riscos-expansion.md).

### D1 — Aggregate `Protection` workspace-scoped (não inflar `Risk`)

Novo aggregate paralelo a `Risk` (ADR-178) e `Decision` (ADR-136/179):

```python
class Protection(Base):
    __tablename__ = "protections"
    id: UUID
    workspace_id: UUID                              # FK → workspaces.id
    category: Enum["vida", "invalidez", "saude",
                   "patrimonial", "rc_profissional",
                   "sucessorio"]
    holder_family_member_id: UUID | None            # FK → family_members.id
    insurer: str | None
    policy_ref: str | None                          # Fernet vault (ADR-109)
    coverage_brl_cents: BigInteger                  # capital segurado (ADR-090)
    premium_monthly_brl_cents: BigInteger | None
    starts_at: Date
    ends_at: Date | None                            # null = renovação automática
    status: Enum["Ativa", "Suspensa", "Cancelada", "Vencida"]
    notes: str | None
    created_at, updated_at
```

`Risk` (ADR-178) ganha coluna `mitigation_protection_ids: JSON` análoga ao `mitigations_decision_ids` existente — link N:N opcional declarando "esta apólice mitiga este risco". Aggregate event-sourced **não escopado** para v1 (segue precedente ADR-178: CRUD + `updated_at` basta).

### D2 — `ProtectionBundle` no `ConfigStore` Protocol (espelha ADR-180)

```python
class ProtectionBundle(TypedDict):
    policies: list[ProtectionItem]                  # apólices ativas projetadas
    gap_analysis: ProtectionGapAnalysis             # capital ideal × atual por categoria
    recommendations: list[ProtectionRecommendation] # ações sugeridas (rules-as-code D3)
    auto_inferred_risks: list[RiskInferred]         # gaps materiais detectados (D3)
    methodology_thresholds: ProtectionThresholds    # cobertura ideal por idade/PL/deps
    has_us_exposure: bool                           # gate para compliance USA (D4)
```

`ConfigStore` Protocol ganha `get_protection_bundle(workspace_id) -> ProtectionBundle`. Adapter mora em `backend/app/services/pipeline_adapter.py` (mesmo lugar de `build_goals_payload_sync`). Pipeline boundary preservado: `pipeline/**` recebe bundle tipado, não importa SQLAlchemy.

### D3 — Auto-inferência de risco via rules-as-code (ADR-143)

Novo módulo `pipeline/domain/services/protection/` com **4 calculators**
determinísticos puros (sem `@lru_cache`, ADR-111):

| Calculator | Fonte metodológica | Output |
|---|---|---|
| `life_insurance_coverage_ideal(family, debts, liquid_pl, age_brackets)` | Cerbasi + Perini (default = `max` dos dois) | `Money.brl` |
| `disability_coverage_gap(active_income_share, current_coverage, target_pct=0.6)` | Cerbasi | gap `Money.brl/mês` |
| `itcmd_estimated(state_code, gross_estate, effective_date)` | Sucessório BR (alíquotas em `fiscal_parameters` por `effective_date`) | `Money.brl` por estado |
| `compliance_risk_us_person(has_us_assets, has_us_income, us_tax_status, thresholds)` | FBAR/FATCA/Estate Tax (thresholds em `fiscal_parameters`) | lista de flags |

`emergency_reserve_target` **não** está aqui — é meta de liquidez, domínio de
`Goal` (ADR-180). Track futuro cobre.

Cada calculator emite `RiskInferred` (não persistido) quando o gap material
existir — entra no `ProtectionBundle.auto_inferred_risks`, renderizado pelo S9
com badge "auto-inferido" e CTA "Confirmar como Risco" (cria `Risk` via
`RiskRepository` ADR-178). Auto-inferência **lista branca**: apenas estes 4
calculators podem emitir; instrumentos jurídicos (holding, fideicomisso,
D&O) ficam **fora** porque exigem análise de caso (Mathoms não tem habilitação
Susep/OAB).

### D4 — Política de empty state + narrativa default segura

- **Narrador `charts_narrator._narrate_riscos_decisoes`** ganha guard early-return para `_riscos_top3 == []` emitindo copy degradada coerente + `data_state: "empty"` no payload (front diferencia "vazio" de "tudo coberto").
- **Renderer `S9RiscosSection`** trata `data_state="empty"` first-class: checklist de 6 categorias com status `✓/◑/✗/–`, alimentado por `auto_inferred_risks`, com CTA "Cadastrar apólices/riscos". **Não esconde** a seção — ausência de proteção em cliente alto-patrimônio é o risco número 1.
- **Compliance USA** entra somente quando `ProtectionBundle.has_us_exposure == True`. Flag derivada de sinais no workspace (`family_members.residencia ∈ {US_codes}` OU ativos USD > threshold OU `WorkspaceContext.us_exposure_explicit`). Default = False.
- **`config/report_layout.yaml` §S9** lista os 5 blocos novos (`hero_gap_protecao`, `cobertura_seguros`, `bubble_riscos`, `sucessao`, `acoes_mitigacao`); codegen ADR-076 (`dev/codegen_report_layout.py`) regenera `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py`.

## Alternativas consideradas

1. **Inflar `Risk` (ADR-178) com campos de apólice** — colapsa "evento incerto" com "contrato com vencimento e prêmio". Ciclos de vida distintos: Risk não tem `ends_at`, apólice sim; sinistro/renovação são eventos exclusivos de apólice. UI mistura conceitos. **Rejeitada.**
2. **JSON em `Risk.metadata` para guardar policy info** — schemaless vira data swamp; nenhuma query bound (cobertura total por workspace, apólices vencendo em 30d, gap por categoria). Perde tipagem e índices. **Rejeitada.**
3. **Sem aggregate — só rules estáticas em `pipeline/domain/services/protection/` lendo `Risk` puro** — perde tenancy da apólice (cada workspace tem N apólices reais distintas, com prêmio variável e beneficiário próprio). Não modela cobertura real, só recomendação. **Rejeitada.**
4. **`ProtectionBundle` exposto via endpoint REST chamado por subprocess do pipeline** — round-trip HTTP em path crítico; ADR-180 já rejeitou esse padrão para `GoalsBundle`. Complexidade desnecessária dado que pipeline já recebe `WorkspaceContext` via `StageConfig`. **Rejeitada.**
5. **Narrativa LLM-generated para S9 expandida** — alucinação numérica em texto financeiro é risco inaceitável; custo proibitivo por render; idempotência fere ADR-111. Determinístico continua certo para a S9. **Aceitável futuramente** como comentário interpretativo opcional com cache idempotente `(workspace_id, report_run_id, prompt_hash)` (padrão `classify_document` ADR-081), em lane separada. Fora do escopo desta ADR.

## Trade-offs explícitos

- **Ganho:** tenancy correta de apólices; gap analysis acionável em R$; auto-inferência transforma "0 riscos" em valor desde o primeiro relatório; narrativa default segura para qualquer perfil; codegen `report_layout.yaml` cobre 5 blocos; 5 rules-as-code (ADR-143) versionadas com `enforcer_modules`; bundle tipado evolui via PR (não dict shape implícito); cliente edita apólices/riscos.
- **Custo:** aggregate `Protection` (model + repo + 6 use cases + endpoints + Alembic) ~3d; bundle wiring + 5 calculators + tests ~3d; expansão `S9RiscosSection` + 5 cards novos + codegen layout ~2d; UI mínima `/protecao` ~1d; goldens E5 mudam (PR de reset dedicado se shape do `bubble_riscos.context/conclusion` for justificado). Total estimado 1-2 sprints com 1-2 agentes paralelos.
- **Risco:** **PII em logs** — `policy_ref` e `coverage_brl_cents` sensíveis. Mitigação: `policy_ref` no vault Fernet (padrão A6f.5a/ADR-109); `MathomsJsonFormatter` (ADR-110) redatado para campos sensíveis em `INFO`; raw apenas em `DEBUG`. **Risco fiduciário** — cobertura "recomendada" pode ser lida como recomendação de produto financeiro. Mitigação: disclaimer obrigatório em narrativa (`"Estimativa metodológica baseada em <Perini/Cerbasi>; não constitui recomendação fiduciária."`) e disclaimer global do relatório (Apêndice B). **Risco de paridade** — `Risk` ganhar `mitigation_protection_ids` é Alembic non-breaking, mas seed template Cerbasi (ADR-178) precisa atualização para popular o campo onde aplicável.

## Critério de aceite

- [ ] `backend/app/models/protection.py` com aggregate `Protection`, FK `workspace_id`, FK `holder_family_member_id`.
- [ ] Alembic migration: cria `protections` (índices `(workspace_id)` + `(workspace_id, status)` + `(workspace_id, category)`); adiciona `risks.mitigation_protection_ids JSON NULL`.
- [ ] Repo `ProtectionRepository` + 6 use cases em `backend/app/application/protections/` (`create`, `update`, `change_status`, `link_to_risk`, `unlink_from_risk`, `archive`).
- [ ] Endpoints `POST/GET/PATCH /protections` + `GET /workspaces/{id}/protection-bundle` com `response_model` explícito (ADR-102 R18).
- [ ] OpenAPI snapshot regenerado (`make update-openapi-snapshot`).
- [ ] `ConfigStore` Protocol ([backend/app/services/db_config_store.py](../../backend/app/services/db_config_store.py)) com método `get_protection_bundle(workspace_id) -> ProtectionBundle`.
- [ ] `pipeline/domain/services/protection/` com 5 calculators determinísticos + value objects tipados (`ProtectionInputs`, `CoverageRecommendation`, `ITCMDEstimate`) ADR-089/097.
- [ ] 5 notas Domain Rule em `docs/reference/rules/` (`life-insurance-coverage`, `emergency-reserve-target`, `disability-coverage-gap`, `itcmd-estimated`, `compliance-risk-us-person`), cada uma com `canonical_adr: [[ADR-192]]` e `enforcer_modules` no frontmatter (schema `note-domain-rule.schema.json`).
- [ ] `pipeline/domain/services/narrativas/charts_narrator.py:_narrate_riscos_decisoes` com guard para `_riscos_top3 == []` + remoção de "CPA expatriado" hardcoded; sinal `data_state` no payload.
- [ ] Teste de regressão `tests/pipeline/domain/services/narrativas/test_charts_narrator.py::test_riscos_decisoes_empty_list` afirmando que output não contém `": ."`, `"R$ 0-"` nem string fixa de perfil expatriado.
- [ ] Testes `tests/pipeline/domain/services/protection/` para os 5 calculators (3+ perfis cada: solteiro, casado com deps minoridade, expatriado USA).
- [ ] `config/report_layout.yaml` §S9 atualizado com 5 blocos (`hero_gap_protecao`, `cobertura_seguros`, `bubble_riscos`, `sucessao`, `acoes_mitigacao`) + `python3 dev/codegen_report_layout.py` re-rodado e commitado.
- [ ] `frontend/src/components/report/sections/S9RiscosSection.tsx` consome `ProtectionBundle` via codegen e renderiza 5 blocos (reuso de `ReportCard`, `PontosUrgentesCard`, `NarrativeChartCard`, `<MonetaryValue/>`).
- [ ] UI mínima de cadastro de apólice em `/protecao` (página dedicada) ou módulo expandido em `/plano` — TBD na lane S9-T05.
- [ ] Goldens E5 atualizados em PR de paridade dedicado quando shape do `bubble_riscos.context/conclusion` mudar.
- [ ] Logs estruturados (ADR-110): `mathoms.protection.*` com `policy_ref` redatado em `INFO`; assertion em teste para garantir que `coverage_brl_cents` aparece como faixa (`R$ 1-5M`) em logs, não valor exato.
- [ ] Disclaimers fiduciários em todas as narrativas/cards que citem cobertura recomendada.
- [ ] [ADR-178](178-risk-aggregate-workspace-scoped.md) ganha `relates_to: [[ADR-192]]` no frontmatter (supersedure bidirecional).
- [ ] Frontmatter validado por `dev/validate_frontmatter.py`, `dev/check_doc_filename_id.py`, `dev/check_doc_links.py`, `dev/check_adr_anchors.py`, `dev/build_doc_index.py --check`, `dev/validate_adr_format.py`.

## Plano de implementação

Lane S9-Expansion (Sprint A11.W5) — track operacional em [docs/sprint/A11/tracks/s9-riscos-expansion.md](../sprint/A11/tracks/s9-riscos-expansion.md), com 6 sub-tasks (S9-T01 hotfix → S9-T06 UI cadastro) em 3 ondas.

- **T01** ✅ mergeado em `main` em 2026-05-11 ([#212](https://github.com/davidrobert/mathoms/pull/212), commit `2ec4254`).
- **T02** ✅ mergeado no PR que carrega esta ADR como `Decidido` — entrega aggregate `Protection`, repositório, 6 use cases (`create_protection`, `get_protection`, `list_protections`, `update_protection`, `cancel_protection`, `link_to_risk` + `unlink_from_risk`), endpoints `POST/GET/PATCH/DELETE /protections` + `GET /protection-bundle`, `ProtectionBundle` TypedDict, adapter `_project_protection_bundle_sync/async`, redaction de logs e helpers PII.
- **T03–T06** aguardam pickup; track lista status atualizado.
