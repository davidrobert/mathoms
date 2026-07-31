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
---

# ADR-355 — Precedência declarada do parágrafo de seção e CV9 como medida de entrega

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
do E5.N: as 8 seções que chamavam `deriveSectionSummary` renderizavam parágrafo
derivado, o que fazia o defeito parecer ausente.

Medição por render real através do dispatcher (`MigratedSection`, 13 seções
`enabled`), antes desta ADR: **7 seções com parágrafo, 0 de 10 narrativas do
E5.N entregues**.

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
| S_IRPF_RENDA, S_IRPF_OTIMIZACAO | `null` | E5.N não produz narrativa fiscal-IRPF |
| S_PROTECAO | `null` | `enabled: false`; [[ADR-240]] é card, não prosa |
| APP_A..APP_E | `null` | apêndices são texto determinístico |

Derivar por lowercase publicaria o parágrafo de score no topo do Fluxo de Caixa.
O bug já está codado em
`backend/app/services/section_summary_orchestrator.py:113`
(`_read_legacy_summary`) e o único teste que o cobre usa `S1` — justamente o id
onde a coincidência acerta. Destino semântico do `s2` é **decisão de produto**
(gatilho `financial-planner`), não inferência de string.

**Allowlist de órfãs** — chaves emitidas sem destino, com razão escrita:
`ORPHAN_SUMMARY_KEYS` em `pipeline/domain/services/narrativas/summaries_narrator.py`
(`s2`, `s5`, `s6`). É fato do **produtor**, por isso não vive no layout. S5
(viagens) e S6 (cambial) saíram do layout com o Modo USA ([[ADR-168]]).

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

### D6 — CV9 mede entrega: destino, órfã e shape

`scripts/validate_cross.py::_cv9_summaries_delivery`. Denominador = inventário
do **consumidor** (layout), numerador = resolubilidade pelo **mesmo mapa que o
renderer lê**. Três predicados, nenhum auto-referente:

1. **destino sem texto** (`error`) — layout declara `summary_source` e a chave
   não existe em `summaries`. Direção que nenhum gate cobria.
2. **chave órfã** (`error`) — `set(summaries) − destinos − allowlist`.
   Adicionar `s11` sem destino passa a falhar; hoje passava verde.
3. **shape** (`error`) — valor tem de ser `str` não-vazia. `{context,
   conclusion}` sob `summaries.sN` **passa** pelo `validate_narrativas`
   (`not {"a":1}` é `False`) e o renderer cai no derivado sem sinal.

`details` = `"entregues=N/esperadas=M; sem_texto=[...]; orfas=[...]; shape_invalido=[...]"`
— o `N/M` **é** o KR-C, observável por run.

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
vem das outras duas pernas — vitest e regra estática. As três pernas observam
coisas diferentes; é isso que remove a auto-referência.

### D7 — Correções de conteúdo, pré-condição de acender S8 e S9

Acender a entrega publica o texto como está. Duas afirmações eram falsas por
construção:

- **`s8`: alíquota DAS de default hardcoded.** `das_aliquota_pct` vinha de
  `FISCAL.get("das_simples", {}).get("aliquota_efetiva_pct", 6.0)`, lido de
  `config/parametros_fiscais.json` — arquivo migrado para a tabela
  `fiscal_parameters` em A7.2b ([[ADR-135]]) e **path proibido no git**. Em
  produção `FISCAL` é `{}`, logo 6% era constante, e
  `das_mensal_estimado`/`das_anual_estimado` derivavam dela. Publicar "alíquota
  efetiva 6%" + DAS em reais é **pior** que não mostrar nada, porque parece
  calculado. Decisão: `das_aliquota_pct` passa a ser `None` sem fonte fiscal, e
  o `s8` suprime a cláusula inteira, degradando para
  `"Perfil tributário PJ pendente — …"` — o registro que o irmão
  `charts_narrator.impostos_pj` já adota ([[ADR-236]] §D5).
- **`s9`: "Seguros de vida e invalidez inexistentes" incondicional.** Passa a
  exigir sinal: `protecao_patrimonial.gap_qualitativo[categoria='vida'].flag`
  ([[ADR-240]]). `None` (bloco ausente) = não sabemos, então não afirmamos.

Mais três, do mesmo cleanup incompleto da [[ADR-168]]/A10.1 (que limpou o `s5` e
esqueceu os vizinhos):

- tail do `s8` "Obrigações fiscais EUA (FBAR, Form 8938, PFIC) requerem CPA
  expatriado antes da mudança" — deletado;
- `s6` "Meta pré-EUA" → "Meta de reserva cambial";
- `_S9_EMPTY` perde o CTA: com a entrega ligada ele imprime **acima** do
  `<EmptyState/>` da S9 (o `<SectionSummary>` está antes do ternário `isEmpty`),
  que já traz call-to-action — com wording diferente. O produtor fica factual; o
  CTA é do componente.

E dois defeitos de dado achados no caminho: `despesas_impostos` somava
`desp_cat.get("das")`, mas a categoria emitida pelo E4 é `das_simples`
(`transaction_classifier_pj.py:26,154`) — o balde de DAS desaparecia; e o `s3`
com cônjuge ausente emitia espaço órfão + frase sem sujeito
(`"… .  possui R$ 0,00 …"`), que viraria user-facing no instante em que o `s3`
acendesse.

### D8 — Higiene do layout, senão o denominador mente nas duas direções

- `plano_de_acao` tinha `summary: true` e **não** renderiza `<SectionSummary>`
  (é projeção da `Decision` aggregate) ⇒ `summary: false`.
- APP_A..APP_E renderizam `<SectionSummary>` e **não** tinham a flag ⇒
  `appendixSpec` ganha `summary` + `summary_source`.
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

- KR-C medido por render real através do dispatcher: **0/7 → 7/7** destinos
  entregues; seções com parágrafo de abertura **7 → 13**.
- Guarda anti-regressão em três pernas independentes: fixture compartilhada
  gerada pelo produtor (`tests/fixtures/narrativas/e5n_delivery.json`, lida por
  `tests/test_e5n_delivery_contract.py` e por
  `frontend/tests/components/report/sectionSummaryDelivery.test.tsx`), teste
  anti-hardcode de conteúdo (`tests/test_e5n_anti_hardcode.py`) e regra estática
  no gate de pre-commit.
- **Delta visual esperado**: S1, S3, S4, S7, S9, S10 ganham a caixa
  `border-l-4`; a S8 troca o `<p>` do fallback pela caixa. Os PNGs de
  `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`
  mudam nessas seções. O job visual **não é bloqueante** ⇒ o rebaseline é
  explícito, não deixado para o próximo agente.
- **Delta monetário esperado: `=`.** Nada nesta ADR escreve campo do
  view-model — o E5.N grava só `narrativas`, `section_summaries`,
  `real_estate` e `tributario`, e nenhum deles está nas 31 chaves de
  `backend/tests/snapshots/dogfood_view_model.json` (o substrato golden roda
  `E1.5c→E3→E4→E5` e **nunca** chama E5.N). Logo o sinal é o snapshot passar
  **verde sem rebaseline**; falhar é achado, não ruído.

## Deferimentos datados (2026-07-31)

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
- **`goals?.trs_pct ?? 5.0`** em `S7IndependenciaSection.tsx:96` — instância
  PD-20/RV3-26, conta no KR-A da A40.l5 ("leituras órfãs 5 → 0"). A chave real é
  `goals.if_trs` (`if_projector.py:175`). A contradição já é visível hoje via
  `perfil_familia_narrator.py:192`, então entregar o `s7` adiciona superfície mas
  não cria o defeito: veredito `agora-visível-e-errado · pré-existente · owned
  by A40.l5`.

## Fronteira com a A40.l5

A l4 entrega **dado declarativo** (mapa `summary_source` no layout + allowlist de
órfãs + shape de `narrativas`/`section_summaries` declarado em
`config/schemas/e5_analysis.schema.json`) e **uma regra** no gate estático que já
existe. A l4 **não** constrói `dev/check_view_model_contract.py` nem
`dev/codegen_report_analysis.py` — são o entregável da l5, e a declaração de
shape que a l4 deixa é o insumo que impede o codegen da l5 gerar tipo frouxo.
