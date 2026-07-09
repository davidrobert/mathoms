---
id: PLAN-llm-prompts-hardening
type: plan
title: "LLM Prompts Hardening — LGPD + ADR-090 + PROMPT_VERSION + telemetria + cross-cutting"
status: done
sprint_origem: A17
sprint_atual: A33
sprints_envolvidas: ["A17", "A18", "A20", "A33"]
created_at: "2026-05-22"
last_review: "2026-07-07"
adrs_canonical:
  - "[[ADR-081]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-137]]"
  - "[[ADR-157]]"
  - "[[ADR-191]]"
  - "[[ADR-212]]"
  - "[[ADR-233]]"
  - "[[ADR-246]]"
tags:
  - type/plan
  - area/llm
  - area/pipeline
  - area/security
  - area/observability
  - sprint/a17
  - sprint/a18
  - sprint/a20
  - sprint/a33
  - status/done
  - priority/p0
  - breaking/schema
---

# Plano canônico — LLM Prompts Hardening

> Endurecer os 9 prompts LLM em [pipeline/llm/prompts/](../../../pipeline/llm/prompts/)
> para fechar gaps LGPD (PII vazada), aderência a [[ADR-090]] (`Decimal` no boundary),
> padronização de `PROMPT_VERSION` ([[ADR-233]] já decidiu semver puro), cobertura
> golden em fluxos fiscais brasileiros típicos do público-alvo (alta renda PJ),
> telemetria de `confidence`/`prompt_version` ([[ADR-110]]) e eliminação do drift
> de catálogos hardcoded no system prompt vs. `institution_catalog` ([[ADR-137]]).

> **Status: draft pós-2 ondas de revisão (2026-05-22).** Revisado por
> `senior-cto` (8 objeções), `data-engineer` (3 bloqueantes + 6 ajustes),
> `financial-planner` (5 bloqueantes + 3 ajustes), `product-manager` (re-MoSCoW
> + re-allocation em A17/A18/A20 + KR refinados) e `information-architect`
> (frontmatter + wikilinks + MOC). Todas as objeções incorporadas. Plano
> aprovado para alocar lanes; pendente apenas reservar IDs ADR e abrir lanes
> em `docs/sprint/A17/A18/A20/lanes/`.

> **Reconciliação + re-alocação 2026-07-07** (revisão de kickoff da
> [[MOC-sprint-a33]], `product-manager` + `data-engineer`): entre maio e
> julho, boa parte das ondas shipou por outras lanes. Estado real:
> **W1α** ✅ fechada 2026-07-06 (rules da [[ADR-259]], #718/#720/#781/#784)
> · **W4-T00** ✅ fechada como [[A17.l5]] (#451) · **W1β** parcialmente
> entregue — `e15_baseline` já é `Decimal` (#718); o residual
> (`e2_llm_extract` + gate no pacote) está lotado como [[A33.l1]] ·
> **W2** ✅ **inteira** — migration `a20l12semver` (A20.l12/l13), 9/9
> prompts semver puro, `llm_call_log.confidence`/`prompt_version`,
> goldens fiscais completos em `tests/fixtures/llm_golden/` (incl.
> PGBL+VGBL mesmo CPF) · **W3** → [[A33.l7]] · **W4-T01/T02** →
> [[A33.l8]]. A alocação em A20 da tabela abaixo é registro histórico do
> planejamento original — a alocação efetiva é a desta nota.

## Origem

Sessão 2026-05-22 — revisão do prompt-engineer sobre os 9 prompts em
`pipeline/llm/prompts/`. Diagnóstico transversal identificou **6 dimensões
inconsistentes** entre prompts e **3 gaps críticos P0** confirmados por leitura
direta dos schemas:

- `pipeline/llm/schemas/e15_baseline.py:20,31-33` — `value_brl`, `total_assets_brl`,
  `total_liabilities_brl`, `net_worth_brl` declarados como `float`.
  **Viola [[ADR-090]] no schema Pydantic**, não só no prompt.
- `pipeline/llm/schemas/e1_members.py:28` — `cpf: Optional[str]` aceita
  11 dígitos crus, sem mask no boundary. Modelo `FamilyMember.cpf_encrypted`
  já existe em `backend/app/models/family_member.py:34` — não há tabela
  nova a criar, há **gap de uso**.
- `pipeline/llm/prompts/informe_aluguel.py` — sem `PROMPT_VERSION` no
  arquivo de prompt (schema tem `informe-aluguel-v1.1.0` em formato legado).
  Inconsistência convencional invalida gate [[ADR-233]]
  (`dev/check_prompt_version_bumped.py` monitora arquivo do prompt).
- `pipeline/llm/prompts/e2_llm.py:35` — instrui "Valores em formato
  numérico (1234.56, não '1.234,56')" — mesma violação ADR-090 classe que
  `e15_baseline`. Schema `e2_llm_extract.py` precisa ser auditado.
- `pipeline/llm/litellm_client.py:69-86` — `LLMCallResult` captura tokens
  /cost/duration/retries mas **não captura `confidence` nem `prompt_version`**.
  Threshold [[ADR-081]] (<0.7 / <0.8) hoje é teoria sem dado empírico.

## Decisões já tomadas pela revisão (2026-05-22)

1. **Formato `PROMPT_VERSION`: semver puro** — [[ADR-233]] já decidiu
   `"1.0.0"`. **Cancelamos** a proposta inicial `<slug>-vX.Y.Z`. Prompts
   legados (`apolice-v1.0.0`, `crlv-v1.0.0`, `e16-v1.1.0`,
   `informe-aluguel-v1.1.0`, `informe-prev-v1.0.0`) migram para semver
   puro **com migration coordenada** de `LLMCallLog.prompt_version` rows
   existentes + `pipeline_artifacts.metadata.prompt_version` para preservar
   dimensão histórica de telemetria.
2. **Telemetria OTLP usa labels compostos `{prompt_name, prompt_version}`**
   — slug embutido na string vira redundância. Label `prompt_name` (ex.
   `e15_baseline`, `parecer_planejador`) é a coordenada de dimensão; `prompt_version`
   é a coordenada de tempo. `confidence_p50{prompt_name="e15_baseline", prompt_version="1.0.0"}`
   é distinguível.
3. **PII pós-extração reutiliza `FamilyMember.cpf_encrypted` existente**
   — não criar tabela `family_member_pii`. Adapter pós-LLM usa
   `backend/app/services/security/vault.py` (Fernet singleton lazy idempotente,
   aderente [[ADR-111]]).
4. **3 ADRs novas + 1 errata em [[ADR-233]]** — consolidado vs. 5 ADRs
   propostas inicialmente. Errata em ADR-233 cobre migration de prompts legados.
5. **CI nunca chama Anthropic real** — fixtures golden são bit-exact
   (regression). Drift de provider via **CI nightly opcional** (lane
   follow-up, não MVP) com hash divergence alert.
6. **Persistência de telemetria precede OTLP** — modelo `LLMCallLog`
   já existe; persistir `confidence` + `prompt_version` em SQL desbloqueia
   análise SQL imediata sem depender de [[PLAN-internal-admin]] dashboard.

## Objetivo

Após este plano:

1. **LGPD compliance unificada** — nenhum prompt LLM emite ou aceita PII crua.
   Schemas Pydantic enforçam `cpf_present: bool` no boundary; mascaramento/
   persistência cifrada fica em adapter Python pós-extração via
   `FamilyMember.cpf_encrypted` (Fernet).
2. **ADR-090 aderente em todos os schemas LLM** — valores monetários em
   `Decimal` (com `_coerce_decimal` validator no boundary, padrão já em
   `pipeline/llm/schemas/e16_irpf_full.py:23-35`), nunca `float`. System
   prompt usa string decimal explícita.
3. **`PROMPT_VERSION` em semver puro** ([[ADR-233]]) em 100% dos prompts;
   gate CI cobre os 9; migration de payloads históricos preserva grep.
4. **Golden fixture cobrindo casos brasileiros típicos** em todos os 9
   prompts — ≥2 fixtures (happy + edge), com cobertura específica para
   alta renda PJ (regimes mistos previdência, comunhão imobiliária, dedução
   IPTU no carnê-leão, etc.).
5. **Telemetria por `prompt_version`** em SQL (`llm_call_log`) **e** OTLP
   ([[ADR-110]]) — `confidence_p50/p95`, `needs_review_rate`, `cache_hit_rate`,
   `parecer.riscos_truncados`.
6. **Drift de catálogos eliminado** — listas de bancos/seguradoras saem do
   system prompt e entram no user prompt via injection do `institution_catalog`
   ([[ADR-137]]). Códigos RFB do `e16_irpf_full` migrados para
   `config/prompts/e16_codigos_rfb_<ano_base>.yaml` versionado anualmente.

## Não-objetivos (V1) — explícitos pelos revisores

- **Few-shot abrangente** em todos os prompts. Adicionar 1-2 exemplos
  apenas em prompts com erro estrutural recorrente.
- **Migração total para YAML** (`config/prompts/`). Códigos RFB são exceção.
- **Provider portability** (OpenAI/Gemini fallback). Anthropic só.
- **Eval LLM-as-judge** sobre output qualitativo do `parecer_planejador`.
- **Drift detection real-LLM em CI** — opcional como lane follow-up.
- **3 prompts faltantes** (extrato de corretora XP/BTG/Avenue; DARF/GCAP;
  informe de FII com proventos isento/amortização/ganho) — registrados
  como **gap reconhecido**, follow-up em sprint A13/A14. Hoje caem em
  `e2_llm` genérico, é fallback ruim mas não bloqueia esta wave.
- **Cap do Parecer (≤12 riscos, ≤2 P0)** — aprovado como está. Cap é UX
  deliberado anti-overwhelm (Cerbasi). Telemetria W3 mede `riscos_truncados`
  para calibrar futuramente.
- **Guardrail anti-recálculo do `e16_irpf_full`** (§IMPOSTO APURADO) —
  aprovado como está. Mathoms é consolidador, não auditor RFB.

## Premissas (validadas pela revisão)

- **`institution_catalog` cobre os 8 bancos hardcoded** atuais (verificado
  em `backend/alembic/versions/b6c7d8e9f0a1_seed_institution_catalog.py`).
  **Não cobre o público-alvo alta renda PJ completo** — gap a fechar em
  W4-T01 antes da injection (ver §W4 expandido).
- **`FamilyMember.cpf_encrypted`** já existe em modelo (`backend/app/models/family_member.py:34`).
  Gap atual: caminho LLM `extract_members` não popula; pode ter payloads
  com CPF cru em `pipeline_artifacts`.
- **`LLMCallResult` é dataclass com defaults** — adicionar campos é
  **aditivo, não-breaking** (confirmado em `pipeline/llm/litellm_client.py:69-86`).
- **Códigos RFB mudam anualmente** — exemplos recentes: 2024 grupo de
  criptoativos expandido (códigos 81/89), Lei 14.754/2023 mudou tributação
  de FIE/offshore; 2025 tabela progressiva ajustada. Fonte oficial:
  Manual de Preenchimento DIRPF (PDF anual RFB). Sem API estruturada
  pública.

## Invariantes (não-negociáveis)

1. **Dinheiro nunca é `float`** ([[ADR-090]]).
2. **PII nunca vaza para LLM no output bruto** ([[ADR-081]] + LGPD art. 46
   + CMN 4.658 + ANPD Guia de Anonimização).
3. **`PROMPT_VERSION` é fonte única de invalidação de cache** ([[ADR-233]]).
4. **`confidence < 0.7` → `needs_review=true`** ([[ADR-081]]).
5. **Pipeline não importa `backend.app`** ([CLAUDE.md] §Pipeline não importa
   framework). Injection via protocol em `pipeline/llm/`.
6. **CI nunca chama Anthropic real** — goldens são bit-exact em snapshot
   test pattern.

## Findings consolidados (matriz 9×6, atualizada pós-review)

| Prompt | `PROMPT_VERSION` aderente ADR-233 | LGPD CPF mask | Few-shot | Golden fixture | Fallback determinístico ([[ADR-081]]) | Catálogo hardcoded |
| --- | --- | --- | --- | --- | --- | --- |
| `apolice.py` | `apolice-v1.0.0` ⚠️ (slug legado) | Python pós-extração ✅ | descrição | 6 ✅ | parcial (cascade Haiku→Sonnet) | seguradoras top-5 ⚠️ |
| `crlv.py` | `crlv-v1.0.0` ⚠️ (slug legado) | Python pós-extração ✅ | descrição | 3 ✅ | **ausente** ❌ | n/a |
| `e15_baseline.py` | `1.0.0` ✅ | **gap (sem regra)** ❌ | minimal | 1 ⚠️ | n/a | n/a |
| `e16_irpf_full.py` | `e16-v1.1.0` ⚠️ (slug legado) | Python pós-extração ✅ | descrição | 3 ✅ | n/a | códigos RFB ⚠️ |
| `e1_members.py` | `1.0.0` ✅ | **vaza cru** ❌ | minimal | 1 ⚠️ | n/a | bancos ⚠️ |
| `e2_llm.py` | `1.1.0` ✅ | n/a | inline | 1 ⚠️ | é o fallback (E2-llm de E2) | bancos ⚠️ |
| `informe_aluguel.py` | **ausente no prompt** ❌ (schema tem `informe-aluguel-v1.1.0` legado) | **vaza cru** ❌ | descrição | **0** ❌ | **ausente** ❌ | n/a |
| `informe_previdencia.py` | `informe-prev-v1.0.0` ⚠️ (slug legado) | Python pós-extração ✅ | descrição | **0** ❌ | **ausente** ❌ | n/a |
| `parecer_planejador.py` | `1.1.0` ✅ (vs. manifest YAML `1.3`) | n/a | persona externa | mock ✅ | n/a | n/a |

**Legenda**: ✅ aderente · ⚠️ gap menor · ❌ gap crítico

## Plano de execução — 5 ondas (split W1α/W1β decidido pela revisão PM)

> **Re-empacotamento pós-PM** (2026-05-22): a onda W1 original misturava 2
> jobs com WSJF distintos — (a) **LGPD compliance** é gate de [PHASES.md
> F7 R4](../../reference/PHASES.md) (passagem dogfood → beta fechado), custo
> de não fazer = não abre beta; (b) **ADR-090 cascata** é correção de
> invariante histórico, risco alto na cadeia `extract_baseline → consolidate_baseline
> → e4_categorizer` (DE confirmou). Empacotar juntos atrasava o gate de
> compliance pelo overhead da migração `Decimal`. Split em **W1α (LGPD-only,
> sprint A18)** + **W1β (ADR-090-only, sprint A20)** permite shipping
> intermediário do compliance milestone sem prender em risco de cadeia.

### Sprint allocation (re-MoSCoW pelo PM)

| Onda | Escopo resumido | Tier | Sprint | Capacity | Justificativa |
| --- | --- | --- | --- | --- | --- |
| **W4-T00** | Seed expandido de `institution_catalog` (XP, BTG digital, Avenue, Nomad, Sicoob, NuInvest, Inter Pag, …) | Must (P0) | **A17 L3** (antecipar) | ~0.5d | Independente do plano; beneficia A17 L3 imediatamente (Wise/XP no catálogo). |
| **W1α** | LGPD compliance: `e1_members` (PR-A foundation + PR-B schema), `informe_aluguel` (LGPD + PROMPT_VERSION + 5 goldens BR), UX boundary CPF mascarado | Must (P0) | **A18** | ~4d | Gate F7 R4 → Beta. Sinergia com A18 (apólices extraem CPF do segurado). |
| **W1β** | ADR-090 `e15_baseline`: W1.A-T01 audit + serializer + W1.B-T01 schema bump + migration cadeia consumers | Must (P0) | **A20** (sprint nova LLM Hardening) | ~3d | Risco alto cadeia Decimal; isolado para não acoplar com gate Beta. |
| **W2** | Migração semver puro (5 prompts legados) + goldens fiscais (7 previdência + outros) + LLMCallLog SQL persistence | Should (P0) | **A20** | ~4d | Desbloqueia W3; goldens FP-críticos (PGBL+VGBL mesmo CPF). |
| **W3** | OTLP `mathoms.llm.*` + `parecer.riscos_truncados` | Should (P1) | **A20** | ~2d | Paralelo a W4 em A20. |
| **W4-T01/T02** | Protocol `InstitutionCatalogProvider` + códigos RFB para YAML + runbook anual fevereiro | Should (P1) | **A20** | ~2d | Cross-cutting; depende de W4-T00 entregue em A17 L3. |

**Total capacity**: A17 L3 (~0.5d) + A18 (~4d) + A20 (~11d eng-time, sprint dedicada).

### W1α — P0 LGPD compliance (sprint A18, 3 PRs)

> **Onda fechada (2026-07-06):** as 4 rules da [[ADR-259]] shiparam.
> Rules 1-3 em #718/#720 (audit r6); rule 4 (UX boundary CPF mascarado +
> "ver completo" auditado) em #781/#784 — track
> [[TRACK-adr259-rule4-cpf-view]] `consumed`.

**Critério de aceite W1α** (falsifiável):
- `grep -rn "cpf.*Optional\[str\]" pipeline/llm/schemas/` retorna 0 ocorrências.
- `jq` sobre `pipeline_artifacts` (stage `extract_members` + `extract_informe_aluguel`)
  retorna 0 rows com CPF cru em payload.
- 5 fixtures golden `informe_aluguel` mergeadas e passando em
  `pytest tests -q -k "informe_aluguel"`.
- **Checklist [F7 R4 LGPD](../../reference/PHASES.md) verde** — auditoria
  interna do founder + checklist ANPD Guia de Anonimização sem item vermelho.

#### W1α-T01 — Audit gravação atual de CPF (foundation W1α, ~1d)
- `grep -rn "cpf_encrypted" backend/app/services/` — mapear quem grava
  hoje (caminho upload via `process_uploaded_document` + regex vs.
  caminho LLM `extract_members`).
- Auditar `pipeline_artifacts` em DB dev/staging para presença de CPF
  cru em payload de stages `extract_members` e `extract_informe_aluguel`
  (jq sobre rows existentes).
- Decidir e documentar **backfill policy**: payloads existentes com
  CPF cru → migration que **purga** ou **re-criptografa** o campo
  `cpf` do payload. Custo: ~1k-10k rows em dev/staging.

#### W1α-T02 — `e1_members` LGPD (split em 2 PRs, ~2d)
- **PR-A (foundation, independente do schema bump)**: garantir que
  `FamilyMember.cpf_encrypted` (já existe em `backend/app/models/family_member.py:34`)
  é populado pelo caminho LLM `extract_members`. Adapter pós-LLM em
  `backend/app/services/family_member_pii_service.py` usa `vault.py`
  Fernet (singleton lazy idempotente, [[ADR-111]]). Backfill de payloads
  `pipeline_artifacts` com CPF cru (rotina + dry-run + apply).
- **PR-B (schema + prompt)**: schema `cpf: Optional[str]` → `cpf_present:
  bool = False`. Prompt: remover instrução de extração CPF; adicionar
  regra de mask explícita. Adapter PR-A passa a ser fonte única de CPF.
  Bump `PROMPT_VERSION → "2.0.0"` (major — schema breaking).
- **Decisão UX explícita**: relatório do cliente em `/reports/[id]`
  precisa **mostrar CPF de volta**. Backend decriptografa Fernet no
  boundary HTTP autenticado (request owner do workspace) e renderiza
  **mascarado `***.***.789-00` por default + opção "ver completo" sob
  clique com audit log**. ADR Proposto cobre ambos os sentidos.
- Atualizar fixture + 1 fixture nova (família 5 membros, dependente
  sem CPF).

#### W1α-T03 — `informe_aluguel` LGPD + PROMPT_VERSION + 5 goldens (~1d)
- Re-export `PROMPT_VERSION` do schema no arquivo de prompt
  (`from pipeline.llm.schemas.informe_aluguel import PROMPT_VERSION`)
  — padrão de `e16_irpf_full`.
- Schema: `locador_cpf: Optional[str]` → `cpf_present: bool = False`.
  `imobiliaria_cnpj`: mantém (CNPJ é informação pública), comentar
  política de anonimização em logs.
- Prompt: remover instrução de extração CPF.
- Bump schema → semver puro (`informe-aluguel-v1.1.0` → `1.2.0` no
  prompt + schema; migration de `LLMCallLog`/`pipeline_artifacts`
  history em W2-T01).
- **Criar 5 fixtures golden** (revisão FP):
  - PF→PF residencial simples (zero IR retido).
  - Multi-imóvel com vacância (`meses_locado < 12`).
  - PF→PJ com IR retido na fonte.
  - **Imóvel em comunhão** (CPF titular + CPF cônjuge, paridade
    com [[ADR-246]]).
  - **PF locador com dedução IPTU/condomínio** (operacional do
    carnê-leão, exigido para `rendimentos_pf` no E1.6).

---

### W1β — P0 ADR-090 cadeia `e15_baseline` (sprint A20, 2 PRs)

**Critério de aceite W1β** (falsifiável):
- `grep -rn "value_brl: float\|total_assets_brl: float" pipeline/llm/schemas/`
  retorna 0 ocorrências.
- Consumer chain `extract_baseline → consolidate_baseline → e4_categorizer`
  passa em testes com `Decimal`/string decimal sem perda de precisão.
- Schema JSON `baseline_patrimonial.schema.json` em pattern string
  decimal `^-?\d+(\.\d{1,2})?$` + `additionalProperties: false`.
- 0 rows em `pipeline_artifacts` (stage E1.5/E1.5a/E1.5c) com payload
  number-typed (após backfill).

#### W1β-T01 — Audit downstream + serializer canônico (~1.5d)
- Auditar consumers de `BaselinePatrimonialOutput`:
  - `pipeline/stages/extract_baseline.py:43-58` — consome `item.value_brl`,
    `output.total_assets_brl`, `output.net_worth_brl`.
  - `pipeline/llm/validators.py` — aritmética `sum(i.value_brl ...)`,
    `abs(computed - output.total_assets_brl)`.
  - `pipeline/domain/services/e4_categorizer_adapter.py:194` — consome
    baseline via E5.
  - `consolidate_baseline` (E1.5c) — pré-baseline.
- Criar helper `_baseline_to_legacy_dict(output) → dict` em
  `extract_baseline.py` que serializa `Decimal → str` (não `float`).
- Migrar `validators.py` para aritmética `Decimal`.
- **Schema JSON**: `config/schemas/baseline_patrimonial.schema.json:55-69,131`
  → `"type": "string", "pattern": "^-?\\d+(\\.\\d{1,2})?$"` nos campos
  monetários + `additionalProperties: false` + `payload_version` no
  envelope para backfill incremental.
- **Mapping `SCHEMA_BY_STAGE`** em `backend/app/services/storage/db_artifact_store.py`:
  adicionar `E1.5` e `E1.5a` (gap atual permite payload sem validation
  no per-IRPF pré-consolidação).

#### W1β-T02 — Schema + prompt + fixture atomic (~1.5d)
- Schema: `value_brl`/`total_assets_brl`/`total_liabilities_brl`/`net_worth_brl`
  → `Decimal` com `_coerce_decimal` validator (padrão `e16_irpf_full.py:23`).
- Prompt: substituir `"150000.00, não R$ 150.000,00"` por instrução
  explícita de string decimal. Adicionar regra de mask CPF (espelhar
  §10 de `apolice.py`).
- Bump `PROMPT_VERSION` (`"1.0.0"` → `"1.1.0"`).
- Atualizar fixture `tests/fixtures/llm_golden/e15_baseline_output.json`
  para strings decimais.
- **Migration de payloads históricos**: `pipeline_artifacts` com stage
  E1.5/E1.5a/E1.5c → re-validar contra novo schema; payloads que falham
  marcados para re-extração ou conversão in-place (decisão por contagem
  do audit W1β-T01).
- **PR atomic**: schema + prompt + validators + serializer + fixture +
  golden test que prova consumer chain aceita string decimal.

---

### W2 — P0 PROMPT_VERSION padronizado + goldens fiscais (sequencial, 3 PRs)

**Critério de aceite W2**: 100% dos prompts em `PROMPT_VERSION` semver
puro ([[ADR-233]]); 100% dos prompts ≥2 fixtures golden; goldens cobrem
casos brasileiros típicos do público-alvo (PGBL+VGBL mesmo CPF, regimes
mistos, comunhão imobiliária, dedução IPTU).

#### W2-T01 — Migração para semver puro + errata em [[ADR-233]]
- Migrar 5 prompts legados (`apolice-v1.0.0`, `crlv-v1.0.0`,
  `e16-v1.1.0`, `informe-aluguel-v1.1.0` ou `1.2.0` pós-W1α-T03,
  `informe-prev-v1.0.0`) para semver puro.
- **Migration coordenada de `LLMCallLog.prompt_version`** (col String(40))
  e `pipeline_artifacts.metadata.prompt_version`: regex map `<slug>-v(\d+\.\d+\.\d+)`
  → `\1`. **Antes** da migration, snapshot histórico para auditoria
  (`_archive/llm_call_log_pre_semver_migration_<date>.csv`).
- Atualizar `dev/check_prompt_version_bumped.py` para validar
  formato estrito semver `^\d+\.\d+\.\d+$`.
- **Errata em [[ADR-233]]**: nova seção §Migration cobre o histórico
  (motivo da decisão: telemetria OTLP usa labels compostos `{prompt_name,
  prompt_version}`, slug embutido é redundância).
- Bump dos 5 prompts em PR coordenado (não atomic per-prompt — quebra
  migration).

#### W2-T02 — Golden fixtures faltantes (público-alvo BR alta renda)
- **`informe_previdencia` — 7 fixtures** (revisão FP expandiu de 4 para 7):
  - PGBL progressivo (dedução 12% renda tributável).
  - PGBL regressivo (alíquota 35→10% conforme tempo).
  - VGBL progressivo (raro).
  - PGBL patrocinador (empresa) → `needs_review=true`.
  - **PGBL+VGBL mesmo CPF/seguradora** (deduz 12% via PGBL, excedente
    em VGBL — alta renda típica).
  - **Regimes mistos PGBL prog + reg no mesmo CPF** (aporte pré-2005
    em prog, novos em reg — cliente 45-60 anos).
  - **Portabilidade entre seguradoras no ano-base**
    (`saldo_01_01 ≠ saldo_31_12_ano_anterior`).
- **`informe_aluguel`**: já criadas em W1α-T03 (5 fixtures).
- **`e15_baseline`**: adicionar 2 fixtures (declaração truncada
  `confidence` baixa, baseline com dependente).
- **`e1_members`**: adicionar fixture família 5 membros (W1α-T02).
- **`e2_llm`**: adicionar fixture com `info_fiscal_anual` (v1.1.0
  ADR-242 sem fixture que prova anti-double-counting).
- **`e16_irpf_full`**: adicionar 1 fixture "fail gracefully"
  (declaração truncada, confidence baixo, notes populado).

#### W2-T03 — Persistência de `confidence` + `prompt_version` em `LLMCallLog` (revisão DE)
- Estender `LLMCallLog` (modelo `backend/app/models/llm_call_log.py`)
  com colunas `confidence: float | None` e `needs_review: bool` (já
  tem `prompt_version`).
- Adapter `litellm_client._record_call_log()` popula campos do output
  Pydantic via `getattr(output, "confidence", None)`.
- **Antes do OTLP em W3.** Desbloqueia análise SQL sobre confidence
  distribution sem depender de dashboard externo.

**Custo W2 estimado**: ~4 dias eng-time (1 dia migration semver + 2 dias
goldens fiscais + 1 dia persistência LLMCallLog).

---

### W3 — P1 Telemetria `mathoms.llm.*` OTLP (1 PR, depende de W2)

**Critério de aceite W3**: métricas OTLP `mathoms.llm.*` emitidas com
labels `{prompt_name, prompt_version}`. Análise SQL via `LLMCallLog`
desbloqueada desde W2-T03. Dashboard `ops.mathoms.ai` é follow-up no
plano [[PLAN-internal-admin]].

#### W3-T01 — Estender `LLMCallResult` + emit OTLP no consumer backend
- Adicionar campos a `LLMCallResult` ([litellm_client.py:69](../../../pipeline/llm/litellm_client.py:69)):
  - `prompt_version: str | None = None`
  - `prompt_name: str | None = None` (label dimensão)
  - `confidence: float | None = None`
  - `needs_review: bool = False`
  - `cache_hit: bool = False` (**condicional**: confirmar se LiteLLM
    expõe sinal de cache hit; se não, drop do campo).
- Helpers `_extract_confidence(output)` e `_extract_needs_review(output)`.
- **Pipeline NÃO emite OTLP** ([CLAUDE.md] boundary). Pipeline retorna
  `LLMRunSummary` agregado por `prompt_version`. Emit OTLP fica em
  **`backend/app/services/documents/document_processor.py`** (ou no orchestrator
  stage runner) que consome o summary após cada chamada.
- Métricas OTLP via `backend/app/core/otel.py` ([[ADR-110]]):
  - `mathoms.llm.confidence` (histogram, labels `prompt_name`, `prompt_version`,
    `model`).
  - `mathoms.llm.needs_review_total` (counter).
  - `mathoms.llm.cache_hit_total` (counter, se aplicável).
  - `mathoms.llm.tokens_in/tokens_out/cost_usd` (já existem em
    `LLMRunSummary` mas sem labels `prompt_*` — adicionar).
  - `mathoms.llm.parecer.riscos_truncados` (counter, do `parecer_planejador`
    quando LLM gera >12 riscos e é truncado).

**Custo W3 estimado**: ~2 dias eng-time (estender result + emit no
consumer + dashboard placeholder).

---

### W4 — P1 Cross-cutting (paralelo após W1, 3 PRs)

**Critério de aceite W4**: nenhum prompt LLM tem catálogo de bancos
hardcoded no system prompt; códigos RFB do `e16_irpf_full` em YAML
versionado por ano-base; `institution_catalog` cobre público-alvo
alta renda PJ.

#### W4-T00 — Seed expandido de `institution_catalog` (precede W4-T01)
- Audit `data-engineer` confirma cobertura mínima para público-alvo
  (revisão FP):
  - **Corretoras alta renda**: XP, BTG Pactual digital (separado de
    `btgpactual` institucional), Genial, Modal, Ágora, Toro, Warren.
  - **Conta global USD**: Avenue, Inter Invest USA, Nomad, Stake.
  - **Migrações históricas**: Pi (Santander), NuInvest (ex-Easynvest).
  - **Conta-pagamento (fluxo de caixa)**: Inter Pag, PicPay Invest,
    Mercado Pago Conta.
  - **Cooperativas**: Sicoob, Sicredi (relevante interior + agro).
- Migration Alembic que extends seed em
  `b6c7d8e9f0a1_seed_institution_catalog.py`.
- Categorização: cada entry tem `category` (banco / seguradora / corretora
  / conta_pagamento / cooperativa) — necessário para W4-T01 discriminar
  domínio.

#### W4-T01 — `InstitutionCatalogProvider` protocol injetado
- Protocol `pipeline/llm/institution_provider.py`:
  ```python
  class InstitutionCatalogProvider(Protocol):
      def list_codes(self, category: str | None = None) -> list[str]: ...
  ```
  Retorna `list[str]` (códigos), não `InstitutionCatalog` ORM —
  evita circular import e isolamento de boundary.
- Implementação concreta `backend/app/services/institution_catalog_provider.py`
  injetada pelo orchestrator que consome o pipeline.
- `e1_members`, `e2_llm`, `apolice` recebem `available_institutions:
  list[str]` no **user prompt** (não system) — evita bump de version
  a cada banco novo.
- System prompt referencia: `"use SOMENTE códigos da lista
  available_institutions injetada"`.
- Bump dos 3 prompts (minor — comportamento mantém).
- Atualizar goldens com `available_institutions` populado.

#### W4-T02 — Códigos RFB para YAML versionado por ano-base
- Estrutura `config/prompts/e16_codigos_rfb_<ano_base>.yaml`:
  ```yaml
  ano_base: 2024
  codigos_bens:
    "01": "Imóveis - Prédio residencial"
    "02": "Imóveis - Prédio comercial"
    # ...
  codigos_rendimentos_isentos:
    "06": "Bolsa estudos pesquisa"
    "12": "Rendimento sócio/titular cota empresarial"
    # ...
  ```
- JSON Schema validador em `config/schemas/e16_codigos_rfb.schema.json`.
- Loader `pipeline/llm/rfb_codes_loader.py` resolve por `ano_base` do
  documento.
- System prompt referencia: `"use tabela RFB injetada no user prompt"`.
- Atualização anual RFB (lane recorrente em fevereiro/cada ano) = edit
  YAML + bump YAML version (não `PROMPT_VERSION`).
- **Runbook anual** em `docs/reference/runbooks/rfb_codes_annual_update.md`:
  fonte oficial Manual DIRPF, fluxo de extração manual, validação contra
  golden fixture de declaração do ano-base.

**Custo W4 estimado**: ~3 dias eng-time (W4-T00 seed 1 dia + W4-T01 protocol
1 dia + W4-T02 RFB YAML 1 dia).

---

## ADRs propostas (consolidado: 3 novas + 1 errata)

| ID | Slug | Escopo | Onda |
| --- | --- | --- | --- |
| ADR Proposto | `boundary-llm-unified` | Política unificada de boundary LLM: tipos (`Decimal`), PII (`cpf_present: bool` + Fernet decrypt no HTTP boundary autenticado para UX), contratos. Estende [[ADR-081]] + [[ADR-090]]. Cobre **extração + exibição** no relatório. | W1 |
| ADR Proposto | `llm-telemetry-by-prompt-version` | Telemetria por labels `{prompt_name, prompt_version}` em SQL (`LLMCallLog`) + OTLP. Estende [[ADR-110]]. Pipeline retorna `LLMRunSummary`, backend instrumenta. | W3 |
| ADR Proposto | `llm-cache-invalidation-policy` | Política de cache invalidation em bump de `PROMPT_VERSION`. Estimativa de custo. Decisão sobre re-extrair vs. servir stale para payloads históricos. | W2/W3 |
| Errata em [[ADR-233]] | (in-place edit) | Nova seção §Migration: migração de 5 prompts legados (`<slug>-vX.Y.Z` → semver puro) com migration coordenada de `LLMCallLog.prompt_version` + `pipeline_artifacts.metadata.prompt_version`. Justificativa: labels OTLP compostos tornam slug redundante. | W2 |

IDs ADR a reservar quando lane abrir.

## Riscos (atualizado pós-review)

| Risco | Probabilidade | Mitigação |
| --- | --- | --- |
| W1α-T02 quebra fluxo de upload (LLM extract_members deixa de gravar CPF e adapter não está pronto) | Média | PR-A foundation antes de PR-B schema. Gate: jq sobre `pipeline_artifacts` confirma 0 CPF cru após PR-A. |
| W3 dashboard ainda não pronto (depende [[PLAN-internal-admin]]) | Alta | W2-T03 já persiste em SQL → análise SQL imediata. OTLP emit fica como infra; dashboard é follow-up. |
| `institution_catalog` cobertura insuficiente para alta renda PJ | Alta (FP confirmou) | W4-T00 antes de W4-T01. Lista mínima definida em §W4-T00 (15+ entries). |
| Bump em massa de `PROMPT_VERSION` invalida cache LLM, custo re-extração | Média | ADR `llm-cache-invalidation-policy` define política. Estimativa: tokens/extração × workspaces × $/1M tokens. Bumps coordenados em W1α e W1β (2 ondas) reduzem N de invalidações. |
| `Decimal` enforcement em `e15_baseline` quebra consumer chain (`extract_baseline → consolidate_baseline → e4_categorizer`) | Alta (DE confirmou) | W1β-T01 audit chain **antes** do bump. `_baseline_to_legacy_dict` serializer Decimal→str. PR atomic com fixture+validators+serializer. |
| Few-shot adicionado em W1 expande tokens | Baixa | Few-shots minimal (1-2/prompt); medir token impact pré/pós. |
| Migration `LLMCallLog.prompt_version` perde grep histórico | Baixa | Snapshot `_archive/llm_call_log_pre_semver_migration_<date>.csv` antes da migration. |
| Provider Anthropic muda modelo sem bumpar nome (drift silencioso) | Média | Lane reservada `a21-llm-drift-nightly-real` (não bloqueia V1). |
| `LLMCallLog` schema breaking change (adicionar `confidence`/`needs_review`) | Baixa | Aditivo: colunas nullable com default. Migration Alembic standard. |

## KR / Métricas de saúde (refinado pelo PM — Goodhart-proofing)

> **PM removeu** `confidence_p50 ≥ 0.8` e `needs_review_rate ≤ 15%` como gates
> de aceite. Vira **observabilidade pós-W3**, não gate. Razão: KR de
> health vestido como gate força otimização sobre métrica em vez de
> outcome (Goodhart). KR refinados são **binários** (passa/falha) e
> ancorados em outcome de produto.

### Gates binários por onda

- **W1α** (LGPD gate F7 → Beta):
  - `grep -rn "cpf.*Optional\[str\]" pipeline/llm/schemas/` retorna 0.
  - 0 rows em `pipeline_artifacts` (stages `extract_members` +
    `extract_informe_aluguel`) com CPF cru em payload.
  - 5 fixtures `informe_aluguel` mergeadas em `tests/fixtures/llm_golden/`.
  - **Checklist [F7 R4 LGPD](../../reference/PHASES.md) verde** —
    auditoria interna do founder + checklist ANPD Guia de
    Anonimização sem item vermelho.
- **W1β** (ADR-090 cadeia):
  - `grep -rn "value_brl: float" pipeline/llm/schemas/` retorna 0.
  - Consumer chain `extract_baseline → consolidate_baseline →
    e4_categorizer` passa com `Decimal` sem perda em testes E2E.
  - `config/schemas/baseline_patrimonial.schema.json` com pattern
    string decimal + `additionalProperties: false`.
- **W2**:
  - `dev/check_prompt_version_bumped.py` valida regex `^\d+\.\d+\.\d+$`
    em 100% dos prompts.
  - 100% dos 9 prompts em `tests/fixtures/llm_golden/` com ≥2 fixtures.
  - `LLMCallLog.confidence`/`needs_review` populado em 100% das
    chamadas LLM pós-W2-T03.
- **W3**:
  - OTLP histograms `mathoms.llm.confidence{prompt_name, prompt_version}`
    emitidos em produção (dogfood).
  - SQL query exemplo retorna ≥1 row por prompt em últimos 7 dias.
- **W4**:
  - `grep -rn "itau\|santander\|bradesco" pipeline/llm/prompts/` retorna 0.
  - `institution_catalog` cobre ≥15 entries categorizadas.
  - Lane `a21-rfb-codes-annual-update` reservada para fevereiro/ano.

### KR de outcome / saúde pós-cutover

- **0 incidentes de dados** (Decimal perde precisão, CPF cru reaparece
  em payload) em 14 dias pós-merge de W1α + W1β em dogfood. Mensurado
  via log de validação + audit jq semanal.
- **0 objeção LGPD** no checklist F7 R4 de auditoria interna
  (binário — passa ou falha).

### KR de observabilidade (pós-W3, **não** gate de aceite)

- `confidence_p50` por `prompt_name` exposto em SQL — dashboard mede
  saúde, não decide release.
- `needs_review_rate` por `prompt_name` exposto — calibração de
  threshold 0.7/0.8 ([[ADR-081]]) ganha dado empírico.
- `parecer.riscos_truncados` rate — calibração do cap ≤12 em
  `parecer_planejador` ganha dado.

## Decisões pendentes (para PM revisor)

- **Sprint para W3/W4**: A12 ou A13.
- **Lane W1.C drift CI nightly**: A13 ou A14 (não-MVP).
- **IDs ADR**: reservar quando primeira lane abrir.
- **Capacity assumption confirmada pelo PM**: A17 L3 (~0.5d para W4-T00)
  + A18 (~4d para W1α) + A20 sprint nova LLM Hardening (~11d para
  W1β+W2+W3+W4-T01/T02). Total ~15.5d eng-time.

## Lanes follow-up reservadas (slug + `status: proposed`)

Por recomendação PM, registrar agora vs. ficar implícito:

- **`a21-llm-drift-nightly-real`** ✅ shipped A33.l5 (#831) — workflow noturno chama Anthropic
  real com fixtures input e gera hash do output normalizado. Divergência
  hash{D} ≠ hash{D-1} → alert + PR de update de fixture. (W1.C original;
  follow-up A21).
- **`a21-prompts-faltantes-corretora-darf-fii`** — 3 prompts faltantes
  do público-alvo alta renda PJ:
  - Extrato/posição de corretora (XP/BTG/Avenue) — hoje cai em `e2_llm`
    genérico, fallback ruim. Crítico para AUVP (desvio por classe).
  - DARF/GCAP (apuração de ganho de capital ações/cripto/FII) —
    relevante para alta renda BR.
  - Informe de FII — 3 naturezas de provento (rendimento isento,
    amortização, ganho na venda da cota) cada uma vai pra ficha
    IRPF diferente.
  Alto valor; não é "nice-to-have". A21 ou A22.
- **`a21-eval-llm-judge-parecer`** — LLM-as-judge sobre output
  qualitativo do `parecer_planejador`. V2 do parecer; depende de
  PLANNER_REVIEW ter dataset real.
- **`a21-rfb-codes-annual-update`** — lane recorrente fevereiro/cada
  ano. Atualização anual de `config/prompts/e16_codigos_rfb_<ano>.yaml`
  a partir do Manual DIRPF (RFB).

## Pré-requisitos para start

1. **Revisores aprovam plano refinado** — todos os 5 revisores
   (prompt-engineer + senior-cto + data-engineer + financial-planner +
   product-manager + information-architect) deram OK em 2026-05-22.
2. Reservar **4 IDs ADR** em `docs/adr/`:
   - `boundary-llm-unified` (W1α + W1β).
   - `llm-telemetry-by-prompt-version` (W3).
   - `llm-cache-invalidation-policy` (W2/W3).
   - Errata in-place em [docs/adr/233-prompt-version-format.md](../../adr/233-prompt-version-format.md)
     (W2, nova §Migration).
3. Abrir lanes em `docs/sprint/A17/lanes/` (W4-T00 antecipado),
   `docs/sprint/A18/lanes/` (W1α), `docs/sprint/A20/lanes/` (W1β + W2 +
   W3 + W4-T01/T02).
4. Adicionar entry em [docs/_MOC/PLANS-active.md](../../_MOC/PLANS-active.md)
   apontando para este plano (IA identificou plano órfão).
5. Rodar `python3 dev/build_doc_index.py` (sem `--check`) para
   regenerar MOC pós-edit + commitar diff em `_generated/`.

## Onde isto fica quando concluído

- Lanes `docs/sprint/A17/lanes/a17-llm-hardening-w4-t00-seed.md`
  (antecipada com L3), `docs/sprint/A18/lanes/a18-llm-hardening-w1α-lgpd.md`,
  `docs/sprint/A20/lanes/a20-llm-hardening-w1β-adr090.md`,
  `a20-llm-hardening-w2-versioning-goldens.md`,
  `a20-llm-hardening-w3-telemetry.md`,
  `a20-llm-hardening-w4-cross-cutting.md`.
- Quando todas as ondas mergeadas: `git mv docs/plan/LLM_PROMPTS_HARDENING
  docs/archive/LLM_PROMPTS_HARDENING-YYYY-MM-DD/` + entry em
  [docs/archive/README.md](../../archive/README.md).

## Histórico de revisão

| Data | Revisor | Veredito | Mudanças incorporadas |
| --- | --- | --- | --- |
| 2026-05-22 | `prompt-engineer` (originador) | — | Diagnóstico inicial dos 9 prompts. |
| 2026-05-22 | `senior-cto` | Aprovado com ressalvas | 8 objeções: W1-T01 expandir escopo (serializer + validators + golden atomic), W1-T02 split PR-A/PR-B, consolidar 5 ADRs → 3, W3 callsite OTLP no backend, W4 depende de W1, estratégia teste snapshot bit-exact, custo cache invalidation, ADR cache invalidation. |
| 2026-05-22 | `data-engineer` | Aprovado com ressalvas (3 bloqueantes) | Pivot semver puro ([[ADR-233]] já decidido), reusar `FamilyMember.cpf_encrypted` (não criar `family_member_pii`), migration payloads `pipeline_artifacts` + JSON Schema string pattern, `additionalProperties: false`, persistir em `LLMCallLog` antes OTLP, RFB YAML versionado por ano-base. |
| 2026-05-22 | `financial-planner` | Aprovado com ressalvas (5 bloqueantes) | UX decrypt CPF no HTTP boundary autenticado, runbook anual RFB fevereiro, audit downstream Perini/AUVP/partilha precisão, +5 fixtures `informe_aluguel` (comunhão + dedução), +7 fixtures `informe_previdencia` (PGBL+VGBL mesmo CPF, regimes mistos, portabilidade), audit `institution_catalog` cobertura alta renda PJ, gap reconhecido de 3 prompts faltantes (corretora/DARF/FII), telemetria `riscos_truncados`. Aprovado sem mudança: cap parecer ≤12, e16 IMPOSTO APURADO. |
| 2026-05-22 | `product-manager` | Aprovado com ajustes bloqueantes | Split W1 em W1α (LGPD A18 gate Beta F7) + W1β (ADR-090 A20). W4-T00 antecipado para A17 L3 (independente). KR refinado: remove `confidence_p50`/`needs_review_rate` como gate (Goodhart); adiciona "F7 R4 LGPD checklist verde" + "0 incidentes 14d pós-cutover". 4 lanes follow-up viram slug+`proposed`: `a21-llm-drift-nightly-real`, `a21-prompts-faltantes-corretora-darf-fii`, `a21-eval-llm-judge-parecer`, `a21-rfb-codes-annual-update`. Sprint allocation corrigida: A17/A18/A20 (A12 está `paused`). |
| 2026-05-22 | `information-architect` | Aprovado com ajustes | Frontmatter passa `validate_frontmatter`. Filename↔id OK. Wikilink `[[INTERNAL_ADMIN]]` quebrado → `[[PLAN-internal-admin]]` (corrigido). Atualizar tags `sprint/a17`+`a18`+`a20`+`priority/p0`+`breaking/schema`. Plano órfão no grafo Obsidian — adicionar entry em `docs/_MOC/PLANS-active.md` (pré-requisito #4). Atomicidade OK (single-file _README.md segue padrão dos pares PLANNER_REVIEW/PLATFORM_REVIEW). Não criar `assets/` (sem mockups). |
