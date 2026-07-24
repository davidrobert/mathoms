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
> antes do PR de implementação (política P0/P1). Reformula o design travado no
> planejamento de [[A38.l13]] após co-design (data-engineer + financial-planner)
> revelar que o número que corrompe o patrimônio nasce num **source-switch em
> E5**, não na lista de posições do E4 — logo várias regras do design original
> eram no-op sobre o PL. Flippa para `Decidido (A39.l9)` no merge da implementação.

## Contexto

A certificação de parse ([[A39.l9]], adota [[A38.l13]]) achou 2 documentos de
investimento que caem em conf 0.0 e corrompem patrimônio silenciosamente:
custódia/"Posição Acionária" (papel + **quantidade, sem valor de mercado**) e
carteira consolidada valorada (XLSX, sai com **instituição vazia**). Os mesmos
papéis+quantidade aparecem nas duas fontes → dupla contagem latente.

**Achado do co-design que reformula o design travado:** `total_por_membro` (o
número que vira patrimônio) **não é Σ posições** — é **Σ dos totais declarados
por fonte** (`total_fonte`), com fallback a `positions_sum` só quando o total da
fonte é 0 ([`investments_consolidator.py`](../../pipeline/domain/services/investments_consolidator.py)
:281-300). E o PL por membro é escolhido por um **source-switch em E5**
([`analyze_finances.py`](../../scripts/analyze_finances.py):980-1035): usa o total
do broker se `> 0`, senão cai no baseline IRPF. Consequências que o design de
[[A38.l13]] não encarava:

- **"Colapsa na valorada" é no-op sobre o PL** — a custódia só-quantidade já
  contribui 0 para `total_por_membro`. Colapsar corrige a **listagem**
  (`n_posicoes`/top-ativos), não o número do patrimônio.
- **A deflação real do membro misto é o buraco vivo:** membro com carteira
  valorada **+** ações que só existem na custódia → `total_por_membro > 0` → o
  fallback IRPF **não** dispara → as ações da custódia somem do PL sem sinal.
  Uma flag `posicao_sem_marcacao` no E4 **nasce morta** se E5 não a lê.
- **`instituicao=""` (Rico) é perda silenciosa, não só ruído:** o dedup
  source-level (`:224-230`) colapsa por `(instituicao_norm, membro)` mantendo o
  `data_ref` mais recente; duas fontes valoradas com instituição vazia colidem
  na chave `("", membro)` e **uma é descartada inteira**, silenciosamente.

`$defs/posicao_investimento` **não existe** hoje (a premissa "estender" de
[[A38.l13]] é factualmente errada) — será **criado**.

## Decisão

Eixo de identidade novo para RV listada + `null-não-soma` como **observabilidade
forward-only**, com escopo honesto: esta ADR corrige de-duplicação de
**listagem** + honestidade de contagem/checksum + propaga a marcação faltante
para o E5; **não** muda o número do PL do membro misto (isso depende da valoração
emprestada, follow-up).

1. **Eixo de identidade RV** (separado de [[ADR-271]], que cobre RF/genérico via
   baseline IRPF E1.5c): chave = `ticker_norm + proprietário`. Discriminante
   **MECE**: posição com `ticker_norm`/ISIN válido → eixo RV; sem → eixo
   ADR-271. Ambíguo → ADR-271 (lado seguro). Escopo V1 = **B3 + ISIN**; sem
   match → **never-fund** (trata como distinta; não funde ativos diferentes).
   Normalização agrega quantidade por `(ticker_norm, proprietário, fonte)`
   **antes** do match (colapso de sufixo fracionário não pode disparar (c) falso).
2. **Resolução tabelada** (calibração [[ADR-271]] "na dúvida, não funde →
   escala"): (a) mesmo ticker+qtd, 1 fonte valorada + outra só-qtd → **colapsa
   na valorada** (corrige listagem; no-op no PL); (b) 2+ fontes **valoradas**
   mesmo ticker+qtd → flag `possivel_posicao_espelho` (WARN de posição, **não**
   `Document.needs_review` que bloqueia o pipeline); (c) qtd diferente pós-
   agregação → **nunca funde**. Proprietário com resolução incerta entre fontes
   → não colapsa (evita join de membro que sabidamente falha).
3. **`null-não-soma` = Leitura A (observabilidade, não rebaseline):**
   `total_por_membro` **permanece source-level** (Σ `total_fonte`); `null-não-
   soma` opera sobre o **checksum** e a **partição de contagem**, nunca sobre o
   número do PL. Posição com `valor is None` = listada em `dados`, contada em
   `n_posicoes`, flag `posicao_sem_marcacao`, fora de qualquer soma. **Forward-
   only, sem backfill** (E4 é recompute puro sobre E2). Se algum golden de valor
   mexer, escorregou para "Leitura B" (Σ posições) → **pare** e aplique a
   disciplina [[ADR-287]] (commit isolado + manifesto + conservação).
4. **Fix do buraco `instituicao=""` ANTES de confiar no dedup:** resolver a
   instituição da carteira (marcador na planilha / rótulo canônico / derivar do
   `artifact_key`); **instituição vazia nunca é chave que descarta** — duas
   fontes valoradas inst-vazia do mesmo membro → ambas preservadas. Dedup
   source-level passa a keyar por `(instituicao, membro, data_ref)`.
5. **Propagação E2→E5 (invariante bloqueante, não follow-up):**
   `posicao_sem_marcacao` num membro ⇒ o snapshot E5 daquele membro carrega
   badge/warn (não renderiza PL "certificado" sobre base com marcação faltante),
   e `desvio_max_pct`/derivados de patrimônio herdam a ressalva no **payload**
   (não só no card). Segue o precedente [[ADR-342]] §Consequências (propagação
   do estado de escalação). **Sem este item, a flag é dark data e o bug de
   deflação continua vivo.**
6. **Checksums** (reuso emenda [[ADR-342]], int cents tol-zero, WARN-first): carteira
   XLSX `Σ round(valor*100) == "Total investido"` **só quando o escopo do total
   casa as linhas** (se o total é agregado de conta com caixa/RF não-itemizado →
   WARN, não HARD); posição acionária só-qtd → checksum de **contagem**
   (`raw_papeis_detected == |posições|`), sem checksum de valor. Flip HARD por
   parser só após ≥1 sprint de corpus verde.
7. **Proventos (V1 = categorizar e parar):** JCP/dividendo de conta de corretora
   → categoria `proventos`, fora da base de poupança, distinção JCP×dividendo
   preservada (razão fiscal). **Não** vira KPI de renda passiva em V1 — a
   TRS/renda-passiva é IRPF-derived e somaria em dobro (precedência extrato×IRPF
   é V2). Accrual/rendimento nunca é receita.
8. **Schema:** **criar** `$defs/posicao_investimento` (`quantidade`,
   `ticker_norm`, `isin` nullable, `valor_atual: ["number","null"]`,
   `posicao_sem_marcacao: bool`, `_resolucao_rv`) + bump de versão do contrato
   (drift-detection `strict`).

**Ordem de operação é contrato** (testável): fix instituição → dedup source-
level sem descarte silencioso → agregação qtd por ticker/fonte → resolução RV
(a/b/c) → checksum → partição de contagem → propagação E5.

## Invariantes testáveis (a implementação DEVE cravar)

1. **Partição MECE:** `n_posicoes == |valoradas| + |sem_marcacao|`, disjuntos.
2. **Conservação de resolução:** `count_before − Σ colapsadas == count_after`;
   toda key colapsada logada (origem → destino). Idempotência: aplicar 2× == 1×.
3. **`total_por_membro` inalterado (Leitura A):** diff dogfood de
   `total_por_membro`/`patrimonio_liquido` pré/pós = **zero**; `total_geral ==
   Σ total_por_membro`. `tests/test_e5_conservation_invariants.py` verde.
4. **`instituicao=""` nunca descarta:** 2 XLSX valoradas inst-vazia mesmo membro
   → 0 fonte perdida.
5. **Colapso (a) exige qtd idêntica pós-agregação;** qtd diferente →
   `possivel_posicao_espelho`, nunca funde.
6. **Discriminante MECE:** posição sem ticker/ISIN nunca entra na resolução RV;
   ação listada nunca entra no eixo `descricao_norm` da ADR-271.
7. **Propagação (invariante bloqueante):** `posicao_sem_marcacao` ⇒ badge no
   snapshot E5 do membro; PL do membro misto não renderiza "certificado".
8. **Regressão poupança/TRS:** incluir/excluir linha JCP não move taxa de
   poupança recorrente nem TRS IRPF-derived (zero double-count).

## Consequências

- **Blast radius contido:** dogfood + poucos workspaces. PL do membro misto
  fica **subestimado-com-ressalva** (badge) em V1 — o menor mal vs PL
  deflacionado-em-silêncio (hoje) ou estimado-com-cotação-externa (fabrica
  precisão sem feed de preço). Ordem de preferência: valoração emprestada intra-
  workspace (V2) > subestimado-com-ressalva (V1) >> cotação externa >> silêncio.
- **`investimentosposicao` deixa de ser bloqueado no discovery**
  ([`extract_bank_documents.py`](../../scripts/extract_bank_documents.py):89-90):
  hoje o `NON_STATEMENT_TYPES` o dropa antes de rotear — a lane levanta o gate
  para os subtipos com parser determinístico.
- Rollout WARN→HARD por parser; caminho certificado permanece cents tol-zero.

## Alternativas rejeitadas

- **Leitura B (reescrever `total_por_membro` = Σ posições):** quebra paridade com
  o total declarado da fonte (caixa/RF não-itemizados) e é rebaseline de valor
  ([[ADR-287]]) disfarçado de migração. Rejeitada em V1.
- **Estimar valor da custódia (qty × cotação externa) já:** fabrica precisão sem
  feed de preço mantido; ancora o cliente em número stale. V2 (build-vs-buy).
- **`Document.needs_review` para espelho (b):** bloqueia o pipeline inteiro por
  uma posição ambígua. Preferida a flag de posição + WARN.
- **Promover proventos a renda passiva em V1:** dobra com a base IRPF. V2
  (precedência extrato×IRPF).

## Follow-ups V2 (registrados)

Valoração emprestada intra-workspace · feed de cotação externa RV · reconciliação
proventos-extrato × renda-passiva-IRPF · auto-resolução entre 2 fontes valoradas
idênticas · identidade RV internacional/offshore (BDR↔subjacente) · split/
bonificação como reconciliação de qtd · posições conjuntas entre membros
(análogo [[ADR-246]]) · FII/ETF/unit no ticker "11" no bucketing de classe.
