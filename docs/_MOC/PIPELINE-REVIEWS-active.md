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
5. **Fronteira.** `rN` aqui numera **runs de pipeline** (a skill dispara a
   execução). Revisão de **relatório já entregue**, sem run, vai para
   [[REPORT-REVIEWS-active]] — a cadência do item 4 **não cruza** os dois
   registros, para que um run novo não herde a triagem de achados que não são
   dele.

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
| RV2-05 — CV16/CV17 (conservação `severity=error`, ADR-330/336) fora do gate `_CONSERVATION_CHECKS` (`validate_cross.py:479`); falha não pausa run | correção | Médio | P2 | procede (latente) | procede-aberto | owner: data-engineer/senior-cto · [[A42.l4]] (residual adotado; agravado por RV4-20) |
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

> **Movida.** Revisão de **relatório entregue**, não run de pipeline — vive em
> [[REPORT-REVIEWS-active]] (mesma seção, códigos `RV3-*` inalterados). Este stub
> preserva a âncora histórica `#r3--ws-1b9f2cf5-2026-07-29` para PRs e commits que
> já a citam (`2fda9a91`, #1112).
---

## r4 — ws-1b9f2cf5-2026-08-04

> Skill pipeline-review ([[ADR-343]]) · run `82b30303` · tier premium · código `origin/main` **tip `66c3475b`**.
> Execução: **completed**, 18/18 stages, 163 docs, 22,1 min, **CV 16/16** (`falhas=[]`), 6 calls LLM.
> Julgamento: 5 especialistas em paralelo (Workflow) + **verificação adversarial** (41 agentes; 74 findings →
> 25 CONFIRMED, 42 PARTIAL, 7 REFUTED, 0 sem veredito) + verificação direta do loop principal.
> Cru + baseline durável: `storage/1b9f2cf5-…/reviews/20260804-1525-82b30303/` (off-git);
> working: `_scratch/pipeline-review-<ws>-2026-08-04.md`. Anti-regressão: `compare_reviews` exit **0**
> contra r2 **e** r3 — nenhuma regressão HARD.
> **1 achado de instância/dado ficou off-git** (agrupamento de balde tributário na pizza de despesas).

**Preflight que mudou o resultado.** O worker Celery compartilhado rodava código **38 commits atrasado** —
justamente parecer, cone de IF ([[ADR-360]]/[[ADR-361]]), tributário run-scoped (A40.l9) e narrativas.
Revisar isso re-derivaria bugs já consertados. O run foi executado com um worker deste worktree
(`PYTHONPATH` vence o finder do editable install, que aponta para o checkout principal), e a
atualidade do código foi **provada pelo output**: `if_monte_carlo.p*_censurado`/`seed_usado` só existem
pós-#1162/#1156.

| Código | Achado (defeito) | Dimensão | Sev | Prio | Dif | Risco | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|---|---|---|
| RV4-01 | `unlock_documents` (stage 1/18) chama `load_passwords()` antes do glob de cifrados e faz `sys.exit(1)` — run inteiro morre sem nenhum documento cifrado, e o arquivo de senhas só chega ao tenant via `config_materializer.py:44-47` (`copytree` de path bloqueado por `.gitignore` + `check_forbidden_paths.py`), logo deploy limpo não consegue criá-lo | saúde-execução | Alto | **P0** | M | Médio | PARTIAL | procede-aberto | senior-cto · reproduzido por mutação + run real `failed` · sem cobertura (workaround assado no fixture) · [[A42.l1]] |
| RV4-02 | `_narrate_top5_decisoes` descarta `decisoes[0]`: `_fmt_aporte_head` ocupa "Prioridade 1" incondicionalmente e a fila é enumerada de `[1:5]` — decisão registrada pelo dono não chega à única seção que responde "o que fazer", e duplica quando outra decisão da fila é de aporte (`charts_narrator.py:417-433`) | clareza-ux | Alto | **P0** | M | Médio | CONFIRMED | procede-aberto | product-designer + financial-planner (2 lentes, mesma causa) · render confirmado em `S10SinteseSection.tsx:16-17` |
| RV4-03 | `llm_call_log.stage` é `String(64)` e 2 writers interpolam filename — chave estoura a coluna, Postgres levanta `StringDataRightTruncation`, a exceção é engolida em WARNING (`litellm_client.py:342-350`) e a row de custo desaparece; derrota o hard-stop da [[ADR-173]], cuja SSOT é essa tabela | correção | Alto | P1 | S | Baixo | PARTIAL | procede-aberto | data-engineer · **provado em Postgres real** · impacto se realiza no cutover, não hoje · precedente de fix em `comprovantes_bens_llm.py:54-63` · [[A42.l7]] |
| RV4-04 | Janela canônica 12m não tem teto na data de análise: `_compute_janela_12m` fatia `meses[-12:]` e divide por `len` sobre série sem teto (`fluxo_caixa_enricher.py:424-427` + `cash_flow_builder.py:378`) — slots de meses não decorridos entram no divisor e diluem toda base mensalizada; dispara alarme falso de vacância (`generate_narratives.py:249-261`) | correção | Alto | P1 | M | Alto | PARTIAL | procede-aberto | financial-planner · nenhum CV cobre a base (CV8 re-deriva a razão) · emenda a [[ADR-306]] D3 · [[A42.l8]] |
| RV4-05 | Universo de meses do fluxo é a união das pernas receita+despesa com zero-fill, então mês documentado só em receita entra no denominador da despesa como zero — segunda causa, independente do teto de data (`fluxo_caixa_enricher.py:426-437`) | correção | Médio | P1 | M | Alto | PARTIAL | procede-aberto | data-engineer · **par com RV4-04** (mesmo fix) · [[A42.l8]] |
| RV4-06 | Adapter publica a meta de IF pelo múltiplo do yield-alvo e **descarta** a meta conservadora já derivada e persistida no agregado (`pipeline_adapter.py:204` ignora `derived.if_meta_conservadora_brl`; `goal_service.py:126` calcula as duas) — prontidão de IF superestimada em termos relativos e componente de score de peso 2,0 inflado | solidez-financeira | Alto | P1 | M | Alto | PARTIAL | procede-aberto | financial-planner · **atenção:** rotular a meta pelo yield é decisão declarada em [[ADR-191]] §Aceite — o defeito é a escolha do adapter, não o rótulo |
| RV4-07 | E2 descarta o token de tipo do lançamento que a fonte fornece (`c6bank.py:373` reconhece, `:489` joga fora), sobrando só o favorecido — evento patrimonial (quitação de dívida a instituição credora declarada) cai em `nao_identificado` e entra 100% no numerador de consumo; sem guard de dominância de transação única em balde | correção | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner · causa-raiz achada pelo verificador no PDF de origem + ausência de contrapartida em 106 grupos E3 · [[A42.l2]] |
| RV4-08 | Perna de cascade de IPTU/condomínio/taxa de administração não é plumbada: campos que o extrator de informe produz (`informe_aluguel.py:79-95`) são descartados em `real_estate_e5_integration.py:250-258` e nunca setados em `real_estate_adapter.py:188-197`; `CascadeSources` não tem perna de despesa — o cap rate "líquido" publica esses custos como zero, contra [[ADR-216]] D6, que os declara **observados** | solidez-financeira | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner · provado por execução · viola ADR `Decidido` |
| RV4-09 | Bloco `scalar` denso do manifest do parecer sofre corte silencioso de 300 chars (`parecer_planejador.yaml:499` + `parecer_distiller.py:107,131`) sem marcador: 7 blocos truncam, o pior perdendo ~90% — o parecer raciocina sobre uma fração do payload de Monte Carlo enquanto emite risco de IF ancorado nele, **com folga de budget não usada** | qualidade-llm | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner (reenquadrado pelo verificador) · resíduo da migração scalar→key_value de [[ADR-341]] D3 |
| RV4-10 | `_dedup_excluded_projection` é inerte por construção: `_identity_key` chaveia por `property_id` — o exato campo cuja fragmentação deveria colapsar — e nenhum dos 2 passes de remap resgata; invariante [[ADR-334]] D3 (`imoveis ∩ excluded == ∅`) não aplicado e override manual do dono fica sem efeito monetário | consistência | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner · **escalação de RV2-13** (de `consistência` p/ `correção`) |
| RV4-11 | YAML de layout deixou de governar o render nos dois sentidos: item `enabled: true` sem componente existente, e `navigation` com link para seção `enabled: false` → âncora morta no TOC (`ReportShell.tsx:90-137,187-207` não filtram por `enabled`; `ReportToc.tsx:115-118` é no-op silencioso). Falha WCAG 2.4.4/2.4.7 + buraco de numeração | clareza-ux | Alto | P1 | M | Baixo | CONFIRMED | procede-aberto | product-designer · **prova de render** (shell real) · agrava: componente da seção existe como dead code órfão e a métrica server-side afirma que renderizou |
| RV4-12 | Termo de marca metodológica proibido (COPY_GUIDELINES §13.1) chega ao TOC web via `title` de seção no YAML de layout; o gate `check_sigilo_terms.py:107-111` não cobre `config/report_layout.yaml` nem `frontend/src/generated/` — rodado contra os dois e contra `--all`: exit 0 | clareza-ux | Alto | P1 | S | Baixo | PARTIAL | procede-aberto | product-designer · PDF **não** afetado (TOC é `no-print`) · existe cópia saneada do título em `S_ProtecaoSection.tsx:20` |
| RV4-13 | `_resolve_aliquota_ir` ancora a alíquota efetiva no ano-base de `passive_income`, que pode ser o exercício que o próprio relatório marca `incompleto` (`ratios_calculator.py:334-338`), enquanto o bloco IRPF usa o ano completo — mesma fórmula, anos diferentes, sem disclosure; **inverte veredito** contra o target que o parecer publica | qualidade-llm | Alto | P1 | M | Médio | CONFIRMED | procede-aberto | prompt-engineer · exercício incompleto tem 1 de 2 declarantes (perde no numerador **e** no denominador) |
| RV4-14 | `llm_call_log` perde toda call posterior ao 1º write de artifact do stage sob SQLite — stage multi-documento registra 1 row de N e a verdade in-memory (`LLMRunSummary`) nunca é reconciliada contra o SSOT | saúde-execução | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | senior-cto · causa é contenção SQLite (dev), não recorre em Postgres · **par com RV4-03** · [[A42.l7]] |
| RV4-15 | Predicado de presença de artefato E2 no sync de documentos ignora o payload (`document_pipeline_sync.py:88-95`), então stub de escalação satisfaz "extraído" — limpa `needs_review` e liga o badge; os outros 2 consumidores do mesmo fato inspecionam o payload (`extract_with_llm.py:80`, `e3_reconciler_adapter.py:234`) | consistência | Médio | P2 | S | Médio | PARTIAL | procede-aberto | senior-cto · extrair predicado único `is_e2_extracted(payload)` · [[A42.l6]] |
| RV4-16 | Limiar de confiança declarado nos schemas de extração é aplicado em 1 de 3 stages, e nenhum dos 3 emite `validation` no `output_summary` — o canal único de pausa (`pipeline_task.py:1205-1211`) é inalcançável e extração de confiança baixa é consumida a jusante sem rótulo | correção | Médio | P2 | M | Médio | PARTIAL | procede-aberto | senior-cto · vizinho de [[ADR-357]] · acoplar a A40.l21 |
| RV4-17 | Perna de volume do gate anti-regressão é morta: `compare_reviews.py:154` busca folha `transacoes_total` que não existe no view-model E5, `_sum_leaf` devolve `None` e o guard `if b and …` (`:232`) torna o check inalcançável; 3 dos 10 campos de `run_health` do snapshot durável são null | saúde-execução | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | senior-cto · **a perna de drift de valor cobre o caso** (perda de metade das tx → 158 regressões HARD, medido) · [[A42.l3]] |
| RV4-18 | `StageLogTail.emit` descarta todo `extra` do log record (`observability/logger.py:170-177`) e 6 módulos logam fora do namespace capturado — os WARNINGs de drift de schema chegam ao registro durável como eventos idênticos sem `validation_path`/`validator_keyword`/`occurrence_count` | saúde-execução | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | senior-cto · **sharpening de RV2-16** (o drift É persistido, mas cego) · [[ADR-284]] · [[A42.l3]] |
| RV4-19 | `document_pipeline_sync` hardcoda 3 stages E2 e desconhece os stages de extração criados pós-[[ADR-216]]/[[ADR-238]]/[[ADR-239]] — documentos efetivamente extraídos ficam marcados "sem extrato" e `status='processed'` é promovido incondicionalmente | consistência | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | senior-cto · derivar do `STAGE_REGISTRY` + teste de completude que falhe na próxima ADR · [[A42.l6]] |
| RV4-20 | "CV n/n OK" é auto-referente ao E5 (`validate_cross.py:709` lê 1 artefato; nenhum check lê E2/E3/E4) e o denominador é auto-normalizante — check que não consegue avaliar devolve `None` e **evapora** da conta em vez de aparecer como `skipped`; provado por mutação que ausência de input produz falso-verde | correção | Médio | P2 | M | Baixo | CONFIRMED | procede-aberto | senior-cto · **sharpening de RV2-17** · piso de contagem por check-id · [[A42.l4]] |
| RV4-21 | `pipeline_artifacts.document_id` nunca é populado no write-path, então as duas queries reversas de lineage filtram por coluna 100% NULL e devolvem `[]` silencioso (falso-negativo, não erro) — e o teste passa porque a fixture semeia um shape que nenhum produtor emite | completude | Médio | P2 | M | Médio | PARTIAL | procede-aberto | data-engineer · falso-verde de fixture é a parte mais sólida · **sharpening de RV2-14** · [[ADR-278]] · [[A42.l6]] |
| RV4-22 | Skip incremental grava `status='completed'` com `output_summary={"skipped": true}` enquanto skip de LLM grava `status='skipped'` — "n/n stages completed" não é sinal de trabalho feito e o baseline de duração fica inatribuível | saúde-execução | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | data-engineer · propagar o retorno do stage para o enum que os leitores consultam · [[A42.l7]] |
| RV4-23 | Artefato do parecer é persistido sem validação JSON-schema pós-write (`SCHEMA_BY_STAGE` sem entrada para `review_finances_holistic` nem `extract_members`) e com `schema_version` NULL, embora o schema exista e seja exercitado só em teste — e o artefato **deste run viola** o schema (`_meta.tool_iterations` acima do `maximum`) | consistência | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | data-engineer · **ordem obrigatória:** corrigir o schema antes de gatear, senão `strict` derruba o parecer · [[A42.l6]] |
| RV4-24 | Ramo `empty` da S9 é o único alcançável em qualquer workspace porque o aggregate `Risk` tem 0 rows em todos eles (`seed_default_risks` sem call-site de produção; wiring deferido nunca entregou) — a cláusula determinística de gap de proteção existente fica morta | completude | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | financial-planner · o texto **não** chega ao leitor (EmptyState, [[ADR-356]] §D7) — a contradição vive no payload |
| RV4-25 | Componente de proteção declarado em ADR `Decidido` nunca foi implementado no score (composição vive com 5 componentes, `status` hardcoded) e não há penalidade por qualidade de dado — classificação favorável convive com gap de proteção sinalizado em outras superfícies | solidez-financeira | Médio | P2 | M | Alto | PARTIAL | procede-aberto | financial-planner · [[ADR-217]] §D1 · metade já é RV3-13 / A40.l11 — não duplicar |
| RV4-26 | Categoria de aporte é transferência patrimonial em um bloco e gasto discricionário em outro: **4 listas paralelas** de categoria (`fluxo_caixa_enricher.py:74`, `consumo_consciente_calculator.py:58-74`, `report/consumo_pontuais.py:18-21`, +1) divergem, e poupança é contada como consumo pontual | consistência | Médio | P2 | S | Médio | PARTIAL | procede-aberto | financial-planner · [[ADR-333]] · derivar de fonte única (cuidado com erro de 2ª ordem no fix ingênuo) · [[A42.l8]] |
| RV4-27 | Base da TRS é publicada como escalar sem composição, e a maior parte dela é imóvel (parte com classificação pendente) — o parecer rotula o número como carteira financeira contra o guardrail do próprio prompt | solidez-financeira | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | financial-planner · incluir imóvel na base é **decisão declarada** em [[ADR-164]] §1 — o defeito é a ausência de decomposição |
| RV4-28 | Custo essencial lê só `categorias_in` (`fluxo_caixa_enricher.py:117-125`); `categorias_out` e o sub-bloco `impostos.{incluir,excluir}` do `scoring.json` são **config morta sem leitor**, deixando o balde de impostos inteiro fora do essencial contra a regra declarada | solidez-financeira | Médio | P2 | S | Médio | PARTIAL | procede-aberto | financial-planner · pré-requisito do deferimento **segue não cumprido** p/ guias federais sem discriminador PF/PJ · [[A42.l8]] |
| RV4-29 | `premissas_economicas.status` é binário sem estado terminal (`economic_assumptions_snapshot.py:30`, `any(...)`): 1 de N e N de N produzem a mesma string "parcial", e o parecer escreve "ao menos uma premissa" quando nenhuma existe; o cone de probabilidade roda com sigma de constante hardcoded sem proveniência | completude | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | financial-planner + prompt-engineer (2 lentes) · **sharpening de RV2-20** · `_SIGMA_POR_PERFIL` é dead code |
| RV4-30 | `_split_gastos` do equilíbrio presente/futuro tem `else` exaustivo (`equilibrio_cerbasi_analyzer.py:202-213`), então tudo que não é futuro cai em "presente" — inclusive tributo de PJ, impostos e o balde não identificado; a whitelist `categorias_presente` (13 entradas) é **config morta** | consistência | Médio | P2 | M | Médio | PARTIAL | procede-aberto | financial-planner · sob a lista declarada o percentual publicado **inverte** (medido) |
| RV4-31 | Gate do chart derruba a seção de riscos inteira (`S9RiscosSection.tsx:83,100-108`), tirando do ar 4 cards `enabled: true` que não dependem do aggregate vazio; e a seção de proteção está duplamente apagada (`enabled: false` **e** fora de `MIGRATED_SECTIONS`) apesar de payload e componente prontos | clareza-ux | Médio | P2 | M | Médio | PARTIAL | procede-aberto | product-designer · **par com RV4-11 e RV4-24** |
| RV4-32 | Caminho primário do doughnut de despesas escapa do mapa único de labels (`categoryLabels.ts:52-58` faz lookup exato em snake_case; o wire emite `.title()` de `fluxo_caixa_enricher.py:404`) — fatias renderizam rótulo não-canônico, parte sem diacrítico, divergindo do rótulo que a tabela da mesma seção imprime | clareza-ux | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | product-designer · o teste que "prova" a humanização usa fixture que o backend não emite |
| RV4-33 | No doughnut de despesas o contexto renderizado é calculado sobre a janela plotada e a conclusão sobre o período completo, sem rótulo de base em nenhuma das duas (`DespesasDoughnutChart.tsx:204-205` vs `conclusionUtils.ts:151-158`) — o percentual citado contradiz a fatia visível | consistência | Médio | P2 | M | Médio | PARTIAL | procede-aberto | product-designer · deduplicar contra A40.l15 item 1, não abrir lane nova |
| RV4-34 | Prosa gerada no pipeline formata número monetário/percentual com f-string en-US (`consumo_consciente_calculator.py:283-285`, `pontos_fortes_analyzer.py:118-119`) e é renderizada verbatim ao lado de KPIs corretos — os helpers pt-BR existem em `narrativas/format_helpers.py` e não são importados. Viola COPY_GUIDELINES §4.1 | clareza-ux | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | product-designer · estender `dev/check_monetary_render.py` |
| RV4-35 | Dois limiares do **mesmo** bloco de config para a mesma métrica são impressos ambos com a palavra "referência" em seções diferentes do mesmo relatório (`scoring.json:156` vs `:159`) — há faixa em que uma seção chama de ponto forte o que a outra chama de abaixo do ideal | consistência | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | product-designer · **escalação de RV2-24** (agora as duas afirmações são do E5 e as duas estão na tela) · fix é vocabulário, não unificar valor |
| RV4-36 | KPI de cobertura de citação do parecer não tem grão de ITEM: a unidade é a citação (contrato pinado por teste), então item sem âncora nenhuma não gera entry e `coverage_failed` fica em zero com a maioria dos itens ancoráveis sem citação; o piso de densidade é insensível | qualidade-llm | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | prompt-engineer · **relacionado a RV2-01/RV2-10** · budget explícito exige ADR ([[ADR-358]]) |
| RV4-37 | Catálogo de citação renderiza folha não-monetária como valor em R$ (`parecer_citation_catalog.py:199` hardcoda o hint `brl`) enquanto o stamping usa `ancora_format_hint` para o mesmo path — probabilidade e idade entram no prompt como moeda | qualidade-llm | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | prompt-engineer · fix melhor é **não catalogar** folha cujo hint ≠ `brl` (`monetary_only: true`) |
| RV4-38 | Rede pós-LLM de rebaixamento de confiança sob premissa em fallback depende da âncora que o próprio LLM escolheu (`parecer_pos_llm_guardrails.py:65-68,83-85`) — claim de Monte Carlo mis-ancorado escapa, e a telemetria não distingue "nada elegível" de "gatilho inalcançável" | qualidade-llm | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | prompt-engineer · predicado por conteúdo/tema, não por âncora (cuidado: over-fire medido) |
| RV4-39 | Parecer eleva qualificador de denominador a rótulo de métrica e publica alíquota de IRPF como carga consolidada PF+PJ (`parecer_planejador.yaml:319`), embora o numerador não contenha tributo de PJ algum e a cascata esteja em `regime_nao_suportado` — superfície `metricas[]` não coberta pela lista de não-publicação da [[ADR-356]] | qualidade-llm | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | prompt-engineer · **par com RV4-13** |
| RV4-40 | `metricas[].target` do parecer introduz limiar de domínio **sem fonte no repo** (metade dos targets não existe em `scoring.json`, no prompt nem na persona) — regra metodológica nascendo no prompt, fora do controle de config ([[ADR-143]] na prática); o schema não restringe | qualidade-llm | Médio | P2 | M | Baixo | CONFIRMED | procede-aberto | prompt-engineer · **relacionado a RV2-01** · catálogo de limiares no exec context |
| RV4-41 | Âncora fora do conceito da frase é contada como `verified` e vira chip de evidência na UI: `_check_anchor` (`parecer_evidencia.py:211-221`) valida só que o path resolve e que o rótulo casa a raiz — nunca conceito↔frase | qualidade-llm | Médio | P2 | M | Baixo | CONFIRMED | procede-aberto | prompt-engineer · fix barato = renomear o outcome (`path_resolves`) + restringir o chip, não construir comparador |
| RV4-42 | Reask do Instructor (`max_retries=2`, `litellm_client.py:307`) é cobrado pelo provider e invisível: `usage` vem só da última resposta, o ramo `except` não registra nada e `llm_call_log` não tem coluna de tentativa — o budget da [[ADR-173]] opera sobre piso, não sobre gasto | saúde-execução | Médio | P2 | M | Médio | CONFIRMED | procede-aberto | prompt-engineer · instrumentar por tentativa no choke-point · [[A42.l7]] |
| RV4-43 | `tool_iterations`/`tool_trace` nomeiam uso de tool que o modelo não tem (`LLMService.call` não monta `tools=`; o afordance de drill-down não tem call-site de produção) — as entries são o stamping pós-LLM de âncoras, e o cap `max_tool_iterations` é um teto sobre nada | saúde-execução | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | prompt-engineer · ADR `Decidido` cujo mecanismo central não foi entregue e cuja emenda nunca foi escrita |
| RV4-44 | Cap dominante do catálogo de citação é `max_entries` (aplicado em `parecer_citation_catalog.py:210`, **antes** de `max_bytes`), entregando ~1/9 das folhas citáveis e 3 de 13 seções; e uma segunda classe de folha é inelegível por heurística de **nome**, independente de budget | qualidade-llm | Médio | P2 | M | Médio | PARTIAL | procede-aberto | prompt-engineer · **causa-raiz nova de RV2-10** · subir só `max_bytes` não atinge o critério (medido) |
| RV4-45 | Auditoria de paridade FinOps é fail-open sem a env var (SQLite cria arquivo vazio → "tabela ausente" → exit 0) e compara dois sinks alimentados pelo **mesmo** hook — "não consegui medir" é indistinguível de "medi e passou" | saúde-execução | Baixo | P3 | S | Baixo | PARTIAL | procede-aberto | senior-cto · condição é declarada no docstring · exit code próprio p/ INDETERMINADO · [[A42.l3]] |
| RV4-46 | `meses_ordenados` elide mês sem nenhuma transação mas mantém mês com transação só de receita — duas semânticas de lacuna no mesmo divisor de média mensal (`cash_flow_builder.py:376` vs `:412-415`) | consistência | Baixo | P3 | S | Médio | PARTIAL | procede-aberto | data-engineer · sem direção otimista (medido: fica entre as duas políticas consistentes) · **par com RV4-04/05** · [[A42.l8]] |
| RV4-47 | `CascataInput.das_pago_mensal`/`iss_pago_mensal` são derivados do E4 e **não têm leitor** — [[ADR-236]] §D2 os declara inputs mas §D3 calcula os tributos federais sem consultá-los, logo o tributo medido nunca reconcilia com o estimado | completude | Baixo | P3 | M | Médio | PARTIAL | procede-aberto | data-engineer · dead-input de contrato (o card faz early-return no estado pendente) |
| RV4-48 | `E1.5a` é gravado literalmente em `pipeline_artifacts.stage` mas não é key de `STAGE_RENAME_MAP` — escapa do gate anti-legado (`test_no_legacy_stage_names.py:35` deriva as keys do map) sem estar em `ALLOWED_PREFIXES`: ponto cego, não isenção declarada | consistência | Baixo | P3 | M | Médio | PARTIAL | procede-aberto | data-engineer · [[ADR-093]] · [[A42.l6]] |
| RV4-49 | `_SECTION_KEYS` do orquestrador de section summaries não passa o payload da própria seção (`section_summary_orchestrator.py:275-287`): a seção de riscos não recebe `protecao_patrimonial` e a tributária não recebe `tributario`, contradizendo o próprio fallback genérico | completude | Baixo | P3 | S | Baixo | PARTIAL | procede-aberto | data-engineer |
| RV4-50 | Eixo member-level do lineage está 0% funcional: o único agregado transaction-fed sai com `member_hashes: []` por cobertura parcial de `natural_key` no E4 (degradê intencional e correto, mas nenhum dos 7 campos emite atribuição) | completude | Baixo | P3 | M | Médio | PARTIAL | procede-aberto | data-engineer · relacionado ao débito de `natural_key` no E3 |
| RV4-51 | `protecao_patrimonial.pct_renda_anual` é fração 0..1 num payload onde todo outro campo com sufixo `_pct` é ponto percentual — convenção de unidade quebrada no contrato | consistência | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | data-engineer |
| RV4-52 | `llm_call_log.stage` carrega o filename canônico do documento (código da instituição incluído) numa tabela classificada pelo export LGPD como sem dado pessoal | consistência | Baixo | P3 | S | Baixo | PARTIAL | procede-aberto | data-engineer · **mesmo fix de RV4-03** (stage descritivo puro) · [[A42.l7]] |
| RV4-53 | Guia tributária de PJ é exposta como linha de despesa doméstica sem disclosure PJ/PF, enquanto a seção tributária declara o perfil PJ desconhecido | clareza-ux | Baixo | P3 | M | Médio | PARTIAL | procede-aberto | financial-planner · **consequência do fix #1133**, não regressão dele |
| RV4-54 | Componente de score de endividamento declara unidade de comprometimento de renda mas recebe alavancagem patrimonial | solidez-financeira | Baixo | P3 | M | Médio | PARTIAL | procede-aberto | financial-planner |
| RV4-55 | Dois números diferentes com o mesmo rótulo "cobertura de despesas em meses" no mesmo payload, com fator ~2× entre eles | consistência | Baixo | P3 | S | Baixo | PARTIAL | procede-aberto | financial-planner · **par com RV4-04** (bases distintas) · [[A42.l8]] |
| RV4-56 | Falha de rede silenciosa no contador de documentos pendentes vira selo verde afirmativo de "sem pendências" | clareza-ux | Baixo | P3 | S | Baixo | PARTIAL | procede-aberto | product-designer · distinguir "não sei" de "está zerado" |
| RV4-57 | `tarefas`/`tarefas_status` não têm consumidor e o único leitor de `changelog` casa por um namespace de id que nunca coincide | completude | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | product-designer · **sharpening de RV2-12** |
| RV4-58 | Tabela de receitas por fonte não tem humanização de fallback — categoria fora do mapa local renderiza a chave crua | clareza-ux | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | product-designer · **par com RV4-32** |
| RV4-59 | CTA do empty state de riscos nomeia um destino que não existe no produto do cliente | clareza-ux | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | product-designer |
| RV4-60 | `evidencia_summary` e `red_lines_summary` são computados e descartados — drift entre prompt-versions não é reconstruível do que fica armazenado | saúde-execução | Baixo | P3 | S | Baixo | PARTIAL | procede-aberto | prompt-engineer |
| RV4-61 | Duas datas de independência financeira no mesmo relatório sem disclosure — a regra de persona que manda reconciliar contradição interna não foi honrada e o contexto tinha as duas | qualidade-llm | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | prompt-engineer · **par com RV4-06** |
| RV4-62 | Filtro 3-vias de `campos_faltantes` trataria container semanticamente vazio como dado presente, silenciando pedido legítimo | qualidade-llm | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | prompt-engineer · **sharpening de RV2-25** (null-semantics) |
| RV4-63 | Fragmento de identificador fiscal mascarado egressa ao provider no exec context, duplicado em dois campos | qualidade-llm | Baixo | P3 | S | Baixo | CONFIRMED | procede-aberto | prompt-engineer · relacionado ao débito de PII no prompt do parecer |
| RV4-64 | Conclusão determinística do gráfico de despesas hardcoda 4 categorias e afirma um ranking que não computa (`charts_narrator.py:200-204`) — o método vizinho do mesmo arquivo já usa ranking dinâmico | qualidade-llm | Médio | P2 | S | Baixo | CONFIRMED (latente) | procede-aberto | prompt-engineer · **rebaixado pelo loop:** essa prosa **não é renderizada** (S2 usa `deriveChartConclusion` em TS; leitura de `narrativas` é ramo morto declarado, [[ADR-356]]) e o parecer exclui narrativas do E5 por decisão (`parecer_planejador.yaml:104`). **Acorda quando a migração deferida da ADR-356 aterrissar** |
| RV4-65 | REFUTADO — drop do E2-LLM no guard de texto/imagem vazia não é causa-raiz nova nem regressão: o registro de r2 já cita as mesmas linhas e o mesmo ramo, e o `output_summary` é **byte-idêntico** em 3 runs | correção | — | — | — | — | REFUTED | refutado | 2 lentes chegaram nele; ambas caíram · **RV2-02 permanece aberto, inalterado** |
| RV4-66 | REFUTADO — sumário determinístico da seção de riscos não chega ao leitor: o ramo é emitido exatamente quando o render site é desligado, e a supressão é declarada (`report_layout.yaml:481` + [[ADR-356]] §D7) | qualidade-llm | — | — | — | — | REFUTED | refutado | verify adversarial |
| RV4-67 | REFUTADO — conclusão renderizada do gráfico de despesas **ordena** por valor: a frase hardcoded não é a que a UI usa (ver RV4-64) | clareza-ux | — | — | — | — | REFUTED | refutado | verify adversarial · **este veredito é o que rebaixou RV4-64** |
| RV4-68 | REFUTADO — base full do orçamento prospectivo é o que [[ADR-306]] D1 permite (rotulado `full`), e a obrigação de rótulo impresso está cumprida nos dois ramos do card | solidez-financeira | — | — | — | — | REFUTED | refutado | verify adversarial · migração p/ 12m é follow-up documentado |
| RV4-69 | REFUTADO — placeholder de `pontos_milhas` no contrato E4 é débito **conhecido e owner-gated** (A37.l15, [[ADR-147]]), com as mesmas 3 evidências e critério de aceite já definidos | completude | — | — | — | — | REFUTED | refutado | não duplicar lane |
| RV4-70 | REFUTADO — prefixos de percentil apontando caudas opostas no mesmo dict é **deferimento datado com dono** escrito na [[ADR-361]] §Deferimento item 2, um dia antes do run | solidez-financeira | — | — | — | — | REFUTED | refutado | observação factualmente correta, mas já roteada |
| RV4-71 | POSITIVO — reclassificação de guia tributária de PJ (`das_simples` ↔ `impostos`) é o **fix #1133 aterrissando**, tributariamente correta: o predicado antigo casava preposição e perdia a guia real; `transaction_classifier_pj.py:22-29` agora exige sinal unívoco | correção | — | — | — | — | positivo | procede-fechado | #1133 · verificado independentemente pelo loop **e** por 2 lentes |
| RV4-72 | POSITIVO — cascata tributária acende só o sinal de detecção e mantém `regime_nao_suportado` com camadas em zero em vez de fabricar alíquota; `previdencia_pgbl` (ex-RV2-03) está correto e não prescreve produto | solidez-financeira | — | — | — | — | positivo | procede-fechado | #1096 · #1092 |
| RV4-73 | POSITIVO — `if_monte_carlo` cumpre [[ADR-360]]/[[ADR-361]] com proveniência completa (`mc_version`, `seed_usado`, `n_simulacoes_usado`) e censura declarada por percentil; narrativas são determinísticas por design (0 call LLM) e recomputadas a cada run; `review_snapshot.json` é PII-clean (verificado); lineage reverso materializa e a retenção N=1 funciona | saúde-execução | — | — | — | — | positivo | procede-fechado | #1162 · #1156 · [[ADR-343]] |

**Re-triagem da r2** (run `9d47574c`) — disposição de todo `procede-aberto` anterior:
**Fechados desde r2:** RV2-03 (#1092), RV2-08 (#1094), RV2-18 (#1096), RV2-26 (#1097), RV2-21 (#1098) → confirmados no output deste run (ver RV4-72).
**Permanecem abertos, com evidência nova deste run:** RV2-02 → **RV4-65** (refutado como "novo", mas o defeito é byte-idêntico em 3 runs; segue P1); RV2-05 → medido inalterado (`_CONSERVATION_CHECKS = {CV1,CV2,CV3,CV6}` em `validate_cross.py:605`, CV16/CV17 fora do gate de pausa) e **agravado por RV4-20** (check que não avalia evapora); RV2-10 → **RV4-44** (causa-raiz nova: o cap dominante é `max_entries`); RV2-12 → **RV4-57**; RV2-13 → **RV4-10** (escalado de `consistência` p/ `correção`); RV2-14 → **RV4-21**; RV2-16 → **RV4-18** (o drift é persistido mas cego: `extra` descartado); RV2-17 → **RV4-20**; RV2-20 → **RV4-29**; RV2-22 → re-medido (0 rows contra 6 no `llm_call_log`) e **agravado por RV4-45** (a auditoria de paridade é fail-open); RV2-24 → **RV4-35** (escalado: as duas afirmações agora são do E5 e as duas estão na tela); RV2-25 → **RV4-62**; RV2-01 → adjacente a **RV4-36/RV4-40** (limiar sem fonte no repo) — segue bloqueado pela dependência do catálogo KPI.
**Permanecem abertos, sem re-teste neste run** (mantidos na prioridade da r2): RV2-04, RV2-06, RV2-07, RV2-09, RV2-11, RV2-15, RV2-19, RV2-23.
**Sem zumbi:** nenhum item da r2 ficou sem disposição.
