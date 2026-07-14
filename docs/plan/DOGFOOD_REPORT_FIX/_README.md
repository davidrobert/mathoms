---
id: PLAN-dogfood-report-fix
type: plan
title: "Correções de qualidade do relatório (dogfood 2026-07-11)"
status: in_progress
created_at: 2026-07-12
last_review: 2026-07-14
adrs_canonical:
  - "[[ADR-326]]"
  - "[[ADR-327]]"
  - "[[ADR-328]]"
  - "[[ADR-329]]"
tags:
  - type/plan
  - status/in-progress
  - area/pipeline
  - area/backend
  - area/report
---

# Correções de qualidade do relatório — dogfood

> Origem: revisão profunda do run `22fa587e` / report `1457b67d` (workspace dogfood
> 5@5.com, 2026-07-11), com painel multi-agente + verificação adversarial. O pipeline
> executa limpo; o **relatório** concentra os defeitos. Este plano cobre o subconjunto
> priorizado pelo owner: **C2, C3, C4, C5, C7, C8, C11**. Findings brutos e dashboard da
> revisão em `_scratch/dogfood-review-2026-07-11.md` (gitignored).

## Reconciliação de premissa (ler antes de abrir lanes)

- **Única dependência dura intra-lote:** **C3 ↔ C4** (editam o mesmo
  `config/prompts/parecer_planejador.yaml` + exigem bump de manifest + eval).
- **C7 e C8 são folhas independentes** — nenhum bloqueio de build.
- O acoplamento de score do **C5** é com **FIN-05** (diversificação) + **FIN-01**
  (input de poupança) — ambos do cluster C1, **fora deste lote**. O bump de
  `score_version` deve batelá-los ([[ADR-328]]).

### Decisões de domínio (owner + financial-planner)

> **Atualizado 2026-07-14** pela re-review `pipeline-review` do run `98b2cd38` /
> report `6848eb61` (pós-Onda 1). O owner travou 3 decisões; 2 seguem abertas (P2).

**Travadas 2026-07-14:**

1. ✅ **TRS canônica = 5%** (meta IF atual). O owner **sobrepôs** a recomendação
   FIN-005 (4% · regra dos 300) — afeta C3 + cluster A. A emenda [[ADR-191]] deve
   registrar o override + rationale explicitamente (não silenciar a alternativa).
2. ✅ **Lucro distribuído da PJ do titular = renda ativa de negócio** (não passiva).
   Rotear `por_fonte.lucros_distribuidos` → `passive_income.distribuicao_pj_titular`,
   fora de `passive_income.dividendos`. Gate do **cluster A (P0)**.
3. ✅ **Aporte de investimento = transferência para balanço** (não consumo). Sai de
   `desp_bruto`; conservação exige que o valor reapareça no balanço. Gate do
   **cluster C1 (P1)**.

**Ainda abertas (P2 — não bloqueiam o lote P0/P1):**

4. **Base canônica de concentração imobiliária:** 63,4% (carteira) vs 67,2% (bruto) —
   afeta C11-Fase2 / emenda [[ADR-177]] + reconciliação com FIN-05.
5. **Tendência do gauge (C2.2):** nasce no E5.N ou na camada `comparisons`?
   (recomendação: `comparisons`, onde há baseline; FIN-010: derivar de snapshots datados).

## Regra de ouro — 3 eixos de versão, 1 bump cada (anti-thrashing)

Cada bump re-invalida cache/goldens e força re-eval (~US$ 12/run no parecer).
**Proibido bumpar por item.**

- **Manifest do parecer** `1.8→1.9`: C3 + C4 + C11-parecer → 1 PR-sequência, 1 eval.
- **`score_version` `1.0-legacy→2.0`**: C5 + FIN-05 + FIN-01 ([[ADR-328]]; [[ADR-217]] §D3 exige sucessora).
- **Schema E5** (`config/schemas/e5_analysis.schema.json`): C8 + C11 + C3 + C5 → 1 bump aditivo, no último PR.

### 4 superfícies de colisão (serializar — nunca paralelizar dentro delas)

- **A · Parecer:** `parecer_planejador.yaml`, `parecer_distiller.py`, `parecer_pos_llm_guardrails.py` (C3, C4, C11-parecer).
- **B · Score:** `financial_score_calculator.py`, `config/scoring.json` (C5, FIN-05, FIN-01).
- **C · Narrativa:** `scripts/generate_narratives.py`, `pipeline/domain/services/narrativas/*` (C2.1–C2.4, C11-narrativa).
- **D · Schema/serialização:** `e5_serialization.py`, `e5_analysis.schema.json` (C3, C5, C8, C11).

## Ondas de execução

### Onda 0 — Docs (bloqueante)
Abrir ADRs `Proposto` (§ADRs) + sign-off `financial-planner` (C5, C11-F2) + travar as 3 decisões.
**Estado:** [[ADR-326]] (C7), [[ADR-327]] (C2.5), [[ADR-328]] (C5), [[ADR-329]] (C8) abertas `Proposto`.
Emendas C3/C4/C11 a abrir na pega da lane, após travar a decisão de domínio correspondente.

### Onda 1 — Folhas, sem bump de versão (quick wins, lanes paralelas)

| Item | O quê | Effort | Risco | ADR |
|---|---|:--:|:--:|:--:|
| **C7** | Popular `reports.score`/`patrimonio_liquido` na criação + `--backfill-columns` | S | Baixo | [[ADR-326]] |
| **C2.1–C2.4** | Narrativa: religar a campos vivos, matar placeholders/PII, remover tendência falsa | M | Médio | — |
| **C11-Fase1** | Rotular cada % de imóvel com sua base; corrigir `conclusionUtils` "líquido→bruto" | S | Médio | — |
| **C5-Camada1** | Card "excedente realocável ~R$ 417k"; unificar custo essencial | M | Baixo | — |
| **C8** | `RETRIABLE_SKIP_REASONS` + retry de docs parkados no início do run premium | M | Médio | [[ADR-329]] |

### Onda 2 — Bumps únicos + guardas

| Item | O quê | Bump | ADR |
|---|---|:--:|:--:|
| **C3 + C4** | 1 lane parecer: TRS suspeita suprime observado (C3) + piso de severidade proteção (C4) | manifest 1.9 + 1 eval | emenda [[ADR-191]] + [[ADR-240]] |
| **C5-Camada2** | Plateau da nota de cobertura em `meses_alvo` | `score_version 2.0` (c/ FIN-05+FIN-01) | [[ADR-328]] |
| **C2.5 + C2.6** | Guarda pós-geração (binding token→campo vivo, fail-closed) + golden/eval | — | [[ADR-327]] |

### Onda 3 — Métrica canônica (gated por sign-off)

| Item | O quê | ADR |
|---|---|:--:|
| **C11-Fase2** | Campo canônico `ratios.concentracao_imobiliaria` lido bit-a-bit por doughnut/S3/parecer; reconciliar FIN-05 | emenda [[ADR-177]] |

## ADRs

| Item | Formato | ADR |
|---|---|---|
| C7 | nova (Proposto) | [[ADR-326]] |
| C2.5 | nova (Proposto) | [[ADR-327]] |
| C5 | nova (Proposto, sucessora [[ADR-217]] §D3) | [[ADR-328]] |
| C8 | nova (Proposto, emenda semântica [[ADR-081]]) | [[ADR-329]] |
| C3 | emenda datada | [[ADR-191]] |
| C4 | emenda datada | [[ADR-240]] |
| C11 | emenda datada | [[ADR-177]] |
| B (re-review) | nova (Proposto) — contrato `por_fonte` | [[ADR-330]] |
| C7-golden (re-review) | nova (Proposto) — fidelidade fixture↔E4 | [[ADR-331]] |
| H1 (re-review) | nova (Proposto) — sanitização PII no parecer | [[ADR-332]] |
| C1 (re-review) | nova (Proposto) — aporte transferência (irmã [[ADR-328]]) | [[ADR-333]] |
| G (re-review) | nova (Proposto, reservada — gated por auditoria) | [[ADR-334]] |
| A (re-review) | emenda datada (E1–E4) | [[ADR-191]] |
| D (re-review) | emenda datada | [[ADR-240]] |
| F1 (re-review) | expansão in-place (4→6 predicados) | [[ADR-327]] |

## Re-review 2026-07-13 — novos P0/P1 (pós-Onda 1)

> A re-review `pipeline-review` do run `98b2cd38` / report `6848eb61` **confirmou a
> Onda 1 em `main`** e trouxe achados P0/P1 novos ou aprofundados. Cada cluster foi
> **co-desenhado por especialista + refutado por verificador adversarial** (workflow
> `dogfood-p0p1-codesign`, 2026-07-14). IDs de ADR novos = **330–334** (maior anterior
> = 329). Nomenclatura de cluster desta onda segue a tabela priorizada do relatório
> (`_scratch/pipeline-review-dogfood-2026-07-13.md`).

| Cluster | O quê | Prio | ADR | Bump | Estado / gate |
|---|---|:--:|---|:--:|---|
| **A** | Lucro PJ roteado p/ dividendo infla renda passiva/IF; gate "suspeito" **suprime** o observado e ancora IF a 5% s/ patrimônio financeiro | **P0** | emenda [[ADR-191]] (E1–E4) | manifest parecer 1.9 | pronto (core verificado; correções aplicadas) |
| **C7-golden** | Golden diverge do E4 real (`receita_pj` agregado que o E4 não emite) → CI cego | **P0/P1** | [[ADR-331]] nova | none | pronto |
| **B** | Chave morta `por_fonte.receita_pj` (3 consumidores caem a 0) → `perfil_renda` falso | **P1** | [[ADR-330]] nova (contrato `por_fonte`) | schema e5 | pronto (verificado; `meses_alvo` fica 12, não 18) |
| **D** | Piso de severidade de proteção; reframe reposição de renda | **P1** | emenda [[ADR-240]] | manifest parecer 1.9 (batela com A) | pronto |
| **H1** | PII (CPF/CNPJ/matrícula) em `top_ativos[].nome` alcança o prompt do parecer | **P1** | [[ADR-332]] nova | none | pronto |
| **C1** | Aporte contado como despesa deprime poupança/score | **P1** | [[ADR-333]] nova (irmã [[ADR-328]]) | score_version 2.0 | pronto |
| **CV4** | CV4 recomputa janela errada (full vs 12m) → RED por ruído | **P1** | dobrado em [[ADR-333]] (check-espelho) | none | pronto (independe de FIN-01) |
| **E1** | `cobertura_despesas_meses` (18,52) usa investível c/ imóvel ilíquido vs 25,6 | **P1** | ⚠️ **sem ADR ainda** | schema e5 | **BLOQUEADO** — `pontos_fortes_analyzer.py:224` é consumidor vivo (renderiza "Colchão Patrimonial"); é decisão de **produto** (renomear, não remover) → `financial-planner` |
| **G** | Dedup de imóvel (1 matrícula 4×; ativo+excluído simultâneos) | **P1** | [[ADR-334]] nova (reservada) | migration Alembic | **BLOQUEADO** — mecanismo `_extract_matricula` provavelmente não casa o fantasma; exige **auditoria empírica** da taxa de extração de matrícula nas rows do dogfood antes de fixar approach |
| **F1** | Narrativa `s9` "nenhum risco" contradiz `pontos_urgentes` Alta; `s6` soma não fecha | **P1** | expandir [[ADR-327]] in-place (4→6 predicados) | none | **BLOQUEADO-on-327** — CV15/módulo de predicados/guarda da ADR-327 ainda não existem; serializar F1 após a impl da 327 (metade de conteúdo `s9`/`s6` é landável antes) |

**Correções cross-cutting da verificação adversarial (aplicar em toda a onda):**

- **CV15 já está reservado** pela [[ADR-327]] (linha "guarda espelhada como CV15"). CVs
  novos desta onda entram em **CV16+** (`validate_cross.py` ~:390, registro em
  `_CV_ALWAYS_CHECKS` :403).
- **`ADR-272` foi mal-citado** como fonte da conservação em todo o material de origem —
  ADR-272 é "needs_review razão estruturada". A invariante de conservação E5 vive em
  `tests/test_e5_conservation_invariants.py` (A23.l2 guard-rail G-b). Usar a fonte certa
  nas ADRs e testes.
- **`backend/tests/snapshots/dogfood_view_model.json` é golden mutável compartilhada** por
  vários clusters (C7-golden/B/C1 + C8/C11/C3/C5) — **serializar rebaseline** com manifesto
  `dev/golden_diff.py` único e ordem coordenada, senão conflito de merge + baselines duplicadas.
- **Gate de completude = visitor AST** chaveado no dict de origem (`por_fonte` /
  `por_fonte_detalhado` / `receita_totals` / `despesa_totals` + acesso encadeado
  `fluxo.get("por_fonte",{}).get(...)`), **não** scan de nomes de variável — senão não pega
  `previdencia_analyzer.py:215` nem `tributario_input_builder.py:151`.

**Gates a fechar antes de destravar E1 e G:**

- **E1 → `financial-planner`**: decidir se "Colchão Patrimonial" (autonomia patrimonial,
  A28.l10) é **renomeado** (nome honesto p/ o conceito de colchão) ou mantido+relabelado — a
  correção de consistência é desambiguar nomes de campo, **não deletar** um KPI renderizado.
- **G → auditoria empírica**: medir a taxa real de extração via `_extract_matricula` nas 11
  rows vivas de `property_identity` do dogfood (em cópia do DB) e registrar o número na
  [[ADR-334]] como evidência — nunca "assumir 100%". Prever 2ª chave estruturada (endereço
  normalizado) para o fallback quando matrícula ausente.

## As 4 qualidades como gates verificáveis

- **Completude** → `rg` zero-hit de referência morta (`pat.get('investivel'`,
  `por_fonte.get('receita_pj'`, `processed/E3_reconciled`) + enumeração de
  consumidores (teste falha se um ficar de fora) + contagem de estado
  (`COUNT(*) WHERE ... NULL = 0`).
- **Corretude** → golden de execução **red-antes-de-green** (fixture do shape do
  run `22fa587e` que falha pré-fix, passa pós) + conservação sem regressão
  (tolerância zero) + `Decimal` exato ([[ADR-090]]).
- **Consistência** → gate cross-surface bit-a-bit (% igual em doughnut==S3==parecer)
  + guarda [[ADR-327]] espelhada como `CV15` em `validate_cross.py` + eval do parecer.
- **Precisão** → `dev/golden_diff.py` (diff em cents) + erro cita `slot+dot.path+valor`
  + thresholds de config (não hardcode) + schema strict no CI para blocos novos.

## Aceite por item (4 lentes) e touch-points

Cada item leva critério de aceite nas 4 lentes; touch-points file:linha estão nas
ADRs (itens com ADR) e no design multi-agente de origem. Resumo por item:

- **C7** — Compl: 2 construtores + backfill dos 59 + 4 consumidores. Corr: `score`=6,3 (0–10), `patrimonio_liquido`=Decimal(18,2). Consist: coluna == view-model E5. Prec: 0/59 NULL pós-backfill. ([[ADR-326]])
- **C2.1** — Compl: 3 reads mortos + todos consumidores. Corr: investível=`investivel_efetivo`, receita_pj>0, USD real. Consist: "investível (X% da meta)" = `goals.if_pct` (24,94%). Prec: golden mostra só os slots que saíram de R$0.
- **C2.2** — Compl: nenhum verbo de tendência incondicional (v1+v2). Corr: verbo casa com `delta_signal`; sem baseline ⇒ sem comparação. Consist: caption ↔ changelog. Prec: teste 43,05→14,19 ⇒ "queda".
- **C2.3** — Compl: nenhuma cláusula com var vazia; dead-USA removido. Corr: campo ausente ⇒ omite. Consist: perfil só afirma o que o DB tem. Prec: teste "só-nome" sem "é ()".
- **C2.4** — Compl: nenhum slot emite CNPJ/matrícula/IPTU/endereço. Corr: rótulo abstraído preservando valor. Consist: mesmo abstrator em toda superfície. Prec: teste sem regex de PII.
- **C2.5/C2.6** — ver [[ADR-327]].
- **C3** — Compl: flag suspeito gateia goals+passive+parecer+cobertura. Corr: TRS observada 14,08% > threshold ⇒ só estimativa a **5%** (s/ patrimônio financeiro, sem lucro PJ) + aviso. Consist: mesmo veredicto det↔parecer↔narrativa; `if_pct` inalterado. Prec: threshold de `RentabilidadeConfig` (config, não hardcode). *(TRS travada 5% em 2026-07-14; R$ concreto recomputado no fix.)*
- **C4** — Compl: 3 apólices sem truncar; risco+campos_faltantes+pontos_urgentes coerentes. Corr: "falta VIDA/invalidez", severidade ≥Alta. Consist: severidade parecer == `pontos_urgentes`. Prec: S9 scalar→table; alias de path.
- **C5** — ver [[ADR-328]]; Camada1 (card+custo) sem ADR.
- **C8** — ver [[ADR-329]].
- **C11** — Compl: 4 origens + todas superfícies; card morto excluído. Corr: cada % com (num,den) real; fallback "líquido"→"bruto". Consist: mesmo campo canônico bit-a-bit. Prec: rótulo cita base literal. (Fase2: emenda [[ADR-177]].)

## Quick wins (payoff decrescente)

1. **C7** (S, zero-dep) — ressuscita feature morta (meta IF em 3 telas). Melhor ROI.
2. **C11-Fase1** (S) — mata a confusão dos 3 percentuais só com rótulos.
3. **C2.3** (Baixo) — remove prosa constrangedora.
4. **C5-Camada1** — corrige a "celebração" errada da reserva.
5. **C2.1** (M, raiz) — R$0/PJ0%/US$0 → valores vivos; desbloqueia C2.5/C2.6.

Pesados (cauda): **C3** (regra de domínio + eval) e **C11-Fase2** (emenda [[ADR-177]] + sign-off).
