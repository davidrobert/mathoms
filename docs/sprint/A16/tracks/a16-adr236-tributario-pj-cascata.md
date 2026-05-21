---
id: TRACK-a16-adr236-tributario-pj-cascata
type: track
title: "Track A16 — Tributário PJ Cascata Fiscal: BusinessProfile expandido + calculator + narrator + card UI (6 PRs)"
sprint: A16
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a16
  - status/ready
  - area/methodology
  - area/pipeline
  - area/persistence
  - area/report
  - area/backend
  - area/frontend
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
---

# Track A16 — Tributário PJ Cascata Fiscal

> **Lane:** Sprint A16 (L2 de 2) · **ADR canônica:** [[ADR-236]] §"Decisão" + §"Gates" + §"Implementação"
> · **Plano canônico:** [[PLAN-tributario-pj]] (6 fases P1-P6)
> · **Branch prefix:** `agent/a16-adr236-tributario-pj-cascata-P<N>/*` (um prefixo por fase)
> · **Pré-requisito externo:** [[ADR-236]] mergeada em `main` + co-design `financial-planner` validado (Q1-Q5 em [[PLAN-tributario-pj]] §Origem)
> · **Bloqueia:** nenhuma lane downstream — L1 nu_proprietario é independente
> · **Tamanho estimado:** ~9d eng em ~2 semanas calendário · 6 PRs sequenciais (não paraleliza dentro da lane)

## Briefing

Card S8 "Tributário PJ — Cascata Fiscal" no relatório premium tem 3 problemas em 3 níveis (diagnóstico em sessão dogfood 2026-05-20):

- **N1** — Strings vazias no template (`regime_obs`, `contador_nome`, `holding_prazo` defaultam para `""`).
- **N2** — Wiring incompleto: `pipeline_adapter.build_goals_payload_sync` nunca lê `Workspace.business_profile_json` (lane A10.7 ficou pela metade) e os nomes dos campos não casam com o que o narrator espera.
- **N3** — Texto canned conceitualmente errado: mistura Simples (DAS) com Lucro Presumido (fator 32%) e afirma base PGBL = `receita_pj × 32%`, quando na verdade é renda tributável PF (Perini cap. previdência · AUVP módulo previdência · Cerbasi cap. renda variável PJ).

[[ADR-236]] decidiu **modelo de domínio expandido + cascata calculada por regime + inputs derivados ≫ declarados + decision triggers parametrizados** com 6 fases coordenadas. V1 cobre Simples (Anexo III/V) + Presumido + MEI (>95% da ICP). Lucro Real e multi-PJ ficam para V2.

**Esta lane é 6 PRs sequenciais.** Não pode ser feita em PR único — cada fase tem gates independentes (schema migration, classifier dogfood, calculator goldens, narrator regression, UI a11y, telemetria + flip).

**O que esta lane NÃO faz** (escopo explícito):

- Lucro Real e multi-PJ por workspace ([[ADR-236]] §Não-objetivos).
- Reforma tributária / PEC dividendos (ADR de schema evolution quando aprovar).
- Holding patrimonial — gatilhos completos. V1 implementa só T4 (≥3 imóveis alugados).
- Hot-fix paralelo de esconder/encurtar card no meio-tempo — descartado pelo usuário em favor da solução completa. Card permanece errado em prod ~2 semanas até P4.

## Decisões já fechadas (do co-design `financial-planner` 2026-05-20 · [[ADR-236]])

- **Base PGBL** = soma da ficha "Rendimentos Tributáveis" do IRPF (pró-labore + aluguéis + outras tributáveis). **Não** `receita_pj × 32%`. Não reabrir.
- **Inputs derivados ≫ declarados** — pró-labore, lucros, folha, das, ISS, receita PJ e renda tributável PF saem de E3/E4/E1.6. Só `anexo_simples`, `iss_aliquota_pct`, `cnae_principal`, `tipo_declaracao_ir` ficam em `BusinessProfile`.
- **Fator-R derivado**, não declarado. Calculator computa `(folha + pró-labore) × 12 / receita_pj_anual`.
- **5 decision triggers** canônicos com break-even explícito ([[ADR-236]] §D6). Folclore rejeitado (holding por patrimônio absoluto, anuização via lucros isentos no teto Simples).
- **Linha CRC** — copy "considere avaliar" / "sinal de atenção" / "oportunidade"; nunca "você deve" / "recomendamos". Disclaimer obrigatório no rodapé do card.
- **Lucro Real fora de V1** — workspace com `regime=lucro_real` renderiza estado "regime não suportado" + CTA suporte. Não inventa.
- **Hot-fix descartado** — card mentiroso em prod ~2 semanas é trade-off aceito.

## Critério de aceite — por fase

### P1 — `BusinessProfile` expandido + UI captura (~1d, 1 PR)

- [ ] Migration Alembic `backend/alembic/versions/<hash>_adr236_business_profile_expanded.py`:
  - `upgrade()`: `business_profile_json` JSONB ganha 4 chaves novas via Pydantic `extra=forbid`. Workspaces existentes ficam com `None` até consultor preencher.
  - `downgrade()`: reversível (Pydantic relaxa para o schema A10.7).
- [ ] `backend/app/schemas/business_profile.py` — `BusinessProfile` adiciona `anexo_simples`, `iss_aliquota_pct`, `cnae_principal`, `tipo_declaracao_ir` com `model_config={"extra":"forbid"}` ([[ADR-236]] §D1 code block).
- [ ] Endpoint PATCH `/workspaces/{id}/business-profile` — `response_model=BusinessProfileResponse` ([[ADR-102]] R18). `make update-openapi-snapshot` commitado.
- [ ] UI captura no console interno (`ops.mathoms.ai`, [[ADR-116]]) — form com validação Pydantic-side.
- [ ] Tests: `backend/tests/test_business_profile.py` cobre cada Literal/range; `backend/tests/api/test_business_profile_patch.py` cobre o endpoint.
- [ ] Workspace incompleto degrada graciosamente (sem campo, sem crash; UI mostra estado "perfil pendente").

### P2 — Derivação do pipeline (E3/E4/E1.6) (~2d, 1 PR)

- [ ] `category_template` ganha 5 labels novas: `pro_labore`, `lucros_distribuidos`, `das_simples`, `folha_pj`, `iss`. Migration Alembic.
- [ ] Discriminadores estruturais no classifier E4:
  - `pro_labore` — origem `account_type=PJ` + destino `member_key=titular_pj` + descrição contém variantes ("PRO-LABORE", "PROLABORE", "PRO LABORE").
  - `lucros_distribuidos` — origem `account_type=PJ` + destino `member_key=titular_pj` que **não** matched `pro_labore` (resíduo).
  - `das_simples` — descrição com "DAS" + débito de conta PJ.
  - `folha_pj` — pagamento a `member_key` ≠ titular_pj (CLT).
  - `iss` — descrição com "ISS" + débito de conta PJ (só relevante em Presumido).
- [ ] Leitor de `outras_rendas_tributaveis_pf_anual` via `extract_irpf_full` artifact ([[ADR-157]]) — soma da ficha "Rendimentos Tributáveis" (códigos relevantes a confirmar com `financial-planner` se necessário; lista canônica: aluguéis, salários CLT, RPA, ganhos tributáveis).
- [ ] Gate dogfood: workspace `5@5.com` (ou equivalente) — E4 classifica 100% das transferências PJ→sócio em `pro_labore` vs `lucros_distribuidos`; total bate com IRPF declarado (±5%).
- [ ] Tests:
  - `tests/test_e4_classifier.py::test_pro_labore_vs_lucros_distribuidos_disambiguation`
  - `tests/test_e4_classifier.py::test_folha_pj_excludes_titular_pj`
  - `tests/test_irpf_renda_tributavel_extraction.py` (novo)

### P3 — Calculator canônico (~2d, 1 PR)

- [ ] `pipeline/domain/services/tributario/cascata_calculator.py` puro ([[ADR-097]] boundary; sem `fastapi`/`sqlalchemy`/`celery`).
- [ ] Implementa `CascataInput` + `CascataOutput` + `compute()` conforme [[ADR-236]] §D3.
- [ ] Cobre 4 regimes V1:
  - Simples Anexo III (alíquota inicial 6%, faixa RBT12 progressiva).
  - Simples Anexo V (alíquota inicial 15,5%, faixa RBT12 progressiva).
  - Lucro Presumido (PIS 0,65% + COFINS 3% + ISS destacado + IRPJ 15% sobre presunção 32% + adicional 10% no que exceder R$60k/trim + CSLL 9% sobre presunção 32%).
  - MEI (DAS fixo + teto R$ 81k).
- [ ] Lucro Real retorna `CascataOutput` mínimo com flag `regime_nao_suportado=True` + razão.
- [ ] Fator-R derivado: `(folha + pro_labore) × 12 / receita_pj_anual × 100`. Break-even computado (quanto subir folha pra mudar Anexo).
- [ ] Base PGBL = `outras_rendas_tributaveis_pf_anual + pro_labore_anual_tributavel`. Flag `pgbl_aplicavel=False` se `tipo_declaracao_ir=simplificada`, com `pgbl_motivo_inaplicavel="declaracao_simplificada"`.
- [ ] 5 decision triggers conforme [[ADR-236]] §D6 (T1-T5) com break-even computado, não copy genérico.
- [ ] Tests:
  - 4 goldens em `tests/test_cascata_calculator.py` — 1 por regime + 1 com workspace incompleto.
  - `tests/test_cascata_calculator.py::test_pgbl_base_is_renda_tributavel_pf_not_receita_pj_times_32pct` — gate explícito da N3 da ADR.
  - `tests/test_cascata_calculator.py::test_simplificada_anula_pgbl`
  - `tests/test_cascata_calculator.py::test_triggers_break_even_computed` — todos triggers têm campo `break_even` calculado.
  - `tests/test_cascata_calculator.py::test_no_holding_trigger_by_absolute_patrimonio` — gate explícito anti-folclore.
- [ ] Gate manual: paridade ±2% com cálculo do contador real do dogfood `5@5.com`.

### P4 — Adapter + narrator reescrito (~1d, 1 PR)

- [ ] `backend/app/services/pipeline_adapter.py::build_goals_payload_sync` (e versão async) — chama `cascata_calculator.compute(...)` e injeta `bundle["tributario"]` conforme [[ADR-236]] §D4.
- [ ] Pydantic model `TributarioBundleSection` valida shape no boundary (gate `tests/test_pipeline_adapter.py::test_tributario_section_shape`).
- [ ] `pipeline/domain/services/narrativas/charts_narrator.py::impostos_pj` reescrito — método `_narrate_cascata(M, ctx)` que ramifica por `regime`.
- [ ] Workspace sem `BusinessProfile` completo → narrator retorna estado "perfil tributário pendente". Não inventa.
- [ ] **Regression test obrigatório:** `tests/test_charts_narrator.py::test_impostos_pj_no_hardcoded_lucro_presumido` — string `"Lucro presumido (32%)"` não pode aparecer no output de nenhum workspace simples. **Este é o gate de remoção da N3.**
- [ ] Tests:
  - `tests/test_charts_narrator.py::test_impostos_pj_branches_by_regime` (4 ramos + incompleto).
  - `tests/test_charts_narrator.py::test_impostos_pj_no_hardcoded_lucro_presumido` (gate N3).
  - `tests/test_pipeline_adapter.py::test_tributario_section_shape`.

### P5 — `<CascataFiscalCard/>` UI (~2d, 1 PR)

- [ ] `frontend/src/components/report/CascataFiscalCard.tsx` — componente novo seguindo design tokens (sem hex literal; usar `var(--brand-*)`, `var(--surface-*)`, `var(--semantic-*)`).
- [ ] Conteúdo mínimo V1 conforme [[ADR-236]] §D5:
  - Header com regime + label completa + badge fator-R (quando aplicável).
  - Cascata em camadas (waterfall ou steps verticais).
  - Bloco "Base PGBL" separado com flag amarela quando `tipo_declaracao_ir=simplificada`.
  - Decision triggers como callouts (0-5).
  - Disclaimer obrigatório no rodapé.
- [ ] Substitui `<NarrativeChartCard chartId="impostos_pj"/>` em `frontend/src/components/report/sections/S8PrevidenciaSection.tsx`.
- [ ] Todos os valores monetários via `<MonetaryValue/>` (font-mono + tabular-nums).
- [ ] Co-design `product-designer` — 1 rodada de revisão de layout + copy antes de merge.
- [ ] Co-design `financial-planner` — 1 rodada de revisão final do copy (gates de linha CRC: "considere avaliar" vs "recomendamos").
- [ ] Tests:
  - `frontend/src/components/report/CascataFiscalCard.test.tsx` — render por regime; estado "perfil pendente"; estado `regime_nao_suportado`.
  - A11y: axe-core (zero violations) + Lighthouse a11y ≥ 95.
  - Mobile: cards stackam, fator-R badge wrap, callouts full-width.
  - E2E `@critical` em `frontend/playwright/`: workspace dogfood `/reports/<id>` renderiza Cascata Fiscal com decomposição esperada.
- [ ] Visual snapshot regression atualizado (light + dark).
- [ ] Dogfood: 2 famílias confirmam (a) números batem com IRPF/DAS real, (b) decision triggers fazem sentido.

### P6 — Cutover + telemetria + flip ADR (~1d, 1 PR)

- [ ] Sunset do código canned em `charts_narrator` — texto livre vira mínimo (`_narrate_cascata` ramifica + estado "pendente"). Remover dead-code path.
- [ ] Telemetria estruturada em `backend/app/core/logging.py`:
  - `mathoms.tributario.cascata_rendered` — campos: `regime`, `has_complete_profile`, `triggers_count`.
  - `mathoms.tributario.trigger_shown` — campos: `trigger_code` (T1-T5), `regime`.
  - `mathoms.tributario.profile_incomplete` — campos: `missing_fields[]`.
  - **Gate LGPD obrigatório:** `tests/test_telemetria_lgpd.py::test_tributario_no_money_in_logs` — denylist de campos monetários e identificadores PJ/CNPJ. Zero valores monetários nos logs.
- [ ] FAQ produto: entrada nova sobre "como calcular cascata fiscal" + "por que PGBL diferente do que outras planilhas falam" (linkado da ADR).
- [ ] Flip [[ADR-236]]: `status: Proposto` → `Decidido`; adicionar `decided_at: "<data-merge>"`; tag `status/proposto` → `status/decidido`.
- [ ] Entrada [docs/CHANGELOG.md](../../../CHANGELOG.md) citando ADR-236 + sprint A16.
- [ ] `python3 dev/build_doc_index.py --inline` regenera `_generated/`.
- [ ] Sprint A16 `_README.md` flippa `sprint_status: current → done` no merge **quando L1 também tiver fechado** (sprint multi-lane fecha quando ambas lanes terminam).
- [ ] Track flippa `status: ready → consumed` + `consumed_at: "<data>"`.

## Arquivos esperados

### Novos

- `pipeline/domain/services/tributario/__init__.py`
- `pipeline/domain/services/tributario/cascata_calculator.py`
- `frontend/src/components/report/CascataFiscalCard.tsx`
- `frontend/src/components/report/CascataFiscalCard.test.tsx`
- `backend/alembic/versions/<hash>_adr236_business_profile_expanded.py`
- `backend/alembic/versions/<hash>_adr236_category_template_pj_labels.py`
- `tests/test_cascata_calculator.py` (4 goldens + gates)
- `tests/test_irpf_renda_tributavel_extraction.py`
- `tests/test_telemetria_lgpd.py` (extensão para tributário)
- E2E spec novo em `frontend/playwright/<file>.spec.ts`

### Editados

- `backend/app/schemas/business_profile.py`
- `backend/app/services/pipeline_adapter.py`
- `backend/app/api/workspaces.py` (PATCH /business-profile já existe; pode precisar extensão)
- `pipeline/domain/services/narrativas/charts_narrator.py`
- `pipeline/domain/goals_bundle.py` (TypedDict ganha `TributarioBundleSection` tipado)
- `frontend/src/components/report/sections/S8PrevidenciaSection.tsx`
- `frontend/src/generated/openapi.json` (regen)
- `backend/app/core/logging.py` (telemetria + denylist LGPD)
- `docs/adr/236-tributario-pj-cascata-fiscal-canonica.md` (flip Proposto → Decidido no P6)
- `docs/CHANGELOG.md`
- `docs/sprint/A16/_README.md` (flip do sprint quando L1+L2 terminarem)
- `docs/sprint/A16/tracks/a16-adr236-tributario-pj-cascata.md` (este arquivo — flip ready → consumed no P6)

## Testes (comandos exatos por fase)

```bash
# P1 — BusinessProfile + endpoint
pytest backend/tests/test_business_profile.py -q
pytest backend/tests/api/test_business_profile_patch.py -q
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# P2 — Classifier E4 + IRPF
pytest tests/test_e4_classifier.py -q
pytest tests/test_irpf_renda_tributavel_extraction.py -q
# Gate dogfood: workspace 5@5.com — confirmar manual

# P3 — Calculator
pytest tests/test_cascata_calculator.py -q  # 4 goldens + gates
# Paridade ±2% com contador real — gate manual

# P4 — Adapter + narrator
pytest backend/tests/test_pipeline_adapter.py -q
pytest tests/test_charts_narrator.py -q

# P5 — UI
cd frontend && npm test -- --run CascataFiscalCard
cd frontend && npm run test:e2e -- --grep @critical
# axe-core + Lighthouse — gate manual

# P6 — Telemetria + flip
pytest tests/test_telemetria_lgpd.py -q

# Cross-stack (sempre)
pre-commit run --all-files
python3 dev/validate_frontmatter.py
python3 dev/check_doc_links.py
python3 dev/build_doc_index.py --check
make update-openapi-snapshot
```

## Riscos

- **R1 · Classifier E4 confunde pró-labore com salário CLT do cônjuge** (P2) — Mitigação: discriminador estrutural exige `member_key=titular_pj` + `account_type=PJ` na origem. Teste com workspace multi-membro obrigatório.
- **R2 · Workspace sem IRPF processado — base PGBL = 0 mesmo com renda real** (P3) — Mitigação: estado UI explícito "renda tributável PF não detectada — sem IRPF processado"; CTA upload IRPF. Não infere base PGBL de pró-labore apenas (sub-estima quando há aluguéis).
- **R3 · Fator-R cai por sazonalidade (férias coletivas) e gera trigger T2 falso** (P3/P4) — Mitigação: janela 12m móvel suaviza; copy "fator-R móvel 12m" deixa premissa explícita; threshold "proximidade < 5pp" só dispara T2 se persiste 3 meses.
- **R4 · LGPD — telemetria de carga tributária vaza** (P6) — Mitigação: `tests/test_telemetria_lgpd.py::test_tributario_no_money_in_logs` é gate hard; denylist de campos. Risco P0 mas controlado por gate.
- **R5 · Decision trigger T1 ("subir pró-labore") mal-calibrado gera dívida fiscal** (P3/P5) — Mitigação: copy patterns obrigatórios + disclaimer + threshold conservador (T1 só dispara se base PGBL < 80% do limite potencial). Co-design `financial-planner` em P5 valida copy final.
- **R6 · Workspace com `regime=lucro_real` (fora do escopo V1) vê card vazio sem explicação** (P3/P4/P5) — Mitigação: `regime_nao_suportado=True` no `CascataOutput` propaga até UI; card renderiza "Lucro Real — cascata em desenvolvimento (V2)" + CTA suporte.
- **R7 · Card mentiroso em produção ~2 semanas até P4 shipping** — Aceito pelo usuário 2026-05-20 (escolha de solução completa sem hot-fix). Mitigação: P1-P4 priorizados sobre P5/P6 cosméticos.
- **R8 · Adapter regression — `bundle["tributario"]` chega com shape errado e narrator quebra** (P4) — Mitigação: Pydantic `TributarioBundleSection` no boundary; teste de shape.

## Subagentes a consultar (apenas se desviar do plano)

A ADR-236 + co-design 2026-05-20 já fecharam decisões críticas. **Não delegue rotineiramente** — apenas se aparecer:

- **Mudança em modelagem de DB além do que ADR define** → `data-engineer`.
- **Mudança no calculator/regime além do que ADR define** → `senior-cto` + `financial-planner` em paralelo (decisões metodológicas).
- **Copy do card / decision triggers vira polêmica** → `product-designer` (P5) + `financial-planner` (revisão final P5).
- **Mudança em parecer LLM E6 sobre tributário** → `financial-planner` (não esta lane, mas FU possível).
- **Folclore aparece em PR** (gatilho de "holding por patrimônio absoluto" ou "anuização via lucros isentos no teto Simples") → `financial-planner` rejeita explicitamente.

Caso contrário, execute o plano direto seguindo [[ADR-236]] + [[PLAN-tributario-pj]].

## Ligações

- **ADR canônica:** [[ADR-236]]
- **Plano canônico:** [[PLAN-tributario-pj]]
- **Sprint MOC:** [[MOC-sprint-a16]]
- **Lane irmã (independente):** [[TRACK-a16-adr235-nu-proprietario-flip]] (L1)
- **ADRs relacionadas:** [[ADR-143]] (rules-as-code) · [[ADR-157]] (extract_irpf_full E1.6) · [[ADR-180]] (GoalsBundle) · [[ADR-097]] (boundary pipeline↔backend) · [[ADR-102]] (response_model R18) · [[ADR-129]] (HTML server-side descontinuado) · [[ADR-186]] (override sticky) · [[ADR-229]] (artifact → suggestion pattern, V2 cascata snapshots) · [[A10.7]] (BusinessProfile minimal origem)
- **Co-design:** `financial-planner` 2026-05-20 — 5 Q&A validadas em [[PLAN-tributario-pj]] §Origem + [[ADR-236]] §Decisão.
- **Caso real de gatilho:** workspace dogfood (sessão 2026-05-20) — card S8 com lacunas literais ("enquadrada no  ("), texto canned errado ("Lucro presumido 32% define base PGBL"), `bundle["tributario"]` nunca propagado.
- **Referências metodológicas:** Perini "Viver de Renda" cap. previdência privada · AUVP módulo previdência · Cerbasi "Como organizar sua vida financeira" cap. renda variável PJ.
