---
id: ADR-375
type: adr
title: "Limite PGBL tem um produtor, e a prescrição exige evidência declarada"
status: Proposto
phase: A40
date: "2026-08-11"
relates_to:
  - "[[ADR-236]]"
  - "[[ADR-135]]"
  - "[[ADR-089]]"
  - "[[ADR-097]]"
  - "[[ADR-370]]"
supersedes:
  - "[[ADR-196]]"
  - "[[ADR-277]]"
superseded_by: []
aliases: ["ADR 375", "base do limite PGBL", "polaridade da prescrição PGBL"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# ADR-375 — Limite PGBL tem um produtor, e a prescrição exige evidência declarada

> Esta ADR **não decide base nova**. A [[ADR-236]] já declarou canônica a base
> do limite PGBL em 2026-05-21 e **condenou nominalmente** a fórmula que a S7
> usa. Esta ADR conforma a S7 àquele `Decidido` e retira as duas cláusulas que
> a mantiveram divergente por três meses.

## Contexto

O relatório publica **"Limite PGBL (12%)" em duas seções, sobre bases que ele
mesmo declara incompatíveis**:

| Superfície | Base |
|---|---|
| **S7**, `PrevidenciaAnalyzer._analyze_via_proxy` ([previdencia_analyzer.py:264](../../pipeline/domain/services/previdencia_analyzer.py)) | `receita_pj_anual × 32%` (lucro presumido) |
| **S8**, `PgblBlock` ([CascataFiscalCard.pgbl.tsx:38](../../frontend/src/components/report/cards/CascataFiscalCard.pgbl.tsx)) | pró-labore + outras tributáveis IRPF; lucros distribuídos fora |

A [[ADR-236]] §3 já escreveu, em 2026-05-21: *"**Base PGBL errada** — texto
afirma que `receita_pj × 32%` … **Não é.**"*, com a aritmética do arquétipo
(pró-labore R$ 1.500/mês + R$ 40k/mês de lucros isentos ⇒ base ≈ R$ 18k/ano,
*independente* de a receita PJ ser R$ 500k ou R$ 5M). A S7 nunca conformou.

### O proxy não está descalibrado — está invertido

Sob lucro presumido, `receita_PJ × 32%` líquido dos tributos aproxima o teto do
que se distribui **isento** ao sócio (Lei 9.249/95 art. 10 · IN RFB 1.700/2017
art. 238). É o **complemento** da base PGBL: o proxy usa como base tributável a
grandeza que melhor estima o que **não** é tributável. Nenhum coeficiente
conserta referente invertido — daí **remover**, não recalibrar.

Por isso a [[ADR-196]] §1 caso 4 (*"Card A **subestima** espaço fiscal"*) não
precisa de correção de direção e sim de **substituição**: ela afirma sinal sobre
uma quantidade cujo sinal é indeterminado — depende de
`(pró-labore + outras) ÷ (0,32 × receita_PJ)`, com erro ilimitado nos dois lados.

### A polaridade da prescrição está invertida, em três lugares

`getPgblCardStrategy` ([pgbl-card-strategy.ts:103](../../frontend/src/lib/irpf/pgbl-card-strategy.ts))
devolve `DEFAULT_STRATEGY` — o modo que **prescreve** aporte + economia — quando
**não há** IRPF; com IRPF autoritativo degrada para `informative-*`, que
**suprime**. `PrevidenciaAnalyzer.analyze` ([previdencia_analyzer.py:227](../../pipeline/domain/services/previdencia_analyzer.py))
espelha no Python — o que falsifica a §D6 da [[ADR-196]] (*"backend
inalterado"*). E `_tipo_declaracao` ([tributario_input_builder.py:280](../../backend/app/services/tributario_input_builder.py))
devolve `"completa"` na **ausência** de `BusinessProfile`, então a S8 afirma
`pgbl_aplicavel` sobre um default. **Prescreve-se onde a evidência é mais fraca.**

### A alíquota marginal está errada nos dois caminhos — medido 2026-08-11

`_resolve_aliquota` tem `elif faixa.limite_anual is None: aliquota = ...` **sem
guarda de renda**. Com a tabela IRPF anual real:

| renda anual | devolvido | correto |
|---|---|---|
| 20.000 | **27,5%** | 0% (isento) |
| 30.000 | **27,5%** | 7,5% |
| 40.000 | **27,5%** | 15% |
| 50.000 | **27,5%** | 22,5% |

São **três** modos errados: (a) toda renda recebe a alíquota do topo quando a
tabela tem faixa terminal; (b) sem faixa terminal, devolve a alíquota da faixa
**excedida**, não da que contém (38,4k numa tabela 24k/48k ⇒ 7,5%, correto 15%);
(c) com `irpf_faixas` vazia cai em `aliquota_fallback = 7,5%`. Atinge também
`_analyze_via_irpf` — o caminho **autoritativo**.

**O defeito está armado para detonar num fix de dados.** Plumbar
`fiscal_parameters.ir_brackets` — correção que qualquer agente faria sem ADR —
converte o 7,5%-para-todos em 27,5%-para-todos, **com CI verde**, porque dois
testes asseveram 27,5%.

### `limite × alíquota marginal` é o instrumento errado

A economia é `IR(base) − IR(base − aporte)`. Multiplicar pela marginal
superestima sempre que a fatia de 12% cruza fronteira de faixa e — decisivo —
**não devolve zero para o isento**. A diferencial devolve, por construção. A
primitiva progressiva correta já existe: `compute_irrf_mensal`
([cascata_calculator.py:189](../../pipeline/domain/services/tributario/cascata_calculator.py)).

### Já há segundo produtor da mesma regra, e ele discorda

`_ir_marginal_anual` ([cascata_triggers.py:50](../../pipeline/domain/services/tributario/cascata_triggers.py))
resolve a faixa marginal com semântica **correta**, em escala **mensal**, sobre
`IRRF_TABELA_MENSAL` **hardcoded** — tensão direta com a [[ADR-135]], que pôs as
faixas em `fiscal_parameters`. Dois "economia de IR" no mesmo documento, sobre a
mesma pessoa, por regras diferentes: a mesma classe que nomeia esta ADR, um
andar abaixo.

## Decisão

**D1 — Um produtor, uma publicação.** O número dedutível tem dono único: a
cascata fiscal (S8), cuja base já é a canônica da [[ADR-236]]. A S7 **deixa de
publicar** base, limite, aporte sugerido e economia de IR. O `restante`
(teto − aportado) do caminho IRPF muda de casa, para o bloco PGBL da S8, onde a
base que o torna interpretável já mora.

> Recusada a alternativa "S7 publica só quando há IRPF autoritativo": ela faria a
> S7 imprimir `restante` e a S8 imprimir `teto` sob **o mesmo rótulo "Limite PGBL
> (12%)"**, com valores diferentes derivados da mesma fonte — a duplicação que
> esta ADR existe para matar. E preservaria a matriz de 6 modos, que é onde a
> inversão de polaridade se escondeu por três meses.

**D2 — A S7 mantém card de previdência com registro trocado:** patrimônio
previdenciário, PGBL×VGBL quando conhecido, custo (taxa de administração e
carregamento via informes, [[ADR-238]]) e papel na IF. **Zero quantidade
fiscal**, mais cross-link para a S8.

**D3 — O proxy `receita_pj × 32%` é removido**, não recalibrado (ver Contexto).
`fonte_recomendacao` sobrevive como campo de proveniência; o valor
`proxy_receita_pj` sai do vocabulário.

**D4 — Piso de prescrição.** Não se prescreve PGBL nem se publica "economia de
IR" a menos que as três sejam simultaneamente verdadeiras:

1. `tipo_declaracao_ir == "completa"` **conhecido**, não defaultado;
2. `IR(base) − IR(base − aporte) > 0` no ano, com as faixas vindo de
   `fiscal_parameters` — **nunca literal em código**;
3. contribuição a regime oficial (INSS/RPPS) presente — precondição legal dos
   12%. Quando desconhecida, a copy declara a precondição.

Abaixo do piso a saída **não é número menor: é "não se aplica" com o motivo**. E
a dedução nunca sai em `--semantic-gain` — é **diferimento**, não ganho: o
resgate é tributado sobre o **total**, não sobre o rendimento.

**D5 — A economia passa a ser diferencial**, `IR(base) − IR(base − aporte)`,
sobre uma função `IR(base, ano)`. Encerra o `limite × marginal`.

**D6 — A regra de faixa marginal vira service de domínio próprio**, com fonte
única `FiscalParameters.ir_brackets` ([[ADR-135]]), função pura sobre renda
**anual** e conversor explícito de escala. Injetada por construtor na config
tipada que o `PrevidenciaAnalyzer` já recebe ([[ADR-089]]/[[ADR-097]]). Nesta
lane migra **um** consumidor; `cascata_triggers` muda T1/T3 publicados e vai em
lane própria.

**D7 — Paridade com legado nunca justifica número prescritivo.** Os dois testes
que caem (`test_sempre_aplica_ultima_faixa_sem_limite`,
`test_faixas_sem_ultima_none_usa_ultima_aplicavel`) não são testes de paridade:
são **especificação do defeito**, com docstring explicando o mecanismo do bug
como se fosse a regra. São **deletados** — não `skip`, não `xfail` — e
reescritos com nomes que descrevem a regra. Paridade pode governar número
descritivo durante janela de migração; para número prescritivo, correção vence.

## Consequências

**O que da [[ADR-196]] permanece vigente:** §D2 (switch de modos), §D3, §D4, §4
(copy com sign-off G0), §5. **O que cai:** §D1 na linha `irpfKpis = null`, §D5
na linha `default`, §D6 inteira, §1 caso 4 (substituído — ver Contexto).

**O que da [[ADR-277]] permanece vigente:** INV-PREV-2, INV-PREV-3, o boundary
do value object `CapacidadePgblIRPF`, e `fonte_recomendacao` como campo de
proveniência. **O que cai:** §Escopo na cláusula *"sem IRPF, comportamento
idêntico ao atual (fallback proxy)"* e o ramo `capacidade_irpf is None`.

**O golden é cego ao defeito da alíquota — e isso é gate bloqueante.** Nem
`test_report_view_model_snapshot.py` nem `test_e5_golden_execution.py` injetam
`ir_brackets`; `irpf_faixas` fica vazia e devolve o fallback. **Corrigir
`_resolve_aliquota` não move o golden.** Injetar faixas reais na fixture é
pré-requisito, não polimento: sem isso o fix ship sem gate.

**A fixture do dogfood é o caso isento** — base tributável R$ 11.520/ano contra
o limite de isenção de R$ 27.110,40. O relatório publica hoje `economia de
IR/ano = R$ 103,68` para quem não paga IR. É o ramo de dano **de sinal** (quanto
mais a família seguir, mais perde: o PGBL converte principal não tributado em
saldo tributado integralmente no resgate), contra o erro de **magnitude** do
arquétipo PJ. Com D5 + D6 + faixas na fixture, esse campo vai a `R$ 0` e a
prescrição some — é a verificação de aceite mais direta que esta ADR tem.

**Custo:** a lane cresce para três PRs sequenciais (P1 regra da faixa — não move
golden; P2 base + polaridade — move; P3 hospedagem + `FORMULAS.md`), mexe no
substrato do snapshot e emenda duas ADRs.

## Não-objetivos (achados datados 2026-08-11, com rota própria)

- **Double-count potencial na base da S8** — `cascata_calculator.py:383` soma
  `bruto_anual` (pró-labore anualizado) + `outras_rendas_tributaveis_pf_anual`,
  e este último vem de `_load_irpf_renda_tributavel` = **total** de rendimentos
  tributáveis do IRPF. Se o total já contém o pró-labore, a base soma duas
  vezes. É defeito do produtor da S8, dentro da [[ADR-236]]. Lane nova.
- **Migração de `cascata_triggers._ir_marginal_anual`** para o resolver comum e
  retirada de `IRRF_TABELA_MENSAL` hardcoded em favor da [[ADR-135]]. Lane nova.
- **Redutor da Lei 15.270** torna qualquer lookup de faixa incapaz de acertar a
  banda de phase-out — razão adicional para a diferencial de D5, mas a
  modelagem do redutor não entra aqui.

## Alternativas consideradas

**Emendar a [[ADR-196]] sem ADR nova.** Recusada: muda a base (regra de
domínio), inverte a polaridade, falsifica o §1 caso 4 e remove o card que a
ADR-196 desenhou em seis modos.

**`superseded_by` na [[ADR-196]] inteira.** Recusada por vocabulário de estado: o
`ADR_INDEX` classificaria como superada uma ADR cujos quatro modos informativos
e a copy §4 continuam sendo o contrato em produção — e neste repo se audita por
status, não por conteúdo.

**Campo `partially_superseded_by` novo.** Recusada: `note-adr.schema.json` não o
tem, e vocabulário de schema é escopo de `information-architect` em lane própria.
A precisão do "parcial" vive nas duas seções nomeadas de §Consequências, com
emenda datada recíproca nos dois arquivos, `status` preservado em ambos.

## Co-design

`financial-planner` + `senior-cto` em paralelo, 2026-08-11. Divergência
registrada: o `senior-cto` reportou divergência de 100× entre a `nota` e
`renda_tributavel_anual` no snapshot — **refutada** na conferência: os campos são
centavos e a cadeia fecha ao centavo com receita PJ de R$ 36.000/ano. Nada a
explicar antes do rebaseline por esse motivo.
