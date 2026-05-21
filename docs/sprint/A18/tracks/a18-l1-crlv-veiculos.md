---
id: TRACK-a18-l1-crlv-veiculos
type: track
title: "Track A18 L1 — CRLV-e: tabela canônica vehicles + classifier + stage extract_comprovantes_bens + reconciliação assíncrona"
lane: "[[A18.l1]]"
sprint: A18
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a18
  - status/ready
  - area/pipeline
  - area/persistence
  - area/backend
---

# Track A18 L1 — CRLV-e (Comprovante de Bem · Veículo)

> **Lane:** [[A18.l1]] · **ADR canônica:** [[ADR-239]] §D1-D9 + §Gates + §Implementação
> · **Branch prefix:** `agent/a18-l1-crlv-P<N>/*`
> · **Pré-requisito:** [[ADR-239]] mergeada em `main` como `Proposto`
> · **Bloqueia:** [[A18.l2]] (apólice precisa do padrão arquitetural), [[A18.l3]] (FIPE precisa de `vehicles.fipe_code`)
> · **Tamanho estimado:** ~5d eng em 4 PRs sequenciais

## Briefing

Sessão dogfood 2026-05-21 com 6 PDFs reais (3 CRLV + 3 apólices) revelou que CRLV-e (Certificado de Registro e Licenciamento de Veículo eletrônico, exercício anual) cai em `.other` silencioso. Hoje veículos no Mathoms são `baseline_patrimonial.veiculos_consolidados[]` (array sem schema interno definido) + Grupo G02 do IRPF E1.6 ([[ADR-157]]) — **anti-pattern** que [[ADR-216]] e [[ADR-225]] vieram consertar para imóveis.

[[ADR-239]] decidiu **tabela canônica `vehicles`** com identidade `(workspace_id, placa, renavam)` imutável e FK opcional + reconciliação assíncrona. **Esta lane (L1) implementa o padrão arquitetural completo** que L2 (apólice) e L3 (FIPE) reutilizam.

## Decisões já fechadas (não reabrir)

- **Tabela `vehicles`** com identidade imutável tipo [[ADR-225]] — colisão `(placa, renavam)` = `needs_review` ([[ADR-239]] D1).
- **Stage único** `extract_comprovantes_bens` em `STAGE_REGISTRY` com sufixo `-2_comprovante_bem.json`; despacho por `tipo_comprovante` em `artifact_key` ([[ADR-239]] D8).
- **FK opcional + reconciliação assíncrona** com IRPF G02 ([[ADR-239]] D3).
- **Dedupe hierárquico** com fail-fast em colisão ([[ADR-239]] D4).
- **`baseline_patrimonial.veiculos_consolidados[]` vira projection** com FK `veiculo_id` (padrão `real_estate_e5_integration` [[ADR-216]] D9).
- **LLM Haiku** — padrão simples de CRLV-e, custo otimizado.
- **Goldens sintéticos** — PDFs anonimizados, eval real fora do git.
- `codigo_rfb='21'` (veículo automotor terrestre) padrão; `'22'` aeronave, `'23'` embarcação — invariante imutável [[ADR-225]].

## Plano de fases

### P1 — Migration Alembic `vehicles` + extensão `market_rates.reference_month` (~1d)

- Migration cria tabela `vehicles` ([[ADR-239]] D1):
  ```python
  vehicles(
      id UUID PRIMARY KEY,
      workspace_id UUID REFERENCES workspaces(id),
      placa TEXT NOT NULL,
      renavam TEXT NOT NULL CHECK (renavam ~ '^[0-9]{9,11}$'),
      marca TEXT NOT NULL,
      modelo TEXT NOT NULL,
      ano_modelo INTEGER NOT NULL,
      ano_fabricacao INTEGER NOT NULL,
      fipe_code TEXT,
      cor TEXT,
      combustivel TEXT,
      codigo_rfb TEXT,  -- '21' default
      archived_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE (workspace_id, placa)
  )
  ```
- Migration adiciona `market_rates.reference_month TEXT` (formato `'YYYY-MM'`).
- SQLAlchemy model `Vehicle` em `backend/app/models/vehicle.py`.
- Adicionar entry em `dev/check_codigo_rfb_invariant.py` para vehicles.codigo_rfb.

**Gate P1:** `pytest backend/tests/test_models.py -q` verde. Migration smoke test verde.

### P2 — Schema CRLV + parser LLM Haiku (~1.5d)

- `pipeline/llm/schemas/crlv.py` — Pydantic strict para campos do CRLV-e:
  ```python
  class CRLVPayload(BaseModel):
      placa: str
      renavam: str
      marca: str
      modelo: str
      ano_modelo: int
      ano_fabricacao: int
      cor: str
      combustivel: str
      exercicio: int  # ano do licenciamento
      categoria: str  # particular, comercial, ...
      proprietario_cpf: str
      proprietario_nome: str
      municipio_emplacamento: str
      uf_emplacamento: str
      data_emissao: date
      confidence: float
      prompt_version: str  # 'crlv-v1.0.0'
  ```
- `config/schemas/crlv.schema.json` — wire string decimal não aplicável (sem valores monetários), datas ISO.
- `pipeline/llm/prompts/crlv.py` — `PROMPT_VERSION = "crlv-v1.0.0"`. Prompt orientado a extrair só campos canônicos.
- Hook `DBArtifactStore.write` ([[ADR-212]]) — adicionar `crlv` em `SCHEMA_BY_STAGE`.

**Gate P2:** smoke test com `tests/fixtures/comprovantes/sample_crlv_nmax_anonymized.pdf` produz payload válido.

### P3 — Classifier E0 + mapping E0→DocumentType (~0.5d)

- [`backend/app/services/classification/type_classifier.py`](../../../../backend/app/services/classification/type_classifier.py) — `TypeRule` content-based para `crlv_eletronico`:
  - Required: `(DENATRAN|Certificado de Registro|Licenciamento de Veículo|RENAVAM)` + (`Placa|CRLV-e`)
- `document_classification.py` — `DocumentType.COMPROVANTE_BEM` enum novo; `map_e0_doc_type_to_document_type` mapeia `crlv_eletronico` → `COMPROVANTE_BEM`.
- Payload de classificação inclui `tipo_comprovante="crlv"` para roteamento downstream.

**Gate P3:** 3 CRLVs do batch classificam como `COMPROVANTE_BEM` + `tipo_comprovante="crlv"` com `confidence ≥ 0.7`. 18 outros documentos (15 informes A17 + 3 apólices) continuam em seu fluxo sem regressão.

### P4 — Stage `extract_comprovantes_bens` + reconciliação assíncrona + projection (~2d)

- `pipeline/stages/extract_comprovantes_bens.py` — paralelo a `extract_irpf_full.py`. Registrar em `STAGE_REGISTRY` (`pipeline/stage_spec.py`) com sufixo `-2_comprovante_bem.json` em `_STAGE_TO_SUFFIX`.
- Stage produz CRLV payload; **upsert em `vehicles`** pela chave `(workspace_id, placa)`:
  - Match → atualiza campos editáveis (cor, combustivel, fipe_code se vazio).
  - Mismatch placa↔renavam → `needs_review=true` sem upsert.
  - Novo → INSERT.
- **Reconciliação assíncrona** com IRPF G02 (`backend/app/application/comprovantes/reconciliation.py`):
  - Job pós-stage que percorre `baseline_patrimonial.veiculos_consolidados[]` sem `veiculo_id` FK
  - Fuzzy match marca+modelo+ano contra `vehicles` table
  - Confidence ≥ 0,85 → preenche FK; < 0,85 → `needs_review`
- **Projection update:** `baseline_patrimonial.veiculos_consolidados[]` enriquece com `veiculo_id` FK (não substitui — backwards compat).
- LLM Haiku via `anthropic` SDK ([[ADR-144]] cache idempotente por SHA do PDF).

**Gate P4:** Teste unitário `tests/test_vehicle_reconciliation.py`:
- (a) CRLV novo → INSERT em `vehicles`; baseline projection ganha `veiculo_id`
- (b) CRLV duplicado mesma placa+renavam → no-op (idempotente)
- (c) CRLV colisão placa+renavam diferente → `needs_review=true`
- (d) IRPF G02 com fuzzy match ≥ 0,85 → FK preenchida; < 0,85 → `needs_review`

### P5 — Goldens + cutover + flip lane (~1d)

- Goldens sintéticos em `tests/fixtures/comprovantes/crlv/`:
  - `sample_crlv_moto_anonymized.pdf` (NMAX placa fictícia, RENAVAM fictício, CPF mascarado)
  - `sample_crlv_carro_anonymized.pdf` (Toro fictício)
  - `sample_crlv_zero_km_anonymized.pdf` (sem FIPE code — fallback)
- Goldens JSON pareados em `tests/fixtures/comprovantes/crlv/golden/`.
- Telemetria: log estruturado `mathoms.comprovantes.classified` com `{tipo_comprovante, confidence, ano_exercicio}` (sem PII — alinhado [[ADR-231]]).
- Atualizar [docs/CHANGELOG.md](../../../CHANGELOG.md) via `docs/sprint/A18/changelog/CHG-YYYY-MM-DD-a18-l1-crlv.md`.
- Atualizar [[A18.l1]] status → `shipped` + `ship_pr` + `ship_date`.
- Atualizar [[MOC-sprint-a18]] §Lanes com checkmark.

**Gate P5:** `pre-commit run --all-files` + `pytest backend/tests tests -q` + `cd frontend && npm test -- --run` verdes. PR de Decidido + flip de status.

## Critério de aceite (lane completa)

- 3 CRLVs do batch classificam como `tipo_comprovante="crlv"` com `confidence ≥ 0.7`.
- Tabela `vehicles` criada via migration; UNIQUE `(workspace_id, placa)`; CHECK RENAVAM válido.
- Identidade imutável: colisão placa↔renavam diferente → `needs_review=true`.
- Reconciliação IRPF G02 → `vehicles` funciona — fuzzy ≥ 0,85 = auto-merge; < 0,85 = `needs_review`.
- `baseline_patrimonial.veiculos_consolidados[]` projection ganha `veiculo_id` FK retroativo.
- 18 PDFs fora desta lane continuam em seu fluxo sem regressão.
- `dev/check_codigo_rfb_invariant.py` verde após adição de `codigo_rfb='21'` em vehicles.
- Disclaimer visível em S4 quando veículo presente: "Valor de mercado atualizado via FIPE (refresh anual). Compare com valor declarado em IRPF."
