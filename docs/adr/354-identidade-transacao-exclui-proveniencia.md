---
id: ADR-354
type: adr
title: "Identidade de transação (K4) exclui atributos de proveniência do documento"
status: Proposto
phase: report-review r3 (RV3-01) · A40.l2
date: "2026-07-30"
amended_at: ["2026-08-05", "2026-08-05"]
relates_to:
  - "[[ADR-278]]"
  - "[[ADR-287]]"
  - "[[ADR-137]]"
  - "[[ADR-350]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-354 — Identidade de transação (K4) exclui atributos de proveniência do documento

> ⚠️ **Emendada em 2026-08-05.** A §Decisão original segue válida; **duas das
> quatro §Consequências foram revogadas por medição** (alias-map a montante e
> fail-closed de vocabulário). O mecanismo de correção mudou de
> *canonicalizar a montante* para *colapsar por transação antes do
> agrupamento*. Leia a §Emenda antes de implementar — a forma original leva a
> um fix que colapsa ~48% ou apaga dado legítimo.
>
> ⚠️ **Segunda emenda, 2026-08-05 (mesma data, sessão posterior):** a cláusula 4
> do predicado (multiset por perna) foi **revogada por medição** — 0/262 legs com
> ≥2 rows tinham evidência de 2 eventos, e a cláusula preservava o par nativo+LLM
> em 42 chaves. A cardinalidade passa a contar eventos por **arquivo**. Ver
> §Emenda 2.

## Contexto

A revisão do relatório entregue ([[REPORT-REVIEWS-active]] §r3, RV3-01) **mediu**
duplicação material no razão E4 do workspace dogfood: o mesmo lançamento entra duas
vezes, vindo de dois documentos do mesmo banco.

As pernas diferem em três campos, e a análise inicial atribuiu a causa ao errado.
`normalize_banco` (`pipeline/domain/services/_tx_identity.py:75`) já faz
`_strip_accents(...).lower()` + colapso de whitespace **antes** do hash, e é
chamada dentro de `_hash_v1` e `_hash_v2` — a caixa de `banco` **não** fura o
`transaction_hash`; fura a chave de grupo. Os carriers reais são:

1. **`tipo_conta` com vocabulário divergente** (`extrato` vs `extratoconta`).
   `normalize_tipo_conta` (`:84`) faz casing e whitespace, **não vocabulário** —
   as duas strings sobrevivem distintas até o hash.
2. **`titular` vazio numa das pernas.** Efeito de segunda ordem:
   `_has_discriminants` (`:169-171`) devolve `False`, então `natural_key` sai
   `None` — mas o `transaction_hash` **continua sendo computado** com titular
   vazio. A perna fica sem chave de re-ancoragem e com hash próprio.

Ambos descrevem **qual documento entregou o dado**, não **o evento bancário**.

A conservação por grupo-fonte fecha em tol-zero (105/105) com a duplicação
presente, porque mede dentro de cada grupo e a duplicação é entre grupos.

## Decisão

**Só campos que descrevem o evento bancário entram na identidade K4.** Campos que
descrevem a proveniência do documento — variante de rótulo de `tipo_conta`, taxa de
preenchimento de `titular`, identificador do documento de origem — são
**canonicalizados a montante** ou **excluídos**, nunca resolvidos dentro da função
de hash.

Consequências:

- **`tipo_conta` ganha alias-map declarado e versionado no DB**, no padrão
  `institution_catalog` ([[ADR-137]]) — não normalização free-form dentro de
  `_hash_v2`. O vocabulário desconhecido é **fail-closed**: emite sinal e a conta
  cai em review, em vez de criar grupo-fonte silencioso.
- **`titular` vazio é defeito de extração** a reparar em E2/E3. Row que bate no
  gate `_has_discriminants` passa a ser **sinal contado e surfaçado**, não passe
  silencioso.
- **Duplicata que sobrevive à canonicalização é quarentenada** (`needs_review`),
  nunca somada em silêncio.
- **A conservação por grupo é declarada insuficiente** como gate de duplicação. O
  gate de duplicação é o check cross-grupo, por chave provenance-free
  `(data, valor_cents, moeda, direction, descricao_normalizada)`.

## Não-decisão explícita

**Nenhum `_hash_v3` nesta ADR.** `_hash_v1` está congelado ([[ADR-278]] D1) e
`_hash_v2` é simultaneamente a chave de dedup e a de re-ancoragem de
`transaction_overrides`. Mudar os inputs de v2 órfãna a categorização manual do
dono — regressão user-facing **pior** que a duplicação que se está corrigindo, e já
vivida neste repositório. Versão nova de chave exige ADR própria **e** plano de
backfill de override.

## Alternativas rejeitadas

- **Canonicalizar `tipo_conta` dentro de `_hash_v2`.** Rejeitada: resolve o caso e
  órfãna overrings existentes em silêncio. É o modo de falha que a sequência de 5
  PRs da [[A40.l2]] existe para evitar.
- **Dedupar por similaridade no E4.** Rejeitada: dedup fuzzy sobre razão já
  fechado esconde o defeito de identidade a montante, e não há como distinguir
  duplicata de compra legítima repetida sem a identidade de conta correta.
- **Aceitar a duplicação e corrigir só o relatório.** Rejeitada: o razão é a fonte
  de verdade de todo agregado; corrigir na saída multiplicaria o erro por consumidor.

## Consequências

Positivas: elimina a classe inteira (qualquer par de documentos do mesmo banco com
rótulo de conta variante), e o alias-map versionado dá rastreabilidade de quando o
vocabulário mudou.

Negativas: exige backfill com re-ancoragem de override, cujo gate operacional é
medir `COUNT(*) WHERE orphaned_at IS NOT NULL` antes e depois — se subir, abortar e
restaurar. O custo é real e é a razão de a lane ter 5 PRs em vez de 1.

Não supersede [[ADR-278]] nem [[ADR-287]]; complementa [[ADR-350]] (mesma família
de falha, lado fatura).

## Emenda A40.l2 — o mecanismo é colapso por transação, não canonicalização a montante · 2026-08-05

> A certificação de razão de 2026-08-04 ([[LEDGER-CERTIFY-active]] §r4, LC01-LC04)
> re-mediu o defeito e **eliminou 4 dos 5 desenhos de fix** desta ADR. O defeito
> medido não mudou (261 ocorrências, reproduzidas byte-a-byte); a causa e o
> mecanismo de correção mudaram.

**Revogado — as duas primeiras §Consequências.**

- *"`tipo_conta` ganha alias-map … canonicalizado a montante"* como mecanismo de
  correção: a chave que faz as duas pernas se encontrarem é **provenance-free**
  (não contém `tipo_conta`), logo canonicalizar `tipo_conta` a montante não é
  pré-requisito de nada. O alias-map sobrevive com **papel novo** (abaixo).
- *"O vocabulário desconhecido é fail-closed"*: a cobertura de contraparte no
  corpus é **50,88%** — quarentenar vocabulário desconhecido apagaria ~252 rows
  de fonte única ou órfãs. Fail-closed aqui é destrutivo, não conservador.

**Também rejeitado, e não estava escrito como alternativa: fundir os grupos-fonte.**
Dois motivos independentes. (1) O dedup existente exige descrição **bruta
byte-idêntica** (`reconciliation_service.py:159`), teto de colapso ~48% (126/261) —
fecharia verde pagando o preço máximo. (2) É **destrutivo**: a perna escalada ao LLM
não tem saldo, e o merge elege `closing_balance=stmts[-1].closing_balance`
**posicional** (`e3_reconciler_adapter.py:409`) — inserir a perna sem saldo apagaria
o saldo da conta inteira.

**Decisão emendada.** O mecanismo é um **colapsador cross-documento por
transação**: domain service puro, injetado com `default None` no
`E3ReconcilerAdapter`, **após** `reconcile_with_report` e **antes** do agrupamento
de artefato. Chave = a mesma do detector da [[A40.l1]]
(`data, valor_cents, moeda, direction, descricao_normalizada`). O colapsador
**seleciona rows**; não toca input de hash — a §Não-decisão (nenhum `_hash_v3`)
segue integralmente válida **quanto ao mecanismo**.

> 🔴 **Correção, 2026-08-06 ([[ADR-364]]).** A frase acima é verdadeira sobre o
> mecanismo e **falsa sobre a consequência**. A §Não-decisão proíbe `_hash_v3` **porque
> órfãna a categorização manual do dono** — e remover a row sob o hash produz o **mesmo
> resultado** que mudar o hash sob a row: o override deixa de resolver. A [[ADR-364]]
> declara que remoção de row **herda** a restrição, e a **quita por re-ancoragem** em vez
> de evitação.

**O predicado do colapsador é estritamente mais forte que a chave do detector.**
Um detector pode sobre-detectar rotulado ([[ADR-342]]); um mutador que sobre-colapsa
**deleta dado legítimo**. Quatro cláusulas conjuntas, cada uma fechando uma classe
medida:

1. **`carrier-shaped`** — nunca `coincidence-shaped`. Fecha a classe de
   sobre-detecção declarada da [[A40.l1]] §SOBRE-detecção (mesma tarifa, mesmo dia,
   contas distintas, pernas simétricas).
2. **Par de `tipo_conta` ∈ allow-list** — é aqui que o alias-map renasce, como
   allow-list do predicado e não como canonicalização. Colapsa **só**
   `extrato` ≡ `extratoconta`; **sufixo de moeda é identidade de conta**
   (C6 Global USD/EUR, Wise BRL/USD são contas distintas), com **deny-list
   explícita** validada na construção da config. Sem esta cláusula, carrier 1
   ("qualquer divergência de `tipo_conta`") colapsaria tarifa de mesmo valor em
   conta **e** poupança — o §Residual declarado da [[A40.l1]].
3. **Exatamente uma perna marcada como extraída por LLM.** O marcador
   `extraido_por` tem **um único writer** (`extract_with_llm.py:432`) e o extrator
   nativo não o emite, então ausência ⇒ nativo. Par nativo↔nativo **não colapsa**
   (é a classe latente da [[A42.l5]]); ambas-LLM não colapsa. A conflação
   "row legada sem o campo" ⇒ nativo erra para **sub-colapso**, que é a direção
   segura para um mutador.
4. **Multiset-aware** — a cardinalidade do sobrevivente é o `max` por proveniência,
   nunca 1-por-chave. Chave day-exact não distingue *1 evento visto 2×* de *2
   eventos vistos 1× cada*; sem esta cláusula, duas compras legítimas idênticas no
   mesmo dia viram uma.

Sobrevivente do par: a **perna nativa**.

**A conservação por grupo segue declarada insuficiente** (§Consequências original,
4º item) — inalterada, e é o que explica por que o defeito atravessou 105/105
grupos em tol-zero.

**Anti-Goodhart — a banda não basta.** A chave do colapsador contém a chave do
detector, então "o numerador cai a 0" é quase tautológico: o colapso zera o
instrumento por construção. O critério exige **eixos que não derivam da mesma
chave**: conservação de cardinalidade multiset por (conta, mês); invariante de
saldo (nenhum grupo perde `closing_balance`, contagem de `saldo_final_unknown`
inalterada, 105 grupos ainda fecham tol-0); e o oráculo a jusante (queda de ~19%
da receita e ~8% da despesa nos meses afetados). **Corolário:** o colapso correto
pode ser **menor** que 261 — e isso é sinal, não regressão.

**Consequência de sequenciamento.** A re-ancoragem de `transaction_overrides` deixa
de ser o último passo e passa a ser **pré-condição do enforce**: o colapsador remove
row, e override ancorado no `transaction_hash` dela órfãna — que é exatamente o
critério de aborto (`COUNT(*) WHERE orphaned_at IS NOT NULL` não sobe). O caminho
respeita o boundary de `pipeline/**` (sem `sqlalchemy`): o pipeline **emite** os
hashes que removeria, o backend **decide** o mapa removido→sobrevivente.

Co-design `data-engineer` (2026-08-05) — as cláusulas 1, 3 e 4 e o eixo de
cardinalidade são objeções dele ao desenho que eu havia proposto.

## Emenda 2 — cardinalidade conta eventos por arquivo, não por perna · 2026-08-05

> Co-design data-engineer + financial-planner sobre a medição do PR1 apontado ao
> corpus (verificação adversarial de 4 lentes, mesma data).

**Revogada a cláusula 4 da Emenda 1** (multiset: `max` de rows por proveniência).
Medido: nas 262 legs com ≥2 rows, `source_document` difere em **262/262**, a
descrição bruta é byte-idêntica em 168 (onde `is_duplicate` retorna `True` em
168/168) e nas 94 restantes a divergência é exatamente o sufixo de roteamento que
`normalize_descricao` remove ([[ADR-255]] it.2). **0/262 têm evidência de 2
eventos.** A cláusula importava a duplicação intra-proveniência para dentro do
sobrevivente (182 rows) e preservava o par nativo+LLM — o defeito-alvo — em 42
chaves. Pior: fazia a identidade do lançamento depender de **quantos arquivos** a
família subiu, com sinal perverso (quem envia extrato anual + mensais vê mais
renda), sendo que documento sobreposto é o onboarding modal.

**Regra nova:** eventos distintos = máximo de rows num mesmo
`(proveniência, source_document)`. Um arquivo reportando 2× = 2 eventos (repetição
legítima aparece 2× no MESMO extrato — protegida); dois arquivos reportando 1×
cada = 1 evento visto por documentos sobrepostos. A regra é **estritamente mais
rígida** que o `is_duplicate` que já roda a montante (±3 dias, ±R$ 0,01) — não
abre classe nova de falso-positivo; remove a dependência de fronteira de arquivo
de uma regra que o produto já aceitou.

**Dois critérios foram rejeitados no co-design:** descrição normalizada
(degenerada — constante dentro da chave por construção, equivale ao colapso
ingênuo e apagaria repetição legítima em 80 chaves) e `is_duplicate` byte-idêntico
(o critério que já falhou nas 94 legs com sufixo de roteamento; reproduziria o
teto de ~48% que a Emenda 1 sepultou).

**Invariante mantido e agora testado:** sobrevivente é a perna **nativa**
(native-first) — nas 6 chaves com `kind` assimétrico, eleger a perna LLM
converteria receita em transferência, apagando renda em silêncio.

**Rebaseline no corpus dogfood:** removível 411 → **593** (`card {1: 331}`); o
alvo é a **regra**, não o número — pinar 593 seria Goodhart.
