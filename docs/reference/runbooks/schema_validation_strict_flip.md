# Runbook — Flip de schema-validation `warn→strict` per-stage

> **ADR:** [[ADR-284]] (Proposto · 2026-06-09) — mode_overrides per-schema +
> enforcement strict real; follow-up de [[ADR-283]] decisão D.
> **Afeta:** `config/pipeline.json → schema_validation`, hook pós-write de
> `DBArtifactStore.write` ([[ADR-212]]), todos os stages mapeados em
> `SCHEMA_BY_STAGE` **e** `SCHEMA_BY_STAGE_KEY`
> (`backend/app/services/storage/db_artifact_store.py`) — desde a [[A42.l19]] a
> resolução é por `(stage, artifact_key)`, e os schemas por balde do E4 são
> alcançáveis **só** pelo segundo mapa.
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
pytest backend/tests/test_db_artifact_store_schema_strict.py -q   # verde
```

### 1.2. Corpus golden verde em strict para o schema alvo

Para `e2_extract.schema.json`:

```bash
MATHOMS_PIPELINE_SCHEMA_MODE=strict pytest tests/test_e2_schema_strict_corpus.py -q
```

O flip exige adicionalmente que os buckets de débito do corpus estejam
resolvidos **ou aceitos por escrito** na linha do §7:

- `KNOWN_DRIFT_CASES` (vocabulário `instituicao`/`tipo_documento` vs
  `banco`/`tipo`): **bloqueador** quando não-vazio. ✅ **Esvaziado em
  2026-06-10 ([[ADR-286]])** — cdbresumo emite `banco` aditivo; o writer
  E2-llm ganhou contrato dedicado `e2_llm_artifact.schema.json` (stage
  `E2-llm` remapeado em `SCHEMA_BY_STAGE`). Consequência: o ciclo deste
  runbook cobre **2 schemas E2 independentes** — `e2_extract.schema.json` e
  `e2_llm_artifact.schema.json` — cada um com baseline (§2) e flip (§3)
  próprios.
  **Atualização 2026-07-08 ([[ADR-312]]):** o writer E2-llm passou a
  canonical-only — não emite mais `instituicao`/`tipo_documento`
  top-level. `required` de `e2_llm_artifact.schema.json` mudou de
  `[instituicao, tipo_documento, moeda]` para `[banco, tipo, moeda]`;
  os campos legados viraram properties opcionais (só presentes em rows
  anteriores a 2026-07-08). **Se um baseline de 7 dias (§1.3) para este
  schema foi coletado antes de 2026-07-08, descarte e recolha** — ele
  mediria o vocabulário antigo, não o `required` real pós-cutover.
- `INPUT_GAPS` (parsers sem input sintético): aceitável flipar se o baseline
  (§2) mostrar zero WARN nos tipos correspondentes na janela. ✅ **Esvaziado
  em 2026-06-10 (A24.l7 passo 3)** — corpus cobre **22/22 writers** em
  real-parse (faturas PDF com layout sintético dedicado; XLS binário via
  `xlwt` dev-dep). Para `e2_extract` e `e2_llm_artifact`, a pré-condição de
  corpus está integralmente fechada — o gate restante é só o baseline (§1.3).

> ⚠️ **Correção de 2026-08-24 — o ✅ acima afirma cobertura sobre o corpus de
> parsers, e o stage tem writer que não é parser.** Medido no §Ataque da
> [[A40.l58]] (PR #1650): `e2_extract` drifta em **6/6 runs** da última janela,
> 54 artefatos, sempre `required $.banco` + `$.moeda`. A causa não é vocabulário
> — é `generate_llm_fallback` (`scripts/extract_bank_documents.py:101`), que
> persiste um stub sem `banco`/`moeda` sob `extract_statements`/`extract_invoices`
> quando nenhum parser reconhece o documento. Mesma classe da [[ADR-407]] (stage
> polimórfico com mapa 1:1 para schema).
>
> **O corpus 22/22 não o alcança por construção:**
> `tests/test_e2_schema_strict_corpus.py:353` enumera `registry._ALL_PARSERS`, e o
> `:363` **rejeita o shape por asserção** (`assert ... not
> result.get("requires_llm_fallback")`). Flipar `e2_extract` hoje aborta o write
> exatamente dos documentos que o parser não soube ler — o run morre em E2
> **antes** de o fallback LLM existir. Pré-condição de corpus de `e2_extract`:
> **reaberta**. Mudança de pré-condição revisa com `data-engineer` (§Owner).

### 1.3. Baseline de 7 dias zero-WARN para o schema alvo

Janela mínima: **7 dias corridos** com pipeline ativo. Critério **binário**:
0 records para o schema alvo (strict não tem tolerância — qualquer WARN no
baseline vira run abortado pós-flip).

**Desde 2026-08-24 ([[ADR-409]] §B) isto é um comando, não uma agregação de log:**

```bash
python3 dev/measure_schema_drift.py --schema <alvo> --days 7 --gate
```

**Leia a coluna `veredito`, não o exit code.** O exit `1` significa **há drift**, e
só isso — nunca significou `GO`/`NO-GO`. Um schema pode sair com exit `0` e **não**
ser promovível: massa trivial, contrato não re-derivado e cobertura incompleta são
guardas do veredito, e nenhuma delas muda o exit (vermelho ali trocaria falso-verde
por falso-vermelho, pela mesma razão escrita em `mass_trivial`). A afirmação
`Exit 0 = GO` vivia aqui desde 2026-08-24 e já era falsa quando a
[[A42.l26]] a mediu — `e4_pontos_milhas` saía `0` sem ser promovível.

O predicado do veredito tem quatro guardas, cada uma por um falso-verde medido:
**janela sem artefato não é GO** (ausência de medição — a cadência do dogfood é ~2
runs/semana); **artefato ilegível não é GO**; **contrato não re-derivado não é GO**
([[ADR-409]] §F); e **cobertura incompleta não é GO** ([[A42.l26]]) — se um nó do
payload emite chave que o contrato não declara, o `0 erros` não é afirmação sobre
aquele nó. As colunas `grão` e `cob` publicam a profundidade: `grão` é quantos itens
de coleção exigem alguma chave, `cob` é quantos nós emitem além do declarado. Cite
as duas no PR do flip, com os paths que o comando imprime.

O instrumento também reporta `documents` distintos — cite a massa em **documentos**,
não em artefatos, no PR do flip: 6 artefatos do mesmo documento em 6 runs não são 6
evidências.

A **fila de elegibilidade** medida está na [[ADR-409]] §D. Não a copie para cá: ela
se re-mede com o comando acima, e fila copiada apodrece no primeiro run novo.

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
   (`tests/test_schema_validation_telemetry.py::TestModeOverridesPerSchema`; o path
   antigo `tests/test_schema_validation.py` não existe — corrigido 2026-08-31).
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
   PR manual de 1 linha. Deploy de config **+ restart do worker** (ver correção
   abaixo). RTO ~minutos.

> ⚠️ **Correção de 2026-08-24 — sem restart, este rollback é inerte.** Medido no
> §Ataque da [[A40.l58]] (PR #1650): `load_json_config` cacheia `pipeline.json` em
> `_config_cache` (`scripts/pipeline_common.py:146`), então **reverter
> `mode_overrides` no disco não muda o modo efetivo do processo que está
> rodando** — segue `strict`, e o incidente continua. Só a limpeza do cache
> (≡ restart do worker) aplica o revert.
>
> O lever alternativo `MATHOMS_PIPELINE_SCHEMA_MODE=warn` **funciona**, e é
> **global**: medido com 2 schemas em `mode_overrides`, a env derruba o strict dos
> dois. Enquanto houver 1 schema promovido os dois levers são equivalentes; do 2º
> em diante ele despromove tudo em silêncio. Escolha do lever é decisão da ADR da
> [[A40.l58]] — até lá, **nenhum dos dois é quente**.
2. O artefato rejeitado **não foi escrito** — não há dado a reparar, e os
   baldes irmãos do mesmo stage voltam junto (a sessão é rolada em
   `pipeline_task.py::_rollback_and_close_artifact_session`). **O run falhado
   NÃO retoma por `resume`** — ver §8.3 passo 2.
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

## 8. Incidente — um run de cliente abortou por schema

> Gatilho `sre-devops`. Este é o único modo de falha que o flip **introduz**: em
> `strict`, `DBArtifactStore.write` levanta `jsonschema.ValidationError`, o stage
> falha para aquele workspace e o **dado não corrompe** — o write não acontece.

### 8.1. Confirmar que é abort de schema (30s)

O erro é **não-retryable por desenho** ([[ADR-284]] §A) — não houve backoff, a
falha é do primeiro attempt. Três sinais, em ordem de custo:

```sql
-- 1. o run e o stage onde parou
SELECT id, status, failed_at_stage, failure_reason FROM pipeline_runs
 WHERE status = 'failed' ORDER BY started_at DESC LIMIT 5;

-- 2. o erro do stage (a mensagem do raise nomeia stage/key/schema)
SELECT stage, status, errors FROM pipeline_stage_logs
 WHERE pipeline_run_id = '<run_id>' AND status = 'failed';
```

A mensagem do raise é
`payload de <stage>/<key> viola <schema> em modo strict`. O `reason_class`
gravado é **`output_invalid`** — contrato rejeitado, não bug nosso.

> ⚠️ Runs anteriores a 2026-08-24 gravaram `internal_error` para este caso: a
> `ValidationError` chega **nua** (vem do store, não de um provider) e caía no
> ramo genérico. Corrigido junto com este runbook; ao triar incidente antigo,
> não confie no `reason_class`.

3. Os **paths** em drift estão no logger `mathoms.pipeline.schema_validation`
   com `mode=strict, outcome=reject` — é o §4 deste runbook.

### 8.2. Decidir: rollback ou fix-forward

A pergunta que decide é **se o drift era conhecido**:

```bash
python3 dev/measure_schema_drift.py --schema <alvo> --days 7
```

| medição | leitura | ação |
| --- | --- | --- |
| o path que abortou **não** aparecia na janela do flip | drift novo — um writer mudou, ou chegou documento de forma nova | **rollback** (§5) e reabra a janela |
| o path **aparecia** e o flip foi feito assim mesmo | o gate foi contornado | **rollback** (§5) + postmortem do PR de flip |
| drift só neste workspace, contido, com fix trivial no writer | caso único | fix-forward, **avisando** que o schema segue `strict` |

Na dúvida, **rollback**. O custo de reabrir a janela é dias; o de manter cliente
com run abortado é confiança.

### 8.3. Executar

1. **Rollback** — §5. Lembre do **restart**: reverter `mode_overrides` no disco
   não muda o modo do worker vivo (`pipeline.json` é cacheado). Se precisar de
   segundos e não puder esperar deploy, use
   `MATHOMS_PIPELINE_SCHEMA_MODE=warn` + restart — mas ele é **global** e
   despromove todo schema já promovido ([[ADR-409]] §C). Registre no §7 quais
   voltaram a `warn`.
2. **Retomar o run — NÃO por `resume`.** Corrigido em 2026-08-31 (A42.l19):
   a rota existe no snapshot OpenAPI, mas a **pré-condição** não fora conferida.
   `pipeline_service.py::_flip_run_to_resuming` levanta
   `ValueError("Run is not paused for review (status: ...)")` para qualquer
   status ≠ `needs_review`, e run abortado por schema é **`failed`** (E4 é
   `criticality: required` por default em `stage_spec.py:61`, logo
   `resolve_stage_outcome` → `failed`, não `degraded`). O `_stages_after_paused`
   também lê `paused_at_stage`, não `failed_at_stage`.

   A recuperação real é **run novo pinado ao falho**: `from_stage` no stage que
   abortou + `base_run_id` do run falho ([[ADR-291]]), que lê os stages
   run-scoped a montante do base em vez de reprocessá-los. É operação diferente
   e gera `run_id` novo — não confunda os dois no incidente.
3. **Confirmar** — o run completa e `measure_schema_drift --days 1` mostra o path
   de volta como WARN (mensurável), não como abort.

### 8.4. Depois

- Linha no §7 com data, schema, path que abortou e desfecho.
- Se o drift era novo: o writer mudou sem o contrato acompanhar — a correção é do
  produtor ou do schema, com gatilho `data-engineer`, **antes** de reabrir a
  janela.
- A janela de baseline do schema **reinicia**. Não se re-promove no mesmo dia.

## O que este runbook NÃO cobre

- Schemas fora de `SCHEMA_BY_STAGE` **e** de `SCHEMA_BY_STAGE_KEY` (não validados
  no write — passthrough).
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
