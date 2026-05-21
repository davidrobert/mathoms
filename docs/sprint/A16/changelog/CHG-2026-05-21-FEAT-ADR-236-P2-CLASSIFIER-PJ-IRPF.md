---
id: CHG-2026-05-21-FEAT-ADR-236-P2-CLASSIFIER-PJ-IRPF
type: changelog-entry
date: "2026-05-21"
sprint: A16
lane: "[[TRACK-a16-adr236-tributario-pj-cascata]]"
adrs: ["[[ADR-236]]"]
summary: |
  feat(adr-236 P2): classifier E4 com 5 labels PJ-side + leitor IRPF
  base PGBL canônica (Sprint A16 L2 P2 — ADR-236 fase 2 de 6).
tags:
  - type/changelog-entry
  - sprint/a16
  - area/methodology
  - area/pipeline
---

# feat(adr-236 P2): classifier E4 PJ labels + leitor IRPF (Sprint A16 L2 P2)

P2 de 6 fases da L2 (`tributario-pj-cascata`) — fornece os inputs derivados
(pró-labore, lucros distribuídos, DAS, folha PJ, ISS) que o calculator P3
vai agregar, mais o leitor de renda tributável PF (base PGBL canônica).
[[ADR-236]] permanece `Proposto` até P6 fechar (cutover + telemetria + flip).

**Decisão arquitetural pré-P2 (scouting 2026-05-21, co-design `senior-cto`):**
opção (b) `pj_source_mapping` como proxy PJ-side. [[ADR-236]] §D2
originalmente assumia `account_type=PJ` + `member_key=titular_pj` —
conceitos que não existem em
[pipeline/domain/services/transaction_classifier.py](../../../../pipeline/domain/services/transaction_classifier.py).
Em vez de schema migration cross-stack (opção a, ~1.5d), reusamos
`pj_source_mapping` já consumido por `IncomeOriginResolver` desde A3a.
Mapping vira contrato de 2 consumidores; upgrade-path para schema
explícito preservado se gate dogfood ficar < 90% precisão. Decisão
documentada em commit `docs(adr-236):` separado antes do PR de código.

**Entregue:**

- [pipeline/domain/services/transaction_classifier_pj.py](../../../../pipeline/domain/services/transaction_classifier_pj.py) (NOVO) —
  isola lógica PJ-side: `PJ_LABELS` (conjunto fechado), `PJLabelConfig`,
  `RunContext`, `try_classify_pj_label` (precedência `pro_labore` → `das` →
  `iss` → `folha_pj` → `lucros_distribuidos`), `FolhaPJProxyUnavailable`
  warning tipado ([[ADR-097]] D1).

- [pipeline/domain/services/transaction_classifier.py](../../../../pipeline/domain/services/transaction_classifier.py) —
  `ClassifierConfig` aceita `pj_label_config`. `TransactionClassifier`
  ganha `classify_all_with_warnings(accounts) -> (list, list[Warning])`
  com pre-pass run-level que detecta `has_pj_income`. API antiga
  (`classify_account`, `classify_all`) preservada (descarta warnings).

- [pipeline/domain/services/tributario/irpf_renda_tributavel.py](../../../../pipeline/domain/services/tributario/irpf_renda_tributavel.py) (NOVO) —
  primeiro deliverable do package tributário.
  `extract_renda_tributavel_pf` agrega base PGBL canônica =
  `rendimentos_pj[].rendimentos_tributaveis_brl + rendimentos_pf[].valor_brl`
  do artifact `extract_irpf_full` ([[ADR-157]],
  [config/schemas/e16_irpf_full.schema.json](../../../../config/schemas/e16_irpf_full.schema.json)).
  Exclui 13º (tributação exclusiva), lucros isentos e exterior — V1 cobre
  só "ficha Rendimentos Tributáveis". Money em Decimal string ([[ADR-090]]).

- **Degradação graciosa de `folha_pj`:** quando `pj_source_mapping` vazio
  ou nenhuma receita PJ observada no run, label não é atribuída + 1
  `FolhaPJProxyUnavailable` warning é emitido por run (agrega todas as
  candidatas). Telemetria distingue ausência real de proxy desabilitado.

- **Tests** (+26 novos; 48 verdes totais):
  - [tests/unit/pipeline/test_transaction_classifier_pj_labels.py](../../../../tests/unit/pipeline/test_transaction_classifier_pj_labels.py)
    — 16 casos: 5 labels happy-path + word-boundary regression (DAS vs
    ADASA, ISS vs DEMISSAO) + 2 cenários de warning + multi-account.
  - [tests/unit/pipeline/test_irpf_renda_tributavel.py](../../../../tests/unit/pipeline/test_irpf_renda_tributavel.py)
    — 10 casos: agregação + precisão decimal + casos vazios/parciais +
    robustez (float rejeitado, items malformados) + exclusão de
    13º/isentos/exterior.

- **`docs/adr/236-tributario-pj-cascata-fiscal-canonica.md` atualizada
  pré-código** (commit `docs(adr-236):` 72428c3e): §D2 corrige nomes
  do schema E1.6 (`rendimentos_tributaveis_brl` em vez de
  `valor_liquido`; `valor_brl` em vez de `valor`) + documenta opção (b)
  como discriminador V1 PJ-side + sinaliza `folha_pj` como discriminador
  mais fraco mitigado por warning tipado.

- **`dev/code_style_baseline.json` atualizado.** Novo módulo
  `transaction_classifier_pj.py` introduz funções que disparam contadores
  de `P1_long_functions` (`try_classify_pj_label`, `_build_run_context`)
  e `P5_float_money` (`_classified_transferencia(valor)` legacy do JSON
  E3). ADR-090 incidence é em domínio crítico (`Money`), não nesses
  helpers de I/O.

**Não-objetivos (escopo de fase):**

- Calculator canônico `cascata_calculator.py` + 4 goldens — vem em **P3**.
- Migration v2 `category_template` com as 5 labels — diferida. Labels
  saem como categoria-livre em `ClassifiedTransaction.categoria`; P3
  agrega por nome. v2 só é útil quando UI/admin reconhecer as labels
  (defer para P5).
- Adapter `bundle["tributario"]` + narrator reescrito — vem em **P4**.
- `<CascataFiscalCard/>` UI + co-design `product-designer` — vem em **P5**.
- Telemetria estruturada + flip ADR — vem em **P6**.

**Próximo:** P3 — calculator canônico (~2d eng) em branch
`agent/a16-adr236-tributario-pj-cascata-P3/*`. Cobre 4 regimes V1
(Simples Anexo III/V, Lucro Presumido, MEI) + fator-R derivado + base
PGBL a partir do leitor IRPF entregue em P2.
