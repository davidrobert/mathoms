# Spec — endpoint "reprocessar documento" (contrato, sem implementação)

> Artefato derivado da lane [A32.l6](../lanes/A32-l6-review-ux-identidade-natureza.md)
> (PR3), decisão **Q3 do owner (2026-07-07)**: o botão "Reprocessar" NÃO entra
> na UI nesta sprint (dead UI proibida) — a lane entrega apenas este contrato
> para a sprint seguinte de review UX. **Não é fonte de verdade canônica**:
> a implementação deve abrir ADR `Proposto` própria (política P0/P1) e pode
> revisar qualquer decisão daqui.

## 1. Propósito

Na tela de review (pós-A32.l6), cada card aponta para um documento-fonte cuja
extração provavelmente falhou ("Falha na nossa leitura"). A ação natural do
usuário é "leia de novo" — hoje só existe via console interno
(`reset_workspace_from_stage`, ADR-116) ou script dirigido da l5. Este endpoint
expõe o re-processamento de **um documento** como ação de produto.

## 2. Contrato

### Request

```
POST /workspaces/{workspace_id}/pipeline/documents/{document_id}/reprocess
Authorization: Bearer <JWT>   (require_write_role)
Content-Type: application/json
```

```json
{
  "reason": "review_card",
  "review_id": "b7e2…"
}
```

| Campo | Tipo | Obrigatório | Semântica |
|---|---|---|---|
| `reason` | enum `review_card \| manual \| reclassification` | sim | Telemetria/auditoria — de onde veio o pedido. |
| `review_id` | string (UUID) | não | Quando disparado de um card de review, correlaciona a ação ao `StageReview`. |

### Response — `202 Accepted`

```json
{
  "document_id": "…",
  "tombstoned_artifacts": 2,
  "pipeline_run": { "…": "PipelineRunResponse (shape existente)" }
}
```

`response_model` explícito (ADR-102 R18) + `make update-openapi-snapshot`
no PR de implementação (ADR-109).

## 3. Semântica (ordem interna)

1. **Tombstone** dos artifacts E2* do documento via
   `backend/app/services/artifact_tombstone.py::tombstone_e2_artifacts_for_document`
   (ADR-311 D1): deleta rows de `pipeline_artifacts` dos stages E2*
   (`e2_tombstone_stage_names()`, aliases legacy+descritivo) casando por FK
   `document_id` **ou** prefixo `content_hash[:12]_` da key (ADR-084).
   Reusar o service existente — não duplicar a lógica de match.
2. **Re-queue incremental**: dispara `PipelineRun` com `incremental=true`
   (ADR-080) a partir dos stages de extração — o documento sem artifact é
   detectado por `_find_unprocessed_docs` e re-extraído; E3+ downstream
   re-executam com o artifact novo.
3. **Idempotência**: repetir o POST com run ativo NÃO cria segundo run
   (retorna `409`). Repetir após o run terminar re-tombstona e re-executa
   (operação é naturalmente re-aplicável; tombstone de zero rows é no-op).
4. **Auditoria**: log estruturado `mathoms.pipeline.artifact` (padrão do
   tombstone atual) + `reason`/`review_id` no payload do run.

## 4. Erros

| Status | Código | Quando |
|---|---|---|
| `404` | `document_not_found` | `document_id` inexistente ou de outro workspace (tenancy). |
| `409` | `pipeline_run_active` | Run `running`/`resuming` em andamento no workspace, ou review pendente bloqueante no mesmo run — retomar/concluir antes. |
| `409` | `document_not_processable` | `doc_type = other` sem rota de extração (nada a reprocessar). |
| `429` | `llm_budget_exhausted` | Cap mensal de budget LLM atingido (hard-stop ADR-173) — ver §5. |
| `403` | — | Papel sem escrita (RBAC existente, `require_write_role`). |

## 5. Custo LLM / cap (ADR-173)

- Reprocessar 1 documento re-executa **no pior caso** a extração LLM daquele
  documento (`extract_with_llm`) + stages determinísticos downstream (grátis).
  Custo unitário observado no dogfood da l5: centavos de dólar por documento
  (1 chamada de extração; reasks raros pós-ADR-292/294).
- O endpoint **não** cria categoria nova de gasto: passa pelo choke-point de
  budget existente — se o hard-stop mensal (ADR-173, teto configurável até
  US$ 300 via console ops, A31.l2) já disparou, o POST falha com `429`
  **antes** de tombstonar qualquer artifact (pré-check; nunca deixar o
  documento sem artifact e sem run).
- Sem rate-limit dedicado no MVP além do `409` de run ativo — 1 workspace
  não paraleliza runs, o que limita estruturalmente o abuso. Se a telemetria
  mostrar spam de reprocess, adicionar limite por documento/dia (padrão
  `invitation_service`, contador em DB).

## 6. Fora de escopo (deste contrato)

- Reprocess em lote (fleet-wide) — permanece no script dirigido da l5.
- Form tipado de correção pré-reprocess + micro-estados pós-ação — sprint
  seguinte de review UX (mesmo pacote da implementação deste endpoint).
- Re-extração automática em bump de `PROMPT_VERSION` — decisão de custo do
  owner (ver "Fora de escopo" no [_README da sprint](../_README.md)).

## 7. Critérios de aceite da implementação futura

1. ADR `Proposto` aberta antes do PR (política P0/P1) referenciando esta spec.
2. `pytest` cobrindo: tombstone chamado com os stages E2* corretos; `409` com
   run ativo; `429` com budget estourado; tenancy (`404` cross-workspace).
3. Snapshot OpenAPI commitado; teste de contrato no frontend se a UI consumir.
4. Card da review ganha o botão "Reprocessar" **somente** neste PR futuro —
   nunca antes do endpoint existir (Q3).
