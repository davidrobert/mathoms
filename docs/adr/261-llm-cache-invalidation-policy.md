---
id: ADR-261
type: adr
title: "Política de cache invalidation em bump de PROMPT_VERSION — re-extrair vs. servir stale"
status: Proposto
phase: A20.W2
date: "2026-05-22"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-212]]"
  - "[[ADR-233]]"
  - "[[ADR-242]]"
  - "[[ADR-260]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 261"
  - "LLM cache invalidation"
  - "Prompt bump policy"
tags:
  - area/llm
  - area/pipeline
  - area/finops
  - status/proposto
  - type/adr
---

# ADR-261 — Política de cache invalidation em bump de PROMPT_VERSION

**Status:** Proposto • **Data:** 2026-05-22 • **Relaciona** [[ADR-081]] (regex→LLM→needs_review), [[ADR-212]] (DBArtifactStore + pipeline_artifacts), [[ADR-233]] (formato PROMPT_VERSION semver puro), [[ADR-260]] (telemetria por prompt_version).

## Contexto

[[ADR-233]] decidiu que bump de `PROMPT_VERSION` é obrigatório quando conteúdo de prompt muda (gate CI `dev/check_prompt_version_bumped.py`). Razão: garantir que cache LLM (interno do LiteLLM + cache em `pipeline_artifacts.payload`) não sirva resposta stale após mudança de prompt.

**Lacuna**: ADR-233 trata da **detecção** (gate força bump), mas não da **política operacional** após o bump:

1. **Cache interno do LiteLLM** (hash de `(system+user+model+temperature)`) é invalidado automaticamente quando `PROMPT_VERSION` muda o conteúdo. ✅ resolvido.
2. **Artifacts em `pipeline_artifacts`** com `metadata.prompt_version="1.0.0"` continuam servindo o output antigo para qualquer consumer que lê o artifact. **Não é cache estritamente, mas é "resposta congelada"** que pode ser servida em UI mesmo após bump.
3. **Re-extração custa $$$** — Anthropic Sonnet 4 a ~$3/1M input + $15/1M output, com prompts de 5-10k tokens cada. Bump de prompt em massa pode custar centenas de dólares × N workspaces × N documentos.

Plano [[PLAN-llm-prompts-hardening]] W1α + W1β + W2 propõe bumps coordenados em **6 prompts simultâneos** (`e15_baseline`, `e1_members`, `informe_aluguel`, `apolice`, `crlv`, `e16_irpf_full`, `informe_previdencia` — migration semver puro). Sem política explícita, decisão fica no review do PR e é inconsistente.

Dogfood atual = 1 workspace dogfood. Custo total de re-extração agora é trivial (~$5-10 estimado). **Mas o gate precisa estar pronto para beta fechado** quando workspaces × documentos sobe.

**Sintoma observado em produção (2026-05-23):** workspace dogfood, relatório `fae3544d-0588-4344-bf37-6fe12749571d`, card "Consumo Consciente" mostra linha "Parcelas pagas Crédito Imobiliário - Contrato 999.999 - Recursos Próprios (ano 2025)" R$ 50.000,00 com `categoria: nao_identificado`. Diagnóstico: [[ADR-242]] mergeou em `main` 21/maio 19:53 (PR #410, bump `PROMPT_VERSION` 1.0.0 → 1.1.0 com sentinel `info_fiscal_anual`); artifact `extract_with_llm` do informe IR foi gravado **antes** do bump e o classifier corrente lê `categoria_sugerida=null|legacy`, não skipa, e a linha cai em `despesas` como `nao_identificado`. Comentário em [pipeline/stages/extract_with_llm.py:399-400](../../pipeline/stages/extract_with_llm.py:399) é honesto sobre o gap: "Invalidação por bump de PROMPT_VERSION exige re-delete manual de artifacts antigos (runbook), não auto-skip aqui." Caso é **Tier 2 (minor bump)** desta política — sem implementação atual, usuário só recupera o fix via reset cirúrgico manual.

## Decisão

**Política de cache invalidation em 3 tiers, baseada no semver do bump:**

### Tier 1 — Patch (`1.0.0 → 1.0.1`): servir stale OK, sem re-extração

Bump patch é cosmético/typo/reformat. **Output esperado mantém shape e semântica.** Servir artifact antigo (`metadata.prompt_version="1.0.0"`) ao consumer downstream é seguro.

- `pipeline_artifacts` antigos **não** são marcados para re-extração.
- Próxima execução do pipeline (workspace novo, re-upload de doc) usa nova versão; antigos ficam congelados.
- **Custo**: $0 imediato. Comparação histórica via [[ADR-260]] confidence telemetry detecta drift se houver.

### Tier 2 — Minor (`1.0.0 → 1.1.0`): servir stale OK, re-extração opcional sob demanda

Bump minor adiciona campo opcional, regra adicional não-breaking, refinamento de instrução. Output antigo continua válido mas pode estar sub-especificado.

- `pipeline_artifacts` antigos **não** são marcados para re-extração automática.
- **UI `/documents` ganha botão "Re-extrair com nova versão"** para o usuário decidir (audit log).
- Cron job opcional `mathoms_reextract_stale_artifacts` (intervalo configurável) re-extrai N artifacts mais antigos por dia, com budget mensal.
- **Custo**: pago por workspace ativo conforme decisão de UI/cron. Telemetria `mathoms.llm.reextract_total{prompt_version, trigger}` em [[ADR-260]].

### Tier 3 — Major (`1.0.0 → 2.0.0`): re-extração **obrigatória** programada

Bump major muda contrato semântico — schema de output muda, regras de extração incompatíveis com cache prévio. Output antigo é stale **e** pode quebrar consumer downstream.

- Migration Alembic correspondente marca `pipeline_artifacts` afetados com `metadata.reextract_required=true`.
- Cron job `mathoms_reextract_required_artifacts` (a cada N horas) processa fila em background; bloqueia consumer se artifact não-re-extraído.
- **Hard gate em consumer**: `DBArtifactStore.read()` levanta `StaleArtifactError` quando `payload_version < schema_version_atual` E `prompt_version` é major-anterior. Force re-extração on-demand.
- **Custo**: estimado **antes** do PR via `dev/estimate_reextract_cost.py` novo: `prompt_version_bump × N_workspaces × N_docs_por_prompt × tokens_médios × $/1M`. PR review **deve** incluir essa estimativa.

### Snapshot histórico pré-bump

**Sempre** (independente do tier), antes de mergear bump de `PROMPT_VERSION`:

```bash
python3 dev/snapshot_llm_call_log_history.py \
    --prompt-name <prompt_name> \
    --output _scratch/llm_call_log_<prompt_name>_pre_bump_<date>.csv
```

Preserva grep histórico em `LLMCallLog` antes de migration coordenada (caso W2-T01 de [[PLAN-llm-prompts-hardening]]: `<slug>-v1.X.Y` → `1.X.Y`).

## Implicações

- **`pipeline_artifacts.metadata`** ganha campo opcional `reextract_required: bool`. Migration aditiva.
- **`DBArtifactStore.read()`** ganha guard `StaleArtifactError` quando major-anterior. Breaking change minor em consumer mas comportamento desejado.
- **2 cron jobs novos** (Celery beat): `mathoms_reextract_stale_artifacts` (Tier 2 opcional) + `mathoms_reextract_required_artifacts` (Tier 3 obrigatório). Reserva entry em `backend/app/tasks/reextract.py`.
- **1 helper novo**: `dev/estimate_reextract_cost.py` — pre-bump cost estimation.
- **1 helper novo**: `dev/snapshot_llm_call_log_history.py` — snapshot histórico pré-bump.
- **UI** `/documents` ganha botão "Re-extrair" condicional ao tier do prompt afetado.
- **Telemetria** `mathoms.llm.reextract_total{prompt_version, trigger}` ([[ADR-260]]).

## Alternativas consideradas

**A. Sempre re-extrair tudo em qualquer bump.** Rejeitado: patch cosmético não justifica custo. Quebra previsibilidade de custo.

**B. Nunca re-extrair (servir stale para sempre).** Rejeitado: bump major implica schema breaking; consumer downstream pode falhar lendo output antigo.

**C. Servir o output antigo até consumer pedir re-extração explicitamente (lazy invalidation).** Rejeitado para Tier 3: race condition entre consumer lendo stale e cron re-extraindo. Hard gate em consumer (`StaleArtifactError`) é mais seguro.

**D. Estimar custo apenas em PR review do bump, sem helper.** Rejeitado: depender de estimativa manual em PR review introduz drift de cálculo. `dev/estimate_reextract_cost.py` é fonte única de verdade.

## Referências

- Plano canônico: [[PLAN-llm-prompts-hardening]] §W2-T01 (migration semver) + §Riscos (custo cache invalidation).
- [[ADR-233]] formato semver puro + gate CI bump.
- [[ADR-212]] DBArtifactStore + `pipeline_artifacts`.
- [[ADR-260]] telemetria por prompt_version (campo `mathoms.llm.reextract_total`).
- Cost reference: Anthropic pricing 2026 Sonnet 4 ~$3/$15 per 1M tokens (verificar antes do PR).
