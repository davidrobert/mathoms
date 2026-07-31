---
id: ADR-355
type: adr
title: "Precedência declarada do parágrafo de seção e CV9 como medida de entrega"
status: Proposto
phase: report-review r3 (RV3-03 · RV3-33) · A40.l4
date: "2026-07-31"
relates_to:
  - "[[ADR-144]]"
  - "[[ADR-122]]"
  - "[[ADR-076]]"
  - "[[ADR-168]]"
  - "[[ADR-192]]"
  - "[[ADR-216]]"
  - "[[ADR-236]]"
tags:
  - type/adr
  - status/proposto
  - area/frontend
  - area/pipeline
size_lines: 658
---

# ADR-355 — Precedência declarada do parágrafo de seção e CV9 como medida de entrega

## Tamanho — por que não é split

Esta nota tem **658 linhas de corpo** (`size_lines`, medido), muito acima das 150
que o CLAUDE.md marca como limite — as vizinhas ADR-350 a ADR-354 têm 99-125. A
justificativa exigida:

**as 11 decisões não são separáveis, são uma só mudança em 11 lugares.** Acender a
entrega do parágrafo de seção só é seguro se, no mesmo ato, o mapa de destino for
declarado (D2), o registro visual for escolhido (D3), as guardas em ramo morto
saírem (D4), o gate de medição parar de mentir (D6) e **cada número que o texto
passa a publicar** for confiável (D7-D9). Dividir produziria ADRs que decidem
sobre código morto — exatamente o anti-padrão que a §Contexto documenta: as 5
cópias do fallback e o CV9 verde por construção existiam porque cada peça foi
decidida sozinha. Um split honesto seria por *superfície* (renderer / produtor /
gate), e as três compartilham a mesma pergunta ("de onde vem esse parágrafo, e o
número dele é confiável?").

O que **foi** separado: a fonte plugável do yield-alvo, a base da cascata, o
ranking do donut e o nome de `renda_passiva_estimada_4pct` viraram §Deferimentos
datados com dono, em vez de decisão aqui.

## Contexto

Três produtores disputam o **mesmo** parágrafo de abertura de seção, sem
precedência declarada em lugar nenhum:

| # | Fonte | Shape | Estado medido |
| --- | --- | --- | --- |
| a | `narrativas.summaries.s1..s10` (E5.N) | `str` | **nunca lida** |
| b | `data.section_summaries["S1"]` (LLM, [[ADR-144]] §3) | `dict[str,str]` | opt-in, flag OFF desde 2026-04 |
| c | `deriveSectionSummary(sectionId, data)` (determinístico) | `str` | renderiza |

`SectionSummary.tsx:23` lia `narrativas[<ID maiúsculo>]` esperando
`{context, conclusion}` — **chave e shape que nenhum produtor emite**. O E5.N
emite `summaries.sN` como string; o LLM emite `dict[str,str]`; o derivador
devolve string. O que estava morto em 100% dos casos era especificamente o texto
do E5.N: as seções que chamavam `deriveSectionSummary` renderizavam parágrafo
derivado, o que fazia o defeito parecer ausente.

Medição na **página real** (servidor no commit-base `5fa70296`, payload injetado
via `**/data`; procedimento completo em §Consequências): **7 seções com parágrafo
de abertura, 0 de 7 destinos do E5.N entregues**. As 7 são S8, S9, S10, APP_A,
APP_B, APP_D e APP_E — nenhuma exibindo texto do E5.N (todas caíam no derivado).
Versões anteriores desta §Contexto disseram "7" e depois "8" contando **call
sites** de `deriveSectionSummary` e render **isolado pelo dispatcher**, que monta
seção sem o dado que a página exige (a `APP_C` entrava assim). Call site não é
parágrafo entregue, e dispatcher não é página.

Cinco cópias do fallback determinístico viviam **fora** do componente, cada uma
guardada por `!narrativas?.["<ID>"]` — guardas em ramo morto, que nunca podiam
disparar. A S4 tinha uma sexta: o gate de visibilidade
`if (!realEstate && !hasS4Narrativa) return null`.

O CV9 (`Narrativas completeness`) media **geração**, não entrega — e era
**redundante**: `validate_narrativas` (`format_helpers.py:187-195`) já hard-falha
o próprio E5.N quando qualquer `s1..s10` falta ou vem vazia. "Presença +
não-vazio" era garantido a montante, então o CV9 era verde por construção.

## Decisão

### D1 — Precedência canônica em quatro camadas, uma função pura

`resolveSectionSummary(sectionId, data)` em
`frontend/src/components/report/utils/sectionSummarySource.ts`:

1. `data.section_summaries[<ID>]` — LLM ([[ADR-144]] §3).
2. `data.narrativas.summaries[LAYOUT_SUMMARY_SOURCE[<ID>]]` — E5.N.
3. `deriveSectionSummary(sectionId, data)` — determinístico + changelog.
4. `null` → não renderiza nada.

Isto **insere a camada 2** na precedência de [[ADR-144]] §3, que declarava só
LLM → determinístico.

**Fail-soft em todas as camadas** ([[ADR-144]] §3, "o relatório nunca falha por
causa de LLM"): fonte ausente, string vazia/só-whitespace, ou shape inesperado
(`typeof !== "string"`) contam como ausentes e caem para a próxima — sem log e
sem throw. Consequências desejadas: LLM que devolve vazio não apaga o texto do
E5.N; objeto sob `summaries.sN` nunca imprime `[object Object]`.

A chave da camada 2 **não** é `sectionId.toLowerCase()`. Ver D2.

### D2 — `summary_source` no layout: mapa declarado, não derivado

`config/report_layout.yaml` ([[ADR-076]], codegen para TS + Pydantic) ganha
`summary_source` em `sectionSpec` e em `appendixSpec`:

| Seção | `summary_source` | Razão |
| --- | --- | --- |
| S1 / S3 / S4 / S7 / S8 / S9 / S10 | `s1` / `s3` / `s4` / `s7` / `s8` / `s9` / `s10` | correspondência semântica |
| S2 | `null` | `summaries.s2` é o parágrafo de **SCORE** (`summaries_narrator.py:111-116`); a S2 é Fluxo de Caixa |
| S_IRPF_RENDA, S_IRPF_OTIMIZACAO | `null` + `summary: false` | E5.N não produz narrativa fiscal-IRPF, e as camadas 1 e 3 também não — render site morto, deletado (§D11) |
| S_PROTECAO | `null` | `enabled: false`; [[ADR-240]] é card, não prosa |
| APP_A..APP_E | `null` | apêndices são texto determinístico |

Derivar por lowercase publicaria o parágrafo de score no topo do Fluxo de Caixa.
O mesmo bug estava codado em
`backend/app/services/section_summary_orchestrator.py::_read_legacy_summary`
(`summaries.get(section_id.lower())`) e o único teste que o cobria usava `S1` —
justamente o id onde a coincidência acerta. Com a entrega ligada o caminho
passou a ser alcançável em 5 seções, então o `_read_legacy_summary` **também**
lê `summary_source` (via `backend/app/generated/report_layout.py`); seção sem
destino declarado cai no fallback genérico em vez de publicar o parágrafo de
outra dimensão. Destino semântico do `s2` é **decisão de produto** (gatilho
`financial-planner`), não inferência de string.

**Allowlist de órfãs** — chaves emitidas sem destino, com razão escrita:
`ORPHAN_SUMMARY_KEYS` em `pipeline/domain/services/narrativas/summaries_narrator.py`
(`s2`, `s5`, `s6`). É fato do **produtor**, por isso não vive no layout. S5
(viagens) e S6 (cambial) saíram do layout com o Modo USA ([[ADR-168]]).

**O mapa esperado é declarado FORA do runtime** —
`tests/fixtures/narrativas/e5n_destinations.json`, com a razão semântica por
entrada, lido pelas duas pernas (Python + vitest). Sem isso as guardas liam o
destino do layout e o aferiam **contra o layout**: declarar
`summary_source: "s2"` na S2 passava 30/30 asserções, exatamente o defeito que
esta §D2 existe para prevenir. Medido: com a declaração, a mesma mutação
vermelha duas pernas — a de mapa (layout ≠ declaração) e a de conteúdo (a S2
publicou o texto de outra dimensão).

**KR-C honesto: 7 de 7 destinos declarados** — não 10/10 (10 chaves emitidas,
3 sem seção) nem 16/16 (16 call sites, 8 sem chave produtora).

### D3 — Registro visual por origem, para não gerar delta silencioso

- `source === "derived"` → `<p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">`,
  **markup byte-idêntico** aos 5 blocos de fallback que substitui. Onde nada
  novo chega, zero delta visual.
- `source in {"e5n","llm"}` → caixa `border-l-4` existente, **um** parágrafo no
  registro foreground **sem `font-medium`**: os textos do E5.N são expositivos,
  não conclusões editoriais.

O par `{context, conclusion}` do componente colapsa para um parágrafo: é shape
que nenhum produtor de **seção** emite (de **chart**, sim — ver D5).

### D4 — As 6 guardas são deletadas, não atualizadas

`S8:24`, `S9:99`, `S10:28`, `ApendiceA:96`, `ApendicesSections:50`
(`SectionFallback`) e o gate de visibilidade `S4RealEstateSection.tsx:14-18`.
Com render site único, o duplo-parágrafo é impossível **por construção**.

Para a S4, o gate volta a ser `if (!realEstate) return null;`. O escape "tem
narrativa S4" nunca foi alcançável, e com a entrega ligada seria **sempre**
verdadeiro (o E5.N emite `s4` sempre; `validate_narrativas` hard-falha em
summary vazio) — o que mataria o hide-when-empty da [[ADR-216]] Onda 6. O dono
da visibilidade é `data.real_estate`, não a prosa.

### D5 — Conclusão de chart mora em `narrativas.charts`, e só lá

`readNarrativeConclusion` promovido para
`frontend/src/components/report/utils/chartNarrative.ts`. As leituras top-level
mortas de `S1PatrimonioSection.tsx:45-51,84` e `S2FluxoCaixaSection.tsx:53-58`
são deletadas (0 dos 17 chart ids aparece no topo de `narrativas`), junto com o
comentário que descrevia o caminho inexistente ("narrativa explícita do E5.N >
fallback").

**Regra estática nova** (regra 5 de `dev/check_chart_conclusion_parity.py`, o
gate que já varre `sections/*.tsx`): em `sections/*.tsx` o bag `narrativas` só
pode ser acessado via `.charts`. Mesma classe da regra 4 um nível acima — "call
site com id que ninguém conhece renderiza vazio em runtime, silenciosamente". O
gate passa a ignorar comentários (senão o comentário que documenta a remoção de
um padrão proibido dispara a própria regra).

### D6 — CV9 mede entrega: render site, destino, órfã, shape e supressão

`scripts/validate_cross.py::_cv9_summaries_delivery`. Denominador = as entradas
do layout que **de fato exibem parágrafo** (`enabled` **e** `summary: true` **e**
`summary_source`), numerador = resolubilidade pelo **mesmo mapa que o renderer
lê**, menos o que o run não entregou. Quatro predicados de falha, nenhum
auto-referente:

1. **destino sem texto** (`error`) — layout declara `summary_source` e a chave
   não existe em `summaries`. Direção que nenhum gate cobria.
2. **chave órfã** (`error`) — `set(summaries) − destinos − allowlist`.
   Adicionar `s11` sem destino passa a falhar; hoje passava verde.
3. **shape** (`error`) — valor tem de ser `str` não-vazia. `{context,
   conclusion}` sob `summaries.sN` **passa** pelo `validate_narrativas`
   (`not {"a":1}` é `False`) e o renderer cai no derivado sem sinal.
4. **destino sem render site** (`error`) — `summary_source` declarado numa
   entrada com `summary: false` ou `enabled: false`: texto gerado, mapeado e
   **invisível**. É o caso *gerado-mas-não-entregue* estático.

E um quinto bucket, que **não reprova**:

5. **suprimido no run** (`info`) — a seção existe, tem render site e o texto
   existe, mas a seção **curto-circuita** neste run. Caso vivo: a S9 troca o
   corpo por `<EmptyState/>` quando `bubble_riscos.data_state == "empty"` e não
   imprime o `s9` (§D7). Medido: nesse estado o render entrega **6 de 7** e a
   primeira versão do CV9 devolvia `entregues=7/esperadas=7` — os quatro
   predicados de falha leem só flags **estáticas** do layout, cegas a supressão
   condicional, e a regra 6 do gate estático só exige que o `<SectionSummary>`
   **exista** no arquivo. Render condicional passava nas duas.

O gate de supressão é **declarado** — `summary_suppressed_by` na entrada do
layout (chart id cujo `data_state: "empty"` engole o parágrafo) — e não inferido
do código. Sai do numerador (`entregues=6/esperadas=7`) e entra em
`suprimido=[S9->s9]`, sem reprovar: a supressão é a decisão de produto da §D7, e
reprovar deixaria o CV9 vermelho em todo workspace sem risco cadastrado —
trocaria um verde decorativo por um vermelho decorativo. O que o nome "entregues"
promete é o número que o render produz, e é esse que sai.

**Duas premissas tornam o `entregues=N` honesto**, ambas regras do gate de
pre-commit `dev/check_chart_conclusion_parity.py`:

- **regra 6** — `summary: true` ⟺ `<SectionSummary … sectionId="<id>">` em
  `sections/*.tsx`, nas duas direções. Sem ela a flag mentiria: flag sem
  componente (texto invisível contado como entregue) e componente sem flag
  (denominador subestimado). Medido por mutação: apagar o `<SectionSummary>` da
  S10 deixa o gate vermelho;
- **regra 7** (nova) — `<SectionSummary>` sob condição no TSX ⟺
  `summary_suppressed_by` declarado, nas duas direções. Sem ela, supressão nova
  nasce invisível ao CV9 e declaração órfã fica de pé. Medido: a regra acusou de
  imediato um caso não previsto — o `{data && <SectionSummary …>}` da APP_A, onde
  a condição era null-guard de uma prop `data?` que só existia porque **um teste**
  montava o apêndice sem dados; em produção o `MigratedSection` sempre passa.
  Prop virou obrigatória e o render site voltou a ser incondicional.

Alternativa considerada e rejeitada: **renomear o CV9** para "mapping" e tirar
"entregues" da mensagem. Rejeitada porque a informação que falta (o render site e
o gate de supressão) é **declarativa** — vive no layout ou pode viver nele. Nome
honesto sem medir entrega seria trocar um gate decorativo por um rótulo modesto;
aqui o gate passou a medir o que promete.

`details` = `"entregues=N/esperadas=M; sem_texto=[...]; shape_invalido=[...]; orfas=[...]; sem_render=[...]; suprimido=[...]"`
— o `N/M` **é** o KR-C, observável por run. Unit test dos cinco buckets
(incluindo o gerado-e-não-entregue estático e o suprimido-no-run, este último
provado **sobre o layout versionado**, não sobre cenário sintético):
`tests/test_cv9_narrativas_delivery.py`.

CV9 lê o **YAML** do repo (`_pc._REPO_ROOT / "config/report_layout.yaml"`), não
o módulo Python gerado: importá-lo acoplaria `pipeline` → `backend`. O override
DB de `report_layout` não afeta o renderer React (`ReportShell` importa
`@/generated/report-layout`), então o YAML é a fonte correta hoje; se o renderer
passar a ler o layout do DB, este leitor tem de seguir.

**Severidade.** CV9 continua **fora** de `_CONSERVATION_CHECKS`
(`validate_cross.py`) — a medição da A36.l3 segue válida: run incremental que
reusa narrativa não pode pausar 100% dos runs. Mas sai de `_RENDER_SOFT` em
`dev/compare_reviews.py` para um terceiro conjunto `_DELIVERY_HARD = {"CV9"}`,
reportado no gate **default**. Sem isso o check nasceria silenciado no
pipeline-review e trocaria-se um verde vazio por outro.

**Limite honesto:** CV9 é telemetria de run, nunca gate de PR (só roda no stage
`validate_cross`; em CI há apenas unit test com E5 sintético). O bloqueio em PR
vem das outras pernas — vitest (fixture + mapa declarado + PII) e as regras
estáticas 5 e 6. As pernas observam coisas diferentes; é isso que remove a
auto-referência.

### D7 — Nenhum número entregue vem de default de código

Regra unificadora (co-design `financial-planner`, 2026-07-31): **ou o número vem
do payload, ou não é afirmado**. Três instâncias da mesma doença — "sem dado →
constante com aparência de cálculo" — tratadas como uma classe, com uma guarda
por instância em `tests/test_e5n_anti_hardcode.py` §braço D:

**1. `s8` — a estimativa fiscal sai inteira.** `das_aliquota_pct` vinha de
`FISCAL["das_simples"]["aliquota_efetiva_pct"]`, default 6%. Três defeitos
independentes, todos medidos:

- *constante fantasiada*: a própria fonte legada se desmente
  (`_comment: "estimativa para Anexo V típico … RBT12 ≤ R$ 360k"` +
  `_calcular_realmente: "usar tabela completa com RBT12"`). 6% só vale na 1ª
  faixa (RBT12 ≤ R$ 180k, parcela a deduzir 0). Na faixa do ICP a efetiva é
  11,05% (RBT12 720k) a 14,02% (1,8M) — **subestimava ~2×**, e no sentido que
  infla sobra de caixa e capacidade de aporte. O motor canônico já calcula certo
  (`cascata_calculator.compute_simples_aliquota_efetiva`, LC 123 art. 18);
- *base errada*: `receita_pj_anual` anualizava `receita_por_natureza.receita_pj`
  = pró-labore + lucros distribuídos ([[ADR-330]]), dinheiro que entrou na conta
  **PF**. DAS incide sobre faturamento bruto (RBT12). [[ADR-236]] §Emenda CTO-05
  já proibiu exatamente essa derivação;
- *ramo impossível*: `f"{_S8_REGIME_SEM_LABEL}{das}"` produzia "Regime PJ não
  informado (alíquota efetiva X%)". Sem regime não existe DAS.

E o card irmão `impostos_pj`, na **mesma seção S8**, já publica receita bruta +
tributos + carga + fator-R pela cascata canônica: um segundo estimador só pode
concordar (redundante) ou discordar (defeito publicado).

Decisão: o `s8` afirma **regime declarado** + contador + holding. Zero número
fiscal; carga, alíquota e faturamento ficam com a cascata.
`das_aliquota_pct`, `das_mensal_estimado`, `das_anual_estimado`,
`pct_das_receita_pj` e `receita_pj_anual` foram **deletados** do metrics — eram
os únicos consumidores do default fiscal.

**Nem DAS recolhido — silêncio, e não substituição (correção da 2ª versão desta
§D7).** A versão anterior trocava a estimativa por **DAS recolhido** (categoria
E4 `das_simples`, fato de extrato). O substituto é o certo em princípio e está
errado em fato **hoje**: `_DAS_KEYWORDS = ("DAS",)` casa a **preposição** ("DAS
LOJAS", "pedágio DAS …") e a medição do balde no workspace de dogfood deu **100%
de falso-positivo** (pedágio, supermercado). O fix do matcher é o **PR #1133**,
ainda não mergeado. Afirmar "DAS recolhido no período: R$ X" com esse balde
publicaria despesa de consumo como tributo — o oposto do que esta §D7 existe para
impedir. Enquanto o #1133 não aterrissa, o `s8` fica em silêncio sobre DAS: nem
estimado (default de código) nem recolhido (sinal contaminado). Reintrodução é
lane própria, com o balde corrigido.

Pela mesma razão a l4 **não** liga `das_simples` em `despesas_impostos` (só
corrige a documentação da chave morta `desp_cat["das"]`, que o E4 nunca emitiu):
trocar "balde de DAS ausente" por "consumo publicado como imposto" é regressão,
não fix. O consumidor é a narrativa do donut de despesas, hoje sem leitor
(§Deferimentos).

**Correção da primeira versão desta §D7 (objeção medida):** ela afirmava que o
`s8` degradaria para "Perfil tributário PJ pendente". Falso em produção —
`regime_obs` vem de `trib_cfg["regime_label"]` e `_regime_to_label(None, …)`
devolve `"Perfil tributário incompleto"` (`pipeline_adapter.py`), nunca vazio,
com `payload["tributario"]` sempre setado. Logo `_S8_REGIME_PENDENTE` era
**código morto** e o que renderizava era o rótulo pelado, sem CTA e sem o valor
detectado — regressão de UX vs. o card irmão. O sinal de ausência é
`tributario.regime is None`, não string de label.

**Não publicar (lista fechada, co-design `financial-planner`):** alíquota efetiva
sem `regime` + `anexo_simples` declarados; DAS estimado a partir de entradas PF;
"receita PJ anualizada" rotulada como receita da PJ sem o qualificador *entrada
na conta PF*; **R$ 0,00 em campo fiscal** (lê-se como "sua PJ não paga imposto",
pior que silêncio); honorário de contador (`contador_mensal` **não existe** em
`bundle["tributario"]` — o `get(..., 0)` publicava "(R$ 0,00/mês)" em todo
workspace com contador cadastrado); e **`contador_nome`**, que é PII de terceiro
(ver D9).

**2. `s3`/`perfil_familia`/`patrimonio_doughnut` — `diversificacao`.**
`len([...]) or 5` transformava "nenhuma categoria classificada" em "5
categorias", nos três consumidores. Zero é zero: `carteira_diversificacao_frase`
declara a ausência ("Composição da carteira ainda não classificada por categoria
de ativo") em vez de afirmar contagem.

**3. `TrsEfetivaStat` (S7) — `goals?.trs_pct ?? 5.0`.** Ver D8.

**Duas afirmações incondicionais** (não são default de código, são frase sem
sinal):

- **`s9`: "Seguros de vida e invalidez inexistentes".** Passa a exigir
  `protecao_patrimonial.gap_qualitativo[categoria='vida'].flag` ([[ADR-240]]).
  `None` = não sabemos, então não afirmamos.
- **`s4`: contagem contraditória — o `s4` não conta imóveis, em ramo nenhum.**
  A contagem disponível ao narrador é `investimentos.n_imoveis_total`
  (`InstituicoesPorMembroAnalyzer`, conta `bens_por_membro` do baseline IRPF:
  residência + investimento); a **tabela da S4** renderiza `real_estate.imoveis`
  (`populate_real_estate`, filtro estrito por `codigo_rfb`, [[ADR-225]]). Duas
  fontes, e nada reconcilia: medido no dogfood, `n_imoveis_total` = 6 e
  `len(real_estate.imoveis)` = 4 — o parágrafo abria a S4 com "6 imóveis no
  portfólio" e a MESMA seção listava 4 na tabela e dizia "4 imóveis de
  investimento" (nem 4+1 fecha em 6; `excluded_properties` tem 7, 3 deles
  duplicatas do mesmo registro de casa).

  A 1ª versão desta §D7 aplicou a regra só ao ramo `n == 0` (medido:
  `"0 imóveis no portfólio: residência (R$ 800k)"`); com `n > 0` a contagem
  voltava a ser afirmada — a instância grave, porque é a que o dogfood produz.
  Estender a guarda por "afirma só quando as duas fontes concordam" seria **guarda
  em ramo morto**: `generate_narratives` monta metrics e constrói as narrativas
  **antes** de `_e5n_populate_real_estate`, então em produção o lado direito da
  comparação nem existe. Logo o `s4` descreve **valor** (de `patrimonio`, a mesma
  fonte do card irmão) e a quantidade fica com a tabela da seção, seu único dono.
  Cada parcela é condicional: `residência (R$ 0,00)` lê-se como "sua casa não vale
  nada". Guarda: `tests/test_e5n_anti_hardcode.py::test_s4_nao_afirma_contagem_de_imoveis`
  proíbe **qualquer** `\d+ imóvel/imóveis`, não só a contagem divergente.

Mais três, do mesmo cleanup incompleto da [[ADR-168]]/A10.1 (que limpou o `s5` e
esqueceu os vizinhos):

- tail do `s8` "Obrigações fiscais EUA (FBAR, Form 8938, PFIC) requerem CPA
  expatriado antes da mudança" — deletado;
- `s6` "Meta pré-EUA" → "Meta de reserva cambial";
- `_S9_EMPTY` perde o CTA. **E a S9 em empty state não publica o `s9`**: o
  `<EmptyState/>` já *é* a mensagem ("sem riscos cadastrados não há análise de
  cobertura") — deduplicar o CTA não bastava, a afirmação também estava duplicada.
  Idem APP_C: é o único apêndice com parágrafo de abertura **autoral** (tom
  CVM/Susep, "não são previsões"), e o derivado repetia "validar a margem de
  segurança do plano" logo abaixo ⇒ `summary: false` e sem `<SectionSummary>`.

E dois defeitos de dado achados no caminho: `despesas_impostos` somava
`desp_cat.get("das")`, mas a categoria emitida pelo E4 é `das_simples`
(`transaction_classifier_pj.py:26,154`) — chave morta, e a chave certa fica fora
até o #1133 (acima); e o `s3` com cônjuge ausente emitia espaço órfão + frase sem
sujeito (`"… .  possui R$ 0,00 …"`), que viraria user-facing no instante em que o
`s3` acendesse.

**A fixture compartilhada é gerada na condição de PRODUÇÃO, e com conteúdo.** Duas
correções empilhadas:

1. a 1ª versão gerava com `tests/fixtures/legacy_configs/parametros_fiscais.json`
   copiado pelo `_build_e5_workspace`, então a guarda exercitava o ramo "alíquota
   declarada 6%" que produção nunca toma — o mesmo falso-verde de escopo que a
   A40.l3 pagou em 3 rodadas. O arquivo é removido antes de gerar;
2. o substrato era o E3 mínimo de **1 transação de R$ 100**, e a fixture nascia
   financeiramente **vazia** (`s1` com quatro `R$ 0,00`, `s2` com "0 meses",
   `s3`/`s5` zerados). Sentinela de **forma** funcionava; de **conteúdo**, não —
   com todo monetário em zero, trocar a fonte de um número por outra mantém a
   string idêntica e o par TS+Python fica verde sobre nada. O substrato passa a
   ser a fixture sintética PII-zero do dogfood (`run_dogfood_pipeline_ctx`, A23.l2:
   E1.5c→E3→E4→E5, com imóvel, CDB em dois anos, financiamento e dois extratos), e
   um teste próprio exige ≥6 valores monetários **distintos e não-zero** nos
   destinos entregues — impede a volta silenciosa a um substrato pobre.

### D8 — O yield-alvo da S7 vem do payload, e "meta" não serve a dois conceitos

[[ADR-191]] §Emenda 2026-07-15 (FP-03) decidiu que *yield-alvo/TRS-meta* (5%,
rentabilidade da carteira) e *taxa de retirada segura/SWR* (4%, regra dos 300 /
Trinity ×25) são conceitos **distintos que nunca se colapsam**. Logo o `s7` está
**correto** como está: "Renda passiva estimada (4% retirada segura)" é a
superfície do SWR, com rótulo casando com valor.

O defeito estava no card, em três camadas:

1. **chave fantasma** — `goals.trs_pct` **não existe** no payload (o E5 emite
   `goals.if_trs`, `if_projector.py:175`), então `(goals?.trs_pct) ?? 5.0` em
   `S7IndependenciaSection.tsx` disparava **100% das vezes**: literal de código
   impresso como se fosse a meta da família;
2. **fonte** — a casa sancionada do yield-alvo é `ratios.rentabilidade.meta_pct`
   (obrigatória em `e5_analysis.schema.json`, presente no snapshot do
   view-model), a **mesma** que o `kpi_rentabilidade` da S3 lê. Ausente ou de
   shape inesperado ⇒ **não se imprime meta alguma**; a TRS efetiva é valor
   observado e sustenta-se sozinha;
3. **rótulo** — o sublabel passa a "Yield-alvo", não "Meta" (a palavra "meta" já
   é da meta de IF dois elementos acima), e o tooltip perde o comparativo com
   Trinity 4%, vetado por [[ADR-191]] §D5 ("SWR de depleção do principal vs.
   yield de fluxo são incomparáveis").

**Enquadramento importa:** isto **não** é "contradição 4 vs 5 na mesma seção".
Sob FP-03 os dois números são legítimos e coexistem, desde que cada um seja
rotulado pelo próprio conceito e venha do payload. Tratar como contradição
convidaria um fix que "harmoniza" os dois — o que desfaz FP-03 e reintroduz o
otimismo ×20-vs-×25 (meta de IF ~20% mais curta).

### D9 — PII não vai ao texto entregue

O relatório é o artefato que a família guarda e **mostra a terceiros** (contador,
corretor, banco). Medido em render real: a narrativa determinística publicava
`nome_completo` de adultos **e de menor** (`perfil_familia_narrator`), a
residência por logradouro (`s4`, via `endereco.rua`), o endereço completo na
cláusula de pets, e o **nome do contador** (`s8` e o disclaimer do
`CascataFiscalCard`). Todos PII dura por [[ADR-319]].

Substituições: **primeiro nome** (`nome_curto`, já disponível em
`NarrativasContext`) para adultos, **papel** para o menor ("Primeiro filho do
casal" — menor é a PII mais sensível) e para o contador ("Contador cadastrado" /
"Há contador cadastrado no perfil da PJ"), e **nada** para endereço.

Guarda em três braços (`tests/test_e5n_pii_guard.py`), porque nenhum sozinho
basta:

- **sentinela por campo** — a família de teste carrega um valor PII-shaped
  inconfundível em cada campo; nenhum pode aparecer no output. Campo novo que
  vaze fica vermelho sem editar o teste. Inclui `nome_nascimento` (nome civil
  anterior, lido por `member_name_resolver` na raiz **e** em `extra`), que estava
  fora da lista e da família-sentinela;
- **forma de nome completo** — sequência de 2+ palavras capitalizadas é padrão de
  nome próprio. Dois furos fechados no fechamento da lane: (a) `nome_curto` de 2+
  palavras ("Ana Clara") tem a mesma forma e é o substituto **sancionado** — é
  subtraído dinamicamente da varredura, nunca declarado na allowlist de domínio,
  senão a única saída de quem vê a falha seria pôr nome de pessoa lá; (b) a
  allowlist tinha só rótulos de regime, mas o texto real emite **labels de classe
  de ativo** ([[ADR-193]], via `alocacao_narrator`) — "Renda Fixa", "Ações Int" —,
  e a fixture não produzia o chart que os gera, então a guarda ficava verde sobre
  vocabulário que ela não via. A fixture passa a emitir `alocacao_alvo.derived` e
  um teste próprio recusa entrada de allowlist que a regra **nunca poderia
  acusar** (achou uma na hora: `Ações BR`, sigla em maiúscula);
- **regra estática** — narrador nenhum pode LER `nome_completo`,
  `local_nascimento`, `cpf` ou `endereco` (o gate de pre-commit
  `dev/check_pipeline_log_pii.py` cobre **log**, não texto renderizado; a regra
  distingue leitura de menção em prosa, senão o comentário que documenta a
  remoção dispara a própria regra).

Medido por mutação: reintroduzir `nome_completo` no card de perfil deixa 3
asserções vermelhas (sentinela + forma + regra estática).

### D10 — O sufixo de changelog compõe com a camada 2

O sufixo de delta ([[ADR-148]]) era anexado **dentro** de `deriveSectionSummary`
— camada 3. Com a camada 2 acesa em 7 seções, a 3 deixaria de rodar nelas e o
sufixo pararia de renderizar **sem ninguém decidir isso**.

Decisão: o sufixo é *anotação de delta*, ortogonal a quem escreveu o
parágrafo-base ⇒ **compõe com a camada 2**. **Não** compõe com a camada 1: o LLM
recebe o snapshot e é quem redige o delta ([[ADR-144]] §3), e
`deriveSectionSummary` já retornava antes do sufixo no ramo LLM. Assim o
comportamento existente é preservado onde existia e estendido onde a camada 2 o
substituiu. A [[ADR-148]] **não** perde efeito.

**Ressalva medida:** o "pararia de renderizar" é hipotético, não observado. O
sufixo casa por `changelog[].section_id == sectionId`, e
`get_report_data.py:78` monta `SnapshotChangelogConfig()` **default**, cujo
`sections_to_compare` é `M_PL`/`M_TAXA_POUPANCA`/`M_RESERVA_MESES`/`M_AUVP_DESVIO`
([[ADR-190]] §Emenda) — **nenhum** é id de seção do layout. Logo, hoje, o sufixo
não renderiza em seção nenhuma, com ou sem camada 2. A decisão vale como
**contrato** (o dia em que a config voltar a comparar ids de seção, a composição
já está definida e testada no vitest), não como preservação de comportamento
visível. Registrar isso importa porque a versão anterior desta §D10 tratava a
composição como salvamento de um sufixo que estava renderizando.

### D11 — Higiene do layout, senão o denominador mente nas duas direções

- `plano_de_acao` tinha `summary: true` e **não** renderiza `<SectionSummary>`
  (é projeção da `Decision` aggregate) ⇒ `summary: false`.
- `S_IRPF_RENDA` e `S_IRPF_OTIMIZACAO` ficavam com `summary: true` + render site +
  `summary_source: null` — flag prometendo parágrafo que **nenhum produtor podia
  produzir**. Medido nas três camadas: fora de `SUPPORTED_SECTION_IDS` e do
  catálogo `config/prompts/section_summaries.yaml` (camada 1), `summary_source:
  null` porque o E5.N não produz narrativa fiscal-IRPF (camada 2), e sem entrada
  em `SECTION_SUMMARIES` de `conclusionUtils.ts` (camada 3) ⇒
  `resolveSectionSummary` devolve `null` **sempre**. O sufixo de changelog também
  não salva: `DEFAULT_SECTION_VALUE_PATHS` não tem esses ids e um override os
  rejeitaria com `UnknownSectionError`. ⇒ `summary: false` e o `<SectionSummary>`
  **deletado** dos dois componentes, mesmo critério da §D4 (render site morto sai,
  não é atualizado). Dar texto de abertura a essas seções é decisão de copy.
- APP_A, APP_B, APP_D, APP_E renderizam `<SectionSummary>` e **não** tinham a
  flag ⇒ `appendixSpec` ganha `summary` + `summary_source`. A APP_C fica
  `summary: false` (parágrafo autoral, ver D7).
- A correspondência flag ⟺ render site deixa de ser higiene manual e passa a ser
  gate: regra 6 de `dev/check_chart_conclusion_parity.py` (ver D6).
- `AppendixSpec` do codegen é `extra="forbid"` e não declarava `optional`,
  enquanto `APP_C` tem `optional: true` ⇒ **`backend/app/generated/report_layout.py`
  levantava `ValidationError` no import** (bug pré-existente; `--check` compara
  texto, não importa). Corrigido no mesmo PR.

## Alternativas consideradas

**Normalizar no boundary Python (`get_report_data.py:38-68`).** Rejeitada: as 5
fixtures E2E em `frontend/tests/e2e/fixtures/reports/*.json` **são a saída desse
boundary**; normalizar lá faz a fixture codificar o resultado do boundary e o
teste fica verde testando o que produção não executa — a armadilha que a A40.l3
pagou em 3 rodadas.

**Normalizar em `getReportData` (`lib/api/reports.ts:313-315`).** Rejeitada:
cobre produção + PDF + E2E, mas é **invisível aos 139 arquivos de vitest**, que
injetam `data` direto no componente. E vitest é o job bloqueante
(`frontend-checks`); o visual não é.

O caminho de render é a única posição em que **toda** superfície atravessa a
normalização: produção, PDF (mesma rota React, [[ADR-129]]), E2E, vitest por
seção e vitest de shell.

**Estender o substrato golden (`tests/pipeline_golden_substrate.py`) para incluir
E5.N.** Rejeitada: seria a única forma de o snapshot do view-model ver
narrativa, mas acopla churn de copy a um teste de 8min do backend e injeta prosa
num golden cuja finalidade declarada é conservação monetária em cents com zero
float. O golden de narrativa é a fixture própria, com flag de regeneração
própria.

## Consequências

- **KR-C medido na página real** (dois servidores Next simultâneos — `:3000` do
  checkout principal em `5fa70296`, base da lane, e `:3011` do worktree —, um
  único spec Playwright injetando o **mesmo payload** nos dois via `**/data`):
  seções com parágrafo de abertura **7 → 12** (+5 = S1, S2, S3, S4, S7), das
  quais **0 → 7** em registro de caixa; destinos do E5.N entregues **0/7 → 7/7**.
  S2 entra pelo derivado (`summary_source: null`), não pelo E5.N. Denominador = as
  **14** entradas que a página monta com esse payload (de 17 `enabled`):
  `S_IRPF_*` exigem `irpf_kpis` e a `APP_C` não monta com essa fixture.
  A tabela anterior ("8 → 13") vinha de render **isolado pelo dispatcher** em
  vitest, que monta seção sem o dado que a página exige — dois procedimentos, dois
  denominadores; o que o usuário vê é a página.
- Guarda anti-regressão em **cinco** pernas independentes: (1) fixture
  compartilhada gerada pelo produtor na condição de produção **e sobre substrato
  com valores não-triviais** (`tests/fixtures/narrativas/e5n_delivery.json`);
  (2) mapa de destino declarado fora do runtime (`e5n_destinations.json`), que é o
  que detecta destino semanticamente errado; (3) anti-hardcode **por parâmetro
  citado** com a lista **derivada do fonte do builder**, não curada
  (`tests/test_e5n_anti_hardcode.py`); (4) guarda de PII sobre o **artefato
  inteiro** (`tests/test_e5n_pii_guard.py`); (5) regras estáticas 5, 6 e 7 do gate
  de pre-commit. As duas primeiras são lidas pelos dois lados (Python + vitest).
- **A curadoria era o furo da perna 3.** `_PARAMS_CITAVEIS` tinha 22 linhas
  escritas à mão e nada forçava que parâmetro citável novo entrasse: um parâmetro
  fora da lista podia nascer congelado sem o teste ver. O braço A2 extrai do
  próprio `scripts/generate_narratives.py` as **24 folhas** de `goals.json` que o
  builder lê e exige classificação para cada uma — linha citável, `gate` (perturbar
  muda algum summary) ou `sem_efeito` (perturbar não muda nenhum) —, com as duas
  últimas **verificadas contra o comportamento**. Congelar um literal move o
  parâmetro de "citado" para "sem efeito": a linha do braço A fica vermelha e a
  classificação passa a mentir.
- **Delta visual, medido por registro** (mesmo procedimento de dois servidores):
  com o bag `narrativas` presente, **7 seções** passam a exibir a caixa
  `border-l-4` — S1, S3, S4, S7, S9 vinham de *nada*, e S8 e **S10** trocam o
  `<p>` derivado pela caixa. A S2 ganha o `<p>` derivado (markup idêntico ao
  fallback que substitui, texto novo).
- **Delta visual nas 5 fixtures E2E, medido na `medium`**: o bag `narrativas`
  dessas fixtures só tem `perfil_familia`, então a camada 2 **não dispara** e
  nenhuma seção muda de registro; o delta é `S1`, `S2`, `S3` e `S7` passando de
  nada para o `<p>` derivado ⇒ **8 PNGs** (4 seções × {light, dark}) em
  `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`. `S4`
  e `APP_C` não montam com a `medium`. A versão anterior desta linha dizia que o
  delta era "S2 ganhando o `<p>` derivado e as demais mantendo o markup" —
  **medido falso**. O job visual **não é bloqueante** ⇒ o rebaseline é explícito,
  não deixado para o próximo agente.
- **Delta monetário esperado: `=`.** Nada nesta ADR escreve campo do
  view-model — o E5.N grava só `narrativas`, `section_summaries`,
  `real_estate` e `tributario`, e nenhum deles está nas 31 chaves de
  `backend/tests/snapshots/dogfood_view_model.json` (o substrato golden roda
  `E1.5c→E3→E4→E5` e **nunca** chama E5.N). Logo o sinal é o snapshot passar
  **verde sem rebaseline**; falhar é achado, não ruído.

## Deferimentos datados (2026-07-31)

- **`s3` contradiz a tabela da própria S3.** Medido no render single-source (cards
  e parágrafo do MESMO payload): o texto abre a S3 com "Carteira diversificada
  entre **3** categorias de ativos" e a tabela da seção lista **2** classes.
  `diversificacao` conta entradas não-zero de `patrimonio.composicao` (buckets
  patrimoniais, um deles **por membro**: `Imóveis de Renda`, `Investimentos Alex`,
  `Caixa e Moeda Estrangeira`) e a tabela lê `investimentos.tabela_classes`
  (`Imóveis Investimento`, `Renda Fixa`) — mesma classe do `s4` (§D7): contagem de
  fonte que não é a da seção, com rótulo que não descreve o que foi contado. O fix
  candidato é de uma linha (`summary_source: null` na S3), mas mudar destino é
  **decisão de produto** por esta própria §D2 (gatilho `financial-planner`) —
  tomá-la no fechamento da lane repetiria o defeito que a §D2 existe para impedir.
  Lane própria, com o gate.
- **`s1` publica `residência própria de R$ 0,00`.** Mesma classe do "R$ 0,00 em
  campo fiscal" da §D7; no `s4` a parcela zerada passou a ser suprimida, no `s1`
  não. Dono A40.l5.
- **`perfil_familia.right` publica `n_imoveis`** — a contagem que o `s4` deixou de
  afirmar. Contradição **cross-seção** com a tabela da S4 (não intra-seção),
  pré-existente e independente desta lane, num card que já renderizava.

- **S1/S2 apontando para `narrativas.charts`** — fora do escopo da A40.l4, dono
  A40.l15. Dois bloqueios independentes: (a) `charts_narrator.py:190-199` tem o
  **ranking hardcoded** do donut de despesas ("não identificado lidera, seguida
  por impostos, moradia e serviços domésticos", 4 slots fixos, zero ordenação) —
  a instância do RV3-33 em que a 14ª maior aparece como 3ª; hoje o usuário está
  protegido por acidente porque o `deriveChartConclusion` do TS ordena de
  verdade; (b) a A40.l3 tornou obrigatória a cláusula de janela no texto
  derivado de `receita_bar`, e o texto do E5.N não a tem.
- **`has_us_exposure` não chega ao E5.N.** `_ACTION_LINES[(True, *)]` de
  `charts_narrator` ("Ação: CPA expatriado + seguro term …") é gatilhada por
  `M.get("has_us_exposure")`, que `load_metrics_from_e5` **nunca popula** — o
  campo existe no `ProtectionBundle` ([[ADR-192]] §D4) e no DB, mas não é
  cabeado ao metrics do narrador. Os dois ramos `True` são inalcançáveis em
  produção. Não é defeito de texto (a cláusula é corretamente condicional), é
  fio solto: cabear ou deletar exige decisão sobre US tax status.
- **A meta de TRS exibida não é configurável pela família.** O card agora lê
  `ratios.rentabilidade.meta_pct` (D8), o que resolve a leitura órfã e a
  contradição intra-seção — mas **não** faz o número ser da família:
  `RatiosCalculator()` roda com `RentabilidadeConfig()` default (5,0) e
  `PassiveIncomeConfig.trs_meta_pct`, construído a partir do goal do workspace,
  **nunca é lido** pelo calculator. O wizard coleta `goal.if.inputs.trs_pct`
  (0-20) e o relatório ignora. Ligar `RentabilidadeConfig.meta_pct` ao goal e
  matar `PassiveIncomeConfig.trs_meta_pct` é mudança de **cálculo** — lane
  própria, não esta.
- **Base da cascata herda o erro de categoria do CTO-05 no ramo de regime
  declarado** (`receita_bruta = receita_pj_anual`). A fonte correta de
  faturamento declarado é `FinanceiroPJSnapshot.receita_bruta_total_anual`
  (informe financeiro_pj, [[ADR-238]]), hoje passthrough e não usada. Mudança de
  cálculo ⇒ ADR e lane separadas.
- **`renda_passiva_estimada_4pct` cristaliza "4" no nome da chave** enquanto a
  taxa é configurável (`taxa_retirada_segura_pct`). Workspace com 3,5% produz um
  campo cujo nome mente para o próximo leitor (o LLM do parecer incluído). O
  texto entregue é honesto (imprime a taxa real); a liability é o **nome da
  chave** do view-model — dono A40.l5, que já mexe no contrato.

## Fronteira com a A40.l5

A l4 entrega **dado declarativo** (mapa `summary_source` no layout + allowlist de
órfãs + shape de `narrativas`/`section_summaries` declarado em
`config/schemas/e5_analysis.schema.json`) e **uma regra** no gate estático que já
existe. A l4 **não** constrói `dev/check_view_model_contract.py` nem
`dev/codegen_report_analysis.py` — são o entregável da l5, e a declaração de
shape que a l4 deixa é o insumo que impede o codegen da l5 gerar tipo frouxo.
