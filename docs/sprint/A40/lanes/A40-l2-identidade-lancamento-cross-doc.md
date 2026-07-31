---
id: A40.l2
type: lane
title: "Identidade de lançamento cross-documento: tipo_conta com vocabulário divergente + titular vazio"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l2-identidade-lancamento-cross-doc
adrs: ["[[ADR-354]]"]
depends_on: ["[[A40.l1]]"]
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
---

# A40.l2 — `identidade-lancamento-cross-doc` (RV3-01 · Crítico)

> ⚠️ **Leia a §Problema antes de codar.** O mecanismo publicado originalmente no
> [[REPORT-REVIEWS-active]] estava **errado** e foi corrigido pelo painel. A
> versão errada leva a um fix que é **no-op** e fecha verde.

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
numerador contra 261. A l1 deixou 8 ratchets provados por mutação, então filtro
ou cap silencioso no numerador quebra teste em CI (grupo `dev_tools` no
`ci.yml`).

**Residual que esta lane herda:** o predicado de carrier 1 aceita QUALQUER
divergência de `tipo_conta` (mais largo que o par variante). Par de tipos de
conta genuinamente distintos sai `carrier-shaped` e fica in-whitelistável até o
**alias-map versionado** que a [[ADR-354]] §Consequências atribui a esta lane.
Assimetria a fechar: variante de vocabulário em `banco` com as duas pernas
cheias **não** é carrier-shaped hoje — se o alias-map cobrir `banco`, a partição
precisa do mesmo tratamento.

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

## Escopo — 5 PRs, nenhum toca `_hash_v2`

Princípio: **medir → conter → corrigir a montante → re-ancorar → quarentenar**.

`_hash_v1` está **congelado** ([[ADR-278]] D1) e `_hash_v2` é a chave de dedup
**e** de re-ancoragem de `transaction_overrides`. Mudar os inputs de v2 órfãna a
categorização manual do dono — regressão user-facing **pior** que a duplicação
que estamos consertando, e já vivida neste repo.

- **PR0 (docs-only, serializado)** — [[ADR-354]] `Proposto`: *"Identidade de
  transação (K4) exclui atributos de proveniência do documento"*. Invariante: só
  campos que descrevem o **evento bancário** entram no hash; campos que descrevem
  **qual documento entregou** são canonicalizados a montante ou excluídos.
  Não-decisão explícita: **nenhum `_hash_v3`** nesta ADR.
- **PR1** — depende da [[A40.l1]] (detector + blast radius).
- **PR2 — canonicalização a montante.** `tipo_conta` ganha alias-map **declarado e
  versionado no DB**, no padrão `institution_catalog` ([[ADR-137]]) — não
  normalização free-form dentro do hash. `account_grouper.py:181`
  (`account_type_equivalences`, hoje passthrough) vira **fail-closed**: vocabulário
  desconhecido emite sinal, não cria grupo silencioso.
- **PR3 — `titular` vazio vira sinal.** É defeito de extração a reparar em E2/E3;
  row que bate no gate `_has_discriminants` passa a ser **contado e surfaçado**,
  não passe silencioso.
- **PR4 — re-ancoragem + quarentena.** Duplicata que sobrevive à canonicalização é
  **quarentenada** (`needs_review`), nunca somada em silêncio.

## Critério de aceite

- Detector da [[A40.l1]] reporta **0 duplicação não-explicada** no corpus após os PRs.
- `COUNT(*) WHERE orphaned_at IS NOT NULL` em `transaction_overrides` **não sobe**
  entre antes e depois do backfill. Se subir, o re-run rodou sem re-âncora →
  **abortar e restaurar**.
- Vetores-golden de hash em `tests/unit/pipeline/test_tx_identity_propagation.py`:
  N tuplas `HashInputs` fixas → N hashes literais, cobrindo v1 e v2. Qualquer
  edição em `normalize_*` que mude um hash **quebra o teste**.
- Teste de propagação: transação com `transaction_hash` pré-estampado em E2 sobre
  identidade não resolvida tem o hash **substituído** após resolução em E3 — senão
  o fix inteiro é inerte.
- Declarar o **sinal esperado do delta** (§Decisões nº 5 do sprint) e conferir com
  `dev/golden_diff.py`.

## Guarda anti-regressão

A guarda central é o **vetor-golden de hash**: impede que alguém "resolva" um caso
futuro canonicalizando dentro de `_hash_v2` e órfãne overrides em silêncio — o
modo de falha que esta sequência de 5 PRs existe para evitar.
