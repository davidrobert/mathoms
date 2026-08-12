---
id: A40.l51
type: lane
title: "Follow-ups órfãos da A40.l43: o que o co-design achou na vizinhança e ninguém está atacando"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l51-followups-orfaos
adrs:
  - "[[ADR-356]]"
  - "[[ADR-319]]"
  - "[[ADR-236]]"
  - "[[ADR-090]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/frontend
  - area/pipeline
  - area/financial-planning
---

# A40.l51 — `followups-orfaos-da-l43`

> **Aberta em 2026-08-12**, a pedido do dono: *"todos os follow-ups (ou achados que
> estão em aberto) que não estão sendo atacados deveriam estar documentados em uma
> nova lane no fim do sprint A40"*. Cumpre a convenção que o §Inventário de
> follow-up já declara — **um item ou tem lane, ou tem disposição escrita; item que
> tem só descrição evapora no fim da sprint.**
>
> **Prioridade P1 é proposta**, elevada de P2 depois da medição: 3 dos itens são
> defeito **em prosa/número já entregue ao usuário**, não débito de forma.
> Colocação, prioridade final e onda são gatilho de `product-manager`.

## O que esta lane é

O co-design da [[A40.l43]] (`prompt-engineer` + `financial-planner` +
`product-designer`, escalado ao `senior-cto`) apontou defeitos **vizinhos** ao
escopo. Os que **têm dono** foram roteados e estão escritos na lane receptora —
[[A40.l6]], [[A40.l15]], [[A40.l29]]. Esta lane recebe **só o que sobrou sem dono**,
mais o que a medição desta sessão descobriu por conta própria.

**Cada item diz o que foi medido, com caminho de re-medição.** Achado alegado que a
medição refutou está na §Fantasmas — para ninguém reabrir.

---

## Críticos — número ou prosa **já entregues** estão errados

### C1. O score de endividamento tem o sinal invertido no default do código

`FinancialScoreConfig.default()` declara `invertido=False` para
`taxa_endividamento`; `config/scoring.json → score_componentes` declara **`true`**.
O código contradiz o config, a própria docstring do módulo (*"invertido: maior =
pior"*) e a `docs/reference/FORMULAS.md`.

**Medido em 2026-08-12** (não por leitura — por execução):

```
DEFAULT   (invertido=False)  | endiv  5% -> nota  0.0 | endiv 20% -> nota 3.3 | endiv 50% -> nota 10.0
scoring.json (invertido=True)| endiv  5% -> nota 10.0 | endiv 20% -> nota 6.7 | endiv 50% -> nota  0.0
```

Endividamento de **5% recebe nota 0,0** e de **50% recebe nota 10,0**. Inversão
total: a melhor situação é pontuada como a pior.

**Alcançável, e por 3 caminhos:**

| call site | como chega ao default |
|---|---|
| `pipeline/domain/services/e5_analyzer_adapter.py:332` | `FinancialScoreCalculator(FinancialScoreConfig.default())` |
| `backend/app/services/score_reader.py:40` | `FinancialScoreCalculator(FinancialScoreConfig.default())` — **backend** |
| `e5_analyzer_adapter.py:419` | `from_scoring_json(scoring or {})` → `cfg={}` → `overrides={}` → cai no default |

O merge é por chave (`invertido=bool(overrides.get("invertido", default.invertido))`,
`financial_score_calculator.py:162`), então **basta o override faltar** para o sinal
inverter. `from_scoring_json({})` devolve `invertido=False` — medido.

- **Fix:** `financial_score_calculator.py:99` → `invertido=True`. Um caractere de
  intenção, mas **muda score** em qualquer caminho que usava o default, logo move
  snapshot/golden — e é mudança de comportamento de domínio: **gatilho
  `financial-planner`** antes do PR.
- **Aceite:** teste que assere `FinancialScoreConfig.default().endividamento.invertido
  is True` **e** que o default concorde com `scoring.json` para **todos** os
  componentes (gate de classe: divergência nova entre default e config quebra).
- **Re-medir:** o bloco de execução acima, com
  `FinancialScoreConfig.default()` vs `from_scoring_json(json.load(open('config/scoring.json')))`.

### C2. Separador de milhar dos EUA em prosa entregue: `R$ 2,000` e `R$ 36,000`

**Medido** em `backend/tests/snapshots/dogfood_view_model.json` — snapshot do
view-model **entregue**:

- `:253` — `consumo_consciente.analise`: *"Nenhum gasto pontual relevante ≥ **R$ 2,000**
  identificado no período…"*
- `:662` — `previdencia_pgbl.nota`: *"Base: receita PJ anualizada **R$ 36,000**, lucro
  presumido 32%."*

Em português, `R$ 2,000` lê **R$ 2** com três decimais — não R$ 2.000. É `:,.0f`
(convenção US) escapando para prosa de um relatório em pt-BR. Viola a regra de idioma
do CLAUDE.md e a §4 do COPY_GUIDELINES.

- **Fix:** formatação pt-BR nos 4 pontos produtores. Localizar com
  `rg -n ':,\.[0-9]f' pipeline/ backend/app/services/ | rg -v replace`.
- **Aceite:** gate que proíbe o padrão `R$ \d+,\d{3}` em **qualquer string do
  view-model entregue** — assert sobre o snapshot, não sobre o produtor (é a chave que
  o leitor vê).

### C3. `.replace(",", ".")` na prosa inteira corrompe a pontuação da sugestão

`pipeline/domain/services/suggestion_rules.py:574` aplica `.replace(",", ".")` à
**string montada inteira**, para trocar o separador de milhar. Efeito colateral
medido — 5 vírgulas gramaticais destruídas:

```
antes:   "Patrimônio já passou de 62% da meta IF, mas a renda passiva…"
entregue:"Patrimônio já passou de 62% da meta IF. mas a renda passiva…"
```

Ponto no meio da frase, seguido de minúscula, no texto que o usuário lê.

- **Fix:** formatar o valor num helper e **remover** o `.replace` da string.
- **Aceite:** regressão asserindo que o rationale contém `", mas a renda"`. Prova por
  mutação: reintroduzir o `.replace` deixa vermelho.

### C4. A causa-raiz que a l43 diagnosticou foi removida **pela metade**

Este é o achado mais importante da medição, e é **crítica à própria l43**.

A l43 e a emenda [[ADR-356]] concluíram que o defeito não era do autor do template,
e sim da regra do validador que **proibia silêncio** — e escreveram, textualmente,
que *"enquanto a regra vivesse, ela reproduziria o defeito na próxima mão"*. A l43
removeu a exigência de `perfil_familia.right`… **e deixou a regra idêntica viva para
todas as 10 summaries.**

`pipeline/domain/services/narrativas/format_helpers.py:244-251`, ainda em vigor:

```python
required_summaries = [f"s{i}" for i in range(1, 11)]
for s_key in required_summaries:
    if s_key not in summaries:      errors.append(f"Missing summaries.{s_key}")
    elif not summaries[s_key]:      errors.append(f"summaries.{s_key} is empty")
```

Compare com o que a l43 **de fato** removeu, 24 linhas acima no mesmo arquivo.

**Consequência medida:** 4 das 10 summaries são órfãs (`s2`/`s3`/`s5`/`s6`,
declaradas em `ORPHAN_SUMMARY_KEYS`), e o validador **obriga as 4 a emitir texto
não-vazio** — ou seja, obriga a fabricar prosa para 4 chaves que **nenhuma superfície
lê**. É a mesma pressão, no mesmo arquivo, produzindo o mesmo tipo de saída.

Foi gate de **instância** vestido de gate de classe — exatamente o erro que a l43
diagnosticou nos outros.

- **Fix:** trocar presença-não-vazia por exigência **condicionada à entrega** — só é
  obrigatório ter texto quem tem destino declarado em `summary_source` (s1, s4, s7,
  s8, s9, s10); chave em `ORPHAN_SUMMARY_KEYS` pode ser ausente ou vazia.
- **Isto destrava o fix de I8**: hoje não se pode silenciar o `s2` porque o gate
  proíbe.
- **Aceite (prova por mutação):** reverter o fix do validador deixa vermelho um teste
  que afirma que `s2` **pode** ser silenciado.

---

## Importantes

### I1. O parágrafo do filho: 4 defeitos no mesmo `_filho_paragrafo`

Tudo em `pipeline/domain/services/narrativas/perfil_familia_narrator.py`, na coluna
`left` que **sobreviveu** à l43:

1. **`:60` afirma "Primeiro filho do casal" incondicionalmente.** Workspace de
   titular solteiro com filho produz afirmação **falsa** no relatório entregue.
   Note a assimetria: `:162-163` gateiam `if _tit` / `if _conj`, e `:164` chama
   `_filho_paragrafo` sem gate de composição. COPY_GUIDELINES §8 proíbe assumir
   composição familiar.
2. **O ordinal "Primeiro" é ordem de inserção do dict, não idade** — `:89-93` usa
   `next(...)` sobre `fm.items()`. E o **2º filho em diante desaparece do card**:
   dispara em qualquer família com 2+ filhos, sem depender de composição.
3. **`:63` afirma juízo incondicional** — *"peça central no planejamento sucessório
   da família"* — sobre qualquer filho. **Viola a regra de classe que a emenda
   [[ADR-356]] acabou de escrever** (o narrador não publica juízo qualitativo).
4. **Idade do dependente é omitida** enquanto a dos adultos é impressa
   (`_membro_paragrafo` recebe `idade`; `_filho_paragrafo` não recebe nem lê
   `data_nascimento`). A omissão **não** é exigida pela [[ADR-319]], que proíbe o
   **nome** do menor. É lacuna de produto com decisão pendente — **não implementar
   sem decisão**.
5. **Membro com `papel == "dependente"` é invisível na prosa** — o filtro casa só
   `"filho"`, e o enum aceita ambos. Não é só a idade que falta: a pessoa inteira
   desaparece do card. A l35/l7 têm o predicado de dependente só no
   `protection_bundle_populator`; o fix de lá **não alcança** o narrador.

**Falso-verde no gate da própria l43:** `test_perfil_nao_emite_juizo_qualitativo`
checa 3 literais (`saudável`, `base sólida`, `diversificada`) e **não pega** "peça
central no planejamento sucessório". A emenda declara a regra ampla; o gate mede 3
strings — gate de instância vestido de gate de classe. **Fechar isso é parte de I1**,
não item separado: a regra existe, a medição não.

### I2. `fmt_currency` contra COPY_GUIDELINES §4 — e há **6** formatadores independentes

Blast radius **medido**: `fmt_currency` tem **72 call sites de produção**
(`charts_narrator` 35, `summaries_narrator` 20, `alocacao_narrator` 3,
`tributario_narrator` 2, …). Defeitos confirmados contra o texto literal da guideline:

| # | defeito | evidência |
|---|---|---|
| a | emite `k`/`M` onde §4.2 manda `mil`/`mi`/`bi` | `format_helpers.py:41,45,47` · medido `fmt_currency(45000) → 'R$ 45k'` |
| b | negativo sai `R$ -1,5M` — §4.1 proíbe sinal entre símbolo e número (canônico `-R$ 1,5 mi`) | `:36` + `f"R$ {sign}…"` · alcançável por `fmt_currency(M['fluxo_liquido'])` em `charts_narrator.py:166,187` |
| c | espaço comum onde §4.1 manda NBSP | medido: todo output traz `0x20` |
| d | §4.2 exige forma **completa** abaixo de R$ 10.000, mas compacta a partir de R$ 1.000 | `:42` · `fmt_currency(1500) → 'R$ 1,5k'` |
| e | `backend/app/services/dashboard_service.py:25-30` é um **3º formatador** com os mesmos defeitos **+ separador US** | `_fmt_brl`, consumido em `:58`/`:85` |

**Veredito: lane própria, não polish** — e o argumento não é o tamanho do diff: são
formatadores independentes na mesma superfície, e corrigir só um cria divergência
interna nova em vez de fechar a classe. Também há um **obstáculo de desenho**: a §4
manda *"renderização única via `<MonetaryValue/>`, nunca formatar à mão"*, o que é
impossível para prosa **materializada no pipeline** — a §4 precisa de emenda com
sub-seção "prosa gerada (E5.N / parecer / sugestões)" antes do fix de código, senão o
código escolhe a convenção sozinho. Revisor exigido pela §12 da guideline:
`product-designer`.

### I3. `taxa_endividamento` — o config declara uma unidade e a fórmula calcula outra

`ratios_calculator.py:279-282` calcula `dividas / patrimonio_bruto` — alavancagem de
**balanço**. `config/scoring.json:63` declara `"unidade": "% renda mensal comprometida"`
(com atribuição de fonte metodológica), que é serviço da dívida sobre **renda** —
conceito diferente. O mesmo erro está no `_metodologia` (`:22-25`), que é o texto que
um agente/humano lê para entender a métrica.

`docs/reference/FORMULAS.md` **não tem linha** para `taxa_endividamento` (0 hits em
402 linhas; o nome aparece só na tabela de pesos do score, `:90`).

- **Não-breaking:** nenhum consumidor lê `unidade` — `_component` lê exatamente 5
  chaves (`range_min`, `range_max`, `peso`, `nome_display`, `invertido`).
- **Fix:** 2 strings em `scoring.json` (unidade → "% do patrimônio bruto"; racional →
  descrever alavancagem, preservando a atribuição de fonte apenas onde ela de fato se
  aplica — a **priorização** de quitar dívida cara antes de aportar em risco) + 1
  linha em `FORMULAS.md`. **Docs-only.**
- **Não confundir com C1**, que é o cálculo. Este é o rótulo.

### I4. As 5 fixtures E2E restantes têm o contrato morto

> **Fronteira com a [[A40.l46]]** (aberta no mesmo dia, no fecho do #1382): ela é
> dona de **provar o gate de print** — o job `frontend-print-visual` é label-gated e
> **skipou em 4 PRs seguidos** no mesmo card, o #1386 desta sessão incluído. Este
> item é dona do **insumo**: com as fixtures emitindo string, rodar o job não
> revelaria os estados vazios, porque a seção não renderiza. **Complementares, não
> duplicados** — a l46 responde "o gate está verde?", este responde "o gate está
> olhando para algo?". Se executados juntos, a ordem é: fixtures primeiro, prova
> depois.

**Medido:** só `medium.json` emite `{left}`; `degraded`, `janela-divergente`,
`large-values`, `long-strings` e `sparse-data` emitem **string**. Com string,
`parseParagraphs` recebe `undefined` e a narrativa não renderiza — então os **estados
vazios por metade** da seção de identidade (só roster / só narrativa / `null` quando
ambos faltam), que são o desenho declarado, **nunca apareceram** em baseline visual,
print ou axe.

Pesa mais agora: a l43 mudou o layout da prosa (`sm:columns-2`, com fallback de 1
coluna em ≤2 parágrafos) e o caso de 1 parágrafo — workspace de uma pessoa, que o
PRODUCT.md admite — não tem baseline.

- **Trava medida:** fixture escrita à mão descreve o que o produtor **não** emite. O
  #1382 caiu nisso duas vezes: pôs em `right` uma prosa de "Plano de vida centrado na
  consolidação patrimonial…" que o narrador nunca produziu, **e** `medium.json:331`
  ainda carrega uma paráfrase à mão (*"O primeiro filho do casal é peça central…"*)
  diferente do que o produtor emite. Derive o conteúdo da fixture gerada
  (`tests/fixtures/narrativas/e5n_delivery.json`).
- **Aceite:** primeira baseline do bloco **olhada**, nunca commitada às cegas.

### I5. Heading order do relatório: h1 → h3 → h2, e o Sumário Executivo sem heading

**Medido:** `ReportCard.tsx:45` emite `<h3>` **fixo**, sem prop de nível;
`ExecutiveSummarySection.tsx:30` tem só `aria-label`. O gate roda
`critical+serious` (`a11y.@critical.spec.ts`) e `axe` classifica `heading-order` como
**`moderate`** — não pega.

Duas consequências distintas: ordem quebrada é violação de WCAG 1.3.1 invisível ao
gate; e o bloco protagonista não tem âncora navegável para leitor de tela.

- **Fix:** `titleAs?: "h2" | "h3"` no `ReportCard` + `h2` nos cards de nível de
  documento + heading (visível ou `sr-only`) no Sumário Executivo. Rebaseline visual.
- **Decisão embutida:** alargar o gate axe além de `critical+serious`, ou assert
  dedicado de ordem? Alargar traz o resto do `moderate` — medir o backlog antes.
- **Não fundir** com o débito de [[ADR-236]] declarar "A11y AAA" enquanto os gates
  medem AA (`withTags` até `wcag21aa`), registrado em
  [A11Y_CHECKLIST §Nível AAA](../../../plan/REPORT_PREMIUM/A11Y_CHECKLIST.md).

### I6. As 6 lanes fora da tabela §Lanes — o §Gate de saída não as vê

**Medido:** `ls docs/sprint/A40/lanes/*.md` dá **44**; a tabela lista **38**.
Ausentes: **l38** (#1391), **l39**, **l40**, **l41**, **l42**, **l44**
(#1397/#1398). O contador foi corrigido no #1405 para declarar os dois números, e as
ausentes ficaram nomeadas por id — isso registra a dívida, **não a paga**: o §Gate de
saída lê esta tabela, e lane fora dela é invisível ao encerramento.

- Não foi feito no #1405 porque a coluna Título é **rótulo editorial** e inventar
  rótulo produz a divergência que a própria convenção da tabela adverte.
- **Nota de processo:** 3 colisões de id numa sessão (l38→l41→l43; e l45 já
  reivindicado pelo #1387, por isso esta é l46). Causa: tabela e disco divergem, então
  "próximo id livre" medido na tabela mente. Meça no **disco** e cruze com títulos **e
  arquivos** de PR aberto — precedente da sprint: l25→l26→l27 em #1167/#1170.

### I7. `renda_passiva.conclusion` imprime "Faltam R$ **-**X/mês" — subtração sem guarda de sinal

`charts_narrator.py:242-244` imprime o percentual da meta e, na frase seguinte,
`fmt_currency(M['if_renda_passiva_meta'] - M['renda_passiva_4pct'])` — subtração
literal, sem `if`. Família que já passou da meta de renda passiva recebe "Faltam
R$ -X/mês", contradizendo o percentual que a mesma frase acabou de imprimir. O
percentual também não é clampado (`generate_narratives.py:592`).

**É entregue** — `S7IndependenciaSection.tsx:87` (`chartId="renda_passiva"`), e o
`NarrativeChartCard` renderiza `context` + `conclusion`.

**Honestidade de medição:** foi medida a **ausência do clamp** e a **entrega**. Não
foi observado um workspace com `renda_passiva_4pct > if_renda_passiva_meta` — o caso é
**plausível, não observado**.

- **Fix:** ramificar em `gap`; `gap > 0` mantém a frase, `gap <= 0` troca por
  excedente. **Medir antes de escrever a copy:** se `renda_passiva_meta` é sempre
  derivada de `if_meta` pela TRS, gap negativo só ocorre quando a meta de IF já foi
  batida — e aí a copy certa é "meta atingida", não "excedente".
- Teste de regressão com os **dois** sinais antes do fix.

### I8. Landmines de veredito sem limiar — reais, mas **não entregues** hoje

Todos confirmados como incondicionais e todos em chave que **nenhuma superfície lê**.
Severidade é de landmine (o próximo agente herda e reacende), não de defeito visível:

| local | veredito fabricado | nota |
|---|---|---|
| `summaries_narrator.py:86-87` (`s2`) | *"Pontos fortes: … e endividamento controlado"* — 3 afirmações incondicionais, incluindo o enquadramento "Pontos fortes:" | O limiar existe (`scoring.json:155`, `endividamento_maximo_pct: 20`) **e** o produtor gated canônico existe e **é entregue**: `pontos_fortes_analyzer.py:137-153` → `"Endividamento Controlado"` no `PontosFortesCard`. O `s2` é um **segundo produtor ungated da mesma palavra** |
| `charts_narrator.py:39-41` (`top15_ativos`) | *"Concentração em poucos ativos…"* nos **dois** ramos | Dead code de narrativa — `Top15AtivosCard` substituiu o chart e recebe só `inv`, nunca `charts` |
| `charts_narrator.py` (`patrimonio_doughnut.context`) | *"mostrando concentração em imóveis"* incondicional — enquanto a `conclusion` **do mesmo chart** consulta o limiar | O gate existe no arquivo; só não é aplicado ao `context` |
| `format_helpers.py:97` | *"Carteira diversificada entre 1 categoria de ativos"* com n=1 | A l43 removeu o **call site entregue**, não o defeito da função. Fica órfã inteira se a [[A40.l15]] decidir que a S3 não afirma nada ⇒ [[A40.l14]] |

**Preferir deleção a reescrita com limiar** onde o produtor gated já existe: dois
produtores da mesma afirmação só podem concordar (redundante) ou discordar (defeito
publicado) — o mesmo argumento que a l4 usou para matar o estimador de DAS do `s8`.
**Depende de C4**: o validador hoje proíbe `s2` vazio.

### I9. Drift de comentário deixado pela própria l43

`format_helpers.py:87` afirma: *"Os três call sites (s3, perfil_familia,
patrimonio_doughnut) passam a compartilhar estas duas frases."* — o call site de
`perfil_familia` **foi removido pela l43**, e o do `s3` está desligado. O comentário
descreve um mundo que não existe mais e custa a próxima pessoa que o ler.

- **Fix:** atualizar o comentário para o estado medido (zero call sites entregues) ou
  deletá-lo junto com a função, se a l15 decidir a remoção. Trivial, mas é
  exatamente a classe "afirmação em prosa envelhece" que a sprint já catalogou.

---

## Feature deferida

### F1. Substrato declarado de plano de vida

Não é débito: é **a feature que o pedido original da l43 queria** e que não pôde ser
feita porque não existe onde a família declarar projeto de vida (`FamilyMember` tem
JSON livre biográfico; `Goal` é numérico; `Decision` é plano de ação financeiro).

Escopo mínimo anti-campo-lixo, do `financial-planner`:

| Campo | Shape | Número que muda |
|---|---|---|
| Evento de liquidez previsto | `{tipo: enum, ano, valor_estimado_brl, confianca: enum}` | trajetória IF, `meta_aporte_mensal`, prazo |
| Mudança de país/cidade | `{pais_destino, ano, custo_transicao_brl}` | alvo de reserva, `goal.dolarizacao`, residência fiscal |
| Novo dependente previsto | `{ano}` | custo essencial projetado, reserva, dependentes IRPF |
| Alteração de renda prevista | `{membro_id, ano, natureza: enum}` | `perfil_renda` ⇒ `meses_alvo`, taxa de poupança projetada |

Critérios travados: **todo campo declarado tem de mudar um número que já existe**
(campo que só alimenta prosa é decoração, e prosa sobre campo livre é superfície de
fabricação); **vocabulário fechado + ano + valor, nunca texto livre**; ausência
silenciosa ([[ADR-356]] §D7); coletado onde o número é editado; **máx. 5 campos**, cada
um com consumidor nomeado antes de existir. **Não coletar horizonte** —
`goal.if.horizonte_anos` já existe.

- **Exige ADR `Proposto`, e o gatilho é PII**, não a forma do narrador: texto livre
  autorado caindo **verbatim** em artefato entregue e no PDF é nova superfície das
  classes que [[ADR-356]] §D9 e [[ADR-319]] removeram deste card. A ADR decide
  contrato de redação/consentimento **e** exclusão explícita de qualquer contexto LLM.
- **Trava histórica:** "mudança de país" declarada é legítima; **modo de relatório**
  por país não é — foi o que a [[ADR-168]] matou. Um campo, não um modo.
- **Depende** de [[A40.l29]] §Escopo 2 ter decidido o par número-projetado/premissa —
  sem isso não há onde pousar sem recriar a duplicação que a l43 removeu.

---

## Já têm dono — apontados para não duplicar

| Achado | Dono |
|---|---|
| `parcela_mensal`/`taxa_juros` sem valor numérico ⇒ produto não pode qualificar dívida por custo | `docs/sprint/A26/tracks/taxa-divida-numerica.md` (`ready`, P2, `data-engineer`) — follow-up de [[ADR-300]]/[[ADR-301]]. **Nuance medida:** a evidência que o painel citou (`analyze_finances.py:1501`) é **dead code** — `analyze_endividamento` não tem call site; as citações da track também estão desatualizadas |
| Branch `block` da red line RL2 inalcançável — o parecer sempre degrada para o proxy de alavancagem em warning | mesma track A26 (§1 descreve a degradação e o limiar 40; §4 pede teste determinístico). Não re-litigar o limiar 1,5% a.m., que é da [[ADR-300]] |
| `custo_medio_pct_aa` sem produtor mata o branch carry-trade de `rule_endividamento_perigoso` | [[ADR-367]] + `docs/reference/rules/rule-ordem-do-plano-por-irreversibilidade.md` — **já documentado**, não é achado novo |
| Contagem de imóveis · política de diversificação · premissas de IF · forma do ramo de prazo ausente | [[A40.l6]] · [[A40.l15]] · [[A40.l29]] (× 2) |

## Fantasmas — medidos e **refutados**, não reabrir

- **`fmt_usd` com negativo** (`fmt_usd(-2500) → 'US$ -2500'`): o defeito existe em
  `format_helpers.py:188` (testa valor com sinal), mas é **dead path** — nenhum call
  site passa negativo. Corrigir de carona se o fix de I2 tocar `fmt_usd`; não abrir item.
- **`R$ 1k`/`R$ 50k`/`R$ 811k` em `protection/*`**: são **docstrings**, não strings
  entregues (`disability_coverage.py:68`, `itcmd_estimator.py:73`,
  `life_insurance_coverage.py:119`). Um `rg` ingênuo por `R\$ [\d.,]+[kM]`
  **sobre-conta 3-4×** o escopo real.
- **"Carteira aderente ao alvo"** — o único veredito de carteira que **é** entregue
  **não** é afirmação fabricada: é derivado da ausência de desvio, com base real.
- **"equilíbrio" nas narrativas do `score_gauge`** — descreve o **instrumento**, não
  os números da família; e é dead code. Não abrir.
- **Resultado negativo da varredura, registrado para ninguém re-varrer:** os termos
  "saudável", "adequado", "confortável", "excelente", "sólida", "robusto" e
  "equilibrado" foram varridos em **todos** os narradores E5.N. Fora do que está em
  I8, não há outra instância incondicional. A varredura foi feita — não repetir.

## Cobertura da medição — o que **não** foi verificado

A verificação rodou 4 lentes das 5 planejadas. A 5ª (**varredura de órfãos deixados
pela remoção** — helpers sem consumidor, métricas de `load_metrics_from_e5` que só o
`right` lia, `right` ainda no `config/schemas/e5_analysis.schema.json`, testes que
passaram a valer vacuamente) **não rodou**: limite de sessão.

Parte dela foi coberta de lado — I8 mapeou os call sites de
`carteira_diversificacao_frase` e I9 achou o comentário órfão. O que **falta medir**:

- métricas que só o `right` consumia e agora ninguém lê (`if_trs_pct`,
  `if_renda_passiva_meta`, `progresso_if`, `patrimonio_investivel`,
  `anos_para_if_calculo`, `idade_titular_if`, a chave de salário do cônjuge…);
- se manter `right` declarada no schema é tolerância intencional ou schema
  descrevendo mundo inexistente (há precedente no repo?);
- testes do E5.N que ficaram trivialmente verdadeiros.

**Não presumir que "não achou" significa "não existe"** — essa lente não rodou.

## Critério de aceite da lane

Lane de **registro + execução opcional**. O aceite mínimo é que nenhum item evapore:

- Cada item tem **medição citada + fix mínimo + caminho de re-medição** — não
  descrição solta (a convenção do §Inventário).
- Item executado sai para o histórico com sha de merge; item não executado ao fim da
  sprint recebe disposição escrita (`§Fora do sprint` ou lane da sprint seguinte),
  **nunca** deleção silenciosa.
- **C1, C2, C3 e I1 têm prova por mutação** quando executados: reverter o fix deixa
  vermelho. C1 exige `financial-planner` antes do PR (muda score).
- I4 exige **baseline olhada** — o bloco nunca esteve em imagem nenhuma.

## Fora de escopo

- O que a [[A40.l43]] entregou em `849e372b`: remoção de `perfil_familia.right`,
  transferência da declaração de ausência para a S7, `today` de `data_analise`, gates
  de classe do perfil.
- Tudo na tabela §Já têm dono — repetir aqui criaria segunda fonte de verdade.
