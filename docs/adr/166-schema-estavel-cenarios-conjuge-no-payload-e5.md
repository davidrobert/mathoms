---
id: ADR-166
type: adr
title: "Schema estável `cenarios_conjuge` no payload E5"
status: Decidido
phase: "A8.4"
date: "2026-05-06"
relates_to: ["[[ADR-076]]", "[[ADR-143]]", "[[ADR-144]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 166"]
tags:
  - type/adr
  - status/decidido
size_lines: 57
---

# ADR-166 — Schema estável `cenarios_conjuge` no payload E5

**Status:** Decidido (A8.4) • **Data:** 2026-05-06 • **Relaciona** [ADR-076](#adr-076--design-tokens-unificados-site--relatório), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76), [ADR-144](#adr-144--section_summaries-llm-driven-em-e5-com-cache--fallback-determinístico-v29).

**Contexto:** O payload E5 usava chave dinâmica derivada do `_CONJUGE_KEY` do workspace: `f"cenarios_{_CONJUGE_KEY}"` produzia `cenarios_mariana` no workspace piloto, `cenarios_ana` em outro hipotético. O serializer (`pipeline/domain/services/e5_serialization.py:266`) recebia `cenarios_conjuge_key` como parâmetro mutável; producer real (`scripts/e5_analyze.py:147`) computava o key via `_CONJUGE_KEY`. Frontend hardcodava `cenarios_mariana` em 3 components + types. A divergência era estrutural — pipeline interno já tratava com chave fixa `cenarios_conjuge` (default no `E5SerializationInputs`), apenas a serialização final acoplava ao workspace.

ADR-143 (methodology = code) é taxativa: chaves universais devem ser fixas; conteúdo workspace fica no DB ou em `notes/`. Acoplar key de payload a config de workspace é exatamente o anti-padrão que ADR-143 combate. Frontend lendo `cenarios_mariana` em workspace que tem `_CONJUGE_KEY="ana"` falha silenciosamente — outro sintoma da chave dinâmica.

**Decisão:** Chave de payload E5 passa a ser literal **`cenarios_conjuge`**, fixa, não-configurável. Todos os 5 sites do producer (`e5_serialization.py`, `e5_analyze.py:147,3105`, `e5n_narrativas.py:68`, `narrativas/context.py:59`) emitem ou esperam `"cenarios_conjuge"` literal. O campo `cenarios_conjuge_key` é removido do `E5SerializationInputs` (era variável; vira impossível).

Frontend mantém **fallback dual-key transitório** (`data.cenarios_conjuge ?? data.cenarios_mariana`) durante PR1 → PR3 para suportar artifacts E5 antigos em `pipeline_artifacts.content_json`. Após backfill em prod (script `dev/backfill_e5_universal_keys.py`, idempotente), PR3 remove o fallback.

LLM cache (ADR-144) **invalida automaticamente** porque `compute_snapshot_hash(section_payload)` muda quando a key muda — re-narração de S7/T5 acontece naturalmente; custo: ~2 chamadas LLM por workspace × N workspaces.

**Não toca** `key_cenarios_section` (em `narrativas/context.py:67`, derivado de `f"{conjuge_key}_cenarios"`) — é chave de seção de narrativas, distinta do bloco de cenários do payload, fora deste escopo.

**Consequências:**

- ✅ Payload E5 universal: workspace com qualquer `_CONJUGE_KEY` emite `cenarios_conjuge`; frontend lê chave única.
- ✅ Test inverter `test_cenarios_conjuge_usa_key_configuravel` → `test_cenarios_conjuge_usa_chave_universal_estavel` documenta que a chave é fixa pós-PR1; remoção do parâmetro variável é regressão-bloqueada por dataclass shape.
- ✅ Sem schema migration de DB — `pipeline_artifacts.content_json` é JSON cru sem index sobre a chave. `MATHOMS_SCHEMA_VERSION` não aplicável (endpoint `/reports/{id}/data` retorna `{type: object}`).
- ✅ OpenAPI snapshot inalterado.
- ⚠️ Workspaces com artifacts E5 antigos têm `cenarios_mariana` no JSON; frontend depende do fallback até backfill rodar. Janela: PR1 mergeado → backfill manual → PR3 remove fallback.
- ⚠️ Logging `INFO` em `mathoms.pipeline.e5_serialization` (`extra={"key": "cenarios_conjuge", "has_data": ...}`) confirma migração via Loki/Cloudwatch.

**Backfill operacional:**

```bash
# Pós-merge PR1, antes de PR3:
python -m dev.backfill_e5_universal_keys
# Idempotente. Itera workspaces com last_report_at < PR1_merge_time
# e dispara `analyze_finances`. LLM cache re-narrate S7/T5.

# Validação:
psql -c "SELECT COUNT(*) FROM pipeline_artifacts
         WHERE stage IN ('E5','analyze_finances')
           AND content_json::text LIKE '%cenarios_mariana%';"
# Esperado: 0 antes de mergear PR3.
```

**Follow-ups:**

1. PR3 (A8.4) remove fallback dual-key no frontend. Pré-requisito: backfill rodado, query acima zerada.
2. ✅ **ADR-176 (Proposto, 2026-05-06):** `key_cenarios_section` (`{conjuge_key}_cenarios`)
   migrada para chave universal `"cenarios_conjuge"` no bloco de narrativas E5.N.
   Fechou esse follow-up — bug visível ("Cenários de Estresse" renderizando
   placeholder) era sintoma da chave dinâmica ainda em uso. Ver
   [ADR-176](#adr-176--chave-estável-cenarios_conjuge-no-bloco-de-narrativas-e5n).
3. ✅ **W1-T08 (PLATFORM_REVIEW_PLAN, 2026-05-06):** schema E5 declara
   `cenarios_conjuge` formalmente — `properties.cenarios_conjuge` em
   [config/schemas/e5_analysis.schema.json](../config/schemas/e5_analysis.schema.json)
   (paridade `to_legacy_dict()`; `patternProperties` para
   `idade_<titular>_if`/`idade_<titular>` cobre titular_key arbitrário).
   Cobertura em `tests/test_schema_validation.py`. Modo continua `warn`;
   cutover `strict` é W6-T01.
