---
id: A40.l34
type: lane
title: "Base do limite PGBL: duas seções publicam 12% sobre bases que o relatório declara incompatíveis"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l34-base-do-limite-pgbl
adrs:
  - "[[ADR-375]]"
  - "[[ADR-196]]"
  - "[[ADR-277]]"
  - "[[ADR-236]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l34 — `base-do-limite-pgbl`

> **Aberta em 2026-08-11**, spun off da [[A40.l7]] enquanto se media o RV3-28.
> Decisão de abrir: do dono. Colocação, prioridade e onda: `product-manager`.
> Severidade de domínio: `financial-planner` — *"a única parte deste achado que
> pode custar dinheiro à família"*.

## Problema

O relatório publica **"Limite PGBL (12%)" em duas seções, sobre bases que ele
mesmo declara incompatíveis**:

| Superfície | Base do limite |
|---|---|
| **S7**, `PrevidenciaPgblCard` (`previdencia_analyzer.py:62`) | `receita_pj_anual × **32%** (lucro presumido)` |
| **S8**, `PgblBlock` (`CascataFiscalCard.pgbl.tsx:38`) | *"pró-labore + outras rendas tributáveis IRPF. **Lucros distribuídos não entram na base PGBL**"* |

A S8 **afirma explicitamente que a base da S7 está errada**, uma seção adiante,
no mesmo documento.

Para o arquétipo central do produto — **PJ alta renda, pró-labore pequeno,
distribuição grande** — a S7 **superestima o espaço dedutível por um múltiplo**
e imprime *"Economia de IR/ano"* em `--semantic-gain`. O dano não é de leitura:
a família aporta acima do teto dedutível sobre um número que o relatório
apresentou como ganho.

**A polaridade da prescrição está invertida.** `getPgblCardStrategy`
(`pgbl-card-strategy.ts:103`) devolve `DEFAULT_STRATEGY` — o modo que
**prescreve** aporte sugerido + economia de IR — quando **não há IRPF
processado**; com IRPF autoritativo ele degrada para `informative-*`, que
**suprime** as duas prescrições ([[ADR-196]] §D5). **O card prescreve justamente
quando a evidência é mais fraca.**

> ### ⚠️ Isto falsifica um `Decidido` — não é lacuna, é contradição
>
> A [[ADR-196]] §1 **caso 4** afirma que o Card A ***subestima*** o espaço fiscal
> frente à fonte autoritativa. A medição diz o **oposto** para o arquétipo PJ.
> Corrigir o código sem registrar a falsificação deixa um `Decidido` assinado
> contradizendo `main` — a classe que esta sprint cataloga.
>
> E a [[ADR-196]] §D6 declara *"backend inalterado"*, o que **deixou de valer**:
> a mesma polaridade vive no Python (`PrevidenciaAnalyzer.analyze`,
> `previdencia_analyzer.py:219-229`, só cai em `_analyze_via_proxy` quando
> `capacidade_irpf is None` · [[ADR-277]]). A lane tem perna Python obrigatória.

## Medição de 2026-08-11 — o inventário rendeu mais do que o escrito

Remedidos os 6 achados de abertura: **5 confirmados**. O 6º precisa correção de
redação — a lane dizia *"`rg 'PGBL|dedu'` dá zero ocorrências"*; o medido é
**PGBL = 0, `dedu` = 1** (`has_deducao_saude_irpf`, `FORMULAS.md:381`, conceito
alheio). A substância vale; a afirmação literal, não.

**Quatro achados novos**, que moveram o desenho e estão na [[ADR-375]]:

1. **A alíquota marginal está errada nos dois caminhos**, inclusive o
   autoritativo. `_resolve_aliquota` devolve **27,5% para toda renda** com
   tabela bem-formada — medido em 20k/30k/40k/50k. Três modos errados (topo
   sempre, off-by-one sem faixa terminal, fallback 7,5% com faixas vazias).
2. **O defeito está armado para detonar num fix de dados.** Plumbar
   `fiscal_parameters.ir_brackets` converte o 7,5%-para-todos em
   27,5%-para-todos, **com CI verde**, porque 2 testes asseveram 27,5%. Prova
   por mutação: corrigi a função, caem exatamente esses 2 — e ambos
   *especificam o defeito*, com docstring justificando "paridade com legado".
3. **O golden é cego por construção.** Corrigir `_resolve_aliquota` **não move o
   golden** — o que refuta o argumento de que o `↓` ficaria ambíguo entre lanes.
   Injetar faixas reais na fixture virou **pré-requisito bloqueante**.

   > **Corrigido em 2026-08-11 (PR1).** Eu havia escrito que as suítes "não
   > injetam `ir_brackets` (zero ocorrências)". Falso como mecanismo:
   > `write_e5_config` **copia** `parametros_fiscais.json`, e a fixture declara a
   > tabela sob `faixas_mensais` — chave que nenhum leitor consome. Medi ausência
   > de string nos `.py` de teste e concluí ausência de **dado**; é afirmação de
   > ausência sobre fonte única.
4. **A fixture do dogfood é o caso isento** — base tributável R$ 11.520/ano
   contra isenção de R$ 27.110,40. O relatório publica hoje `economia de IR/ano
   = R$ 103,68` para quem não paga IR. O `financial-planner` enquadrou como erro
   **de sinal** (o PGBL converte principal não tributado em saldo tributado no
   resgate), contra o erro de **magnitude** do arquétipo PJ: é o ramo mais grave.

**Uma refutação registrada.** O `senior-cto` reportou divergência de 100× entre
a `nota` e `renda_tributavel_anual` no snapshot. Conferido: os campos são
**centavos**, e a cadeia fecha ao centavo com receita PJ de R$ 36.000/ano. Não
há o que explicar antes do rebaseline por esse motivo.

## Escopo

Definido pelo co-design de 2026-08-11 e escrito na **[[ADR-375]] (`Proposto`, #1377)**,
que fecha o gate de "ADR antes de qualquer PR de implementação".

O enquadramento mudou no co-design, e ficou **mais barato de defender**: a
[[ADR-236]] (`Decidido`, 2026-05-21) já declarou canônica a base e **condenou
nominalmente** a fórmula da S7 — *"**Base PGBL errada** … **Não é.**"*, com a
aritmética do arquétipo. A lane não decide base nova: **conforma a S7 a um
`Decidido` que a contradiz há três meses.**

Decisões (detalhe e justificativa na ADR): a S8 vira **dono único** do número
dedutível e a S7 deixa de publicar base/limite/aporte/economia (D1); a S7 mantém
card de previdência com registro trocado — patrimônio, PGBL×VGBL, custo, papel
na IF, **zero quantidade fiscal** (D2), o que fecha a **metade de hospedagem do
RV3-28** herdada da [[A40.l7]]; o proxy de 32% é **removido**, não recalibrado —
ele aproxima o teto da distribuição **isenta**, o *complemento* da base (D3);
piso de três condições para prescrever (D4); economia vira **diferencial**
`IR(base) − IR(base − aporte)`, que devolve zero para o isento por construção
(D5); a regra de faixa marginal vira **service próprio** com fonte única
[[ADR-135]] (D6); paridade com legado **não** justifica número prescritivo (D7).

**Supersedure parcial em dois destinos** — [[ADR-196]] *e* [[ADR-277]], com
emenda datada recíproca e `status: Decidido` preservado nas duas (o schema não
tem "parcialmente superado", e forçar o status a mentir é pior que a assimetria
de campo). Já aplicada.

**Forma: 3 PRs sequenciais.** P1 regra da faixa marginal extraída e testada
(**não** move golden) · P2 base + polaridade (move; declara delta) · P3
hospedagem na S7 + `FORMULAS.md`. P1 antes de P2 para que, ao declarar o `↓`, o
fator alíquota já esteja correto.

## Herdado da [[A40.l7]] (2026-08-11)

A **metade de hospedagem** do RV3-28. A l7 entregou a metade de **nome** (heading
e índice derivam da mesma fonte, #1355) e retitulou a S8; *mover* o card para a
S8 pressupõe que o card deve existir com a base atual — e **é esta lane que
decide isso**. Os 2 cross-links que a l7 entregou são **mitigação declarada**,
não solução.

## Critério de aceite

Revisado pelo co-design de 2026-08-11. O anterior tinha um item **inexequível**
(sinal `↓` conferido pelo golden) e faltavam os gates dos achados novos.

**Bloqueante, antes de qualquer medição de delta:**

- **Injetar `ir_brackets` reais (com faixa terminal) na fixture do snapshot.**
  Sem isso o fix da alíquota ship **sem gate** — o instrumento é cego por
  construção, e "corrigi, 2 testes caem" mede a suíte, não o relatório.

**Publicação:**

- **Um único limite PGBL no relatório inteiro**, ~~na S8~~ **no Card B
  (`S_IRPF_OTIMIZACAO`)** — corrigido 2026-08-13 pelo co-design (§Emenda da
  [[ADR-375]]). O gate é **textual**, não de inventário: medido que o de
  inventário passa verde com o teto publicado 2× dentro da S8, porque conta
  título de card e não vê corpo de trigger nem prosa.
- Prescrição **ausente/suprimida — não `R$ 0`** — sem IRPF **e** sem
  `business_profile`. R$ 0 como "aporte sugerido" continua sendo conselho.
- O gate incide sobre o **default do produtor**, não só sobre o call-site: se
  `aporte_mensal`/`economia_ir_anual` seguirem populados por default no
  dataclass, o card volta a publicar quando alguém mudar o `def`.
- `fonte_recomendacao` sobrevive; o valor `proxy_receita_pj` sai do vocabulário
  — e isso é teste de **consumidor**, não só de produtor.

**Testes (cada um mata um achado medido):**

- Renda **isenta** ⇒ `economia == 0`, `aporte == 0`, prescrição ausente, motivo
  publicado. É o ramo de dano de sinal, e é o que a fixture do dogfood exercita.
- Dedução **cruzando fronteira de faixa** ⇒ a diferencial acerta, o
  `limite × marginal` não.
- Faixa marginal sobre a **tabela anual real das 5 faixas** — mata os três modos
  de uma vez, inclusive o fallback. Renda interior a faixa intermediária **com**
  terminal `None` é o caso que hoje nenhum teste cobre;
  `test_ultima_faixa_sem_limite_captura_alta_renda` passa nos dois desenhos e é
  a fonte da falsa sensação de cobertura.
- `BusinessProfile` ausente ⇒ `pgbl_aplicavel` não é `True`.
- Os 2 testes que asseveram o defeito são **deletados** e reescritos com nomes
  que descrevem a regra (D7) — não `skip`, não `xfail`.

**Delta:**

- **Dois deltas declarados separadamente**, nunca um agregado: `limite_pgbl_anual`
  ⇒ `↓`; `aliquota_marginal` no golden ⇒ de 7,5% (fallback) para a faixa real —
  que **na fixture do dogfood é 0%**, porque a base é isenta. Ambos `↓` neste
  substrato; um agregado esconderia que os fatores se movem por causas distintas.
- A conferência é **manual**: `dev/golden_diff.py` não está em hook nem em job de
  CI (medido 2026-08-11 — só `dev/compare_reviews.py`, `dev/ledger_conservation.py`
  e `dev/ledger_certify_core.py` o importam). O que roda de fato é o assert do
  snapshot. Escrever "conferido por `golden_diff`" como se fosse gate era
  verdadeiro sobre o script e falso sobre o CI.

## PR1 — entregue 2026-08-11 (#1383)

`fix(pipeline)` `cc5d281e` + `test(golden)` `992bf0ad` + rebaseline `b5b96234`.

A regra de faixa marginal saiu para [`irpf_faixa_marginal.py`](../../../../pipeline/domain/services/irpf_faixa_marginal.py),
sobre a `IRPFBracket` **canônica** (centavos + `Decimal`). As 9 fronteiras do
seed devolviam 27,5%; agora devolvem 0 / 7,5 / 15 / 22,5 / 27,5. Delta no golden:
`aliquota_marginal` 7,5% → 0% e `economia_ir_anual` R$ 103,68 → R$ 0, em 520
folhas comparadas — **2 divergentes, nenhuma outra**.

Três defeitos morreram junto, nenhum deles no inventário: a segunda classe
`IRPFBracket` (contrato incompatível, import errado compilava), o falsy-zero de
`from_fiscal_parameters` (faixa de teto 0 virava terminal) e o float monetário
nesse caminho.

**O que o PR1 deliberadamente não fez:** o golden exercita `from_fiscal` (dict
legado), não `from_fiscal_parameters` (produção) — nenhum teste de golden
atravessa o construtor de produção, porque `ctx.config_store is None` em todos.
Coberto por unit test, incluindo a regressão do falsy-zero. Fechar essa lacuna
exige um fake de `config_store` no substrato, e não cabia aqui.

**O que o PR2 herda, agora visível no golden:** `aporte_mensal` continua
publicando R$ 115,20/mês ao lado de uma economia de R$ 0 — prescrição cujo
benefício declarado é zero. E o **D5 está bloqueado**: `deducao_brl_cents` está
em escala mensal contra faixas anuais, e nem o ×12 fecha (degrau de R$ 11,04 em
R$ 26.963,20). Detalhe na §Emenda da [[ADR-375]].

**Registro:**

- `docs/reference/FORMULAS.md` ganha a entrada PGBL (base canônica citando
  [[ADR-236]], teto de 12%, a diferencial, e as 3 condições). Hoje **zero**
  entradas de PGBL.
- Supersedure parcial recíproca em [[ADR-196]] **e** [[ADR-277]] — ✅ aplicada
  2026-08-11, gates verdes.
- **Verificação renderizada** (§Débito de método da sprint). O gate de pixel não
  vê supressão de texto; a conferência é textual, com proximidade.

## PR2 — entregue 2026-08-12 (#1394)

Fecha a **polaridade invertida**: sem IRPF processado, o relatório para de
prescrever. O proxy `receita_pj × 32%` foi **removido**, e sem capacidade
declarada os campos prescritivos nascem **ausentes** — não zerados. No PR1 a
economia deste workspace foi de R$ 103,68 para R$ 0; agora o campo não existe,
que é a diferença entre *"a economia é zero"* e *"não temos como medir"*.

Delta no golden: **8 campos**, todos em `previdencia_pgbl` — inclusive o
`aporte_mensal` de R$ 115,20/mês que o PR1 tinha deixado visível ao lado de uma
economia de R$ 0.

No frontend, a guarda lê o **payload**, não um 7º modo do enum: um modo novo
poria a decisão em dois lugares, e `getPgblCardStrategy` continuaria devolvendo
`default` sem IRPF. Os testes entram por `mode="default"` de propósito — é o
modo que rendia a prescrição.

De brinde, os campos monetários viraram `Decimal` (ADR-090): o hook
`float-money` é **diff-based**, então a linha grandfathered passou a valer ao
ser tocada.

**Fora de escopo, declarado:** D1 (S8 como dono único) e D2 (card com registro
trocado) ficam no PR3; `getPgblCardStrategy` some junto com a matriz de 6 modos.
O **D5 segue bloqueado** pela escala de `deducao_brl_cents`. E a pergunta de
domínio — faixa marginal sobre base de cálculo ou sobre rendimento bruto? —
segue **sem dono**: o `financial-planner` foi interrompido por limite de gasto
da conta. Não afeta o PR2; afeta o PR3.

## PR3a — entregue 2026-08-13 (#1437)

Fecha o **§D4 cond. 1** no lado da S8: `tipo_declaracao_ir` desconhecido deixa de
afirmar dedutibilidade. `_tipo_declaracao(bp=None)` devolvia `"completa"` e
`CascataInput` defaultava o mesmo — e a afirmação **libera T1 e T3**, os dois
triggers que prescrevem aporte. Medido antes do fix, com 3 testes escritos
primeiro: perfil ausente + base > 0 ⇒ **T3 dispara**. Se a família declara no
simplificado, a dedução é zero e o conselho foi inventado sobre um default.

A regra saiu para [`cascata_pgbl.py`](../../../../pipeline/domain/services/tributario/cascata_pgbl.py):
`cascata_calculator.py` estava em **498/500** linhas e o gate P2 reprova qualquer
adição. Extração mecânica, no mesmo commit, declarada na mensagem.

Motivo novo testado no **consumidor**, não só no produtor — sem o ramo em
`PgblStatus` o bloco imprimiria o teto sem caveat nenhum, e sem o verbete no
narrador o motivo cairia no fall-through genérico. De brinde: a `description` de
`previdencia_pgbl` no schema E5 e a docstring de `_build_capacidade_pgbl` ainda
documentavam o `proxy_receita_pj` que o PR2 removeu.

**O golden não se move** e isso é esperado: `tributario` é `None` no snapshot do
dogfood, então o produtor da S8 é invisível ao snapshot.

## Co-design de 2026-08-13 — o inventário era de 2 e são 6

`financial-planner` + `product-designer` em paralelo; **divergiram na hospedagem**
e o `senior-cto` fechou (protocolo anti-loop). Detalhe e justificativa na
§Emenda 2026-08-13 da [[ADR-375]]. O que muda para a execução:

**Quatro publicadores que a lane não contava:** T3 (`pgbl_limite_anual_brl`), T1
(`aporte_pgbl_extra_anual_brl` + `economia_ir_anual_brl`, pelo instrumento que o
D5 condena), a prosa do narrador, e o **catálogo de citação do parecer** — as
folhas `limite_pgbl_anual` / `aporte_mensal` / `renda_tributavel_anual` casam o
predicado monetário e são citáveis por LLM; as do Card B não casam. Consequência
direta: **"um único limite PGBL no relatório inteiro" era falso se o PR3 parasse
no bloco da S8.**

**O instrumento do gate estava errado.** Medido em `medium.json`: R$ 4.320
aparece **duas vezes dentro da S8** (bloco + corpo do T3) e o gate de inventário
passa **verde** — ele conta título de card e é cego a corpo de trigger e a prosa.
O gate certo é **textual** (padrão de `print-text.@critical.spec.ts`, que já roda
em `frontend-checks ⊂ all-green.needs`).

**O D1 troca de dono** — Card B (`S_IRPF_OTIMIZACAO`), por evidência: o piso do D4
é nativo lá e sintético na S8. A partição por horizonte foi recusada por medição
(a base da S8 é híbrida). **O D2 vira nota**, não card: custo não existe em schema
nenhum, regime defaulta `progressivo` no silêncio, e o saldo já sai na S3.

**A fixture certifica um estado impossível.** `medium.json` traz
`previdencia_pgbl = {"saldo": 45000}` — chave que nenhum produtor emite — e **zero**
bloco `irpf`. O card da S7 cai no `DefaultPrevidenciaCard` com os três KPIs
`undefined`: o único sinal de S7 no gate é ficção, e Card B + os 4 modos
informativos **nunca montam em gate nenhum**. Mesma classe do `exposicao_cambial`
([[A40.l33]]) e do `anexo_v`.

## PR3b — o que falta

- **De-publicar os quatro sites restantes**: T3 (corpo **e** `params` — campo sem
  leitor é faceta inerte), `_pgbl_clause` (base + ponteiro, com unit test próprio
  porque `narrativas.S8` é `null` nas fixtures), a folha citável do parecer
  (renomear para fora do predicado monetário ou remover), e a S7.
- **T1**: suprimir `aporte_pgbl_extra_anual_brl` + `economia_ir_anual_brl`. Não é
  escopo novo — é o D4 cond. 2 num site que o inventário da ADR perdeu. A
  *correção* (fonte da faixa) fica na [[A40.l37]], que precisa **herdar D4 cond. 2
  + D5 + D6 + [[ADR-135]] por escrito**; sem isso migra a fonte e preserva o
  instrumento condenado com CI verde.
- **S7 vira nota de 2 estados**; morrem o card, a matriz de 6 modos e
  `getPgblCardStrategy`. **Preservar** `derivePrimaryYear` + `matchIrpfToPeriod`:
  a linha de defasagem ≥2 anos não existe no Card B e é sinal órfão se não migrar.
  Idem a `nota` do produtor (diferimento + ano-calendário corrente, [[ADR-305]] D3).
- **Fixture + gate**: `medium.json` ganha bloco `irpf` e perde o `saldo`;
  `report-inventory.expected.json` perde a linha "Previdência PGBL" **à mão**
  (regenerar não conserta remoção) e ganha as chaves das seções que passam a
  montar.
- **`FORMULAS.md`**: entrada PGBL (hoje **zero** ocorrências) — teto = 12% do
  rendimento **bruto** tributável citando [[ADR-236]], faixa marginal sobre **base
  de cálculo**, a diferencial, os estados e a distinção teto × restante.
- **`ParecerAncoraChips.tsx`**: o rótulo `previdencia_pgbl → "Previdência PGBL"`
  fica falso no merge, e o comentário acima dele justifica o valor dizendo que é o
  title do card da S7. Colisão declarada com a [[A40.l49]] PR1, que substitui o
  mapa inteiro.
- **Emenda da [[ADR-375]]** — ✅ aplicada 2026-08-13; `Proposto` → `Decidido (A40)`
  no merge do PR3b.

## Colisão declarada

`S7IndependenciaSection.tsx` é tocado também pela [[A40.l25]] e pela [[A40.l29]].
Quem mergear depois rebaseia. Não há dependência de conteúdo.
