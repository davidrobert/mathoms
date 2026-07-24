---
id: ADR-346
type: adr
title: "Identidade de posição de renda variável (ticker+proprietário) + null-não-soma no consolidador"
status: Proposto
phase: A39.l9
date: "2026-07-24"
relates_to:
  - "[[ADR-271]]"
  - "[[ADR-287]]"
  - "[[ADR-342]]"
  - "[[ADR-246]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/dados
  - methodology/patrimonio
---

# ADR-346 — Identidade de posição de renda variável + null-não-soma

**Status:** Proposto (A39.l9) · **Data:** 2026-07-24 · **Lane:** [[A39.l9]] (P1)

> **Proposto** — abre o eixo de identidade de RV e a semântica `null-não-soma`
> antes do PR de implementação (política P0/P1). Reformulada após **dois rounds de
> co-design** (data-engineer + financial-planner + senior-cto árbitro): o primeiro
> revelou que o patrimônio nasce de um **source-switch em E5**, não da lista de
> posições do E4; a **revisão de painel** (completude/corretude/consistência/
> robustez/precisão, foco em perda silenciosa) achou que o próprio texto original
> introduzia inflação (chave de dedup) e uma classe de perda-com-invariantes-verdes
> (membro ≥3). Este documento incorpora as correções bloqueantes. Flippa para
> `Decidido (A39.l9)` no merge da implementação. Tamanho >150 linhas justificado:
> contrato multi-stage (E2→E4→E5) com invariantes testáveis por vetor de perda.

## Contexto

A certificação de parse ([[A39.l9]], adota [[A38.l13]]) achou 2 documentos de
investimento em conf 0.0 que corrompem patrimônio silenciosamente: custódia/
"Posição Acionária" (papel + **quantidade, sem valor de mercado**) e carteira
consolidada valorada (XLSX, **instituição vazia**). Mesmos papéis+qtd nas 2
fontes → dupla contagem latente.

**Diagnóstico verificado no código:** `total_por_membro` (o número que vira
patrimônio) **não é Σ posições** — é **Σ dos totais por fonte** (`total_fonte`),
com fallback a `positions_sum` só quando o total é 0
([`investments_consolidator.py`](../../pipeline/domain/services/investments_consolidator.py):281-300).
O PL de produção é montado em **[`patrimonio_calculator.py`](../../pipeline/domain/services/patrimonio_calculator.py):301-337**
(DB-first; lê **só** `total_por_membro`; fallback IRPF por membro só quando o
total é exatamente 0, `:323`). `analyze_finances.py:983-1035` é o **script legado
de paridade** (mesma lógica, não o caminho de produção). Consequências que o
design de [[A38.l13]] não encarava:

- **"Colapsar na valorada" é no-op sobre o PL** — a custódia só-qtd já contribui
  0. Colapsar corrige a **listagem** (`n_posicoes`/top-ativos), não o número.
- **Deflação do membro misto (buraco vivo):** membro com carteira valorada **+**
  ações que só existem na custódia → `total_por_membro > 0` → fallback IRPF não
  dispara → as ações da custódia somem do PL sem sinal. A flag `posicao_sem_marcacao`
  **nasce morta** se o cálculo de PL de produção não a lê.
- **Perda com invariantes verdes (membro ≥3):** o E5 consome **só** titular/
  cônjuge/não-atribuído. Um 3º membro (dependente com RV) tem `total_por_membro>0`
  no E4 (conservação E4 verde) mas **nunca é consumido no E5** → some do PL, e não
  há snapshot de membro para receber a ressalva.
- **`instituicao=""` descarta fonte valorada inteira:** o dedup source-level
  (`:224-230`) colapsa por `(instituicao_norm, membro)` mantendo o `data_ref` mais
  recente; duas fontes valoradas inst-vazia colidem na chave `("", membro)` e uma
  é descartada silenciosamente.

`$defs/posicao_investimento`, `posicao_sem_marcacao`, `_resolucao_rv` **não
existem** hoje — serão **criados**.

## Decisão

Eixo de identidade novo para RV + `null-não-soma` como **observabilidade
forward-only**, escopo honesto: esta ADR corrige de-duplicação de **listagem**,
honestidade de contagem/checksum, e **converte perda/inflação silenciosa em
ressalva visível**; **não** corrige o número do PL do membro misto (depende de
valoração emprestada, V2). Ordem numerada = contrato (passo N não depende de N+k).

0. **Roteamento (passo 0 — a perda começa antes do consolidador):**
   `investimentosposicao` **e** `carteirarendafixa` entram em `is_investment_type`
   (branch always-include, [`registry.py`](../../scripts/e2/registry.py):84-86 /
   `_INVESTMENT_PATTERNS`), como `cdbresumo` — hoje o `NON_STATEMENT_TYPES`
   ([`extract_bank_documents.py`](../../scripts/extract_bank_documents.py):89) os
   **dropa no discovery**. Sem parser determinístico registrado em
   `scripts/e2/banks/`, degradam **explicitamente** para `e2_llm_artifact` (o
   item 8 vale para ESSE schema). `_INVESTMENT_POSITION_TYPES`
   ([`e4_categorizer_adapter.py`](../../pipeline/domain/services/e4_categorizer_adapter.py))
   e a lista de chaves-de-array aceitas (`posicoes|composicao|investimentos`) são
   **contrato**: o parser DEVE emitir `tipo` na tupla e o array numa dessas chaves.
1. **Discriminante de eixo (mecânico, escopo E2):** posição com **identificador de
   mercado** (ticker B3 `^[A-Z]{4}\d{1,2}$` ou ISIN) → **eixo de dedup por
   identificador** (`identificador + proprietário`); sem identificador → **só**
   dedup source-level (passo 4) — **não** invoca a máquina de `descricao_norm` da
   [[ADR-271]] (estágio disjunto: 271 opera no baseline IRPF E1.5c). Escopo V1 =
   B3 + ISIN; fora disso → **never-fund**. Agrega quantidade por `(identificador,
   proprietário, fonte)` **antes** do match (sufixo fracionário não dispara (c) falso).
2. **Resolução tabelada** (calibração [[ADR-271]] "na dúvida, não funde"): (a)
   mesmo id+qtd, 1 fonte valorada + outra só-qtd → **colapsa na valorada** (corrige
   listagem; no-op no PL); (b) 2+ fontes **valoradas** mesmo id+**mesma** qtd →
   flag `possivel_posicao_espelho` **+ ressalva de PL** (`pl_possivel_superestimado`
   no membro — o total soma ambas as fontes em Leitura A, então o PL está inflado
   até V2; a ressalva torna a inflação **visível**, simétrica ao badge de deflação);
   (c) qtd **diferente** pós-agregação → **never-fund, sem flag espelho** — mas se
   os **dois** lados forem valorados, emite `pl_possivel_superestimado` (o total
   soma os dois). Proprietário com resolução incerta → não colapsa.
3. **`null-não-soma` = Leitura A (observabilidade, não rebaseline):**
   `total_por_membro` **permanece source-level** (Σ `total_fonte`). A coerção
   `valor = float(valor) if valor else 0.0`
   ([`investments_consolidator.py`](../../pipeline/domain/services/investments_consolidator.py):258)
   **DEVE detectar `None` antes de zerar** e carregar `posicao_sem_marcacao=true`
   no item de `dados`, sem alterar a aritmética (`None` continua contribuindo 0).
   `posicao_sem_marcacao := valor original is None` — **nunca** `valor_atual == 0`
   (zero legítimo de posição liquidada é valorado). **Forward-only, sem backfill.**
   Golden de valor que mexa ⇒ escorregou para Leitura B → **pare** ([[ADR-287]]).
4. **Fix `instituicao=""` = resolução de instituição, NÃO `data_ref` na chave:** a
   chave do dedup source-level **permanece `(instituicao_norm, membro)` com
   most-recent-`data_ref`-wins** (`:229`). Adicionar `data_ref` à chave **quebra** o
   dedup de snapshots temporais (Dez/24 + Mar/25 do mesmo broker → somam → PL 2×) —
   é inflação silenciosa e regressão. O fix é resolver a instituição para valor
   **nunca-vazio** (marcador na planilha / rótulo canônico / **fallback ao
   `artifact_key`**, identidade de fonte estável); duas fontes distintas obtêm
   chaves distintas sem un-dedup temporal. `data_ref` é tie-break e telemetria,
   **nunca** componente de chave. Todo descarte no colapso `(inst,membro)` é logado
   (vencedor/perdedor); fontes distintas que colidiriam escalam WARN, não descarte mudo.
5. **Propagação para o cálculo de PL de PRODUÇÃO (invariante bloqueante):** a
   ressalva aterrissa em **`PatrimonioCalculator`/`E5AnalyzerAdapter`** (não em
   `analyze_finances.py`, que é o demonstrador legado) como **campo nomeado no
   payload E5 por membro**: `posicoes_sem_marcacao: {count, tickers}` + `pl_ressalva:
   bool`, consumível por `desvio_max_pct`/derivados. O número é **renderizado com
   ressalva** (melhor estimativa disponível) — **nunca suprimido** (supressão
   propaga zero em `total_geral`). Exceções ao rebaixamento do selo: (i) piso de
   materialidade [[A39.l10]] — exposição das posições sem-marcação abaixo do piso
   → flag por-posição fica em `dados` (auditável), selo não rebaixa; (ii) membro
   cujo fallback IRPF já valora o mesmo holding → marcação é `info`, não rebaixa.
   A resolução (a/b/c) roda no **E4**, antes de `reserva_liquidez`/
   `passive_income_calculator` lerem `dados`.
6. **Checksums** (reuso [[ADR-342]], int cents tol-zero, WARN-first): carteira XLSX
   `Σ round(valor*100) == valor bruto de mercado declarado` **só quando o escopo
   casa as linhas**. O anchor é **valor bruto atual** ("Valor Bruto"/"Saldo Bruto"/
   "Patrimônio"/"Posição") — **nunca** "Total investido"/"Valor Aplicado" (custo de
   aquisição; ancorar nele deflaciona o PL pelo ganho não-realizado). Planilha
   só-custo → WARN `valor_apenas_custo`, não certificar. Posição acionária só-qtd →
   checksum de **contagem** (`raw_papeis_detected == |posições|`), sem valor.
7. **Proventos (V1 = categorizar, dois lados):** (i) JCP/dividendo **reconhecido**
   → categoria `proventos`, fora da base de poupança, distinção JCP×dividendo
   preservada; NÃO vira KPI de renda passiva em V1 (a renda passiva é IRPF-derived
   — dobraria). (ii) provento **não-reconhecido** (regex/config não pega) →
   `needs_review`/bucket não-operacional, **nunca** receita que alimenta taxa de
   poupança. Accrual/rendimento nunca é receita.
8. **Schema (criar E wire-ar — `$defs` sozinho valida NADA):** criar
   `$defs/posicao_investimento` (`quantidade`, `identificador`/`ticker_norm`, `isin`
   nullable, `valor_atual: ["number","null"]`, `posicao_sem_marcacao: bool`,
   `_resolucao_rv`, `raw_papeis_detected`) **e** declarar a propriedade de array
   (`posicoes`) com `items: {$ref}` em **`e2_extract` E `e2_llm_artifact`** (ambos
   os caminhos de chegada). No `e4_unified`, **branch `oneOf` dedicado** discriminado
   (o `dados: {}` compartilhado com patrimônio não aperta). No `e5_analysis`, os
   campos `posicoes_sem_marcacao`/`pl_ressalva` (item 5). Confirmar `SCHEMA_BY_STAGE`
   ([`db_artifact_store.py`](../../backend/app/services/storage/db_artifact_store.py):484)
   mapeia o stage de escrita — senão a validação é passthrough. Campos novos são
   **opcionais/nullable no PR1** (produtores em PR3).

## Faseamento (contrato de sequenciamento)

Um estado intermediário pior-que-hoje é perda silenciosa. Ordem **obrigatória**:

- **PR1** — resolução de instituição + dedup corrigido (passo 4) + criar/wire
  `$defs` **aditivo-opcional** (campos nullable). Sem levantar o discovery gate.
- **PR2** — `null-não-soma` (preservar `None`, passo 3) + partição de contagem +
  propagação do campo de ressalva para `PatrimonioCalculator` (passo 5). **Badge
  vivo antes** de qualquer doc de posição fluir.
- **PR3** — TypeRules (Posição Acionária / carteira) + parsers determinísticos +
  resolução RV (a/b/c) + checksums + **lift do discovery gate** (acoplado aqui:
  nenhum subtipo é liberado sem parser) + flip strict dos campos novos.

Abrir o gate em PR1/PR2 joga `investimentosposicao`/`carteirarendafixa` no E2-llm
(custo premium + extração possivelmente errada alimentando o PL) ou em
`needs_review` em massa — "ausente" (hoje) vira "errado-com-cara-de-certo".

## Invariantes testáveis (a implementação DEVE cravar)

0. **Conservação parse→load:** `n_artefatos_tipo_posição (E2) == n_carregados
   (consolidador)`; todo skip em `load_investment_positions`/Phase-1 logado (stage,
   key, motivo). Fecha a perda antes do passo 1.
1. **Partição MECE (sobre a flag, não sobre `valor_atual`):** `n_posicoes ==
   |valoradas| + |sem_marcacao|`, disjuntos; `sem_marcacao := posicao_sem_marcacao`.
   Fixture positiva (custódia só-qtd) assere `|sem_marcacao| > 0` e `valor_atual is None`.
2. **Conservação de resolução + descarte:** `count_before − Σ colapsadas ==
   count_after`; toda key colapsada (resolução a/b/c) **e todo descarte do dedup
   source-level Phase-2** logados (origem→destino). Idempotência: 2× == 1×.
3. **`total_por_membro` inalterado (Leitura A):** diff dogfood de `total_por_membro`/
   `patrimonio_liquido` pré/pós = **zero**, **com fixture sintética de 2 snapshots
   mesmo `(inst,membro)` datas distintas** (prova que não somam). `total_geral == Σ
   total_por_membro`. `tests/test_e5_conservation_invariants.py` verde.
4. **`instituicao=""` nunca descarta:** 2 XLSX valoradas inst-vazia mesmo membro →
   após resolução, chaves distintas → 0 fonte perdida **e** não somadas como
   portfolios distintos.
5. **Resolução:** (a) colapso exige id+qtd idênticos pós-agregação; (c) qtd
   diferente → **never-fund sem flag espelho**; `possivel_posicao_espelho` é
   **exclusivo** do caso (b) [2+ valoradas, mesma qtd].
6. **Discriminante:** posição sem identificador nunca entra na dedup por
   identificador; **nenhuma posição E2 entra na máquina `descricao_norm` da
   ADR-271** (estágios disjuntos).
7. **Cobertura de membros no PL (fecha perda-com-invariantes-verdes):** todo
   `membro` com `total_por_membro > 0` no E4 é consumido pelo PL do E5 **ou** emite
   `membro_rv_orfao` no payload — nunca drop silencioso. Testável: `Σ(investimentos_<m>
   consumidos no E5) == total_geral`. (V1 pode não *projetar* >2 membros, mas a
   ausência é sinalizada.)
8. **Propagação (bloqueante):** `posicao_sem_marcacao` num membro (acima do piso
   [[A39.l10]] e não coberto por fallback IRPF) ⇒ `pl_ressalva=true` **e**
   `posicoes_sem_marcacao.count == |sem_marcacao| do membro` no payload E5;
   `PatrimonioCalculator` não emite "certificado" para esse membro. Teste assere
   presença + igualdade da contagem.
9. **Inflação simétrica visível:** espelho (b) e (c)-2-valorados ⇒
   `pl_possivel_superestimado` no payload do membro (não só WARN de posição).
   Posição conjunta A(broker) + B(fallback IRPF) mesmo `(inst,id)` ⇒ WARN
   `possivel_co_declaracao_rv` + ressalva. Nenhuma inflação silenciosa.
10. **Poupança/TRS + provento:** incluir/excluir linha JCP **reconhecida** não move
    taxa de poupança recorrente nem TRS IRPF-derived; provento **não-reconhecido**
    injetado **não** move a taxa de poupança (cai em não-operacional).

## Consequências

- **PL do membro misto: subestimado-com-ressalva** (badge) em V1 — o menor mal vs
  deflacionado-em-silêncio (hoje) ou estimado-com-cotação-externa (fabrica precisão
  sem feed). Ordem: valoração emprestada intra-workspace (V2) > subestimado-com-
  ressalva (V1) >> cotação externa >> silêncio.
- **Limitação V1 de membros:** o PL projeta titular+cônjuge (+não-atribuído→titular);
  RV de dependente/3º membro é deflação-**com-ressalva** (`membro_rv_orfao`), fusão
  multi-membro é V2. Alinha [tenancy](../reference/tenancy.md) (workspace = família > casal).
- **Posição conjunta entre membros:** guard V1 = WARN `possivel_co_declaracao_rv`
  (não dobra silencioso); fusão 50/50 é V2 (análogo [[ADR-246]]).
- **Ambos os subtipos** (`investimentosposicao` + `carteirarendafixa`) saem do
  bloqueio de discovery — via parser determinístico (PR3), nunca antes.
- Rollout WARN→HARD por parser; caminho certificado permanece cents tol-zero.

## Alternativas rejeitadas

- **`data_ref` na chave de dedup:** ineficaz p/ inst-vazia de mesma data e regressão
  de dupla-contagem de snapshots temporais. Fechado pelo árbitro (senior-cto).
- **Leitura B (`total_por_membro` = Σ posições):** quebra paridade com o total da
  fonte (caixa/RF não-itemizados) e é rebaseline de valor ([[ADR-287]]) disfarçado.
- **Estimar valor da custódia (qty × cotação externa):** fabrica precisão sem feed
  mantido; ancora número stale. V2 (build-vs-buy).
- **`Document.needs_review` para espelho:** bloqueia o pipeline por 1 posição
  ambígua. Preferida flag de posição + ressalva de PL.
- **Promover proventos a renda passiva em V1:** dobra com a base IRPF. V2.
- **Lift do discovery gate antes do parser determinístico:** troca "ausente" por
  "errado-com-cara-de-certo" (pior modo, [[ADR-342]]).

## Follow-ups V2 (registrados)

Valoração emprestada intra-workspace · feed de cotação externa RV · reconciliação
proventos-extrato × renda-passiva-IRPF · auto-resolução entre 2 fontes valoradas
idênticas · projeção multi-membro (>casal) no PL + fusão 50/50 de posição conjunta
([[ADR-246]]) · identidade RV internacional/offshore (BDR↔subjacente) · split/
bonificação como reconciliação de qtd · FII/ETF/unit no ticker "11" no bucketing.
