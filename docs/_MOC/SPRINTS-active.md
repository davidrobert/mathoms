---
type: moc
title: SPRINTS-active — Sprint corrente + curating de prioridade
aliases: ["SPRINTS-active", "sprints-active"]
---

# SPRINTS-active — Sprint corrente + curating de prioridade

> **Editorial.** Resumo narrativo da sprint atual. Status detalhado: `_generated/SPRINT_CURRENT.md`.
>
> **Fonte de verdade da sprint corrente:** o campo `sprint_status` no frontmatter de cada `docs/sprint/<X>/_README.md`. Valores: `current` (única) · `candidate` (próxima) · `paused` (escopo aberto, ceu prioridade — múltiplas permitidas) · `done` (encerrada). Validado por `python3 dev/build_doc_index.py --check` — falha se houver 2+ MOCs com `current` ou status fora do vocabulário. Ao virar a sprint, edite os `_README.md` envolvidos **antes** de regenerar. Transições típicas: `current → done` (escopo entregue) · `candidate → current` (promoção); transições com débito conhecido: `current → paused` ou `candidate → paused` ([[ADR-234]]).

## Sprint corrente

### A40 — Report trust: o dado que entrou tem de chegar ao usuário (`current` desde 2026-07-30)

**Continuação declarada de [[PLAN-report-trust]]** (`sprint_origem: A28`) — não é
plano novo. Origem: skill `report-review` sobre o último relatório do workspace
dogfood, 2026-07-29 ([[REPORT-REVIEWS-active]] §r3, 33 achados sistêmicos).
Nenhum stage foi re-executado: o objeto é o **artefato entregue**.

A A39 provou que o dado **entra** certo; a A40 prova que ele **chega ao usuário**.
26 dos 33 achados são defeitos de **entrega**, não de cálculo — consumidor lê chave
que o emissor não emite, janela trocada, seção que colapsa depois de prometer
conteúdo, PII cartorial interpolada no render. O sinal decisivo: a conservação do
razão fecha em **tol-zero (105/105 grupos)** e ainda assim há duplicação material
medida — **o gate vigente mede a camada errada**.

Painel de 6 especialistas revisou antes da abertura e produziu 33 objeções, duas
delas estruturais: **o mecanismo do achado P0 estava errado** (a normalização de
caixa que ele culpava já existe no hash — escrita como estava, a lane shiparia um
no-op e fecharia verde) e **os 7 achados "inertes" eram um evento de embarque de
regressão** (deixam de ser inertes quando a [[A40.l4]] mergeia). **24 lanes em 5
ondas (0–4) + 1 fora de onda**; a ordem **não** segue a coluna de severidade, e sim
"alcança o usuário na config atual", porque a própria rodada registrou que 37 dos 44
vereditos carregam inflação desconhecida.

**Reordenada em 2026-08-03.** A abertura tinha 14 lanes em 3 ondas; a **Onda 0**
("parar a sangria") e a **Onda 3** ("degradação honesta") nasceram do incidente do
run `2ded7aab`, e a [[A40.l24]] entrou fora de onda, promovida da A41. A Onda 0
**precede a Onda 1 e não é negociável** — a Onda 1 é "medir antes de mexer" e medir
exige run que completa. **Nada saiu da sprint:** as ondas novas entram por cima do
escopo existente, sem despejar lane P2/P3 para a A41.

- **Sprint:** [sprint/A40/_README.md](../sprint/A40/_README.md) · **Origem:**
  revisão de relatório 2026-07-29 ([[REPORT-REVIEWS-active]] §r3; cru off-git).


## Sprint recém-fechada

### A38 — Ingestão confiável: certificação de parse dos layouts 2026 (`done` 2026-07-23)

**Origem:** três certificações empíricas do caminho E0→E2 (2026-07-22/23) sobre
corpora locais reais do owner (16 docs pessoais + 6 de investimento + 129 do
workspace 5@5.com). Achado-título: `parse_itau` perdia ~50% das transações do
layout 2026 e o C6 Global (USD/EUR) sumia inteiro (0 tx), ambos silenciosos.
**Ondas P0+P1 entregues (10 lanes, PRs #1018–#1031)**, revisadas por 3 painéis
de especialistas: **P0** [[A38.l1]] harness de certificação · [[A38.l2]]
`parse_itau` layout 2026 (34→74 tx) · [[A38.l3]] gate anti-silêncio E2
([[ADR-342]]) · [[A38.l14]] gate por observação `raw_rows_detected` (fecha o
buraco do C6 Global). **P1** [[A38.l6]] Wise moeda por conteúdo · [[A38.l4]]
colisão `0800 726` · [[A38.l5]] cdbdetalhes required forte · [[A38.l7]] fatura
Unique 2026 · [[A38.l15]] parser C6 Global USD/EUR (0→199/179/56 tx) · [[A38.l12]]
CDB PDF determinístico + checksum. KR-A..E medidos verdes no harness. North
Star atingido: **nenhum documento suportado perde transação em silêncio** —
extração completa ou escalação honesta. **Cauda P2 trailing** (follow-up/A39):
[[A38.l8]] · [[A38.l9]] · [[A38.l10]] · [[A38.l11]] · [[A38.l13]] (abre ADR nova).

- **Plano:** [sprint/A38/_README.md](../sprint/A38/_README.md) · **Origem:** certificações de parse 2026-07-22/23 (memória de sessão do agente; corpora locais do owner, fora do git).

### A37 — Qualidade do relatório: achados do pipeline-review 2026-07-20 (`done` 2026-07-22)

**Origem:** revisão profunda do run completo do dogfood (skill `pipeline-review`,
2026-07-20 @ `c61c1c29` — primeiro run com a onda R3 ativa): 5 revisores
especialistas + 5 verificadores adversariais; todos os achados sobreviveram com
evidência re-derivada. 15 lanes em 4 ondas por dependência. **P0** [[A37.l1]]
(parecer cego por dupla truncação do exec context + redação de identificadores —
ADR `Proposto` antes do PR) · **P1** [[A37.l2]] narrativa síntese R$ 0,00 ·
[[A37.l3]] self-heal de docs parkados · [[A37.l4]] sentinelas "N/D" · [[A37.l5]]
exemplo sintético no prompt · [[A37.l6]] labels humanizadas · [[A37.l7]] CV17
renda passiva (compõe com [[A36.l3]]) · **P2/W2** coerência de narrativas e
bases canônicas (co-design `financial-planner`), apêndices, seguradora,
resiliência, colunas mortas · **cauda W3** batch cosmético + débitos
owner-gated. Exclusão deliberada: FIN-06. DoD: KR-A..E medidos re-rodando a
skill em run fresco.

- **Plano:** [sprint/A37/_README.md](../sprint/A37/_README.md) · **Origem:** pipeline-review dogfood 2026-07-20 (relatório em `_scratch/`, gitignored; lanes self-contained).

### A12 — Categorization learning loop + post-A11 follow-up (`done` 2026-07-09)

Sprint retomada de `paused` em 2026-07-08 e **fechada em 2026-07-09**. Duas
frentes:

- **Cat-learning-loop** — MVP V1 completo (P1-P4 #188/#194/#195-#198/#203 +
  gate técnico 11/11 #202); gate dogfood humano **PASS por decisão do
  owner** (2026-07-02, ratificado 2026-07-08); plano arquivado.
- **[[A12.alocacao-v2]]** — migração alocação-alvo v1→v2 (7 classes AUVP,
  desvio backend-driven) em **9 PRs (#885-#910)**: calculator de domínio,
  DTOs + conversão on-read, API v2, seed, serializer + E5 `derived` rico,
  card do relatório consumindo `derived` e **`alocacaoBucketMapper`
  client-side deletado** (débito que originou a lane), chart ids
  consolidados. Co-design de 3 especialistas ([[ADR-141]] §Emenda).
  Corrigiu o bug do shape órfão do seed + um bug de integração do derived.

Também nesta sprint: sunset-disk-artifact ([[ADR-212]]),
decision-code-autogen ([[ADR-214]]), bank-account-disambig ([[ADR-226]]),
irpf-prefill ([[ADR-229]]). Débitos não-bloqueantes registrados: PR8
(redesign visual do wizard de alocação — shim já funcional, backlog) e PR11
(remoção do schema v1 + ativação de regra — owner-gated).

### A35 — Continuidade não some quando o número de conta não extrai (`done` 2026-07-08)

Follow-up nomeado da A32 (issue #860, confirmada pelo owner na triagem
KR3): a chave estrita da A32.l4 ([[ADR-310]]) suprimia um gap genuíno de
continuidade quando `account_number_norm` não extrai de um dos extratos
da mesma conta. Co-design (senior-cto + data-engineer + financial-planner):
escada de resolução (Tier 1 `AccountResolver`/ADR-226 quando há cadastro;
Tier 2 intra-run `count==1` — o dogfood tem 0 contas cadastradas, logo é
o tier que conserta), sinal auditável `SaldoChainMemberInferred`
obrigatório, só `not is_fatura`, `_chain_key` puro, `AccountGrouper`
intocado. **Emenda datada na [[ADR-310]]** (não ADR nova — refina a
decisão, herda a absorção pelo `SourceRef.kind`, [[ADR-278]] §B7).

**Encerrada 2026-07-08 — 1/1 lane shipped** (impl #865 `08c535cf` +
surfacing #868 `6e8fb369`; planejamento #864). Gate confirmado no dado
real do dogfood: os 2 extratos rico coalescem em 1 cadeia e o gap
**122 dias (abr–jun/2026)** volta à tela com selo `documento_faltando` e
sinal auditável sem número cru; 14/14 testes de regressão verdes; zero
falsos da A32 reabertos. Issue #860 fechada.

### A32 — Review de reconciliação confiável (`done` 2026-07-08)

Origem: dogfood do owner 2026-07-07 — run `d1732edd` com 18 errors + 31
warnings na tela de review; investigação em 2 frentes (código + dados
reais do DB) confirmou que **100% dos 18 errors são defeito do produto**
(vocabulário E2-LLM stale de mai/jun, regex de período casando o prefixo
sha256 do filename, skip-list furada por `tipo`/`tipo_documento`, chave
de continuidade sem `account_type` + ordenação por hash) apresentados na
tela como problema do dado do usuário. 7 lanes em 5 ondas
([[MOC-sprint-a32]]): l1 purga órfãos + baseline · l2 contrato E2-LLM +
golden de paridade derivado + gate strict CI-only · l3 regex de período
ancorada · l4 chave canônica de conta ([[ADR-310]] Proposto, interina de
ADR-278 §B7) · l5 tombstone na reclassificação + versão de extração
consultável ([[ADR-311]] Proposto) · l6 review UX (identidade legível,
selo de natureza, agrupamento por documento) · l7 gate re-run dogfood
instrumentado. Co-design: senior-cto + data-engineer +
financial-planner + product-designer + prompt-engineer +
product-manager; revisão de forma/priorização: product-manager +
information-architect.

**Encerrada 2026-07-08 (~30h após abertura):** 7/7 lanes shipped em 12
PRs (l1 #825 · l2 #826 · l3 #823 · l4 #829 [[ADR-310]] `Decidido` ·
l5 #837 [[ADR-311]] `Decidido` · l6 #841/#843/#845 · gate #857 + docs
#832/#838/#846). Gate medido na run real: baseline de 58 reasons → **0
em dois re-runs consecutivos** (KR1/KR2/KR4 ✅); 39 warnings
classificados 1-a-1 = zero gaps genuínos (4 famílias de falso
positivo); triagem KR3 do owner aprovou os cards; ressalva rico
(mesma conta, gap genuíno suprimido pela chave sem número) virou
issue #860. Custo LLM do gate ~US$ 2,6 (julho US$ 14,20/20, ADR-173).

### A11 — Platform review execution (`done` 2026-07-08)

**Fechada em modo code-complete modificado** (emenda datada de [[ADR-228]],
decisão do owner na sessão de closure). 6 ondas, 138 findings, 32 tasks.
W1 ✅ + W2 ✅ na sprint; boa parte de W3/W4/W6 shipou via outras sprints —
W3-T01/W3-T04 (#718), W3-T03 (#584), W3-T05 (A21.l6), W4-T04 (#720),
W6-T02 (ADR-307), W6-T03 (F9.4), W6-T04 (#111), W6-T05 (A32.l5 + A33.l6
#844), W6-T06 (ADR-150), W6-T07 (A33.l9 #855). A sessão de closure
entregou o residual executável da W5 — **W5-T01** a11y (#882), **W5-T02**
charts + emenda ADR-139 (#883), **W5-T03** monetário (#884) — e a
reconciliação docs (#876/#881). **Residual transferido (não é débito da
A11):** 5 itens owner-gated (W3-T02 Resend · W4-T01 off-site R2 · W4-T02
Coolify · W4-T03 Sentry · W4-T05 status page) agora possuídos por
[[PLAN-launch-trust]] §F2 + gates G1–G5 da ADR-228; backlog candidates
com tracks preservados: W5-T04 #1/#3/#4, W5-T05 ([[ADR-140]]), W6-T01
residual, flip `prune_mode=delete`. [[ADR-174]] segue `Proposto` até o
off-site R2 existir.

- **Plano:** arquivado em [PLATFORM_REVIEW_PLAN-2026-07-08.md](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md).
- **Sub-lanes:** report-publication ✅ 2026-05-10 ([[ADR-187]]), cat-overrides-ux ✅ 2026-05-10; competitive-pierre segue viva no plano [COMPETITIVE_PIERRE](../plan/COMPETITIVE_PIERRE/_README.md) (Fase 1 ready).
- **DOC_REORG** ✅ 2026-05-07, arquivado em [DOC_REORG_PLAN-2026-05-07.md](../archive/DOC_REORG_PLAN-2026-05-07.md) ([ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md)).

### A31 — Débitos da A30: audit persistido (7B.5) + teto de budget calibrado (`done` 2026-07-07)

Origem: os 2 débitos registrados na lane [[A30.l1]]. 2 lanes paralelas
([[MOC-sprint-a31]]): l1 (P1) audit do console interno → tabela
`internal_ops_audit` na MESMA transação da operação ([[ADR-309]] Proposto —
tabela nova sem FK, REVOKE UPDATE/DELETE em prod, sem dual-write/backfill,
exceção autônoma p/ login session-less) · l2 (P2) clamp do editor de budget
US$ 1.000 → US$ 300 com emenda datada na [[ADR-173]] (racional
financial-planner: ~50× P99 real). Co-design: senior-cto + data-engineer +
sre-devops + product-manager + financial-planner. KR1: 100% dos fluxos de
mutação de operador (15 services + 3 eventos login) auditados em tabela,
medido por teste que enumera os paths.

**Encerrada em 2026-07-07 — 2/2 lanes shipped no mesmo dia** (l2 #818 ·
l1 #819; plano+ADR em #817). ADR-309 Decidido; 7B.5 fechado no plano
INTERNAL_ADMIN (guardrail "troca só do sink" emendado).

### A30 — Ops FinOps: budget LLM editável no console interno (`done` 2026-07-07)

Origem: dogfood do owner 2026-07-06 — run do pipeline (executor Go, F2 do
ADR-150) abortou no hard-stop de budget LLM ([[ADR-173]]: cap $5, gasto
$5.57) e o único unblock foi UPDATE manual via SQL. 1 lane P1
([[MOC-sprint-a30]]): editor de `monthly_llm_budget_usd` por workspace no
console ops (service + PATCH + UI com contexto mês-calendário + audit
hard-fail) — **shipped no PR #815 (2026-07-07, CI verde)**. KR1: 0 unblocks
de budget via SQL após a lane. Co-design:
`product-manager` + `sre-devops`; sem ADR nova ([[ADR-116]] + [[ADR-173]]).

Na fila do owner: retomar [[MOC-sprint-a26]] (`paused → current`) quando as
≥20 gerações qualificadas de parecer acumularem, ou promover a A27
(`candidate`).

### A29 — Review UX: conferência de pipeline centrada em documentos (`done` 2026-07-06)

Origem: dogfood do owner 2026-07-06 — run E3 pausou em `needs_review` com 18
strings duplicadas sem documento + JSON 29KB; owner aprovou às cegas. 3 lanes
sequenciais ([[MOC-sprint-a29]]): l1 tela de review v1.5 (agrupamento +
consequência explícita + telemetria `review_action`) · l2 cobertura
`ReviewReason` completa em E3 + projeção `validation_issues` (fecha ADR-272
crit. 6) · l3 inbox de pendências em `/documents` + banner de análise pausada.
ADR canônica: [[ADR-308]] (Decidido no fechamento).

**Encerrada em 2026-07-06 — 3/3 lanes shipped no mesmo dia** (l1 #800 · l2
#802 · l3 #803; docs/ADR em #798). Gate F0 de medição overridden pelo owner
("atuar em tudo"); KR1 (≥70% resoluções construtivas) instrumentado via evento
`review_action` aguardando uso; baseline KR2 registrado no #800. Fila do owner
pós-A28 segue válida em paralelo: re-gerar parecer com dados corrigidos ·
`G-owner-reclassify` · `G-owner-label` · re-eval golden do parecer
(owner-gated, US$12).

### A28 — Report Trust: o relatório para de afirmar precisão que os dados não sustentam (`done` 2026-07-06)

**Encerrada em 2026-07-06 — 11/11 lanes shipped** (l2 #754 · l3 #755+ADR-305 ·
l4 #756+ADR-306 · l10 #753 · l7 #779 · l5 #782 · l6 #783+manifest 1.7 · l8 #786 ·
l9 #790 · l11 #788+manifest 1.8 · l1 #787). KR1/KR3 atendidos por teste de
invariante; KR2 e re-medição da l7 aguardam gates de owner (por design); KR4
entregue (banner + âncoras tipadas + ressalva de fallback). Reserva: 86,7 meses
"Excessiva" → 53,3 vs alvo 18m (perfil PJ-dominante); TRS 22,63% → universo
consistente + guardrail >8%; PGBL: 1 recomendação por relatório; ADR-240 ativada.

**Promovida em 2026-07-03; A26 → `paused` ([[ADR-234]]).** 1ª janela do plano
[[PLAN-report-trust]], nascida da revisão completa do relatório dogfood `72883bde`:
três recomendações do relatório atual **pioram** a situação do cliente (TRS fictícia
22,63% a.a. → desacelerar aporte; reserva "Excessiva" de 31,6 meses com numerador =
todo o investível → desmobilizar carteira; Cerbasi "Gastador" sobre R$ 401k de despesa
opaca → cortar gasto errado). Duas são violação de contrato escrito (FORMULAS.md
§Reserva · [[ADR-191]]). Co-design 2026-07-03 (PM + IA + data-engineer +
prompt-engineer; financial-planner + product-designer no parecer de origem).

**11 lanes em 3 ondas:** Onda 0 (fórmula, Must, `[l4→l1] ∥ l2 ∥ l3` — ADRs `Proposto`
em l3/l4) → Onda 1 (loop de dados: categorização [[A28.l5]], proteção/apólices
[[A28.l6]], dedup de imóveis excluídos [[A28.l7]], higiene de períodos [[A28.l8]]) ∥
Onda 2 (apresentação honesta: banner de qualidade [[A28.l9]], formatter de âncoras
[[A28.l10]], guardrails pós-LLM [[A28.l11]] — l10 livre; l9/l11 mergem pós-Onda 0).
Gates de owner: `G-owner-reclassify` + `G-owner-label`.

- **Sprint:** [sprint/A28/_README.md](../sprint/A28/_README.md) (11 lanes) · **Plano:**
  [plan/REPORT_TRUST/_README.md](../plan/REPORT_TRUST/_README.md) · **Prompt (arquivado):**
  [agent_prompts/archive/orchestrator_a28_report_trust-2026-07-06.md](../agent_prompts/archive/orchestrator_a28_report_trust-2026-07-06.md).
- **Precedência de corte:** Must l1+l2+l3+l4 (nunca cortar l1/l2) · Should
  l5+l6+l7+l8+l9+l10+l11 · Could re-medição pós-gate da l7.
- **Sinergia A26:** cada iteração re-gera o parecer → acumula as ≥20 gerações que
  destravam [[A26.l2]]/[[A26.l4]]. Reavaliar retomada da A26 ao fim da janela.

## Sprint anterior

### A25 — Data Lineage: reverso + produto N1/N2 + debug LLM (`done` 2026-06-16)

**Encerrada em 2026-06-16 — 7/7 lanes shipped.** Cutover do flip dedup `natural_key`
v2 + `member_hashes` reais (l2/l6, #648), query reversa (l3, #600), debug LLM/eval
(l4, #603), produto N1/N2 (l5, #602), cutover override (l1, #604). A l7 (decisão do
flip `warn→strict` do `evidencia_path`) fechou como **carry-over A26** (#649) — o gate
exige ≥20 gerações e só há 3 com telemetria (taxa ~89%, 81% conformidade de path) →
flip vira lane própria na A26. Requisito de done cumprido; modo segue `warn`.

- **Carry-overs A26:** flip strict `evidencia_path` (foco prompt/whitelist via
  `prompt-engineer`) + drop do shim v1 do dedup (M2, [[ADR-287]]).
- **Plano:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) ·
  **Sprint:** [sprint/A25/_README.md](../sprint/A25/_README.md).

## Sprint candidate (próxima)

### A42 — Provabilidade da ingestão e do razão: fechar o falso-verde do instrumento (`candidate` 2026-08-04)

**Origem:** três certificações do mesmo workspace dogfood em 2026-08-04 —
[[PARSE-CERTIFY-active]] §r2 (ingestão E0→E2, 9 abertos + 1 do r1),
[[LEDGER-CERTIFY-active]] §r4 (razão E3/E4, 10 abertos) e
[[PIPELINE-REVIEWS-active]] §r4 (run completo, 74 achados). Absorve o handoff que a
[[A40]] §Fora do sprint declarou **fora dela por camada** e "não roteado".

**Tese:** o corpus não regrediu em dado — regrediu em **capacidade de provar** que o
dado está certo. Os três instrumentos que deveriam denunciar perda passaram a dar
verde sem medir: gate de conservação suprimido por conclusão do próprio parser, skill
de certificação carimbando `coberto` sobre a dimensão de 62,5% do peso do score, e
check que não consegue avaliar **evaporando** da conta em vez de virar `skipped`.
Daí a Onda 1 ser instrumento, não fix: sem detecção, todo fix abaixo regride em
silêncio e fecha verde.

**Sucessora declarada da [[A39]]** (mesma tese `ingest-trust`), fechada no mesmo PR:
12 de 13 lanes shipadas, e os resíduos deferidos — travados na identidade do checksum
de fatura — ganham destino porque o §r2 destravou o blocker por medição (o total
impresso é a soma das próprias linhas em 31 de 41 documentos ⇒ **teto estrutural**,
não dívida de wiring).

**KRs** (4, binários, cada um com duas linhas de contagem contra Goodhart): fidelidade
discriminada de completude da fonte · instrumento que não dá verde falso (prova por
mutação: remover o input ⇒ exit ≠ 0) · identidade sob cobertura redundante · base
mensal honesta.

**Gate de saída:** não é burn-down — é **re-certificação**. A42 fecha quando
`parse-certify` r3 + `ledger-certify` r5, sobre o mesmo corpus, retornarem **zero
achado novo da classe falso-verde**.

**Gatilho de promoção** (evento, não calendário): [[A40]] → `done`.

- **Sprint:** [sprint/A42/_README.md](../sprint/A42/_README.md) · **11 lanes**
  `planned` em 4 ondas (0–3), teto de capacidade 14. Declara o **critério de admissão**
  em 5 cláusulas, fechando a §Pendência de decisão nº 10 da [[A40]].

### A41 — Governança de chamada LLM: fechar a rota alternativa ao choke-point (`candidate` 2026-08-03)

**Origem:** §Escopo deferido da [[ADR-355]] (mergeada 2026-08-03) + 1 achado
colateral. Três arquivos de produção instanciam o SDK `anthropic` direto, fora do
choke-point `LLMService` — sem budget ([[ADR-173]]), sem `LLMCallLog`, sem cache,
sem sanitização ([[ADR-175]]) — e não há gate impedindo o quarto.

**KR:** `rg 'import anthropic' --type py` retorna 0 fora de `pipeline/llm/` e
`tests/fakes/`, com gate no pre-commit que hard-falha no próximo (3 → 0).

**Gatilho de promoção** (evento, não calendário): decisão de abrir o 2º usuário,
**ou** o `make go-parity` medir ≥1 chamada de visão da Caixa no dogfood.

O `product-manager` recomendou desmembrar em vez de abrir sprint. Acatado em
parte, por decisão do dono (2026-08-03): a lane com **consumidor datado** foi
promovida para a sprint corrente como [[A40.l24]] — a A41 mantém as 3 lanes que
esperam gatilho. A objeção completa está registrada no `_README` da A41.

- **Sprint:** [sprint/A41/_README.md](../sprint/A41/_README.md) · 3 lanes
  `planned` · [[PLAN-launch-trust]].

### A27 — Data Lineage Onda 6 (conclusão): citação confiável do parecer (`candidate` 2026-06-19)

**Sucessora direta da A26 — escopo Must já entregue antecipadamente (2026-07-02),
executado durante a janela A26.** 6ª e última janela do plano [[PLAN-data-lineage]]:
fechou a raiz que a A26 contornou — o LLM parou de autorar o número do parecer e o
pipeline renderiza o valor da folha ([[ADR-296]] `Decidido`, executada via [[A26.l9]]
✅ #687) — e materializou a citação verificada como **edge de lineage por chave
natural** ([[ADR-293]] `Decidido (A27.l1)`, lane [[A27.l1]] ✅ #715/#716/#718; KR3
provado por teste de reordenação de `top_ativos`). Follow-up do KR1: pureza monetária
da prosa (persona 1.1.0, 61→7 violações) + doutrina [[ADR-304]] (#729 ✅). Resta a
**promoção formal** (A26 retoma de `paused`, fecha gates de tráfego → `done`; então
A27→`current`→`done`) — a A28 (`current`) é quem gera esse tráfego. Condicional:
[[A26.l5]] `m2-override-drop` se não fechar na A26.

- **Plano:** [sprint/A27/_README.md](../sprint/A27/_README.md) · **Dono:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) §Onda 6.

### A36 — Follow-up da auditoria r4 (`candidate` 2026-07-09, revisada 2026-07-10)

**Contêiner de proveniência, não sprint coesa.** 5 lanes de mérito da auditoria
externa r4 que não tinham rastreio (achado MAT-03); ~4-5 dias somados, sem
dependência compartilhada, nenhuma gating. **Revisão do painel (2026-07-10)**
verificou todas as âncoras `arquivo:linha` contra o código (verdadeiras), desfez
o "tudo P1" e corrigiu dois erros de mérito: [[A36.l3]] protegia checks cosméticos
(CV9/CV10) e não os de conservação (CV2/CV3/CV6 são `warning`, não `error`);
[[A36.l5]] QUAL-02 cega o alarme de reconciliação E3, não "dropa do patrimônio".
Tiers pós-revisão: **P0** [[A36.l3]] (conservação client-facing) · **P1**
[[A36.l1]] Parte A (gate de fronteira) + [[A36.l5]] QUAL-02 · **P2** o resto
([[A36.l1]] inversão, [[A36.l5]] QUAL-01, [[A36.l4]] gate govulncheck, [[A36.l2]]
spike). Recomendação: promover o subconjunto de alto valor; o resto fica "later".

- **Plano:** [sprint/A36/_README.md](../sprint/A36/_README.md) · **Origem:** auditoria r4 (confidencial, fora do repo).

## Sprints pausadas

Sprints com escopo aberto cujo trabalho foi suspenso. Retomada não-bloqueada: lanes ready continuam ready, frontmatter volta a `current`/`candidate` quando o owner decidir.

### A26 — Data Lineage: consolidação (`paused` 2026-07-03)

**Suspensa em 2026-07-03 em favor de A28 (Report Trust)** — re-priorização do owner
(transição `current → paused`, [[ADR-234]]). Estado ao pausar: **6/10 lanes shipped**
(Regime A todo entregue: [[A26.l1]] #654 · [[A26.l6]] #660 · [[A26.l7]] #662 ·
[[A26.l8]] #666 · [[A26.l9]] #687 · [[A26.l3]] #709) + [[A26.l10]] #732; [[A26.l4]]
`in_progress` (flip default #735 ✅; resta observação ≥1 sprint). Restam **blocked por
tráfego**: [[A26.l2]] (flip strict — falta ≥20 gerações reais p/ budget `needs_review`
≤15%) e [[A26.l5]] (M2 destrutiva — G1/G2/G3 + PITR + go/no-go).

**A pausa não atrasa a A26 — acelera:** as lanes restantes esperam tráfego que só o
dogfood do owner gera, e a A28 é a máquina desse tráfego (cada iteração re-gera o
parecer E6 e exercita o override v2).

**Atualização 2026-07-08 (preparação do fechamento A26→A27):** [[A26.l2]] — o flip
strict **já está em `main`** desde 2026-07-03 (#746); medição real em curso sob
strict: 6/20 gerações, `needs_review = 0` (query na lane). [[A26.l4]] — gate estava
falso-vermelho (`v1_fallback=4`): overrides **quarentenados** seguiam casando via
hash v1 nos índices de match (violando [[ADR-282]] §5); fix + 4 testes de regressão
no PR #878; janela de observação reinicia no merge. [[A26.l5]] — runbook
"Fase E" + drafts de migration/sentinela G3 mergeados (#873). KR1 da A27
(`number_in_prose` como enforcement, [[ADR-304]]) implementado no PR #875.
Checklist do flip final (A26→`done` + A27→`current`→`done`): ~~medição l2 n≥20~~
**l2 `shipped` 2026-07-09** (emenda na lane: fechamento por evidência combinada,
contador ≥20 rebaixado a telemetria passiva — decisão do owner, sanidade PM+PE,
precedente estreito + amarrações de drift registrados) · janela l4 ≥1 sprint
verde pós-#878 · ~~decisão l5~~ **l5 CORTADA 2026-07-09** (deferida owner-gated
no plano DATA_LINEAGE, gate herdado verbatim + 4 pré-condições nomeadas na lane) · PR
editorial único com os flips de frontmatter + regeneração de índices.

- **Plano dono:** [plan/DATA_LINEAGE/_README.md](../plan/DATA_LINEAGE/_README.md) §Onda 5 ·
  **Sprint:** [sprint/A26/_README.md](../sprint/A26/_README.md) ·
  **Prompt:** [agent_prompts/orchestrator_a26_consolidacao.md](../agent_prompts/orchestrator_a26_consolidacao.md).
- **Retomada:** flip `paused → current` quando as gerações qualificadas ≥20 (reavaliar
  ao fim da A28) + observação da l4 completar 1 sprint.

### A20 — Docker dev↔prod parity + P0 production gates (`paused` 2026-05-29)

**Pausada pelo owner** após entregar o objetivo de DX: Docker como caminho opt-in de dev local (`make docker-up` sobe a stack completa numa banda de porta que coexiste com a nativa; docs SETUP/README/`make help` atualizadas). Sprint de infra dedicada, 10 lanes em 2 ondas + gate final, 7 ADRs `Proposto` (ADR-248 a ADR-254). Diagnóstico: review independente `sre-devops` 2026-05-22 (maturidade Docker 2.5/5; 5 blockers P0).

- **Entregue:** Onda A (L10 lockfile → L2 SHA pin; L3 pipeline-service non-root ∥ L6 compose dev) → Gate A → Onda B (L1 multi-stage + Playwright, L7 Makefile+SETUP, L8 driver Postgres psycopg3) + ajuste de coexistência de porta da stack dev (PR #513).
- **Trabalho residual (requer confirmação externa do owner):** L4 (GHCR token + Coolify webhook), L5 (Trivy — depende de L4), L9 (smoke gate — depende de tudo).
- **Plano:** [sprint/A20/_README.md](../sprint/A20/_README.md).
- **Retomada:** flip `paused → current` quando o owner liberar token/Coolify.

## Pickup — antes de pegar lane

1. Confirme `git fetch origin` está atualizado.
2. Veja worktrees ativos: `git worktree list`.
3. Veja branches `agent/*` recentes: `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/`.
4. Lane com slug em uso (worktree OU branch <24h): **não duplique**.
5. Slug das lanes desta sprint: **descritivo curto, kebab-case** (`a11-w2-t01`, `a11-docreorg-f1`, etc.).

## Sprints anteriores (encerradas)

| Sprint | Status | Resumo |
|---|---|---|
| A39 | done | Parse correctness (dívida de verificação E0→E2, tese `ingest-trust`) — 12 de 13 lanes shipadas (#1035–#1047+). Fechada 2026-08-04 pela abertura da [[A42]], sucessora declarada na mesma tese; l13 `cancelled` por duplicação com [[A41.l2]] e os resíduos deferidos adotados por [[A42.l9]]/[[A42.l3]] (§Fechamento do `_README`). |
| A6 | done | Migração infra+domínio (ADR-097, ADR-111). |
| A7 | done | Config DB cutover (CLI legacy removal). |
| A8 | done | Continuação multi-tenant. |
| A9 | done | Multi-front improvements. |
| A10 | done | `goals.json` cutover final ([ADR-090](../adr/090-decimal-money.md) supersedes parcial). |
| A15 | done | FU-3 imóvel financiado ([ADR-227](../adr/227-imovel-financiado-debt-aggregate-valor-mercado.md)) — 8 PRs, 2 bugs silenciosos resolvidos. Plano arquivado em [archive/IMOVEL_FINANCIADO-2026-05-20.md](../archive/IMOVEL_FINANCIADO-2026-05-20.md). |
| A16 | done | L1 ADR-235 `nu_proprietario` ([apps#388](https://github.com/davidrobert/mathoms/pull/388)) + L2 ADR-236 cascata fiscal PJ (PRs #390, #392, #393, #394, #395, #398) — ambas entregues 2026-05-21. |
| A17 | done | Informes anuais avulsos ([[ADR-238]], 4 ondas + 2 lanes extra). L1/L2/L5/L6 em mai/2026 (#402–#480); pausada 2026-05-29 ([[ADR-234]]); residual L3-L4 fechado via [[A33.l2]] (financeiro PF + Wise/PTAX — #833/#835, pós-drift #472/#489/#494) e [[A33.l4]] (proventos→S3 — #830). Fechada `done` em 2026-07-07. |
| A18 | done | Comprovantes de Bem (CRLV-e) + apólices polimórficas + FIPE refresh — 3/3 lanes shipped 2026-05-22 (#388–#436), [[ADR-239]] `Decidido`. Fechada `done` em 2026-07-01 (#707/#708; antiga l4 LGPD realocada — pertencia ao PLAN-llm-prompts-hardening, W1α fechada 2026-07-06). |
| A19 | done | Card S_PROTECAO (4º pilar AUVP) — [[ADR-240]] `Decidido` via PR #436 (extensão E6-parecer + telemetria). Fechada `done` em 2026-07-01 (#707). |
| A21 | done | Launch Trust F1 inteira (confiabilidade do número) — 9/9 lanes entregues (PRs #524–#538). Contrato `EntityDedup` (ADR-276), dedup imóveis/investimentos/previdência (ADR-277), backup/restore drill CI (ADR-275), goldens+métricas dedup. Gates F3/LGPD migram para A22; off-site/deploy permanecem owner-gated ([[ADR-228]] G2/G3). Encerrada 2026-05-31, sucedida por [[MOC-sprint-a22]]. |
| A22 | done | Launch Trust F3 (Parecer defensável) — 5/5 lanes em `main`. `l1`+`l3` de A23–A27; `l2` 7 red lines/KR7 ([[ADR-300]] `Decidido`, #690 + calibração #697–#702, `RED_LINES_VERSION 1.4`); `l5` dedup dívida + schema formal ([[ADR-301]] `Decidido`, #689); `l4` drift 5 sinais + model pin (#801); prompt-side REGRA 14 + `PROMPT_VERSION 2.1.0` (#700/#701). Pausada 2026-06-02 ([[ADR-234]]); fechada `done` retroativamente 2026-07-08 (337 testes Python + 5 React verdes; KR-a..KR-e batidos). Residual owner-gated: deploy/off-site ([[ADR-228]] G2/G3), LLM-real nightly, F1-O5 veículo (Defer). |
| A33 | done | Autonomia total (zero ações do owner) — 8/8 lanes shipped em ~20h, executada **durante a janela da A32 `current`** (precedente A27; `candidate`→`done` direto): l1 ADR-090 boundary LLM + gate float (#827) · l2+l4 fecham [[MOC-sprint-a17]] `done` (#833/#835/#850 + #830) · l5 nightly drift 4/4 PASS (#831) · l6 retenção+prune dry-run (#844) · l7 OTLP (#834) · l8 catálogo+RFB YAML (#836) · l9 services taxonomy 5 PRs + [[ADR-285]] `Decidido` (#849–#855). KR1 anti-Goodhart: nenhum gate de owner escondido. Fechada `done` em 2026-07-08. |

> Tracks por sprint disponíveis em [`docs/sprint/A6/tracks/`](../sprint/A6/tracks/), [`A7/tracks/`](../sprint/A7/tracks/), [`A8/tracks/`](../sprint/A8/tracks/), [`A11/tracks/`](../sprint/A11/tracks/), [`A12/tracks/`](../sprint/A12/tracks/), [`A16/tracks/`](../sprint/A16/tracks/), [`F7/tracks/`](../sprint/F7/tracks/), [`F9/tracks/`](../sprint/F9/tracks/), [`W5/tracks/`](../sprint/W5/tracks/), [`W6/tracks/`](../sprint/W6/tracks/). [BACKLOG](../BACKLOG.md) é apenas shim de navegação.
