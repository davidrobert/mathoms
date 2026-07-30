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

---

## r3 — ws-1b9f2cf5-2026-07-29

> **Revisão de relatório**, não execução de pipeline ([[ADR-343]]) · report `7a7e9333`
> sobre run `573a54a7` (pré-existente, tier premium) · código `origin/main` **#1111**.
> Nenhum stage foi re-executado; o objeto é o **artefato entregue** (view-model E5 +
> parecer + renderer). Julgamento: 6 lentes especializadas em paralelo + 1 lente de
> design + **braço cego** (leu só os dados determinísticos, sem ver o parecer, para
> testar convergência da recomendação nº 1). 188 achados brutos → 36 clusters + 23 de
> design → **verificação adversarial de 44 céticos** (7 CONFIRMADO, 37 PARCIAL, 0
> REFUTADO) + **crítico de completude** que auditou o próprio processo.
> Fechamento determinístico: `dev/certify_ledger_local.py` (conservação tol-zero,
> 105/105) + medição própria de duplicação cross-grupo.
> Cru + síntese com valores: `storage/1b9f2cf5-…/reviews/2026-07-29-573a54a7/` (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV3-01 — dupla contagem cross-grupo no razão E4: `banco` sem normalização de caixa (`c6bank`↔`C6Bank`, `itau`↔`Itau`) + `titular` vazio numa das pernas ⇒ `transaction_hash` divergente fura o dedup K4; mesmo lançamento entra por `tipo_conta=extrato` e `tipo_conta=extratoconta` | correção | Crítico | P0 | procede (medido) | procede-aberto | owner: data-engineer · lane a abrir · [[ADR-350]]? |
| RV3-02 — `fluxo_caixa.janela_12m.*` tem **zero consumidores** em `frontend/src`; todo número de fluxo na tela/PDF vem do bloco de janela `full` (`FluxoMensalChart.tsx:82,92`, `conclusionUtils.ts:109`) enquanto o valor canônico de 12m existe no payload | consistência | Alto | P0 | procede (causa-raiz) | procede-aberto | owner: senior-cto · absorve RV3-16/RV3-17 |
| RV3-03 — `SectionSummary.tsx:23` lê `narrativas[<ID maiúsculo>]`; builder emite `narrativas.summaries.<id minúsculo>` como **string** (componente espera objeto) ⇒ 16/16 parágrafos de abertura não renderizam; gate CV9 verde mede geração, não entrega | completude | Alto | P0 | procede | procede-aberto | owner: senior-cto · lane a abrir |
| RV3-04 — `S_PROTECAO` `enabled: false` (`report_layout.yaml`) com componente entregue e testado + ausente de `MIGRATED_SECTIONS`; `buildNavGroups`/`tocGroups` em `ReportShell.tsx:107-126,187-207` não filtram `enabled` ⇒ âncora de nav sem alvo em 100% dos relatórios | completude | Alto | P1 | procede | procede-aberto | owner: product-designer · [[ADR-240]] §Entrega sem registro do flip |
| RV3-05 — `S9RiscosSection.tsx:87` colapsa a seção inteira por `narrativas.charts.bubble_riscos.data_state=="empty"`, imprimindo antes a linha-promessa de `conclusionUtils.ts:204`; `ParecerRisksTable.tsx:139` emite `§<section_id>` como texto puro ⇒ ponteiro do parecer leva a seção vazia | clareza-ux | Alto | P1 | procede | procede-aberto | owner: product-designer · lane a abrir |
| RV3-06 — descrição cartorial crua do IRPF interpolada verbatim em `RealEstateYieldCard.tsx:194,303,373` e `EndividamentoCard.tsx:75` (CPF de terceiro, matrícula, inscrição municipal, endereço) sem gate de PII no view-model; [[ADR-337]] é escopada a `top_ativos[].nome` | correção | Alto | P1 | procede | procede-aberto | owner: data-engineer+sre · critério 4 da ADR-337 inexistente |
| RV3-07 — ordenação do plano sem critério encodado: maior alavanca declarada (regime PJ / anexo) bloqueada por `tributario.regime=None`+`motivo_nao_suportado="perfil_incompleto"` e **sem pendência acionável** que peça regime/CNAE/pró-labore | solidez-financeira | Alto | P1 | procede | procede-aberto | owner: financial-planner+product-manager · absorve achado órfão FP-21 |
| RV3-08 — nenhum dos paths do manifest do parecer toca `$.real_estate`/`$.tributario`; a mesma `section_whitelist` gateia `get_e5_section` e `planner_drill_down.py:145` ⇒ dado renderizado na tela é inalcançável pela narrativa LLM | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: prompt-engineer · gate próprio já emite WARNING com EXIT=0 |
| RV3-09 — `suggestion_rules.py:123` lê `meses_cobertura`; E5 emite `reserva_emergencia.cobertura_meses` ⇒ regra inerte. 10/10 regras retornam vazio neste payload (demais por campos de [[ADR-161]] latentes) | completude | Alto | P2 | procede | procede-aberto | owner: data-engineer · sub-claim "família não é alertada" **refutado** (`pontos_urgentes_analyzer:137` lê o nome certo) |
| RV3-10 — `dependentes_menores_18` como `rationale` de gap de proteção contra `irpf_kpis.dependentes.count=0`: premissa da recomendação nº 1 contestada dentro do próprio payload | consistência | Alto | P2 | procede | procede-aberto | owner: financial-planner · dado do dono, não análise |
| RV3-11 — `tributario` materializado em `build_config_overrides_from_db`→`_setup_run_context` no início do run, com `_latest_run_id` resolvendo para o run corrente cujo E4 ainda não existe ⇒ todo input run-scoped zerado; regen não corrige | correção | Alto | P2 | procede | procede-aberto | RV2-18 **FU-2 medido** (rótulo "FIXADO" era falso) |
| RV3-12 — `EndividamentoCard.tsx:77,80` lê `d.valor`/`d.taxa`; contrato E5 emite `saldo_devedor`/`taxa_juros`/`parcela_mensal` sem adapter no boundary | consistência | Alto | P2 | procede | procede-aberto | owner: senior-cto · `types/report-analysis.ts:137-145` desalinhado |
| RV3-13 — `diagnostico_confianca` é a única chave top-level do view-model com **zero consumidores**; `dataQualitySignals.ts:54-67` recomputa o share no cliente sobre outra janela ⇒ três percentuais para o mesmo conceito na mesma tela | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer · [[ADR-353]] degrada mas não surfaça |
| RV3-14 — prazo de IF impresso como fato (`HeroKpiGrid.tsx:266-271`, `Stat "Ano projetado"`) com `if_monte_carlo.prob_if_ate_idade_meta` e divergência vs `p50_ano_if` só em `text-xs` | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer+financial-planner |
| RV3-15 — `ParecerRisksTable.tsx:41,93`: `TOP_LIMIT` fixo com rótulo hardcoded "de baixa severidade" para o resto, enquanto a composição real do `extra` inclui severidade média | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer · print CSS já força expansão no PDF |
| RV3-16 — `FluxoMensalChart.tsx:76-88` `buildContext` declara a janela do slice e cita agregado de janela `full`; substitui `narrativas.charts.fluxo_mensal.context` | consistência | Alto | P1 | procede | procede-fechado-em | sintoma de **RV3-02** |
| RV3-17 — `ConsumoConscienteCard.tsx:45` exibe `consumo_consciente.total_pontuais` (janela `full`) em bloco que declara 12m; `total_pontuais_janela` tem 0 hits em `frontend/src`; `consumo.analise` emitida como string pré-formatada en-US | consistência | Alto | P2 | procede | procede-fechado-em | sintoma de **RV3-02** + string formatada no E5 |
| RV3-18 — mesma matrícula com `property_id` distintos ⇒ lista de excluídos repete o mesmo imóvel; banner conta registros, não imóveis | consistência | Alto | P2 | procede | procede-aberto | JÁ-CONHECIDO **RV2-13** ([[ADR-246]]) |
| RV3-19 — `Metrica` (schema do parecer) sem campo `ancoras`; `_iter_items`/`stamp_ancora_values` cobrem riscos+horizontes ⇒ `valor_atual` é o único número autorado pelo LLM sem verify | qualidade-llm | Alto | P1 | procede | procede-aberto | JÁ-CONHECIDO **RV2-01** · 10/10 valores deste run re-derivados e **conferem** (zero fabricação realizada) |
| RV3-20 — `aporte_investimento` vazio na janela ⇒ mecanismo `despesa_consumo = total − aporte` no-op e `despesa_consumo == despesa_total` | solidez-financeira | Alto | P1 | procede | procede-aberto | JÁ-CONHECIDO **LC04-r3** · ver [[ADR-333]] |
| RV3-21 — `nao_identificado` por **valor** cruza o limiar de degradação na janela de 12m (maior que na janela `full`) | solidez-financeira | Alto | P2 | procede (medição) | procede-aberto | MEDIÇÃO de **LC05-r3** · [[ADR-353]] degrada, não bloqueia |
| RV3-22 — `ratios.*_pct` como string onde consumidores fazem aritmética (`conclusionUtils.ts:135-142` cai em fallback por `typeof !== "number"`) | consistência | Médio | P2 | procede | procede-aberto | JÁ-CONHECIDO **RV2-06** ([[ADR-090]]) |
| RV3-23 — KPIs do hero não passam por `<MonetaryValue/>` (`HeroKpiGrid.tsx:323-331` devolve string; `ui/Kpi.tsx:76-86` sem `tabular-nums`); definição do KPI protagonista só em `title` de `<span>` não-focável | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer · viola §Design System do CLAUDE.md + A11Y_CHECKLIST 4.1.2 |
| RV3-24 — jargão de implementação no bloco de premissas (`ReportPremissasBlock.tsx:97-104`: "snapshot E5", endpoint, hash de integridade) contra `COPY_GUIDELINES.md:263-280` | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer |
| RV3-25 — abreviação `k`/`M` em valor monetário (`ReceitaDespesaMensalChart.tsx:216-220`; narrativa E5.N verbatim em `PerfilFamiliaCard.tsx:29-30`) contra `COPY_GUIDELINES.md:196-197` (`mil`/`mi`/`bi`) | clareza-ux | Baixo | P3 | procede | procede-aberto | owner: prompt-engineer (fonte) + product-designer (render) |
| RV3-26 — `S7IndependenciaSection.tsx:96` lê `goals.trs_pct` (inexistente no payload; chave real `goals.if_trs`) e cai em default hardcoded que também alimenta o tone do KPI | correção | Médio | P2 | procede (latente) | procede-aberto | owner: senior-cto · coincide hoje, mente se o dono configurar outro alvo |
| RV3-27 — `real_estate.imoveis[].valor_imovel` zero tratado como valor real no render (`RealEstateYieldCard.tsx:202`) contra `COPY_GUIDELINES.md:199-207` (ausência ⇒ `—`) | clareza-ux | Médio | P3 | procede | procede-aberto | owner: data-engineer (origem do zero) + product-designer |
| RV3-28 — ponteiros `section_id` do parecer apontam seções que não hospedam o card citado; **o mapa de referência é ele mesmo incoerente** (`report_layout.yaml:356` titula S8 por um domínio cujo card vive em S7) | consistência | Médio | P2 | procede (reenquadrado) | procede-aberto | severidade Alto original presumia ponteiro navegável (é texto puro) |
| RV3-29 — base do rebalanceamento (`goals.alocacao_alvo.derived.carteira_liquida_brl`) difere de 4 outras bases patrimoniais do payload sem rótulo que declare o escopo | clareza-ux | Médio | P2 | procede (rebaixado) | procede-aberto | rebaixado pelo crítico: são **5** bases, e o delta é escopo deliberado (reserva/ilíquido fora), não dinheiro ignorado |
| RV3-30 — conversões de câmbio aparecem em `nao_identificado` e novamente como receita na moeda destino | correção | Médio | P2 | procede | procede-aberto | owner: data-engineer · faceta de RV3-01 |
| RV3-31 — duas taxas de retirada (yield-alvo na meta vs SWR na estimativa) | solidez-financeira | Baixo | P3 | **refutado** | não-acionável | decisão explícita: [[ADR-191]] §Emenda 2026-07-15 + `FORMULAS.md:94` "nunca colapsar"; aceite cumprido nas 2 superfícies |
| RV3-32 — `pipeline_run_costs` órfã (SSOT é `llm_call_log`) | saúde-execução | Baixo | P3 | procede (higiene) | procede-aberto | JÁ-CONHECIDO **RV2-22** |
| RV3-33 — achados **inertes** (defeito real sem alcance ao usuário nesta config): ranking de despesa na narrativa (não renderiza por RV3-03), `alertas[]` dead-field, e 5 correlatos | — | — | — | procede-inerte | não-acionável | reavaliar quando RV3-03 fechar — o conteúdo passa a aparecer |

**Positivos verificados:** conservação do razão fecha em tol-zero (105/105 grupos-fonte,
baldes `despesas`/`receitas` fechando em cents); zero-write do harness confirmado;
`PremissasFallbackAlert` dispara corretamente quando as premissas são parciais;
`formatProbability` evita 0%/100% enganosos; card de rentabilidade rotula desvio vs meta
com variante crítica correta (hipótese de "vender ok ao usuário" **refutada**);
apêndice sem dado é omitido em vez de renderizar vazio.

**Débito de método desta rodada** (o crítico de completude auditou o processo e achou
três furos que valem mais que vários achados):
1. **A lente de design não entrou no circuito de clusterização/ceticismo** na primeira
   passagem — a dimensão `clareza-ux` ficou com zero cobertura verificada até uma
   passagem cética dedicada ser rodada depois. Gate para a próxima: conferir que o campo
   `lentes` dos clusters cobre o conjunto de lentes executadas.
2. **O merge vazou 96 dos 188 achados de lente** (21 vivos órfãos, 5 deles Alto). Exigir
   disposição explícita por achado antes de fechar a etapa de clusterização.
3. **Zero REFUTADO em 36 clusters** — calibração frouxa do passo cético (tudo virou
   PARCIAL com severidade rebaixada). As refutações reais vieram do crítico e da medição
   determinística, não dos céticos.
4. **Conservação por grupo não detecta duplicação entre grupos** — este run passa em
   tol-zero com duplicação material (RV3-01). `ledger-certify` precisa de check
   cross-grupo por `(data, valor, descrição-normalizada, contraparte)`.
5. **Ninguém renderizou tela nem PDF** — toda afirmação de `clareza-ux` é inferência de
   código cruzada com payload, e está rotulada como tal.
