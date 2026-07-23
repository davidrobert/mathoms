---
id: MOC-sprint-a38
type: moc
title: "Sprint A38 — Ingestão confiável: certificação de parse dos layouts 2026 (Wise/Santander/Itaú)"
aliases: ["A38", "Sprint A38"]
sprint_status: current
date: "2026-07-22"
theme: "ingest-trust"
---

# Sprint A38 — Ingestão confiável (certificação de parse 2026-07-22)

> **Origem:** certificação empírica de 2026-07-22 — o caminho real de produção
> E0→E2 (classify → nome canônico → roteamento → parse → validação) foi
> executado sobre um corpus local de 13 PDFs reais do owner (2 extratos Wise
> USD/BRL, 2 extratos consolidados Santander, 3 faturas de cartão Santander
> layout 2026, 3 extratos Itaú conta corrente layout 2026, 3 faturas Itaú
> Visa). O corpus **vive fora do git** (política de PII); as lanes são
> self-contained e carregam as métricas mascaradas. 10 achados com causa-raiz
> diagnosticada in-repo; âncoras `arquivo:função` verificáveis no commit em que
> este sprint foi escrito.
>
> **Achado central:** `parse_itau` captura só **~50% das transações** do layout
> 2026 do extrato PDF (34/74, 32/65, 12/23 nas três amostras) e **nenhum
> validador flagga** — as linhas perdidas incluem receitas recorrentes e
> pagamentos de fatura. Perda silenciosa de dados é o pior modo de falha do
> produto: o relatório sai errado com cara de certo.

> **Revisão do sprint (painel 2026-07-22 — pm, ia, data, financial):** zero
> objeção de mérito aos achados; ~15 correções de mecanismo incorporadas antes
> do merge — ver §Decisões do painel no fim deste README.

## North Star e KRs

**North Star:** nenhum documento suportado perde transação em silêncio — ou a
extração é **completa** (conservação de saldo fecha em cents) ou o documento
**escala explicitamente** (`needs_review`/`requires_llm_fallback`). Decisão de
painel: **corretude > cobertura** — é melhor um documento honesto em
`needs_review` do que um artefato parcial "ok".

Medição: harness local da [[A38.l1]] sobre o corpus do owner (fora do git) +
suíte/goldens existentes.

- **KR-A (completude Itaú):** as 3 amostras do layout 2026 extraem **100% das
  linhas de transação** (74/74, 65/65, 23/23) com conservação
  `saldo_inicial + Σtx == saldo_final` em cents, tolerância zero.
- **KR-B (classificação determinística):** os 13 docs do corpus classificam
  com `(banco, tipo)` corretos e **conf ≥ 0.8** (limiar que dispensa o LLM
  fallback — 0.7–0.79 ainda o aciona) — hoje 6 caem em conf 0.0, um vira
  `cdbdetalhes` e um vira banco errado com conf 1.0.
- **KR-C (gate anti-silêncio, extrato E fatura):** extrato com 0 transações
  ou conservação quebrada, e fatura com 0 lançamentos ou total
  ausente/divergente, **nunca** viram artefato válido sem flag — escalam para
  `needs_review`/`requires_llm_fallback` (fixture sintética + corpus).
- **KR-D (moeda determinística):** extrato Wise USD produz `moeda=USD` sem
  depender do LLM acertar o subtipo no filename.
- **KR-E (anti-regressão):** suíte completa + goldens verdes; para cada doc do
  corpus, `n_tx ≥ baseline` (nunca menos); parsers de bancos não tocados com
  output idêntico; nenhum doc hoje bem-classificado muda de tipo
  (`tests/test_e2_parsers.py::TestExtratoRoutingInvariant` + corpus de
  classification existente).

## Baseline medida (2026-07-22, mascarada — sem valores reais)

| Doc do corpus | Classificação regex hoje | Parse hoje | Alvo |
|---|---|---|---|
| Extrato Itaú 2025-S2 | `cdbdetalhes` conf 0.7 (linha "APLICACAO CDB…") | 34/74 linhas, conservação falha | 74/74, conservação zero |
| Extrato Itaú 2026-S1 | `extratoconta` conf 1.0 ✅ | 32/65, conservação falha | 65/65, conservação zero |
| Extrato Itaú 2026-T2 | `extratoconta` conf 1.0 ✅ | 12/23, conservação falha | 23/23, conservação zero |
| Extrato Wise USD anual | `extratoconta` genérico conf 0.7 (sem moeda) | 17 tx, **moeda=BRL** | moeda=USD determinística |
| Extrato Wise BRL anual | idem | 7 tx, moeda ok | + sem falso-positivo de dupe c/ o USD |
| Consolidado Santander mai | `santander` conf 1.0 | **0 tx**, artefato "ok" | tx>0 ou escalação explícita |
| Consolidado Santander jun | **`caixa` conf 1.0** (SAC 0800 726 0322) | 0 tx → LLM c/ banco errado | banco=santander determinístico |
| Fatura Santander Unique ×3 (layout 2026) | conf **0.0** (regex nunca casa) | parser forçado: 9 tx, total/vencimento `None` | classificação determinística + total/vencimento extraídos |
| Fatura Itaú Visa ×3 | conf **0.0** | sem parser → 100% E2-llm | caminho determinístico (ou LLM com aceite explícito) |

## Lanes por onda

Ondas por **dependência**. Lane abre quando suas `depends_on` estão `shipped`.

### W0 — fundação P0 (`open`)

| Lane | Achado | Prio | Escopo em 1 linha |
|---|---|---|---|
| [[A38.l1]] | (transversal) | P0 | Harness `dev/certify_parse_local.py`: classify→route→parse sobre diretório local, métricas mascaradas; registra baseline e vira gate manual de toda mudança de parser |
| [[A38.l2]] | #1 | P0 | `parse_itau` layout 2026: extração por linhas de texto com dispatch por layout (o layout antigo continua no caminho atual) |
| [[A38.l3]] | #2 | P0 | **ADR `Proposto` + gate anti-silêncio** no `validate_extrato_result`: 0 tx ou conservação quebrada ⇒ escalação, nunca artefato "ok" |

### W1 — classificação determinística (P1; **l6 primeiro** — decisão do painel)

| Lane | Achado | Prio | Escopo |
|---|---|---|---|
| [[A38.l6]] | #6 + #10b | P1 | Wise: moeda por **conteúdo** no parser + TypeRule de subtipo de moeda + período range para datas por extenso — **1º P1**: erro invisível ao gate de conservação e direcionalmente enganoso (dolarização) |
| [[A38.l4]] | #3 | P1 | Colisão de instituição: `0800 726` (caixa) casa SAC Santander; âncoras novas p/ o layout consolidado |
| [[A38.l5]] | #5 | P1 | TypeRule `cdbdetalhes`: required forte (hoje `\bCDB\b` rouba extrato com aplicação automática) |
| [[A38.l7]] | #7 | P1 | Fatura Santander Unique layout 2026: TypeRule + `total_fatura`/`vencimento` no parser — **no mesmo PR**, nunca só classificação |

### W2 — cobertura e robustez (P2)

| Lane | Achado | Prio | Escopo |
|---|---|---|---|
| [[A38.l8]] | #4 | P2 | Extrato Consolidado Inteligente Santander: suportar o layout (ou escalação explícita documentada; dívida de produto pré-beta) — `depends_on` [[A38.l4]] |
| [[A38.l9]] | #8 | P2 | Fatura Itaú Visa/Itaucard: parser determinístico (extração via `words` p/ PDF com texto sem espaços) |
| [[A38.l10]] | #9 | P2 | TypeRules genéricas de fatura: `re.DOTALL` nos gaps `.{0,N}` (hoje nunca cruzam linha) + corpus de classificação |
| [[A38.l11]] | #10a | P2 | Fuzzy-dupe: não cruzar-flagar subtipos de moeda distintos do mesmo período (Wise USD × BRL) |

## Regras de execução (completude · corretude · consistência · precisão)

1. **Corretude:** bug → **teste de regressão antes do fix**, com fixture
   **sintética PII-zero** reproduzindo o layout problemático. Os PDFs reais do
   corpus **nunca** entram em git/fixtures/goldens/CI/log não-mascarado
   (paths proibidos + política de dados sensíveis). Dinheiro nunca é float
   ([[ADR-090]]); conservação em cents, tolerância zero.
2. **Completude:** critério de aceite de cada lane é **testável e binário**,
   medido pelo harness da [[A38.l1]] (ou invocação manual equivalente enquanto
   l1 não shipped) + metas da tabela de baseline.
3. **Consistência:** corretude > cobertura — na dúvida entre extrair parcial e
   escalar, **escale** ([[A38.l3]] define o contrato). Detecção de layout
   despacha para estratégia nova **sem substituir** a antiga.
4. **Precisão:** moeda, banco e tipo vêm de **conteúdo**, não de filename;
   filename canônico é derivado, nunca fonte de verdade de domínio.
5. **Anti-regressão (KR-E é gate de toda lane):** baseline antes de mudar;
   `n_tx ≥ baseline` por doc do corpus; parsers não tocados idênticos;
   classificações hoje corretas não mudam. **Toda lane de parser deixa
   fixture sintética do layout em CI** (não-negociável — sem ela a
   certificação é one-shot e regride em silêncio); o KR-E sobre o corpus
   real é **gate manual local** (harness [[A38.l1]], baseline em `_scratch/`)
   — o **relatório mascarado do harness vai no corpo do PR** de toda lane que
   toque `scripts/e2/**`. Ferramental existente: `dev/golden_diff.py`,
   `tests/test_e5_conservation_invariants.py`, `TestExtratoRoutingInvariant`.
6. **Coordenação de hotspot:** [[A38.l5]]/[[A38.l6]]/[[A38.l10]] tocam
   `type_classifier.py` — sequenciar (l6 → l5 → l10) ou rebase incremental
   disciplinado; nunca commit cruzado entre lanes.
7. **Co-design na execução:** ADR da [[A38.l3]] → `senior-cto` +
   `data-engineer` (invariante de read-path); fallback da [[A38.l8]] e
   netting das linhas recuperadas da [[A38.l2]] → `financial-planner`. 1
   rodada; objeção persistente → `senior-cto` decide e fecha.
8. **Segurança de execução:** "concluído" = PR squash-merged em `main` com CI
   verde. Diff >300 linhas → PRs sequenciais. [[A38.l3]] exige ADR `Proposto`
   **antes** do PR de implementação. Gate de sigilo de metodologia e PII-lint
   se aplicam a docs novos.
9. **Pickup:** protocolo padrão (worktrees + branches `agent/*` <24h; slug da
   lane = `branch_slug` do frontmatter).

## Riscos do sprint

- **l3 muda o comportamento de ingestão por design:** docs que hoje "passam"
  com 0 tx passam a escalar. É o comportamento correto, mas aumenta a fila de
  `needs_review` até l2/l4/l8 aterrissarem. Mitigação: l2 (Itaú, maior volume)
  sai na mesma onda; mensagem de review aponta a causa.
- **l2 toca o parser de maior volume do produto:** mitigação: dispatch por
  layout (aditivo), fixture golden do layout antigo intocada, corpus local
  como gate manual.
- **Escalação para E2-llm tem custo/latência (tier premium):** o gate da l3
  não pode criar loop de retry; escalação é one-shot por doc (mesmo contrato
  de `requires_llm_fallback` existente).
- **Fatura Itaú Visa (l9) pode não ter camada de texto utilizável** em todos
  os emissores: aceite alternativo explícito (E2-llm **amarrado ao
  cross-check de total**) documentado na lane.
- **KR-C mede o gate disparar, não o usuário recuperar:** a UX de
  `needs_review` (mensagem causal, recuperação) vive fora deste sprint —
  exclusão deliberada, não omissão. A mensagem de escalação carrega a razão
  estruturada para a UX existente exibir.
- **Escalação E2 não se propaga a E5 ainda:** conta-período com input
  escalado segue renderizando KPIs derivados com cara certificada — follow-up
  explícito registrado na ADR da [[A38.l3]] (candidato A39+), não escopo
  desta sprint.

## Decisões do painel (2026-07-22 — pm, ia, data-engineer, financial-planner)

Zero objeção de mérito aos 10 achados; zero impasse (nenhuma escalação a
`senior-cto`). Correções incorporadas antes do merge:

- **pm:** sprint único confirmado (plano canônico rejeitado — sem tese
  multi-sprint); KR-B pinado em **conf ≥ 0.8** (0.7–0.79 ainda aciona LLM;
  l10 alinhada); contrato anti-silêncio **estendido a faturas** (KR-C);
  [[A38.l8]] rebaixada P1→P2 (l3 já fecha a perda silenciosa; registrada
  dívida de produto pré-beta); [[A38.l9]] fallback amarrado ao cross-check;
  regra de coordenação p/ `type_classifier.py` (l5/l6/l10); aceite da
  [[A38.l11]] só verificável pós-l6; l1-primeiro confirmado (baseline
  congelado sobre `origin/main` antes das mutações).
- **ia:** forma aderente ao padrão A37; `area/dev-tooling` → `area/dx`
  (taxonomia existente); ADR da l3 **nasce na lane**, não neste PR (política
  do repo + precedente A37.l1/ADR-341; executor deve reservar ID cedo);
  corpus fora-do-git documentado via tabela mascarada + harness sem paths
  (padrão A37; sem runbook novo).
- **data-engineer:** flag de escalação sozinho seria **no-op no estado
  estacionário** — contrato da ADR reescrito para cobrir o **read-path**
  (invariante "≤1 artefato não-fallback por (workspace, key)" + stub
  superseding + pickup do E2-llm inspeciona stub + dedup do E3 não reivindica
  stub + normalização de key única); conservação **no-op onde saldo é
  derivado** (Wise/Rico — check tautológico); rollout WARN→HARD por banco com
  allowlist; **flip HARD do Itaú gated por l2**; telemetria via
  `ReviewReasonCode` (zero schema change); cura de parciais antigos por full
  re-run de workspace (runbook, sem backfill dedicado).
- **financial-planner:** P0 Itaú confirmado (corrompe a camada de fluxo
  inteira; defeito sistêmico de layout), mas **l6 é o 1º P1** (USD→BRL é
  invisível ao gate e direcionalmente enganoso em dolarização); moeda
  indeterminada **escala, nunca default BRL**; gate de conservação só na
  forma **global** em produção (per-dia é assert de fixture) com guarda de
  conceito-de-saldo ("não reconciliável" ≠ "quebrada"); aceite da l2 exige
  netting das linhas recuperadas (transferência interna vs. receita vs.
  rendimento — medir taxa de poupança e renda passiva pré/pós); l7 nunca
  shippa classificação sem total+cross-check no mesmo PR; propagação E2→E5
  sinalizada como follow-up.
