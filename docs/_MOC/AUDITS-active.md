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
| F17 — (meta/skill) amostra do coletor não-rotativa: r3/r4/r5 auditaram os MESMOS 24 arquivos (`clean[::STRIDE]`); 97% do vault nunca entra no julgamento | DOC-DRIFT | procede | procede-aberto | P2, owner: loop principal — offset da stride por run/data em `collect_candidates.py` (reproduzível dentro do run) |

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
