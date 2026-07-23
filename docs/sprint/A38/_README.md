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

> **Revisão do sprint (painel 2026-07-22 — pm, ia, data, financial):**
> incorporada antes do merge — ver §Decisões do painel no fim deste README.

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
  com `(banco, tipo)` corretos **sem LLM** — hoje 6 caem em conf 0.0, um vira
  `cdbdetalhes` e um vira banco errado com conf 1.0.
- **KR-C (gate anti-silêncio):** extrato com 0 transações ou conservação
  quebrada **nunca** vira artefato válido sem flag — escala para
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

### W1 — classificação determinística (P1)

| Lane | Achado | Prio | Escopo |
|---|---|---|---|
| [[A38.l4]] | #3 | P1 | Colisão de instituição: `0800 726` (caixa) casa SAC Santander; âncoras novas p/ o layout consolidado |
| [[A38.l5]] | #5 | P1 | TypeRule `cdbdetalhes`: required forte (hoje `\bCDB\b` rouba extrato com aplicação automática) |
| [[A38.l6]] | #6 + #10b | P1 | Wise: moeda por **conteúdo** no parser + TypeRule de subtipo de moeda + período range para datas por extenso |
| [[A38.l7]] | #7 | P1 | Fatura Santander Unique layout 2026: TypeRule + `total_fatura`/`vencimento` no parser |

### W2 — cobertura e robustez (P1/P2)

| Lane | Achado | Prio | Escopo |
|---|---|---|---|
| [[A38.l8]] | #4 | P1 | Extrato Consolidado Inteligente Santander: suportar o layout (ou escalação explícita documentada) — `depends_on` [[A38.l4]] |
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
   classificações hoje corretas não mudam. Ferramental existente:
   `dev/golden_diff.py`, `tests/test_e5_conservation_invariants.py`,
   `TestExtratoRoutingInvariant`.
6. **Segurança de execução:** "concluído" = PR squash-merged em `main` com CI
   verde. Diff >300 linhas → PRs sequenciais. [[A38.l3]] exige ADR `Proposto`
   **antes** do PR de implementação. Gate de sigilo de metodologia e PII-lint
   se aplicam a docs novos.
7. **Pickup:** protocolo padrão (worktrees + branches `agent/*` <24h; slug da
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
  os emissores: aceite alternativo explícito (E2-llm com validação de total)
  documentado na lane.

## Decisões do painel (2026-07-22)

_(preenchido após a rodada de co-design — ver PR deste sprint)_
