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

## Namespace de código

Códigos `RV*` anteriores à rodada unificada `U1` são **ambíguos** entre este
registro e {vizinho}: `RV4-08` nomeia defeitos distintos nos dois, e o §r4 do
[[REPORT-REVIEWS-active]] já cita um `RV5-02` que mora no vizinho. Cite sempre
**qualificado** — `RV4-08 (PIPELINE §r4)` — porque o par `(registro, rodada)`
desambigua.

A ambiguidade é inofensiva e **não se conserta renomeando**: o dedup deste registro
é `(dimensão, evidência-âncora, regra)` e nunca dependeu do código, e os códigos são
identificadores duráveis já citados em commit e trilha de owner.

A partir de `U1` o prefixo é o do **registro de destino** — `LC*` razão · `PV*`
execução · `RR*` produto ([[ADR-416]] D3), com o procedimento em
[runbook-unified-certify-review](../reference/runbooks/unified_certify_review.md).

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

**`remediado — fecha por medição no rN+1`** (declarado 2026-08-21). Achado cujo
remédio **está em `main`** mas cuja prova de fecho é o **corpus do próximo run**,
não um gate. Existe porque `procede-aberto` e `fechado` estavam ambos errados
para essa classe: `aberto` convida a re-trabalhar código já mergeado, e `fechado`
afirma um desfecho que ninguém mediu. Exige as duas coisas: **SHA do remédio** e
**o predicado que o r(N+1) vai medir**. Se o run seguinte não mover o predicado,
o item volta a `procede-aberto` com a medição anexada — nunca decai em silêncio.

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
| RV03 — `schema_validation_drift` em massa no stage `extract_statements` (log_tail WARNING) | correção | Médio | P1 | procede | procede-aberto | owner: data-engineer · inventário drift E2 schema · **inventário FEITO 2026-08-24** ([[A40.l58]] §Ataque A2): 54 artefatos em 6/6 runs da janela, sempre `required $.banco`/`$.moeda`; a causa **não é vocabulário** — é o stub de `generate_llm_fallback` persistido sob o stage dos parsers, 3ª instância da classe [[ADR-407]]. O corpus 22/22 não o alcança (rejeita o shape por asserção) |
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
| RV2-08 — `exposicao_cambial` conta só caixa ME, omite bucket Internacional da carteira (divergência de classificação; `asset_classifier` sem keyword) | solidez-financeira | Médio | P2 | procede | procede-aberto | owner: financial-planner/data-engineer · ADR-193 · **re-triagem pedida 2026-08-24** (closeout [[A40.l63]]): a premissa mudou com a [[ADR-403]] — o bucket **é** medido e publicado como componente próprio (`carteira_lastro_estrangeiro`, via `_sum_ativos_internacionais`), mas fica **fora de `total_brl`** por D1 (observacional em v1). "Omite" é falso quanto à medida e verdadeiro quanto ao total; qual dos dois o achado cobrava é decisão do dono, não minha |
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
| RV4-02 | `_narrate_top5_decisoes` descarta `decisoes[0]`: `_fmt_aporte_head` ocupa "Prioridade 1" incondicionalmente e a fila é enumerada de `[1:5]` — decisão registrada pelo dono não chega à única seção que responde "o que fazer", e duplica quando outra decisão da fila é de aporte (`charts_narrator.py:417-433`) | clareza-ux | Alto | **P0** | M | Médio | CONFIRMED | **procede-fechado** (2026-08-05, [[A40.l10]] PR1) | product-designer + financial-planner (2 lentes, mesma causa) · render confirmado em `S10SinteseSection.tsx:16-17` · [[A40.l10]] (admitido como item P0, 2026-08-04). **Alcance maior que o registrado:** o descarte era **duplo** — `summaries.s10` enumerava `decisoes[1:4]`, derrubando também a cauda a partir da 5ª e, com ≤3 decisões, não listando **nenhuma**. A duplicação de aporte deixa de ser possível por construção: a meta sai da numeração e vira enquadramento. Prova de mutação em 3 rodadas; fixture de regressão abre com decisão que não é de aporte (todas as do repo punham aporte em `[0]`, o que tornava o descarte invisível) |
| RV4-03 | `llm_call_log.stage` é `String(64)` e 2 writers interpolam filename — chave estoura a coluna, Postgres levanta `StringDataRightTruncation`, a exceção é engolida em WARNING (`litellm_client.py:342-350`) e a row de custo desaparece; derrota o hard-stop da [[ADR-173]], cuja SSOT é essa tabela | correção | Alto | P1 | S | Baixo | PARTIAL | procede-aberto | data-engineer · **provado em Postgres real** · impacto se realiza no cutover, não hoje · precedente de fix em `comprovantes_bens_llm.py:54-63` · [[A42.l7]] |
| RV4-04 | Janela canônica 12m não tem teto na data de análise: `_compute_janela_12m` fatia `meses[-12:]` e divide por `len` sobre série sem teto (`fluxo_caixa_enricher.py:424-427` + `cash_flow_builder.py:378`) — slots de meses não decorridos entram no divisor e diluem toda base mensalizada; dispara alarme falso de vacância (`generate_narratives.py:249-261`) | correção | Alto | P1 | M | Alto | PARTIAL | procede-parcial-fechado (2026-08-14) | financial-planner · **absorvido** pela [[A40.l44]] PR1 + [[ADR-306]] §Emenda 2026-08-11: a série passa por `split_provisionado(data_corte)` antes de `_compute_janela_12m` (agora `:497`). Residual (zero por falha de extração, união das pernas) fica na [[A42.l8]] |
| RV4-05 | Universo de meses do fluxo é a união das pernas receita+despesa com zero-fill, então mês documentado só em receita entra no denominador da despesa como zero — segunda causa, independente do teto de data (`fluxo_caixa_enricher.py:426-437`) | correção | Médio | P1 | M | Alto | PARTIAL | procede-aberto | data-engineer · **par com RV4-04** (mesmo fix) · [[A42.l8]] |
| RV4-06 | Adapter publica a meta de IF pelo múltiplo do yield-alvo e **descarta** a meta conservadora já derivada e persistida no agregado (`pipeline_adapter.py:204` ignora `derived.if_meta_conservadora_brl`; `goal_service.py:126` calcula as duas) — prontidão de IF superestimada em termos relativos e componente de score de peso 2,0 inflado | solidez-financeira | Alto | P1 | M | Alto | PARTIAL | procede-aberto | financial-planner · **atenção:** rotular a meta pelo yield é decisão declarada em [[ADR-191]] §Aceite — o defeito é a escolha do adapter, não o rótulo |
| RV4-07 | E2 descarta o token de tipo do lançamento que a fonte fornece (`c6bank.py:373` reconhece, `:489` joga fora), sobrando só o favorecido — evento patrimonial (quitação de dívida a instituição credora declarada) cai em `nao_identificado` e entra 100% no numerador de consumo; sem guard de dominância de transação única em balde | correção | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner · causa-raiz achada pelo verificador no PDF de origem + ausência de contrapartida em 106 grupos E3 · [[A42.l2]] |
| RV4-08 | Perna de cascade de IPTU/condomínio/taxa de administração não é plumbada: campos que o extrator de informe produz (`informe_aluguel.py:79-95`) são descartados em `real_estate_e5_integration.py:250-258` e nunca setados em `real_estate_adapter.py:188-197`; `CascadeSources` não tem perna de despesa — o cap rate "líquido" publica esses custos como zero, contra [[ADR-216]] D6, que os declara **observados** | solidez-financeira | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner · provado por execução · viola ADR `Decidido` |
| RV4-09 | Bloco `scalar` denso do manifest do parecer sofre corte silencioso de 300 chars (`parecer_planejador.yaml:499` + `parecer_distiller.py:107,131`) sem marcador: 7 blocos truncam, o pior perdendo ~90% — o parecer raciocina sobre uma fração do payload de Monte Carlo enquanto emite risco de IF ancorado nele, **com folga de budget não usada** | qualidade-llm | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner (reenquadrado pelo verificador) · resíduo da migração scalar→key_value de [[ADR-341]] D3 |
| RV4-10 | `_dedup_excluded_projection` é inerte por construção: `_identity_key` chaveia por `property_id` — o exato campo cuja fragmentação deveria colapsar — e nenhum dos 2 passes de remap resgata; invariante [[ADR-334]] D3 (`imoveis ∩ excluded == ∅`) não aplicado e override manual do dono fica sem efeito monetário | consistência | Alto | P1 | M | Médio | PARTIAL | procede-aberto | financial-planner · **escalação de RV2-13** (de `consistência` p/ `correção`) · [[PLAN-pipeline-review-r2]] Onda D · [[TRACK-property-identity-cross-era]] (a fragmentação de identidade fecha em [[ADR-385]]/[[ADR-386]]; o invariante D3 segue aberto) |
| RV4-11 | YAML de layout deixou de governar o render nos dois sentidos: item `enabled: true` sem componente existente, e `navigation` com link para seção `enabled: false` → âncora morta no TOC (`ReportShell.tsx:90-137,187-207` não filtram por `enabled`; `ReportToc.tsx:115-118` é no-op silencioso). Falha WCAG 2.4.4/2.4.7 + buraco de numeração | clareza-ux | Alto | P1 | M | Baixo | CONFIRMED | procede-aberto | product-designer · **prova de render** (shell real) · agrava: componente da seção existe como dead code órfão e a métrica server-side afirma que renderizou |
| RV4-12 | Termo de marca metodológica proibido (COPY_GUIDELINES §13.1) chega ao TOC web via `title` de seção no YAML de layout; o gate `check_sigilo_terms.py:107-111` não cobre `config/report_layout.yaml` nem `frontend/src/generated/` — rodado contra os dois e contra `--all`: exit 0 | clareza-ux | Alto | P1 | S | Baixo | PARTIAL | procede-aberto | product-designer · PDF **não** afetado (TOC é `no-print`) · existe cópia saneada do título em `S_ProtecaoSection.tsx:20` · [[A40.l7]] (dona do YAML de layout; alcança o usuário hoje) |
| RV4-13 | `_resolve_aliquota_ir` ancora a alíquota efetiva no ano-base de `passive_income`, que pode ser o exercício que o próprio relatório marca `incompleto` (`ratios_calculator.py:334-338`), enquanto o bloco IRPF usa o ano completo — mesma fórmula, anos diferentes, sem disclosure; **inverte veredito** contra o target que o parecer publica | qualidade-llm | Alto | P1 | M | Médio | CONFIRMED | procede-aberto | prompt-engineer · exercício incompleto tem 1 de 2 declarantes (perde no numerador **e** no denominador) |
| RV4-14 | `llm_call_log` perde toda call posterior ao 1º write de artifact do stage sob SQLite — stage multi-documento registra 1 row de N e a verdade in-memory (`LLMRunSummary`) nunca é reconciliada contra o SSOT | saúde-execução | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | senior-cto · causa é contenção SQLite (dev), não recorre em Postgres · **par com RV4-03** · [[A42.l7]] |
| RV4-15 | Predicado de presença de artefato E2 no sync de documentos ignora o payload (`backend/app/services/pipeline/document_pipeline_sync.py`, path conferido 2026-08-14), então stub de escalação satisfaz "extraído" — limpa `needs_review` e liga o badge; os outros 2 consumidores do mesmo fato inspecionam o payload (`extract_with_llm.py:80`, `e3_reconciler_adapter.py:234`) | consistência | Médio | P2 | S | Médio | PARTIAL | procede-aberto | senior-cto · extrair predicado único `is_e2_extracted(payload)` · [[A42.l12]] |
| RV4-16 | Limiar de confiança declarado nos schemas de extração é aplicado em 1 de 3 stages, e nenhum dos 3 emite `validation` no `output_summary` — o canal único de pausa (`pipeline_task.py:1205-1211`) é inalcançável e extração de confiança baixa é consumida a jusante sem rótulo | correção | Médio | P2 | M | Médio | PARTIAL | procede-aberto | senior-cto · vizinho de [[ADR-357]] · acoplar a A40.l21 |
| RV4-17 | Perna de volume do gate anti-regressão é morta: `compare_reviews.py:154` busca folha `transacoes_total` que não existe no view-model E5, `_sum_leaf` devolve `None` e o guard `if b and …` (`:232`) torna o check inalcançável; 3 dos 10 campos de `run_health` do snapshot durável são null | saúde-execução | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | senior-cto · **a perna de drift de valor cobre o caso** (perda de metade das tx → 158 regressões HARD, medido) · [[A42.l3]] |
| RV4-18 | `StageLogTail.emit` descarta todo `extra` do log record (`observability/logger.py:170-177`) e 6 módulos logam fora do namespace capturado — os WARNINGs de drift de schema chegam ao registro durável como eventos idênticos sem `validation_path`/`validator_keyword`/`occurrence_count` | saúde-execução | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | senior-cto · **sharpening de RV2-16** (o drift É persistido, mas cego) · [[ADR-284]] · [[A42.l3]] |
| RV4-19 | `document_pipeline_sync` hardcoda 3 stages E2 e desconhece os stages de extração criados pós-[[ADR-216]]/[[ADR-238]]/[[ADR-239]] — documentos efetivamente extraídos ficam marcados "sem extrato" e `status='processed'` é promovido incondicionalmente | consistência | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | senior-cto · derivar do `STAGE_REGISTRY` + teste de completude que falhe na próxima ADR · [[A42.l12]] |
| RV4-20 | "CV n/n OK" é auto-referente ao E5 (`validate_cross.py:709` lê 1 artefato; nenhum check lê E2/E3/E4) e o denominador é auto-normalizante — check que não consegue avaliar devolve `None` e **evapora** da conta em vez de aparecer como `skipped`; provado por mutação que ausência de input produz falso-verde | correção | Médio | P2 | M | Baixo | CONFIRMED | procede-aberto | senior-cto · **sharpening de RV2-17** · piso de contagem por check-id · [[A42.l4]] |
| RV4-21 | `pipeline_artifacts.document_id` nunca é populado no write-path, então as duas queries reversas de lineage filtram por coluna 100% NULL e devolvem `[]` silencioso (falso-negativo, não erro) — e o teste passa porque a fixture semeia um shape que nenhum produtor emite | completude | Médio | P2 | M | Médio | PARTIAL | procede-aberto | data-engineer · falso-verde de fixture é a parte mais sólida · **sharpening de RV2-14** · [[ADR-278]] · [[A42.l6]] |
| RV4-22 | Skip incremental grava `status='completed'` com `output_summary={"skipped": true}` enquanto skip de LLM grava `status='skipped'` — "n/n stages completed" não é sinal de trabalho feito e o baseline de duração fica inatribuível | saúde-execução | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | data-engineer · propagar o retorno do stage para o enum que os leitores consultam · [[A42.l7]] |
| RV4-23 | Artefato do parecer é persistido sem validação JSON-schema pós-write (`SCHEMA_BY_STAGE` sem entrada para `review_finances_holistic` nem `extract_members`) e com `schema_version` NULL, embora o schema exista e seja exercitado só em teste — e o artefato **deste run viola** o schema (`_meta.tool_iterations` acima do `maximum`) | consistência | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | data-engineer · **ordem obrigatória:** corrigir o schema antes de gatear, senão `strict` derruba o parecer · [[A42.l6]] |
| RV4-24 | Ramo `empty` da S9 é o único alcançável em qualquer workspace porque o aggregate `Risk` tem 0 rows em todos eles (`seed_default_risks` sem call-site de produção; wiring deferido nunca entregou) — a cláusula determinística de gap de proteção existente fica morta | completude | Médio | P2 | S | Baixo | PARTIAL | procede-aberto | financial-planner · o texto **não** chega ao leitor (EmptyState, [[ADR-356]] §D7) — a contradição vive no payload |
| RV4-25 | Componente de proteção declarado em ADR `Decidido` nunca foi implementado no score (composição vive com 5 componentes, `status` hardcoded) e não há penalidade por qualidade de dado — classificação favorável convive com gap de proteção sinalizado em outras superfícies | solidez-financeira | Médio | P2 | M | Alto | PARTIAL | procede-aberto | financial-planner · [[ADR-217]] §D1 · metade já é RV3-13 / A40.l11 — não duplicar |
| RV4-26 | Categoria de aporte é transferência patrimonial em um bloco e gasto discricionário em outro: **4 listas paralelas** de categoria (`fluxo_caixa_enricher.py:74`, `consumo_consciente_calculator.py:58-74`, `report/consumo_pontuais.py:18-21`, +1) divergem, e poupança é contada como consumo pontual | consistência | Médio | P2 | S | Médio | PARTIAL | procede-aberto | financial-planner · [[ADR-333]] · derivar de fonte única (cuidado com erro de 2ª ordem no fix ingênuo) · [[A42.l8]] |
| RV4-27 | Base da TRS é publicada como escalar sem composição, e a maior parte dela é imóvel (parte com classificação pendente) — o parecer rotula o número como carteira financeira contra o guardrail do próprio prompt | solidez-financeira | Médio | P2 | M | Baixo | PARTIAL | procede-aberto | financial-planner · incluir imóvel na base é **decisão declarada** em [[ADR-164]] §1 — o defeito é a ausência de decomposição |
| RV4-28 | Custo essencial lê só `categorias_in` (`fluxo_caixa_enricher.py:117-125`); `categorias_out` e o sub-bloco `impostos.{incluir,excluir}` do `scoring.json` são **config morta sem leitor**, deixando o balde de impostos inteiro fora do essencial contra a regra declarada | solidez-financeira | Médio | P2 | S | Médio | PARTIAL | procede-aberto | financial-planner · pré-requisito do deferimento **segue não cumprido** p/ guias federais sem discriminador PF/PJ · [[A42.l8]] |
| RV4-29 | `premissas_economicas.status` é binário sem estado terminal (`economic_assumptions_snapshot.py:30`, `any(...)`): 1 de N e N de N produzem a mesma string "parcial", e o parecer escreve "ao menos uma premissa" quando nenhuma existe; o cone de probabilidade roda com sigma de constante hardcoded sem proveniência | completude | Médio | P2 | S | Baixo | CONFIRMED | procede-aberto | financial-planner + prompt-engineer (2 lentes) · **sharpening de RV2-20** · ~~`_SIGMA_POR_PERFIL` é dead code~~ **deletado** 2026-08-08 (#1338, [[A40.l25]]), e `sigma_usado` passou a vir com `sigma_procedencia` (`fallback_codigo` hoje) — a metade "sigma sem proveniência" deste achado está **fechada**. Segue aberta a outra metade: `premissas_economicas.status` binário sem estado terminal |
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

---

## r5 — ws-1b9f2cf5-2026-08-16

> Skill pipeline-review ([[ADR-343]]) · run `0a040a22` · tier premium · executor `7dbbe389` (stream-assemble, PR #1482 aberto).
> Execução: **completed**, 18/18, 171 docs, 27,9 min, CV **16/16**. Julgamento: 5 especialistas
> em paralelo + verificação adversarial (PE-01 dependentes e S9/`missing_data` confirmados no payload).
> Cru + baseline: `storage/1b9f2cf5-…/reviews/20260816-0315-0a040a22/` (off-git).
> Working: `_scratch/pipeline-review-5at5-2026-08-16.md`.
> Compare vs r4: exit 1, 4 FAIL HARD de balde cônjuge → 0; NOTE `corpus_grew`. Três runs do mesmo dia
> tinham morrido em `extract_baseline` (EOF TTFB ~120s); este passou com `stream=assemble`.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV5-01 — `patrimonio.investimentos_conjuge` (e fatias irmãs) zera com instituições IRPF do papel ainda listadas; CV2 só testa Σ composição == bruto | correção | Alto | P0 | procede | procede-aberto | owner: data-engineer + financial-planner · fallback IRPF + igualdade canônica · check de balde role-keyed |
| RV5-02 — parecer `riscos[0]` Crítica menciona dependente menor com `irpf_kpis.dependentes.count=0` e `economic_dependencies=[]` | qualidade-llm | Crítico | P0 | procede | procede-aberto | owner: prompt-engineer · guardrail determinístico (lemma dependente/menor) |
| RV5-03 — S9 EmptyState (“cadastre riscos”) com `protection_bundle.calculation_status.*.status=missing_data` e `protecao_patrimonial.apolices_vigentes` populado | clareza-ux | Alto | P1 | procede | procede-aberto | owner: product-designer · EmptyState missing_data · residual l35/RV4-24/RV4-31 |
| RV5-04 — `llm_call_log` 1 row vs `files_processed=10` em `extract_baseline`; `stage` interpola filename (slen 94/68 > VARCHAR(64)) | saúde-execução | Alto | P1 | procede | procede-aberto | owner: data-engineer · [[A42.l7]] (RV4-14 agravado + RV4-03) |
| RV5-05 — `cenarios_conjuge.premissas.salario_conjuge_clt_brl` zero com CLT do papel em `fluxo_caixa.por_fonte_detalhado` | solidez-financeira | Alto | P1 | procede | procede-aberto | owner: financial-planner · resolver por papel, não substring |
| RV5-06 — `extract_with_llm` `success=true` com `queued > processed` e `errors=[]` | correção | Alto | P2 | procede | procede-aberto | owner: data-engineer · re-teste RV2-02 |
| RV5-07 — stream-assemble não prova a classe TTFB>120s (n=1 na banda histórica 72–81s) | saúde-execução | Médio | P2 | procede | procede-aberto | owner: senior-cto · #1482 = adapter, não “EOF resolvido” · [[ADR-270]] calibração |
| RV5-08 — PII como chave em `fluxo_caixa.por_fonte_detalhado` (keys com espaço) | consistência | Médio | P2 | procede | procede-aberto | owner: data-engineer · re-teste RV2-07 |
| RV5-09 — `metricas[]` sem âncora; `target` órfão (comparador de retorno / limiar sem fonte em `scoring.json`) | qualidade-llm | Alto | P2 | procede | procede-aberto | owner: prompt-engineer · RV2-01 + RV4-40 |
| RV5-10 — `compare_reviews` HARD em folha → 0 sem cruzar conservação irmã (CV2 passou) | saúde-execução | Médio | P2 | procede | procede-aberto | owner: senior-cto · [[A42.l3]] |
| RV5-11 — POSITIVO — `extract_baseline` completed com `stream=assemble` após 3 EOFs no mesmo dia | saúde-execução | — | — | positivo | procede-fechado | #1482 (local) · residual em RV5-07 |

**Re-triagem da r4** — nenhum `procede-aberto` da r4 fecha neste run. Agravados com evidência nova: RV4-14 → P1 (RV5-04); RV4-20 (CV2 tautológico no caso real); RV4-24/31 (S9 ainda vazia, RV5-03); RV4-03 (slen>64 medido). RV4-12 fechado na r4 pelo PD (título saneado). Demais r4 mantidos.

**Sem zumbi:** todo achado sistêmico desta r5 tem disposição.

---

## r6 — ws-1b9f2cf5-2026-08-16

> Skill pipeline-review ([[ADR-343]]) · run `7b64b6c7` · tier premium · executor `7dbbe389`
> (= `origin/main` f724438f + PR #1482 stream-assemble, ainda OPEN — **mesmo executor do r5**;
> worker bootado do checkout na branch do PR, declarado). Execução: **completed**, 18/18,
> 171 docs, 24,8 min, CV **16/16**. Julgamento: 5 especialistas em paralelo + verificação
> adversarial do loop em 2 rodadas empíricas (código + DB + worker log + ADRs citadas):
> 0 refutados, 1 re-rotulado (RV5-02), 1 com versão forte refutada pelo próprio run (RV5-07).
> **Compare vs r5 (corpus idêntico, ~17h): 21 FAIL HARD de drift** — mesma família, mesmo
> código, patrimônio/dívidas/score divergindo; CV verde nos DOIS runs. Compare vs r4:
> os 4 FAIL do balde cônjuge persistem. Cru + baseline:
> `storage/1b9f2cf5-…/reviews/20260816-1947-7b64b6c7/` (off-git).
> Working: `_scratch/pipeline-review-5at5-2026-08-16-r6.md`.
> Cadeia-manchete (artefato-a-artefato): re-extração LLM da mesma declaração flipou 1
> `categoria` → consolidador roteou dívida como imóvel de valor **negativo** → E5 publicou
> balde de ativo negativo, dívidas −89% run-a-run, score **subiu** — e parecer promoveu o
> artefato a "ponto forte".

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV6-01 — roteamento ativo/passivo por rótulo do LLM: `scripts/consolidate_baseline.py:501` conjunciona `categoria` (string livre — `e15_baseline_extract.schema.json:27` sem enum; taxonomia do prompt sem membro de passivo; a SEÇÃO do IRPF, único fato determinístico, não é extraída; `GRUPO_MAP` morto no caminho `itens[]`) quando o sinal do valor decide sozinho | correção | Crítico | P0 | procede | procede-aberto | owner: senior-cto+data-engineer+prompt-engineer · sinal é autoridade (valor<0 ⇒ passivo) + campo `secao` enum + enum de categoria · ADR a abrir · plano: [[PLAN-deterministic-authority]] |
| RV6-02 — conservação intra-artefato descartada por design: `consolidate_baseline.py:546-559` adota o total do `resumo` do LLM e apaga o resíduo detalhe↔agregado que denunciava o flip ao centavo; identidade `Σ detalhe ≡ total` (year-scoped) nunca escrita | consistência | Crítico | P0 | procede | procede-aberto | owner: senior-cto+data-engineer · determinístico ganha; falha alto ([[ADR-359]]) · re-escopo de RV5-10 · plano: [[PLAN-deterministic-authority]] |
| RV6-03 — E5 publica balde de ativo negativo sem guarda de sinal (`patrimonio_calculator.py:179` sem clamp; `:194` clampa o vizinho) — viola [[ADR-227]] §D3 e executa a Alternativa (E) que ela descartou por escrito | solidez-financeira | Crítico | P0 | procede | procede-aberto | owner: financial-planner · guarda: nenhum dos 7 baldes [[ADR-145]] < 0 → warning tipado + needs_review · plano: [[PLAN-deterministic-authority]] |
| RV6-04 — eleição de `fonte_investimentos` é global sem predicado de cobertura POR MEMBRO: balde do cônjuge publica zero com posições presentes no artefato imediatamente a montante e `pl_ressalva=false`; `next_aporte_classe` prescreve sobre carteira truncada; co-fator: `membro` é slug do LLM (6 slugs p/ 3 pessoas) | completude | Alto | P0 | procede | procede-aberto | owner: data-engineer+financial-planner · re-teste RV5-01 (3º run, mecanismo cravado — pronto p/ lane) · medir membro×CPF ([[ADR-267]]) · plano: [[PLAN-deterministic-authority]] |
| RV6-05 — RV5-02 re-rotulado: parecer cita FIELMENTE `protecao_patrimonial.gap_qualitativo[0].rationale` (byte-idêntico em 2 runs) que contradiz `irpf_kpis.dependentes.count=0` — a raiz é o produtor determinístico, não alucinação; punir o parecer treinaria o comportamento errado | consistência | Crítico | P0 | procede (re-rotulado) | procede-aberto | owner: data-engineer+financial-planner (era prompt-engineer) · residual PE: regra de precedência entre fontes no prompt · plano: [[PLAN-deterministic-authority]] |
| RV6-06 — contrato assimétrico + enforcement desligado: `baseline_patrimonial.schema.json` tem `minimum:0` só em `dividas[].saldo_31_12` (baldes de ativo livres) e `pipeline.json → mode_overrides={}` — [[ADR-284]] entregue com strict em 0 stages; drift WARNING engolido com success:true | consistência | Alto | P1 | procede | procede-aberto | owner: data-engineer+senior-cto · simetrizar minimum:0 + strict per-schema pós-janela warn · [[A42.l6]] (RV4-23 mesmo guarda-chuva, PR separado) · plano: [[PLAN-deterministic-authority]] · **medido 2026-08-24** ([[A40.l58]] §Ataque A1): a perna "strict per-schema pós-janela warn" está **bloqueada** para `baseline_patrimonial` — 100% de drift em 91/91 por `required: [pipeline_stage, data_processamento]`, que writer nenhum estampa (o normalizador roda na LEITURA, no E4); `e15_baseline_extract` mede 0/66 e é elegível. A perna `minimum:0` shipou na [[A40.l67]] 1e |
| RV6-07 — agregados irmãos declaram o mesmo conceito e divergem no mesmo payload (`patrimonio.imoveis_investimento` ≠ `goals.alocacao_alvo.derived.imoveis_fisicos_brl`, Δ exato do item flipado); score-manchete SOBE por corrupção — a dimensão que a CV residual-por-construção não cobre | consistência | Alto | P1 | procede | procede-aberto | owner: financial-planner+senior-cto · invariante entre-agregados (cents, tolerância zero) · RV4-20 CONFIRMADO de novo → P1 · plano: [[PLAN-deterministic-authority]] |
| RV6-08 — `metricas[]` do parecer sem slot de âncora no schema (0/10 nos 2 runs) e `target` gerado pelo LLM MIGRA com o dado observado (limiar de endividamento e de concentração afrouxam/apertam seguindo o valor; churn do conjunto entre runs) | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: prompt-engineer+financial-planner · re-teste RV5-09 ESCALADO (ganha dimensão de solidez) · targets de catálogo server-side + `ancoras[]` no schema + gate pré-LLM de sanidade do view-model · plano: [[PLAN-deterministic-authority]] |
| RV6-09 — cobertura de citação do parecer caiu à metade e é a causa do barateamento (verified 86%→43%; riscos ancorados 4/12→2/12; `$.path` dentro de texto livre com `ancoras:[]` escapa do verificador); guardrails: 0 disparos num run com balde negativo | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: prompt-engineer · verified_ratio vira gate (≥70% em itens com número → senão needs_review); `$.` em prosa com ancoras vazio = reask · plano: [[PLAN-deterministic-authority]] |
| RV6-10 — `extract_with_llm` não fecha o próprio balanço: success=true com queued>processed e skip DETERMINÍSTICO (`extract_with_llm.py:231-233` — mesmo `.xls` pulado por "texto vazio" nos 2 runs; documento financeiro permanentemente perdido); fila 3→1 com corpus idêntico | correção | Alto | P1 | procede | procede-aberto | owner: senior-cto+data-engineer · re-teste RV5-06/RV2-02 CONFIRMED n=3, ELEVADO · invariante `queued ≡ processed+errors+skipped(motivo)` · absorver em [[A42.l4]] AMPLIADA (contrato de fan-out de stage) · plano: [[PLAN-deterministic-authority]] |
| RV6-11 — telemetria LLM grava 1 row por stage: ~4× em calls e ~2,6× em custo sub-reportados neste run; tentativa que timeouta é COBRADA e invisível; latência do parecer com 2 fontes divergindo 3,7× (`_meta` vs `llm_call_log`); `stage` interpola filename (94>64 chars — quebra em Postgres) | saúde-execução | Alto | P1 | procede | procede-aberto | owner: data-engineer+prompt-engineer · re-teste RV5-04 AGRAVADO ([[A42.l7]] + RV4-03/RV4-14) · 1 row POR TENTATIVA + stage curto/stage_ref + migration · [[ADR-173]] opera sobre piso · plano: [[PLAN-deterministic-authority]] |
| RV6-12 — `confidence` agregada do E1.5 (min de N chamadas, `extract_baseline.py:161`) é emitida e não tem NENHUM consumidor — ladder [[ADR-081]] nunca cabeado na extração patrimonial; baseline com confiança 4,7× abaixo do limiar de review consolidou e publicou | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: senior-cto · conf<0,7 → review_reason + stage degraded ([[ADR-357]]) · plano: [[PLAN-deterministic-authority]] |
| RV6-13 — `property_identity` minta UUID novo quando `endereco_canonical=None` (`property_identity_enricher.py:44-49` + `endereco_canonicalizer.py:182-192`): 19 rows p/ ~meia dúzia de imóveis, 6 órfãs low_confidence, 2 criadas NESTE run (uma é a própria dívida) — dano durável que rollback de artefato não desfaz | consistência | Alto | P1 | procede | procede-aberto | owner: data-engineer · canonical=None não cria (match por (titular,codigo_rfb,ano) → senão needs_review) + reconciliar órfãs · escala RV4-10/RV2-13 ([[ADR-246]]) · plano: [[PLAN-deterministic-authority]] |
| RV6-14 — cenário do cônjuge é contrafactual E inelegível: participação de renda ~2% < limiar de 15% da [[ADR-167]] (bloco deveria ser OMITIDO); matching por SUBSTRING de nome (`cenarios_conjuge_analyzer.py:211`, contra o comentário role-keyed [[ADR-338]] do próprio arquivo); haircut de aporte constante ~16× a renda simulada — prazo de IF desliza anos indevidos | solidez-financeira | Alto | P1 | procede | procede-aberto | owner: financial-planner · re-teste RV5-05 ESCALADO Médio→Alto · gate e extrator na MESMA fonte por papel; fator derivado; inelegível → omitir · plano: [[PLAN-deterministic-authority]] |
| RV6-15 — inexiste tripwire fluxo×estoque: amortização anual publicada é ~2× o saldo devedor total do mesmo payload (a checagem mais barata da classe inteira de erro de baseline); custo essencial da reserva inclui a prestação da dívida "quase quitada" | correção | Alto | P1 | procede | procede-aberto | owner: financial-planner · cross-check `financiamentos×12 > total_dividas` → warning tipado; queda >50% do saldo run-a-run sem quitação no fluxo → needs_review · plano: [[PLAN-deterministic-authority]] |
| RV6-16 — render absorve o defeito e fecha 100%: `patrimonio.imoveis_nao_geradores` não tem superfície (único hit no frontend é a declaração de tipo `report-analysis.ts:47`); DQ banner cego a violação de contrato; card VERDE de pontos fortes celebra o endividamento colapsado ao lado da descrição de alienação fiduciária a valor cheio; prosa do E5 com decimal en-US renderizada crua | clareza-ux | Crítico | P1 | procede | procede-aberto | owner: product-designer · guard de contrato no frontend (ativo<0 → linha no `ReportDataQualityBanner` + suprime CleanBar) + cross-check imóvel financiado × dívida antes de emitir ponto forte · plano: [[PLAN-deterministic-authority]] |
| RV6-17 — PII composta em chave e rótulo renderizado: `fluxo_caixa.por_fonte_detalhado` com 8/12 chaves embutindo empresa+prenome+regime (identificador instável + vaza em ValidationError); prenome em `patrimonio.composicao[].categoria` e `endividamento.dividas[].descricao` chega ao PDF exportado e a baselines visuais | consistência | Alto | P1 | procede | procede-aberto | owner: data-engineer+product-designer · re-teste RV5-08 ELEVADO (reclassificado p/ contrato de dados) · chave semântica PII-free + rótulo por papel + array tipado · plano: [[PLAN-deterministic-authority]] |
| RV6-18 — RV5-07 versão forte REFUTADA pelo próprio run: o parecer estourou timeout com `stream=assemble` ativo (retry salvou; stage consumiu ~1/3 do run); a classe TTFB é INVERIFICÁVEL sem telemetria por tentativa — o instrumento que a mediria é o mesmo que sub-reporta (RV6-11) | saúde-execução | Médio | P2 | procede (re-escopado) | procede-aberto | owner: senior-cto · mergear #1482 com claim corrigido ("reduz p50; não elimina timeout") · bloqueado por RV6-11 · plano: [[PLAN-deterministic-authority]] |
| RV6-19 — `temperature` global de geração herdada pela EXTRAÇÃO + trava [[ADR-307]] (`litellm_client.py:189-191`: use_cache exige temp 0) tornam o cache estruturalmente inalcançável para todas as calls do run — re-extração integral paga a cada run | qualidade-llm | Médio | P2 | procede | procede-aberto | owner: prompt-engineer · temp por stage (extract_* → 0.0; parecer mantém 0,1 declarado) · plano: [[PLAN-deterministic-authority]] |
| RV6-20 — S9 EmptyState segue mentindo o motivo, agora com contradição INTRA-documento: "cadastre riscos" enquanto `pontos_urgentes[0]` cita as apólices vigentes; `missing_inputs` nomeiam campos PRESENTES no payload; CTA aponta destino que não resolve | clareza-ux | Alto | P1 | procede | procede-aberto | owner: product-designer · re-teste RV5-03 (mantido, com prova de contradição visível) · `hasRealProtectionInputs` considera apólices>0 (degrade parcial) + EmptyState com reasons reais · plano: [[PLAN-deterministic-authority]] |
| RV6-21 — alvo da reserva é função-degrau sobre proxy ruidoso: share PJ cruzou o limiar `_PJ_DOMINANTE_MIN_PCT=60` e o alvo saltou +50% (12→18 meses, janela r4→r5) com custo essencial CAINDO — mudança muda, sem histerese nem changelog (anti-padrão [[ADR-223]]); o suppressor `corpus_grew` do compare mascarou o degrau | solidez-financeira | Médio | P2 | procede | procede-aberto | owner: financial-planner · histerese (2 ciclos) + entrada em `changelog[]` nomeando a causa + ressalva do share não-identificado no denominador · plano: [[PLAN-deterministic-authority]] |
| RV6-22 — contagem de `needs_review` do relatório é client-side com catch→0 (`useNeedsReviewCount.ts:30`): no export estático (ADR-124) efeitos não rodam e o `CleanBar` pode afirmar "sem pendências" no artefato que o cliente arquiva, com docs pendentes no workspace | completude | Médio | P2 | procede | procede-aberto | owner: product-designer · re-teste RV2-23: fecha p/ app vivo (superfície existe desde A28.l9), abre o resíduo do export · contagem server-side + tri-state · plano: [[PLAN-deterministic-authority]] |
| RV6-23 — donut e tabela da mesma composição patrimonial com predicados de filtro duplicados e divergentes (fatia zero some no gráfico; tabela imprime zero-confirmado para o balde suspeito de RV6-04) | consistência | Médio | P3 | procede | procede-aberto | owner: product-designer · funde PD-03/04 da síntese r5 · `visibleCompositionRows()` único; "—" + nota enquanto RV6-04 aberto · plano: [[PLAN-deterministic-authority]] |
| RV6-24 — POSITIVO: run completed n=2 consecutivo com stream-assemble (retry absorveu o timeout); o compare de 3 pernas da [[ADR-343]] pegou a instabilidade run-a-run que os 16 CVs não veem — a skill funcionando como desenhada | saúde-execução | — | — | positivo | procede-fechado | **não congelar r6 como baseline** do compare até RV6-01..03 mergeados (senão o estado corrompido vira o "normal" — r5 já avisava o mesmo do balde cônjuge) |

**Re-triagem da r5** (run `0a040a22`) — disposição de todo `procede-aberto`:
RV5-01 → **RV6-04** (mantido P0, mecanismo cravado: fonte global sem cobertura por membro; dado presente a montante; pl_ressalva inerte). RV5-02 → **RV6-05** (**re-rotulado** — não é alucinação; produtor determinístico; dono PE→DE/FP; piorou 3→6 menções). RV5-03 → **RV6-20** (mantido, evidência nova de contradição intra-doc). RV5-04 → **RV6-11** (mantido AGRAVADO: ~4× calls e ~2,6× custo sub-reportados; tentativa cobrada invisível; 94>64 chars). RV5-05 → **RV6-14** (ESCALADO Médio→Alto: inelegível por ADR-167 + substring + fator ~16×). RV5-06 → **RV6-10** (CONFIRMED n=3, ELEVADO P1; skip determinístico com perda permanente de documento). RV5-07 → **RV6-18** (**versão forte REFUTADA** pelo próprio run — timeout ocorreu com stream-assemble; re-escopado p/ telemetria por tentativa). RV5-08 → **RV6-17** (ELEVADO; chave composta; reclassificado p/ contrato de dados). RV5-09 → **RV6-08** (ESCALADO; targets móveis perseguem o valor; ganha dimensão de solidez). RV5-10 → **RV6-02** (**re-escopado**: o item real é a conservação irmã intra-artefato nunca escrita; compare-como-gate é subordinado — "estabilizar antes de gatear"; [[A42.l3]] não é sobre isso e [[A42.l4]] exclui cross-stage).
**r4 re-tocados neste run:** RV4-20 (confirmado de novo → P1, via RV6-07); RV4-23 (split de PR, via RV6-06); RV4-03/RV4-14 (via RV6-11); RV4-10 (via RV6-13). Demais r4 mantidos na prioridade registrada.

**Sem zumbi:** todo achado sistêmico desta r6 tem disposição.

## r7 — ws-1b9f2cf5-2026-08-18

Run `33514dc4` **completed 18/18** (25,2 min, 171 docs), executor de stage
`ac847372d221`. **Ciclo em 2 tempos:** o run 1 (`140ac8d7`) morreu em 12/18; o
defeito foi corrigido e mergeado (#1535) antes de re-disparar. O run pausou 1× em
`extract_with_llm` e foi retomado por `resume_pipeline_run` (retoma do stage
seguinte). Baseline de compare = **r5**, não r6 — o estado corrompido do r6 viraria
o "normal" do gate. Cru + PII off-git em
`storage/1b9f2cf5-…/reviews/20260818-2122-33514dc4/`.

**Manchete: a remediação do r6 fechou.** `endividamento.total_dividas` volta ao
valor do r5 com resíduo **0,0000%** e **nenhum** dos 7 baldes de patrimônio é
negativo — RV6-01/02/03 fecham **por medição**. Corolário do gate: os 14 FAIL do
compare vs r6 são a correção sendo lida como regressão; congelar r6 teria feito o
gate aprovar a corrupção.

**Fecho parcial datado 2026-08-21.** RV6-04 e RV7-04 fecham; CTO-6 e CTO-3 fecham por
gate/teste; DE-1 e DE-2 entram em `remediado — fecha por medição no r8` (vocabulário
declarado no §Convenção). A triagem do RV6-04 rendeu **4 achados novos** — DE-7 (61% da
soma sem linha de cobertura), DE-8, DE-9 e CTO-7 —, dos quais o **DE-7 é o de maior
magnitude aberto no eixo membro** e não tem instrumento nenhum.

**Adendo 2026-08-24 (posterior à triagem).** Duas coisas medidas depois de fechar a
tabela. (a) O **RV7-05** foi **re-ancorado** na [[A40.l6]] — ver a célula; a instância
nomeada foi fechada pelo #1569 no mesmo dia. (b) Os **6 achados novos** desta onda
(DE-7, DE-8, DE-9, DE-10, CTO-7, CTO-8) **não tinham arquivo de lane** — `grep` pelos
ids sobre os 75 arquivos de `docs/sprint/A40/lanes/` devolvia zero. Achado sem lane é
invisível ao `lane_pickup` e ao `SPRINT_CURRENT`, que derivam de frontmatter. O
roteamento está em [[MOC-sprint-a40]] §Inventário dos achados do r7 sem hospedeiro, e o
**DE-10** — único P0 sem destino nenhum — ganhou a [[A40.l77]].

| Achado | Dimensão | Sev. | Prio | Veredito | Disposição | Gatilho |
|---|---|---|---|---|---|---|
| RV7-05 — campo de descrição de imóvel é a discriminação crua do documento fiscal e é renderizado como rótulo (`RealEstateYieldCard.tsx:200`,`:310`,`:380` via `S4RealEstateSection.tsx:26`); por [[ADR-129]] a rota React é a fonte do PDF, então documento de terceiro sai no artefato exportado; baseline visual usa fixture sintética e não alcança | clareza-ux | Crítico | P0 | procede | **fechado** | **Correção 2026-08-24:** a instância nomeada não existe mais — o #1569 (`dfd561b9`) tocou exatamente este arquivo e `RealEstateYieldCard.tsx:205` renderiza `imovelDisplayLabel(im)`, não `descricao` crua; `redact_cartorial` wired em `real_estate_metrics_payload.py` e `endividamento_analyzer.py`. **Sobra o que esta própria célula nomeava** — *gate sobre payload real*, *baseline visual usa fixture sintética e não alcança* — e ele coincide termo a termo com os 2 critérios abertos da [[A40.l6]]: `scan_view_model_pii` **sem chamador** (zero ocorrências em `.github/`, `.pre-commit-config.yaml`, `dev/` ou stage) e **sem spec renderizada** assertando ausência em `body.innerText()` **e** no PDF. Não vira lane nova — residual com dono na l6 · **FECHADO 2026-08-24** (#1673, [[A40.l6]] §Fecho): os dois termos que esta célula nomeava foram entregues — o gate ganhou 3 chamadores (payload produzido, lint público com 2 waivers queimados, spec renderizada) e a spec assere ausência em `body.innerText()` **e** na camada de texto do PDF, com prova por mutação nas duas superfícies. A medição mudou o remédio: o defeito não era "gate sem chamador", era **gate varrendo o nome do campo** — `endereco_canonical` (= `canonicalize(descricao)`, cascata que devolve `mat:`/`iptu:`) era o que o card renderizava. O gate passa a chavear no VALOR, e a redação também roda na LEITURA para alcançar artefato já gravado · owner: product-designer+data-engineer |
| RV7-01 — caminho de REPORTE aborta a execução que documenta: produtor projetava filename em `review_reasons.document_id` (FK, [[ADR-371]]) → `IntegrityError` → run morto; teste afirmava o filename como esperado e não persistia em DB | correção | Crítico | P0 | procede | **fechado** | #1535 (`ac847372`): produtor manda None + boundary degrada id não-resolvível; regressão DB-backed verificada por mutação |
| RV7-02 — pin de key Fernet em teste cobria a fonte de **menor** precedência (`FERNET_KEY`), inerte sob o `FERNET_KEYS` da [[ADR-171]]: 2 testes de crypto passavam a ser decididos pelo ambiente (verdes no CI, vermelhos em máquina com rotação no `.env`) e o pin do próprio `backend/tests/conftest.py` era inerte pelo mesmo motivo — a suíte inteira cifrava com a key real da máquina, não com a canônica | consistência | Médio | P2 | procede | **fechado** | #1539 (`ab91f7ec`, backend) + #1547 (`37c754cb`, pipeline): pin cobre a chave autoritativa e deixa decoy na deprecada, então a preferência volta a ser gateada. Cegueira medida por mutação — invertida a precedência em `resolve_fernet_keys`, a versão antiga seguia **11/11 verde** |
| DE-1 — `classify_asset` decide classe por texto livre que inclui o rótulo de instituição; **qualquer re-extração** do E1.5a (retry, doc reprocessado, troca de model, `reextract_stale_e2_llm.py`, bump de `PROMPT_VERSION`) reemite instituições em forma canônica e reclassifica posição para a catch-all **sem diff no classificador** — o #1521 foi *um* gatilho, não a causa: `git log -L '/Instituição financeira/,+1'` devolve **um só** commit (`6219acd5`, 2026-04-14), e o #1521 (`3a7aca05`) tocou o arquivo sem tocar a linha; migração atravessa p/ `goals.alocacao_alvo.derived.comparaveis[].desvio_pp`, que é prescritivo | correção | Crítico | P0 | procede | **remediado — fecha por medição no r8** | #1571 (`5f73b116`, [[ADR-400]]): **`tipo` decide em duas camadas** (`conclusivo`/`presuntivo`), keyword/ticker viram degrau 2, ausências são declaradas (`sem_match`/`sem_haystack`/`sem_mapa`) e instituição sai da entrada. **Correção 2026-08-21:** esta célula prescrevia "`secao`+`codigo` RFB decidem" — exatamente o que a [[ADR-400]] §Alternativa considerada e recusada **rejeita por medição** (`codigo` semanticamente puro em só 48,2% de 6.780 itens; `secao` presente em 2,57%). **Predicado do r8:** nenhuma posição migra de classe sob `PROMPT_VERSION` novo sem diff no classificador, e `classe_autoridade` cobre 100% dos itens |
| RV7-04 — reclassificação entre baldes preserva Σ **por construção**, logo os 16 CV são cegos por design: `classify_asset` devolve a mesma catch-all para haystack vazio e para haystack sem keyword (indistinguíveis) | correção | Crítico | P0 | procede | **fechado** | dobrado na [[ADR-406]] (D1/D3): autoridade tipada torna `sem_haystack` ≠ `sem_match`, e `sem_haystack` vira razão **sempre** — o par indistinguível que cegava os 16 CV deixa de existir · #1593 (`d69d3177`) |
| DE-2 — único sensor da catch-all é de **nível** (limiar 5%) e nunca vira `review_reason`; participação observada ~6× abaixo do limiar deixa crescimento de duas ordens passar em silêncio | correção | Crítico | P1 | procede | **remediado — fecha por medição no r8** | #1593 (`d69d3177`, [[ADR-406]]): gate por **item** com piso de 0,5%/item + `sem_haystack` sempre-razão + `n_posicoes` como denominador de identidade. **Predicado do r8:** item da catch-all acima do piso vira `review_reason`, e `sem_haystack` segue em 0 |
| CTO-6 — superfície de diagnóstico compartilha transação e domínio de falha com a transição de estado do run (uma sessão cobre status + `StageReview` + `review_reasons`, sem try/except, enquanto o commit de artefato acima é protegido) | saúde-execução | Crítico | P0 | procede | **fechado** | #1565 (`a8d57ee1`, [[ADR-404]]): sessão separada + try/except no diagnóstico; a **classe** fecha, não só a instância do #1535. **Ressalva de leitura:** o título do commit em `main` cita `ADR-399` — o ID foi tomado por outra lane na mesma janela e a nota shipou como `ADR-404`. Dano permanente da colisão; o commit **não** é corrigido (já mergeado), fica registrado aqui para quem seguir o SHA |
| RV7-03 / DE-3 — contrato warn-first de [[ADR-393]] D4 é decorativo: `validation.valid` é escrito por 6 produtores com 4 políticas divergentes e `BLOCKING_CODES` é honrado por 1; quem retém o run é `pipeline_task.py:1489` lendo `validation.valid`, e `BLOCKING_CODES` só escolhe rótulo de severidade em `:1155` | consistência | Alto | P1 | procede | procede-aberto | owner: senior-cto+data-engineer · **REFUTADO 2026-08-21** → ~~predicado de pausa passa a ser `any(code ∈ BLOCKING_CODES)`~~ — ver §Refutação R2; o primeiro entregável passa a ser **cobertura de emissão por produtor** · produtor emite fato, orquestrador deriva retenção; tabela de política **total** + gate p/ membro novo do enum |
| CTO-2 — a própria [[ADR-393]] declara D4 entregue e promete kill-switch que não existe no código; o §Estado afirma cobertura que a medição refuta | consistência | Alto | P1 | procede | **fechado** | remédio já mergeado: [[ADR-393]] §Emenda 2026-08-19 (`amended_at`) corrige o §Estado e declara o kill-switch inexistente, D4 parcial, D3/D5 não entregues. Reconciliado no closeout da [[A40.l68]] (2026-08-24) — a linha seguia `procede-aberto` sobre trabalho feito. A tabela de política **total** de `validation.valid` permanece viva em **RV7-03 / DE-3** |
| CTO-3 — teste afirma **pertinência em conjunto** e nunca exercita o comportamento (`test_fan_out_balance.py:114-116` afirma "não retém o run" 15 linhas depois de afirmar `valid is False`); o único produtor com teste comportamental é o único que honra `BLOCKING_CODES` | consistência | Alto | P1 | procede | **fechado** | #1581 (`b0f64d8e`): 1 teste comportamental por produtor de `validation.valid` + 1 teste de loop provando que reason advisory não pausa. Fecha por **gate/teste**, não por corpus — independe do r8 |
| DE-5 — invariante de passivo do E1.5 contradiz o prompt shipado no **mesmo PR**: computa Σ dos negativos enquanto o prompt manda transcrever saldo devedor positivo ⇒ predicado vira "declarado ≠ 0" e dispara 100%; rebaixado a `warning`, não vira `review_reason`, não move `valid` | consistência | Crítico | P1 | procede | procede-aberto | owner: data-engineer · referente vira `Σ secao=='dividas_onus'` com fallback datado; rotear `review_reasons` do consolidador ao `detail` do stage (senão [[ADR-394]] D3 fica inerte) |
| DE-6 — item da ficha de dívidas recebe `property_id` mintado e é apresentado como imóvel pendente de rótulo; rotular converte passivo em ativo do patrimônio bruto — a autoridade de `secao` da [[ADR-394]] não foi propagada ao mint de identidade | correção | Alto | P0 | procede | **fechado com ressalva** | #1556 (`26264d6f`, [[ADR-398]]): mint exige eixo atestado por fato; projeção exige que baseline ou dono reivindiquem a identidade. Ver §Nota datada 2026-08-19 |
| DE-4 — balanço de fan-out fecha sobre denominador **pós-filtro** (`queued` conta depois do "já processado", e o lookup é workspace-scoped, não run-scoped): run reportou balanço fechado tendo gravado zero artefatos do stage; consequência — `review_snapshot.provenance` declara `execucao_mista: false` num run que consome artefato de outro executor | saúde-execução | Alto | P1 | procede | procede-aberto | owner: data-engineer+senior-cto · denominador = corpus elegível; `list_keys` run-scoped; proveniência deriva dos artefatos **consumidos**, não dos stage logs · **parcialmente entregue 2026-08-24** ([[ADR-393]] §D5, #1663): formato sem leitor passa a ser recusado no E0 e não entra em `data/` para sumir depois — segue aberto o `list_keys` run-scoped e a proveniência |
| PE-2 — `target` de métrica do parecer é gerado pelo LLM e **migra sobre dado byte-idêntico**, atravessando o valor observado (violação vira conformidade sem nada mudar); orquestrador roda com `temperature` sem `seed`, enquanto os stages de extração já têm gate exigindo ambos | qualidade-llm | Crítico | P1 | procede (RV6-08 agravado) | **parcial** | #1555 (`9d95134c`, [[ADR-396]]) fecha o braço de **amostragem**: o gate passou a casar por **assinatura** (`system_prompt`+`output_schema`) em vez de path+receptor e achou **5 call-sites sem amostragem declarada, não 1** — 2 eram extração fora do glob `extract_*.py` e 1 era o harness de eval de drift medindo a 0.1 um prompt que produção roda a 0.0; `temperature` do parecer 0.1→0.0. **O `seed` NÃO estabiliza o `target`** — é descartado por `litellm.drop_params` em `anthropic/*`, o gate fecha sintaxe. Braço do **`target`**: catálogo determinístico mergeado (#1557, `13deaa8f`, [[ADR-399]]) mas **não-wired** — produção segue publicando alvo do LLM · §Deferimento D3 (2026-08-21) · **WIRED em 2026-08-27** pela [[A40.l89]] (#1770 → #1772 → #1779): o `kpi_target_catalog` é leitor único do alvo publicado e `_render_target` só renderiza com procedência+limiar+operador — a frase *"produção segue publicando alvo do LLM"* ficou falsa e este registro não acompanhou. **Completado em 2026-08-28** pela [[A40.l93]] (#1796): as 2 chaves cujo `observado_path` o resolver de produção NUNCA conseguia ler passaram a resolver, e o alvo de alocação — que publicava `operador="<="`, doutrinariamente falso — virou órfão por decisão de domínio ([[ADR-399]] §Emenda 2026-08-28). **O braço do `target` do PARECER está fechado**; o do **plano de ação** foi fechado em **2026-08-29** pela [[A40.l90]] (#1815): `trs_target_pct` e `rule_trs_desalinhada` saíram **juntos** — `rg` devolve zero —, sob emenda datada da [[ADR-191]] §D6, cujo Aceite contava "dois consumidores" e eram **três**. **RR5-02 fechada pelas duas metades** |
| PE-1 — âncora de citação só existe onde houve round-trip de tool: o conjunto ancorado é idêntico ao buscado, **zero** âncoras vêm do catálogo renderizado; com metade das iterações duplicadas o teto estrutural de cobertura é ~8,6%; `strict` é inerte porque `missing_path` está fora das camadas hard | qualidade-llm | Crítico | P1 | procede (RV6-09 agravado) | procede-aberto | owner: prompt-engineer · rota de âncora p/ percentual; persistir `evidencia_summary`; `missing_path` vira gate soft com piso · emenda [[ADR-296]]/[[ADR-304]] · **DEIXA DE SER BLOQUEADO** (medido 2026-08-21, Onda C): `metricas[]` não tem campo de âncora — nem `evidencia_path` nem `ancoras[]` — e o catálogo de citação é *input-side* (só renderiza markdown p/ dentro do prompt; o verificador de saída não o importa). Dos paths candidatos a fonte de `target`, **9/10 resolvem em `get_e5_jsonpath` e 0/10 estão no catálogo**. O eixo `target` sai do escopo do PE-1 (fechado por [[ADR-399]]); sobra **ancorabilidade de percentual**, sem dependência de curar limiar normativo — some a parte que exigia `financial-planner` |
| PE-3 — RV6-05 **re-diagnosticado**: o produtor não se contradiz (registro familiar ≠ dependente fiscal; ambos verdadeiros); o defeito é o manifest não projetar o campo reconciliador, e os 2 disparos de guardrail do run foram contraproducentes (rebaixou o item correto; marcou spurious um pedido de campo que existe e está vazio) | qualidade-llm | Alto | P1 | procede (re-rotulado) | **fechado** | #1562 (`d1a4276b`, [[ADR-397]]) · owner: prompt-engineer · projetar composição familiar por papel + faixa etária (nunca data crua); coleção vazia deixa de contar como "resolveu" |
| PE-6 — tier invertido (modelo caro em 5/6 chamadas, todas de extração com schema+fallback; síntese aberta no barato); custo do parecer e cobertura de citação caem juntos sem alarme | saúde-execução | Alto | P1 | procede | procede-aberto | owner: data-engineer+prompt-engineer · fechar escrita da tabela; publicar custo × cobertura no mesmo painel; eval antes de mexer em tier |
| RV6-11 — `llm_call_log.stage` interpola filename e excede a largura declarada da coluna (94 em `VARCHAR(64)`); SQLite tolera, Postgres levanta truncation — **mesma classe** do RV7-01 | consistência | Alto | P1 | procede (persiste) | procede-aberto | owner: data-engineer · `stage` curto + `stage_ref`; 1 row por **tentativa** |
| PE-5 — superfícies do mesmo run publicam números conflitantes para o mesmo conceito com janelas distintas e rótulo idêntico; conceito de horizonte aparece em 3 valores em 3 superfícies; veredito de diversificação contradiz veredito de concentração com confiança alta | consistência | Alto | P1 | procede | procede-aberto | owner: prompt-engineer+data-engineer · rótulo de janela obrigatório no manifest; conceito canônico único; CV cruzando parecer × narrativas |
| FP-2 — parecer descreve trajetória em aceleração enquanto o changelog do mesmo payload declara queda, com `comparison_base_changed` verdadeiro; a métrica que ancora o ponto forte nº 1 salta por mudança de base, não por comportamento | solidez-financeira | Crítico | P1 | procede (re-diagnosticado) | **parcial** | #1574 (`0e4d10fa`, mergeado) · o parecer NÃO vê o changelog (zero ocorrência de comparison/delta no manifest, distiller e prompt) — eram 2 defeitos: produtor afirmando direção sob base alterada + trajetória derivada de nível. Braço de concentração **deferido** (ver §Deferimento D2, 2026-08-19) |
| FP-6 — parecer publica `target` **fabricado e mais frouxo** que o alvo declarado em `goals.alocacao_alvo.derived`, subestimando o desvio; e emite duas sugestões P1 que se cancelam por recaírem na mesma comparável com sinais opostos | solidez-financeira | Alto | P1 | procede | **parcial** | #1558 (`b4263e7b`) fecha o braço de **antagonismo**: P1 que aumenta a classe que outra P1 manda reduzir, **sem condição de reconciliação declarada**, cai p/ P2 + `confianca=media` (rebaixa, nunca bloqueia — [[ADR-294]]); a direção vem do **verbo mais próximo**, não da presença — a sugestão medida tem "reduzir" e "ampliar" na mesma frase com 4 classes, e um matcher por presença nunca dispararia. Braço do **`target`**: **fechado em 2026-08-27/28** — a [[A40.l89]] wirou o catálogo e a [[A40.l93]] fez o observado resolver. Especificamente para o FP-6: o par observado↔alvo da renda fixa saía de bases diferentes, e agora **não há mais par** — o alvo de alocação virou órfão, porque desvio é bidirecional e soma zero entre classes, e nenhum operador escalar o exprime ([[ADR-399]] §Emenda 2026-08-28, co-design `financial-planner`). O alvo declarado pela família continua publicado no card S3, com direção e desvio assinado |
| FP-4 — prescreve realocar excedente de reserva para risco sem conhecer a taxa da dívida (`endividamento.dividas[].taxa_juros` nulo e ausente dos campos que pediria), violando a única convergência sem exceção das três metodologias; e trata a mesma reserva como ponto forte **e** risco | solidez-financeira | Alto | P1 | procede | **parcial** | #1575 (`a1fa798a`, mergeado) · piso proíbe as DUAS direções sob taxa nula + injeta o pedido da taxa; liquidez excessiva remove o ponto forte de liquidez. Regra por par (seção, tema) **refutada por medição** — ver §Refutação R1. RL2 destravada (parser numérico, v1.5) |
| FP-5 — `previdencia_pgbl.limite_pgbl_anual` publica zero sobre base positiva (defeito de rótulo que [[ADR-375]] §D4 fechou, reintroduzido) e a nota do bloco afirma o oposto do campo; KPI de exposição cambial ignora a classe internacional, tornando o tier artefato de definição | solidez-financeira | Alto | P1 | procede | **fechado** | #1567 (`440d4618`, [[ADR-402]]) + #1568 (`6c546d7b`, [[ADR-403]]) fecham os **dois** braços. PGBL: `limite_pgbl_anual` carregava a *capacidade restante* sob o nome de *teto* — o `0.0` era valor correto sob rótulo errado, não aritmética errada. Grandezas separadas + `motivo_ausencia` por campo com precedência; `aliquota_marginal` vira bicondicional com `economia_ir_anual`. Exposição cambial: o componente de carteira publicava zero silencioso porque lia universo vazio; agora declara `componentes` com `cobertura` própria, e cobertura incompleta suprime o **veredito** sem apagar a **medida** — `pct` inalterado em 6,98%, `tier` amarelo → **indeterminado**. Nada foi somado ao total; mudou o que passou a ser *declarado* · owner: financial-planner |
| FP-3 — dois universos de imóveis no mesmo payload com membros exclusivos de cada lado; o limiar canônico de concentração cai **entre** as duas leituras, os dois alertas ficam mudos e o LLM fabrica um limiar próprio; default de IPTU zerado infla o rendimento líquido na direção que [[ADR-216]] proíbe | solidez-financeira | Alto | P1 | procede | procede-aberto | owner: financial-planner+data-engineer · fonte única de estoque imobiliário; suprimir a razão enquanto divergirem >5%; corrigir default |
| RV6-04 — balde de investimento de um membro publica zero enquanto o artefato a montante lista instituições dele, com a flag de ressalva falsy e `cobertura_completa` verdadeiro; a narrativa **afirma o zero em prosa entregue**, byte-idêntica em 3 runs | completude | Crítico | P0 | procede (3º run) | **fechado com ressalva** | #1578 (`11b90a4e`, [[ADR-394]] §Emenda (c)) fecha o balde. **Mudou de `fechado por medição` em 2026-08-21: o fecho anterior mediu um dos dois resolvers** — `E5MemberResolver` não recebeu o fix e ainda valora o cônjuge a 0,00, ver **DE-10**. A raiz **não** eram os `extras` por papel — medidos **inertes**: 0 mudanças em 90 instâncias-membro, nenhuma das 3 chaves existe em `bens` no caminho de produção. Era `_max_value_year` reduzindo o baseline a **um** ano e propagando-o a todos os membros: **defeito do eixo, não da pessoa**. Ver §Nota datada 2026-08-21 · [[A40.l69]] |
| CTO-8 — dano de colisão de ID desta onda, **medido**: (a) o commit `a8d57ee1` em `main` cita `ADR-399` no título tendo shipado a nota `ADR-404` — imutável, fica registrado; (b) `aliases: "ADR 396"` vivia em **duas** notas que não são a 396 (`398` e `400`), então 3 notas atendiam pelo mesmo nome; (c) o par `status:` × tag `status/<lc>` **desincroniza em 7 de 394** ADRs, sempre na direção `Decidido` no campo × `proposto` na tag | consistência | Médio | P2 | procede (novo, 2026-08-21) | **parcial** | owner: information-architect · (b) e (c) da onda r7 **corrigidos aqui** (`398`,`400`,`404`); os outros **5** desincronizados (`330`,`333`,`360`,`361`,`395`) são de lanes alheias e ficam **registrados, não varridos** — rename global em nota de terceiro é a armadilha conhecida. O CLAUDE.md descreve a tag `status/<lc>` como "automática"; ela é escrita à mão e **não tem gate** — `build_doc_index.py` lê o campo `status:` e nunca confere a tag, então busca por tag no Obsidian devolve 7 falsos-positivos |
| DE-10 — o RV6-04 fechou em **um dos dois resolvers**: `#1578` corrigiu o eixo de ano-base em `resolve_members` (`patrimonio_resolvers.py`, que alimenta o `PatrimonioCalculator`) e **não tocou** `E5MemberResolver` (`e5_member_resolver.py`, que alimenta `InvestimentosClassesAnalyzer` + `TopAtivosAnalyzer` + `InstituicoesPorMembroAnalyzer`). No **mesmo payload**, a mesma pessoa vale `110.130,67` em `patrimonio.investimentos_conjuge` e `0,00` dentro de `total_financeiro`/`tabela_classes`/`top_ativos` | correção | Crítico | P0 | procede (novo, 2026-08-21) | **fechado por medição** | owner: data-engineer · medido em `207fca00` sobre o run `33514dc4`: `E5MemberResolver` → cônjuge `n=9 soma=0.00`; `resolve_members` → cônjuge `n=9 soma=110130.67`; `git show --stat 11b90a4e` não lista `e5_member_resolver.py`. `instituicoes_por_membro` publica **3 instituições dela com `n_posicoes=9` e valor zero** — a assinatura literal do RV6-04 original. **Precede o DE-7**: corrigir o 2º resolver move `total_financeiro`, que é o denominador que a ressalva do DE-7 publica · dois resolvers paralelos sobre o mesmo baseline é decisão arquitetural, exige co-design antes do código · **ataque de 2026-08-24 ([[A40.l77]] §Ataque) estreita a premissa**: os consumidores são **cinco**, não três — reserva de emergência (`e5_analyzer_adapter.py:655`) e endividamento (`:686`, com `ano_ref=members.reference_year` em `:694`) também leem o resolver não-corrigido; e com o **ano forçado idêntico** os dois ainda divergem em `instituicao` / `tipo` / `ano_base` / guarda do top-up, logo **nenhum é superset do outro** e eleger um vencedor perde dado nos dois sentidos | · **FECHADO 2026-08-24** pela [[A40.l77]] em 4 PRs (#1669 → #1676 → #1677 → #1684), sob a [[ADR-410]] (`Decidido`): produtor único, injetado, com os 3 resolvers mortos enterrados e 3 gates no payload. Medido **na fixture sintética de 2 membros**, não em produção — o E5 mais recente do corpus é de 18/08 e a lane mergeou em 24/08, então o efeito real só se mede no r8: `total_financeiro` 900.000 → **1.010.000**, `investimentos_conjuge` 0,0 → **110.000**, `cobertura` ganha a linha do cônjuge com `frescor` 2023 vs 2025 do titular. Nenhum rebaseline de golden ou snapshot — o dogfood é de um membro só, e é por isso que a fixture de dois membros era precondição. **Destrava o DE-7**: o denominador que ele publica acabou de mudar
| DE-7 — `patrimonio.investimentos_nao_atribuidos` = **61,0% da soma dos baldes** e **não tem linha em `cobertura_investimentos`**: `cobertura_de_membros` só constrói `titular`/`conjuge`, e a chave vazia de `total_por_membro` não gera veredito nenhum. O relatório atribui patrimônio a pessoas e deixa a maior fatia sem dono, sem ressalva | completude | Crítico | P0 | procede (novo, 2026-08-21) | procede-aberto | owner: data-engineer · **61× acima** do piso agregado de 1% que a [[ADR-406]] instalou, em eixo que **nenhum** gate alcança. Invariante medido: `Σ(baldes)+nao_atribuido` vs `Σ(total_por_membro)` — **0,00 exato em 25/25** onde `fonte == "posicoes_atuais"`; nos outros 20 o delta é o top-up (DE-8). Sucessor natural da [[A40.l69]] · o próprio #1578 o nomeia no corpo · **re-medição de 2026-08-24 (pós-[[A40.l77]]): o número não tem substrato.** O E5 mais recente do corpus é de 18/08 e o #1550/#1578/l77 mergearam em 19/08 e 24/08 — nenhum artefato foi produzido por código pós-fix. No run `33514dc4` o payload publica `nao_atribuidos: 0,00` e `cobertura_investimentos: []`, porque é anterior ao #1550 e a chave vazia (`total_por_membro` com **68,1%** em `""`) ainda era absorvida pelo titular. **O r8 precede este achado**, não o sucede |
| DE-8 — top-up IRPF entra no balde do membro **sem quantia declarada**: `fonte_investimentos: "posicoes_atuais+irpf"` descreve o **domicílio**, não diz quanto nem de quem, e o valor fica fora de qualquer denominador publicado | completude | Alto | P1 | procede (novo, 2026-08-21) | procede-aberto | owner: data-engineer · é a queixa que criou `cobertura_investimentos` um andar acima, cometida um andar abaixo — mesma família de [[ADR-394]] §Emenda (c). Medido em **20/45 runs**; delta = exatamente o top-up. Remédio: publicar a quantia por membro, e o invariante do DE-7 passa a fechar nos 45 |
| DE-9 — `cobertura_investimentos[].frescor` tem **zero consumidores**: chegou ao schema (`e5_analysis.schema.json:326`) e ao tipo TS (`report-analysis.ts:350`), e não há leitor em `pipeline/domain/services/narrativas/` nem em componente do relatório. A prosa põe o valor de **2023** de um membro ao lado do de **2025** do outro sem qualificar | clareza-ux | Alto | P1 | procede (novo, 2026-08-21) | procede-aberto | owner: data-engineer+product-designer · mesma família do RV6-04 — **afirmar sem qualificar**. `status` diz se mediu, `frescor` diz quando; publicar o segundo e não lê-lo é o campo existir para o gate e não para o leitor |
| CTO-7 — kill-switch de retenção **não deixa rastro**: com `MATHOMS_E5_CLASSIFICACAO_GATE=0` ou `MATHOMS_E5_COBERTURA_ENFORCEMENT=0` o run fica **indistinguível de run limpo** — sem razão, sem pausa, sem campo. A pausa é auditável; o desligamento não. **Correção 2026-08-24 (r8):** a env de cobertura citada nesta célula não existe no código — a real é `MATHOMS_E5_COBERTURA_MEMBRO` (`investimentos_cobertura.py:18`); o nome errado fica registrado porque quem procurou por ele achou zero e concluiu que o kill-switch não existia | saúde-execução | Alto | P1 | procede (novo, 2026-08-21) | procede-aberto | owner: senior-cto · **segunda instância da classe de falso-verde desta onda** (a 1ª foi o gate que media o contêiner, [[ADR-394]] §Emenda (c)). Remédio barato e sem contenda: `validation.gates_desligados: ["classificacao"]` — **não** toca `e5_analysis.schema.json`, `dogfood_view_model.json` nem o codegen, logo não disputa superfície com #1591/#1568/#1573 |
| PD-4 — predicado de vazio da seção de riscos lê só um bundle e ignora a fonte populada, imprimindo "sem riscos cadastrados" enquanto a seção vizinha cita apólices vigentes; copy de vazio **desqualifica** dado que o próprio documento exibe | clareza-ux | Alto | P1 | procede (RV6-20 persiste) | procede-aberto | owner: product-designer · predicado lê as duas fontes; estado **parcial** em vez de vazio; nunca derivar copy de `missing_inputs` |
| RV6-17 — vocabulário composto com identificador de pessoa/empresa chega ao render — **re-ancorado**: o campo registrado no r6 não tem consumidor (só o tipo); a rota viva é o `label` das séries mensais, consumido pela legenda do gráfico | consistência | Alto | P1 | procede (âncora corrigida) | procede-aberto | owner: data-engineer+product-designer · chave semântica PII-free + rótulo por papel; corrigir a âncora registrada no §r6 |
| PD-3 — catch-all de classe sem drill-down nem provenance: linha de participação baixa parece resíduo de arredondamento, sem rota para as posições que caíram nela | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer · provenance + nota condicional + cinza neutro no donut |
| PD-6 — contagem de pendências é client-side com catch→0 e o guard novo só testa desfecho do run, então falha de fetch no render estático ainda permite afirmar "sem pendências" | completude | Médio | P2 | procede (RV6-22 mitigado, não fechado) | **fechado** | owner: product-designer · hook tri-state; `unknown` **cala** em vez de afirmar — entregue em #1551 (`d2527993`), prova por mutação. A premissa "render estático" era falsa: ver nota datada 2026-08-19 |
| PD-5 — prosa do E5 emite decimal em formato en-US e é renderizada crua; banner de qualidade conta duplicata e inclui item que não é imóvel na contagem que pede rótulo ao usuário | clareza-ux | Médio | P2 | procede | procede-aberto | owner: data-engineer+product-designer · formatação é responsabilidade do produtor + gate de formato; deduplicar antes de contar |
| CTO-5 — supressor `corpus_grew` derruba **toda** a perna de valor de HARD para informativo a partir de um único documento novo, desligando a rede justamente quando corpus e código mudaram juntos | saúde-execução | Médio | P2 | procede (latente — não disparou neste run) | procede-aberto | owner: senior-cto · manter HARD para par compensatório e troca de sinal; supressor por-path via lineage |
| RV6-13 — identidades de imóvel sem canonical persistem no DB (dano durável), embora **nenhuma nova** tenha sido criada neste run | consistência | Médio | P2 | procede parcial | **medido — poda é decisão do dono** | 4 vivas sem canonical (6 no total, 2 supersedidas); zero criadas no r7. Inertes: inalcançáveis pelo resolver e invisíveis ao relatório após #1556. Ver §Nota datada 2026-08-19 |
| RV6-15 — tripwire fluxo×estoque proposto no r6 keyaria em campo de parcela/taxa que é **nulo em 3 runs consecutivos** | solidez-financeira | Médio | P2 | procede (re-escopo) | **parcial** | #1573 (`88b9eb8d`, [[ADR-401]]) fecha as etapas 1-2: o item de dívida deixa de ser "um membro que tem dívida" e passa a ser a **dívida** (itemizado de `baseline_patrimonial.dividas[]`, [[ADR-301]]), com `fontes` por chave e `taxa_juros` → `taxa_juros_aa`. O rótulo fabricado ("Financiamento imobiliário (<nome>)") sai: `descricao` vira rótulo derivado + `membro` tipado, com peneira `_CODIGO_CANONICO` fechando PII na origem. **Aberto:** etapas 3-4 — popular do agregado `debts` e o tripwire de fluxo observado · owner: data-engineer |
| RV6-01 / RV6-02 / RV6-03 — roteamento por rótulo do LLM, conservação intra-artefato descartada e balde de ativo negativo sem guarda de sinal | correção | Crítico | — | **fechado por medição** | fechado | dívidas voltam ao baseline pré-corrupção com resíduo 0,0000%; zero baldes negativos (7/7) · A40.l66/l67 (#1520-#1525, #1529) |
| RV6-07 — agregados irmãos declarando o mesmo conceito e divergindo no mesmo payload | consistência | Alto | — | **fechado por medição** | fechado | divergência zero neste run; era efeito do item flipado do r6 |
| RV6-23 — donut e tabela da composição com predicados de filtro divergentes | consistência | Médio | — | **fechado** | fechado | predicado único com estados nomeados + gate próprio (#1511) |
| RV6-10 — fan-out não fechava o próprio balanço, com skip determinístico e perda permanente de documento | correção | Alto | — | **fechado com ressalva** | fechado | #1526 fez o balanço fechar e o skip ser nomeado — mas o remédio gerou RV7-01 (abort) e expôs RV7-03/DE-4 (o balanço fecha sobre denominador pós-filtro). **Ressalva levantada em 2026-08-24:** a perda era permanente porque `_reader_for` mandava `.xls` para openpyxl; roteado para `xlrd` (#1655), o corpus mede **168/168 legíveis** — o documento deixou de estar perdido, não só de estar calado |
| RV6-24 — positivo do r6: o compare de 3 pernas pegou o que os CV não veem | saúde-execução | — | — | positivo (reconfirmado) | fechado | r7 confirma pelo inverso: **não congelar r7 como baseline** enquanto DE-1/RV7-04 e RV6-04 seguirem abertos — congelar faria o gate aprovar ambos |

**Nota datada 2026-08-19 — DE-6 e RV6-13 remediados; o diagnóstico mudou de lugar.**
O #1556 (`26264d6f`, [[ADR-398]]) fechou o DE-6 em duas frentes, e a re-medição contra
`main` corrigiu a âncora do achado. **`secao` cobre 87/87 itens** no run `33514dc4` — as 6
dívidas têm valor positivo e **2 trazem `categoria_hint: "imovel"`**, mas com `secao`
presente o roteamento da [[ADR-394]] já as manda para `dividas`: **nenhuma** dívida foi
mintada neste run. As duas entradas "DIVIDA" que o leitor viu são rows de **2026-08-12 e
2026-08-16**, anteriores à [[ADR-392]]. O que as levou à tela foi a **leitura**, que
projetava toda row viva de `property_identity` sem consultar o baseline do run.

O buraco de **escrita** existe e é alcançável onde `secao` falta (campo opcional; 766
artefatos históricos não o carregam e o modo incremental os reagrega). Reproduzido em
fixture sintética, com um agravante **não previsto no achado**: quando a descrição do
financiamento canonicaliza para o mesmo endereço do imóvel financiado, o passivo não ganha
identidade nova — **casa com a identidade do próprio imóvel** e o dedup da [[ADR-246]] o
absorve, é a classe da §Emenda da ADR-392 por outra porta.

**Blast radius medido** (mesmo harness, com e sem o filtro): `excluded_properties` é o
único campo do payload que muda, **6 → 2**; `imoveis`, `valor_total_imoveis`, `cap_rate`,
`concentracao_pct`, `componentes_calculo`, `spreads` e `alertas` idênticos. As 4 entradas
podadas são todas `desconhecido` — a contagem que o banner de qualidade usa para pedir
rótulo cai de **4 para 0**, o que endereça metade do PD-5 (a outra metade é o formato
en-US da prosa). Duas são as dívidas do DE-6; duas são identidades cujo CTA apontava para
row que run nenhum resolve (RV4-10). **Nenhuma** sai por dedup — o
`_dedup_excluded_projection` segue inerte.

**Ressalva do fechamento:** a precondição de mint é escopada ao que a fonte pode oferecer
([[ADR-398]] D2). Numa declaração inteiramente legada (sem `secao` em item nenhum) o mint
segue autorizado — exigir o fato ali apagaria `property_id` de todo o corpus antigo, medido
em 17 testes de dedup/identidade. Nesse regime quem protege o leitor é o filtro de leitura.

**RV6-13 medido:** **4** identidades vivas sem `endereco_canonical` (6 no total, 2 já
supersedidas), últimas criadas em 12 e 16/08 — **zero no r7**, confirmando o §r7. São
**inalcançáveis** pelo resolver (o match residual da ADR-392 D1 exige row única por
`(titular_key, codigo_rfb)` e há 2 em cada um dos dois pares) e invisíveis ao relatório
após o #1556. A poda **não** foi executada: o backfill aborta grupo sem âncora no baseline
e nenhuma das 4 tem âncora, então o dry-run esperado é 4 grupos abortados / 0 supersessões.
Podá-las exigiria eleger vencedor por outro critério, que é o que a [[ADR-386]] proibiu.
Recomendação registrada em [[TRACK-property-identity-cross-era]]: **não podar** enquanto
inertes.

**Segue aberto:** o invariante `imoveis ∩ excluded == ∅` ([[ADR-334]] §3 / RV4-10) — o
filtro reduz o conjunto excluído, não fecha a interseção. E `redact_pii` na fronteira do
payload de imóveis, citado na disposição original do DE-6, **não** foi tocado: é o RV7-05,
de outra onda, e mascarar CPF/monetário não resolve endereço nem nome de terceiro.

**Nota datada 2026-08-18 — chegou depois da medição.** A [[A40.l69]] mergeou #1541 e
**#1542** (`58ca1c11`, 21:37Z) **após** o fim deste run (21:21Z): balde de membro não apurado
passa a publicar `null` em vez de `0,00`. Isso endereça o braço de **afirmação** do RV6-04
("omitir ≠ afirmar zero") no produtor. **Não** está medido aqui, e dois braços seguem abertos
até prova em contrário: (a) a **cobertura** — por que as instituições conhecidas do membro não
chegam ao balde; (b) a **prosa entregue**, que afirmava o zero e era byte-idêntica em 3 runs.
Re-medir os três no r8 antes de rebaixar a prioridade.

**Nota datada 2026-08-21 — números da [[ADR-406]] re-medidos pós-#1578: inalterados.**
Em `207fca00`, pelo resolver que a produção usa (`E5MemberResolver`), sobre o corpus do r7:
maior item `sem_match` **1,2803%**, Σ `sem_match` **1,2847%**, `nao_classificado_pct`
**1,2800%**, maior sem instituição **2,8104%**, `sem_haystack` **0**, interseção
`sem_match` × sem instituição **ZERO** — idênticos aos declarados na ADR. O gate dispara
(3 razões). **O motivo de não terem mudado é o DE-10:** o defeito que o #1578 corrigiu
nunca chegou à base da ADR-406, porque os dois analisadores leem de um resolver que o
#1578 não tocou. Registrado para não virar folclore — a ADR-406 está correta **e** a
razão disso é um defeito aberto, não robustez.

> Armadilha de harness, registrada porque quase virou achado falso: medir isto com
> `resolve_members` (em vez de `E5MemberResolver`) devolve `maior sem instituição =
> 21,72%` e 7 razões, porque o `bens` daquele resolver não carrega a chave `instituicao`.
> Foi pego pela **magnitude implausível** (2,81% → 21,72% não é drift), não por gate.

**Nota datada 2026-08-21 — RV6-04 fecha por medição, e a raiz não era a que a linha dizia.**
Os três braços que a nota acima mandou re-medir foram medidos contra `main`, e o defeito
**já estava corrigido** por **#1578** (`11b90a4e`, mergeado 2026-08-19), que a triagem não
tinha visto. Saída crua, com procedência no mesmo output — padrão desta lane:

```
git rev  : 4251a538e58ab65f9b8ac10e45e8ef0250cac1f0
git dirty: ''
modulo   : …/pipeline/domain/services/investimentos_cobertura.py
tem_bens_irpf no modulo carregado: False
RUN      : 33514dc4-115b-45fe-8976-03e25ba971c8

investimentos_titular            = 300444.46
investimentos_conjuge            = 110130.67
fonte_investimentos              = 'posicoes_atuais+irpf'
investimentos_nao_atribuidos     = 642744.79
cobertura_investimentos          = [{"membro": "titular", "status": "apurado",
  "fonte": "posicoes_atuais", "frescor": "2025", "motivo": null},
 {"membro": "conjuge", "status": "apurado", "fonte": "irpf", "frescor": "2023",
  "motivo": null}]
```

**A raiz não eram os `extras` por papel.** A hipótese era que `investimentos_from_irpf`
recebia `("saldo_corretora","moeda_estrangeira","outros")` para o titular e só `("outros",)`
para o cônjuge. Medida sobre o corpus, a assimetria é **inerte**: trocar um pelo outro muda
**0 valores em 90 instâncias-membro**, porque **nenhuma** das 3 chaves existe em `bens`
produzido por `build_members_from_consolidated` — o parâmetro é dead code no caminho de
produção. A raiz é `_max_value_year` reduzindo o baseline a **um** ano e propagando-o a todos
os membros: os lançamentos do cônjuge são de 2023, `ano_ref` resolvia 2025, e
`_resolve_item_valor` caía no fallback e devolvia `0,00`. Forçando o ano para 2023, quem zera
é o **titular** — **defeito do eixo, não da pessoa**.

**Braço (b), a prosa, dissolve-se e é substituído.** Com a cobertura correta,
`fmt_currency` recebe valor real e a frase deixa de afirmar zero. Mas a prosa passa a pôr um
número de **2023** ao lado de um de **2025** sem qualificar: `frescor` existe no payload e
**não tem leitor** — é o **DE-9**, aberto acima, da mesma família (afirmar sem qualificar).

**Duas coisas que a medição comprou e a leitura de código não compraria:**

1. **O terceiro ramo morreu; o estado não.** `classificar_cobertura` não tem mais o ramo
   `tem_bens_irpf ⇒ zero_apurado` (media o **contêiner**: `bens` vem sempre com 4 chaves, o
   predicado era constante `True`). Mas `zero_apurado` **continua alcançável** pelo ramo 1,
   com valor lido = 0 — as docstrings do enum seguem vigentes e **não discriminam** entre as
   duas versões. Só o bloco `if obs.tem_bens_irpf:` discrimina, e ele não existe em `main`.
2. **A mutação matou 2 testes, contra a previsão.** Invertido o default de `apurado`
   (`True`→`False`) em `valor_publicavel`: baseline `7063 passed`; mutado `2 failed, 7061
   passed` — `test_solo_identity_no_conjuge_category` e
   `test_adr145_solo_titular_conjuge_bucket_is_zero`. O ramo **é** exercitado, porque #1578
   trocou o fixture que usava o único dos 4 shapes de `resolve_members` que **desvia** de
   `build_members_from_consolidated`, por onde a produção sempre passa.

**Método, para a próxima triagem.** A análise que dava o RV6-04 por aberto foi feita lendo o
arquivo de **outro checkout do mesmo clone**. `git merge-base --is-ancestor` valida a **ref**;
não valida de onde o arquivo foi lido, e num repo com vários worktrees os dois se separam em
silêncio. Quando a afirmação é sobre uma ref, a leitura passa por `git show <ref>:<path>` —
não pelo filesystem.

**Correção datada 2026-08-19 — erro meu no §r7 acima.** O PE-6 foi registrado afirmando que `pipeline_run_costs` vazio implicaria "nenhum cap da [[ADR-173]] enforceável". **É falso.** `backend/app/services/llm_budget_service.py:115,164` lê `LLMCallLog` — a tabela que ESTÁ populada. `pipeline_run_costs` está vazio por ser **dead schema** pós-ADR-173, não por defeito. Verifiquei as contagens e repassei a INFERÊNCIA da lente sem checá-la.
O que **permanece de pé** no PE-6, medido: (a) tier invertido — 5 de 6 chamadas no modelo caro são de extração, superfície que já tem schema + fallback determinístico, ~82% do custo, enquanto a única síntese aberta roda no barato; (b) subcontagem — 1 row por stage, tentativa cobrada e invisível; (c) custo do parecer e cobertura de citação caem juntos sem alarme (mesma variável, via PE-1).
O que **muda de natureza**: a tabela morta não é falha de governança de custo — é **ruído que se faz passar por medição**, porque o `run_meta` a imprime como `(0): []` e um leitor (este) leu "custo zero". O fix é declará-la morta e removê-la do `run_meta`, ou ressuscitá-la — não "consertar o cap".

**Nota datada 2026-08-19 — PD-6 fechado, e uma premissa minha do §r7 corrigida.** Entregue
em #1551 (`d2527993`): os dois contadores client-side do banner (`useNeedsReviewCount` e o irmão
`useParecerRetidoCount`, que repetia a classe) passam a devolver um tipo discriminado
`loading | ok | unknown`; `unknown` **cala** a barra em vez de afirmar "sem pendências". A
distinção mora no **tipo**, não na UI — `computeDataQualitySignals` recebe o tipo e não `number`,
porque enquanto o valor de falha for indistinguível de zero medido o próximo consumidor repete o
bug. Prova por mutação: `catch → measured(0)` (o defeito original) mata dois testes, um sobre HTTP
real (MSW → `apiFetch` → `ApiError`) e um sobre o render do banner; o controle positivo no mesmo
arquivo garante que zero **medido** continua afirmando (senão o remédio trocaria falso-positivo por
falso-negativo e a barra nunca mais apareceria).

**Nota datada 2026-08-19 — PD-5(b) fechado na ORIGEM, e a premissa da duplicata é falsa.**
A metade (a) saiu em #1561 (`4d70ae16`): percentual em prosa passa pelo produtor único
`fmt_percent`, com gate de formato — mutação nos dois produtores dá `7 failed`, com
`AssertionError: decimal en-US: '28.0%'`. O follow-up em `pontos_urgentes_analyzer` foi roteado
para a [[A40.l73]] (dona daquele produtor) e saiu em #1576 (`ff23c03e`).

A metade (b) **não vira PR**, e a razão é medição, não desistência. A contagem que o banner faz
(`dataQualitySignals.ts:127` — `excluded_properties` filtrado por `classification ===
"desconhecido"`) foi corrigida **a montante** pelo DE-6 (#1556, `26264d6f`): as entradas caem de
**4 para 0**. Deduplicar no banner seria **inerte** — repetiria o padrão do #1476, que consertou a
S9 render-side sobre um predicado que não tinha como enxergar a outra fonte.

E a premissa registrada na linha do PD-5 — "**DUAS** são o mesmo imóvel (mesma matrícula/endereço)"
— **está errada**. Medido pelo DE-6 com e sem o filtro, contra o DB real: das 4 entradas que somem,
**2 saem por serem passivo** e **0 por dedup de identidade**. As outras 2 são identidades cujo item
o baseline corrente já carrega com `property_id` nulo ([[ADR-392]]), com CTA apontando para row que
run nenhum resolve — o "override sem efeito monetário" do **RV4-10**, não duplicação. O
`_dedup_excluded_projection` que já existe seguia **inerte**, e nenhuma entrada some por ele.

**Ressalva de precisão (medida em 2026-08-21):** o "4 para 0" vale enquanto o baseline
reivindica ao menos um `property_id`. `_projetaveis`
(`backend/app/services/real_estate_e5_integration.py`) tem `if not reivindicadas: return
identities` — com `imoveis_consolidados` sem nenhum `property_id`, o filtro **falha aberto** e as
4 voltam a projetar. É fail-safe deliberado (baseline ausente não deve esconder tudo), mas torna o
número condicional, e a frase acima o afirmava sem condição. Re-medido: as 4 órfãs seguem vivas no
DB (criadas em 12 e 16/08, **zero novas**) e **nenhuma está em `workspace_property_overrides`**,
então sob baseline não-vazio as quatro são filtradas.

**O que sobra do PD-5(b) não é dedup — é o RV4-10.** O invariante `imoveis ∩ excluded == ∅`
([[ADR-334]] §3) segue vigente e não aplicado: o D3 do DE-6 reduz o conjunto excluído, não fecha a
interseção. Quem retomar o RV4-10 herda o item; o banner não deve maquiar defeito de montante, e
hoje não precisa, porque a montante já não produz o item.

**A frase "falha de fetch no render estático" da linha do PD-6 está errada** e fica registrada como
erro meu, não corrigida em silêncio na tabela. Por [[ADR-129]] o PDF é Playwright sobre a **mesma
rota React**, num Chromium real que espera `networkidle` + `data-report-ready`: o `useEffect`
**roda**. O vetor não é "o efeito nunca roda" — é falha de fetch/auth **dentro do contexto do
renderer**, que produz a mesma afirmação falsa. O alcance é igual ou pior do que o registrado (o
PDF é a superfície que sai do produto e é arquivada por terceiros, e o KR-3 do [[PLAN-report-trust]]
já a declara obrigatória por isso), mas a causa registrada teria mandado o executor procurar no
lugar errado — SSR/hidratação em vez do caminho de rede.

**§Refutação R2 — RV7-03/DE-3: predicado por code desligaria 11 das 14 pausas (datado 2026-08-21).** A linha do RV7-03 prescreve *"predicado de pausa passa a ser
`any(code ∈ BLOCKING_CODES)`"*. Medido no DB de dogfood antes de implementar, e o gate de blast
radius reprovou: `stage_reviews` tem **14 pausas históricas**, das quais **11 (79%) vêm de
`extract_irpf_full`** — produtor cujo bloco `validation` **não tem a chave `review_reasons`**
(idem `extract_members`). Com o predicado novo, `any([])` é `False`: **esses 11 deixam de pausar,
em silêncio**. A remediação prescrita seria um kill-switch de retenção — exatamente a classe que
esta revisão persegue.

A estimativa que autorizou a mudança ("o run inteiro do r7 tem 1 `review_reason`") media a
**tabela**, não a **retenção**: `review_reasons` tem 8 rows (4 blocking, 4 advisory) e não é a
fonte de quem pausa. Medir o proxy errado é o que fazia a mudança parecer barata.

**Reproduza antes de confiar** (a medição acima é de 2026-08-21; `stage_reviews` cresce a
cada run):

```bash
sqlite3 "$MAIN/mathoms.db" "SELECT stage, COUNT(*) FROM stage_reviews GROUP BY 1 ORDER BY 2 DESC;"
```

O denominador que importa é `stage_reviews` (**quem pausou**), não `review_reasons` (**o que foi
registrado**): a tabela tem 8 rows e não governa retenção. Foi medir o proxy errado que fez a
mudança parecer barata.

**Pré-requisito que a especificação não previu:** todo produtor emite `review_reasons` **antes**
de o predicado passar a chavear por code. A ordem inversa desliga a retenção. RV7-03 permanece
`procede-aberto`, **re-escopado**: owner senior-cto + data-engineer, e o primeiro entregável é a
cobertura de emissão por produtor, não o predicado. O CTO-3 correlato foi entregue (#1581,
`b0f64d8e`: 1 teste comportamental por produtor + 1 teste de loop), e é ele que torna a fase
seguinte verificável.

**Nota datada 2026-08-19 — CTO-6 remediado (#1565 `a8d57ee1`, [[ADR-404]]).** Re-medido contra
`origin/main` (`ab91f7ec`) e **confirmado**: a assimetria persistia (o commit de artefato do
ramo `needs_review` tem `try/except`; o `_record_stage_needs_review` logo abaixo, nenhum), e
três payloads de produtor derrubavam o run **no SQLite** — `dict` em coluna `Text` (o driver
recusa o bind), entrada `str` no lugar de objeto (`AttributeError`) e `occurrence_count`
não-numérico (`ValueError`). Nenhum é largura de coluna: o #1535 fechou uma munição de FK e a
classe era de **tipo**. Remediado em três camadas — controle (`stage_log` + `StageReview` +
`run.status`) commita primeiro e sozinho, sem `try/except`; sink de `review_reasons` em
`backend/app/services/diagnostics/` com sessão própria e sem `Session` na API pública; DTO
normaliza tipo e largura (larguras derivadas de `__table__`). `StageReview` fica do lado do
**controle** de propósito: a retomada é recusada com qualquer review sem decisão, e um
`StageReview` fail-open trocaria abort ruidoso por retomada silenciosa sobre dado
não-revisado. (Quando este parágrafo foi escrito, o predicado vivia **só** na camada
HTTP e o service era caminho vivo — é o RV8-08 do §r8, fechado em 2026-08-27 pela
[[A40.l84]] com emenda à [[ADR-404]].) Gate
`dev/check_diagnostic_session_isolation.py`. **Fica aberto:** RV6-11 é a mesma classe em
`llm_call_log.stage` e segue com writer fora do sink — lane própria.

**Nota datada 2026-08-21 — FP-5A remediado (#1567 `440d4618`, [[ADR-402]]); o braço cambial
segue aberto.** O diagnóstico do §r7 subestimava: não era "publica zero sobre base positiva",
era **valor correto sob rótulo errado**. `IRPFAnalyzer.pgbl_capacidade_dedutivel` devolve
`Decimal("0")` em declaração simplificada por contrato documentado, e `_analyze_via_irpf`
publicava esse *restante* num campo chamado *teto*. Consertar só "não publique zero" manteria
a mentira: quem aportou metade do teto continuaria lendo "Limite PGBL (12%)" com metade do
valor. Remediado separando as grandezas (`limite_pgbl_anual` = teto; `capacidade_restante_anual`
= restante), com `motivo_ausencia` **por campo** (enum fechado + precedência) e o invariante
`campo == 0.0 ⇒ motivo_ausencia[campo] is None`. `aliquota_marginal` passa a ser **bicondicional**
com `economia_ir_anual`: sem economia publicável ela era ruído citável ao lado de campos nulos.
Medido no payload do r7: `limite_pgbl_anual` **0.0 → null**, `aliquota_marginal` **positivo →
null**, `motivo_ausencia.teto = "modelo_simplificado"`, `nota` **1111 → 521 chars** (deixa de
concatenar dois motivos mutuamente exclusivos). Prova por mutação: 4 reversões, 4 quedas
(teto→restante 12 falhas; precedência invertida 4; alíquota incondicional 1; nota concatenada 3).
**Fica aberto:** o braço da **exposição cambial** (#1568) — verde e mergeável, não
mergeado; a ADR dele entra junto.

> **Nota datada 2026-08-24 (closeout da [[A40.l63]]).** O "fica aberto" acima
> venceu **no mesmo dia** em que foi escrito: o #1568 mergeou em 2026-08-21T15:53
> (`6c546d7b`) e a [[ADR-403]] está `Decidido`. A linha de FP-5 na tabela deste
> mesmo arquivo já o registra fechado citando esse SHA — o parágrafo e a tabela
> se contradiziam. **Não há braço cambial pendente do FP-5.** O que segue aberto
> na superfície de exposição é outro item, com dono: `caixa_fx` declara
> `cobertura: apurado` sem consultar `conversao.status`, então linha em
> `missing_rate` sai do total com o componente ainda dizendo que apurou —
> registrado na [[A40.l50]] (`open`). Precedente que ele reforça: RV2-08 foi declarado fechado 2× e reincidiu, e RV4-72
declarou `previdencia_pgbl` "correto" e reincidiu; os dois fechamentos foram **por inspeção**,
não por gate — daí o teste parametrizado `PgblStatus × regime_completo` asserindo coocorrência
campo↔nota.

**§Deferimento D2 — trava de concentração de lançamento (datado 2026-08-19).**
O braço de concentração do FP-2 (o brief pedia "lançamento único ≥10% da janela em
categoria não identificada ⇒ `needs_review`") **não foi construído**, e não por falta de
tempo: **o E5 não tem grão transacional**. `fluxo_caixa.despesas_por_categoria` é um mapa
categoria→total, e `transacoes` é **contagem inteira** no schema
(`config/schemas/e5_analysis.schema.json`); o grão de lançamento vive no E3
(`transacoes[]`), e o E4 publica `periodo` + `total_geral`. A detecção nasceria no E4 com
plumbing E4→E5 novo — construir meia-solução aqui repetiria o erro do DE-2.
O desenho também foi **corrigido** antes de deferir (co-design `financial-planner`): o
limiar certo é "cruza faixa de KPI publicado", não tamanho; a conjunção "categoria não
identificada" elimina a classe mais comum e tratável (anualidades bem categorizadas —
IPVA, IPTU, prêmio de seguro, matrícula); e o desfecho é **ressalva no KPI**, nunca
`needs_review` (≈20% de retenção mataria a categoria).
**Dono:** `data-engineer` (contrato E4→E5) + `financial-planner` (calibração do limiar).
**Condição de retomada:** existir no E5 um agregado por lançamento — ou o `top-N` de
lançamentos por categoria — sem exigir que o parecer leia o E3.

**§Deferimento D3 — wiring do catálogo de alvo de KPI (datado 2026-08-21).**
O catálogo determinístico está em `main` (#1557, `13deaa8f`, [[ADR-399]]) e **provado**:
resolve 6/10 sobre o payload real do r7, é **byte-idêntico entre r5 e r7** — o par exato em
que o alvo do LLM migrou `< 30%` → `< 35%` sobre `ratios.concentracao_imobiliaria`
byte-idêntico — e mutação na fonte move o alvo enquanto mutação no observado não move.
**Mas `build_kpi_targets` não tem call-site:** `analyze_finances.py` e `e5_serialization.py`
não o chamam, então em produção o parecer **continua publicando `target` gerado pelo LLM**.
O critério de aceite ("o publicado tem de ser o declarado") **ainda não é verdade** — o
defeito que PE-2 e FP-6 descrevem segue vivo no relatório entregue.
Falta: (a) `Metrica.metrica_key` (enum fechado) + `target`/`valor_atual` opcionais no schema
Pydantic e no JSON schema; (b) stamping em `parecer_pos_llm_guardrails` lendo `kpi_targets`;
(c) `kpi_targets` publicado no payload E5; (d) persona **seleciona a chave** e não autora
alvo nem valor, com bump de `PROMPT_VERSION`.
Deferido porque o passo **muda número publicado** — toca snapshot do view-model e goldens —
e a janela coincidiu com o rebaseline de classificação de ativo de outra onda; rebaselinar
por cima de rebaseline em voo é como o gate passa a aprovar a corrupção que deveria pegar
(precedente RV6-24: não congelar baseline com achado de classificação aberto).
**Dono:** `prompt-engineer` (contrato de saída + persona) + `data-engineer` (bloco
`kpi_targets` no E5 + schema).
**Condição de retomada:** nenhum rebaseline de golden em voo, e o diff de snapshot
**inspecionado item a item** — nunca regenerado no automático.

**§Refutação R1 — auto-contradição por par (seção, tema) (datado 2026-08-19).**
A regra ratificada para o FP-4 D3-B era: mesmo `(section_id, tema_canonico)` em ponto
forte e risco ⇒ remove o ponto forte. **Medida no parecer do r7: casa 2/5 pontos fortes e
1 é falso-positivo** — S2 + "Equilíbrio presente-futuro" aproxima "taxa de poupança alta"
de "gasto com saúde elevado": mesmo balde, assuntos diferentes. Removê-lo derrubaria o
ponto forte mais sólido do parecer. Casar só por `section_id` é pior (4/5). O par é um
**balde**, não identidade de assunto, e identidade exigiria âncora estrutural — mas
`PontoForte` é da classe PROSA-SEM-ÂNCORA (sem campo `ancoras`, ver
`parecer_evidencia._iter_prose_only_items`). R1 foi **rebaixada a contagem** em
`_meta.pos_llm_guardrails.autocontradicao_pares_secao_tema`; o desfecho ficou com R2,
cujo sinal vem do E5 (`avaliacao_liquidity == "Excessiva"`). Re-avaliar no r8 se a
contagem justificar predicado mais fino.

**§RV6-15 — metade fechada (datado 2026-08-19).** O #1575 fecha as duas cegueiras de
**parser** da RL2 (B4: exigia `%` literal e o schema tipa `["number","null"]`; B5: limiar
mensal contra produtor anual — 12% a.a. viraria hard-block em todo financiamento). Não
fecha B1/B2, o portão `_is_aporte_risco`: mexer nele mexe na **RL1**, que também é
hard-block, e exige eval próprio. E **não toca** o que o E5 publica em
`endividamento.dividas[]` (D4(i)/(ii) — agregado `debts`, `fonte`,
`desembolso_mensal_observado_brl`, preenchimento de `parcela_mensal`/`taxa_juros`), que
segue com o dono. Rótulo da taxa no card do relatório (`EndividamentoCard.tsx` renderiza
`%` sem período) fica atrelado à mesma decisão.

**Nota datada 2026-08-19 — PD-4 fechado no produtor, e o re-roteamento se confirmou.**
Entregue pela [[A40.l73]] ([[ADR-395]] `Decidido`) em 5 PRs: #1549 (lane + ADR) · #1554 (canal
`escopo_cobertura.categorias_somente_no_documento`) · #1560 (`e6774876`, retenção no populator) ·
#1564 (S9 de vazio para **parcial**) · #1576 (metade (i) + `pontos_urgentes`). Escopo fora do MVP
declarado da A40, aberto por decisão do dono.

**O diagnóstico do r7 estava certo e a lição do RV6-20 se pagou.** O #1476 tentou consertar
render-side e foi **no-op por construção**: os 4 sinais de `hasRealProtectionInputs` saem todos do
mesmo `protection_bundle`. O defeito era do produtor, que lia só o cadastro `Protection` e, com ele
vazio, publicava `actual = 0`, gap igual à necessidade integral e prescrição "alta" — enquanto a
seção vizinha listava as apólices vigentes extraídas dos documentos.

A regra decidida com o `financial-planner`: extração é **hint**, o número tem produtor único
(cadastro, [[ADR-192]]), as duas fontes **nunca somam** (não têm chave de identidade comum,
[[ADR-240]] §D12), e documento vigente numa categoria **sem** cadastro ativo é contraprova de
inventário incompleto ⇒ `missing_data`, sem entry em `gap_analysis`, sem prescrição. Isso é a
aplicação literal da [[ADR-387]] §D4. Categoria **com** cadastro continua computando: ali o gap
superestima a necessidade, que é o lado seguro da assimetria (descoberto é ruína irreversível;
prêmio duplicado é fluxo corrigível).

**Dois defeitos irmãos fecharam junto:** `_gap_analysis_to_response` coagia `actual` nulo para
`Decimal("0.00")` — retenção agora é ausência de entry + status, nunca zero fabricado; e a copy do
vazio **total** deixou de dizer "sem riscos cadastrados" (afirmação sobre o patrimônio do cliente a
partir de uma fonte só) para nomear o insumo que falta.

**O que NÃO foi tocado, de propósito:** o manifest do parecer e o prompt LLM — a precedência entre
fontes contraditórias no prompt é PE-3 / Onda 5. E o gate de `_categorias_de_documento`
(`cobertura_consolidada.py`) fecha `flag_vida` com **qualquer** `tipo == "vida"` vigente, sem
distinguir apólice **prestamista** (beneficiário = credor) nem **vida em grupo** do empregador
(morre com o vínculo) — defeito vivo, independente desta entrega, registrado como follow-up com
dono (`financial-planner` + `data-engineer`) em [[ADR-395]] §Deferido. Por isso o estado parcial
**nomeia** o identificado e **não afirma adequação de cobertura**.

**Re-triagem do §r6 (cadência).** Fechados por medição: RV6-01/02/03, RV6-07, RV6-23,
RV6-10 (com ressalva). Persistem re-priorizados: RV6-04 (P0, 3º run), RV6-11 (P1),
RV6-17 (P1, **âncora corrigida** — o campo registrado no r6 é dead code), RV6-13 (P2,
parcial), RV6-15 (P2, re-escopo — o campo do tripwire é nulo 3/3), RV6-20→PD-4 (P1, **fechado
2026-08-19** — ver nota datada acima),
RV6-22→PD-6 (P2), RV6-08→PE-2 (P1, agravado), RV6-09→PE-1 (P1, agravado),
RV6-05→PE-3 (P1, re-rotulado: o produtor está correto, o manifest é que não reconcilia),
RV6-06/RV6-12/RV6-14/RV6-16/RV6-18/RV6-19/RV6-21 mantidos na prioridade do §r6 (não
re-medidos neste run — ausência de medição não é fechamento).

---

## r8 — ws-1b9f2cf5-2026-08-24

> Skill pipeline-review ([[ADR-343]]) · run `d0f6260a` · tier premium.
> Execução: `completed` 18/18, 171 docs, 66,2 min, **CV 17/17**. Julgamento:
> 5 especialistas em paralelo + verificação adversarial (10 hipóteses refutadas,
> incluindo 3 minhas). Cru + baseline em `storage/<uuid>/reviews/` (off-git).

**Correção metodológica antes do run.** O worker Celery estava de pé desde a janela
do r7 e o checkout principal, 125 commits atrás de `main` (44 tocando
`pipeline/`/`backend/`). Rodar assim mediria o código do r7. O checkout foi
sincronizado e o worker reiniciado; `executor_revision` do run confirma o `main`
do dia. **Sem isso o r8 seria um quase-duplicado do r7** — vale como passo fixo
da skill, não como acidente desta sessão.

**Manchete: uma regressão de classe entrou junto com a consolidação de produtor
da [[A40.l77]] e nenhum instrumento a viu.** `_match_bucket` itera **baldes**
sobre `tipo + descricao` concatenados e `EVALUATION_ORDER` põe `Renda Fixa` antes
de `Fundos`; o produtor único que a l77 consolidou passou a incluir `tipo` no
entry, o que o resolver anterior não fazia. Reclassificando o mesmo corpus com e
sem `tipo`: `Fundos` cai de 12 para 2 itens e `Renda Fixa` sobe de 21 para 32 —
**11 de 61 posições, 16,6% do valor**, todas fundos de ações/multimercado
publicados como renda fixa com `autoridade: "keyword"`. Reclassificação **entre**
baldes preserva Σ, então os 17 CV passam, `nao_classificado_pct` não se move e
nenhum golden quebra: **a ausência de rebaseline na l77 não foi prova de que nada
mudou — foi o sintoma de que nada conseguia ver.**

**Segundo eixo: metade da carteira não tem dono e nenhuma superfície diz isso.**
`investivel_financeiro` **exclui** `investimentos_nao_atribuidos` enquanto
`_compute_bruto` **inclui** — as duas funções no mesmo arquivo. Consequência
medida: a banda de exposição cambial cruza para verde com o total em ME
**byte-idêntico** ao run anterior, e o parecer publica isso como ponto forte. O
parecer, porém, **não alucinou**: o manifest é whitelist e não projeta nenhum dos
seis campos de incerteza; ele ressalvou 3/3 lacunas que o payload declarou e 0/1
da que não declarou.

**Re-triagem do §r7** (cadência §Convenção item 4). `DE-1` e `DE-2` estavam em
`remediado — fecha por medição no r8`: **DE-2 fecha** (item acima do piso virou
razão e reteve o run; `sem_haystack` em 0) e **DE-1 fecha com ressalva** (houve
migração de classe, mas houve diff no classificador, então o predicado como
escrito não é violado; a ressalva é que `autoridade` só existe em duas superfícies
e "100% dos itens" não é mensurável sobre o corpus). `RV6-04` braço prosa
**refutado** (6/10 sumários mudaram). `FP-5` (PGBL) **fechado**. `FP-3` fechado no
eixo medido, com residual. `PD-4` refutado na copy, sobrevive como predicado.
`CTO-5`, `CTO-7`, `PD-3`, `PD-5`, `PE-1`, `PE-6`, `RV6-11` e `FP-4`
**reproduzidos** e re-ancorados abaixo. `DE-4`, `DE-5`, `DE-8`, `DE-9` e
`RV7-03/DE-3` do r7 **não foram re-medidos neste run** e seguem `procede-aberto`
sem alteração de prioridade — registrado para não decaírem em silêncio.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV8-01 — haystack plano faz o sinal genérico de `tipo` vencer o específico de `descricao` (`asset_classifier.py:32,207` itera balde, não campo; `patrimonio_resolvers.py:481` passou a incluir `tipo`): 16,6% do valor migra de fundo de ações para renda fixa com `autoridade: keyword`, sem razão e sem quebra de golden | correção | Crítico | P0 | procede (novo) | **procede-parcial-fechado** (2026-08-25) | **contenção shipada** · [[A40.l82]] `shipped` (#1698) · SHA `2fd2e60e` · [[ADR-400]] §Emenda 2026-08-25 · `tipo` sai da entry de `patrimonio_resolvers` e as 5 marcas de gestora saem do `_DEFAULT_KEYWORDS` **e** de `config/scoring.json` (só do default seria **no-op** — `merge_asset_keywords` deixa o scoring sobrescrever a classe inteira); gate comportamental `tests/unit/pipeline/test_classe_de_ativo_nao_le_tipo.py`; Σ preservado nas 3 colunas (194.647.320 cents) · ~~precedência de campo + gate de migração entre baldes run-a-run~~ **a rota escrita nesta linha não shipou e está gateada**: a [[ADR-400]] mede que o degrau 1 *reproduziria o RV8-01 com etiqueta melhor* enquanto o produtor não separar **default de grupo** de **evidência**; a pré-condição é `classify_asset_outcome` deixar de aceitar `tipo: str` posicional (dono `data-engineer`, janela J5) · **residual medido no fechamento**: a contenção **subavalia** a reserva da cônjuge em R$ 25.337,34 (110.130,67 → 84.793,33) — a `poupanca` dela saía de ramo de **evidência** e `tipo` era o único portador; o conserto é o `tipo_proveniencia` (dono `data-engineer`, [[ADR-400]] §"A contenção tem custo medido") · **não fecha o RV8-19**: `tipo` continua no hash de identidade |
| RV8-02 — `investivel_financeiro` exclui `investimentos_nao_atribuidos` e `_compute_bruto` inclui, no mesmo arquivo (`patrimonio_calculator.py:209-212` vs `:403-416`); todo KPI ancorado no denominador passa a medir "de quanto se sabe o dono" | consistência | Crítico | P0 | procede (novo) | procede-aberto | base canônica única, ou `base_ressalva` propagada aos 3 KPIs |
| RV8-03 — banda de `exposicao_cambial.pct_investivel_financeiro` cruza para verde com `total_brl` byte-idêntico ao run anterior; `pontos_fortes[]` publica a faixa como conquista | solidez-financeira | Crítico | P0 | procede (novo) | procede-aberto | base que inclua a fatia órfã + regra pós-LLM barrando ponto forte sobre base amputada |
| RV8-04 — `reserva_emergencia.composicao_liquida.investimentos_titular` diverge de `patrimonio.investimentos_titular` por fator >2× no mesmo payload: a reserva absorve a fatia sem dono sob rótulo de membro, e o bloco não tem campo de ressalva | correção | Crítico | P0 | procede (novo) | **remediado — fecha por medição no r10** (2026-08-27) | remédio em `main`: SHA `e8bd8448` ([[A40.l80]] PR2 #1727) matou `_positions_for_member` e o eixo B passou a `CarteiraPorPapel` com `Papel` ternário. **Predicado do r10:** `reserva_emergencia.composicao_liquida` publica `investimentos_nao_atribuidos` **e** nenhum valor sem dono aparece sob rótulo de membro. Medido hoje no `dogfood_view_model.json`: a chave existe ao lado de `investimentos_titular`/`_conjuge`. O r9 **não** re-mediu esta linha ("demais linhas do §r8 … sem alteração") — esta é a re-medição |
| RV8-05 — manifest do parecer é whitelist e não projeta `investimentos_nao_atribuidos`, `cobertura_investimentos`, `nao_classificado_pct`, `diagnostico_confianca`, `guarda_de_sinal` nem `pl_ressalva`; `_meta.tool_trace` fica em 3 paths de uma só raiz. A maquinaria de incerteza da A40 é inerte no único consumidor que prescreve | qualidade-llm | Crítico | P0 | procede (novo) | **procede-fechado** (2026-08-25) | **fechado por medição 2026-08-25** · [[A40.l83]] `shipped` (#1714 · SHA `b78b0793`; drift em #1716 · SHA `34544f0a`) · os 6 campos passam a ser projetados no bloco `patrimonio` (manifest 2.3.0) e 2 `narrative_hints` **consomem** veredito que já existia — [[ADR-353]] (`parcial` >10%, `insuficiente` >30%) e [[ADR-394]] §Emenda (`guarda_de_sinal.motivo_supressao`); nenhum limiar novo foi inventado · **a rota escrita nesta linha era metade**: promover o drift de `warn` a `fail` não bastava porque o check era **inerte** — derivava de `git diff HEAD`, vazio sob `pre-commit --all-files`, logo nunca existiu no CI (medido: 0 paths). O que o fez existir foi mover o baseline para a base de merge, e o gate agora **recusa ficar cego** (hard-fail sob `strict` quando `origin/main` é inalcançável) · no r8 o `diagnostico_confianca.nivel` estava em `insuficiente` (30,7%) e o parecer prescrevia sem receber isso · **residual**: 84 folhas do E5 seguem fora do manifest como débito herdado, publicado como contagem e não como allowlist |
| RV8-06 — `cobertura_de_membros` (`investimentos_cobertura.py:207-222`) itera **papéis** e `cobertura_investimentos[].membro` é enum fechado em titular/cônjuge: a fatia órfã não tem célula onde existir e `review_reasons_da_cobertura` só projeta `nao_apurado`. DE-7 do r7 é infixável no vocabulário atual | completude | Crítico | P0 | procede (re-ancorado do DE-7) | **remediado — fecha por medição no r10** (2026-08-27) | ⚠️ **o remédio escrito nesta linha foi REJEITADO**: abrir o enum de `membro` quebra leitor antigo lendo artefato novo (`CoberturaStatus(linha.get("status"))` levanta `ValueError`) e `cobertura_investimentos` particiona **pessoas** enquanto a órfã particiona **dinheiro** ([[ADR-412]] §D5; [[A40.l80]] C7). Remediado por eixo **irmão e ortogonal**: `patrimonio.atribuicao_investimentos`, SHA `f2cca647` (#1735), com piso próprio (`PISO_AGREGADO_PCT = 1.0`) e razão advisory. **Predicado do r10:** `atribuicao_investimentos.motivo` é não-nulo sempre que a fatia órfã cruza o piso. O r9 **não** re-mediu esta linha |
| RV8-07 — catálogo de citação colapsa em 2 raízes por `_PRIORITY_ROOTS` + `max_bytes`: ancorabilidade **zero** sobre o E5 real contra ~39% no snapshot sintético que gateia; e `coverage_failed` é fail-open (só conta âncora emitida que não resolve), devolvendo 0 com a maioria dos itens sem âncora nenhuma | qualidade-llm | Crítico | P0 | procede (re-ancorado do PE-1) | **procede-fechado** (2026-08-25) | **fechado por medição 2026-08-25** · [[A40.l83]] `shipped` (#1707 · SHA `8d468d1c`; KPI em #1709 · SHA `4165f9f8`) · catálogo semeado pelo conjunto visível: ancorabilidade no E5 real do run `d0f6260a` vai de **0/36 a 32/37 (86,5%)**; semear custa **zero** (0%→52,8% no orçamento intacto) enquanto subir bytes sem semear compra 25% a 3,1× · `citation_catalog_for` vira produtor único, então instrumento e produção não podem mais divergir · **a rota escrita nesta linha não serve na metade do `itens_sem_ancora`**: gate no golden mensal é impossível — esse eval **nunca rodou** (sem secret `ANTHROPIC_API_KEY_GOLDEN_MONTHLY`, 4 runs agendados pulando com `success` em 16–34s, `tests/golden_baselines/` vazia), e gatear ali seria fail-open dentro de fail-open. Entregue como **KPI logado** (`itens_sem_ancora` + `itens_total`, crus), que é o que o painel lê; o secret é **owner-gated** · **residual medido**: o snapshot que gateia segue otimista — 92,9% no sintético contra 86,5% em produção, e reverter a semente custa **7,2pp** ali contra **86,5pp** em produção (o delta do sintético ENCOLHEU, era 53,6pp, quando o orçamento subiu) → [[A40.l85]] |
| RV8-08 — guard de review pendente vive só na camada HTTP (`resume_run.py:21-29`); `pipeline_service.resume_pipeline_run` não consulta `stage_reviews`, e o comentário em `pipeline_task.py:1129` declara o invariante como se fosse global. Runs completam sobre review que ninguém aprovou | saúde-execução | Crítico | P0 | procede (novo) | **procede-fechado** (2026-08-27) | **fechado por medição 2026-08-27** · [[A40.l84]] · [[ADR-404]] §Emenda 2026-08-27 · o predicado sai da camada HTTP e passa a `stage_review_gate.py`, consultado na **mesma sessão** do `UPDATE` que flipa o status (contar numa e flipar noutra era TOCTOU por construção) · **a rota escrita nesta linha era incompleta em dois pontos**: (a) `_finalize_run` não é o único escritor de `completed` — `_mark_run_completed` grava direto quando o stage pausado é o último do `FULL_ORDER`, medido por execução; (b) `_finalize_run` **recusar** `completed` levantaria depois do trabalho feito e o `on_failure` gravaria `failed`, convertendo "ninguém decidiu" em "morreu" — ele **re-estaciona** a pausa, e só sobre desfecho que ENTREGA (`completed`/`partial_failure`, tupla LISTADA: `(failed, pending)` diz a verdade e `(cancelled, pending)` é resíduo sancionado da [[ADR-417]] D3) · o predicado é `NOT IN (approved, edited)`, não `== pending`: membro novo do enum destravaria calado · provado por mutação nos dois eixos (sem guard, o repark reprova; com o gate alargado para `failed`, o teste de escopo reprova) · **as 2 rows históricas ficam** — runs `33514dc4` (r7, `extract_with_llm`, review `064426fd`) e `d0f6260a` (r8, `analyze_finances`, review `bdbcdf63`): `approved` forjaria decisão humana que não houve, e a rota sancionada recusa por desenho. Congeladas por id em `dev/check_par_completed_pending.py`, que mede **quais**, nunca quantos, e trata banco vazio como WARN · **predicado do r9: o conjunto de ids não cresce — baseline 2, não 0** |
| RV8-09 — `record_review_reasons` tem call-site único dentro do ramo de pausa: stage WARN-first entrega razão no artefato e ela **nunca** chega à tabela. Exatamente os stages projetados para não pausar perdem 100% do diagnóstico | saúde-execução | Crítico | P0 | procede (novo) | procede-fechado | **fechado por medição 2026-08-25** · [[A40.l81]] `shipped` (#1697) · SHA `954f892f` · [[ADR-411]] `Decidido` · **a rota escrita nesta linha era insuficiente**: mover o sink sozinho colhe **zero** no `consolidate_baseline` (o `detail` dele não tem bloco `validation`), e o gate que shipou compara `detail`↔tabela por Σ `occurrence_count` — não artefato↔tabela por contagem · **medição A/B no mesmo corpus, mesmo dia, diferindo só no código do worker**: run `b4e0bb73` (worker de 24/08, pré-l81) → **0** rows de stages que entregaram, `locator` 0/2; run `7164ddee` (worker reiniciado) → **5 rows / Σocc 32** de stages que entregaram (`consolidate_baseline` 2, `reconcile_transactions` 3), `locator` 7/7. Total 7 rows / Σ37 contra 2 / Σ3 antes · **defeito achado na medição e corrigido**: o re-harvest do orquestrador sobrescrevia o `locator` do item · **residual**: a perna de diagnóstico do `compare_reviews` só sai da cegueira com baseline em snapshot v3 (run com LLM) |
| RV8-10 — linha de lacuna de titularidade entra na composição com a **mesma forma** dos baldes reais e `classify()` a marca `apurado` por ter valor > 0, então `donutSlices` a desenha como fatia categórica (`visibleCompositionRows.ts:47-51,75-79`) | clareza-ux | Alto | P1 | procede (novo) | procede-aberto | `kind` no produtor + estado `sem_atribuicao` + anotação fora das fatias |
| RV8-11 — `llm_call_log.stage` interpola nome de arquivo e excede a largura declarada da coluna; além do truncation em Postgres, explode a cardinalidade da dimensão de custo e torna **falsa** a justificativa de exclusão LGPD "sem conteúdo do titular" (`lgpd_export_service.py:191`) | contrato | Alto | P1 | procede (re-ancorado do RV6-11, agravado) | procede-aberto | `stage` volta a ser identificador; discriminador de documento em coluna própria; corrigir a rationale |
| RV8-12 — `dev/review_snapshot.py` soma custo de `pipeline_run_costs` (tabela sem escritor desde a Fase 1 do DE-01) e lê `transacoes_total` de um payload que não o contém: 3 campos são `null` **por construção** nos dois runs e `_tx_regression` nunca dispara | saúde-execução | Alto | P1 | procede (novo) | procede-aberto | custo de `llm_call_log`, volume do artefato de reconcile |
| RV8-13 — dois leitores independentes do conjunto de imóveis da família, com predicado divergente (`especulacao` conta num e não no outro) e fonte divergente; a paridade deste run é acidente de corpus, não invariante | consistência | Alto | P1 | procede (novo) | procede-aberto | invariante de conservação de `set(property_id)` em `test_e5_conservation_invariants` |
| RV8-14 — auditoria de paridade FinOps itera a tabela congelada, encontra zero rows, imprime "paridade confirmada" e retorna 0 — autorizando o `DROP` sobre universo vazio (`de01_finops_parity_audit.py:66-89`) | saúde-execução | Alto | P1 | procede (novo) | procede-aberto | piso de amostra: universo vazio ⇒ exit≠0 |
| RV8-15 — opt-in de cache existe e é usado por **um** stage; os demais já satisfazem a pré-condição de temperatura e não optam, e a maior parte do gasto mensal é prompt byte-idêntico repago | saúde-execução | Alto | P1 | procede (novo) | procede-aberto | `use_cache` nos stages de extração + coluna `cache_hit` para tornar o hit-rate derivável |
| RV8-16 — `field_request_spurious` classifica consultando o E5 enquanto a afirmação do modelo era sobre o **catálogo**; e placeholder de ausência de domínio conta como `present`. Pedidos legítimos são podados do output do usuário e o contador inverte o diagnóstico (truncamento vira "alucinação") | qualidade-llm | Alto | P1 | procede (novo) | **procede-fechado** (2026-08-25) | **fechado por medição 2026-08-25** · [[A40.l83]] `shipped` (#1712 · SHA `b1f28113`) · [[ADR-206]] §Emenda 2026-08-25 (enum sob `additionalProperties: false`) · filtro passa a 4 vias e `field_request_out_of_catalog` **audita sem remover** — é a única pista, no output, de que o contexto truncou · **aferido por replay do `_meta.field_request_audit` do r8**, não por unit test: `field_requests_spurious` **2 → 0**, com os dois pedidos reaparecendo no output, um por cada mecanismo (sentinela de domínio ausente e universo trocado) · `catalog_paths` é keyword **obrigatório** para que call-site novo não herde em silêncio a pergunta ao universo errado · **precisão do enunciado**: o discriminador de sentinela não é a palavra, é a **posição** — `nao_identificado`, `saldo_desconhecido` e `sem_match` ficaram FORA de propósito porque **são** o dado, e incluí-los faria o erro simétrico |
| RV8-17 — `investimentos.nao_classificado_itens[]` chegou ao payload, ao schema e ao tipo gerado e tem **zero** consumidores no frontend: o run reteve por um item que a tela não menciona | clareza-ux | Alto | P1 | procede (PD-3 do r7: só a metade produtora fechou) | procede-aberto | disclosure na linha catch-all com locator + peso + badge de autoridade |
| RV8-18 — predicado de vazio da seção de proteção lê um só bundle e nega gap que outras duas superfícies do mesmo payload afirmam apurado | consistência | Alto | P1 | procede (PD-4 re-ancorado: copy corrigida, arquitetura não) | procede-aberto | predicado sobre a união das fontes |
| RV8-19 — identidade de posição é hash de campos de extração LLM, incluindo o mesmo `tipo` degenerado do RV8-01: a maior parte dos identificadores não sobrevive entre dois runs do mesmo corpus, e o locator que a `review_reason` entrega ao operador não é reencontrável | correção | Alto | P1 | procede (novo) | procede-aberto | tirar `tipo` da chave; ancorar em fato do documento; medir sobrevivência run-a-run |
| RV8-20 — nenhum stage **escolhe** o model caro: ele é herança de config de workspace, e as duas únicas escolhas explícitas do repo rebaixam — uma delas a síntese aberta do parecer, que não tem verificador a jusante | qualidade-llm | Médio | P2 | procede (PE-6 reproduzido) | procede-aberto | mapa stage→tier versionado em ADR; golden nos dois tiers |
| RV8-21 — resolução de ano é **per-membro**, não per-item: item cujo único ano declarado difere do máximo do membro cai num fallback sobre chave inexistente e vira zero com ano nulo — conflação ausência↔zero que a [[ADR-394]] proíbe um andar acima | correção | Médio | P2 | procede (novo) | procede-aberto | resolver por item; ausência ⇒ `None` + razão; matar o fallback |
| RV8-22 — `compare_reviews` tem supressor único e ortogonal à causa do drift, então corpus idêntico + correção de código produz reprovação em massa; e o mascaramento de path colapsa o índice da série temporal, deixando o operador sem rota até a linha | saúde-execução | Médio | P2 | procede (CTO-5 reproduzido e agravado) | procede-aberto | baseline como **par declarado** (PRs/ADRs entre as pontas); agregar drift por path; preservar índice ordinal |
| RV8-23 — `cobertura_completa` (sign guard) e `cobertura_investimentos` (atribuição por membro) convivem no mesmo objeto com semânticas distintas, e o campo booleano não tem `description` no schema; há colisão análoga em `alertas` | consistência | Médio | P2 | procede (novo) | procede-aberto | renomear o booleano para o predicado que ele calcula |
| RV8-24 — endurecimento de rótulo de imóvel cobriu a rota do relatório e deixou telas do app lendo o campo cru **primeiro** na cascata; a duplicação do helper em 3 arquivos é o motivo de o fix ter pego só uma | clareza-ux | Médio | P2 | procede (RV6-17 re-ancorado) | procede-aberto | produtor único de rótulo + gate que barre referência fora dele |
| RV8-25 — prosa gerada por LLM emite decimal em locale en-US e chega crua a dois caminhos de render; o mesmo relatório formata correto onde o número vem de template determinístico, o que isola a causa no caminho de prosa | clareza-ux | Médio | P2 | procede (PD-5: metade reproduzida, metade refutada) | procede-aberto | asserção de locale no golden do narrador + reask; **não** sanitizar por regex no render |
| RV8-26 — estado `zero_apurado` é inalcançável porque os dois call-sites omitem o argumento de cobertura, e o comentário que justifica a omissão está vencido — o payload já traz o campo | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | passar a cobertura ou remover o estado |
| RV8-27 — tabela de top ativos publica rótulos idênticos para itens distintos e esconde o único desambiguador abaixo do breakpoint; o payload emite valor de `autoridade` **fora** da união declarada no tipo gerado | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | desambiguar no produtor; promover o desambiguador à sublinha; corrigir a união |
| RV8-28 — kill-switch de gate de classificação/cobertura não deixa rastro: com a env desligada o run fica indistinguível de run limpo | saúde-execução | Médio | P2 | procede (CTO-7 do r7 confirmado aberto) | procede-aberto | `validation.gates_desligados` (campo aditivo) |
| RV8-29 — dívida declarada não tem relógio: o "registro" do enum sem produtor é teste de polaridade invertida sobre amostra pequena, que passa enquanto a dívida existe e **falha no dia em que ela for paga** | saúde-execução | Médio | P2 | procede (novo) | procede-aberto | registro datado com dono lido pelo CI (precedente: waiver que vence) |
| RV8-30 — `dev/run_provenance.py` afirma em prosa uma temperatura que o código não usa; o `run_meta` de **toda** revisão informa ao revisor a causa errada da irreprodutibilidade. As reais são seed descartado pelo provider, model em alias não-datado e config em DB | saúde-execução | Médio | P2 | procede (novo) | procede-aberto | corrigir a frase; registrar snapshot resolvido na telemetria |
| RV8-31 — prescrição de alocação segue sem ressalva visível com taxa de dívida nula em todas as dívidas; o contador do guardrail fica em zero porque casa prescrição **de dívida** e não prescrição **de alocação que pressupõe dívida barata**, e o parecer promove juízo sobre qualidade da dívida a ponto forte | solidez-financeira | Médio | P2 | procede (FP-4 do r7 reproduzido) | procede-aberto | com taxa nula, barrar juízo sobre qualidade e ressalvar na seção, não só em meta-diagnóstico |
| RV8-32 — este índice nomeava env de kill-switch que não existe no código; quem verificasse por grep concluiria que o kill-switch não existe | saúde-execução | Baixo | P3 | procede (defeito deste índice) | **procede-fechado** | correção **anotada in loco** na célula do §r7 (o nome errado fica como evidência do que foi escrito); a env real é `MATHOMS_E5_COBERTURA_MEMBRO` |
| DE-1 (r7) — migração de classe sob re-extração | correção | Crítico | P0 | — | **fecha com ressalva** | predicado cumprido como escrito (houve diff no classificador); ressalva: `autoridade` não tem domicílio no registro geral de posição, logo "100% dos itens" não é mensurável |
| DE-2 (r7) — sensor de catch-all só por nível | correção | Crítico | P1 | — | **fechado por medição** | [[ADR-406]]: item acima do piso virou razão e **reteve o run**; `sem_haystack` em zero |
| RV6-04 (r7) braço prosa · FP-5 (r7) PGBL · FP-3 (r7) eixo dos agregados | — | — | — | — | **fechados** | prosa respondeu ao dado; PGBL publica ausência com motivo; agregados de imóvel batem por correção de eixo de ano-base |
| DE-4 · DE-5 · DE-8 · DE-9 · RV7-03/DE-3 (r7) | — | — | P1 | — | **procede-aberto (não re-medido no r8)** | mantidos sem alteração de prioridade; registrados para não decaírem em silêncio |
| Refutados nesta rodada | — | — | — | **refutado** | fechado | instituição fora do haystack como causa da migração de classe; `desconhecido` como eixo da divergência de imóveis; endereço/terceiro verbatim em descrição de imóvel; cache servindo payload anterior; contaminação de trajetória no parecer; dois models no mesmo stage (é cascata deliberada); tabela de custo vazia como anomalia (é desenho — o defeito é o consumidor, RV8-12/RV8-14) |

---

## r9 — ws-1b9f2cf5-2026-08-26

> Rodada unificada **U1** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r5 · [[REPORT-REVIEWS-active]] §r5.
> Run `c97b97c2` `completed` 18/18 · 25,5 min · executor `1eb6a8bf` · report `97a76360`.
> Painel: 5 lentes com eixo primário + braço cego com trava · 7 céticos (**1 confirmado /
> 6 parciais / 0 refutados** — *zero sobreviveu inteiro*) · crítico de completude: sim.
> Cru + síntese com valores: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

**A rodada procede sobre 6 avisos retidos.** O run pausou em `analyze_finances` com 4 ativos
materiais na catch-all de classificação, a fração não classificada da carteira acima do piso
agregado, 1 posição sem instituição e 1 investimento sem titularidade — **zero errors**.
Aprovado pelo caminho sancionado e retomado. Toda linha de `solidez-financeira` e as
perguntas Q2/Q4/Q6 herdam a condição.

**Desvio de gate declarado.** O `sync-main` reprovou (checkout 1 commit atrás de
`origin/main`) e o delta medido era **um arquivo em `dev/`**, que o pipeline não importa.
Disparado com o desvio escrito no estado durável. O executor real do run confirma
byte-identidade do código de pipeline com `origin/main`; o `-dirty` vem de dois sidecars
SQLite, nenhum código.

**Manchete: a proveniência afirma sobre um substrato que ela não observa.** Nenhum dos campos
do bloco de proveniência lê a tabela de artefatos consumidos; `execucao_mista` deriva das
revisões dos stages **executados** e é `false` por construção em run completo. O cético
refutou a leitura forte — a partição binária de um stage era **reuso legítimo** (ele
curto-circuita com `skipped` quando não há documento novo) — e o defeito do **claim**
sobreviveu inteiro.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| PV9-01 — o bloco de proveniência não tem predicado sobre insumo e chama a si mesmo de proveniência: `mixed_execution` itera as rows do próprio run, e nenhum dos campos de `provenance_context` deriva de `pipeline_artifacts` | contrato | Alto | P1 | PARCIAL (execução mista refutada; o claim sobrevive) · inerte-para-usuário | procede-aberto · agrega DE-4 do §r7 | predicado ortogonal `insumo_herdado`, com quebra por run de origem. "Auto-contido" é conjunção de quatro termos, não um |
| PV9-02 — `_SKIPPED` do `run_scope` **nunca casa**: o produtor mapeia `skipped` para `completed` de propósito (ADR-357 §2), então `skipped_stages()` não vê skip auto-declarado e o escopo publica `full` contando stage que computou zero | saúde-execução | Médio | P2 | procede (novo) | procede-aberto | mapa exaustivo `status → classe` que falhe por ausência, forma do `RUN_EXIT_BY_STATUS` da [[ADR-417]] |
| PV9-03 — `run_scope` derruba silenciosamente o stage que pausou o run e os que degradaram; o whitelist de status **falha aberto** e `scope_kind` devolve `full` para run interrompido por decisão humana | saúde-execução | Alto | P1 | procede (novo) | procede-aberto | `provenance_lines` ganha linha obrigatória de pausa: quem pausou, quantas issues, resolvido por qual ação |
| PV9-04 — a suíte de cross-validation tem **severidade constante**: `info` em 17/17, `passed` em 17/17. Dois passam por **isenção** declarada. `falhas=[]` é tautologia, não evidência de correção | contrato | Alto | P1 | procede (novo) | procede-aberto | pelo menos um check com severidade capaz de reprovar, ou o consumidor para de ler a lista vazia como verde |
| PV9-05 — contador de guardrail que só pode dar zero: a tabela de alias que o alimenta está **vazia** desde o r7, e o classificador só emite a razão por lookup nela. Enquanto isso o parecer pediu um path alegando ausência de um fato que existe em outro path | contrato | Alto | P1 | procede (novo) | procede-aberto | antes de ler contador em zero como verde, verificar se ele **pode** ser não-zero |
| PV9-06 — `pontos_urgentes` é a superfície determinística de risco e tem **4 regras hard-coded**, nenhuma lendo `kpi_targets`; o catálogo canônico de limiar ([[ADR-399]], declarado "leitor único") é **órfão** — existe no tipo gerado e em nenhum componente | completude | Alto | P0 | procede (novo; **corrige o alvo** da leitura inicial, que acusava `alertas`) | **fechado 2026-08-29** | [[A40.l90]] em 5 PRs (#1812 → #1816), sob a [[ADR-419]] (`Proposto`). O gatilho de risco passou a derivar de um **registro de doutrina** tipado — não de `kpi_targets`, que é resolvido sobre o payload FINAL e seria leitura circular; o corte cai de graça porque todo limiar de doutrina é payload-independente. Cada regra declara `kpi_key`, e um **gate estático de cobertura** (`elegíveis ⊆ com-regra ∪ dispensadas-com-motivo`) reprova chave nova sem leitor — que é como este catálogo nasceu órfão. `concentracao_imobiliaria` ganhou regra graduada; no dogfood ela estava em **82,19% contra limiar de 50%** e a superfície determinística não dizia nada. **Dois ataques medidos antes de executar** (#1766/#1767, #1810) refutaram 4 afirmações do próprio atacante — entre elas que `exposicao_cambial` estivesse "rompido" (o produtor **suprimiu** o veredito) — e mostraram que o invariante proposto pela lane **passava com o defeito inteiro presente**. **Ressalva:** a gradação da reserva segue no §Deferimento, dono `financial-planner` |
| PV9-07 — o veredito determinístico de perfil de renda existe no produtor e **não chega ao parecer**: o manifest projeta os valores absolutos por natureza e não o enum classificado nem o percentual. O modelo autora o veredito de resiliência sem ver o veredito que o pipeline já calculou | qualidade-llm | Alto | P1 | procede (novo) | procede-aberto | projetar `perfil_renda` + o percentual no exec context |
| PV9-08 — a mesma composição de renda é precificada como **força** num ponto forte e como o **motivo de elevar o alvo de reserva** no ponto forte anterior, no mesmo output | solidez-financeira | Alto | P1 | PARCIAL (o eixo de regime procede e tem lastro; a contradição interna é o achado) | procede-aberto | guardrail de autocontradição passa a **agir**, e a chave deixa de ser `(seção, tema)` — o par mais caro é cross-section |
| PV9-09 — o guardrail de autocontradição contou 3 pares e agiu em **zero**; o de sugestão antagônica **disparou** e não alcançou nenhuma superfície nem o brief da rodada | qualidade-llm | Médio | P2 | procede (novo) | procede-aberto | contador que dispara sem consumidor é telemetria morta |
| PV9-10 — ponto forte de trajetória **sobrevive no E5** depois que o guardrail o removeu do parecer, e renderiza na tela e no print, enquanto a comparação registra queda no patrimônio líquido | correção | Alto | P1 | procede (novo) | procede-aberto | o guardrail roda sobre o conjunto unificado de pontos fortes, não só sobre o ramo LLM |
| PV9-11 — o separador de transferência patrimonial está **inerte nas quatro janelas** (`transferencia_patrimonial_mensal = 0.0` e consumo == despesa média), enquanto o ranking de gastos pontuais traz uma conversão cambial e um depósito rotulado como aporte | correção | Alto | P1 | procede (novo) | procede-aberto | a taxa de poupança e a classificação de equilíbrio orçamentário herdam base de despesa inflada por movimento patrimonial ([[ADR-333]]) |
| PV9-12 — a mesma moeda entra como **despesa e como ativo**: uma conversão cambial conta como gasto pontual e o saldo resultante conta como caixa em exposição cambial; o maior pontual da janela tem descrição de instituição e categoria não identificada | correção | Médio | P2 | procede (novo) | procede-aberto | medir a fração de despesa com contraparte em conta própria — gateado por LC5-06 |
| PV9-13 — `folga_mensal` remove 100% dos gastos pontuais e a prescrição de teto **ancora nela**; duas sobras publicadas na mesma janela divergem em ~19 pp e a maior é a que prescreve | consistência | Alto | P1 | procede (novo) | procede-aberto | invariante proposto: `\|folga_mensal − taxa_poupança × receita recorrente\| ≤ ε` — falha hoje |
| PV9-14 — a definição de exposição cambial **impressa na página** não é a implementada: o componente de lastro estrangeiro vale zero com cobertura `indeterminado`, e o denominador consome o zero. A prescrição aponta a **perna errada** — a de caixa já excede o alvo declarado | correção | Alto | P0 | procede (novo; agrava RV8-03) | procede-aberto | quando a cobertura é indeterminada o componente não contribui com zero: ou suprime a banda, ou publica por perna com a cega marcada |
| PV9-15 — o tier cambial **troca de sinal entre runs** porque a base é amputada: no §r8 cruzou para verde e virou ponto forte; neste run saiu amarelo e virou risco. O parecer lê o campo corretamente — não é alucinação | correção | Alto | P0 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-02/RV8-03) | procede-aberto · **re-triagem devida** (2026-08-27) | corrigir o denominador no produtor; consertar no prompt seria consertar o lado errado · ⚠️ **o remédio prescrito já estava em `main` quando este run rodou**: SHA `e8bd8448` (#1727) mergeou 2026-08-25 18:46 UTC e o r9 é de 26/08 com byte-identidade de código declarada no cabeçalho. E a [[ADR-412]] §Consequências **previu** o movimento observado — `pct_investivel_financeiro` `12,55% → 6,40%`, que cai na faixa amarela. Logo "saiu amarelo" pode ser **a correção**, não o defeito persistindo — a armadilha que a [[A40.l80]] §Raio de explosão nomeia ("vai parecer defeito e não é"). Não re-disposto aqui: decidir exige medir o run, não reler. Owner: quem triar o r10 |
| PV9-16 — `if_meta` é composta pela fórmula **bruta** e consumida nos slots **líquidos**: os três campos publicados fecham a identidade bruta ao centavo, mas o gap e o progresso são as fórmulas líquidas | correção | Alto | P0 | PARCIAL (a leitura da identidade procede; a inferência de que o número está errado **cai no regime medido**) | **procede-fechado** pela [[A40.l91]] (PR #1753, 2026-08-27) sob a [[ADR-418]] | a meta é **derivada** (resíduo R$ 0,00). Mas descontar a renda passiva **observada** seria dupla-contagem: o `patrimonio_gerador` que a produz é **93,10%** do numerador. O que decide é o **par** numerador↔meta, e o toggle `imoveis_no_if` o governa — com `true` (este run) o publicado está **certo**; com `false` (o **default**, [[ADR-223]]) a meta não desconta o aluguel de bens que ela mesma excluiu: meta **+9,56%**, progresso **−1,74 pp**. Uma base só + base publicada em dados; `CV5` deixa de ser tautologia |
| PV9-17 — limiar **suprimido** no registro reaparece como referência em prosa determinística e como alvo no parecer | contrato | Alto | P1 | procede (novo) | procede-aberto | prosa só cita limiar cujo `kpi_targets[*].limiar` seja não-nulo; se `null`, a frase perde o comparador |
| PV9-18 — prescrição de realocação aponta para alvo que o motor **suprimiu com motivo publicado**, e a própria página confirma a supressão duas seções abaixo | consistência | Médio | P2 | procede (novo) | procede-aberto | com o destino suprimido, nenhuma prosa pode conter o lema da classe defasada |
| PV9-19 — o parecer declara **ausente** a alocação-alvo que a família declarou, e a tabela por classe está renderizada | qualidade-llm | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-05) | procede-aberto | o custo da whitelist do manifest não é campo faltante genérico — é a prescrição de rebalanceamento inteira |
| PV9-20 — a precondição de regime oficial de previdência se perde na travessia E5 → parecer: o E5 a codifica e o parecer reproduz só a metade do modelo de declaração | solidez-financeira | Médio | P2 | procede (novo) | procede-aberto | a precondição vira campo estruturado, não prosa em nota |
| PV9-21 — o corte de provisionado e a consolidação cross-documento **não alcançam nenhuma superfície de render**: o dado existe, o tipo existe, o destino não | completude | Alto | P1 | procede (novo) | procede-aberto | check de cross-validation no molde do CV9 (destino declarado × site de render), aplicado aos dois |
| PV9-22 — a consolidação declara `count` por mês e **nenhum valor**, enquanto a camada computa os cents removíveis e os descarta | contrato | Médio | P2 | procede (novo) | procede-aberto | o bloco ganha `cents` no schema |
| PV9-23 — a média mensal da janela divide por mês **parcial**: todo run feito no meio do mês subdeclara as três médias | correção | Médio | P2 | procede (novo) | procede-aberto | ponderar o último mês pela fração decorrida, ou excluí-lo e declarar o rótulo real — escolher **uma** e travar com golden |
| PV9-24 — a janela mistura duas fontes para a mesma grandeza e a tabela **descarta resíduo negativo**: categoria com líquido ≤ 0 some da tabela e permanece no total, e o resíduo negativo desaparece da normalização | consistência | Médio | P2 | procede (novo) | procede-aberto | fonte única, ou emitir resíduo negativo explicitamente. Mutação: injetar categoria de líquido negativo |
| PV9-25 — a máquina de tools do parecer não tem **loop**: o cliente LLM não aceita `tools` e a chamada é single-shot, enquanto o system prompt instrui o modelo a citar valores "retornados por tool" | contrato | Médio | P2 | PARCIAL (o bloco `tools:` **é** carregado e o enum governa a whitelist de resolução; o "vestigial" cai) · JÁ-CONHECIDO (RV4-43) | procede-aberto | decidir num PR só: ou o loop existe, ou a instrução sai do prompt e do manifest |
| PV9-26 — **três** caminhos de eval real do parecer nunca executaram: 20 runs verdes pulando por secret ausente, e o comparador do golden **nunca teve baseline** (o diretório não existe). O pin do modelo se justifica citando um deles | contrato | Alto | P1 | **CONFIRMADO** · inerte-para-usuário | procede-aberto | owner-gated para os secrets; **não** owner-gated: workflow que reporta sucesso sobre skip |
| PV9-27 — `schema_validation_drift` em 6 de 18 stages, todos passando em modo `warn` | contrato | Médio | P2 | PARCIAL (a [[ADR-409]] já decidiu a fila e **rejeita** o flip global; os 6 colapsam em 4 schemas já classificados) | procede-aberto | sobra **uma** linha nova: o schema do E5 estava em "reavaliar após 1 run novo" e **este é o run novo** — o drift persiste |
| PV9-28 — a telemetria de review rotula aprovação de 6 warnings como `approve_clean`, e o ramo legado conta **toda linha como erro**: o rótulo é função de qual coluna está preenchida, não do conteúdo | contrato | Médio | P2 | procede (novo) | procede-aberto | três baldes; alinhar o discriminante ao do gate de pausa — se aviso pausa o run, aviso não é "clean" |
| PV9-29 — a guarda de review pendente vive **fora da transação** que ela protege: o use case lê a contagem numa sessão e o flip acontece em outra. TOCTOU por construção, agravado agora que existe um segundo ator sobre o estado pausado | saúde-execução | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-08) | **procede-fechado** (2026-08-27) | **fechado com o RV8-08** · [[A40.l84]] `shipped` (#1771 · `07cd5c66`) · o predicado passou para `_flip_run_to_resuming`, dentro da transação do `UPDATE` · **a rota escrita aqui divergiu do entregue e a divergência é deliberada**: ela dizia *"a checagem HTTP **fica**, rebaixada a UX"*, e a checagem async do `resume_run.py` foi **removida**. Mantê-la seria conservar um segundo produtor do mesmo predicado — a forma do próprio RV8-08 —, e o efeito de UX que a rota queria comprar **não se perde**: a rota segue respondendo **409**, agora pela tradução do `ValueError` do service (verificado ponta-a-ponta contra a API, com a mensagem nomeando stage e review). O `resume_run` não tem caminho próprio de flip, então não há o falso-verde que a [[A40.l27]] pagou com o cancel duplicado |
| PV9-30 — `StageSpec.writes` é contrato **consumido e sabidamente falso**, e a falsidade está numa docstring em vez de num gate: um stage declara escrever um artefato que nunca existe, e o validador de ordenação valida contra ele | contrato | Alto | P1 | procede (novo) | procede-aberto | tornar `writes` verdadeiro e gatear: `writes ≠ ∅ ⇒ artefato emitido`. **É o X5 corrigido** |
| PV9-31 — o `stage` do log de chamada LLM interpola filename de documento, incluindo razão social de terceiro; e o campo é a **chave de junção** do único caminho de FinOps que resta, então a auditoria nunca sai zero-mismatch | contrato | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-11, com consequência nova) | procede-aberto | `stage` volta a ser identificador; discriminador de documento em coluna própria, por hash |
| PV9-32 — `riscos` **saturou o cap do schema**: o máximo declarado e o produzido são o mesmo número. Truncagem-por-cap é indistinguível de "existem N riscos" | qualidade-llm | Médio | P2 | procede (novo) | procede-aberto | emitir sinal quando o cap morde |
| PV9-33 — o cenário de estresse contradiz o próprio apêndice na unidade e aterrissa no mesmo ano do cenário central, o que faz o teste parecer inerte | consistência | Médio | P2 | procede (novo) | procede-aberto | um só cálculo de delta alimentando seção e apêndice |
| PV9-34 — ausência de dado do cônjuge renderizada como **zero**, na frase anterior à que afirma que sem a renda dela o aporte cai um terço | correção | Alto | P1 | procede (novo) | procede-aberto | traço + "não apurada"; bloquear o cenário de estresse quando o insumo que ele estressa está ausente |
| PV9-35 — duas tabelas do mesmo relatório dão respostas **mutuamente exclusivas** sobre titularidade: uma publica a fatia sem dono, a outra atribui membro nomeado a todas as linhas | consistência | Alto | P0 | procede (novo) | procede-aberto | uma só função de atribuição alimentando as duas; fallback visível na célula |
| PV9-36 — "renda passiva" tem três valores e dois significados, com o rótulo trocado na tabela de metas | clareza-ux | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de RV4-13: a inversão chegou ao **rótulo**) | procede-aberto | um rótulo por número: recebida vs. potencial pela regra de retirada |
| PV9-37 — `run_meta` declara uma temperatura que o código não usa, e errado no sentido pessimista | contrato | Baixo | P3 | procede (novo) | procede-aberto | o gerador lê a constante em vez de repeti-la em prosa |
| PV9-38 — o painel do entregável lê um sink em sunset e imprime custo zero ao lado do custo real | clareza-ux | Baixo | P3 | procede (novo) | procede-aberto | a linha de custo sai só da tabela viva |
| RV8-09 · RV8-32 (§r8) | — | — | — | — | **fechados** | mantidos como fechados; não re-medidos nesta rodada |
| RV8-01 · RV8-02 · RV8-03 · RV8-05 · RV8-07 · RV8-11 · RV8-19 (§r8) | — | — | — | — | **procede-aberto (re-ancorados acima)** | PV9-15/14 re-medem RV8-02/03; PV9-19 re-mede RV8-05; PV9-31 re-mede RV8-11 |
| Demais linhas do §r8 não re-medidas neste run | — | — | — | — | **procede-aberto (sem alteração)** | registrado para não decaírem em silêncio |

**Refutados nesta rodada** (taxa de refutação ≠ 0 é requisito de calibração): execução
materialmente mista como causa da partição binária — o stage curto-circuita por ausência de
trabalho · `alertas` como superfície determinística de risco — nunca carregou limiar, e o
docstring declara lista vazia como empty state honesto · "máquina de tools vestigial" — o
bloco é carregado e governa a whitelist de resolução · promover o drift de schema a `fail` —
decisão já tomada e explicitamente rejeitada · filtrar o gate de sincronia por path — `dev/`
**é** o instrumento, e o commit que de fato contaminou a rodada estaria dentro da whitelist
proposta.

**Positivos verificados.** Run `completed` 18/18 · determinismo do categorizador fecha ao
centavo sobre o E3 do próprio run · zero-write do harness provado · as três superfícies de
render geram sem truncagem e o PDF de produção sai íntegro · ancoragem monetária do parecer
sem órfãos (com a ressalva de denominador em [[REPORT-REVIEWS-active]] §r5) · o guardrail de
dívida absteve-se corretamente em 4 de 4 quando a taxa estava ausente.

## r10 — ws-1b9f2cf5-2026-08-29

> Rodada unificada **U2** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r6 · [[PIPELINE-REVIEWS-active]] §r10 (este) · [[REPORT-REVIEWS-active]] §r6.
> Run `79a61e33` `completed` 18/18 · 25,5 min · executor `887579734428` · report `c011c40c`.
> Painel: 5 lentes com eixo primário + braço cego com trava · 3 lotes de céticos (**2 REFUTADO / 14 PARCIAL / 2 CONFIRMADO**) · crítico de completude: sim.
> Preflight 11 PASS · 4 WARN · 0 FAIL. Cru: `storage/<uuid>/reviews/U2-2026-08-29/` (off-git).
> Cobertura: matriz 7×3 — **3 células SEM COBERTURA declaradas com motivo**, 1 N/A por roteamento, 1 reivindicada-e-estruturalmente-vazia.

**A rodada procede sobre 7 avisos retidos, e desta vez eles estão enumerados** (o §r9 não
os enumerou, e isso virou o item 1 do §Débito de método): 4 ativos materiais na catch-all
(2,58 · 1,90 · 1,17 · 0,85% da carteira), fração não classificada em **6,51%** acima do
piso, 1 posição sem instituição, e **1 investimento sem titularidade em 49,03% da carteira
financeira** contra validador que espera `< 1,0%`. Zero errors. Aprovados pelo caminho
sancionado; o resume entra no stage **seguinte** e `analyze_finances` **não re-rodou**.

**Manchete: o brief desta rodada classificou como "já conhecido e aberto" achados que
tinham conserto mergeado dias antes — e isso faz a lente descartar o sinal.** Entre o
executor do run anterior e o deste entraram **33 commits** em código de produto; o brief
nomeou **7** consertos. Fora da lista, com âncora dentro de achado declarado ABERTO:
`#1800` (guardrail de auto-contradição → `PV9-09`), `#1796` (alvo publicado com observado
legível → `PV9-19`), `#1794`/`#1806`/`#1795` (cambial → `PV9-14`), `#1740`/`#1743` (porta
de saída da pausa → `RR5-05` e a própria condição de resume desta rodada).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| PV10-01 — o check de cobertura cambial converte "não sei o tier" em "passou": `coberto = len(apurados) == len(componentes) **or tier == "indeterminado"`. Escotilha de sinal invertido — quanto menos o sistema sabe, mais fácil o check passa. Neste run `CV18` sai `passed: true` com `não apurados=['carteira_lastro_estrangeiro']; tier=indeterminado` | contrato | Alto | P0 (**P1 recomendado** pela medição) | **re-enunciado** pela [[A42.l16]] — *"sinal invertido"* **não procede**: o caso perigoso (banda afirmada sobre cobertura incompleta) **já reprovava**, com teste desde o #1568; e reprovar o caso que o `or` cobre reprovaria **100% dos runs**, porque é o estado sancionado da v1 ([[ADR-403]]) | **fechado** em [[A42.l16]] · #1827 (`221534e8`, 2026-08-29) | o defeito real é de **outro sinal**: `_tier` define `indeterminado` como *exatamente* "algum componente não apurado" ⇒ os dois disjuntos eram `P ∨ ¬P` e o termo **não discriminava nada**. Medido: em **60 combinações de input do produtor** ele emite **uma única** forma de cobertura e CV18 reprova em **0** — as três pernas do check são constantes sob a v1, e ele publica `passed: true` desde `6c546d7b` porque não pode fazer diferente. ⚠️ **o remédio prescrito aqui não servia:** devolver `None` com `tier == indeterminado` apagaria o check inteiro de todo run. Entregue: `or` → **equivalência** (fecha o eixo inverso — cobertura completa com faixa suprimida), tripwire de produtor, e CV18 **observado disparando no stage** (a evidência que este §r10 declarou fraca) |
| PV10-02 — nenhum predicado de proveniência lê `status`, `needs_review` ou `pipeline_artifacts`; e `stages_terminais` **nomeia terminalidade e computa cardinalidade de nomes distintos que logaram**. O stage que pausou entra na contagem como qualquer outro, e o entregável de proveniência **não menciona a pausa** | saúde-execução | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de `PV9-01` + `PV9-03`, com **mecanismo nomeado e predicado substituto formulado**) | procede-aberto | `execucao_mista=false` é verdadeiro **por construção**: `revisions_in` só enxerga linhas deste run — mede quem **executou**, nunca quem **produziu o artefato lido**. Com read-path workspace-latest sobre **17.382 artefatos de 116 runs**, o predicado ortogonal é sobre o conjunto **efetivamente lido**: `insumo_de_outro_run` e `execucao_mista_de_insumo`, ambos **join, não instrumentação nova** |
| PV10-03 — a suíte de cross-validation tem **4 de 17** checks capazes de pausar o run, e os 4 são **recompute de produtor único** (leem componentes e total do mesmo payload E5); os 13 restantes são advisory, e a linha de resumo publica "17/17 OK" contando advisory como gate | contrato | Alto | P1 | **re-enunciado** — `PV9-04` não procede como escrito ("severidade constante" é **efeito** de 17/17 passar; no código a severidade é ternária condicional em todo check) | procede-aberto · re-triagem de `PV9-04` | é a classe que a [[ADR-418]] §D4 já condenou **no mesmo arquivo**: *"dois campos em que o SEGUNDO deriva do primeiro: não podia falhar"*. `CV5` recebeu o remédio (cruzar três produtores independentes); `CV1`/`CV2`/`CV3`/`CV6` **não receberam, e são justamente os 4 que gateiam**. ⚠️ **evidência fraca declarada:** o gate foi lido no código, **nunca observado disparando** — a prova barata existe e não foi usada (`tests/test_e7_conservation_gate.py`). **Corrigido pela [[A42.l16]] (2026-08-29): a prova existia E estava em uso** — `test_stage_pausa_em_conservacao_violada` observa CV2 reprovando e pausando via `stage.run()` desde o **#941** (`67e4f2b9`, 2026-07-10, A36.l3), no arquivo que esta linha nomeia. O que **não** era observado é o outro lado: a l94 mediu que CV18 emite `severity="error"`, reprova no stage e **não pausa** — um `error` fora de `_CONSERVATION_CHECKS` é exatamente o que a linha "17/17 OK" conflaciona com gate. A substância desta linha (os 4 que gateiam são recompute de produtor único) **não é afetada** |
| PV10-04 — `pipeline_run_costs` tem **zero rows** enquanto o `llm_call_log` do mesmo run declara custo em 6 chamadas; não existe grandeza de custo por run/workspace consultável, logo nenhum cap por workspace é exequível e nenhum alerta pendurado nela pode disparar | contrato | Alto | P1 | procede (novo) | procede-aberto | mesmo modo de falha de `PV9-05` (contador que só pode dar zero). `review_snapshot.py` soma `tool_iterations` a partir de `costs` — sobre zero linhas devolve `None` silenciosamente |
| PV10-05 — o `metadata` do parecer não registra `temperature`, `seed`, nem hash do exec context renderizado; `model_id` é **alias flutuante** sem sufixo de data, e a chave do cache de 7 dias inclui temperature e seed mas o **nome do modelo é o alias** ⇒ refresh do provider é invisível no artefato e **não invalida o cache** | determinismo | Médio | P2 | procede (novo) | procede-aberto | `PARECER_SEED` existe e é passado, mas `litellm.drop_params` o descarta em `anthropic/*` — o seed é **inerte** e o artefato não diz isso a ninguém |
| PV10-06 — `run_meta.md` declara que *"o parecer roda com temperature 0,1"*; o código fixa `PARECER_TEMPERATURE = 0.0` nos dois call-sites. O 0,1 é o default do serviço, que o parecer sobrescreve | contrato | Baixo | P3 | procede (novo) · **verificado** | procede-aberto | importa porque a [[ADR-307]] **proíbe** `use_cache` com temperature > 0: a 0,1 o cache de 7 dias seria inalcançável. A conclusão de "reprodutibilidade não garantida" **continua de pé** por câmbio/DB/alias de modelo — o motivo nomeado é que era falso |
| PV10-07 — `validation_issues` traz **7** itens e o campo legado `validation_errors` traz **6 linhas**; o ausente do canal legado é `investimento_sem_titularidade`, **o de maior materialidade** (49,03% da carteira) | consistência | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de `PV9-28`, com o ofensor nomeado) | procede-aberto | ⚠️ a metade user-facing — **quantos avisos o aprovador vê na tela** — é a célula `PIPELINE × clareza-ux`, declarada **sem cobertura** nesta rodada |
| PV10-08 — `consolidate_baseline` (tier `free`, `is_llm=False`, isto é: determinístico) deriva o ano de referência de `date.today()` por rota alcançável: `extract_baseline` emite `"ano_referencia": max(years) if years else 0`, e **`0` é falsy** ⇒ o `or` cai no relógio de parede | saúde-execução | Médio | P2 | PARCIAL (2 dos 3 call-sites são inertes; **1 é alcançável, por rota que o achado original não nomeou**) | procede-aberto | 4 linhas abaixo do `ano_referencia: 0` há comentário do próprio autor: *"`0.0` aqui era sentinela de ausência lida como medição"* — ele corrigiu `confidence` e deixou `ano_referencia` com o mesmo defeito, **no mesmo dict literal** |
| PV10-09 — `_meta.evidencia_verification` declara **5 `verified`** sobre um artefato que tem **4 âncoras**, e duas entradas apontam `sugestoes_taticas[3]` — índice **fora de faixa** (`len == 3`). A verificação roda **antes** do cap de geração por horizonte, então os `item_index` da trilha não correspondem à lista publicada | contrato | Médio | P2 | procede (novo) · **verificado** | procede-aberto | um operador lendo a trilha aponta para item inexistente — ou, se houve reordenação, para o item errado. 25% do contador de ancoragem não resolve por join |
| PV10-10 — `StageSpec.writes` declara alvo que 2 stages não escrevem (`generate_narratives` escreve sob a chave de **outro** stage; `validate_cross` tem **zero** call-site de `write`) | contrato | Baixo | P3 | **re-enunciado + rebaixado** — `PV9-30` dizia 3 ofensores; são **2, em 2 classes**, e `extract_with_llm` **não é ofensor** (fallback condicional legítimo, com writer real) | procede-aberto | **CAI a perna que dava peso:** mutação com `writes=()` e com `writes=("xpto_inexistente",)` **passa em `validate_full_order` nos dois casos** ⇒ o campo é **ornamental**, não load-bearing. O docstring do próprio `StageSpec` já o chama de ficção. ⚠️ **resíduo de instrumento:** o predicado do X5 vai reprovar `extract_with_llm` em **todo run sem fallback** — classe de falso-positivo conhecida e não codificada |
| PV9-15 (§r9) — tier cambial "trocou de sinal entre runs" | correção | — | — | **REFUTADO** · re-triagem fechada, e **não por esta rodada** | fecha como achado próprio | `carteira_lastro_estrangeiro` é fixado `Cobertura.indeterminado` **incondicionalmente** desde `6c546d7b` (2026-08-21), **anterior aos dois runs** ⇒ o campo não podia flipar, e `_tier_from_pct` é **código morto em produção**. A [[A40.l80]] §C1 **já havia medido e publicado isto em `main`**, e nomeia o produtor real: quem publicou "faixa verde" foi a **prosa do parecer**, não o campo. O item vivo é **RR-class**, não PV — ver [[REPORT-REVIEWS-active]] §r6 |
| PV9-25 (§r9) — máquina de tools sem loop | — | — | — | **duplicata** de `RV4-43`, que carrega diagnóstico mais forte | fecha; não abre registro novo | `rg 'tools='` em `pipeline/llm/**` → **zero**. O modelo nunca recebe tools; o número de round-trips é **estruturalmente 0**. `max_tool_iterations` é parseado e **nunca lido** no caminho do parecer ⇒ não falta canal, falta **sujeito** |
| PV9-06 · PV9-16 · PV9-29 (§r9) | — | — | — | **fechados** — consertos verificados neste run | mantidos fechados | — |
| PV9-09 · PV9-19 · PV9-14 (§r9) | — | — | — | ⚠️ **classificação suspeita** — tiveram conserto mergeado entre os dois runs e o brief os declarou ABERTOS | **re-triagem devida** | `#1800`, `#1796`, `#1794`/`#1806`/`#1795`. Não re-dispostos aqui: decidir exige medir contra o conserto, e o brief contaminado pode ter feito as lentes descartarem o sinal. **Owner: quem triar o r11** |
| Demais linhas do §r9 não re-medidas | — | — | — | **procede-aberto (sem alteração)** | registrado para não decaírem em silêncio | — |

**Positivos verificados.** Run `completed` 18/18 · as 4 superfícies de render geram sem
truncagem e o **PDF de produção sai íntegro** · o determinismo do categorizador fecha ao
centavo sobre o E3 do próprio run (2.289 células) · zero-write do harness provado ·
`main` **não andou** durante a rodada (re-medido no fecho — nenhum achado sai marcado
`re-verificar contra HEAD`) · a supressão do tier cambial **chega íntegra às três
superfícies** ("não apurado" / "Não afirmamos um alvo" / o parecer citando
`tier=indeterminado`).
