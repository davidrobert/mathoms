---
id: PLAN-dogfood-report-fix
type: plan
title: "Correções de qualidade do relatório (dogfood 2026-07-11)"
status: in_progress
created_at: 2026-07-12
last_review: 2026-07-15
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
| G (re-review) | nova (Proposto) — dedup deriva chave inline | [[ADR-334]] |
| E1 (re-review) | nova (Proposto) — autonomia financeira exclui imóvel ilíquido | [[ADR-335]] |
| A (re-review) | emenda datada (E1–E4) | [[ADR-191]] |
| D (re-review) | emenda datada | [[ADR-240]] |
| F1 (re-review) | expansão in-place (4→6 predicados) | [[ADR-327]] |

## Re-review 2026-07-13 — novos P0/P1 (pós-Onda 1)

> A re-review `pipeline-review` do run `98b2cd38` / report `6848eb61` **confirmou a
> Onda 1 em `main`** e trouxe achados P0/P1 novos ou aprofundados. Cada cluster foi
> **co-desenhado por especialista + refutado por verificador adversarial** (workflow
> `dogfood-p0p1-codesign`, 2026-07-14). IDs de ADR novos = **330–335** (maior anterior
> = 329). Nomenclatura de cluster desta onda segue a tabela priorizada do relatório
> (`_scratch/pipeline-review-dogfood-2026-07-13.md`).

| Cluster | O quê | Prio | ADR | Bump | Estado / gate |
|---|---|:--:|---|:--:|---|
| **A** | Lucro PJ mal-classificado como `dividendos` (R$284k) infla TRS/IF; roteia p/ `distribuicao_pj_titular` via 2º sinal de fluxo | **P0** | [[ADR-336]] nova | none | ✅ **implementado** (PR cluster-A): TRS 14,08%→~2%; gate/estimador desacoplados (defense-in-depth/P1) |
| **C7-golden** | Golden diverge do E4 real (`receita_pj` agregado que o E4 não emite) → CI cego | **P0/P1** | [[ADR-331]] nova | none | pronto |
| **B** | Chave morta `por_fonte.receita_pj` (3 consumidores caem a 0) → `perfil_renda` falso | **P1** | [[ADR-330]] nova (contrato `por_fonte`) | schema e5 | pronto (verificado; `meses_alvo` fica 12, não 18) |
| **D** | Piso de severidade de proteção; reframe reposição de renda | **P1** | emenda [[ADR-240]] | manifest parecer 1.9 (batela com A) | pronto |
| **H1** | PII (CPF/CNPJ/matrícula) em `top_ativos[].nome` alcança o prompt do parecer | **P1** | [[ADR-332]] nova | none | pronto |
| **C1** | Aporte contado como despesa deprime poupança/score | **P1** | [[ADR-333]] | none (input, sem bump score_version) | ✅ **implementado**: `despesa_consumo` (Decimal) exclui aporte; taxa sobe; equilibrio_cerbasi = follow-up |
| **CV4** | CV4 recomputa janela errada (full vs 12m) → RED por ruído | **P1** | dobrado em [[ADR-333]] (check-espelho) | none | ✅ **implementado** (espelha janela 12m + despesa_consumo) |
| **E1** | `cobertura_despesas_meses` (18,52) mistura imóvel ilíquido com reserva (25,6) sob 1 rótulo | **P1** | [[ADR-335]] Decidido | schema e5 | ✅ **implementado** (PR #968): renomeado → `autonomia_financeira_meses`, numerador `investivel_financeiro` (sem cat_2), toggle-independente; alias deprecated 1 ciclo; relabel "Autonomia Financeira"; score sem bump (fallback = refinamento de input, ADR-217 §D3); trio E5 legado morto removido (zero-hit). Verificado real: 18,52→~9,93; reserva/progresso_if inalterados |
| **G** | Dedup de imóvel (1 matrícula 4×; ativo+excluído simultâneos) | **P1** | [[ADR-334]] nova | none (talvez migration) | **destravado** (auditoria 2026-07-14): matrícula extraível 100%; 11 rows→6 chaves derivadas (= "6 imóveis"); bug real = coluna `endereco_canonical` fragmentada (9+2 NULL) e read-path lê a coluna, não a chave derivada. Fix: derivar inline / backfill, sem fallback de endereço |
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

**Gates fechados — todos os P0/P1 destravados (2026-07-14):**

- **E1** → resolvido por `financial-planner` → [[ADR-335]] (renomear + numerador financeiro-only).
- **G** → resolvido por auditoria empírica → [[ADR-334]] (matrícula 100% extraível; bug é
  coluna persistida fragmentada, não extração; fix = derivar inline / backfill). A auditoria
  **inverteu** a hipótese original — lição: medir antes de fixar approach.

Resta apenas a **implementação** (nenhum gate de decisão aberto). Ordem recomendada:
substrato Frente 2 ([[ADR-330]]/[[ADR-331]]) primeiro — sem o golden fiel o CI segue cego à classe B.

### Revisão final do `financial-planner` (2026-07-14) — GO condicional

Revisão de domínio de todo o lote **antes** do código. **GO nos 5 clusters**; Frente 2 (B) recebeu
**GO limpo**. Condições a incorporar **na pega de cada lane** (as de A/D antes de codar aqueles clusters):

| # | Prio | Lane/ADR | Ajuste obrigatório |
|---|:--:|---|---|
| 1 | **P0** | A · emenda [[ADR-191]] | Base do estimador de 5% = `investivel_efetivo` (mesma do `if_pct`), **não** "s/ patrimônio financeiro" — senão 3ª base inconsistente (classe do erro E1). Liquidez-only já é `autonomia_financeira_meses` ([[ADR-335]]). |
| 2 | **P0** | A · emenda [[ADR-191]] | Suprimir a TRS observada **na fronteira do prompt do parecer** (não só UI); ao suprimir, narrativa **preserva** a renda passiva recorrente documentada (aluguel/dividendos), não diz "não estimável". |
| 3 | ✅ resolvido | A · [[ADR-336]] | **`ganho_capital` foi REFUTADO empiricamente** (=0 no dogfood; a hipótese da revisão final do FP não se sustentou). A inflação real são R$284k em `dividendos` = distribuição PJ mal-classificada; fix = **roteamento via 2º sinal de fluxo** (`lucros_distribuidos`, ADR-236/330), piso no match IRPF + teto no cod-09. `ganho_capital` sai do numerador como hardening separado. Follow-ups: `yield_ref` (proteção de dividendo genuíno, exige sleeve RV-BR); base do estimador `investivel_efetivo` + relabel `*_4pct` (P1 desacoplado). Lição: **verificar os buckets reais antes de codar** — o adversarial-check pegou a hipótese errada. |
| 4 | **P1** | D · emenda [[ADR-240]] | MIP trata o **gatilho**, não só o sizing: gatilho só-dívida **não** recebe piso-Alta com status MIP desconhecido (degrada p/ pergunta/médio); piso-Alta ancora em dependentes/cônjuge-sem-renda. |
| 5 | **P1** | B · [[ADR-330]] | "Excedente realocável" usa alvo **conservador** p/ perfil PJ-material (ou copy CRC de hedge). Proxy PGBL super-estima com `lucros_distribuidos` — nota já adicionada à ADR-330. |
| 6 | **P1** | C1 · [[ADR-333]] | Aporte removido do consumo deve ter **mesmo escopo de recorrência** que a receita do numerador. |
| 7 | **P2** | A/E1 · [[ADR-191]]/[[ADR-335]] | Relabelar `renda_passiva_estimada_4pct` (nome mente com taxa 5%). |

Gates de aceite adicionados pela revisão: teste de **consistência de base** (renda passiva estimada e
`if_pct` movem juntos no flip de `imoveis_no_if`); **não-vazamento ao LLM** (TRS suprimida ausente do
payload do prompt); **proteção/MIP** (financiamento grande + sem dependentes ⇒ vida não crava Alta).

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

---

## Onda R2 — 12 achados curados (pipeline-review 2026-07-15)

> Origem: `pipeline-review` do run `455b5da5` / report `91a682e8` (dogfood pós-A/B/C7/C1/E1).
> Painel de 5 dimensões + verificação adversarial: **30 brutos → 21 verificados, 9 refutados**
> (dashboard PII-scrubbed + relatório em `_scratch/pipeline-review-dogfood-2026-07-15.md`, gitignored).
> Run **verde**, conservação 15/15 — o lote anterior segurou; os defeitos migraram para
> **view-model → UI** e **inconsistências cross-superfície**. O owner curou **12** dos 21.
> Co-desenho: workflow `codesign-review-wave` (6 especialistas → síntese senior-cto → red-team,
> 2026-07-15). Touch-points verificados contra `main` (não contra worktree stale).

### Correção de premissa do red-team (ler antes de abrir lanes)

- **A fronteira de sanitização de PII é a FONTE E5, não a UI.** `top_ativos[].nome` carrega
  descrição cartorial crua + **CPF de terceiro** e é lido por **duas** superfícies: o card
  React (`Top15AtivosCard.tsx`) **e** o prompt do parecer (`parecer_planejador.yaml:147` →
  **egresso a LLM de terceiro**, o vetor de maior risco pois sai do tenant). Sanitizar no E5
  (`top_ativos_analyzer`/payload E5) é o **boundary único** que subsume PD-02 (React, [[ADR-337]])
  **e** H1 (prompt, [[ADR-332]]). **Onda 1 fecha H1** — sem isso, não fecha o gate de PII de beta.
- **Granularidade do rótulo:** na fonte E5, `imóvel → classe` **apenas** (padrão estrito
  [[ADR-332]]); enriquecimento de display (bairro/cidade) fica **downstream** só no view-model/React,
  **nunca** upstream do input do prompt (senão vaza mais PII de localização ao LLM).
- **"Manifest do parecer não bumpa / zero eval" exige PROVA, não grep.** Como CTO-02 põe role-keys
  no artefato E5 que o distiller consome, e PD-02 sanitiza no E5 (muda input do prompt): (a) teste
  de whitelist provando que role-keys **não** entram no `exec_context` do distiller; (b) orçar 1
  eval OU provar neutralidade do rótulo (texto estável no prompt). Coordenar com a lane paralela
  de parecer (C3/C4, manifest 1.8→1.9) — se as janelas coincidem, **dividir 1 eval**.
- **Emenda [[ADR-191]] colide com a lane de parecer** (C3 também emenda 191 na mesma data):
  **uma única PR de emenda 2026-07-15** cobrindo os dois refinamentos (taxa canônica 5%/4% + supressão
  da TRS observada no prompt), ou ordem explícita FP-03 → C3 relendo o frontmatter.
- **`score_version 2.0` deve reconciliar [[ADR-218]] + [[ADR-328]]** numa só definição de 2.0
  (`meses_cobertos_essencial` + plateau-em-alvo), OU deferir 218 para 3.0 — antes do PR de scoring.json.

### Decisões travadas em você (owner) — gates de execução

| # | Item | Decisão | Recomendação (co-design) |
|---|---|---|---|
| 1 | **FP-03** | TRS/meta-IF migra p/ 5% (×20), ou 4% (SWR/regra-dos-300, ×25) permanece taxa de retirada **distinta** do yield-alvo 5%? | **Manter os dois separados e rotulados:** 5% = yield-alvo/TRS (acumulação, card + estimativa de renda) · 4% = SWR/Trinity (decumulação, ×25). Colapsar em 5%/×20 superestima prontidão de IF ~20%. Registrar na emenda [[ADR-191]]. |
| 2 | **PD-02/H1** | Confirmar que o CPF na Top-15 é de **terceiro** (não da família) + grau do rótulo de imóvel no display | Confirmar; sanitizar na **fonte E5** (classe-only) fechando React+prompt; display pode ter bairro/cidade (só view-model). |
| 3 | **CTO-05** | Cascata PJ sem regime: **derivar** receita_bruta do fluxo ou **suprimir** a cascata zerada + CTA? | **Suprimir + CTA** citando o valor detectado (pro_labore ≠ faturamento PJ; derivar renderiza número enganoso). Emenda [[ADR-236]]. |
| 4 | **DE-01** | Export LGPD pode ler custo de `llm_call_log` (por-call) em vez de `pipeline_run_costs` (por-stage)? | **Consolidar em `llm_call_log`** (SSOT — já grava os 8 stages) + drop two-phase de `pipeline_run_costs`; agregação read-side só se houver tela de breakdown. Emenda [[ADR-173]]. |
| 5 | **FP-02** | Ratificar [[ADR-328]] (plateau-em-alvo + piso 3m) — pré-condição do bump `score_version 2.0` | Ratificar + reconciliar com [[ADR-218]] (ver premissa acima). |

### Ondas de execução

| Onda | Título | Itens | Gate de entrada |
|---|---|---|---|
| **R2.1** ✅ | **P0 — PII na fonte E5 (bloqueia beta)** | CTO-02 ✅, PD-02+H1 ✅, CTO-06 ✅ | [[ADR-337]]/[[ADR-338]] Proposto docs-first; owner+LGPD confirmam CPF de terceiro; **1** bump aditivo `schema_e5` (CTO-02 âncora, último a tocar o schema); gate PII-scan estendido ao **view-model E o contexto do LLM** (distiller/tool output); teste de contrato view-model↔card scaffolded; **1** manifesto de rebaseline `dev/golden_diff.py` |

> **Estado R2.1 — ✅ COMPLETA (2026-07-15):** **CTO-02** ([[ADR-338]] Decidido, PR #970) — contrato role-keyed nos 5 emissores/readers + `scripts/generate_narratives.py` (E5.N) + schema/TS/golden; teste de contrato `test_view_model_key_contract.py` (shape determinístico + zero chave com nome); ~114 testes migrados. **PD-02+H1** ([[ADR-337]] Decidido) — `top_ativos[].nome` sanitizado na **fonte E5** (imóvel→classe-only, sem descrição cartorial): fecha o vazamento de CPF de terceiro na UI **e** o egresso ao prompt do parecer; teste anti-PII red→green. **CTO-06** — flag `source_document_ids_truncated`/`consumed_document_ids_truncated` no `_report_lineage`. Próxima: **R2.2** (FP-03 emenda [[ADR-191]] TRS 5%/4% → CTO-04/PD-01/CTO-05).
>
> **Estado R2.2 — ✅ COMPLETA (2026-07-15):** **FP-03** (emenda [[ADR-191]]) + **CTO-04** (PR #972) — yield-alvo/TRS 5% × taxa de retirada segura 4% (×20 vs ×25) rotulados distintos em toda a superfície; `taxa_retirada_segura_pct` plumado no E5.N; charts/summaries relabelam a estimativa. **PD-01** (PR #973) — card "A Família" lê o contrato `{left,right}` do narrador (era `{context,conclusion}` morto → `null`), parseia `<p>` sem `dangerouslySetInnerHTML`, cláusulas condicionais (sem buracos de template). **CTO-05** (emenda [[ADR-236]], PR #973) — cascata PJ com perfil incompleto suprime número zerado, CTA cita entradas PJ detectadas (não faturamento) + sinal `perfil_incompleto_com_receita` (`CascataOutput.signals`, sem bump de schema). Próxima: **R2.3** (P2 débito — FP-02/FP-04/DE-01/DE-02; gates: `financial-planner` ratifica [[ADR-328]]+[[ADR-218]], owner confirma DE-01).
>
> **Estado R2.3 — ✅ COMPLETA (2026-07-15):** **DE-02** (emenda [[ADR-287]], PR #975) — cobertura K4 (%) instrumentada em `signals.k4_coverage_pct` + alerta (log estruturado) preservando all-or-nothing; golden +1 signal, 0 delta. **FP-02** — `financial-planner` **ratificou com ajuste** [[ADR-328]] (plateau ancora em `meses_alvo_por_perfil_renda` 6/12/18, **não** 12 fixo; piso 3m; sem penalização; prova "cobertura só sobe/flat") + [[ADR-218]] (denominador essencial **já vivo** A28.l1 — ratificação parcial fecha gap de governança; card/tabela/rename deferidos). Emendas datadas em ambas. **`score_version 2.0` IMPLEMENTADO standalone (FP-02 + FP-04)**: ao implementar, o batch coordenado se dissolveu — **FIN-01 já resolvido** (ADR-333, input fix sem bump) e **FIN-05 subespecificado** (co-design pendente, não inventar regra). Então 2.0 = só o plateau (`_cobertura_component` ancora em `reserva.meses_alvo` 6/12/18, fallback config 12; `scoring.json` 24→12) + label FP-04 morto (`media_12m_documentados`, 0-cent). [[ADR-328]] flipada `Decidido`. `golden_diff` dogfood **flat** (família over-provisioned já saturava em 10 → só `score_version` muda); testes provam nota ≥ 1.0-legacy ∀ cobertura. **FIN-05 → `score_version` 2.x própria** quando co-desenhada (2 bumps preservam [[ADR-217]] §D3; "1 bump" era otimização). **DE-01** — owner autorizou; co-design `data-engineer` + verificação adversarial (workflow 3-finders). **Fase 1** (PR #977, em auto-merge): removido o único writer de `pipeline_run_costs` (`planner_review_persistence`), SSOT = `llm_call_log`; + `dev/de01_finops_parity_audit.py` (Fase 0, read-only). **Fase 2 (drop) deferida** — owner/ops-gated: soak ≥1 mês + snapshot cold + auditoria verde em prod + migration atômica (model + allowlist LGPD + DB_SCHEMA_REFERENCE). **FP-04** ri na lane coordenada 2.0 (label `media_12m_documentados`, mesmo PR de `scoring.json`).
>
> **Estado R2.4 — 📋 DESIGN TRAVADO (2026-07-15):** **DE-03** ([[ADR-339]] Proposto) — dedup fuzzy de documento inclui declarante (informes de casal deixam de flagar duplicata). Verificação de viabilidade 2026-07-15: o `Document` **não carrega** o eixo de declarante (nem coluna, nem `classification_meta`; o CPF só aparece como `titular_ln_masked` no artefato E2 extraído, pós-dedup). "Derivar no rebuild code-only" **não é viável** — DE-03 exige **lane de write-path** (HMAC do declarante na ingestão → `classification_meta` → chave do dedup → backfill). Design travado na ADR-339; implementação quando priorizada (P3).
>
> **Balanço da onda R2 (2026-07-15):** dos 12 itens curados — **11 shipados** (PD-02, CTO-02, CTO-06 [R2.1]; FP-03, CTO-04, PD-01, CTO-05 [R2.2]; DE-02, **FP-02** (score_version 2.0 plateau), **FP-04** (label morto), DE-01-Fase1 [R2.3]); **DE-03** design travado (lane write-path, P3, não é code-only). Deferidos com gate explícito: **FIN-05** → `score_version` 2.x própria (subespecificado, co-design pendente — não confundir com FIN-01, já resolvido via ADR-333); **DE-01 Fase 2** (drop pós soak ≥1 mês / owner); **DE-03** (write-path). FIN-01 do plano original era input fix, não parte do bump de fórmula.
| **R2.2** | **P1 — consistência cross-superfície** | FP-03, CTO-04, PD-01, CTO-05 | decisão FP-03 na emenda [[ADR-191]] (serializada c/ lane de parecer) **antes** do PR de CTO-04; emenda [[ADR-236]] (CTO-05) com sign-off `financial-planner`; CTO-02 já em `main` (PD-01/CTO-04 ramificam depois); teste de contrato verde |
| **R2.3** | **P2 — score + FinOps + lineage (débito, não-bloqueante)** | FP-02, FP-04, DE-01, DE-02 | `financial-planner` ratifica [[ADR-328]]+[[ADR-218]] → destrava `score_version 2.0`; owner confirma DE-01; cadeia alembic a **um head único** |
| **R2.4** | **P3 — dedup de documentos co-declarados** | DE-03 | [[ADR-339]] Proposto; preferir derivar no rebuild (code-only) sem migration; se coluna, alembic **após** DE-01 |

**Sequência crítica:** CTO-02 (redefine o contrato view-model que PD-01/CTO-04 herdam) lidera a R2.1;
FP-03 (doc-only) trava a taxa e destrava CTO-04 na R2.2. Colisões de superfície narrativa
(`context.py`/`if_projector.py`/`charts_narrator.py`/`summaries_narrator.py`) **serializadas**:
FP-03 (taxa) → CTO-02 (role-keys) → CTO-04 (rótulo) → PD-01 (template).

### Anti-thrashing — eixos de versão (1 bump/eixo)

- **`schema_e5`** (aditivo, R2.1, **1×**): CTO-02 (role-keys, âncora) + PD-02 (campo `top_ativos[].nome`).
  **CTO-05 e DE-02 NÃO bumpam** — emitem via `signals` (objeto aberto, `e5_analysis.schema.json:37` verificado).
- **`score_version 1.0-legacy→2.0`** (R2.3, **1×**): FP-02 (carona na [[ADR-328]] ainda Proposto, não-shipada; reconciliar [[ADR-218]]). FP-04 pega o **mesmo PR** de `scoring.json` **sem** bump (label morto).
- **`migration_alembic`**: DE-01 (drop two-phase `pipeline_run_costs`, R2.3) → DE-03 (só se coluna `declarante_ref`, R2.4, head após DE-01).
- **`manifest parecer`**: **0 bump** condicional à prova de whitelist (role-keys fora do `exec_context`) + neutralidade/eval de PD-02 (ver premissa).

### Colisões de arquivo (serializar — nunca paralelizar intra-onda)

- `config/schemas/e5_analysis.schema.json` → CTO-02 (âncora) + PD-02 · **1** bump, último PR da R2.1.
- `backend/tests/snapshots/dogfood_view_model.json` (golden compartilhada) → **1** manifesto `dev/golden_diff.py` por onda: R2.1={CTO-02,PD-02,CTO-06} · R2.2={PD-01,CTO-04,CTO-05} · R2.3={FP-02,DE-02}.
- `config/scoring.json` + `financial_score_calculator.py` → FP-02+FP-04 no **mesmo** PR (R2.3); o `financial_score_calculator.py` batela no **mesmo** 2.0 de C5/FIN-05/FIN-01 (que **conformam** ao 2.0, não co-bumpam).
- Superfície narrativa → serializar por dependência (acima).
- `report_lineage.py` (CTO-06) × `e5_lineage.py` (DE-02) → **arquivos distintos** (API count vs domínio K4); só compartilham a golden → resolvido por separação de onda.

### ADRs da onda

| Item | Ação | ADR |
|---|---|---|
| PD-02 | nova Proposto — rótulo de exibição sem PII na fonte E5 (irmã de 332, React+prompt) | [[ADR-337]] |
| CTO-02 | nova Proposto — contrato role-keyed no view-model (nome só em valores; fecha follow-up [[ADR-176]]) | [[ADR-338]] |
| DE-03 | nova Proposto — dedup fuzzy de doc inclui declarante (HMAC/member_id, nunca CPF cru) | [[ADR-339]] |
| FP-03 | emenda datada — override 5% (yield) × 4% (SWR ×25) distintos | [[ADR-191]] |
| CTO-05 | emenda datada — suprimir cascata PJ zerada + CTA | [[ADR-236]] |
| DE-01 | emenda datada — `llm_call_log` como SSOT de FinOps + deprecar `pipeline_run_costs` | [[ADR-173]] |
| DE-02 | emenda datada — instrumentação de cobertura K4 + degradação graciosa | [[ADR-287]] |
| FP-02 | conforma in-place (+ reconciliar 218) | [[ADR-328]] |
| FP-04 | conforma (label `media_12m_documentados`) | [[ADR-306]] |
| CTO-06 | conforma (`source_document_ids_truncated`) | [[ADR-281]] |
| CTO-04 | conforma à emenda [[ADR-191]] de FP-03 | — |
| PD-01 | sem ADR — bug de contrato left/right × context/conclusion | — |

### Aceite por item (4 lentes — resumo)

- **CTO-02** — Compl: `rg`/walk zero-hit de chave de dict com token de nome (3 blocos: patrimonio, reserva.composicao_liquida, goals/cenarios). Corr: role-keys presentes, valores em cents idênticos ao pré-fix. Consist: 2 conjuntos de nomes → key-set idêntico + TS declara essas keys. Prec: golden só rename de chave, 0 delta de cents.
- **PD-02+H1** — Compl: nenhum slot/prompt emite CPF/CNPJ/matrícula/IPTU/endereço de terceiro (view-model **e** `exec_context` do LLM). Corr: rótulo classe-only na fonte, valor monetário preservado. Consist: mesmo abstrator em React e prompt. Prec: teste sem regex de PII em `top_ativos[].nome` e no contexto do distiller.
- **CTO-06** — Compl/Prec: `source_document_ids_truncated` explícito; `make update-openapi-snapshot`.
- **FP-03** — Compl: 5% e 4% rotulados distintos em toda superfície. Corr: meta-IF documenta ×20 vs ×25. Consist: card ↔ regra de sugestão não se contradizem. Prec: emenda [[ADR-191]] registra o override.
- **CTO-04** — Corr/Consist: rótulo == taxa que gerou o valor; observada × estimada rotuladas.
- **PD-01** — Compl: card renderiza; cláusulas condicionais (sem "é ()"/"0 gatos"). Corr: `<p>` parseado, sem `dangerouslySetInnerHTML`. Prec: conforma ao teste de contrato de shape.
- **CTO-05** — Corr: sem número tributário enganoso; sinal `perfil_incompleto_com_receita` (signals aberto, sem bump). Consist: seção fiscal não contradiz R$1M de PJ.
- **FP-02** — Corr: interpolação ancorada a `meses_alvo` do perfil. Consist: bump 2.0 reconcilia 218+328. Prec: `golden_diff` de score documentado 1×.
- **FP-04** — Prec: label `media_12m_documentados`; `golden_diff`=0 cents (label morto).
- **DE-01** — Compl: FinOps por (run,stage) reflete 100% do gasto (via `llm_call_log`). Consist: budget hard-stop inalterado. Prec: migration two-phase reversível; export LGPD repontado.
- **DE-02** — Compl: cobertura K4 (%) por run instrumentada + alerta. Prec: degradação graciosa preserva all-or-nothing (`member_hashes=[]` em partial).
- **DE-03** — Compl: informes de casal não flagam duplicata. Prec: discriminador HMAC/member_id, nunca CPF cru, nunca em `content_hash`.
