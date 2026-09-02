---
id: A40.l102
type: lane
title: "Superfície do gasto pontual: dedup do par publicado sob promessa de unicidade + o que cada superfície declara excluir"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l102-superficie-do-pontual-e-dedup
owner: data-engineer
depends_on:
  - "[[A40.l98]]"
partial_delivery: true
adrs:
  - "[[ADR-422]]"
  - "[[ADR-425]]"
  - "[[ADR-347]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/pipeline
  - area/frontend
---

# A40.l102 — `superficie-do-pontual-e-dedup`

> **Origem:** split da [[A40.l98]] no co-design de 2026-08-30 (`financial-planner` +
> `data-engineer` + `senior-cto`). O corte é pelo eixo **muta E5 × não muta**: a l98
> pertence à janela de mutação que precede o próximo re-run e disputa a cláusula de
> reinício do contador de saída; esta não, e pode ir em paralelo.

## Escopo

1. **`LC6-07` — dedup do par publicado.** Ver §Formulação corrigida abaixo.
2. **Declaração impressa do que cada superfície exclui** — ver §Item 2 re-enunciado.
3. **Os dois cards de S2 herdados da [[A40.l15]]** (texto de conclusão do donut e do
   chart mês a mês).

> ⚠️ **Obrigação que não pode se perder:** a [[A40.l15]] é dona do `CARDS_DA_L15`, que
> exclui nominalmente dois cards de `janelaCanonica.contract.test.tsx` e de
> `janela-canonica.@critical.spec.ts`. **Remover as duas exclusões é critério de aceite
> desta lane.** O assert de "exclusão não é vácuo" fica **verde depois** de removida —
> ninguém será avisado automaticamente se isso for esquecido, e a guarda fica cega para
> sempre.

## `LC6-07` — formulação corrigida (2026-08-30)

O registro do `LEDGER` diz *"dois pares duplicados (mesma data, mesma categoria, mesmo
valor)"*. **As duas metades estão erradas**, medido nos itens do report `c011c40c`:

- **Não é mesma data.** O par difere em 1 dia: `2025-10-26` em `C6Bank (extratoconta)`
  e `2025-10-27` em `c6bank (extrato)` — mesmo banco, **documentos-fonte distintos**,
  mesmo valor (R$ 3.000), mesmo beneficiário. Assinatura de D+1 entre dois documentos.
- **Não são dois pares.** Chaveando por `(data, categoria, valor)` dá **0** grupos; por
  `(mês, categoria, valor)` dá **1**; por `(mês, valor)` dá 2, mas o segundo é falso —
  beneficiários distintos. E o grupo verdadeiro traz um **terceiro** item legítimo
  (`PDV*BARA CLINICA`, outro documento, outra natureza): chave por mês+valor colapsaria
  os três.

### A medição inicial foi sobre CÓDIGO MORTO — registrado para não se repetir

A primeira análise mediu `transaction_signature`/`deduplicate_transactions`
(`scripts/reconcile_transactions.py:464-537`) e concluiu que *"a descrição já colapsa,
só a data separa"*. **Essa função não roda.** Seu único chamador é `reconcile_account`
(:877), que **não tem chamador nenhum** no repo; o caminho vivo é `main_with_store` →
`_e3_build_adapter` → `E3ReconcilerAdapter.reconcile_via_store`. `tests/test_e3_dedup.py`
a chama direto — é o teste que a mantém verde e a fez parecer viva.

**Consequência:** consertar a assinatura ali deixaria o teste verde, o dogfood parado e o
defeito publicado — um conserto que mede a si mesmo.

### No caminho vivo, o par falha em CINCO cláusulas, em dois mecanismos

| mecanismo | cláusula | por que o par não passa |
| --- | --- | --- |
| `ReconciliationService.is_duplicate` | `a.description != b.description` | descrição difere byte a byte (o sufixo está lá) |
| idem | escopo do grupo | dedup cross-file roda dentro de `{banco}_{tipo_conta}_{MOEDA}_...` ⇒ `extrato` e `extratoconta` são grupos **diferentes** |
| `CrossDocumentCollapser._collapse_key` | `tx.date.isoformat()` | **day-exact** — D+1 nunca vira candidato |
| `_extraction_reason` | `par_nao_e_nativo_mais_llm` | exige 1 nativa + 1 LLM; dois nativos é **bloqueado** |
| `cross_document_collapse_enforce_enabled` | default `False` | measure-only: nada é removido |

A tolerância de ±3 dias **já existe** — em `is_duplicate`, que em compensação exige
descrição idêntica. A normalização que resolve a descrição (`_ROUTING_SUFFIX_RE` já tira
`TRANSF ENVIADA PIX`) vive só no colapsador, que é day-exact. **As cegueiras são
exatamente complementares e o par cai no vão.**

### Decisão: measure-first, sem enforce

**D±1 é aceitável como classe de candidato, inaceitável como critério de remoção — hoje.**

- **Direção do erro.** Sub-dedup publica duplicata **visível e auditável**, conservação
  intacta. Super-dedup **destrói** row, órfã override ancorado no `transaction_hash` dela,
  e é **silencioso**. Sob [[ADR-347]] + `ReportPublication` pinado com `RESTRICT`, um erro
  é recuperável e o outro não.
- **Não há discriminante positivo.** `saldo_apos` é emitido por **0 dos 13** parsers;
  `nr_doc` por 1 (Caixa); `Transaction.from_dict` **descarta os dois**; não há hora. D±1
  hoje decide por prior, não por evidência — e taxa de falso-positivo não-verificável não
  é taxa aceitável.
- **Escala:** 1 par em 89 itens (0,76% da janela) contra 63,2% de base não classificada.
  Duas ordens de grandeza menor, e é o único item do lote que **destrói dado**.

**PR-0 é produzir o número:** hoje a classe D±1 **não é sequer contável** — o par nunca
vira candidato, logo nunca ganha `blocked_reason`. Segunda passada no **colapsador** (não
na assinatura), classe própria `proximidade_d1`, measure-only, artefatos byte-idênticos
antes/depois (molde: `dev/probe_collapse_rollback.py`).

**Quando D±1 vira seguro:** quando houver teste **positivo** por candidato. O árbitro já
existe e não é heurística — a **cadeia de saldo** (`continuity_chain.py`,
`ledger_saldo_oracle.py`): duplicata genuína quebra a cadeia em exatamente o valor
duplicado; duas transações genuínas não quebram. Critério: *remove-se o candidato se e
somente se a remoção **repara** a cadeia*. Habilitador: fazer o parser C6 **emitir** o
saldo diário que ele já lê (`day_last_saldo`) e hoje descarta.

⚠️ **`_extraction_reason` é bloqueio maior que a data**, e mexer nele é território da
[[ADR-354]] §D5. **Não fazer dentro desta lane** sem emenda datada.

### A promessa de unicidade não está sendo quebrada — verificado

`_le_consolidacao` só emite `consolidacao_cross_documento` quando `count > 0`, e com
enforce desligado a chave é omitida ⇒ a nota *"contamos cada um uma vez só"* **não
aparece**. Não há P0 de copy. O que existe é uma promessa que a peça **não faz** sobre
uma classe que ela **não conta** — e o objeto `base_pontuais` da [[A40.l98]] fecha isso
sem tocar no E3: o par continua na lista, e a lista passa a declarar o critério.

## Item 2 re-enunciado (2026-08-30, co-design de 3 especialistas)

O enunciado original dizia: *"o output da política única que a [[A40.l98]] entrega. Sem
produtor único, três declarações são três oportunidades de mentir; com ele, a declaração
é derivada."* **Medido, ele é falso em duas frentes** — não são três declarações a
escrever, e derivar todas de um objeto seria o defeito, não o conserto.

### O inventário fechado: 4 superfícies, 2 gaps

| superfície | consumidor | declara? |
| --- | --- | --- |
| Card Consumo Consciente — **KPI** | humano | ✅ `BaseDeclaracao` (#1865) |
| Card Consumo Consciente — **tabela** | humano | ❌ **gap 1** — outra população, não declarada |
| Referência mensal de consumo (`despesa_consumo`, [[ADR-333]]) | humano | ✅ `TransferNote` — **pré-existente, nunca foi dívida** |
| Exec context — `despesa_total`/`fluxo_liquido` | LLM | ✅ `LC6-06` (#1865) |
| Exec context — `total_pontuais*`, `analise` | LLM | ❌ **gap 2** — `base_pontuais` não projetado |

### Gap 1 — o card declara sobre o KPI e a tabela ao lado tem outra população

Medido na fixture do próprio #1865 (E3→E4→E5, os dois filtros sobre o mesmo artefato):

```
base_pontuais (a DECLARAÇÃO):  bruto {127000,18} · publicado {39000,2}
  excluidos: nao_identificado {7000,1} · recorrente {65000,13} · transferencia_por_categoria {16000,2}
LISTA (_is_pontual):           3 itens, soma 46000 — INCLUI o item nao_identificado {7000}
```

A declaração imprime *"fora da base: não classificados R$ 7.000 (1)"* e a tabela logo
abaixo **renderiza exatamente aquela linha**. A divergência é deliberada
(`_VEREDITOS_DO_INVENTARIO` + [[ADR-425]] §D1), está em três comentários de código, e
**não é impressa em lugar nenhum do card** — o `TabelaHeader` declara só escopo temporal.
O delta é por **natureza**, não por período: com o toggle em 3m ele continua lá.

Isso é pior que superfície não-declarada: é declaração que **contradiz a evidência
adjacente**, e cai na [[ADR-306]] D1/D6 que o docstring do próprio card cita.

### A regra que substitui "declaração derivada"

**Fonte única de vocabulário ≠ fonte única de fato.** `GastoPontualPolicy` é serviço de
domínio e segue fonte única do enum e das cláusulas; `BasePontuais` é **value object
computado sobre uma população**. Imprimir o de A sobre B é *o número errado com pedigree*
— pior que não declarar. A forma certa é **uma declaração por superfície, computada pela
superfície sobre a própria população, no mesmo tipo**.

A lista já tem tudo: `_is_pontual` chama `policy.classify` por item e **joga o veredito
fora** (`return veredito in _VEREDITOS_DO_INVENTARIO`). Agregar em `BaldePontual` em vez
de descartar são ~10 linhas, e não muta E5 — respeita o eixo do split desta lane.

### Divisão de dono

- **Gap 2 (exec context) → [[A40.l98]]/#1865**, por custo: `parecer_planejador.yaml`,
  `dev/snapshots/parecer_ancorabilidade.json` e o golden do parecer **já estão sujos**
  naquele PR. Entrar depois custa segundo rebaseline, segundo bump de frota e uma segunda
  emenda datada à [[ADR-425]] na mesma data da primeira. Roteado em
  [comentário no #1865](https://github.com/davidrobert/mathoms/pull/1865#issuecomment-5472036617).
- **Gap 1 (tabela do card) → esta lane**, quando o #1865 mergear.

## Critério de aceite

- `CARDS_DA_L15` removido das **duas** guardas, com o assert de não-vácuo verificado
  antes e depois.
- Classe `proximidade_d1` contável, com `blocked_reason` por candidato; **zero** rows
  removidas; artefatos byte-idênticos antes/depois.
- Se algum dia houver enforce: prova nos **dois substratos** — o par some da lista
  (`backend/tests`) **e** de `total_pontuais`/`total_pontuais_janela` (`tests`), com a
  mesma constante de delta compartilhada entre os dois arquivos.

---

## Entrega parcial (2026-08-30)

Dois dos três itens entregues. O item 2 fica de fora **por dependência**, não por
escopo: ele precisa do objeto `base_pontuais`, que a [[A40.l98]] entrega no PR3a.

> **Correção 2026-08-30, mesmo dia.** Este parágrafo dizia *"a l98 está `open` sem PR"*.
> Falso desde o **#1865**, aberto horas depois, que entrega `GastoPontualPolicy` +
> `base_pontuais` + um leitor. A dependência continua real — o #1865 não mergeou —, mas o
> motivo mudou de "não existe" para "está em revisão", e o §Item 2 re-enunciado acima
> substitui a justificativa inteira: não são três declarações a escrever, são **2 gaps**,
> e um deles voltou para a l98. `depends_on: [[A40.l98]]` + `partial_delivery` seguem
> corretos.

| item | estado |
| --- | --- |
| 1. `LC6-07` — classe D±1 contável, measure-only | ✅ entregue |
| 2. Declaração impressa do que cada superfície exclui | ⏸ atrás do `base_pontuais` da [[A40.l98]] |
| 3. Os dois cards de S2 (`CARDS_DA_L15`) | ✅ entregue |

### Duas afirmações do enunciado caíram

**O código morto já não existe.** O §"A medição inicial foi sobre CÓDIGO MORTO"
descreve `transaction_signature`/`deduplicate_transactions` como vivas-porém-inertes,
com `tests/test_e3_dedup.py` mantendo-as verdes. As três funções — e aquele arquivo
de teste — **foram deletadas** em `35860eb5` (*"deleta 3 gêmeas mortas de service
extraído"*). `git grep` sobre `scripts/ pipeline/ tests/` no HEAD não acha nenhuma.
O aviso continua valendo como registro de método; não como armadilha viva.

**Eram QUATRO textos ofensores, não um.** Removido o `CARDS_DA_L15`, a varredura
reprova no primeiro e esconde os demais — o modo de falha do fail-fast. Enumerando
em vez de assertar um a um:

| card | texto | defeito |
| --- | --- | --- |
| Despesas por Categoria | `Distribuição das despesas totais (R$ 828.000) entre 3 categorias…` | sem cláusula de base |
| Despesas por Categoria | `Moradia concentra 43% do gasto recorrente.` | sem base **e** 7 pontos abaixo do próprio desenho (50,0%) |
| Receita vs Despesa | `Série temporal mensal (36 meses) de receitas…` | sem cláusula de base ("36 meses" é o desenho) |
| Receita vs Despesa | `Receita média de R$ 42.667/mês … Taxa de poupança de 15.6%.` | sem base + mensalização do bloco `full` + **taxa de poupança própria** |

O 2º e o 4º não eram "escolher a base": eram **contradição interna**. A conclusão do
donut vinha de `despesas_por_categoria` (bloco `full`, COM aporte) enquanto a rosca
desenha ex-aporte da janela renderizada — o comentário em `conclusionUtils.ts` já
media a divergência (50,0% × 43%) e a parqueava aqui. Nenhuma base de payload
acompanha o `PeriodToggle`, então o texto desceu para o componente e passou a derivar
das fatias que ele desenha; a cláusula sai de `clausulaDeBase`, que lê `fonte` e
`aporteExcluido` do **mesmo** `DespesaSlices` que somou os valores — par que a lane
anterior deixou ali para esta, e que até agora nenhum texto lia.

### Para a [[A40.l98]]: havia produtor de taxa de poupança no frontend

O §r7 da l98 registra, sobre o `LC6-06`, que *"o produtor vivo da terceira taxa não
foi localizado no schema nem no frontend"*. `ReceitaDespesaMensalChart.buildConclusion`
publicava `Taxa de poupança de 15,6%` — média da série inteira, **sem rótulo**, dentro
da mesma S2 cuja taxa canônica vive no hero de S1. Foi removida aqui.

**Não afirmo que seja a mesma taxa do `LC6-06`**: a base desta era a média da série
renderizada, não `despesa_total` na janela cheia com aporte e amortização. O que muda
para a l98 é o pressuposto da busca — havia, sim, um produtor de taxa divergente no
frontend, e ele escapou da varredura que concluiu ausência.

> **Reconciliado 2026-08-30 pela própria [[A40.l98]]** (#1865): *"O produtor que este PR
> nomeia é **outro** — a derivabilidade de `fluxo_liquido / receita_total` no exec context
> do parecer —, e os dois estão fechados."* A ressalva acima estava certa: não era a mesma
> taxa. Nada a fazer aqui.

### O que a entrega NÃO prova

O gate de pixel de S2 (`sections.snapshots.visual.spec.ts`, `maxDiffPixelRatio 0.025`
sobre a seção inteira) **não vê mudança de texto** — precedente medido na A40.l7, em
que um `<h2>` inteiro trocou e a baseline passou. A verificação renderizada destes
quatro textos é a perna de conteúdo (`janela-canonica.@critical.spec.ts`, 27/27 em
chromium+firefox+webkit), não a de imagem. As baselines `S2-{light,dark}` e a do PDF
são Linux/CI-parity e **não foram regeradas** — regerar em macOS produz baseline
inútil, e o diff local do PDF é da 1ª página (capa + hero), que estes textos nem
tocam.

## Evidência de produção recebida da [[A42.l25]] (2026-09-01)

O corpus `ws-1b9f2cf5` tem **48 receitas negativas** somando **R$ 9.993,86** — `PAGAMENTO EFETUADO`/estorno classificados como receita, que é exatamente o defeito que a [[ADR-429]] descreve e hoje só sustenta com fixture. Medido no fecho da [[A42.l25]] (#1965) ao decompor o eixo-valor E3→E4: as 48 explicam **100%** do Δ daquela perna (`2 × 999.386 = 1.998.772` cents, exato).

Não é entrega desta lane — é o **denominador** que faltava para o gate `receita_total ≥ 0 ∧ ∀ por_fonte[*] ≥ 0` deixar de ser proposto sobre fixture.
