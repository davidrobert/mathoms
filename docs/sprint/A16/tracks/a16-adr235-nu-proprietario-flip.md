---
id: TRACK-a16-adr235-nu-proprietario-flip
type: track
title: "Track A16 — Flip ADR-235 `nu_proprietario` para Decidido (migration + call-sites + ADR updates + E6 prompt + CI gate)"
sprint: A16
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a16
  - status/ready
  - area/db
  - area/backend
  - area/pipeline
  - area/frontend
  - area/methodology
---

# Track A16 — Flip ADR-235 `nu_proprietario`

> **Lane:** Sprint A16 (única) · **ADR canônica:** [[ADR-235]] §"Plano de implementação" + §"Critério de aceite"
> · **Branch prefix:** `agent/a16-adr235-nu-proprietario-flip/*`
> · **Pré-requisito externo:** [[ADR-235]] mergeada em `main` ([apps#382](https://github.com/davidrobert/mathoms/pull/382))
> · **Bloqueia:** nenhuma lane downstream — sprint A16 tem 1 lane só
> · **Tamanho estimado:** 1–1,5d eng (migration trivial, mas cross-stack: backend + pipeline + frontend + prompt LLM)

## Briefing

[[ADR-235]] decidiu adicionar `nu_proprietario` ao enum `classification` para cobrir imóvel em nu-propriedade com usufruto vitalício de terceiro (cliente é dono, antigo proprietário mora gratuitamente, consolidação plena no falecimento). Comporta-se como `uso_pessoal` em todos os filtros computacionais (não-gerador, fora de cap rate, fora de `investivel_efetivo`), mas é **entidade semântica distinta** para relatório, parecer LLM (E6 · [[ADR-199]]) e diagnóstico de liquidez.

**Esta lane é o PR único de Decidido.** Migration + 6 call-sites + 4 ADR updates + prompt E6 + CI gate + testes + flip frontmatter ADR — tudo num PR coeso (cross-doc invariants exigem atomic merge; split produz peças órfãs).

**O que esta lane NÃO faz** (escopo explícito):

- Captura de `expected_extinction_year`, `valor_mercado_consolidado`, alertas de extinção, tábua atuarial — FU pós-A16.
- Sub-bucket "Patrimônio ilíquido condicional" como categoria nova em [[ADR-145]] — rejeitado pela ADR (cat_2 não-gerador absorve).
- Heurística de aviso de seguro de vida no parecer E6 — FU-2 (heurística baseada em `nu_proprietario` + dependentes); esta lane só atualiza o prompt para **não recomendar venda**.

## Decisões já fechadas (do co-design 2026-05-20 · [[ADR-235]])

- **Opção A escolhida** (novo valor de enum) vs B (flag ortogonal) vs C (só docs). Rationale em [[ADR-235]] §"Alternativas consideradas". Não reabrir.
- **Categoria:** cat_2 **não-gerador**. Não criar categoria nova em [[ADR-145]].
- **Filtros computacionais:** paridade total com `uso_pessoal` — fora de `INVESTMENT_CLASSIFICATIONS`, fora de `_CLASSIFICATIONS_GERADORAS`, fora de `investivel_efetivo` (invariante adicionado a [[ADR-142]]).
- **Cap rate:** indefinido para nu-propriedade (não puxa média do portfolio pra baixo — fica fora do denominador).
- **Migration:** drop + recreate CHECK em 2 tabelas (Postgres não permite editar in-place). Sem backfill. Down valida pre-down (raise se houver row com `nu_proprietario`).
- **Posição no enum:** após `especulacao`, antes de `desconhecido` — ordem semântica (residência/uso → renda → improdutivo → ônus civil → default).
- **Label UI:** "Nu-propriedade (usufruto vitalício)" + tooltip explicando consolidação futura. Texto sugerido do tooltip: "Você é dono, mas outro detém usufruto vitalício e ocupa o imóvel gratuitamente. Está no seu patrimônio, mas não gera caixa nem está disponível para venda livre. Pode virar `locado` ou ser vendido livremente quando o usufruto extinguir."

## Critério de aceite

### 1. Migration Alembic

- [ ] `backend/alembic/versions/<hash>_adr235_nu_proprietario.py`
  - `upgrade()`: drop + recreate `chk_classification_enum` em `property_identity` **e** `chk_classification` em `workspace_property_overrides` incluindo `nu_proprietario`. SQL idêntico para ambas as tabelas (mesma lista de valores).
  - `downgrade()`: **pre-down guard** — `SELECT COUNT(*) FROM property_identity WHERE classification='nu_proprietario'` + idem para overrides; raise `RuntimeError` se >0 (evita data loss silencioso). Recriar CHECK sem `nu_proprietario`.
- [ ] Test integration: `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` limpo.
- [ ] Test pre-down guard: insert row com `nu_proprietario`, `alembic downgrade -1` **deve falhar**; delete row, downgrade **deve passar**.

### 2. Backend models + enum

- [ ] `backend/app/models/property_identity.py` — adicionar `CLASSIFICATION_NU_PROPRIETARIO = "nu_proprietario"`; estender Literal/Enum (linha 31 atual + linha 104 CHECK constraint comment).
- [ ] `backend/app/models/workspace_property_override.py` (se existir como model separado) — mesma extensão.

### 3. Pipeline classifier

- [ ] `pipeline/domain/services/patrimonio_imovel_classifier.py:19` — adicionar `CLASSIFICATION_NU_PROPRIETARIO`.
- [ ] **Não** entra em `_CLASSIFICATIONS_GERADORAS` (paridade com `uso_pessoal`/`especulacao`/`desconhecido`).
- [ ] Comentário linha 24 (`uso_pessoal | especulacao | desconhecido nunca entram`) — estender para incluir `nu_proprietario`.

### 4. Pipeline real_estate

- [ ] `pipeline/domain/services/real_estate_metrics.py:14` — adicionar `"nu_proprietario"` à tuple de valores válidos (input validation).
- [ ] `pipeline/domain/services/real_estate_metrics.py:18` — `INVESTMENT_CLASSIFICATIONS` permanece sem `nu_proprietario` (confirma fora do cap rate).

### 5. Backend real_estate adapter

- [ ] `backend/app/services/real_estate_adapter.py:131,156,169` — literais `("locado", "comercial", "especulacao")` permanecem inalterados; `nu_proprietario` cai no else (`origin="none"`, `aluguel_anual=None`). Comportamento idêntico a `uso_pessoal`.

### 6. Frontend types + UI

- [ ] `frontend/src/lib/api/properties.ts:10` — adicionar `| "nu_proprietario"` ao union type `Classification`.
- [ ] `frontend/src/app/(app)/config/ResidenciaSection.tsx`:
  - Linha 18-25 — adicionar `nu_proprietario: "Nu-propriedade (usufruto vitalício)"` ao `CLASSIFICATION_LABELS`.
  - Linha ~269 — adicionar `<option value="nu_proprietario">Nu-propriedade (usufruto vitalício)</option>` ao dropdown.
  - Tooltip `title=` ou popover com texto fechado em §"Decisões já fechadas".

### 7. Parecer LLM E6 ([[ADR-199]])

- [ ] Prompt em `config/prompts/parecer_planejador.yaml` (ou caminho equivalente — verificar): adicionar bullet ao contexto sobre classifications: "`nu_proprietario` é ativo ilíquido por contrato civil (usufruto vitalício de terceiro). **Não recomende venda** como solução de liquidez. Mencione que liquidez chegará via consolidação plena quando o usufruto extinguir."
- [ ] Bump `PROMPT_VERSION` em `parecer_planejador.yaml` (gate W2-T05 · [[ADR-233]]).
- [ ] Atualizar golden de teste E6 cobrindo cenário `nu_proprietario` (workspace fixture com 1 imóvel classificado).
- [ ] Atualizar eval (se houver suite de eval LLM em [[ADR-199]] família).

### 8. ADRs adjacentes (atualizadas no mesmo PR)

- [ ] [[ADR-215]] §1 — estender lista do enum incluindo `nu_proprietario` com definição operacional ("nu-propriedade com usufruto vitalício de terceiro").
- [ ] [[ADR-142]] — adicionar invariante explícito: "`nu_proprietario` **nunca** entra em `investivel_efetivo`, independente do toggle `imoveis_no_if`".
- [ ] [[ADR-145]] — documentar nu-propriedade em cat_2 **não-gerador** (alinhado com `uso_pessoal`/`especulacao`).
- [ ] [[ADR-216]] — explicitar que `nu_proprietario` está fora do denominador de cap rate (cap rate indefinido, não zero).
- [ ] Flip [[ADR-235]]: `status: Proposto` → `Decidido`; adicionar `decided_at: "<data-merge>"`; tag `status/proposto` → `status/decidido`.

### 9. CI gate

- [ ] `dev/check_classification_exhaustive.py` novo — varre TS + Python procurando `switch (classification)` / `match classification:` sem branch default; falha se encontrar para forçar atualização explícita em mudanças futuras do enum.
- [ ] Registrar hook em `.pre-commit-config.yaml`.
- [ ] Auto-test do script: positive case (switch sem default raises), negative case (com default passa).

### 10. Testes regressivos

- [ ] `tests/unit/pipeline/test_split_imoveis_with_overrides.py` — adicionar caso: imóvel classificado `nu_proprietario` vai para `imoveis_outros` (não-gerador).
- [ ] `tests/test_real_estate_metrics.py` — `nu_proprietario` **não** está em `INVESTMENT_CLASSIFICATIONS`; cap rate ignora.
- [ ] `tests/unit/pipeline/test_patrimonio_calculator.py::test_investivel_efetivo_exclui_uso_pessoal_e_especulacao_sempre` — estender para incluir `nu_proprietario` no fixture; renomear para `test_investivel_efetivo_exclui_nao_geradores_sempre` (semântica clara).
- [ ] `backend/tests/models/test_property_identity_constraints.py` (ou test equivalente) — insert com `classification='nu_proprietario'` passa; insert com `classification='xxxx'` raises.
- [ ] Frontend Vitest — snapshot do dropdown inclui nova opção; teste de submit/round-trip do novo valor via API client.
- [ ] **E2E `@critical`** em `frontend/playwright/`: usuário em `/config?tab=members` muda classification de imóvel para `nu_proprietario` → relatório (`/reports/<id>`) reflete cat_2 não-gerador, fora de cap rate (S4 Real Estate empty state ou imóvel ausente do denominador), fora de IF.

### 11. Snapshot + changelog + close-out

- [ ] `make update-openapi-snapshot` rodado; diff commitado.
- [ ] Entrada em [docs/CHANGELOG.md](../../../CHANGELOG.md) citando ADR-235 + sprint A16.
- [ ] `python3 dev/build_doc_index.py --inline` para regen `_generated/`.
- [ ] Sprint A16 `_README.md` flippa `sprint_status: paused → done` no merge.
- [ ] Track flippa `status: ready → consumed` + `consumed_at: "<data>"`.

## Arquivos esperados

**Novos:**

- `backend/alembic/versions/<hash>_adr235_nu_proprietario.py`
- `dev/check_classification_exhaustive.py`
- `backend/tests/models/test_property_identity_nu_proprietario.py` (ou test equivalente)
- Frontend E2E: `frontend/playwright/<file>.spec.ts` (cenário novo ou extensão de existente)

**Editados:**

- `backend/app/models/property_identity.py`
- `backend/app/models/workspace_property_override.py` (se existir)
- `pipeline/domain/services/patrimonio_imovel_classifier.py`
- `pipeline/domain/services/real_estate_metrics.py`
- `frontend/src/lib/api/properties.ts`
- `frontend/src/app/(app)/config/ResidenciaSection.tsx`
- `config/prompts/parecer_planejador.yaml` (ou path equivalente)
- `tests/unit/pipeline/test_split_imoveis_with_overrides.py`
- `tests/unit/pipeline/test_patrimonio_calculator.py`
- `tests/test_real_estate_metrics.py`
- `.pre-commit-config.yaml`
- `docs/adr/235-nu-proprietario-usufruto-vitalicio-de-terceiro.md` (flip Proposto → Decidido)
- `docs/adr/215-classificacao-imoveis-override-db-first.md` (extensão enum §1)
- `docs/adr/142-toggle-imoveis-no-if-em-pipelinejson-invariante.md` (invariante)
- `docs/adr/145-formulas-canonicas-de-composicao-patrimonial.md` (cat_2 não-gerador)
- `docs/adr/216-stage-extrair-informe-de-rendimento-de-imoveis-e-cap-rate-real-estate.md` (fora cap rate)
- `docs/sprint/A16/_README.md` (flip paused → done)
- `docs/sprint/A16/tracks/a16-adr235-nu-proprietario-flip.md` (flip ready → consumed)
- `docs/CHANGELOG.md`
- `frontend/src/generated/openapi.json` (regen)
- `docs/_MOC/_generated/*` (regen)

## Testes (comandos exatos)

```bash
# Migration
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest backend/tests/test_alembic.py -q

# Backend models + constraints
pytest backend/tests/models/test_property_identity_nu_proprietario.py -q

# Pipeline domain
pytest tests/unit/pipeline/test_split_imoveis_with_overrides.py -q
pytest tests/unit/pipeline/test_patrimonio_calculator.py -q
pytest tests/test_real_estate_metrics.py -q

# Paridade geral
pytest backend/tests -q
pytest tests -q

# Frontend unit + types
cd frontend && npm test -- --run
cd frontend && npx tsc --noEmit

# E2E @critical
cd frontend && npm run test:e2e -- --grep @critical

# OpenAPI snapshot
make update-openapi-snapshot

# Doc gates
python3 dev/validate_frontmatter.py
python3 dev/check_doc_links.py
python3 dev/check_adr_anchors.py
python3 dev/build_doc_index.py --check

# Novo CI gate
python3 dev/check_classification_exhaustive.py

# Pre-commit completo
pre-commit run --all-files
```

## Riscos

- **R1 · Schema evolution downstream** ([[ADR-188]]) — readers exhaustive (TS `never`, Python `match`) podem quebrar. Auditoria prévia ([[ADR-235]] §"Riscos"): backend usa whitelist literal `in (...)`, frontend sem `switch` exhaustive sobre `Classification`. Mas dependências indiretas (codegen, libs) podem fechar exhaustive sem você saber — rode `cd frontend && npx tsc --noEmit` antes de commit. Mitigação proativa: o novo CI gate `check_classification_exhaustive.py` previne regressões.
- **R2 · Migration down em produção** — workspace que adotou `nu_proprietario` bloqueia rollback (pre-down guard raises). É comportamento desejado (evita data loss silencioso), mas exige runbook claro. Documente em [docs/reference/runbooks/](../../../reference/runbooks/) (criar novo arquivo ou estender existente): "Antes de revert ADR-235, UPDATE rows `nu_proprietario` → `uso_pessoal` no DB; só então `alembic downgrade`."
- **R3 · Prompt E6 sem golden atualizado regride parecer** — se não bumpar `PROMPT_VERSION` + atualizar golden, eval LLM pode passar com regressão silenciosa. Gate W2-T05 ([[ADR-233]]) detecta bump faltando, mas golden é responsabilidade do dev. Cenário fixture obrigatório no critério de aceite §7.
- **R4 · Label/tooltip UI inadequado** — copy técnico ("nu-propriedade", "usufruto vitalício") é jurídico, pode confundir usuário leigo. Texto sugerido em §"Decisões já fechadas" tenta balancear precisão e clareza. Se houver objeção do `product-designer`, **1 rodada de ajuste** no copy antes de mergear (não bloqueia merge se texto razoável; perfectionism aqui é YAGNI).
- **R5 · Dropdown comportamento desktop vs mobile** — `ResidenciaSection.tsx` é tela densa em mobile. Verifique rendering em ≤375px width antes de mergear; se quebrar, ajuste ou eleve para `<select>` nativo no breakpoint pequeno.

## Subagentes a consultar (apenas se desviar do plano)

A ADR já fechou as decisões críticas. **Não delegue rotineiramente** — apenas se aparecer:

- **Mudança em modelagem de DB** (não prevista) → `data-engineer`.
- **Mudança no enum além do que ADR define** → `senior-cto`.
- **Copy do tooltip vira polêmica** → `product-designer` (1 rodada).
- **Comportamento em parecer LLM diverge do que ADR-199 fixa** → `financial-planner` + `senior-cto` em paralelo.

Caso contrário, execute o plano direto.

## Ligações

- **ADR canônica:** [[ADR-235]]
- **Sprint MOC:** [[MOC-sprint-a16]]
- **ADRs relacionadas:** [[ADR-142]] (toggle IF) · [[ADR-145]] (categorias canônicas) · [[ADR-186]] (override pattern) · [[ADR-188]] (schema evolution) · [[ADR-199]] (parecer LLM) · [[ADR-215]] (enum classification base) · [[ADR-216]] (cap rate) · [[ADR-225]] (codigo_rfb invariante) · [[ADR-227]] (debt + property_market_value — base para FU-1 futuro) · [[ADR-233]] (PROMPT_VERSION gate)
- **PR de Proposto (pré-requisito):** [apps#382](https://github.com/davidrobert/mathoms/pull/382)
- **Pattern reuso:** [`backend/alembic/versions/adr215residencia1_property_overrides_residencia_status.py`](../../../../backend/alembic/versions/adr215residencia1_property_overrides_residencia_status.py) — migration de CHECK constraint do enum classification original (template para esta migration)
- **Caso real de gatilho:** workspace dogfood `98432212-9624-4405-a951-803efee62b34` (cliente nu-proprietário com usufruto vitalício de terceiro, sessão 2026-05-20)
