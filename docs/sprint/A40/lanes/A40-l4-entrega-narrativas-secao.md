---
id: A40.l4
type: lane
title: "Entrega de narrativas de seção + re-triagem dos 7 achados que passam a aparecer"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1139
ship_date: "2026-07-31"
priority: P0
branch_slug: a40-l4-entrega-narrativas-secao
adrs:
  - "[[ADR-356]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/frontend
  - area/pipeline
---

# A40.l4 — `entrega-narrativas-secao` (RV3-03 + RV3-33)

> ⚠️ **Esta lane destrava conteúdo latente.** Fechá-la sem o checklist da
> §Critério de aceite publica 7 defeitos conhecidos de uma vez, por um PR correto.

## Problema

`SectionSummary.tsx:23` lê `narrativas[<ID maiúsculo>]`; o builder E5.N emite
`narrativas.summaries.<id minúsculo>` **como string**, onde o componente espera
objeto. Incompatibilidade **dupla** — chave *e* shape. Resultado: os parágrafos de
abertura do E5.N não renderizam em nenhuma seção.

**Precisão pedida pelo painel:** não são duas fontes desalinhadas, são **três**
competindo pelo mesmo parágrafo sem precedência declarada — (a)
`narrativas.summaries.s1..s10` (E5.N, string, nunca lido); (b)
`data.section_summaries["S1"]` (LLM, opt-in, default OFF); (c) derivação no
cliente. Seções que chamam `deriveSectionSummary` **renderizam** um sumário
derivado; o que está morto em 100% dos casos é especificamente **o texto do E5.N**.
Isso muda o fix de "trocar o path" para **"declarar precedência"**.

O gate CV9 "Narrativas completeness" passa verde porque mede **geração**, não
entrega — instância do padrão transversal (§Decisões nº 4 do sprint).

## Escopo

- Declarar precedência explícita em `SectionSummary`:
  `section_summaries[<ID>]` → `narrativas.summaries[<id>]` → `deriveSectionSummary`.
- Normalizar o shape (string vs objeto) no boundary, não no componente.
- Padronizar os call-sites de conclusão de chart em `narrativas.charts`.
- **Redefinir CV9** em `scripts/validate_cross.py` para medir entrega.
- **Corrigir o que a entrega passa a publicar** — nenhum defeito conhecido vai ao
  relatório: PII fora do texto (ADR-356 §D9), zero número de default de código
  (§D7-D8), zero afirmação duplicada com o empty state (§D7).

### O que a lane ENTREGA e o que ela DESLIGA

A lane entrega o **mecanismo** de precedência e **as narrativas verificadas
corretas**. Nenhuma dessas 10 narrativas havia sido validada contra a seção que
abre — foram escritas quando ninguém as lia. Validar uma a uma é lane própria; o
princípio (co-design `financial-planner`) é **ou o número é confiável, ou não é
afirmado**.

| Destino | Estado | Razão |
| --- | --- | --- |
| `s1` → S1 | **entrega** | conferido contra os cards da própria seção no render single-source: 82,2% imóveis vs "82% do patrimônio bruto (R$ 600.000)" no card de composição |
| `s3` → S3 | **entrega, com residual aberto** | ver §Residual — a contagem de "categorias de ativos" vem de `patrimonio.composicao` e a tabela da S3 vem de `investimentos.tabela_classes`; medido 3 vs 2 |
| `s4` → S4 | **entrega sem contagem** | a quantidade de imóveis foi removida do texto (ADR-356 §D7); o que resta (valores de `patrimonio`) confere com o card |
| `s7` → S7 | **entrega** | 4% SWR, gap, prazo e ano conferem com os três cards da seção |
| `s8` → S8 | **entrega parcial — DAS desligado** | o texto afirma só regime declarado + contador + holding. Estimativa de DAS/alíquota **removida** (§D7) e DAS **recolhido** também: o balde `das_simples` é 100% falso-positivo até o PR #1133 |
| `s9` → S9 | **entrega, suprimida em empty state** | com riscos cadastrados o texto confere com a tabela de cobertura; sem riscos o parágrafo não é impresso (o `<EmptyState/>` é a mensagem) e o CV9 conta 6/7 |
| `s10` → S10 | **entrega** | as 4 decisões e o aporte conferem com o card `top5_decisoes` |
| `s2`, `s5`, `s6` | **não entregues (órfãs)** | sem seção de destino, com razão em `ORPHAN_SUMMARY_KEYS` |
| `S_IRPF_RENDA`, `S_IRPF_OTIMIZACAO` | **render site deletado** | as três camadas são vazias para essas seções — flag prometia parágrafo que nenhum produtor podia produzir (ADR-356 §D11) |
| conclusão de chart de S1/S2 via `narrativas.charts` | **deferida** | A40.l15 — o ranking do donut é hardcoded e o texto não tem a cláusula de janela da A40.l3 |

## Critério de aceite

- **KR-C: os 7 destinos declarados no layout entregam o texto do E5.N na página
  real (7/7).** O critério anterior — "nº de seções que renderizam parágrafo ==
  nº com narrativa emitida" — é **aritmeticamente impossível** e foi descartado:
  medido, 12 seções renderizam parágrafo de abertura e o produtor emite 10 chaves
  `s1..s10`; 12 ≠ 10 por construção, porque 5 dos parágrafos são **derivados**
  (camada 3, sem chave no E5.N) e 3 chaves emitidas são **órfãs** (`s2`, `s5`,
  `s6`, sem seção — ver `ORPHAN_SUMMARY_KEYS`). Igualar os dois números exigiria
  ou apagar parágrafo derivado que funciona, ou inventar seção para chave órfã.
  O número que mede entrega é o **par destino→chave**, e ele fecha.
- Par de testes sobre **fixture único compartilhado** (TS + Python) com o shape
  real do builder e um texto sentinela por seção: o lado TS assere o sentinela no
  DOM; o lado Python assere que o builder emite naquele shape. Divergência futura
  quebra os dois.
- **Prova do gate:** emitir a narrativa sob a chave antiga tem de deixar o teste
  **vermelho**.
- **CHECKLIST BLOQUEANTE — re-triagem dos 7 inertes (RV3-33).** A lane só pode ser
  marcada `done` com os 7 re-verificados **contra o output já renderizando**, cada
  um com veredito registrado (`ainda-inerte` / `agora-visível-e-correto` /
  `agora-visível-e-errado`). **A re-triagem rodou duas vezes e bloqueou nas duas.**
  A 1ª achou C29 e C32 `agora-visível-e-errado` (PD-20 também). A 2ª, pós-remediação,
  achou C32 resolvido e provado por mutação e **C29 ainda errado** — o DAS
  "recolhido" que entrou no lugar da estimativa também era falso —, mais **duas
  contradições novas**: o `s4` afirmando 6 imóveis com a seção listando 4, e o CV9
  contando 7 de 7 quando o render entrega 6. A **3ª passada, depois da remediação
  final, não rodou** (limite de gasto da org). Vereditos em §Checklist são os da
  remediação final; o que está aberto é a verificação **dessa última rodada de
  correções**, não a re-triagem inteira.
- Teste anti-hardcode **por parâmetro citado**, não por summary: para cada
  parâmetro citável, o trecho que o cita tem de conter o token do valor — com dois
  valores diferentes. A granularidade por summary (a primeira versão) fica VERDE
  quando se congela um literal entre outros parâmetros que ainda variam; medido:
  congelar `if_meta` em `summaries_narrator` deixa o assert coarse `a != b`
  **verde** e o caso por-parâmetro **vermelho**.
- Snapshot do view-model: **não rebaselinar**. Nenhum campo novo entra no
  view-model, então o sinal é `test_report_view_model_snapshot.py` passar verde
  **sem** `MATHOMS_UPDATE_SNAPSHOT=1`. Medido: 4 passed.
- **Declarar o sinal esperado do delta** (decisão nº 5 do painel): esta lane não
  recalcula número, então o sinal é `=` para todo campo monetário — qualquer
  divergência em `dev/golden_diff.py` no rebaseline é achado, não ruído de
  snapshot. Se um valor mover, pare: a narrativa está sendo gerada a partir de
  caminho diferente do que o card lê.

## Fechamento (2026-07-31 · #1139 `6c5d9814`)

**Entrega com gate por narrativa, não liga-tudo.** `s1`, `s7`, `s10` entregam
(conferidos contra os cards da própria seção). `s4` entrega **sem contagem**
(`n_imoveis_total`=6 vs `real_estate.imoveis`=4 na mesma seção). `s8` entrega
**sem afirmar DAS** (o balde `das_simples` era 100% falso-positivo até o #1133,
mergeado). `s9` segue gerado e o CV9 passa a saber que foi suprimido por empty
state. `s2`, `s5`, `s6` são órfãs declaradas.

**O `s3` foi desligado depois, em #1144** — afirmava diversificação contando
`patrimonio.composicao` (baldes patrimoniais, um por membro) enquanto a tabela da
S3 conta `investimentos.tabela_classes`: 3 vs 2. Conceito errado, não número
errado; a decisão do que a abertura da S3 afirma sobre a carteira está na
[[A40.l15]].

**Critério de aceite parcialmente cumprido — a re-triagem bloqueante rodou duas
vezes e bloqueou nas duas; a 3ª passada não rodou.** Cronologia:

1. **1ª passada** — C29 e C32 viraram `agora-visível-e-errado` (PD-20 também).
   Bloqueou; remediação aplicada.
2. **2ª passada, pós-remediação** — C32 resolvido e **provado por mutação**. C29
   **ainda errado**: o DAS *recolhido* que entrou no lugar da estimativa também era
   falso. Mais **duas contradições novas**: o `s4` afirmando 6 imóveis com a seção
   listando 4, e o CV9 contando 7 de 7 quando o render entrega 6. Bloqueou de novo;
   remediação final aplicada (DAS em silêncio, `s4` sem contagem, CV9 com
   `summary_suppressed_by`).
3. **3ª passada, depois da remediação final — não rodou.** Morreu no limite de gasto
   da org, junto com as duas lentes adversariais. A lane mergeou assim por decisão
   do dono.
   **Disposição (2026-08-05, decisão do dono, §Pendência nº 4 do [[A40]]):**
   critério **não-cumprido**, **subsumido pelo §Gate de saída e encerramento** da
   sprint — o §Checklist bloqueante desta lane entra como **insumo declarado** da
   revisão do dono no 1º dos 2 re-runs. Sem work-item novo (cláusula 2 do
   §Critério de admissão da [[A42]]): os alvos nomeados já são itens adotados em
   [[A40.l6]], [[A40.l12]] e [[A40.l11]]. A lane **não** volta a `open`: `shipped`
   é fato de merge, e a dívida agora tem host com gatilho.

O que **está aberto** é a verificação da **última rodada de correções**, não a
re-triagem inteira. O que foi verificado: suítes (5544 pytest · 1464 vitest · tsc 0),
as 106 asserções das guardas novas, e a medição do KR-C com dois servidores e o mesmo
payload (7 → 12 seções). O que **não** foi verificado: se os três fixes da remediação
final se sustentam no output renderizado, e se algum texto entregue contradiz a
própria seção além dos casos já desligados.

**Defeitos de produção que a lane removeu, medidos:** PII (nome completo de
adultos e de menor no card de perfil) · alíquota efetiva de 6% vinda de constante
legada que se desmentia no próprio comentário, ~2× subestimada na direção que
infla sobra · `or 5` publicando "5 categorias" quando são zero.

## Guarda anti-regressão

Cinco pernas independentes — é a independência que remove a auto-referência.
Cada uma foi provada por mutação (aplicada, vermelha, restaurada):

1. **Par sobre fixture compartilhada** (forma) — `tests/fixtures/narrativas/e5n_delivery.json`,
   gerada pelo produtor **na condição de produção** (sem
   `parametros_fiscais.json`) e sobre substrato com **valores não-triviais**
   (`run_dogfood_pipeline_ctx`: E1.5c→E3→E4→E5, fixture sintética PII-zero da
   A23.l2), lida por `tests/test_e5n_delivery_contract.py` e por
   `frontend/tests/components/report/sectionSummaryDelivery.test.tsx`. O substrato
   anterior era o E3 mínimo de 1 transação de R$ 100 e a fixture nascia
   financeiramente vazia — sentinela de forma, não de conteúdo. Teste próprio
   exige ≥6 valores monetários distintos e não-zero nos destinos entregues.
2. **Destino semântico** — `tests/fixtures/narrativas/e5n_destinations.json`: o
   mapa esperado seção → chave, declarado **fora** do layout, com a razão
   semântica por entrada. Sem ele as pernas liam o destino do layout e o aferiam
   contra o layout: declarar `summary_source: "s2"` na S2 passava 30/30. Medido:
   com ele, a mesma mutação deixa duas asserções vermelhas (mapa e conteúdo).
3. **Anti-hardcode por parâmetro** (conteúdo) — `tests/test_e5n_anti_hardcode.py`
   (braços A, B, C, D) + `tests/test_e5n_param_classification.py` (braço A2),
   sobre o substrato compartilhado `tests/narrativas_synthetic.py`; nenhum teste de
   forma detecta narrativa citando parâmetro congelado. A tabela de parâmetros
   citáveis era **curada à mão** (22 linhas) e nada forçava entrada nova: o braço
   A2 **deriva do fonte do builder** o universo de parâmetros de `goals.json`
   (24 folhas) e exige que cada um esteja classificado — linha citável, `gate` ou
   `sem_efeito` —, com a classificação **verificada contra o comportamento**
   (perturbar um `gate` tem de mudar algum summary; perturbar um `sem_efeito`,
   nenhum). O split em três arquivos é do gate de estilo: o módulo único passou de
   500 linhas.
4. **PII no output** — `tests/test_e5n_pii_guard.py`, 3 braços (sentinela por
   campo, forma de nome completo, regra estática de leitura), endurecidos no
   fechamento: a varredura passa a ser do **artefato inteiro** (recursiva) em vez
   de um blob enumerado à mão; `nome_nascimento` entra na lista e na
   família-sentinela; a forma de nome completo passa a tolerar `nome_curto` de 2+
   palavras (substituto sancionado, subtraído dinamicamente) e a allowlist de
   termos de domínio ganha os labels de classe de ativo, com a fixture emitindo o
   chart que os produz — antes a allowlist era declarada no vácuo.
5. **Regras estáticas** (estrutura) — regras 5, 6 e 7 de
   `dev/check_chart_conclusion_parity.py`: bag `narrativas` só via `.charts`;
   `summary: true` ⟺ `<SectionSummary sectionId="…">`; e `<SectionSummary>` sob
   condição ⟺ `summary_suppressed_by` declarado no layout.

CV9 (`entregues=N/esperadas=M`) é a **sexta** perna e telemetria de run, não gate
de PR — só roda no stage `validate_cross`. Os cinco buckets têm unit test próprio
(`tests/test_cv9_narrativas_delivery.py`): os quatro de falha (incluindo o
gerado-e-não-entregue estático) e o de supressão condicional, este provado
**sobre o layout versionado** — payload sem risco cadastrado devolve
`entregues=6/esperadas=7` com `suprimido=['S9->s9']`, onde a 1ª versão dizia 7/7.

## Medição — KR-C (página real, dois servidores, um payload)

Procedimento (reproduzível, medido no fechamento da lane):

1. dois servidores Next simultâneos — `:3000` do **checkout principal** parado em
   `5fa70296` com árvore limpa (= base desta lane) e `:3011` do worktree;
2. **um** spec Playwright/chromium roda contra os dois: intercepta `**/data` e
   injeta o **mesmo payload** dos dois lados;
3. payload = fixture E2E `large-values.json` (dá corpo aos cards) + bag
   `narrativas` de `tests/fixtures/narrativas/e5n_delivery.json` + bloco
   `real_estate` (a S4 é hide-when-empty; sem ele não monta);
4. detector = o primeiro filho do grid do `ReportSection` é `<p>` (registro
   derivado) ou `<div>` com `border-l-4` (registro E5.N/LLM).

| | antes (`5fa70296`) | depois |
| --- | --- | --- |
| seções que renderizam parágrafo de abertura | **7** | **12** |
| dessas, em registro de caixa (E5.N/LLM) | **0** | **7** |
| destinos declarados que entregam o texto do E5.N | **0 / 7** | **7 / 7** |

As 7 de antes: S8, S9, S10, APP_A, APP_B, APP_D, APP_E — nenhuma exibindo texto
do E5.N (todas no derivado). As **+5** são S1, S2, S3, S4, S7 (a S2 pelo
derivado, `summary_source: null`; as outras 4 pelo E5.N).

**Denominador é o que a página monta, não o que o layout declara:** 14 das 17
entradas `enabled` montam com este payload. `S_IRPF_RENDA`/`S_IRPF_OTIMIZACAO`
exigem `irpf_kpis` e a `APP_C` não monta com esta fixture; `S_PROTECAO` é
`enabled: false`.

**A tabela anterior ("8 → 13", com a APP_C entre as 8) vem de outro
procedimento** — render de cada entrada **isolada** pelo dispatcher em vitest,
onde uma seção monta mesmo sem o dado que a página exige. Números de dois
procedimentos não se comparam, e o que o usuário vê é a página; a medição por
dispatcher foi descartada. É a 6ª ocorrência desta sprint de contagem que não
sobrevive a nova medição — daqui em diante a tabela só aceita número com
procedimento descrito **e** servidor identificado por commit.

> **Armadilha medida no caminho:** o `webServer` do `playwright.config.ts` tem
> `reuseExistingServer: !CI` e a porta 3000 já estava ocupada por um `next dev` do
> **checkout principal**. A primeira rodada mediu o worktree contra código de
> outro checkout e devolveu exatamente o padrão do "antes". `PLAYWRIGHT_WEB_SERVER_COMMAND`
> não existe na config — passar essa env não muda servidor nenhum. Verificação
> renderizada exige `PLAYWRIGHT_SKIP_WEB_SERVER=1` + porta própria + confirmar o
> commit de quem serve.

## Checklist bloqueante — re-triagem dos 7 inertes (RV3-33)

Códigos de **cluster** (não RV3-xx), de `SINTESE.md` §placar cético do run
`2026-07-29-573a54a7`. Verificados contra o output com a entrega ligada.

**A re-triagem rodou duas vezes e bloqueou nas duas.** 1ª: C29 e C32
`agora-visível-e-errado` (PD-20 também) — ver ADR-356 §D7-D9. 2ª, pós-remediação:
C32 resolvido e provado por mutação, **C29 ainda errado** (o DAS *recolhido* que
substituiu a estimativa também era falso), mais duas contradições novas — `s4`
afirmando 6 imóveis contra 4 na seção, e CV9 contando 7 de 7 com o render
entregando 6. A **3ª passada, pós-remediação final, não rodou** (limite de gasto da
org). Os vereditos abaixo são os da **remediação final** e não passaram por
verificação renderizada.

| # | Cluster | Veredito | Motivo |
| --- | --- | --- | --- |
| 1 | **C11** — runway canônico (ADR-335) calculado e nunca renderizado; alias colide de nome com cobertura da reserva | `ainda-inerte` | Medido: `ratios.autonomia_financeira_meses` = 16,72 no payload, sem consumidor. É campo do view-model, não de narrativa. Dos 7 destinos entregues nenhum cita runway — o `s2`, que cita `cobertura_meses`, é órfão (`summary_source: null` na S2). A l4 não muda a superfície. Dono: A40.l5. |
| 2 | **C18** — narrativa do donut de despesas publica ranking com 4 categorias fixas e ordem falsa | `ainda-inerte` | A l4 **não** aponta os charts de S1/S2 para `narrativas.charts` (ADR-356 §Deferimentos): o texto com o ranking hardcoded continua sem leitor, e o usuário segue protegido pelo `deriveChartConclusion` do TS, que ordena de verdade. Medido no texto real: ele cita **só o topo**, então o defeito das "4 categorias fixas" não se materializa como "14ª aparece como 3ª" — materializa-se como *ordem inventada quando há empate/valores próximos*. Dono: A40.l15. |
| 3 | **C29** — narrativa fiscal publica DAS estimado e alíquota efetiva que nenhum campo do payload sustenta | `agora-visível-e-errado → CORRIGIDO (silêncio)` | O bloqueante de acender o `s8`. Três defeitos medidos (constante 6% fora de faixa, base = entrada na conta PF, ramo "sem regime + DAS" impossível) + o fallback declarado na §D7 original ser **inalcançável em produção**. Fix: a estimativa sai inteira e o `s8` afirma **só o regime declarado** + contador + holding. A substituição planejada (DAS **recolhido**, balde E4 `das_simples`) **também saiu**: o balde media 100% de falso-positivo enquanto o matcher casava a preposição "DAS". O fix é o PR **#1133**, **mergeado em `69a2fad4`** (2026-07-31 17:06, uma hora antes desta lane) — `_DAS_KEYWORDS` hoje tem **6 keywords unívocas** (`SIMPLES NAC`, `DAS SIMPLES`, `DAS-SIMPLES`, `DAS MEI`, `DAS-MEI`, `DASMEI`). Nem estimado nem recolhido: o `s8` shipou em silêncio porque o sinal do balde não foi re-medido pós-`69a2fad4` — reintroduzir é lane própria. ADR-356 §D7. |
| 4 | **C30** — `dev/explain_number.py` devolve números de fixture sintética sem marcar | `ainda-inerte` | Ferramenta de dev, fora do caminho de render. A l4 não a toca. |
| 5 | **C32** — narrativa determinística publica nome completo de adultos e de menor | `agora-visível-e-errado → CORRIGIDO` | A classificação "inerte" da SINTESE estava errada: `perfil_familia` renderiza hoje, independente desta lane. Mas a l4 **acendeu duas superfícies novas de PII** (`s4` citava `endereco.rua`; `s8` citava `contador_nome`), então não havia como fechar a lane sem tratar. Fix: primeiro nome para adultos, papel para o menor e para o contador, nada para endereço; guarda em 3 braços. ADR-356 §D9. |
| 6 | **C36** — blocos que não movem decisão competem com o sinal (orçamento 44m, premissas 10/10 indisponíveis, checklist de sucessão todo negativo) | `ainda-inerte` | São cards, não narrativa. Medido: a S9 curto-circuita em `<EmptyState/>` quando `bubble_riscos.data_state == "empty"` — e a l4 passou a **suprimir o `s9`** nesse ramo (o EmptyState já é a mensagem). O `s9` continua sendo **gerado** (`validate_narrativas` hard-falha em summary vazio); quem passa a saber que ele não foi entregue é o CV9, via `summary_suppressed_by` no layout — `entregues=6/esperadas=7` nesse run, sem reprovar. Não bloqueia a lane. |
| 7 | **PD-20** — `goals?.trs_pct ?? 5.0` em `S7IndependenciaSection.tsx` (chave real é `goals.if_trs`) | `agora-visível-e-errado → CORRIGIDO (parcial)` | Não é "contradição 4 vs 5": sob ADR-191 §Emenda FP-03 o SWR 4% (que o `s7` cita, corretamente) e o yield-alvo 5% são conceitos distintos que **não se harmonizam** — "consertar" na direção de um número só desfaz FP-03 e encurta a meta de IF ~20%. O defeito era chave fantasma + rótulo: o card lê `ratios.rentabilidade.meta_pct`, imprime "Yield-alvo" (não "Meta") e não imprime nada quando o payload não traz. Residual: a meta ainda não é da família (ver §Residual). ADR-356 §D8. |

## Residual medido (não bloqueou, fica declarado)

| Item | Veredito medido | Dono |
| --- | --- | --- |
| **`s3` contradiz a tabela da própria S3** — "Carteira diversificada entre **3** categorias de ativos" enquanto o `top15_ativos`/`tabela_classes` da mesma seção lista **2** classes | Medido no render single-source (payload de um run real, cards e parágrafo da MESMA fonte): `diversificacao` conta entradas não-zero de `patrimonio.composicao` (`Imóveis de Renda`, `Investimentos Alex`, `Caixa e Moeda Estrangeira` — buckets patrimoniais, um deles **por membro**), e a tabela da S3 lê `investimentos.tabela_classes` (`Imóveis Investimento`, `Renda Fixa`). Mesma classe do `s4`: contagem de fonte que não é a da seção, e rótulo ("categorias de ativos") que não descreve o que foi contado. Fix candidato de 1 linha: `summary_source: null` na S3 — mas mudar destino é **decisão de produto** sob ADR-356 §D2 (gatilho `financial-planner`), não de quem fecha a lane | lane própria (gate `financial-planner`) |
| **`s1` publica `residência própria de R$ 0,00`** | Medido no mesmo render. Mesma classe do "R$ 0,00 em campo fiscal" da §D7 (lê-se como "sua casa não vale nada"); no `s4` a parcela zerada foi suprimida nesta lane, no `s1` não — o `s1` não estava na lista fechada | A40.l5 |
| **`perfil_familia.right` publica `n_imoveis`** — a mesma contagem que o `s4` deixou de afirmar | Medido: o card de perfil renderiza hoje (independe desta lane) e imprime `{n_imoveis} imóvel/imóveis`. É contradição **cross-seção** com a tabela da S4, não intra-seção; pré-existente e fora da lista fechada | **[[A40.l6]]** — item adotado 2026-08-05 |
| **DAS no `s8` ficou em silêncio** — e `despesas_impostos` segue sem o balde | Medido: `_DAS_KEYWORDS = ("DAS",)` casava a preposição e o balde `das_simples` deu 100% de falso-positivo (pedágio, supermercado) no dogfood. O PR **#1133 mergeou em `69a2fad4`** (2026-07-31 17:06) e `_DAS_KEYWORDS` hoje tem **6 keywords unívocas**; a lane mergeou às 18:09 sem re-medir o balde com o matcher novo. A l4 não afirma DAS (estimado ou recolhido) e não soma `das_simples` em `despesas_impostos` — trocar "balde ausente" por "consumo publicado como imposto" é regressão. Reintroduzir as duas coisas exige **re-medir o sinal do balde pós-`69a2fad4`** | **[[A40.l12]]** — item adotado 2026-08-05 |
| **Sufixo de changelog (ADR-148) não renderiza em seção nenhuma** | Medido: `get_report_data.py:78` usa `SnapshotChangelogConfig()` default, cujo `sections_to_compare` é `M_PL`/`M_TAXA_POUPANCA`/`M_RESERVA_MESES`/`M_AUVP_DESVIO` — nenhum é id de seção do layout, e o casamento é por `section_id`. A composição decidida na §D10 é contrato, não preservação de comportamento visível | **fora da A40** — [[PLAN-snapshot-changelog-v3]] §Residual W3 (é resíduo daquele plano; o ponteiro "A40.l5" nunca aterrissou no §Escopo da l5 — corrigido em 2026-08-05, ver `_README` §Fora do sprint) |
| **C11** — `ratios.autonomia_financeira_meses` = 16,72 calculado e sem consumidor | Confirmado. Campo do view-model, não de narrativa; nenhum dos 7 destinos o cita. | A40.l5 |
| **C18** — ranking do donut | O texto real cita só o topo; a instância "14ª maior como 3ª" **não se materializa**. O defeito é ordem inventada em valores próximos, e o texto segue sem leitor. | A40.l15 |
| **C30** — `dev/explain_number.py` devolve fixture sintética | Confirmado, fora do caminho de render. | — |
| **C36** — blocos que não movem decisão | Confirmado como cards; a parte narrativa (duplicação no empty state da S9) foi corrigida aqui. | A40.l5 |
| **PD-20** — a meta de TRS não é configurável | `RatiosCalculator()` roda com `RentabilidadeConfig()` default (5,0) e `PassiveIncomeConfig.trs_meta_pct` (construído do goal) **nunca é lido** pelo calculator. O wizard coleta `trs_pct` 0-20 e o relatório ignora. Ler `meta_pct` resolve a contradição intra-seção, **não** "a meta é da família" — isso é mudança de cálculo. | **[[A40.l12]]** — item adotado 2026-08-05, com bound explícito de faixa |
| **Base da cascata** — `receita_bruta = receita_pj_anual` herda o erro de categoria do CTO-05 no ramo de regime declarado; a fonte correta (`FinanceiroPJSnapshot.receita_bruta_total_anual`, ADR-238) é passthrough e não usada | Confirmado por leitura do `tributario_input_builder`. Mudança de cálculo ⇒ ADR + lane. | **fora da A40** — dono do arquivo é a [[A40.l9]] (`shipped`); materialidade não medida. Disposição em [[REPORT-REVIEWS-active]] (residual pós-r3, 2026-08-05): medição de entrada decide lane nova (com emenda ADR-236/238) ou `aceito-wontfix` |
| **`renda_passiva_estimada_4pct`** cristaliza "4" no nome enquanto a taxa é configurável | O texto entregue é honesto (imprime a taxa real); a liability é o nome da chave no view-model. | A40.l5 |
| **`FORMULAS.md:94`** documenta `goals.trs_pct` como local do yield-alvo — chave que o payload não tem | Corrigido nesta lane (aponta `ratios.rentabilidade.meta_pct` + `goals.if_trs`), senão o próximo agente reimplementa o mesmo bug. | — |
| **Fixture compartilhada roda sobre E3 mínimo** (monetários zerados) | É contrato de **forma e string exata**, não amostra de conteúdo. A revisão de conteúdo é o anti-hardcode, que semeia valores. | — |

## Delta esperado

- **Monetário: `=`.** Nada da lane escreve campo do view-model. O sinal é
  `backend/tests/test_report_view_model_snapshot.py` passar **verde sem
  rebaseline** — o golden tem 31 chaves e não contém `narrativas` (o substrato
  roda `E1.5c→E3→E4→E5` e nunca chama E5.N). Rodar com `MATHOMS_UPDATE_SNAPSHOT=1`
  aqui só poderia mascarar regressão.
- **Visual — medido na fixture `medium`** (a que o spec de snapshots usa), mesmo
  procedimento de dois servidores da §Medição: seções com parágrafo de abertura
  **7 → 11**. As **+4** são `S1`, `S2`, `S3`, `S7`, todas no registro **derivado**
  (`<p>`, markup idêntico aos blocos de fallback substituídos) — o bag
  `narrativas` das 5 fixtures só tem `perfil_familia`, então a camada 2 não
  dispara e **nenhuma seção muda de registro** nelas. Logo o rebaseline é
  4 seções × {light, dark} = **8 PNGs**. `S4` não monta (`real_estate: null` em
  `medium`) e `APP_C` não monta com essa fixture — nada a rebaselinar nelas.
  O card de TRS da `S7` troca "Meta 5,0%" por "Yield-alvo …" **ou nada** — nas
  fixtures sem `ratios.rentabilidade`, nada.
  Rebaseline **tem de rodar em CI Linux** — o próprio spec
  (`sections.snapshots.visual.spec.ts:22`) proíbe atualizar em macOS.

  > A versão anterior deste bullet dizia que "nessas fixtures o delta é S2
  > ganhando o `<p>` derivado e as demais mantendo o markup" — **medido falso**:
  > S1, S3 e S7 também passam de nada para `<p>`. O número de PNGs (8) estava
  > certo por acidente; a lista de seções, errada.
