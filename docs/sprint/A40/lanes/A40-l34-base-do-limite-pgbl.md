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
  - status/open
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
3. **O golden é cego por construção.** Nem `test_report_view_model_snapshot.py`
   nem `test_e5_golden_execution.py` injetam `ir_brackets` (medido: zero
   ocorrências). Corrigir `_resolve_aliquota` **não move o golden** — o que
   refuta o argumento de que o `↓` ficaria ambíguo entre lanes. Injetar faixas
   reais na fixture virou **pré-requisito bloqueante**.
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

- **Um único limite PGBL no relatório inteiro**, na S8. Gate de inventário
  (padrão [[ADR-370]]) impede que superfície futura re-publique.
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

**Registro:**

- `docs/reference/FORMULAS.md` ganha a entrada PGBL (base canônica citando
  [[ADR-236]], teto de 12%, a diferencial, e as 3 condições). Hoje **zero**
  entradas de PGBL.
- Supersedure parcial recíproca em [[ADR-196]] **e** [[ADR-277]] — ✅ aplicada
  2026-08-11, gates verdes.
- **Verificação renderizada** (§Débito de método da sprint). O gate de pixel não
  vê supressão de texto; a conferência é textual, com proximidade.

## Colisão declarada

`S7IndependenciaSection.tsx` é tocado também pela [[A40.l25]] e pela [[A40.l29]].
Quem mergear depois rebaseia. Não há dependência de conteúdo.
