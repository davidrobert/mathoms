# Runbook — Flip de schema-validation `warn→strict` per-stage

> **ADR:** [[ADR-284]] (Proposto · 2026-06-09) — mode_overrides per-schema +
> enforcement strict real; follow-up de [[ADR-283]] decisão D.
> **Afeta:** `config/pipeline.json → schema_validation`, hook pós-write de
> `DBArtifactStore.write` ([[ADR-212]]), todos os stages mapeados em
> `SCHEMA_BY_STAGE` (`backend/app/services/db_artifact_store.py`).
> **Owner:** operador on-call; mudanças de pré-condição revisam com `data-engineer`.
> **Rollback:** revert de 1 linha em `mode_overrides` (deploy de config normal).

## Por que este runbook existe

Validação de schema roda em modo `warn` global — drift de contrato só loga.
`strict` aborta o write do artefato (`jsonschema.ValidationError` propagada →
stage falha para aquele workspace; **dado não corrompe**, o write não
acontece). O flip é por schema (`mode_overrides`), nunca global de uma vez:
strict global abortaria runs em qualquer stage com drift não-mapeado. Este
runbook define o gate de promoção de cada schema, o procedimento e o rollback.

## 1. Pré-requisitos (gate antes de flipar)

Todos verificáveis; sem exceção informal.

### 1.1. Código de enforcement mergeado

- [ ] Raise em strict no `DBArtifactStore._validate_schema` ([[ADR-284]] §A).
- [ ] `ValidationError` não-retryable em `_run_stage_with_retry` ([[ADR-284]] §A).
- [ ] `mode_overrides` consumido por `_effective_schema_validation_mode` ([[ADR-284]] §C).

Verificação rápida:

```bash
pytest backend/tests/test_db_artifact_store_schema_strict.py -q   # 5 passed
```

### 1.2. Corpus golden verde em strict para o schema alvo

Para `e2_extract.schema.json`:

```bash
MATHOMS_PIPELINE_SCHEMA_MODE=strict pytest tests/test_e2_schema_strict_corpus.py -q
```

O flip exige adicionalmente que os buckets de débito do corpus estejam
resolvidos **ou aceitos por escrito** na linha do §7:

- `KNOWN_DRIFT_CASES` (vocabulário `instituicao`/`tipo_documento` vs
  `banco`/`tipo` — cdbresumo Itaú/Santander + writer E2-llm): **bloqueador**.
  Flipar com este bucket não-vazio aborta todo write E2-llm e de cdbresumo.
- `INPUT_GAPS` (parsers sem input sintético — PDFs de fatura dedicados, XLS
  binário): aceitável flipar se o baseline (§2) mostrar zero WARN nos tipos
  correspondentes na janela.

### 1.3. Baseline de 7 dias zero-WARN para o schema alvo

Janela mínima: **7 dias corridos** com pipeline ativo. Critério **binário**:
0 records para o schema alvo (strict não tem tolerância — qualquer WARN no
baseline vira run abortado pós-flip).

## 2. Pré-check — medir violações atuais em `warn`

Os records são WARNING no logger `mathoms.pipeline.schema_validation` (JSON
estruturado em prod, [[ADR-110]]), um por path distinto de drift, com
`workspace_id`, `stage`, `artifact_key`, `schema_name`, `validation_path`
(índices de array normalizados para `[]`), `validator_keyword`,
`occurrence_count`.

Agregação da janela (ajuste o sink — arquivo local / `docker logs` / agregador):

```bash
# Contagem por path de drift (a pergunta do go/no-go):
jq -r 'select(.logger=="mathoms.pipeline.schema_validation"
        and .schema_name=="e2_extract.schema.json")
       | [.validation_path, .validator_keyword] | @tsv' logs.jsonl \
  | sort | uniq -c | sort -rn

# Exposição: quais workspaces produziram drift na janela:
jq -r 'select(.logger=="mathoms.pipeline.schema_validation"
        and .schema_name=="e2_extract.schema.json")
       | .workspace_id' logs.jsonl | sort -u
```

**Go**: zero linhas nas duas queries para a janela de 7 dias.
**No-go**: qualquer linha → corrigir o writer (ou declarar o campo no schema,
se legítimo — ver gate `tests/test_e2_schema_strict_corpus.py`) e reiniciar a
janela.

## 3. Procedure de flip (per-stage)

### 3.1. Flip via mode_overrides per-schema (canônico — ADR-284)

1. Anuncie o flip (canal de ops) com link para a medição do §2.
2. PR de config — diff de 1 linha:

   ```json
   "schema_validation": {
     "enabled": true,
     "mode": "warn",
     "mode_overrides": { "e2_extract.schema.json": "strict" }
   }
   ```

3. Gate do PR: CI verde **inclui** o corpus em strict (§1.2) e o teste de
   keys de `mode_overrides`
   (`tests/test_schema_validation.py::TestModeOverridesPerSchema`).
4. Merge + deploy de config normal (squash, [[ADR-108]] flow).
5. Registre a linha no §7.

### 3.2. Flip global via MATHOMS_PIPELINE_SCHEMA_MODE (escape, não-cirúrgico)

`MATHOMS_PIPELINE_SCHEMA_MODE=strict` no env do worker força **todos** os
schemas — vence `mode_overrides`. Só para ambiente de staging/diagnóstico;
nunca como flip de prod (aborta qualquer stage com drift não-mapeado).

## 4. Validação pós-flip

Janela de observação: **48h ou ≥10 runs** (o que vier depois).

- Success rate de pipeline runs inalterado vs semana anterior.
- Zero `ValidationError` de `e2_extract.schema.json` em
  `pipeline_stage_logs.errors` / logs do worker.
- Records do logger `mathoms.pipeline.schema_validation` com
  `mode=strict, outcome=reject`: devem ser **zero** (qualquer um = um write
  bloqueado em prod → avalie rollback imediato, §5).

## 5. Rollback (warn ⟵ strict)

**Gatilho objetivo:** ≥1 run falhando por `ValidationError` do schema flipado
em workspace que não tinha WARN no baseline.

1. Revert do PR de config (a linha do `mode_overrides`) — `gh pr revert` ou
   PR manual de 1 linha. Deploy de config. RTO ~minutos.
2. O artefato rejeitado **não foi escrito** — não há dado a reparar. O run
   falhado retoma via UI (resume de stage) após o revert.
3. Abra issue com o `validation_path` rejeitado e workspace; o drift volta a
   ser WARN mensurável.

## 6. Critério de "stage promovido a strict"

Um schema é considerado promovido quando: flip mergeado (§3.1) + janela do §4
fechada sem rollback + linha registrada no §7. Próximo schema da fila repete
§1–§5 do zero (baseline próprio).

## 7. Histórico de flips

| Data | Schema | Operador | Violações pré-flip (7d) | Resultado |
| ---- | ------ | -------- | ----------------------- | --------- |
| —    | —      | —        | —                       | —         |

## O que este runbook NÃO cobre

- Schemas fora de `SCHEMA_BY_STAGE` (não validados no write — passthrough).
- Alerta automático de drift contínuo pós-flip — follow-up da [[ADR-284]]
  (ticket em rate>0/1h; não criar antes do primeiro flip).
- Mudança no **conteúdo** dos schemas (gate próprio:
  `tests/test_schema_validation.py` + corpus).

## Referências

- [[ADR-284]] — mode_overrides, enforcement strict, telemetria (decisão).
- [[ADR-283]] decisão D — fechamento de `additionalProperties` por transação.
- [[ADR-212]] — hook de validação pós-write no `DBArtifactStore`.
- [`pipeline_rollback.md`](pipeline_rollback.md) — rollback de pipeline (snapshot DB).
- `tests/test_e2_schema_strict_corpus.py` — corpus gate 22/22 writers.
