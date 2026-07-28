---
type: moc
title: AUDITS-active — Rastreamento de auditorias de repositório
aliases: ["AUDITS", "AUDITS-active", "audit-tracking"]
---

# AUDITS-active — Rastreamento de auditorias

> **Editorial.** Curado manualmente — **não é gerado**. Um gerador baseado em
> frontmatter de ADR só veria itens que viraram ADR; o valor deste índice é
> capturar **todos** os achados — inclusive os que viraram só commit, os
> refutados e os não-acionáveis. Uma seção por auditoria; seções de auditorias
> 100% fechadas viram histórico aqui mesmo (não se arquiva linha a linha).

## Convenção de rastreamento (timeless)

Para que nenhum achado se perca entre auditorias:

1. **Cobertura 100%.** Toda auditoria gera uma seção abaixo cobrindo **todos**
   os achados — inclusive refutados e não-acionáveis. Triagem só é considerada
   completa quando todo item tem disposição registrada.
2. **ADR para o que tem peso de decisão.** Item que procede e altera
   decisão/invariante/dependência entra em ADR de veredito (1 ADR pode cobrir N
   itens correlatos — ex.: [[ADR-298]]). Refutado/não-acionável basta neste
   índice com 1-2 linhas de rationale + link à evidência. **Não** se exige "1 ADR
   por item".
3. **Aberto exige gatilho.** Item `procede-aberto` **deve** ter prioridade
   (P0-P2) + owner + link para linha de BACKLOG ou ADR `Proposto`. `procede-aberto`
   sem gatilho de execução é bug deste índice.
4. **Cadência.** Ao abrir auditoria nova, revise a seção da anterior: todo
   `procede-aberto` que persiste é re-priorizado ou rebaixado a `aceito-wontfix`
   com rationale. Sem zumbis silenciosos.

**Taxonomia de disposição:** `procede-fechado` · `procede-aberto` · `refutado`
· `não-acionável` · `aceito-wontfix`.

---

## r9 — `vault-2026-07-28-r9` (scope `all` · mode `comprehensive` · painel 6 lentes)

> Skill audit-vault ([[ADR-302]]) · amostra **rotativa** `--run 9` (NÃO `--full`).
> **Painel completo de 6 especialistas restaurado** — o limite de gasto mensal da
> org (que bloqueou o r8) foi liberado; um probe (information-architect síncrono)
> validou antes do fan-out. Gates 7/7 verdes (339 ADRs, 1002 notas, 0 wikilink
> broken). Coletor: **33 candidatos** — adr 15 · plan 8 · reference 8 · claude 1 ·
> prompt 1 (`gate_flagged=0`, `changed=0`). Lentes: information-architect (forma:
> 8 planos + agente + 15 ADRs) · data-engineer (schema/pipeline) · senior-cto
> (arquitetura + ARCHITECTURE.md) · financial-planner (rule-alocacao + Decision) ·
> sre-devops (Docker/CI + runbooks) · prompt-engineer (lineage_debug.yaml + LLM
> boundary) · loop principal (PHASES). Bruto: `_scratch/audit-vault-2026-07-28-r9.md`.
>
> **Cadência anti-zumbi:** r8 (2026-07-27) fechou 100% (F01–F05 via #1102, F09
> rebaixado). Zero `procede-aberto` remanescente para re-triar. **Watch item do r8
> materializou:** o cluster ADR-285 (`services/*.py`→subpacotes) rendeu **+1**
> (ADR-259, `vault.py`→`security/vault.py`), corroborado por 3 lentes independentes.

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — ADR-259 :84/:88: `backend/app/services/vault.py` ⟂ real `services/security/vault.py` (`get_vault` em :84) — **cluster ADR-285**, decisão vigente | DOC-DRIFT | procede | procede-fechado | batch #1104 (IA+data-eng+loop; citação dupla) |
| F02 — ADR-331: campo `status: Decidido` (+corpo "Entregue" D1/D4) ⟂ tag `status/proposto` — polui filtro tag-based | DOC-DRIFT | procede | procede-fechado | batch #1104 (IA+data-eng) |
| F03 — ADR-329 `Proposto` mas D1 (`RETRIABLE_SKIP_REASONS`) já em produção | DOC-DRIFT | procede | **não-acionável** | verificado: **`Proposto` está correto** — só D1 shipou; D2 (retry hook)/D3 (OCR)/D4 (`documentos_pendentes`) **sem código**. Flip prematuro |
| F04 — P1_STRUCTURAL `status: paused` + pause_reason "substituído" ⟂ corpo "concluído (2026-04-17)" + fases ✅; sucessor PLATFORM_REVIEW `done`+arquivado | DOC-DRIFT | procede | procede-fechado | **owner autorizou (2026-07-28):** `git mv → docs/archive/P1_STRUCTURAL-2026-07-28.md` + flip `done` + cascade (CLAUDE.md/CANONICAL_ENGINE_P0/PLANS-active + archive/README) |
| F05 — PIPELINE_REVIEW_R2 declara `relates_to [[PLAN-ledger-integrity]]` ⟂ LEDGER_INTEGRITY sem recíproco | DOC-DRIFT | procede | procede-fechado | batch #1104 (recíproco add; coordenam RV2-02/05/17 · ADR-347) |
| F06 — SNAPSHOT_CHANGELOG_V3 `sprint_atual: A11` (fechada 2026-07-08) + W1-W4 shipados; só W5 backlog data-gated | DOC-DRIFT | procede | procede-fechado | batch #1104 (`sprint_atual`→null; status `in_progress` mantido — W5 aberta) |
| F07 — rule-alocacao-alvo `enforcer_modules` cita só o classificador (10 buckets ADR-193); falta o enforcer real do KPI desvio/próximo-aporte (`alocacao_alvo_deviation.py`) — defeito de lineage (ADR-143) | DOC-DRIFT | procede | procede-fechado | batch #1104 (add `alocacao_alvo_deviation.py`; números da regra batem 1:1) |
| F08 — ARCHITECTURE §10:902 `service.py` ⟂ real `litellm_client.py` (rename A6g.2c, commit 8e115ec7) | DOC-DRIFT | procede | procede-fechado | batch #1104 |
| F09 — ARCHITECTURE §1:27 stack só lista Recharts; relatório usa Chart.js 4.5 (`report/charts/`, §10:935 já citava) | DOC-DRIFT | procede | procede-fechado | batch #1104 (+Chart.js na stack) |
| F10 — `config/schemas/goal.alocacao_alvo.v2.schema.json` `description` "candidato v2, não em produção" ⟂ v2 **em produção** (cutover A12, 2026-07-08); a regra está certa, o schema ficou stale | DOC-DRIFT | procede | procede-fechado | task chip → **#1107** (`description` reescrita "v2 EM PRODUÇÃO"; owner rodou em sessão separada) |
| F11 — POLISH (≥10): ADR-130 `size_lines: 175` vs 216 linhas sem justificativa; `relates_to`⊊corpo (130/152/162/184/331); âncora-GH intra-doc morta em nota atômica (152/162); ADR-093 `_scratch/audit_stage_references.py`→`dev/`; ADR-162 `target_value String(64)`→`String(128)`; ADR-024 exceção classificador SDK-direto sem nota; api/v1/README versioning "não implementado" vs path-based live (A6e.5); ADR-152 ref TimelineTab.tsx removida; IA agent shorthand `<UPPER>_PLAN.md` legado | DOC-POLISH | procede | parcial | **ADR-162 (`String(128)`) + api/v1/README (versioning A6e.5) promovidos → fixados #1110**; demais 7 wontfix pré-beta |

> **Cluster ADR-285 (watch item, RESOLVIDO):** r8 fixou 303/208/236; r9 fixou
> **259**; **r9-follow-up fixou 077/134/192/211/231 (#1110) + 132 (#1111,
> display-text de link com href já correto) = +6** — o subconjunto que apresentava
> `services/pipeline_adapter.py` / `db_artifact_store.py` como localização
> **vigente** (agente consultaria o ADR e erraria). **Restam ~9 que
> citam o path antigo como contexto histórico CORRETO** (corrigir = revisionismo,
> por isso NÃO se toca): 075 (estratégia CLI→web de época), 083 (já bannerado r6),
> 092 (rename ADR, superseded por 093), 099/100/168/180/212 (descrevem
> passado/sunset), 166/176 (chave `cenarios_conjuge`, decisão fechada, paths de
> edit-site entrelaçados com `e5_analyze.py`). **Correção do próprio r9:** a nota
> anterior citava 077 como "histórico" — errado; 077 era o ADR canônico do adapter
> (drift real, agora fixo). Watch do cluster **encerrado**.
>
> **Gap de infra (fora de escopo doc):** Dockerfile do serviço Go
> (`services/pipeline-service-go/`) sem entry no `.github/dependabot.yml` (SHA-pin
> OK, falta re-pin automático). **Resolvido:** entry `docker` para
> `/services/pipeline-service-go` adicionado (conforma ADR-249; Dockerfile criado
> pós-config em #792). Fecha o gap; task chip `task_bad477ac` retirado.
>
> **Falsos-positivos evitados (6 lentes):** (a) **ADR-024** (LiteLLM) NÃO foi
> superseded por ADR-259 — é o proxy vigente (senior-cto+prompt-eng); classificador
> ADR-081 usa SDK Anthropic só como fallback P2 (coexistência). (b) **ADR-093**
> cita stage-names legados como contexto histórico do próprio rename F9.4 — não
> drift; F9.4 confirmado 100% concluído. (c) **DATA_LINEAGE** `in_progress`/`A26`
> defensável (pause é nível-sprint; Ondas 6/7 abertas). (d) **PIPELINE_REVIEW_R2 /
> PUBLIC_RELEASE / COMPETITIVE_PIERRE** `Proposto`/owner-gated frescos, não stale.
> (e) `lineage_debug.yaml` determinismo íntegro (model/temp/seed; armadilha ADR-122
> corretamente descartada). (f) ADR-162 PROJECTIONS + ADR-331 citações pré-fix =
> snapshots evolutivos/históricos.
>
> **Verificados limpos:** ADR-021/042/130/152/184/324; runbooks
> schema_validation_strict_flip/f9_3_alembic/dev_environment/docker_images;
> api README (contrato); PHASES (evergreen); GO_SHELL a3cli (`consumed`);
> ADR-249/250/322 (infra 1:1); ADR-259 Decimal/PII (linha-a-linha).
>
> **r9: 0 DOC-BLOCK · 10 DOC-DRIFT (F01–F10) · POLISH (F11).** Batch
> `vault-drift-batch-r9` **executado** (#1104, 7 fixes docs-only, citação dupla) —
> síntese neste PR. F03 não-acionável (Proposto correto); F04 rebaixado
> (cadência §4, owner-gated); F10 via task chip (toca `config/`). Painel de 6
> restaurado após o r8 loop-principal-only.

---

## r8 — `vault-2026-07-27-r8` (scope `all` · mode `comprehensive`)

> Skill audit-vault ([[ADR-302]]) · amostra **rotativa** `--run 8` (NÃO `--full`,
> NÃO `--fix`). Gates 7/7 verdes (zero finding mecânico: 339 ADRs, 1002 notas, 0
> wikilink broken, `_generated/` sincronizado). Coletor: **23 candidatos**
> (`gate_flagged=0`, `changed=0` — delta A36–A39 já em `origin/main`). Universo:
> reference 59 · adr 343 · plan 34 · claude 12 · prompt 5 · root 1. **Sprint
> bucket vazio** (nenhuma sprint `current`; claude/prompt/root fora da classe do
> run-8). **Julgamento loop-principal-only** — painel de especialistas bloqueado
> (limite de gasto mensal da org); owner escolheu prosseguir sem subagentes.
> Verificação empírica doc↔código via Read/Grep. Bruto:
> `_scratch/audit-vault-2026-07-27.md` (efêmero).
>
> **Cadência anti-zumbi:** r7 (2026-07-09) fechou 100%; os `procede-aberto` do r5
> (F04–F11) foram absorvidos por r6 (6 executados, 1 refutado-parcial, 1
> rebaixado). Zero `procede-aberto` remanescente para re-triar. **Meta-achado:**
> o refactor **ADR-285** (`backend/app/services/*.py` → `services/pipeline/` +
> `services/storage/`) deixou paths stale **apresentados como vigentes** em ADRs
> Decidido que r7 não re-julgou — r7 Fase 3 focou só o delta + Proposto/Roadmap,
> e o r6 (2026-07-03) julgou esses Decidido **antes** do 285 aterrissar. A
> amostra rotativa r8 é exatamente o mecanismo que pega esse tipo de resíduo.

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — ADR-303 (2 paths, contrato vigente): :71 `backend.app.services.db_artifact_store.DBArtifactStore` ⟂ real `services/storage/db_artifact_store.py`; :119 `services/run_context_factory.py` ⟂ real `services/pipeline/run_context_factory.py` (fallout ADR-285; 303 fora do delta do r7) | DOC-DRIFT | procede | procede-fechado | batch `vault-drift-batch-r8` #1102 (owner autorizou execução na sessão; citação dupla) |
| F02 — ADR-208 :56 (nota de correção **do próprio r6**): `services/pipeline_service.py` ⟂ real `services/pipeline/pipeline_service.py` (`resolve_llm_tier_async`/`_classify_llm_config` :27,:74) | DOC-DRIFT | procede | procede-fechado | idem batch #1102 |
| F03 — ADR-236 (2 refs vigentes): :56/:190 `services/pipeline_adapter.py` ⟂ real `services/pipeline/pipeline_adapter.py` (`build_goals_payload_sync` :469); :120 "Já calculado em `e5n_narrativas.py:374`" ⟂ arquivo inexistente (F9.4 → `scripts/generate_narratives.py:~472`) | DOC-DRIFT | procede | procede-fechado | idem batch #1102 |
| F04 — ADR-035 `window.print()` + "upgrade path → Playwright se necessário": upgrade **foi tomado** (PDF prod = Playwright `pdf_renderer.py`, [[ADR-129]]); `superseded_by: []` sem nota | DOC-DRIFT | procede | procede-fechado | idem batch #1102 (nota de supersedure + relates_to) |
| F05 — LAUNCH_TRUST/_README `last_review: 2026-05-30` (~2mo stale) + `sprint_atual: A22` mas A22 F3 fechou (#872); residuais em §F2 owner-gated | DOC-DRIFT | procede | procede-fechado | idem batch #1102 (`last_review`→07-08 + `sprint_atual`→null; corpo já datava A22 fechada) |
| F06 — ADR-236 372 linhas sem `size_lines` no frontmatter (>150 sem justificativa de split) | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta (gate não enforça; precedente r3/r6) |
| F07 — ADR-178 `Decidido` com checkboxes de impl `- [ ]` desmarcadas embora `models/risk.py` + `application/risks/` tenham shipado | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |
| F08 — ADR-342 sem `relates_to` no frontmatter apesar do corpo cross-linkar ADR-344/272/090; ADR-344 declara `relates_to: [[ADR-342]]` (unidirecional no frontmatter) | DOC-POLISH | procede | aceito-wontfix | corpo cross-linka nos 2 sentidos; gates verdes; batch pré-beta |
| F09 — S4_REAL_ESTATE_ENRICHMENT `status: done` não-arquivado (MESMO follow-up r3-F01; arquivamento deferido por 5+ links inbound — cascade) | DOC-DRIFT | procede | aceito-wontfix | rebaixado (cadência §4): recorrente desde r3, cosmético, owner-gated. **Gatilho de reabertura:** owner decide arquivar OU os links inbound caírem, então `git mv → docs/archive/` + reescrita de links |

> **Tamanho do cluster ADR-285/F9.4 (grep amplo, NÃO julgado):** `pipeline_adapter`
> em 211/077/236/075/134/192; `db_artifact_store` em 303/132/083/231;
> `pipeline_service` em 208; `run_context_factory` em 303; `e5n_narrativas` em
> 212/092/099/100/166/236/176/168/180. **Muitos são contexto histórico correto**
> (092 É a ADR do rename F9.4; 075/077 são era CLI-web; 212 descreve o que
> sunset). O batch r8 exige **julgamento vigente-vs-histórico por ADR — nunca sed
> cego**; só os 3 lidos (208/236/303) confirmam apresentação-como-vigente.
>
> **Falsos-positivos evitados (loop principal):** (a) **ADR-353** `Proposto` com
> backend shipado mesmo-dia (#1098) NÃO é drift — governado pelo plano ativo
> [[PLAN-pipeline-review-r2]] (ondas B/C deferem flip); símbolos corroborados
> (`NAO_IDENTIFICADO_PARCIAL_PCT=10.0`/`INSUFICIENTE_PCT=30.0`; `diagnostico_confianca`
> no schema E5 + adapter). (b) **ADR-342/344** LIMPO — todos os símbolos batem
> (`_CONSERVATION_MATERIALITY_PISO_CENTS=10000`; 5 `ReviewReasonCode`;
> `raw_rows_detected` no schema; traço `fatura_checksum` read-only). (c)
> **ADR-314/174** `Proposto` owner-gated legítimo (checkboxes vazios G0 / §F2
> residual), não zumbi. (d) **rule-imoveis-no-if** LIMPO (enforcers + PUT endpoint
> `properties.py:151` verificados). (e) 7 ref docs **sem** fallout ADR-285 (r7 já
> limpou); portas SETUP consistentes (native 800x / Docker 801x).
>
> **Verificados limpos:** ADR-080/304; PIPELINE_ARTIFACTS/REPORT_PUBLICATION/SETUP/
> SMOKE_TEST/disaster_recovery/incidents; GO_SHELL (in_progress + F2 ready).
>
> **r8: 0 DOC-BLOCK · 5 DOC-DRIFT (F01–F05) · 3 DOC-POLISH (F06–F08) · 1
> recorrente (F09).** Vault saudável — nenhum drift indutor-de-erro-imediato; o
> sinal é o resíduo ADR-285 em ADRs Decidido não-delta. Batch
> `vault-drift-batch-r8` **executado na sessão** (#1102, owner autorizou; F01–F05
> fechados com citação dupla) — síntese em #1101. F06–F08 (POLISH) wontfix
> pré-beta; **F09** rebaixado a `aceito-wontfix` (cadência §4 — S4 archival
> owner-gated). **Zero `procede-aberto` remanescente.**

---

## r7 — `vault-2026-07-09-r7` (sweep one-shot `--scope all --full --fix`)

> Skill audit-vault ([[ADR-302]]) · **sweep 100% one-shot** em 3 fases
> (contrato do one-shot na SKILL). Gates 7/7 verdes (zero finding mecânico:
> 314 ADRs, 930 notas, 0 wikilink broken, `_generated/` sincronizado).
> Coletor rotativo `--full` (stride 1): universo **423 arquivos** — reference
> 58 · adr 314 · plan 33 · claude 12 · prompt 5 · root 1. **Sprint bucket
> vazio** — nenhuma sprint `sprint_status: current` (A26/A34 `paused`, A27
> `candidate`). **Cadência anti-zumbi:** r6 (2026-07-03) fechou 100% dos
> findings; sem `procede-aberto` remanescente para re-triar. **Contexto do
> delta:** r6 foi há 6 dias, mas shipou uma semana de dev (A29-A35, Go
> F1+F2, refactor ADR-285 de `backend/app/services/` em subpacotes, scrubs
> PII A34) — superfície nova legítima, não re-run vazio.

### Fase 1 — reference (58/58 julgados)

> Julgamento: data-engineer + sre-devops + financial-planner + senior-cto em
> paralelo + loop principal (6 docs cross-cutting). Verify: 5/5 DOC-BLOCK
> confirmados pelo loop principal com citação dupla, 0 rebaixados.
> **Cluster dominante:** paths stale pós-refactor **ADR-285** (`services/`
> → subpacotes `storage/`/`documents/`/`security/`/`pipeline/`), confirmado
> por 3 especialistas independentes. Bruto em `_scratch/audit-vault-2026-07-09.md`.

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — `suggestion_backfill.md:29`: `from ...database import AsyncSessionLocal` (símbolo inexistente; base usa `async_session as AsyncSessionLocal`) → snippet copy-paste dá ImportError | DOC-BLOCK | procede | procede-fechado | #926 (`async_session as`) |
| F02 — `RUNBOOK.md:105` §5.2: `from backend.app.services import category_cache` (services/__init__ vazio pós-ADR-285) → invalidação de cache do downgrade nunca roda (bug de 15min stale que a seção previne) | DOC-BLOCK | procede | procede-fechado | #926 (`.storage.category_cache`) |
| F03 — `tenancy.md:13,99`: prefixo `/api/workspaces/...` (TL;DR + exemplo DO); routers reais usam relativo `/workspaces/...` com `/api/v1` no mount → cópia literal produz `/api/v1/api/...` quebrado | DOC-BLOCK | procede | procede-fechado | #926 (`documents.py:76` + `config.py:39`) |
| F04 — `runbooks/dev_environment.md:33-35,51,121`: portas do stack Docker 8000/3000/5432; compose publica 8010/3010/5433 → operador curla porta errada, smoke falha com stack saudável | DOC-BLOCK | procede | procede-fechado | #926 (`docker-compose.dev.yml` + `Makefile:73-75`) |
| F05 — `config/methodology.md:188`: reserva "média trimestral"; enforcer usa janela 12m (ADR-306 supersede "trimestral, nunca implementada", já vigente em FORMULAS.md + `fluxo_caixa_enricher.py:80`) → reserva-alvo/cobertura erradas | DOC-BLOCK | procede | procede-fechado | #926 (align 12m; +2 ponteiros `definitions.md`→config DB). Config-adjacente (docs-only; não runtime-read) |
| F06-F15 — DRIFT (cluster ADR-285 + outros): PIPELINE_ARTIFACTS (SCHEMA_BY_STAGE→`storage/`; `_create_report_from_output`→`app/tasks/`); schema_validation_strict_flip + pipeline_rollback + GO_PORT_DEPS×2 (db_artifact_store→`storage/`); CANONICAL_ENGINE×2 (content_classifier + document_classification→`documents/`); disaster_recovery (vault→`security/`); ARCHITECTURE (events→`pipeline/`; §6 nota 112→~81+6 subpacotes; §17.2 nota datada Go F1/ADR-323); FORMULAS (`definitions.md`→docstring PatrimonioCalculator); rule-alocacao (status v2 candidato→produção, ADR-141); security_gates (`dev/gen-secrets.sh`→`scripts/`) | DOC-DRIFT | procede | procede-fechado | batch `vault-drift-batch-r7-f1` #924 (`--fix`, citação dupla) |
| F16 — POLISH: `TESTING.md:573` checkbox órfão referenciando `_STAGE_TO_DIR` (deletado ADR-213); `PERFORMANCE_BASELINE.md:387` path importtime stale (snapshot datado pré-ADR-285) | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |

> **Falsos-positivos evitados (loop principal):** COPY_GUIDELINES cita
> `config/methodology.md` + `config/report_spec.md` — **ambos existem**
> (`config/methodology.md` ≠ `docs/methodology/` proibido). REPORT_PUBLICATION
> paths OK — `report_publication.py` **não** moveu no ADR-285;
> `is_month_closed_sync` em :75 ✓. security_gates.md:18 lista
> `pipeline-service/requirements*.txt` inexistente MAS espelha fielmente o
> workflow — possível bug do `security.yml`, não drift de doc (fora de escopo).
>
> **Verificações que passaram:** 12 rule files (`financial-planner` número-a-número
> contra enforcers: concentração 40%, cascata PJ T3/T4/T5, TRS 5%, seguros,
> score weights 1:1 com scoring.json); README/SLO + 9 runbooks (`sre-devops`);
> PHASES/PRODUCT/api-README (`senior-cto`, evergreen por design); 6 docs
> cross-cutting + banners r6 F03/F06/F07 intactos (loop principal).
>
> Fase 1: síntese #926 (5 BLOCK), batch #924 (DRIFT). Taxa: 5 BLOCK + ~12
> DRIFT + 2 POLISH em 58 arquivos (~33% com finding; concentrado no
> fallout de paths do ADR-285).

### Fase 2 — plan + claude/agents + prompt + root (51/51 julgados; sprint bucket vazio)

> Julgamento: product-manager (33 plans) + information-architect (plans forma +
> 11 agentes + CLAUDE.md forma) + prompt-engineer (5 YAMLs) + loop principal
> (CLAUDE.md doc↔código + README). Verify: 3/3 DOC-BLOCK com citação dupla.
> **Meta-achado:** o **F32 do r6 foi aplicado parcialmente** — o batch r6
> (`b3f9e1e4`) tocou 1 de ~6 instâncias em `senior-cto.md` e nunca cobriu
> `product-manager.md`, apesar do commit-msg alegar cobertura total. Fechado
> agora (lição SEC-03: verificar que o fix aterrissou). Fase única (BLOCK+DRIFT
> no mesmo PR) porque flips de status re-tocam `_generated` — 2 PRs garantiriam
> conflito.

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F17 — `senior-cto.md:81`: recipe "`grep` em `docs/DECISIONS.md`" (shim de 221 linhas sem corpos de ADR) contradiz a linha 25 já migrada (r6) → agente grepa shim e decide errado | DOC-BLOCK | procede | procede-fechado | #927 (`rg docs/adr/` + 9 links bare→notas reais + BACKLOG/DECISIONS-live→SPRINT_CURRENT/ADR_INDEX) |
| F18 — `INTERNAL_ADMIN/_README.md:26,163,206`: 3 âncoras mortas `BACKLOG.md#f7f-*` (shim não tem seção F7F) → pickup cai no topo do shim sem tasks | DOC-BLOCK | procede | procede-fechado | #927 (tasks in-plan + SPRINT_CURRENT) |
| F19 — `RESIDENCIA_E_USO/_README.md`: `status: draft` + P1-P6 ⏳ contradiz §63-66 do próprio doc ("todos os blocos ✅ shipped 2026-05-15") + ADR-215 Decidido | DOC-BLOCK | procede | procede-fechado | #927 (`done` + P1-P6 ✅; arquivamento owner-gated → F22) |
| F20-F33 — DRIFT (14): F32 residual (`senior-cto.md` 9 bare `#adr-NNN` + BACKLOG/DECISIONS-live; `product-manager.md` CHANGELOG-live; REPORT_PREMIUM 3 âncoras BACKLOG mortas) + status/tag de plano (LLM_PROMPTS_HARDENING draft→done; TRIBUTARIO_PJ tag status/draft→done; DATA_LINEAGE A26 `current`→`paused` + sprints_envolvidas +A27 + "Sprint corrente A25"→A26/A27; SNAPSHOT_CHANGELOG_V3 W1-only→W1+W2; GO_SHELL nota datada Go F1/F2; COMPETITIVE_PIERRE 3.E prep decidido ADR-262/263/264) | DOC-DRIFT | procede | procede-fechado | batch `vault-drift-batch-r7-f2` #927 (`--fix`, citação dupla) |
| F34 — POLISH: anchor-to-shim que resolve (wikilink preferido) em REPORT_PREMIUM/_README, P1_STRUCTURAL, CLAUDE.md; S4 intro ADR-216 Proposto→Decidido; SUGGESTION_LIFECYCLE in_progress→done candidato; `sprint_atual` de vários planos aponta sprint já `done` | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |
| F35 — arquivamento de `PLANNER_REVIEW` + `RESIDENCIA_E_USO` (concluídos) — `git mv → docs/archive/` com cascade de wikilinks vivos (LAUNCH_TRUST §F3) | DOC-DRIFT | procede | procede-fechado | **owner escolheu Opção B (2026-07-09):** `git mv` para `docs/archive/<X>-2026-07-09.md` + reescrita de 6 wikilinks + 5 markdown links + linha CLAUDE.md + entrada em `archive/README.md`. RESIDENCIA sem inbound links (arquiva limpo). |

> **Falso-positivo evitado:** `INTERNAL_ADMIN:141` linka `_generated/ROADMAP.md`
> — **existe** (auto-gerado; allowlisted em `check_doc_markdown_links.py:42`);
> a "ROADMAP.md deletada" do CLAUDE.md é a antiga `docs/ROADMAP.md`, não a gerada.
>
> **Verificações que passaram:** 5 prompts (`prompt-engineer`, 1:1 vs
> schema/enum/consumidor; ADR-122 trap respeitada); CLAUDE.md (codemod ADR-285
> #855 manteve os paths de `services/`; 27 schemas; F34/F35 do r6 seguros);
> README.md (bandas de porta native 800x / Docker 801x consistentes, 11 parsers);
> F32 nos outros 4 agentes (data-engineer/sre-devops/build-vs-buy/_TEMPLATE OK).
>
> Fase 2: PR único #927 (3 BLOCK + 14 DRIFT + AUDITS). Taxa: 3 BLOCK + 14 DRIFT
> + POLISH em 51 arquivos (~25% com finding; concentrado em status-drift de plano
> + F32 residual). Sprint bucket vazio (nenhuma sprint `current`).

### Fase 3 — adr (314; foco de risco: 27 Proposto/Roadmap + ~15 Decidido do delta)

> Julgamento: senior-cto (Proposto/status stale) + information-architect
> (supersedure/emenda forma) + data-engineer (data/pipeline/schema) em paralelo.
> Verify: 1/1 DOC-BLOCK com citação dupla. **Cobertura:** os 288 Decidido foram
> julgados 100% pelo r6 (2026-07-03, 6 dias antes); r7 focou o **risco** —
> Proposto/Roadmap 100% (decisão-shipada-sem-flip) + os ~15 Decidido do delta
> (emendados/refatorados: 285/310/246/212/141/150/228/259/260/261/308/312/323).
> Padrão dominante: fallout residual do ADR-285/F9.4 (paths) + Proposto shipado
> sem flip (owner-gated).

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F36 — `ADR-092` (Proposto): tabela de rename propõe nomes agente-substantivo (`transaction_reconciler.py`…) que nunca existiram; F9.4 (ADR-093 Decidido) renomeou com convenção verbo-objeto (`reconcile_transactions.py`…). Agente que use a tabela erra nos 9 paths | DOC-BLOCK | procede | procede-fechado | #929 (supersedure bidirecional 092↔093 + banner histórico; flip 092→Decidido owner-gated) |
| F37-F42 — DRIFT (6): ADR-212 (`db_artifact_store`→`storage/`); ADR-246 ×3 (`e15_consolidate`→`consolidate_baseline`, `e4_categorize`→`categorize_transactions`); ADR-260 (nota r7: camada 3 OTLP shipou A33.l7 #834); ADR-323 (nota r7: FallbackPipelineClient dark-launch na F2); ADR-308 (supersedure parcial de ADR-158 só-no-corpo → frontmatter bidirecional); ADR-261:85 (runbook proposto escrevia em `_archive/` proibido → `_scratch/`) | DOC-DRIFT | procede | procede-fechado | batch `vault-drift-batch-r7-f3` #928 (`--fix`, citação dupla) |
| F43 — POLISH: ADR-259:40 (`relates_to` sem ADR-260); ADR-320:8 (`relates_to` sem ADR-322, 322→320 unidirecional); ADR-261:46 (citação de comentário stale, código reescrito ~72 linhas) | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |
| F44 — flip `Proposto→Decidido` de ADR-092/260/323 (decisões-núcleo shipadas, notas de estado adicionadas) | DOC-DRIFT | procede | procede-fechado | **owner seguiu a recomendação (2026-07-09):** manter `Proposto` + nota de estado — 323 é dark-launch (env OFF), 260 tem camada 1 pendente, 092 já coberto por supersedure. Reavaliar flip quando cada uma ficar 100% ativa. |

> **Não-findings (verificados):** 095/096 (supersedure/nota OK), 141 (schema v2
> existe), 221/264 (Proposto fiel — serviços/tabelas não criados), 285 (6 subpacotes
> conferem), 310/312 (implementados, schema bate), 218 (comentário futuro, não impl),
> 140/159/160 (Roadmap legítimo, gatilho externo), 005/058/174/228/250/251
> (owner-gated: go-live/GHCR/R2 — não-acionável), 6 ADRs emendados com sinal completo.
> **Falso-positivo evitado:** `size_lines` ausente em 14/17 é campo opcional
> pré-existente (não drift do delta).
>
> Fase 3: síntese #929 (1 BLOCK), batch #928 (6 DRIFT). Taxa: 1 BLOCK + 6 DRIFT
> + 3 POLISH + 1 owner-gated no foco de risco (~40 ADRs julgados a fundo; range
> Decidido estável carregado do r6).

> **r7 fechado.** Sweep one-shot `--scope all --full --fix` em 3 fases, 5 PRs
> (#924/#926 F1 · #927 F2 — PR único · #928/#929 F3). Cobertura: reference 58/58 + plan
> 33 + claude 12 + prompt 5 + root 1 (100%) + adr foco-de-risco (Proposto/Roadmap
> 100% + delta; Decidido estável carregado do r6). **Total: 9 DOC-BLOCK
> mergeados** (5 F1 + 3 F2 + 1 F3), 0 rebaixados no verify · **~32 DOC-DRIFT**
> corrigidos com citação dupla · POLISH wontfix · **2 owner-gated** (arquivamento
> de planos concluídos F35; flip Proposto→Decidido F44). Critério de aceite:
> ≥1 BLOCK em `main` ✓ (9) · falso-positivo BLOCK 0/9 ✓ · zero finding recriando
> gate ✓ · faseado <30min/pacote ✓. **Lição recorrente:** o F32 do r6 (fix
> parcial alegado como total) e o SEC-03 do r2 confirmam — verificar sempre que
> o fix aterrissou no artefato, não só que foi anunciado.

---

## r6 — `vault-2026-07-03-r6` (sweep one-shot `--scope all --full --fix`)

> Skill audit-vault ([[ADR-302]]) · **sweep 100% one-shot** em 3 fases
> (runbook `vault_full_audit`, contrato do one-shot na SKILL). Gates 6/6
> verdes (zero finding mecânico). Coletor rotativo com `--full` (stride 1):
> universo 410 arquivos — reference 55 · plan 29 · sprint 12 · claude 12 ·
> prompt 4 · root 1 · adr 297. Com `--fix`, os batches de DRIFT são
> executados no próprio run (PR próprio por fase). **Cadência anti-zumbi:**
> os `procede-aberto` do r5 (F04-F09 ADRs · F10-F11 plans, batch
> `vault-drift-batch-r5` nunca executado) são absorvidos pelos batches das
> Fases 3 e 2 deste run, respectivamente.

### Fase 1 — reference (55/55 julgados)

> Julgamento: financial-planner + sre-devops + 2× loop principal em
> paralelo. Verify: 10/10 DOC-BLOCK confirmados com citação dupla, 0
> rebaixados. Bruto em `_scratch/audit-vault-2026-07-03-r6.md` (efêmero).
> Fixes r4/r5 verificados: sem regressão (exceto entradas do §2 do
> STATELESS_AUDIT que moveram pós-r4 — F22).

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — rule-concentracao-imobiliaria: alerta doc >50% via `patrimonio_calculator`; real >40% (`RealEstateConfig` + aggregator, `concentracao_alta`); constante 50 é só narrativa E5.N | DOC-BLOCK | procede | procede-fechado | conceito/enforcers reescritos (2 thresholds, papéis distintos) neste PR |
| F02 — FAQ_cascata_fiscal_pj T4: "> R$ 60k/ano" vs `T4_RECEITA_ALUGUEL_MIN_ANUAL=90000` | DOC-BLOCK | procede | procede-fechado | ≥ R$ 90k/ano neste PR |
| F03 — SMOKE_TEST_HUMAN §4.7 audita coexistência disco↔DB removida (ADR-212): script, flag e campo `/health` deletados | DOC-BLOCK | procede | procede-fechado | banner HISTÓRICO no PR #766; **sub-item de arquivamento fechado 2026-07-03** (owner decidiu): expurgo A6b → `docs/archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md`; runbook segue vivo (§4.9 gate A26.l5 + protocolo do gate humano ADR-150) |
| F04 — PHASES F7 "☐ Planejada" vs 5/6 lanes `shipped` em `docs/sprint/F7/lanes/` | DOC-BLOCK | procede | procede-fechado | "🔶 Em curso (5/6; falta F7-c)" neste PR |
| F05 — COPY_GUIDELINES §2/§11 mandam editar `docs/methodology/definitions.md` (inexistente + path proibido ADR-143) | DOC-BLOCK | procede | procede-fechado | aponta config DB (ADR-137) + rules-as-code neste PR |
| F06 — DOGFOOD_LEARNING_LOOP_HANDOFF conduz gate fechado (PASS 2026-07-02) como pendente; "sem UI" contradiz P4 shipped (#203) | DOC-BLOCK | procede | procede-fechado | banner HISTÓRICO neste PR |
| F07 — DOGFOOD_PM_CHECKLIST: roteiro do gate como a-executar; pós-gate prescrito já superado | DOC-BLOCK | procede | procede-fechado | banner HISTÓRICO neste PR |
| F08 — PIPELINE_ARTIFACTS: `SCHEMA_BY_STAGE` citado em `pipeline/schema_validation.py` (inexistente; real: `db_artifact_store.py:82`) | DOC-BLOCK | procede | procede-fechado | path correto + nota de boundary neste PR |
| F09 — PIPELINE_ARTIFACTS tabela: E1.5→`baseline_patrimonial.schema`; real `e15_baseline_extract` (A20.l11), só E1.5c usa baseline_patrimonial | DOC-BLOCK | procede | procede-fechado | linha desdobrada neste PR |
| F10 — TESTING + ARCHITECTURE: `python -m pipeline.run_dev` (deletado, ADR-212 PR3a) como comando canônico | DOC-BLOCK | procede | procede-fechado | `python -m pipeline.orchestrator run-stage` (A3.cli · ADR-150) neste PR |
| F11-F25 — DRIFT (15): paths populator vs adapter (itcmd/us-person); FAQ T5 R$3M vs 2,88M; PERFORMANCE_BASELINE §6 bug já corrigido; pipeline_rollback freeze SQL incompatível com schema + `/health/celery`; docker_images SHA-pin "futuro"; security_gates paths pip-audit; PHASES âncoras shim; IconBadge "planejado"; REPORT_PUBLICATION learning loop "(futuro)"; CANONICAL_ENGINE ids/omissões de stages; GO_PORT_DEPS paths + A3.cli contradição interna; STATELESS §1/§2/§3 refs movidas; TESTING dir/guardrail deletados; ARCHITECTURE §11/§6 pré-ADR-212/A7.5; tenancy prefixo duplo | DOC-DRIFT | procede | procede-fechado | batch `vault-drift-batch-r6-f1` executado neste run (`--fix`), PR docs-only próprio |
| F26 — POLISH agrupado (9 itens: line-drifts, contagens, links a stub, data de revisão) | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |
| F27 — (meta/skill) `collect_candidates.py --help` crasha: `%` sem escape no help de `--full` | DOC-DRIFT | procede | procede-fechado | fix 1-linha (lateral) no PR do batch F1 (#767) |

> Fase 1 fechada: síntese em PR #766, batch DRIFT em PR #767 — ambos
> mergeados 2026-07-03. Taxa da fase: 10 BLOCK + 16 DRIFT + 9 POLISH em 55
> arquivos (~45% com finding; concentrado em docs pré-ADR-212/A7).

### Fase 2 — plan + sprint + claude + prompt + root (58/58 julgados)

> Julgamento: product-manager (20 plans + A28) + information-architect
> (sub-docs + 12 agentes) + prompt-engineer (4 YAMLs) + loop principal
> (CLAUDE.md + README) em paralelo. Verify: 2/2 DOC-BLOCK confirmados com
> citação dupla. README 100% limpo; 3/4 prompts limpos (gates de paridade
> rodados). Zumbis r5 re-verificados: F10 → resíduo na linha 382 (F30);
> F11 → parcialmente **refutado** (lane `report-mobile-impl` está ancorada
> no plano-pai §17.10 como spec-only; sobra forma → F33).

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F28 — TRIBUTARIO_PJ `draft`/"P1-P6 não iniciados"/"ADR-236 pendente write" vs ADR-236 `Decidido` (2026-05-21) + P1-P6 shipped (#390-#398, código em `tributario/` + card + telemetria + FAQ) | DOC-BLOCK | procede | procede-fechado | frontmatter `done` + §Status executivo reescrito com nota datada, neste PR |
| F29 — section_summaries.yaml header: "bump força invalidação natural" do cache; `_cache_key` não inclui `version` → bump serve texto stale até 24h | DOC-BLOCK | procede | procede-fechado | comentário corrigido (honesto: TTL/snapshot só) neste PR; follow-up de código (version na key) virou task chip |
| F30 — CAT_LEARNING_LOOP §"Status atual (2026-05-11)" :382 ainda diz lane `in_progress`/gate pendente (contradiz §executivo PASS 2026-07-02) — resíduo do zumbi r5-F10 | DOC-DRIFT | procede | procede-fechado | batch `vault-drift-batch-r6-f2` (`--fix`, PR próprio) |
| F31 — PLATFORM_REVIEW: corpos W1-T03/W1-T06 `status: ready` vs Index/NEXT UP `done` (PR #94) | DOC-DRIFT | procede | procede-fechado | idem batch F2 |
| F32 — 4 agentes (senior-cto, data-engineer, sre-devops, build-vs-buy; product-designer menor) tratam DECISIONS/BACKLOG como fontes vivas: receita `grep ^## ADR-` retorna vazio, teto "ADR-139" (~164 atrás), ~35 âncoras bare `#adr-NNN` que não resolvem no shim | DOC-DRIFT | procede | procede-fechado | idem batch F2 (padrão do _TEMPLATE, já conforme desde r4) |
| F33 — REPORT_PREMIUM sub-docs (MOBILE_SPEC, A11Y_CHECKLIST, GAPS) linkam ADR via âncora GH ao shim em vez de wikilink (resíduo de forma do r5-F11) | DOC-DRIFT | procede | procede-fechado | idem batch F2 |
| F34 — CLAUDE.md "26 schemas" (real: 27; enumeração omite `e15_baseline_extract`, A20.l11) | DOC-DRIFT | procede | procede-fechado | idem batch F2 |
| F35 — CLAUDE.md :573 "DB `pipeline_artifacts.stage` continua em formato legado até F9.3" — falso: E3/E5/E1.x/extract_* já gravam descritivo (só E2 legado); docstring `artifact_reader.py:30` com o mesmo drift (lateral) | DOC-DRIFT | procede | procede-fechado | idem batch F2 |
| F36 — A28 `_README` tabela: l5-l8 `planned` vs frontmatter `open` (recorrência da classe r5-F01) | DOC-DRIFT | procede | procede-fechado | idem batch F2 |
| F37 — POLISH agrupado (GAPS :272 instrução pré-ADR-182 sob banner histórico; âncora `batch2.13` em A11Y/VISUAL_SNAPSHOTS; MOBILE_SPEC sem frontmatter — padrão da pasta; checkboxes de tasks done no PLATFORM_REVIEW; dupla numeração v2.9/1.1 no section_summaries; CLAUDE.md literais e5n/e4/108KB; CAT nota de retenção in-place) | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |

> Fase 2 fechada: síntese em PR #768, batch em PR #769 — ambos mergeados
> 2026-07-03. Taxa da fase: 2 BLOCK + 7 DRIFT + ~10 POLISH em 58 arquivos
> (README e 3/4 prompts 100% limpos).

### Fase 3 — adr (297/297 julgados, 5 sub-lotes)

> Sub-lotes: A = 18 Proposto + 3 Roadmap (senior-cto) · B-E = 276 Decidido
> em 4 faixas (loop principal). Verify: 3/3 DOC-BLOCK confirmados com
> citação dupla. Gate informativo do runbook (taxa fases 1-2): ~45% dos
> arquivos de reference com finding; ~19% na Fase 2 — owner já havia
> decidido pagar o sweep inteiro (one-shot). Taxa da Fase 3: 3 BLOCK +
> ~20 DRIFT + ~25 POLISH em 297 (≈16% com finding; range recente muito
> mais limpo que o F2-F7). Padrões dominantes: (a) ciclo ADR-212/303
> atualizou algumas ADRs da era A6 mas não todas; (b) cluster do parecer
> (Ato 1, escrito pré-implementação) divergiu da implementação sem emendas;
> (c) emenda-datada-no-corpo-sem-sinal-no-frontmatter é o gap sistêmico do
> range recente (7 ocorrências).

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F38 — ADR-083 (canônica do `ArtifactStore`) descreve `DiskArtifactStore`/default disco/flag como vigentes — o oposto do invariante DB-only ([[ADR-212]]); supersedure parcial só documentada no lado do 212 | DOC-BLOCK | procede | procede-fechado | banner de supersedure parcial neste PR (convenção do corpo, [[ADR-212]] §Supersedure parcial) |
| F39 — ADR-120 ensina "fallback limpo para `DiskArtifactStore`" nos readers; `artifact_reader.py` diz "fallback disco morreu" (ADR-212 PR3b); 106/118 ganharam `superseded_by`, 120 ficou órfã | DOC-BLOCK | procede | procede-fechado | banner neste PR |
| F40 — ADR-207 D2/D4/D6: trio `methodology_mapping.{yaml,py,ts}` + codegen nunca implementados; `tema_canonico` é emitido pelo LLM e persistido (não derivado em runtime); schema JSON repete o YAML fantasma | DOC-BLOCK | procede | procede-fechado | emenda datada na ADR + descriptions do schema corrigidas neste PR |
| F41 — ADR-259/ADR-260 `Proposto` com decisões-núcleo implementadas de facto (PR #720, A18/A20) sem nota de estado (259: rules 1-3 shipped, rule 4 pendente; 260: camada SQL shipped, camadas 1/3 pendentes) | DOC-DRIFT | procede | procede-fechado (nota de estado) | batch `vault-drift-batch-r6-f3`; **DECISÃO-OWNER aberta:** flip para `Decidido` parcial vs manter `Proposto` com nota |
| F42 — ADR-046 revisão in-place sem data + "PWA adiada para F8" órfã (zumbi r5-F05) | DOC-DRIFT | procede | procede-fechado | batch F3 |
| F43 — ADR-068 enumera stages mortos (`E0-audit`, `E7-review/apply`) como contrato vigente, `relates_to: []` (zumbi r5-F06); ADR-028 é a irmã com o mesmo defeito | DOC-DRIFT | procede | procede-fechado | batch F3 (banner + relates_to em 068 e 028) |
| F44-F48 — Decidido F2-F7 com claim vigente falso: 051 Geist↔076 sem supersedure bidirecional; 055 "CI gate ≥95%" inexistente; 059 "gate 0 CVEs" é check informativo (image scan diferido W4-T02); 061 tabela `UsageMetric` nunca criada; 094 single-active revertida de facto (1 Report/run, REL-03) | DOC-DRIFT | procede | procede-fechado | batch F3 (notas de estado/banners/frontmatter) |
| F49-F52 — ciclo ADR-212/303 incompleto: 105 sem supersedure bidirecional c/ 127/128; 112 boundary disco invertido por [[ADR-303]] sem banner; 142 autocontraditória pós-emendas (parágrafos pré-ADR-222 não podados; relates_to sem 222/235) | DOC-DRIFT | procede | procede-fechado | batch F3 |
| F53-F59 — cluster parecer + extensões sem fan-out: 189 hub de 6 extensões sem backlink (copy §4 não é mais canônica pós-197); 201 gates de persona (schema/hook/auto-hash) não implementados + semver; 202 validadores raise/reask viraram coerce (ADR-292/294) sem sinal; 203 whitelist vive no manifest em runtime (script de pre-commit fantasma); 208 `workspace.tier` não existe — tier é derivado BYOK (zumbi r5-F04); 216 D8 cita enum de classification que nunca existiu; 220 regra IF é soft check no Pydantic (script fantasma; manifest é ADR-200) | DOC-DRIFT | procede | procede-fechado | batch F3 |
| F60-F63 — range recente: 255 identidade v1 superseded por natural_key v2 (282/287) sem forward ref; 270 emenda sem sinal + [[ADR-289]] fora do relates_to (zumbi r5-F08); 269 sem backlink ←290 (zumbi r5-F09); 282 emenda 2026-07-01 substitui mecanismo sem sinal | DOC-DRIFT | procede | procede-fechado | batch F3 |
| F64 — POLISH agrupado (~25: supersedure só-no-corpo da era pré-atomização 013/014/030/062; backlinks 060/136/148/194/199/303; paths envelhecidos 002/021/070/080/092/108/139; título 121; alias errado 229/269; emendas sem sinal 238/254/287/293/300/302; 217 wikilink alvo errado) | DOC-POLISH | procede | aceito-wontfix | lista no bruto; batch pré-beta |
| F65 — ADR-228 `Proposto` estagnado (zumbi r5-F07) — re-verificado: bloqueado legitimamente por go-live que não ocorreu; nota A21.l9 já documenta cobertura em CI | DOC-DRIFT | reavaliado | **não-acionável** | rebaixado do procede-aberto do r5 (cadência §4); reavaliar no go-live |

> **r6 fechado.** Cobertura 100% do universo auditável (410/410; 3 fases,
> 6 PRs). Critério de aceite da skill: 15 DOC-BLOCK mergeados em `main` ✓;
> falso-positivo no verify = 0/15 rebaixados ✓; zero finding recriando
> gate de pre-commit ✓; triagem faseada <30min/pacote ✓. Zumbis r5
> F04-F11: 6 executados (F42/F43/F57=F53-cluster/F61/F62 + F30/F33 na
> Fase 2), 1 refutado parcial (F11→lane spec-only ancorada), 1 rebaixado
> (F07→não-acionável). Follow-ups fora de doc: task chip `section_summary`
> cache key + decisão de flip 259/260 (owner).

---

## r5 — `vault-2026-07-03-r5`

> Skill audit-vault ([[ADR-302]]) · scope=all · mode=comprehensive. Gates 6/6
> verdes (zero finding mecânico). Amostra determinística: os MESMOS 24 arquivos
> de r3/r4 — ver meta-achado F17. Julgamento: senior-cto +
> information-architect + product-manager + prompt-engineer em paralelo + loop
> principal (reference/root doc↔código). Verify: 3/3 DOC-BLOCK confirmados com
> citação dupla. Fixes do r4 reverificados no código — nenhum regrediu. Bruto em
> `_scratch/audit-vault-2026-07-03.md` (efêmero).

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — A28 `_README` tabela: 11 lanes `planned`, mas l2/l3/l4/l10 `shipped` (#753-756; PR #758 só atualizou `lanes/*.md`) | DOC-BLOCK | procede | procede-fechado | tabela reconciliada + seção §Progresso datada, neste PR |
| F02 — A28.l1 `planned`/fora do SPRINT_CURRENT, mas desbloqueada (l4 ✅) e em execução (branch `a28-reserva-formula-canonica` de 2026-07-03) | DOC-BLOCK | procede | procede-fechado | frontmatter `in_progress` → SPRINT_CURRENT regenerado exibe a lane como tomada |
| F03 — ADR-188 declara supersedure parcial de ADR-186 §D3/§D6 + "wikilink bidirecional preservado", mas ADR-186 tem 0 menções a 188 | DOC-BLOCK | procede | procede-fechado | banner datado em 186 + `[[ADR-188]]` no `relates_to` (precedente ADR-095/r2) |
| F04 — ADR-208 D1 "lê `workspace.tier` (existing column)"; coluna não existe — tier é derivado BYOK (`_classify_llm_config`) | DOC-DRIFT | procede | procede-aberto | batch `vault-drift-batch-r5` (P2 proposto, owner: information-architect) |
| F05 — ADR-046 decisão revertida in-place sem âncora datada; "PWA em F8" órfã (F8 passou) | DOC-DRIFT | procede | procede-aberto | idem batch r5 |
| F06 — ADR-068 enumera stages mortos (`E0-audit`, `E7-review/apply`) como contrato atual; sem relates_to 093/199/213 | DOC-DRIFT | procede | procede-aberto | idem batch r5 |
| F07 — ADR-228 `Proposto` estagnado: gatilho "7 dias pós-tráfego real" sem registro há ~6 semanas | DOC-DRIFT | procede | procede-aberto | idem batch r5 (nota datada ou re-avaliação) |
| F08 — ADR-270 emenda 2026-06-12 (revisa §1/§3) sem sinal no frontmatter; `[[ADR-289]]` fora do relates_to | DOC-DRIFT | procede | procede-aberto | idem batch r5 (padrão bom: ADR-027) |
| F09 — ADR-290 estende ADR-269 sem backlink 269→290 | DOC-DRIFT | procede | procede-aberto | idem batch r5 |
| F10 — CAT_LEARNING_LOOP §"Status atual (2026-05-11)" contradiz §executivo (07-02, gate ✅); plano `done` não arquivado (§Conclusão prevê `git mv`) | DOC-DRIFT | procede | procede-aberto | idem batch r5 |
| F11 — MOBILE_SPEC sem frontmatter; links via âncora GH a shims (BACKLOG/DECISIONS) em vez de `[[ADR-129]]`/`[[ADR-151]]`; lane `report-mobile-impl` fora do funil | DOC-DRIFT | procede | procede-aberto | idem batch r5 (forma) · priorização é decisão do owner |
| F12-F16 — POLISH (contagens ARCHITECTURE §8 117→197; relates_to vazio/sub-representado ADR-108/148; size_lines fora de ordem ADR-188; ADR-248 sem H1) | DOC-POLISH | procede | aceito-wontfix | batch pré-beta, junto com POLISH remanescentes |
| F17 — (meta/skill) amostra do coletor não-rotativa: r3/r4/r5 auditaram os MESMOS 24 arquivos (`clean[::STRIDE]`); 97% do vault nunca entra no julgamento | DOC-DRIFT | procede | procede-fechado | fechado 2026-07-03 (follow-up r5): amostra rotativa `sha1(path) % stride` + `--run N`, stride por bucket (ref/plan/sprint/root 5 · adr/claude/prompt 20), `--stride`/`--full` p/ sweep 100% (modo de evento), self-test prova determinismo + cobertura; emenda datada na [[ADR-302]] |

**Falso-positivo evitado (3ª vez):** ausência de `model`/`temperature` em
`chart_conclusions.yaml` é design (ADR-122) — o gate de paridade rodou EXIT 0 e
os 6 builders ativos batem palavra-a-palavra com `conclusionUtils.ts`.
**Retirado no verify:** suposta supersedure unidirecional ADR-128↔199 (é
bidirecional; grep truncado do próprio especialista).

**Verificações que passaram:** README raiz (11 parsers 1:1, portas Docker,
scripts), ARCHITECTURE §4.1 (17 paths do glossário existem) e §18, 14/15 ADRs
com conteúdo técnico confirmado contra código, _TEMPLATE.md, forma/KRs do A28
`_README` (exemplar), fixes r4 (banner f9_3 + STATELESS_AUDIT §2/§4) presentes.

---

## r4 — `vault-2026-07-02-r4`

> Skill audit-vault ([[ADR-302]]) · scope=all · mode=comprehensive. Gates 100%
> verdes (zero finding automático). Amostra determinística: 24 arquivos (15 ADRs,
> 2 plans, MOC A26, chart_conclusions.yaml, 3 reference, README, _TEMPLATE).
> Julgamento: information-architect + senior-cto + product-manager +
> prompt-engineer em paralelo + loop principal (reference doc↔código). Verify:
> 3/3 DOC-BLOCK confirmados com citação dupla, 0 rebaixados. Bruto em
> `_scratch/audit-vault-2026-07-02.md` (efêmero). Nenhum finding do r3 regrediu.

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — MOC A26 tabela: l3 `blocked`/l8 `planned` mas lanes `shipped` | DOC-BLOCK | procede | procede-fechado | tabela corrigida (l3 ✅ 2026-07-01, l8 ✅ #666) neste PR |
| F02 — MOC A26 narrativa: l8 tratada como bloqueador futuro de l2 | DOC-BLOCK | procede | procede-fechado | narrativa + §Gate reescritos: pré-condição de código da l2 ✅, resta gate de tráfego |
| F03 — README/SETUP senha dev `admin123` ≠ seed `admin` | DOC-BLOCK | procede | procede-fechado | `admin` em README.md:88 + SETUP.md:239,339 (seed.py:22 é fonte) |
| F04-F07 — ADR-188/248/228/270 sem `size_lines` (>150 linhas) | DOC-DRIFT | procede | procede-fechado | batch r4 executado 2026-07-02: `size_lines` body-only adicionado aos 4 |
| F08 — plano CAT_LEARNING_LOOP §P3 diz `409`; ADR-188 §D7 decidiu `422` | DOC-DRIFT | procede | procede-fechado | corpo alinhado à ADR-188 §D7 (`422` + rationale) |
| F09 — `_TEMPLATE.md` de agente aponta shims BACKLOG/DECISIONS | DOC-DRIFT | procede | procede-fechado | template aponta SPRINT_CURRENT + ADR_INDEX + `rg docs/adr/` |
| F10 — ADR-027 mecânica de retry superada pela emenda ADR-270, sem cross-ref | DOC-DRIFT | procede | procede-fechado | banner de emenda + `relates_to` recíproco 027↔270 |
| F11 — CAT_LEARNING_LOOP `sprint_atual: A12` preso (corrente A26) | DOC-DRIFT | procede | procede-fechado | `status: paused` + `paused_at: 2026-05-11` + pause_reason (gate dogfood) |
| F12 — CAT gate dogfood vencido ~7 semanas sem prazo/escalonamento | DOC-DRIFT | procede | procede-fechado | **owner decidiu PASS (2026-07-02):** plano `done`; dogfood ritual dispensado, gate técnico 11/11 aceito como evidência; reabre se uso real mostrar revert alto/não-adoção |
| F13 — chart_conclusions: `receita_bar`/`despesas_doughnut` nunca interpolam (call site S2 usa ids inexistentes `receita_fonte`/`despesas_categoria` → conclusion null) | DOC-DRIFT | procede | procede-fechado | PR #725 (merge `27543bce`): ids canônicos no call site S2 + regra 4 no gate (call-site ∈ BUILDERS ∪ FALLBACKS) + teste de regressão |
| F14 — ARCHITECTURE §4.1 cita `family_members.json` (path proibido, ADR-134) | DOC-DRIFT | procede | procede-fechado | glossário aponta config `family_members` via `DBConfigStore` (ADR-134) |
| F15 — ARCHITECTURE §5 "20 routers" (real: 34) | DOC-DRIFT | procede | procede-fechado | 4 linhas "Contagem real" re-sincronizadas (models 48, routers 34, services 110, pages 32) |
| F16 — ARCHITECTURE §7 identificadores legados (E3…) vs descritivos F9.2/F9.5 | DOC-DRIFT | procede | procede-fechado | FULL_ORDER/DET_ORDER/tabela/snippet migrados p/ descritivo; legado vira coluna de referência |
| F17 — STATELESS_AUDIT §4 "único rate limit: invitations" falso pós-#720; `_DEFAULT_POLICIES` não registrado §2 | DOC-DRIFT | procede | procede-fechado | §4 reescrito (DB + Redis `INCR`+`EXPIRE`); `_DEFAULT_POLICIES` registrado §2 cat. (a) |
| F18 — STATELESS_AUDIT §2 `INSTITUTION_CONTENT_PATTERNS` path migrou | DOC-DRIFT | procede | procede-fechado | `classification/institution_classifier.py:11` |
| F19 — runbook f9_3 sem banner "concluído/histórico" (F9.3 executada 2026-05-05) | DOC-DRIFT | procede | procede-fechado | banner ✅ CONCLUÍDO/HISTÓRICO no topo |
| F20-F25, F27-F28 — POLISH (size_lines body-only 208/108, paths ADR-068/208, CAT §P4 vs corte de escopo, dono do gate de tráfego A26, contagens ARCHITECTURE §10, linhas STATELESS §2) | DOC-POLISH | procede | procede-fechado | batch r4 executado 2026-07-02 junto com os DRIFT |
| F26 — header chart_conclusions "8 builders ativos" (real: 6) | DOC-POLISH | procede | procede-fechado | PR #725: header cita os 2 builders sem call site vivo (score_gauge/impostos_pj) |
| S4 arquivamento (follow-up r3-F01) | — | confirmado | não-acionável | deferimento segue correto; reavaliar quando ADR-216 → Decidido |

**Zumbi r2-new-2 (LGPD export parcial) — FECHADO (2026-07-02, PR #732).**
Owner decidiu na triagem: **não** era escolha consciente de Art.18 — virou lane
P2 [[A26.l10]] (`lgpd-export-cobertura`), executada no mesmo dia. PR #732
estende `lgpd_export_service.py` às 6 famílias (Debt, PropertyIdentity,
Vehicle, Protection, Risk, TransactionOverride) + satélites com dado do
titular, e adiciona `test_lgpd_export_coverage.py`: todo model no fecho de FK
até `workspaces` (mesmo perímetro do erasure ADR-275) deve estar no export ou
em `EXPORT_EXCLUDED_TABLES` com rationale — model novo fora das listas falha o
teste (anti-recorrência).

**Lane P2 batch `vault-drift-batch-r4` — EXECUTADA 2026-07-02** (owner pediu
"atacar todos os pontos" na mesma sessão): F04-F11 + F14-F19 + POLISH F20-F25/
F27-F28 corrigidos em PR docs-only #726. F13/F26 fechados em PR #725 (código:
ids + gate regra 4 + teste, merge `27543bce`). Lateral de código (import morto
`lru_cache` em `pipeline/domain/models/bank.py:29`) fechado em #727. Os 2 itens
de decisão do owner foram triados em 2026-07-02: F12 → PASS/done; r2-new-2 →
lane [[A26.l10]], executada no mesmo dia (PR #732). **r4 sem remanescentes
abertos.**

**Falso-positivo evitado (repetido do r3):** ausência de `model`/`temperature` em
`chart_conclusions.yaml` é por design (ADR-122).

---

## r3 — `vault-2026-07-01-r3`

> Primeira execução da skill [`audit-vault`](../../.claude/skills/audit-vault/SKILL.md) ([[ADR-302]]).
> Escopo `all`/`comprehensive`. Gates determinísticos 6/6 verde (zero finding
> mecânico). Camada 2: 24 candidatos (amostra estratificada). Julgamento por 4
> especialistas (senior-cto, information-architect, product-manager,
> prompt-engineer). Relatório bruto: `_scratch/audit-vault-2026-07-01.md`.
> **Todos os 18 findings fechados neste PR** (docs + tema chart_conclusions).

| Código | Severidade | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| F01 — S4 plano entregue marcado `draft` | DOC-BLOCK | procede | procede-fechado | flip `status: done` + last_review; arquivamento deferido (5+ links inbound — cascade) |
| F02 — CAT_LEARNING_LOOP status/last_review stale | DOC-DRIFT | procede | procede-fechado | last_review 2026-07-01 + nota datada; decisão do gate dogfood é ops do owner |
| F03 — A26 prosa de entrada contradiz tabela (l1 shipada) | DOC-DRIFT | procede | procede-fechado | entrada reescrita → [[A26.l8]] |
| F04 — A26 "segurança já garantida" mas l8 `planned` | DOC-DRIFT | procede | procede-fechado | "a garantir quando l8 shipar" |
| F05 — ADR-208 Files touched aponta artefato inexistente | DOC-DRIFT | procede | procede-fechado | `apply_tier_filter` em service (não repository) |
| F06 — ADR-208 >150 linhas sem size_lines | DOC-DRIFT | procede | procede-fechado | `size_lines: 187` |
| F07 — ADR-168 supersedure via anchor GH bruto | DOC-DRIFT | procede | procede-fechado | trocado por `[[ADR-X]]` |
| F08 — ADR-168/151 relates_to ausente (bidirecional) | DOC-DRIFT | procede | procede-fechado | `relates_to` recíproco 168↔151 |
| F09 — chart_conclusions `alocacao_alvo` template diverge | DOC-DRIFT | procede | procede-fechado | YAML alinhado ao builder ("Maior desvio: … pp em …") |
| F10 — chart_conclusions `score_gauge` required_keys incompleto | DOC-DRIFT | procede | procede-fechado | `+ score.max`; classe opcional documentada |
| F11 — 12 templates fallback-only sem marca | DOC-DRIFT | procede | procede-fechado | marcados `# fallback-only` |
| F12 — chart_conclusions sem gate de paridade | DOC-DRIFT | procede | procede-fechado | `dev/check_chart_conclusion_parity.py` + pre-commit + `version 1.1` |
| F13 — tag `area/relatorio` vs `area/report` | DOC-DRIFT | procede | procede-fechado | normalizados 11 arquivos → `area/report` |
| F14 — ADR-290 sem size_lines | DOC-POLISH | procede | procede-fechado | `size_lines: 105` |
| F15 — ADR-208 aliases folksonomy | DOC-POLISH | procede | procede-fechado | trimmed p/ 2 |
| F16 — ADR-128 campo `phase` com status+placeholder | DOC-POLISH | procede | procede-fechado | `phase: "A6-cleanup"` |
| F17 — ADR-208 endpoint `{run_id}` vs `{report_id}` | DOC-POLISH | procede | procede-fechado | `{report_id}` |
| F18 — chart_conclusions header sem formatter `num` | DOC-POLISH | procede | procede-fechado | documentado |

**Falso-positivo evitado (prompt-engineer):** ausência de `model`/`temperature`
em `chart_conclusions.yaml` **não** é finding — ADR-122 define esses templates
como determinísticos por design.

**Follow-up não-bloqueante:** arquivamento do plano S4 (F01) fica deferido — o
`git mv` para `docs/archive/` quebraria 5+ links inbound; fazer junto com
atualização desses links quando conveniente.

---

## r2 — `repo-audit-mathoms.ai-2026-06-11-r2`

> Relatório original efêmero (externo, não versionado). Esta seção foi
> **reconstruída** da trilha verificável: ADRs `phase: audit-r2`, corpo dos
> commits [#671](https://github.com/davidrobert/mathoms/pull/671) /
> [#676](https://github.com/davidrobert/mathoms/pull/676) e
> [#668](https://github.com/davidrobert/mathoms/pull/668). Códigos/severidades
> originais preservados onde recuperáveis.

| Código | Sev. orig. | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| **SEC-03** | HIGH/CRIT | procede | procede-fechado | [[ADR-299]] · #676 (bump 4 deps; pip-audit 17→0) ⚠️ |
| **REL-03** | Médio→P1 | procede | procede-fechado | [[ADR-297]] · #671 (idempotência de Report) |
| **P0-4 / SEC-06** | P0 | procede | procede-fechado | #671 (fail-fast FERNET_KEY em prod; sem ADR) |
| **QUA-05** | Médio | procede | procede-fechado | #671 (detector P7 isenta docstring de módulo; sem ADR) |
| **QUA-04 / ARQ-01** | Baixo | procede | procede-fechado | #671 (slogan money do CLAUDE.md ↔ ADR-090; docs) |
| **MAT-01 / DAT-06** | — | procede | procede-fechado | #668 (flip ADR-241/242/243 → Decidido) |
| **item 6** — nota Qual. 4→3 | — | não-acionável | não-acionável | [[ADR-298]] D1 (recalibração de avaliador, não regressão) |
| **item 6** — "backend limpo, dívida no pipeline" | — | refutado | refutado | [[ADR-298]] D2 (medição: backend tem a maior fatia) |
| **item 6** — ratchet "sem metas decrescentes" | — | procede | procede-fechado | [[ADR-298]] D1 (política documentada; já decresce) |
| **DAT-01** (float monetário, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | data-engineer: ADR-283 shipou (Numeric(18,2), `check_float_money --scan-models`+hook, drop monthly_cap) |
| **DAT-02** (contrato schema warn/strict, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | data-engineer: e2 `additionalProperties:false`+gate; flip strict é lane de telemetria consciente (ADR-283) |
| **DAT-05** (PII/retenção/erasure, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | data-engineer: ADR-231 (crypto wired) + ADR-275 (retenção+erasure cascade FK fim-a-fim) Decididos |
| **REL-02** (idempotência pós-run, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | sre-devops: guarda terminal ADR-297 ([`pipeline_task.py:757,527`](../../backend/app/tasks/pipeline_task.py)) cobre TODO o pós-processamento, não só Report; demais tasks idempotentes |
| **REL-02b** (latente) — `TaskSuggestion.dedup_key` sem UC | P3 | procede | aceito-wontfix | sre-devops: inalcançável sob `reject_on_worker_lost`+`prefetch=1`; **gatilho:** reabrir P2 se `prefetch>1`/redelivery concorrente ([`task.py:242`](../../backend/app/models/task.py)) |
| **r2-new-1** — ADR-095 status stale | P2 | procede | procede-fechado | data-engineer: 095 `Proposto` mas D1/D2→ADR-231, D3/D4→ADR-275 shipados; banner + `relates_to [[ADR-231]]` adicionado nesta rodada |
| **r2-new-2** — LGPD export cobertura parcial | P2 | procede | **procede-fechado** (2026-07-02) | lane [[A26.l10]] executada: PR #732 estende export às 6 famílias + satélites e adiciona gate estrutural (fecho de FK até `workspaces` ∈ export ∪ allowlist c/ rationale) |

**⚠️ SEC-03 — lição de processo.** A validação manual de #671 colocou SEC-03 no
balde "CVEs Python… refutados ou já endereçados (versões já patched)". Estava
**errado**: `pip-audit` (2026-06-19) confirmou 17 CVEs reais com fix acima da
versão pinada. Reaberto e fechado em #676 / [[ADR-299]]. Validar CVE **sempre**
com `pip-audit` contra o lock — leitura manual de "versão X já é segura" decai
conforme novas CVEs são divulgadas.

**✅ DAT-01/02, REL-02, DAT-05 — reverificação concluída (2026-06-30).** O balde
foi reverificado com disciplina empírica (`data-engineer` p/ DAT-*, `sre-devops` p/
REL-02), exatamente porque fora refutado no mesmo passo que errou o SEC-03. **Resultado:
diferente do SEC-03, a refutação RESISTIU** — cada decisão das ADRs correlatas foi
confirmada *shipada no código* (não só lida na ADR): float monetário (ADR-283 +
gate scan), `additionalProperties` (e2 + gate), criptografia/retenção/erasure
(ADR-231/275 + cascade FK fim-a-fim), e a guarda terminal da ADR-297 cobrindo todo
o pós-processamento. O relatório original é efêmero, então os códigos foram
*reconstruídos* (rótulos exatos perdidos) e a superfície re-auditada do zero. A
re-auditoria fresca levantou **2 achados novos** (r2-new-1 ADR-095 stale, fechado
nesta rodada; r2-new-2 LGPD export parcial, `procede-aberto` p/ decisão do owner)
+ 1 latente (REL-02b, aceito-wontfix com gatilho). Lição SEC-03 aplicada: nenhuma
refutação aceita sem evidência empírica de que o fix existe no código.
