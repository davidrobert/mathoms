---
type: moc
title: PIPELINE-REVIEWS-active — Rastreamento de revisões de pipeline
aliases: ["PIPELINE-REVIEWS", "PIPELINE-REVIEWS-active", "review-tracking", "pipeline-review-ledger"]
---

# PIPELINE-REVIEWS-active — Rastreamento de revisões de pipeline

> **Editorial.** Curado manualmente — **não é gerado**. Registro durável dos
> achados **sistêmicos/defeito** da skill `pipeline-review` ([[ADR-343]]).
> Uma seção por run; seções de runs 100% fechados viram histórico aqui mesmo.

## O que entra aqui (e o que NÃO entra) — [[ADR-343]]

Achados da `pipeline-review` são de duas naturezas; **só uma** aterrissa neste
arquivo:

- ✅ **Sistêmico / defeito** — afirmação sobre o **pipeline** (código, contrato
  de stage, schema, render, prompt, metodologia). Recorre entre runs e é
  **PII-free por construção**. Ex.: "checksum X lê campo morto `a.b`, deveria ler
  `a.c`". **Entra aqui**, keyed por `(dimensão, evidência-âncora, regra)` — âncora
  = `campo.dot.path` ou `arquivo:linha`, **nunca** um valor.
- ❌ **Instância / dado** — afirmação sobre os números **deste workspace neste
  run** (carrega PII, não recorre). **Fica off-git** em
  `storage/<uuid>/reviews/<ts>-<run8>/` junto com a síntese crua e o baseline.

**Commit-safe:** zero literal monetário, zero nome próprio. O título do achado
tem de ser um **defeito**, não um dado. Discriminador de workspace na seção =
`ws-<uuid8>` (nunca slug derivado de email). O hook de PII do pre-commit é
backstop, não garantia primária.

## Convenção de rastreamento (timeless)

Para que nenhum achado-defeito se perca entre runs:

1. **Cobertura 100%.** Cada run gera uma seção cobrindo **todos** os achados
   sistêmicos — inclusive refutados e não-acionáveis. Triagem só é completa
   quando todo item tem disposição.
2. **ADR/lane para o que tem peso de decisão.** Item que procede e altera
   decisão/invariante/contrato entra em ADR de veredito ou lane do BACKLOG.
   Refutado/não-acionável basta neste índice com 1-2 linhas de rationale + link à
   evidência. **Não** se exige "1 ADR por item".
3. **Aberto exige gatilho.** Item `procede-aberto` **deve** ter prioridade
   (P0-P3) + owner + link para lane ou ADR `Proposto`. `procede-aberto` sem
   gatilho é bug deste índice.
4. **Cadência.** Ao abrir run novo, revise a seção do anterior: todo
   `procede-aberto` que persiste é re-priorizado ou rebaixado a `aceito-wontfix`
   com rationale. Sem zumbis silenciosos.

**Severidade** (própria da skill, **não** a `DOC-*` do `audit-vault`):
`Crítico` · `Alto` · `Médio` · `Baixo`, cruzada com **Prioridade** `P0`–`P3`.
**Taxonomia de disposição** (reusada do `AUDITS-active`): `procede-fechado` ·
`procede-aberto` · `refutado` · `não-acionável` · `aceito-wontfix`.

**Formato de seção** (por run):

```
## rN — ws-<uuid8>-<AAAA-MM-DD>

> Skill pipeline-review ([[ADR-343]]) · run <run8> · tier <premium|free>.
> Execução: <status>, <N> docs, <dur> min, CV <ok>/<total>. Julgamento:
> <especialistas> em paralelo + verificação adversarial (<X>/<Y> confirmados).
> Cru + baseline em storage/<uuid>/reviews/ (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV01 — <defeito, com campo.dot.path ou arquivo:linha> | correção | Crítico | P0 | procede | procede-aberto | <lane/ADR/commit> |
```

Colunas: **Dimensão** ∈ correção · consistência · completude · clareza-ux ·
solidez-financeira · qualidade-llm · saúde-execução. **Trilha** = lane do
BACKLOG, ADR de veredito, ou commit que fechou.

---

## r1 — ws-1b9f2cf5-2026-07-25

> Skill pipeline-review ([[ADR-343]]) · run `5c030f1f` · tier premium.
> Execução: **completed**, 160 docs, 30.2 min, CV **16/16**. Julgamento:
> multi-lente (correção, consistência, completude, UX, solidez financeira,
> qualidade-llm, saúde-execução) + verificação empírica em stage logs / E5 /
> parecer `_meta` (achados abaixo confirmados; sem REFUTED nesta rodada).
> Cru + baseline: `storage/1b9f2cf5-…/reviews/20260725-1340-5c030f1f/` (off-git).
> Working: `_scratch/pipeline-review-5at5-2026-07-25.md`.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV01 — E2-llm `success` com skip silencioso (`queued` > `total_processed`, `errors=[]`) · `pipeline/stages/extract_with_llm.py` success gate | correção | Alto | P1 | procede | procede-aberto | owner: data-engineer · lane candidata: residual E2-llm honesty |
| RV02 — PII como chave de dict em `fluxo_caixa.por_fonte_detalhado` (label nominal vira key) | consistência | Alto | P1 | procede | procede-aberto | owner: data-engineer · member_id/account_id canônico |
| RV03 — `schema_validation_drift` em massa no stage `extract_statements` (log_tail WARNING) | correção | Médio | P1 | procede | procede-aberto | owner: data-engineer · inventário drift E2 schema |
| RV04 — `real_estate.alertas` não propagam para `alertas[]` top-level do E5 | clareza-ux | Médio | P2 | procede | procede-aberto | owner: e5/frontend |
| RV05 — contrato money misto string/number no payload E5 (`irpf_kpis.*`, `protecao_patrimonial.premio_*`, `ratios.rentabilidade_pct`) | consistência | Médio | P2 | procede | procede-aberto | owner: data-engineer · unificar serializer |
| RV06 — `pipeline_run_costs` vazio com `llm_call_log` populado (telemetria dual) | saúde-execução | Médio | P2 | procede | procede-aberto | owner: sre · unificar ou deprecar |
| RV07 — parecer: `evidencia_verification` com `number_in_prose` (riscos sem `$.path`) | qualidade-llm | Médio | P2 | procede | procede-aberto | owner: prompt-engineer · gate de citação |
| RV08 — `llm_call_log` subconta calls E2-llm vs `llm_usage.total_calls` do stage | saúde-execução | Médio | P2 | procede | procede-aberto | owner: sre · persist resilience |
| RV09 — `tributario.cascata` com `regime_nao_suportado` / `perfil_incompleto` sem UX de fechamento | completude | Médio | P2 | procede | procede-aberto | owner: product · BusinessProfile onboarding |
| RV10 — docs `needs_review` (other + informes) sem fecho no loop de run | completude | Médio | P2 | procede | procede-aberto | owner: product · review queue |
| RV11 — `llm_fallback` residual alto em extratos PDF (parser det. ausente/escalação) | saúde-execução | Médio | P2 | procede | procede-aberto | owner: e2 · parsers PDF |
| RV12 — parecer multi-risco não materializa em `tarefas[]` (bridge fraco) | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product · suggestion lifecycle |
| RV13 — `_report_lineage.source_document_ids_truncated` (cap de lista) | completude | Médio | P3 | procede | procede-aberto | owner: data-engineer · cap/paginação |
| RV14 — `cenarios_conjuge` unidimensional (matriz rasa) | solidez-financeira | Médio | P3 | procede | procede-aberto | owner: fin-planner · plano CENARIOS_ESTRESSE |
| RV15 — field_request_spurious residual no parecer (já guardrailed) | qualidade-llm | Baixo | P3 | aceito | aceito-wontfix | monitorar taxa; guardrail ativo |
| RV16 — `generate_narratives` duração sub-segundo (templates det., não LLM) | qualidade-llm | Baixo | P3 | não-acionável | não-acionável | by design se stage det.; documentar na UI se confunde |
| RV17 — CV 16/16 e run completed pós-fix C6 stale (#1079) | correção | — | — | positivo | procede-fechado | #1079 |

**Notas de re-triagem:** primeira seção do índice — sem `procede-aberto` anterior.

---

## r2 — ws-1b9f2cf5-2026-07-27

> Skill pipeline-review ([[ADR-343]]) · run `9d47574c` · tier premium · código `origin/main` **#1089**.
> Execução: **completed**, 160 docs, 17.4 min, CV **16/16**. Julgamento: 5 especialistas
> em paralelo (Workflow) + **verificação adversarial** (14 céticos, 1 por finding: 5
> CONFIRMED, 7 PARTIAL, 2 REFUTED) + verificação direta do loop principal nos claims
> determinísticos. Cru + baseline durável: `storage/1b9f2cf5-…/reviews/20260727-1835-9d47574c/`
> (off-git); working: `_scratch/pipeline-review-5at5-2026-07-27.md`.
> Conservação verificada: ledger E3 fecha em zero (105/105 artefatos); a "perda de tx"
> da hipótese foi **refutada** (dedup legítimo). Baseline durável 1º deste ws (habilita `--compare`).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV2-01 — parecer `metricas[]` sem âncora `$.path` escapam do verify (`parecer_evidencia.py::_iter_items` só itera riscos+sugestões) → métrica user-facing não verificável/fabricável | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: prompt-engineer · lane a abrir |
| RV2-02 — `extract_with_llm.py:224-232,583` `success=len(errors)==0` com doc enfileirado descartado no guard de texto/imagem vazia (0 sinal, run não pausa) | correção | Alto | P1 | procede | procede-aberto | owner: senior-cto/e2 · re-teste RV01 (confirmado c/ linha) |
| RV2-03 — `previdencia_analyzer.py:168-176` emite nota "teto atingido" sem ramificar por `PgblStatus` (modelo_simplificado colapsa → conselho invertido) | correção | Alto | P1 | procede | procede-aberto | owner: financial-planner · lane a abrir |
| RV2-04 — parecer `sugestoes_*` (P0-P2, com dedup_key) não consolidam em `tarefas[]` (1 item determinístico) | clareza-ux | Alto | P2 | procede | procede-aberto | owner: product · re-teste RV12 |
| RV2-05 — CV16/CV17 (conservação `severity=error`, ADR-330/336) fora do gate `_CONSERVATION_CHECKS` (`validate_cross.py:479`); falha não pausa run | correção | Médio | P2 | procede (latente) | procede-aberto | owner: data-engineer/senior-cto · lane a abrir |
| RV2-06 — money/pct string vs number no view-model E5 (`ratios.rentabilidade_pct` str vs `ratios.taxa_poupanca_recorrente_pct` float) | consistência | Médio | P2 | procede | procede-aberto | owner: data-engineer · re-teste RV05 (ADR-090) |
| RV2-07 — PII como CHAVE de dict em `fluxo_caixa.por_fonte_detalhado` (label nominal vira key; instável + vaza) | consistência | Médio | P2 | procede | procede-aberto | owner: data-engineer · re-teste RV02 (fonte_id canônico) |
| RV2-08 — `exposicao_cambial` conta só caixa ME, omite bucket Internacional da carteira (divergência de classificação; `asset_classifier` sem keyword) | solidez-financeira | Médio | P2 | procede | procede-aberto | owner: financial-planner/data-engineer · ADR-193 |
| RV2-09 — parecer `riscos[0]` rotula `reserva_emergencia.receita_pj_pct` (=PJ/(PJ+CLT)) como "% da receita" (base trocada) | qualidade-llm | Médio | P2 | procede | procede-aberto | owner: prompt-engineer · anotar escalar no exec-context |
| RV2-10 — riscos citam % na prosa com `ancoras=[]` e escapam do `evidencia_verification` (só R$/$.path cobertos) | qualidade-llm | Médio | P2 | procede | procede-aberto | owner: prompt-engineer · re-teste RV07 (ampliado a %) |
| RV2-11 — `_meta.evidencia_verification.item_index` out-of-range vs `riscos[]` (índice posicional stale pós enforce_strict_per_item) | qualidade-llm | Médio | P2 | procede | procede-aberto | owner: prompt-engineer · id estável por item |
| RV2-12 — `alertas[]` top-level dead field (`reports.ts:132`, sem consumidor React) + `real_estate.alertas` sem surface global; colisão de nome (list[str] vs list[dict]) | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer · RV04 reenquadrado (não é propagação) |
| RV2-13 — identidade de imóvel fragmentada: mesma matrícula com `property_id` distintos entre `imoveis[]`/`excluded_properties[]` | consistência | Médio | P2 | procede | procede-aberto | owner: data-engineer · [[ADR-246]] |
| RV2-14 — `_report_lineage.source_document_ids` truncado (cap) + ID scheme incompatível (`source`=UUID vs `consumed`=chave composta) | completude | Médio | P2 | procede | procede-aberto | owner: data-engineer · re-teste RV13 ([[ADR-278]]) |
| RV2-15 — `cenarios_conjuge` unidimensional + `premissas.retorno_real_anual_pct` desalinhado da `meta_pct` | solidez-financeira | Médio | P3 | procede | procede-aberto | owner: financial-planner · re-teste RV14 |
| RV2-16 — investigar `validation_path` recorrente do drift `e2_extract` (drift É persistido em `output_summary`, non-gated by design — RV03 "log-only" refutado) | saúde-execução | Baixo | P3 | procede (reenquadrado) | procede-aberto | owner: data-engineer · re-teste RV03 |
| RV2-17 — falta assertiva única de conservação de CONTAGEM E2→E4 concentrada (ledger fecha 105/105 mas implícito) | saúde-execução | Baixo | P3 | procede (observab.) | procede-aberto | owner: data-engineer · LC-01 re-teste (perda refutada) |
| RV2-18 — `tributario.cascata` perfil_incompleto sem nudge PJ + inconsistência `receita_pj_detectada_anual=0.0` vs `receita_pj_pct` | completude | Baixo | P3 | procede | procede-aberto | owner: product/financial-planner · RV09 render refutado; domínio persiste |
| RV2-19 — aluguel IRPF-declarado vs banco-observado (bases distintas) sem disclosure; `passive_income` usa o menor | consistência | Baixo | P3 | procede | procede-aberto | owner: financial-planner · explicitar base |
| RV2-20 — `premissas_economicas` global vazia p/ o período (todas as classes de ativo `indisponivel`) → projeção em fallback | completude | Baixo | P3 | procede | procede-aberto | owner: data-engineer · seed global ("MC 100% fallback" refutado) |
| RV2-21 — `diagnostico_comportamental` raso by-design (catálogo determinístico fixo) sem degradê por cobertura de categorização | qualidade-llm | Baixo | P3 | procede | procede-aberto | owner: financial-planner · é determinístico (não LLM) |
| RV2-22 — `pipeline_run_costs` órfã dead schema (SSOT = `llm_call_log`, DE-01/ADR-173) | consistência | Baixo | P3 | procede | procede-aberto | owner: data-engineer · RV06 dual-telemetria refutada; só higiene (drop) |
| RV2-23 — docs `needs_review` pós-`completed` sem surface no view-model/run_meta (só query DB) | completude | Baixo | P3 | procede | procede-aberto | owner: product · re-teste RV10 |
| RV2-24 — limiar de taxa de poupança divergente parecer (referência 30%) vs E5 `diagnostico` (25%) | qualidade-llm | Baixo | P3 | procede | procede-aberto | owner: prompt-engineer · fonte única ([[ADR-143]]) |
| RV2-25 — `field_request_spurious` dispara p/ `[]` (JSONPath resolve não-nulo → "presente") | qualidade-llm | Baixo | P3 | procede | procede-aberto | owner: prompt-engineer · re-teste RV15 (null-semantics) |
| RV2-26 — `protecao_patrimonial.premio_decomposicao` atribui 100% a "auto" apesar de apólice multi-bem (imóvel+veículo) | consistência | Baixo | P3 | procede | procede-aberto | owner: financial-planner · ratear multi-bem |
| RV2-27 — CV16 `<=` unilateral: `receita_outras` é resíduo derivado (`total−explicit`), Σ==total seria vacuous | correção | — | — | refutado | refutado | verify adversarial (proposta não adiciona poder) |
| RV2-28 — `trs_efetiva_pct` (yield de renda) vs meta 5% é like-for-like (taxa de retirada segura), não apples/oranges | correção | — | — | refutado | refutado | verify adversarial |
| RV2-29 — `llm_fallback` residual alto em PDF (RV11): neste run E2-llm = 0 calls (parsers determinísticos cobrem) — não reproduzido | saúde-execução | — | — | não-reproduzido | não-acionável | #1079/#1080/#1089 |
| RV2-30 — subcontagem de telemetria E2-llm (RV08): artefato de lock SQLite local, não recorre em Postgres | saúde-execução | — | — | refutado (dev-env) | não-acionável | caveat de ambiente |
| RV2-31 — CV 16/16 · conservação E3 fecha (105/105) · run completed em #1089 (timeout 300s #1079 segurou) | correção | — | — | positivo | procede-fechado | #1089 |

**Re-triagem da r1** (run 5c030f1f) — todo `procede-aberto` anterior tem disposição em r2:
RV01→**RV2-02** (aberto, +linha de código); RV02→**RV2-07** (aberto); RV03→**RV2-16** (reenquadrado Baixo — drift É persistido, "log-only" refutado); RV04→**RV2-12** (reenquadrado — não é propagação, é dead-field + colisão); RV05→**RV2-06** (aberto); RV06→**RV2-22** (dual-telemetria **refutada** como defeito — só higiene de dead schema); RV07→**RV2-10** (aberto, ampliado a %); RV08→**RV2-30** (**refutado**, dev-env); RV09→**RV2-18** (render **refutado**, domínio persiste); RV10→**RV2-23** (aberto); RV11→**RV2-29** (**não-reproduzido** — fallback 0 neste run); RV12→**RV2-04** (aberto); RV13→**RV2-14** (aberto, +ID scheme); RV14→**RV2-15** (aberto); RV15→**RV2-25** (aberto Baixo); RV16→não-acionável (mantido); RV17→**RV2-31** (positivo, mantido). Novos em r2: RV2-01, RV2-03, RV2-05, RV2-08, RV2-09, RV2-11, RV2-13, RV2-17, RV2-19, RV2-20, RV2-21, RV2-24, RV2-26, RV2-27, RV2-28.
