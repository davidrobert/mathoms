---
id: MOC-sprint-a39
type: moc
title: "Sprint A39 — Parse correctness: fechar a dívida de verificação da ingestão E0→E2"
aliases: ["A39", "Sprint A39"]
sprint_status: done
date: "2026-07-23"
theme: "ingest-trust"
---

# Sprint A39 — Parse correctness (dívida de verificação E0→E2, 2026-07-23)

> **Status:** `done` — fechada em 2026-08-04 pela abertura da [[A42]], sua sucessora
> declarada na mesma tese `ingest-trust`. **12 de 13 lanes shipadas**; a 13ª e os
> resíduos deferidos receberam disposição item a item em §Fechamento. Follow-on direto
> do [[MOC-sprint-a38]]. Escopo: **ingestão E0→E2** — do documento ao artefato E2
> verificado. Propagação E2→E5 e selo no relatório ficam **fora** (deferidos ao plano
> REPORT_TRUST; ver §Deferidos).

> **Nota de leitura.** As seções abaixo são registro datado de 2026-07-23 e **não
> foram reescritas**. Onde a §"Deferido — fase pesada" lista lanes com blocker
> (l9/l10/l11/l12), o estado final divergiu: as quatro shiparam depois. A disposição
> autoritativa é a de §Fechamento.

> **Origem:** skill `parse-certify` sobre o workspace dogfood inteiro
> (`5@5.com`, 123 docs em `financial_statements`), 2026-07-23, sobre `main @
> d59a72cc` (**pós-A38**). Relatório mascarado: `_scratch/parse-certify-5at5-2026-07-23.md`;
> baseline durável (fora do git, PII): `storage/<uuid>/certify/`. Corpus real
> **vive fora do git** — lanes carregam métricas mascaradas; nenhum PDF/valor/CPF
> real entra em git/fixtures/CI.

> **Revisão do sprint (painel 2026-07-23 — pm, ia, senior-cto, data-engineer,
> financial-planner, prompt-engineer):** zero objeção de mérito aos vereditos da
> certificação; **correções estruturais incorporadas antes deste README** (ver
> §Decisões do painel). O painel reescreveu 5 lanes do rascunho, reconciliou a
> cauda P2 do A38, e fechou a estrutura de 3 ADRs novas.

## Estado de execução (2026-07-23)

**Onda de flips + observabilidade + classificação ENTREGUE** — 7 lanes em `main`
(+ l8 em auto-merge), **KR-A completo**:

| Lane | PR | Nota |
|---|---|---|
| [[A39.l1]] harness | #1035 | ✅ (entregue antes da abertura) |
| [[A39.l2]] C6 CSV opt-in | #1039 | ✅ |
| [[A39.l4]] C6 PDF saldo | #1041 | ✅ |
| [[A39.l5]] bradesco saldo | #1042 | ✅ (R$1 é real: sweep Invest Fácil) |
| [[A39.l6]] CDB trace | #1043 | ✅ |
| [[A39.l7]] verificabilidade sweep | #1040 | ✅ (itau_xls+santander_xls) |
| [[A39.l3]] gate fatura escopo-aware | #1045 | ✅ **parcial** — gate; opt-in do parser **deferido** |
| [[A39.l8]] classificação fatura Itaú | #1047 | ✅ **parcial** — classificação; parser determinístico **deferido** |

**KRs:** **KR-A** ✅ (os 4 perda-silenciosa escalam via l2/l4/l5) · **KR-B** 6
parsers declaram `conservacao_verificavel` · **KR-C/D** observabilidade CDB (l6) +
gate de fatura escopo-aware (l3).

### Deferido — fase pesada (bloqueada por decisão/iteração; não é cauda P2 comum)

Cada uma tem um **blocker real** que torna cramar temerário (arrisca a
perda-silenciosa que o sprint combate). Handoff turnkey na memória de sessão
`project_a39_execution`:

- **Opt-in de fatura ([[A39.l3]] c2) + parser Itaú ([[A39.l8]] parser):**
  bloqueados na **identidade do checksum de fatura** — `Σ(tx despesa_brasil) ==
  total_compras` **não fecha em 0/3** faturas reais (encargos/IOF-nacional NÃO
  itemizados em "Total Despesas"; senior-cto já sinalizou). **Decisão de domínio
  pendente:** o que "Total Despesas/Débitos no Brasil" inclui? Sem isso, opt-in =
  WARN permanente e parser novo é não-verificável.
- **[[A39.l9]] posição RV:** **parser NOVO** (custódia PDF + carteira XLSX) + **ADR
  nova** (identidade `ticker+proprietário`) + `null-não-soma` no consolidador —
  build de sessão dedicada, iteração no corpus real.
- **[[A39.l10]] piso de materialidade:** **ADR-344** (id reservado; 343 é
  pipeline-review) + o **valor do piso é uma decisão de materialidade de domínio**
  (financial-planner) — não arbitrável no fim da sessão.
- **[[A39.l11]] temp=0 LLM:** ADR nova + **eval owner-gated** (LLM real precisa da
  key).
- **[[A39.l12]] resíduo binance/rico:** verificação; parte `rico .xlsx` acoplada a
  [[A39.l9]].

DoD do sprint (W0+W1) atingido **exceto [[A39.l9]]** (deferida com blocker). W2
(l10/l11/l12) trailing por design (padrão A37/A38).

## North Star

Nenhum documento suportado vira artefato "ok" sem prova de fechamento. A38
garantiu que **transação não some em silêncio** (extrai completo **ou** escala).
A39 sobe a régua: **todo parser com saldo observado independentemente DECLARA
verificabilidade** (`conservacao_verificavel=True`, para o gate HARD da
[[ADR-342]] poder graduá-lo) **e faturas ganham um checksum de fechamento**
(identidade de domínio própria, [[ADR-342]] item 1 corrigido por ADR-343).
Decisão de painel herdada do A38: **corretude > cobertura** — documento honesto
em `needs_review` > artefato parcial "ok".

Medição: harness `dev/certify_parse_local.py` (estendido pela [[A39.l1]]) sobre o
corpus congelado + goldens/fixtures sintéticas em CI.

## Baseline medida (2026-07-23, mascarada — sem valores reais)

Certificação de 123 docs `financial_statements`, veredito fail-closed:

| Veredito | N | Leitura |
|---|---|---|
| `completo` (checksum fecha) | **3** | só `parse_itau` PDF declara `conservacao_verificavel=True` |
| `coberto-sem-verificação` | **99** | parseou, não escalou, **sem** prova de fechamento |
| `escalado-honesto` (ADR-342) | **11** | correto — sem parser/checksum falha → `needs_review` |
| `perda/corrupção silenciosa` | **4** | conservação material falha em cents, não escala |
| `não-coberto` | **6** | regex E0 não classificou (LLM em prod pode cobrir) |

> **A P0 do run anterior (C6 Global USD/EUR 0-tx + false-dormant) está
> CORRIGIDA** ([[A38.l14]]/[[A38.l15]]): o layout Global agora extrai 56/63/199/179
> tx; o único C6 Global 0-tx restante é dormência genuína (`raw_rows_detected=0`).

### Entregue durante a autoria (#1035/#1036/#1037 — reconciliação com `main`)

Enquanto este sprint era autorado (co-design de 6 especialistas), 3 PRs mergearam
em `main` implementando parte do escopo — **convergindo com o design do painel**:

- **#1035** (`a3188b7a`) → **[[A39.l1]] SHIPPED** (harness: campos por-tipo,
  conservação em cents, `--compare` seguro, baseline PII-safe).
- **#1036** (`a63ec80f`) → **gate** de checksum de fatura (opt-in
  `total_lancamentos_conferivel` contra `total_compras` escopado, WARN-first,
  int cents, emenda [[ADR-342]]) + checksum de investimento (CDB XLSX/Itaú). O
  gate/contrato de [[A39.l3]] e a cobertura de [[A39.l6]] estão em `main`; **resta
  o lado do parser** (l3: emitir o sinal + flip WARN→HARD) e a **observabilidade**
  (l6: traço `checksum_ok`). **ADR-343 descartada** (a emenda superou a proposta).
- **#1037** (`f7320b33`) → skill `parse-certify` (§Extensões + rubric) reflete os
  checksums entregues.

Efeito nas ondas: **l1 nasce `shipped`**; **l3/l6 encolhem para residual**; as 9
lanes restantes seguem válidas (nenhuma shipou).

### Rastreabilidade KR-A — os 4 `perda/corrupção silenciosa` → lane

| Doc (#hash) | Parser | GAP conservação (verificado) | Lane que zera |
|---|---|---|---|
| #f658 bradesco extratoconta | `parse_bradesco` | saldo_ini=saldo_fim=**R$1,00** (sentinela) + over-count **refutado** (data 1×/dia) | [[A39.l5]] |
| #2570 c6bank extratoconta (PDF) | `parse_c6bank` | −R$1.000 (valor reconciliador **ausente** do doc → defeito real) | [[A39.l4]] |
| #637b c6bank extratoconta (CSV) | `parse_c6bank_csv` | +R$1.978 (semântica de saldo correta → row-drop real) | [[A39.l2]] |
| #5a21 c6bank extratoconta (CSV) | `parse_c6bank_csv` | −R$296 (idem, menor magnitude) | [[A39.l2]] |

> **Refutados na verificação adversarial (NÃO são silêncio):** #786e (−R$17k) e
> #c5c6 (+R$7k) do C6 PDF são **cosméticos** — a abertura reconciliadora está no
> doc e `abertura + Σtx == fechamento` fecha; tx completas, `saldo_final`
> (consumido) correto; só o `saldo_inicial` interno defaultou. [[A39.l4]] os faz
> passar de graça ao corrigir a semântica.

### Rastreabilidade KR-A — os 6 `não-coberto` → lane

| Doc | Causa | Lane |
|---|---|---|
| itau_fatura .pdf ×3 | lacuna de TypeRule (regex) — não é ambiguidade | [[A39.l8]] |
| itau_investimentosposicao .pdf + rico_investimentosposicao .xlsx | TypeRule RV ausente + instituição vazia | [[A39.l9]] |
| binance_extratoconta .csv | mapeia p/ `.other` **sem stage consumidor** — escala honesto é o correto | [[A39.l12]] |

## KRs (5 — binários, medidos pelo harness da [[A39.l1]] sobre o corpus congelado)

- **KR-A (zero perda silenciosa):** todo doc do corpus é `completo` **ou**
  `escalado-honesto` — os 4 `perda-silenciosa` zerados (tabela acima) e os 6
  `não-coberto` cobertos-ou-escalados. Nenhum drop silencioso.
- **KR-B (verificabilidade + completude):** parsers declarando
  `conservacao_verificavel=True` sobem **1 → ≥7**
  (`parse_itau` PDF já + c6_csv, c6_pdf, itau_xls, santander_xls, bradesco);
  `%completo` sobe de **3/123 → ≥55/123 (~45%)** (o restante escala legítimo →
  conta em KR-A, não é miss de KR-B). O número de parsers é o alvo controlável;
  45% é forecast.
- **KR-C (closure coverage):** **36/36 faturas** com checksum de fechamento
  passando (identidade de domínio ADR-343) **ou** escalação honesta; **N/N
  posições CDB** verificadas (Santander xlsx, total independente) **ou**
  `checksum_skipped_no_total` honesto (Itaú CDB PDF, sem total agregado). Conta
  `checksum_ok` **separado** de `skipped_no_total` (no-op não infla cobertura).
  Companheiro de valor: **% do valor de despesa sob checksum-pass sobe de ~0**.
- **KR-D (guard forward):** gap material (> piso) **nunca** persiste `ok`
  independente do flag do parser — provado por **teste de gap injetado**
  (ADR-344). Caminho certificado permanece **cents tolerância zero**.
- **KR-E (anti-regressão):** suíte + goldens verdes; harness `--compare` vs
  baseline congelado sem regressão (`n_tx ≥ baseline`, `escalated` não vira
  `False` sem checksum-pass); parsers não tocados idênticos; nenhum doc hoje
  bem-classificado muda de tipo.

## Lanes por onda

Ondas por **dependência**. DoD do sprint = **W0 + W1 shipped** com KRs
A/B/C/D/E verdes; **W2 trailing** (padrão A37/A38). A [[A39.l1]] **congela o
baseline sobre `origin/main` antes de qualquer mutação**.

### W0 — instrumento + silêncio + fatura (P0)

| Lane | Achado | Prio | ADR | Escopo em 1 linha |
|---|---|---|---|---|
| [[A39.l1]] ✅ | (transversal) | P1 | — | **SHIPPED #1035** — harness emite campos por-tipo, conservação em cents, `--compare` seguro, baseline PII-safe |
| [[A39.l2]] | PC-02 | P0 | [[ADR-342]] | Flip `conservacao_verificavel` em `parse_c6bank_csv` (semântica já ancorada) → escala #637b/#5a21; `depends_on` [[A39.l1]] |
| [[A39.l3]] | PC-01 | P0 | [[ADR-342]] | **Gate shipped #1036** — parsers (Santander/quintoandar) emitem `total_lancamentos_conferivel` (`total_compras` escopado) + flip WARN→HARD; `depends_on` [[A39.l1]] |
| [[A39.l4]] | PC-03 | P1 | [[ADR-342]] | `parse_c6bank` PDF: ajuste `summarize_saldos` do 1º dia (`c6bank.py:598`), validar, **depois** flipar → zera #2570, faz #786e/#c5c6 cosméticos passarem; `depends_on` [[A39.l2]] (hotspot `c6bank.py`) |

### W1 — verificabilidade + cobertura determinística (P1)

| Lane | Achado | Prio | ADR | Escopo |
|---|---|---|---|---|
| [[A39.l5]] | PC-04 | P1 | [[ADR-342]] | Bradesco saldo `R$1/R$1`: **diagnosticar** raiz (miss de extração vs default — não confirmado no código) + teste de independência, então flipar; `depends_on` [[A39.l1]] |
| [[A39.l6]] | PC-05 | P1 | [[ADR-342]] | **Cobertura shipped #1036** (CDB XLSX/Itaú, int cents) — residual = traço positivo `checksum_ok`/`skipped_no_total`; `depends_on` [[A39.l1]] |
| [[A39.l7]] | PC-06 | P1 | [[ADR-342]] | Sweep de verificabilidade: **`itau_xls` + `santander_xls`** declaram `conservacao_verificavel=True` (**wise/rico cortados** — saldo derivado tautológico); `depends_on` [[A39.l1]] |
| [[A39.l8]] | PC-07 / A38.l9 | P1 | **ADR-343** | Fatura Itaú Visa: TypeRule (regex, conteúdo) + parser determinístico (via `words`) + checksum ADR-343 → cobre 3 `não-coberto`; **adota [[A38.l9]]**; `depends_on` [[A39.l3]] |
| [[A39.l9]] | A38.l13 | P1 | **ADR nova (RV)** | Posição RV (custódia + carteira): TypeRule + parser + identidade `ticker+proprietário` + `null-não-soma` no consolidador → cobre 2 `não-coberto`; **adota [[A38.l13]]**; `depends_on` [[A39.l1]] |

### W2 — guards e robustez (P2, trailing)

| Lane | Achado | Prio | ADR | Escopo |
|---|---|---|---|---|
| [[A39.l10]] | PC-08 | P2 | **ADR-344** (nova) | Piso de materialidade como **roteamento sobre o caminho não-certificado** (transitório; north-star = certificar; telemetria de dependência) + emenda-ponteiro ADR-342 item 2; `depends_on` [[A39.l2]]/[[A39.l4]]/[[A39.l5]]/[[A39.l7]] |
| [[A39.l11]] | PC-07 (LLM) | P2 | **ADR nova (temp=0)** | Determinismo da classificação LLM: `temperature=0` na via compartilhada + golden sintético N=3 + telemetria `mathoms.llm.classification.*`; co-design senior-cto (muda runtime de todo upload) |
| [[A39.l12]] | PC-07 (resíduo) | P2 | — | Verificar que `classify_document` roteia o resíduo real (binance csv) a escalação honesta; investigar extração de preview `.xlsx` (rico); binance consumer stage = **fora de escopo** (nota); `depends_on` [[A39.l1]] |
| [[A39.l13]] | PC-07 (LLM) | P1 | **[[ADR-349]]** (nova) | Spin-off do co-design da [[A39.l11]]: re-route de `classify_by_llm` pelo choke-point `LLMService` (budget/cache/telemetria/enum de graça). Fecha a doença de fundo que a l11 cirúrgica deixou; faseada (PDF-imagem = risco); priorização `product-manager` (pode ir p/ A40) |

## Deferidos (fora de A39 — decisão explícita do painel)

- **Propagação E2→E5 + selo de qualidade no relatório** (o "taint" que impede
  KPI derivado de input escalado nascer com cara certificada) → **plano
  REPORT_TRUST**, gated por **[[ADR-345]]** (read-path/render, co-design
  product-designer + data-engineer + financial-planner). É o follow-up que a
  própria [[ADR-342]] §Consequências punt para "A39+". **Risco registrado
  (financial-planner):** até [[ADR-345]] aterrissar, input escalado ainda pode
  aparecer em KPI com cara certificada — KR-A do A39 cobre a camada **E2**, não a
  de KPI.
- **Reconciliação dos 3 docs órfãos no DB** (dir=123, `documents`=126) por
  `content_hash` + **quarentena inerte no read-path do artefato** (4 pontos de
  match E3/E4, não só `documents.status`) → **A40** (data-cleanup one-shot).
- **Cauda A38 não surfada no corpus 5@5:** [[A38.l8]] (Santander Consolidado
  Inteligente — não apareceu neste corpus) e [[A38.l11]] (fuzzy-dupe moeda) →
  A40. [[A38.l10]] (DOTALL TypeRules) — fatia de classificação absorvida pela
  [[A39.l8]]; remanescente trailing/A40.

## Regras de execução (completude · corretude · consistência · precisão)

1. **Corretude:** bug → **teste de regressão antes do fix**, com fixture
   **sintética PII-zero** reproduzindo o layout. PDFs reais **nunca** entram em
   git/fixtures/CI/log não-mascarado. Dinheiro nunca é float ([[ADR-090]]);
   conservação e checksum em **cents, tolerância zero** no caminho certificado.
2. **Completude:** aceite de cada lane é **binário**, medido pelo harness da
   [[A39.l1]]. Nenhuma lane de fatura shippa classificação sem o checksum de
   fechamento no mesmo PR.
3. **Consistência:** corretude > cobertura — na dúvida, **escale**. Detecção de
   layout despacha estratégia nova **sem substituir** a antiga.
4. **Precisão:** moeda/banco/tipo vêm de **conteúdo**, nunca de filename.
   `conservacao_verificavel` é observação **auditada por fixture** (não
   auto-conclusão confiada pelo gate — lição [[A38.l14]]).
5. **Anti-regressão (KR-E é gate de toda lane):** baseline congelado antes de
   mutar; toda lane de parser deixa **fixture sintética em CI** + **relatório
   mascarado do harness no corpo do PR**.
6. **Hotspots:** `c6bank.py` ([[A39.l2]]→[[A39.l4]]) e `type_classifier.py`/
   `content_classifier.py` ([[A39.l8]]/[[A39.l9]]/[[A39.l11]]) — sequenciar ou
   rebase incremental; nunca commit cruzado.
7. **ADR `Proposto` antes do PR de impl** (P0/P1 + escopo arquitetural):
   ADR-344 ([[A39.l10]] piso), ADR nova de RV ([[A39.l9]]), ADR nova de temp=0
   ([[A39.l11]]). **ADR-343 descartada** — o checksum de fatura shipou como
   emenda [[ADR-342]] (#1036, identidade `total_compras` escopada), não como ADR
   nova. Emendas datadas à [[ADR-342]] (protocolo ADR-027: `## Emenda YYYY-MM-DD`
   + `amended_at` + blockquote) em commit **separado** do código. **Reservar ID
   de ADR cedo** (re-checar `ls docs/adr` antes do push — colisão em sessão longa).
8. **Segurança:** "concluído" = PR squash-merged em `main` com CI verde. Diff
   >300 linhas → PRs sequenciais. Gate de sigilo de metodologia (ADR-319) +
   PII-lint em docs novos.

## Riscos do sprint

- **Piso de materialidade ([[A39.l10]]) vira anti-incentivo a certificar
  parser** (viver do piso em vez de flipar o flag): ADR-344 **declara o piso
  transitório/modo-degradado** + exige telemetria contando artefatos que
  dependem dele. É defesa em profundidade (P2), não o mecanismo primário.
- **Piso pode falso-escalar parser de saldo derivado** (Wise/Rico tautológicos):
  escopo restrito a **saldo observado independentemente**; co-design
  financial-planner + data-engineer.
- **`temperature=0` ([[A39.l11]]) muda o runtime de TODO upload em prod**, não só
  o harness — coordenar com senior-cto; ADR `Proposto` antes.
- **Propagação E2→E5 deferida:** KR-A garante o E2, não o KPI — até [[ADR-345]],
  input escalado pode surfar em KPI certificado (aceito, registrado).
- **Sobreposição com cauda A38:** [[A38.l9]]/[[A38.l13]] **adotadas** como lanes
  A39 (evita merge-hell); resto da cauda deferido explicitamente.

## Decisões do painel (2026-07-23 — pm, ia, senior-cto, data-engineer, financial-planner, prompt-engineer)

Co-design sobre o rascunho de 9 lanes. Correções incorporadas:

- **pm:** 5 KRs (mata "trace exposed" — atividade, não outcome; funde em KR-C);
  KR-A exige **tabela doc→lane** (feita acima); KR-B = parsers 1→≥7 (controlável)
  + %completo ≥55/123 (forecast). **[[A39.l7]] subida P2→P1** (maior driver do
  KR-B). **[[A39.l1]] split do l9** (harness = instrumento P1/W0, congela
  baseline). **Reconciliar cauda A38:** adotar l9+l13; encolher a lane de
  cobertura LLM. **[[A39.l10]] piso = P2 backstop**, não mecanismo primário.
  DoD = W0+W1; W2 trailing; **não abrir A40 prematuramente**.
- **ia:** `sprint_status: candidate`, `MOC-sprint-a39`, `theme: ingest-trust`;
  lane `A39-lN-<slug>.md`↔id `A39.lN`; **9→12 lanes ok** (A38 rodou 15);
  emendas moram no **ADR**, não na lane (lane só declara `adrs: [[ADR-342]]`),
  uma emenda datada **por PR/data**; ADR nova referenciada em prosa (não
  wikilink órfão) até stub; A39 entra em "Sprint candidate" do SPRINTS-active;
  **nunca** editar `_generated/` à mão; tags `area/*` do vocab existente
  (`area/pipeline`/`area/dados`/`area/dx`).
- **senior-cto (decide e fecha ADRs):** **l3 = ADR-343 nova** (identidade de
  fechamento de fatura é regra de domínio própria, ≠ conservação de extrato)
  **+ emenda-ponteiro** corrigindo ADR-342 item 1 (que já legislou a identidade
  **errada** `Σlançamentos==total`, e inerte no código) — supersedure **parcial**
  (só a cláusula de fatura). **l6 = emenda** ADR-342 (calibração do mecanismo
  l12; não consolidar). **l10 = ADR-344 nova** (piso) — **não** reintroduz
  float-think **se** enquadrado como **roteamento sobre não-certificado**
  (certificado segue zero-cents; não-certificado hoje escala ∞→materialidade =
  estritamente mais estrito); piso **global único** (respeita veto DE contra
  per-banco). **Selo (E2→E5) = [[ADR-345]] nova** (read-path) → deferida a
  REPORT_TRUST. **Coerência de threshold:** selo dispara em "escalado OU
  gap>piso", nunca `gap≠0` cru (senão ruído de arredondamento). Ordem: ADR-343/344
  `Proposto` antes do impl; l6 só referencia (emenda + impl mesmo PR).
- **data-engineer:** **[[A39.l7]] MISFRAMES — cortar wise+rico** (derivam saldo
  `round(saldo_final−Σtx)` → gate nunca dispara = selo falso, contradiz docstring
  ADR-342); sweep = `itau_xls`+`santander_xls`. **[[A39.l6]] MISFRAMES parcial** —
  Itaú CDB PDF emite posição única sem total agregado → `total_declarado=None` →
  `skipped_no_total` (não checksum); só Santander xlsx tem total independente;
  KR conta `checksum_ok` **≠** `skipped`. Schema: aditivo declarar `total_fatura`/
  `checksum_ok` (`additionalProperties:true`, sem bump). **KR-B "%completo" não é
  conceito de schema** (métrica do harness/selo). **[[A39.l5]] fora dos vereditos
  anteriores** — R$1 não confirmado no código; **confirmar evidência antes de
  enquadrar**. Órfãos: quarentena **inerte no read-path do artefato** (4 pontos),
  não `documents.status`.
- **financial-planner:** materialidade **faturas > conservação C6 > bradesco**
  (fatura viesa **otimista**: despesa↓→poupança↑, pior modo). **KR-C precisa de
  companheiro de valor** (não só contagem 36/36 — escalar tudo bate o KR com zero
  despesa verificada). **Propagação E2→E5 é load-bearing** (sem ela KR-A é
  cosmético na camada de KPI) → registrada como dependência deferida ([[ADR-345]]),
  não descartada. Posições de investimento perdidas corrompem patrimônio →
  [[A39.l9]] é **P1**, não P2.
- **prompt-engineer:** a chamada LLM roda em **`temperature=1.0`** (sem seed) —
  certificar classificador não-determinístico mede ruído → **temp=0 é P0 real**
  ([[A39.l11]], ADR própria, muda runtime compartilhado). **itau_fatura +
  investimentosposicao = lacuna de regex, não caso de LLM** — TypeRule
  determinístico (caminho A da ADR-081; pagar LLM por tipo recorrente é bug
  financeiro) → [[A39.l8]]/[[A39.l9]]. **Binance = falta de consumer stage** (não
  classificação) e **rico .xlsx = possível lacuna de extração de preview** →
  separados em [[A39.l12]]. Telemetria `mathoms.llm.classification.*` (prompt
  hash, tokens, confidence, needs_review rate) para drift.

## Origem e âncoras

Relatório: `_scratch/parse-certify-5at5-2026-07-23.md`. Baseline durável:
`storage/<uuid>/certify/financial_statements-2026-07-23.json`. Contrato que as
lanes emendam: [[ADR-342]]. Cauda reconciliada: [[MOC-sprint-a38]].

---

## Fechamento (2026-08-04) — disposição autoritativa

A A39 é fechada pela abertura da [[A42]], sua sucessora declarada na mesma tese
`ingest-trust`. Motivo: manter duas sprints `candidate` com a mesma tese, sobre os
mesmos arquivos, cria duas fontes de verdade — exatamente o que o roteamento da A42
existe para evitar. Precedente: a própria A39 fez isso com a cauda da [[MOC-sprint-a38]].

**Lanes:** 12 de 13 `shipped` (l1–l12). Disposição do restante e dos resíduos:

| Item | Estado em 2026-08-04 | Disposição |
|---|---|---|
| [[A39.l13]] — re-route da classificação pelo choke-point de LLM | `planned`, nunca pescada | **`cancelled`** por duplicação: é a [[A41.l2]], que já é dona dos mesmos arquivos e nasceu com o escopo completo |
| [[A39.l3]] c2 (opt-in de fatura) + [[A39.l8]] (parser determinístico) | A §Deferido acima (escrita 2026-07-23) os declara bloqueados na identidade do checksum | **Já entregues — o deferimento durou um dia.** A [[ADR-342]] §Emenda **2026-07-24** decidiu a identidade (**por seção**, `escopo` declarado no schema) e ligou os dois parsers, `parse_santander_unique` e o novo `parse_itau_fatura`, com o corpus real **fechando a cent e zero falso-fire**, em co-design com `financial-planner`. Nada a adotar |
| [[A39.l6]] residual — traço positivo do checksum | Emitido pelo produtor e declarado no schema; nunca lido pelo harness | **Adotado** por [[A42.l3]] |
| §Deferidos — propagação E2→E5 e selo de qualidade, gated por [[ADR-345]] | Nota `Roadmap`, adoção deferida | **Gatilho de retomada registrado** por [[A42.l2]]. A condição escrita na nota ("quando um achado de revisão demonstrar número de origem degradada chegando ao usuário sem sinal") foi satisfeita pelo §r2. Registrar o gatilho é docs-only; promover a nota exige design ([[ADR-358]]) |
| §Deferidos — reconciliação de órfãos no DB e quarentena inerte no read-path | Roteado para A40 | Permanece com a [[A40]]; sem mudança |
| §Deferidos — cauda da A38 não surfada no corpus | Roteado para A40 | Permanece; sem mudança |

**KRs:** atingidos como registrado acima (KR-A ✅, KR-B 6 parsers, KR-C/D
observabilidade + gate escopo-aware). O que a A39 **não** provou — e a [[A42]] assume
como tese — é que os instrumentos que declaram esses KRs não dão verde sem medir: o §r2
achou o gate de conservação de um parser suprimido por conclusão do próprio parser,
introduzido **depois** do fechamento das lanes desta sprint.
