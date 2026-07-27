---
id: PLAN-pipeline-review-r2
type: plan
title: "Pipeline Review r2 — remediação dos achados sistêmicos (run 9d47574c, ws-1b9f2cf5)"
status: in_progress
created_at: 2026-07-27
last_review: 2026-07-27
sprint_origem: A39
sprint_atual: A39
sprints_envolvidas: [A39]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-343]]"
relates_to:
  - "[[PLAN-ledger-integrity]]"
tags:
  - type/plan
  - status/in-progress
  - area/pipeline
  - area/backend
---

# Pipeline Review r2 — remediação

> Origem: skill `pipeline-review` ([[ADR-343]]), run `9d47574c` em origin/main #1089,
> registrado em [[PIPELINE-REVIEWS-active]] §r2 (PR #1091). 25 achados sistêmicos
> acionáveis (26 − RV2-01, **parkado por decisão do owner**). Síntese crua + baseline:
> `storage/1b9f2cf5-…/reviews/20260727-1835-9d47574c/` (off-git, PII).

## Princípio de execução (decisão senior-cto)

1. **Conformance-first.** A maioria dos achados é **gap contra ADR já Decidida** — implementar à conformidade, **sem reabrir a decisão** (CLAUDE.md §"não delegue para… mudança que apenas conforma a ADR existente"). Poucos exigem ADR novo.
2. **Colisão-zero.** RV2-02/05/17 (gate/conservação) pertencem ao workstream **ATIVO** [[PLAN-ledger-integrity]] / [[ADR-347]] (A39) + [[ADR-342]] (amendada 2026-07-27), com worktrees vivos. **Não abrir PR concorrente** — registrar como follow-up e sinalizar aos donos.
3. **Ordem:** correção/domínio → contrato → citação (com eval) → UX. Relatório errado corrói confiança antes de qualquer refinamento.

## Ondas

### Onda A — domínio (conformance a ADR decidida)

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-03 | nota PGBL "teto atingido" sem branch por `PgblStatus` · `previdencia_analyzer.py:168-176` | [[ADR-305]] | conformance | 🚧 em execução |
| RV2-08 | `exposicao_cambial` omite bucket Internacional · `exposicao_cambial_analyzer.py` | [[ADR-193]] · [[ADR-224]] | conformance | aberto |
| RV2-19 | aluguel IRPF vs banco (bases distintas) sem disclosure | [[ADR-306]] | conformance | aberto |
| RV2-26 | `premio_decomposicao` 100% "auto" apesar de apólice multi-bem | — | fix | aberto |
| RV2-21 | `diagnostico_comportamental` sem degradê por cobertura de categorização | — | fix | aberto |
| RV2-15 | `cenarios_conjuge` unidimensional + retorno vs meta | — | fix | aberto |
| RV2-18 | cascata `perfil_incompleto` sem nudge PJ + detecção PJ inconsistente | [[ADR-268]] | fix | aberto |
| RV2-20 | `premissas_economicas` global vazia p/ o período (seed) | — | config | aberto |

### Onda B — contrato do view-model E5 (1 ADR novo + refactor)

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-06 | money/pct string vs number no E5 | [[ADR-090]] | conformance | aberto |
| RV2-07 | PII como CHAVE de dict em `fluxo_caixa.por_fonte_detalhado` | [[ADR-332]] | conformance + contrato | aberto |
| RV2-12 | `alertas[]` top-level dead field + alertas de imóvel sem surface global | [[ADR-129]] | contrato novo | aberto |
| RV2-14 | `_report_lineage` truncado + ID scheme incompatível | [[ADR-278]] | fix | aberto |
| RV2-22 | `pipeline_run_costs` dead schema (drop) | [[ADR-173]] | cleanup | aberto |

Co-design: `data-engineer` + `product-designer`. ADR novo de **contrato do view-model E5** (money=number, id estável, sem PII-key, shape de alertas).

### Onda C — citação do parecer (inclui RV2-01, desparkado 2026-07-27)

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-10 | riscos citam % na prosa com `ancoras=[]` fora do verify | [[ADR-304]] | extensão (R$→%) | aberto |
| RV2-11 | `evidencia_verification.item_index` out-of-range vs `riscos[]` | [[ADR-293]] | fix | aberto |
| RV2-09 | parecer rotula `receita_pj_pct` como "% da receita" (base trocada) | — | exec-context | aberto |
| RV2-24 | limiar de poupança 30% (parecer) vs 25% (E5) | [[ADR-143]] | fonte única | aberto |
| RV2-25 | `field_request_spurious` p/ `[]` (null-semantics) | — | fix | aberto |
| RV2-01 | parecer FABRICA métrica em `metricas[]` (valor não derivável de nenhum campo E5); itens sem âncora escapam do verify (`parecer_evidencia.py::_iter_items` só itera riscos+sugestões) | [[ADR-304]] | ADR novo / extensão | aberto |

Co-design: `prompt-engineer` + golden eval. **RV2-01 desparkado (2026-07-27, pedido do owner)** — incluído: âncora `$.path` obrigatória em `metricas[]` + estender o loop de verificação de citação a `metricas[]`; eval golden anti-fabricação (temp=0).

### Onda D — plano de ação & identidade

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-04 | parecer `sugestoes_*` não consolidam em `tarefas[]` | — | contrato | aberto |
| RV2-13 | identidade de imóvel fragmentada (property_id divergente) | [[ADR-246]] | conformance | aberto |
| RV2-23 | `needs_review` pós-completed sem surface no view-model | — | fix | aberto |

## Coordenado — NÃO abrir PR aqui (workstream ativo)

| Achado | Onde vive | Ação |
|---|---|---|
| RV2-02 | `extract_with_llm` success mascara skip → **[[ADR-342]]** (anti-silêncio E2) | verificar cobertura; se gap, follow-up ao dono do ADR-342/e2-antisilence |
| RV2-05 | CV16/CV17 fora do gate de conservação → **[[ADR-347]]** / [[ADR-330]] / [[ADR-336]] | escopo do gate é decisão A39; propor CV17 no gate como follow-up ao ADR-347 |
| RV2-17 | ledger de contagem E2→E4 → **[[ADR-347]]** (Proposto) / [[PLAN-ledger-integrity]] | já é o escopo do plano ativo — não duplicar |

## Parkado

- _(vazio)_ — **RV2-01 desparkado em 2026-07-27** por pedido do owner → movido para a Onda C. Nada permanece parkado.

## Critério de aceite (por onda)

- **Cada fix:** teste de regressão ANTES do fix (bug reproduzido), conformidade ao ADR citado, `pre-commit` verde, sem PII, PR squash com CI verde.
- **Onda B/C:** ADR novo/estendido referenciado no PR, flip `Decidido` no merge; eval golden na Onda C.
- **Coordenado:** zero PR concorrente; follow-ups registrados nos ADRs donos.

## Decisões de co-design — Onda A (2026-07-27)

> Co-design 5/6 (RV2-18 pendente de retry) · financial-planner + data-engineer. Racional
> completo off-git em `storage/1b9f2cf5-…/reviews/20260727-1835-9d47574c/ondaA_codesign.json`.
> **3 dos 5 exigem ADR novo** → Onda A = ~5 PRs substanciais (cada um com ADR Proposto onde marcado + co-design já feito), **não** conformance trivial.

- **RV2-08** (conformance [[ADR-224]] + **emenda datada**): bug de binding em V1 (`exposicao_cambial_analyzer.py`) **E** V2 (`exposicao_cambial_v2.py`) — leem `valor`/`valor_31_12` (campo real = `valor_atual`, `investments_consolidator.py:426`) e ticker errado. Fix: (1) value chain `valor_atual→valor_total→valor_31_12`; (2) ticker `ticker_norm` p/ match de catalog em V2; (3) lastro per-position via `lastro_resolver` (nunca moeda de negociação); (4) **não** somar `tabela_classes[Internacional]` (fonte errada); (5) V2 é fonte de verdade, V1 só instant-render — wire `workspaceId` no PDF server-side. Emenda [[ADR-224]] documentando o contrato de campos da posição E4.
- **RV2-19** (conformance [[ADR-306]]): **manter** base IRPF-declarada (conservadora, correta p/ dependência); acabar com uso silencioso — bloco `aluguel_divergencia` quando divergência ≥25% & janela ≥6m; cobertura reporta faixa (irpf + recorrente); parecer modula severidade pela faixa (D7 estende de defasagem-temporal p/ divergência-de-valor).
- **RV2-26** (**ADR novo**): decompor prêmio por COBERTURA (bottom-up), não por bem-dominante. cobertura→chave {auto,residencial,vida,saude,ap}; peso = Σ cobertura.premio_brl; reconciliar por apólice. Invariante: Σ premio_decomposicao == premio_total (cent-exato).
- **RV2-21** (**ADR novo**): condicionar densidade/confiança do `diagnostico_comportamental` a `nao_identificado_share_pct` (ancora em `NAO_IDENTIFICADO_THRESHOLD_PCT`); campo `confianca` (alta|parcial|insuficiente); 3 tiers (≤10% alta / 10–30% parcial+caveat+item de atenção / >30% zero item comportamental).
- **RV2-15** (**ADR novo**): `cenarios_conjuge` emite **exatamente 2** cenários quando gate [[ADR-167]] True: "Renda atual do casal" (base, aporte cheio) + "Sem renda do cônjuge" (estresse, aporte ×0.66); retorno ancorado numa fonte única (base == IF realista). Sem upside/renda-parcial (fabricaria fator sem dado grounded).
- **RV2-18** — co-design falhou (structured-output retry cap); **re-rodar** antes de implementar.

## Retomada (prompt de execução — sessão fresca)

> Cole numa sessão Claude Code fresca **no checkout principal** (serviços API+Celery+Redis de pé). Este plano é o spec; execução é **1 PR por fix**.

**Missão.** Executar a remediação restante do pipeline-review r2 — Ondas A(resto)/B/C/D **+ RV2-01** (desparkado) — como PRs pequenos, 1 por achado, cada um verde no CI e mergeado por auto-merge squash. **NÃO** tocar RV2-02/05/17 (workstream ativo A39; coordenar/follow-up em [[ADR-342]]/[[ADR-347]], **sem PR concorrente**).

**Ordem sugerida.** (1) **RV2-18** — re-rodar o co-design (data-engineer) que falhou: detecção PJ `cascata=0.0` vs `reserva=58,67` + nudge de perfil ([[ADR-268]]). (2) **ADR-novo** (1 ADR Proposto + 1 PR cada): **RV2-26** (prêmio por cobertura), **RV2-21** (confiança do diagnóstico por cobertura de categorização), **RV2-15** (2 cenários do cônjuge), **RV2-01** (âncora `$.path` em `metricas[]` + verify + eval anti-fabricação). (3) **RV2-19** (guardrail de aluguel, conformance [[ADR-306]]). (4) **Onda B** — contrato do view-model E5 (RV2-06/07/12/14/22): 1 ADR novo de contrato, co-design `data-engineer`+`product-designer`. (5) **Onda D** (RV2-04/13/23). **RV2-08 §E** (wire `workspaceId` no PDF server-side) é follow-up.

**Decisões prontas.** Onda A co-designada (5/6) em `## Decisões de co-design — Onda A` acima; racional bruto off-git em `storage/1b9f2cf5-…/reviews/20260727-1835-9d47574c/ondaA_codesign.json`. Demais ondas: **co-designar antes de codar** (regra de domínio/contrato/prompt → especialista; CLAUDE.md §delegação).

**Disciplina por fix.** conformance-first (não reabrir ADR decidida); **ADR Proposto ANTES do PR** para os de ADR-novo; **teste de regressão ANTES do fix** (reproduz o bug); função ≤20 linhas; `pre-commit run --all-files` verde; zero PII no git.

**Gotchas desta execução.** (a) **Nunca** pipe `git commit` por `| tail` — engole a falha do hook; rode direto e confira `git log -1`. (b) Novo plano/ADR desincroniza `docs/_MOC/_generated/` → `python3 dev/build_doc_index.py --inline` + `git add`. (c) hook `code-style-baseline` falha se função nova >20 linhas (P1) — extraia helper, não `--save-baseline`. (d) auto-merge rápido deleta a branch → re-push vira "new branch" com commits órfãos pós-squash; sempre branch nova `off origin/main` + cherry-pick só o commit novo. (e) emenda de ADR exige `amended_at` no frontmatter + blockquote de sinal. (f) pipeline vs backend têm conftests que colidem — rode `pytest tests` e `pytest backend/tests` **separados**.

**Estado.** RV2-03 (PR #1092, merged) + RV2-08 (PR #1094) entregues. Memória de sessão: `project_pipeline_review_r2_remediation` (fora do vault); MOC dos achados: `docs/_MOC/PIPELINE-REVIEWS-active.md` §r2.
