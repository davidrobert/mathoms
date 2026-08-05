---
id: A40.l2
type: lane
title: "Identidade de lançamento cross-documento: tipo_conta com vocabulário divergente + titular vazio"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l2-identidade-lancamento-cross-doc
adrs: ["[[ADR-354]]"]
depends_on: ["[[A40.l1]]"]
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
---

# A40.l2 — `identidade-lancamento-cross-doc` (RV3-01 · Crítico)

> ⚠️ **Leia a §Problema antes de codar.** O mecanismo publicado originalmente no
> [[REPORT-REVIEWS-active]] estava **errado** e foi corrigido pelo painel. A
> versão errada leva a um fix que é **no-op** e fecha verde.

> 🔴 **Segunda correção de mecanismo — 2026-08-05.** O [[LEDGER-CERTIFY-active]]
> §r4 (2026-08-04) **eliminou 4 dos 5 desenhos de fix** do §Escopo original. O
> defeito medido não mudou; o mecanismo mudou de *canonicalizar a montante* para
> *colapsar por transação antes do agrupamento*. O §Escopo abaixo foi reescrito e
> a decisão está na **§Emenda de [[ADR-354]]** (2026-08-05). O plano de 5 PRs
> que estava aqui até 2026-08-04 colapsaria ~48% do defeito **ou** apagaria dado
> legítimo — não o siga a partir de histórico de PR antigo.

## Medição herdada da [[A40.l1]] (instrumento pronto, baseline congelado)

O detector cross-grupo mediu o defeito desta lane no corpus dogfood. **Não
re-meça do zero — parta daqui:**

- **261 ocorrências**, Σ excesso 81.288.000 cents. `carrier-shaped=261`,
  `coincidence-shaped=0`.
- Composição **exaustiva**: `banco` preenchido e **idêntico** nas duas pernas ·
  `titular` **parcial** (preenchido numa, vazio na outra) · `tipo_conta` no par
  `('extrato','extratoconta')` · `(2 rows, 2 provs)` em 100%.
- **`banco` não diverge em nenhuma das 261** — confirma a decisão nº 1 do painel
  e sepulta o mecanismo original do achado.
- **Blast radius da re-ancoragem: 5 overrides** julgáveis (+7 quarentenados,
  inertes). O passo de re-ancoragem é muito mais barato que o desenho assumia.
- Baseline congelado off-git em `storage/<uuid>/ledger_certify/` (path e valores
  fora do git, [[ADR-343]]).

**Como provar o fix:** re-rodar `dev/certify_ledger_local.py <ws>` e comparar o
numerador contra 261. A l1 deixou **8 ratchets — 4 re-confirmados manualmente, 4
só com a prova do implementador** (ver [[A40.l1]] §Fechamento, residual 4) —,
então filtro ou cap silencioso **no numerador** quebra teste em CI (grupo
`dev_tools` no `ci.yml`).

> ⚠️ **Furo conhecido do instrumento que você vai usar como prova.** Os caps de
> **comprimento** do render não têm ratchet: `dev/ledger_cross_group_render.py:118`
> e `:124` (histogramas, 12), `:126` (`_fmt_occurrences(hits, 20)`) e `:137`
> (cap 8). Os ratchets existentes pinam o **numerador impresso**
> (`test_numerador_nao_tem_cap_constante`,
> `test_render_pina_o_numero_impresso_em_corpus_misto`), não o comprimento das
> listas — a lista de evidência pode encolher em silêncio enquanto o headline a
> contradiz. **Prove pelo numerador, não pela lista renderizada.** Detalhe em
> [[A40.l1]] §Fechamento, residuais 3 e 4.

**Residual que esta lane herda:** o predicado de carrier 1 aceita QUALQUER
divergência de `tipo_conta` (mais largo que o par variante). Par de tipos de
conta genuinamente distintos sai `carrier-shaped` e fica in-whitelistável no
**detector**. O PR1 fecha isso **do lado do colapsador** — a allow-list
(`extrato` ≡ `extratoconta`, com deny-list de sufixo de moeda) impede que o par
conta↔poupança colapse. O detector segue sobre-detectando rotulado, que é a
direção correta para instrumento ([[ADR-342]]); só o mutador precisa da
allow-list. Assimetria que **continua aberta**: variante de vocabulário em
`banco` com as duas pernas cheias não é carrier-shaped hoje, e o colapsador a
bloqueia por `banco_conflitante` — logo um alias de `banco` exigiria tratamento
próprio nos dois lados.

## Problema

O mesmo lançamento entra **duas vezes** no razão E4, vindo de dois documentos do
mesmo banco. As pernas diferem em `banco` (caixa), `tipo_conta` e `titular`, e o
`transaction_hash` diverge — então o dedup K4 não colapsa.

**O carrier NÃO é a caixa de `banco`.** `normalize_banco` (`_tx_identity.py:75`)
faz `_WHITESPACE_RE.sub("", _strip_accents(value).lower())` e é chamada dentro de
`_hash_v1` **e** `_hash_v2` (`:233`). `c6bank` e `C6Bank` produzem o mesmo
componente de hash. A caixa fura a **chave de grupo**, não o hash.

Os carriers reais, ambos sobrevivendo à normalização como strings distintas:

1. **`tipo_conta`** — `extrato` vs `extratoconta`. `normalize_tipo_conta` (`:84`)
   só faz casing/whitespace, **não vocabulário**.
2. **`titular`** vazio numa das pernas. Efeito de segunda ordem:
   `_has_discriminants` (`:169-171`) devolve `False`, então `natural_key` sai
   `None` — mas o `transaction_hash` **continua sendo computado** com titular
   vazio. A perna fica sem chave de re-ancoragem e com hash próprio.

## O que a medição de 2026-08-04 eliminou

Os 4 desenhos abaixo estavam no §Escopo desta lane e **morreram por medição**
([[LEDGER-CERTIFY-active]] §r4). Ficam registrados para que ninguém os
ressuscite achando que são escopo pendente:

| Desenho morto | Por que morreu |
| --- | --- |
| alias-map de `tipo_conta` como **canonicalização a montante** da chave de grupo | A chave que faz as duas pernas se encontrarem é **provenance-free** e não contém `tipo_conta`. Canonicalizar a montante não é pré-requisito de nada |
| **fail-closed** em vocabulário desconhecido | Cobertura de contraparte é **50,88%** ⇒ quarentenar apagaria ~252 rows de fonte única ou órfãs. Fail-closed aqui é destrutivo |
| **fail-closed** em `account_type_equivalences` (`account_grouper.py:181`) | Mesma medição |
| **fundir os grupos-fonte** | Colapsa só ~48% (teto 126/261, LC03) **e** é destrutivo: a perna LLM não tem saldo e o merge elege `closing_balance=stmts[-1].closing_balance` **posicional** (`e3_reconciler_adapter.py`) ⇒ apagaria o saldo da conta inteira (LC13) |

**Sobreviveu:** colapso **por transação**, pré-agrupamento — e o alias-map do dono
renasce como **allow-list do predicado de colapso**, não como canonicalização.

## Escopo — 3 PRs, nenhum toca `_hash_v2`

`_hash_v1` está **congelado** ([[ADR-278]] D1) e `_hash_v2` é a chave de dedup
**e** de re-ancoragem de `transaction_overrides`. O colapsador **seleciona rows**;
não toca input de hash — a §Não-decisão da [[ADR-354]] (nenhum `_hash_v3`) segue
integralmente válida.

- **PR0 (docs-only, feito)** — **§Emenda de [[ADR-354]]** em 2026-08-05 (`6ae208b6`):
  revoga as duas primeiras §Consequências e registra o predicado de 4 cláusulas.
- **PR1 — colapsador measure-only** ✅ (`5bbead91`). Domain service puro
  `CrossDocumentCollapser`, injetado com `default None` no `E3ReconcilerAdapter`
  **após** `reconcile_with_report` e **antes** do agrupamento. Chave = a do detector
  da [[A40.l1]]. Não remove row; emite candidato com os `_hash_v2` que **removeria**.
- **PR2 — re-ancoragem (backend), pré-condição do enforce.** Consome os hashes do
  PR1, cruza com `transaction_overrides` ativos e produz o mapa
  removido→sobrevivente. Respeita o boundary (`pipeline/**` sem `sqlalchemy`): o
  pipeline **emite**, o backend **decide**. Enforce só liga se a interseção for
  vazia **ou** o mapa cobrir 100%.
  **Não construa do zero** — `backend/app/services/internal_ops/backfill_override_identity.py`
  ([[ADR-282]]) já tem a máquina: `ReanchorPlan`, `CollisionPlan` (N overrides
  colapsam numa chave ⇒ vencedor reancora, perdedores soft-delete),
  `BackfillReport`, revalidação TOCTOU entre plan e apply, e o filtro
  `orphaned_at IS NULL` que mantém override quarentenado inerte. O delta desta
  lane é a **fonte** dos candidatos (hashes do colapsador em vez de
  `natural_key_hash IS NULL`).
- **PR3 — enforce.** Colapsa de fato, com os 4 eixos de aceite abaixo.

**`titular` vazio deixa de ser PR próprio:** é a cláusula de unificabilidade do
predicado (perna vazia unifica, perna conflitante não colapsa) e já está no PR1
com teste. O débito de âncora estável de override que a [[A42]] §Fora do sprint
roteia para "l2 PR3" é atendido pelo **PR2** desta numeração.

## Critério de aceite

**Anti-Goodhart primeiro:** a chave do colapsador **contém** a do detector, logo
"o numerador cai a 0" é quase tautológico — o colapso zera o instrumento por
construção. Por isso o aceite exige eixos que **não derivam da mesma chave**, e
declara que o colapso correto pode ser **menor** que 261 (sinal, não regressão).

- **Banda, não ponto fixo:** colapso ∈ `[259,261]` — o instrumento é estimador com
  piso irrefutável 126 (descrição bruta).
- **Conservação de cardinalidade (multiset)** por (conta, mês): sobrevivente =
  `max` sobre proveniências. Métrica derivada da chave não falsifica isto.
- **Invariante de saldo:** nenhum grupo perde `closing_balance`, a contagem de
  `saldo_final_unknown` não muda, e os 105 grupos seguem fechando em tol-0.
- **Oráculo a jusante:** queda de ~19% da receita e ~8% da despesa nos meses
  afetados, **e** desaparecimento da incoerência "folga confortável + reserva
  insuficiente" que o [[LEDGER-CERTIFY-active]] §r4 nomeia como sintoma visível.
- `COUNT(*) WHERE orphaned_at IS NOT NULL` em `transaction_overrides` **não sobe**
  entre antes e depois do backfill. Se subir → **abortar e restaurar**.
- Vetores-golden de hash em `tests/unit/pipeline/test_tx_identity_propagation.py`
  seguem verdes — o colapsador não altera nenhum hash.
- Declarar o **sinal esperado do delta** (§Decisões nº 5 do sprint) e conferir com
  `dev/golden_diff.py`.
- **Prova por mutação** em cada cláusula do predicado (8 mutações no PR1).

## Guarda anti-regressão

Duas, e nenhuma é o vetor-golden de hash (que segue válido mas agora é trivial —
o colapsador não toca hash):

1. **Equivalência com o carrier da [[A40.l1]]:** todo candidato colapsável tem de
   ser `carrier-shaped` pela definição **única** de `carrier_signatures`, com as
   tags derivadas do próprio candidato. Impede que uma cláusula relaxada faça o
   colapsador apagar a coincidência cross-conta que a l1 declara como
   sobre-detecção aceitável.
2. **Cardinalidade multiset:** impede que a chave day-exact transforme *2 eventos
   vistos 1× cada* em *1 evento*.

## Achado adjacente medido no PR1 (não é escopo desta lane)

`_reconciled_copy` (`reconciliation_service.py`) reconstrói `BankStatement`
campo-a-campo e **perde `account_number_raw`/`_norm`** — o "discriminador real
entre 2 membros no mesmo banco" da [[ADR-226]] PR2 nunca chega ao payload E3 nem
ao `account_number` por transação. Medido em 2026-08-05: presente após o load,
`None` após o reconcile. Está gateado por `xfail(strict=True)` em
`tests/unit/pipeline/test_cross_document_collapser.py::test_reconcile_preserva_todo_campo_de_identidade`;
corrigir muda output do E3 (golden), logo é **PR próprio com delta declarado**, e
o XPASS estrito força a remoção do marker. Candidato natural a dono: [[A42.l5]]
(já reescreve o keying de grupo do E3).
