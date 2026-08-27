---
id: A40.l39
type: lane
title: "Posição por instituição: o header '31/12' mente para 10 de 16 linhas — separar visão corrente da fiscal"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l39-posicao-visoes-corrente-fiscal
adrs:
  - "[[ADR-238]]"
  - "[[ADR-245]]"
  - "[[ADR-376]]"
  - "[[ADR-382]]"
depends_on: ["[[A40.l38]]"]
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l39 — `posicao-visoes-corrente-fiscal`

> **Aberta em 2026-08-11.** Parecer `financial-planner`: um balanço tem uma
> data; o 31/12 é marco, não linha da fotografia corrente. Co-design
> `senior-cto` + `data-engineer` (2026-08-11).

## Problema

O card `posicao_informe_31_12` (S1) mistura 6 linhas de informe 31/12/2025 com
10 linhas de extrato com saldo **atual** (até 2026-08-11) sob o header "Valor
em 31/12" ([PosicaoInformeCard.tsx:86](../../../../frontend/src/components/report/cards/PosicaoInformeCard.tsx)).
A mesma conta aparece 2× sem vínculo (Itaú CC informe R$ 0,00 + extrato
R$ 5.156,06; Wise BRL idem). A regra "informe vence extrato D+1"
([[ADR-238]] D5) é letra morta: a janela roda sobre o **último** extrato da
conta e nunca dispara em workspace com extratos correntes.

## Entregável

Dois PRs + ADR:

- **PR-a (mecânico, sem mudança de número):** propaga `data_referencia`
  (`YYYY-MM-DD`, fim de período) + `data_referencia_precisao` + `id` estável
  (`{codigo}:{moeda}:{fonte}:{ano_base}`) até as linhas de
  `posicao_31_12`/`caixa_detalhes`. Sem bloco novo no payload — **renomear e
  migrar** o produtor existente, nunca criar segundo produtor (veto
  `data-engineer`).
- **ADR (Proposto antes do PR-b):** visões corrente×fiscal; emenda datada na
  [[ADR-238]] (D5 parcial — `_period_in_janela_d1` deixa de existir como
  regra de negócio); destino explícito da [[ADR-245]] (fallback ME
  permanece, com data e proveniência por linha).
- **PR-b (split visual):** S1 vira "Posição por Instituição e Moeda" só com
  posição corrente + coluna de data + sinal de defasagem; bloco
  "Fechamento de 31/12/AAAA" (informe + IRPF, zero extrato) na seção
  **Renda Anual e Impostos**, levando o alerta CBE. Spec de UI:
  `product-designer` (pendente — bloqueado por limite de spend em
  2026-08-11; obrigatório antes do PR-b).


## Aberto — 2026-08-27 · dono: David Robert

Estado medido no fecho das lanes de contraste/papel (skill `lane-closeout`).
A lane **volta a `open`**: `in_progress` significa "branch/PR aberta"
(§Predicado do `_README`) e não há branch remota — `git for-each-ref
refs/remotes/origin/agent/ | grep a40-l39` é vazio; as duas locais são
fantasma. `depends_on: [[A40.l38]]` está `shipped`, então `open` é o valor
correto.

### O PR-b não começou — e três itens de outras lanes já foram roteados p/ cá

Nenhum estava registrado neste arquivo até hoje. **Os três chegam de lanes que
não podem mais executá-los.**

| item | origem | estado da origem |
| --- | --- | --- |
| **P0 · rodapé de PTAX** — o rodapé afirma conversão pela PTAX de 31/12 em linhas cujo saldo é de 26/03, 22/07 e 11/08/2026 | [[A40.l50]] §P0, roteado em **2026-08-14** | `open`, mas declarou explicitamente *"não é lane desta … abrir PR aqui conflita no arquivo que ela está partindo"* |
| **Se e como o snapshot 31/12 do IRPF deve aparecer no card de posições** — hoje não aparece, o que é honesto mas talvez não seja o que a família quer ver | [[A40.l63]] §Roteamento | **`shipped`** — terminal, não executa mais nada |
| **Qual taxa a coluna "31/12" usa** | [[A40.l63]] §Fora de escopo | **`shipped`** |

**Correção de enquadramento que a l39 herda junto com o P0** (co-design
`financial-planner` + `senior-cto` na l50, 2026-08-14): a linha de extrato tem
**dois** erros, não um — taxa errada *e* **data errada**. Por isso *"converter
tudo pela PTAX de 31/12"* está **vetado**: aplicar PTAX de 31/12/2025 a saldo de
agosto/2026 não aplica regra fiscal nenhuma, fabrica um número que não
corresponde a posição alguma, com aparência de autoridade fiscal. O split desta
lane é o que resolve — não a footnote.

### O que o PR-a deixou inerte (medido em 2026-08-27)

O #1399 propagou 3 campos e **nenhum consumidor os lê**. Não é defeito do PR-a
(era plumbing declarado); é o tamanho real do que falta.

| campo | estado |
| --- | --- |
| `id` estável | `PosicaoInformeCard.tsx:92` continua com `key={`${row.instituicao}-${row.moeda}-${idx}`}`; `row.id` tem **0** ocorrências no frontend |
| `data_referencia` / `_precisao` | 4 ocorrências no `frontend/src`, **todas declaração de tipo** (`types/posicao-31-12.ts:8-9`, `generated/report-analysis.ts:25-26`). Zero uso |
| contrato | `posicao_31_12` **não existe** em `config/schemas/e5_analysis.schema.json` (0 ocorrências). Os campos novos não têm schema |

**O `id` também não serve de natural key no diff, que era a 2ª justificativa
para criá-lo.** `dev/golden_diff.py::_NATURAL_KEYS` é tupla **ordenada** com
`"fonte"` antes de `"id"`, e `_natural_key` retorna no 1º match — toda row de
`posicao_31_12` tem `fonte`, então o diff cai em posicional. E `golden_diff` não
é invocado por `.github/workflows/` nem pelo `.pre-commit-config.yaml`.

### O bloqueador do critério de aceite: a superfície não tem golden

`backend/tests/snapshots/dogfood_view_model.json` traz `posicao_31_12` com
**0 itens**. Há teste de componente com rows sintéticas
(`frontend/tests/components/PosicaoInformeCard.test.tsx`), mas o caminho de
snapshot/golden — o que provaria o critério *"PR-a: goldens/snapshot idênticos
exceto campos aditivos"* e protegeria o split — **nunca exercitou o card**.
Construir o PR-b sem esse substrato é desenhar a fotografia corrente contra
dados inventados, que é exatamente a classe que a sprint existe para matar.

**Ordem que isto impõe ao PR-b:** substrato de golden com as duas famílias de
linha (informe 31/12 e extrato corrente) **antes** do split visual, não depois.

### Bloqueador 1 do PR-b segue vivo

`IrpfRendaSection.tsx:28` continua `if (!kpis) return null` — confirmado hoje.
A decisão já está tomada (§Bloqueadores resolvidos: relaxar para
`kpis || fechamentoRows.length > 0`); falta executar.

### [[ADR-382]] segue `Proposto`

15 dias sem PR-b. A ADR não vigora; nada nela pode ser citado como decidido.

## Critério de aceite

- Header ≡ conteúdo: card que declara data fixa só renderiza linhas daquela
  data (o dogfood atual **reprova**; o novo desenho passa).
- Nenhuma tabela mistura datas sem coluna de data; nenhuma tabela de datas
  mistas exibe total.
- CBE continua ancorado no agregado 31/12 após a realocação.
- Leitor tolerante a artefato antigo (mutação por remoção das chaves novas
  sobre view-model + contexto do parecer). Alinhar com [[A40.l5]]
  (`check_view_model_contract`) antes do PR-a.
- PR-a: goldens/snapshot idênticos exceto campos aditivos (sem `value_delta`
  monetário no manifesto).

## PR-a entregue — 2026-08-12 (PR #1399)

Plumbing mecânico no lugar: linhas de `posicao_31_12` e `CaixaDetalhe`
carregam `data_referencia` (`YYYY-MM-DD`, fim de período — 31/12/ano_base nas
linhas de informe, inclusive quando o override adota o informe),
`data_referencia_precisao` e `id` estável. `Posicao3112Row` extraído para
`types/posicao-31-12.ts`. Zero mudança de número.

## PR-b — spec de UI recebida (`product-designer`, 2026-08-12)

Duas metades commitáveis: (A) `PosicaoCorrenteCard` — coluna `Em` com
`<time>`, badge de defasagem em faixas de meses fechados usando
`color-mix(...)` + par `-on-tint` **no mesmo `className`** (a forma `/15` é
invisível ao `check_tint_contrast`), nudge agregado, coluna `Fonte`
condicional, `table-fixed`, deleta o `InformeVenceuNudge`; (B)
`FechamentoFiscalCard` em `S_IRPF_RENDA` — CNPJ formatado como identificador
até a [[A40.l40]] resolver o nome, CBE **fora** do `<details>` sazonal, total
travado por parágrafo de não-aditividade, `<details>` forçado aberto no print.

**Dois bloqueadores achados pela spec, a resolver no PR-b:**

1. `IrpfRendaSection` retorna `null` sem `irpf_kpis` — workspace com informe e
   sem IRPF perderia o card fiscal **e o alerta CBE** (obrigação legal).
   Relaxar o guard para `kpis || fechamentoRows.length > 0`.
2. A footnote PTAX 31/12 **não pode** ficar no S1 pós-split: o S1 converte
   saldos correntes. Falta confirmar qual taxa o pipeline usa nas linhas
   correntes em ME antes de escrever a footnote nova.

Âncora temporal única (defasagem e sazonalidade contra a data de geração do
relatório, nunca `Date.now()`) e `md:` inativo no print (703px) são restrições
do PR-b.

## Bloqueadores do PR-b resolvidos por medição — 2026-08-12

**1. O guard do `IrpfRendaSection` é real e mataria o CBE.**
Confirmado em [IrpfRendaSection.tsx:28](../../../../frontend/src/components/report/sections/IrpfRendaSection.tsx):
`if (!kpis) return null` — a seção inteira some quando o E5 não traz
`irpf_kpis`. Informe financeiro é documento independente do IRPF (o
`posicao_31_12_builder` não depende de `irpf_kpis`), então workspace com
informe e sem declaração perderia o card fiscal **e o alerta CBE** — que é
obrigação declaratória, não enfeite.

Decisão para o PR-b: relaxar o guard para `kpis || fechamentoRows.length > 0`.
Os KPIs e charts já fazem hide-when-empty individualmente, então a seção
degrada para só o card fiscal sem código novo de fallback. Registrar como
consequência na [[ADR-382]] antes de flipar para `Decidido`.

**2. A footnote PTAX ficaria falsa no S1 — a taxa corrente é outra.**
As linhas correntes em moeda estrangeira são convertidas pela cotação de
mercado **da data do run**, não pela PTAX de 31/12:
[analyze_finances.py:2248](../../../../scripts/analyze_finances.py) chama
`ConfigStore.get_market_rate("USD/BRL", TODAY)` (e EUR/BRL), com `TODAY =
date.today()` do run; `get_market_rate` devolve a última cotação com data
`<= observed_at` ([db_config_store.py:128](../../../../backend/app/services/db_config_store.py)).
Fallback: `taxas.cambio_usd_brl` / `cambio_eur_brl`, e por último os defaults
codificados 5,80 / 6,35.

Decisão para o PR-b: a footnote PTAX 31/12 vai **inteira** para o card fiscal;
o S1 recebe footnote própria declarando a cotação de fechamento da data do
relatório. Quando a conversão cair no default codificado, isso é degradação e
pertence à superfície da [[A40.l22]] — não a uma footnote que afirma cotação
de mercado que não houve.
