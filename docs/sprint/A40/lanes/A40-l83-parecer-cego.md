---
id: A40.l83
type: lane
title: "Parecer cego em três eixos: não recebe a incerteza, não consegue citar o que recebe, e o guardrail que deveria pegar isso inverte o diagnóstico"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
priority: P0
branch_slug: a40-l83-parecer-cego
ship_pr: 1716
ship_date: "2026-08-25"
adrs:
  - "[[ADR-200]]"
  - "[[ADR-353]]"
  - "[[ADR-394]]"
  - "[[ADR-206]]"
  - "[[ADR-304]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/llm
  - area/report
---

# A40.l83 — Parecer cego (RV8-05 · RV8-07 · RV8-16)

> **O parecer é a única superfície que PRESCREVE.** Tudo o mais no relatório
> descreve; ele recomenda. Os três achados desta lane são independentes no
> código e convergem no mesmo efeito: ele prescreve sem ver, sem poder citar, e
> sem que o instrumento de eval registre nenhuma das duas coisas.

## O que foi medido no r8 (run `d0f6260a`)

**RV8-05 — não recebe a incerteza.** `config/prompts/parecer_planejador.yaml` é
**whitelist**: o que não está declarado não entra. Grep dos seis campos de
incerteza construídos na A40 devolve **zero** ocorrências —
`investimentos_nao_atribuidos`, `cobertura_investimentos`, `nao_classificado_pct`,
`diagnostico_confianca`, `guarda_de_sinal`, `pl_ressalva`. O `_meta.tool_trace`
do run confirma que o pull discricionário não compensa: **6 iterações, 3 paths
únicos, todos em `reserva_emergencia`**.

**O modelo não alucinou — e isso muda o remédio.** Ele ressalvou **3 de 3**
lacunas que o payload declarou e **0 de 1** da que o payload não declarou. O
defeito é de projeção, não de prompt. Consertar o prompt seria consertar o lado
errado.

**RV8-07 — não consegue citar.** `measure_anchorability` sobre o E5 **real**
deste run devolve `ancoraveis: []` — **0 de 36** caminhos monetários visíveis têm
rota de citação, com `catalogo_renderizado: 16` de `catalogo_construido: 30`. O
snapshot que **gateia** (`dev/snapshots/parecer_ancorabilidade.json`, corpus
sintético `make_workspace_e5`) reporta **11/28 = 39,3%**.

Mecanismo: `_PRIORITY_ROOTS` (`parecer_citation_catalog.py:67`) ranqueia
(`:205-207`), `max_entries=30` corta (`:232,242`) e `select_catalog_entries(...,
max_bytes)` (`:268`) trunca. O renderizado colapsa em **2 raízes**
(`reserva_emergencia` + `endividamento`), cuja cardinalidade **escala com o
cliente**: quem tem mais dívidas nunca vê investimentos.

**RV8-07b — o eval é fail-open.** `coverage_failed`
(`parecer_evidencia.py:192-194`) devolve `failures_by_layer.get(_COVERAGE_LAYER)`
— conta só `missing_path`, que **só existe para âncora emitida**. Item com
`ancoras: []` não gera entry. Resultado no r8: `coverage_failed: 0` com **17 de
21 itens sem âncora nenhuma**. Pior: `itens_sem_ancora` **existe** como campo
(`:178`, incrementado em `:292`) e **não entra** em `log_evidencia_kpi`
(`:252-262`), que loga apenas `verified`/`coverage_failed`/`correctness_failed`.
O painel lê 100% de cobertura, zero falhas.

**RV8-16 — o guardrail inverte o diagnóstico.** `_meta.field_request_audit` traz
2 pedidos marcados `field_request_spurious`, **ambos legítimos**, ambos removidos
do output do usuário:

1. Path cortado do catálogo por `max_bytes`. `_classify_campo`
   (`parecer_pos_llm_guardrails.py:266`) pergunta `classify_field_path(e5_data,
   path)` — **consulta o E5**, enquanto a afirmação do modelo era sobre o
   **catálogo**. Predicado e afirmação falam de universos diferentes.
2. Valor `'desconhecida'` no E5. `_ABSENCE_SENTINELS = {"", "N/D", "nan"}`
   (`:62`) não o contém ⇒ `present` ⇒ spurious.

Taxa de falso-positivo: **2 de 2**. E o contador que deveria sinalizar
**truncamento de contexto** é lido como "modelo alucinou path".

## Armadilhas

**A pior: rebaselinar o snapshot pelo mesmo corpus re-certifica a cegueira.**
O gate é verde porque o corpus sintético não parece com produção — cardinalidade
de dívidas e baldes de reserva muito menor. Rebaseline tem de vir de corpus com
cardinalidade comparável à real, senão o instrumento continua medindo outra coisa
e o próximo run reabre o achado. Classe conhecida: fixture que clampa o que
produção não clampa.

**Subir `max_bytes` sozinho não resolve, e round-robin também não.** A medição do
r8 indica: semear pelo **conjunto visível** (`iter_visible_money_paths`) antes de
completar com o walk genérico é o que move a agulha; round-robin por raiz sem
mudar o seed chega a ~5,6%. Re-meça antes de escolher — o corpus muda.

**Mexer no manifest muda o parecer.** Golden precisa de rebaseline consciente e
`PROMPT_VERSION` precisa de bump (há hook `check_prompt_version_bumped`).

**`out_of_catalog` é mudança de contrato.** O enum de `reason` vive sob
`additionalProperties: false` ([[ADR-206]]) — schema + bump, não só código.

**A camada de token monetário em prosa é decisão vigente, não descuido.**
`money_tokens_total` está fora de `_HARD_LAYERS` por [[ADR-304]] §Emenda
2026-08-03. Se a lane quiser mudar isso, é emenda datada — não edite em silêncio.

## Escopo

| Peça | Superfície | Natureza |
|---|---|---|
| RV8-05 | `config/prompts/parecer_planejador.yaml` (bloco `patrimonio`) | projeção declarativa + `narrative_hint` de supressão |
| RV8-05b | `dev/_planner_coverage_internals.py:325-335` | drift E5↔manifest é `warn` e 3 ADRs passaram por ele — promover a `fail` com lista de escape versionada |
| RV8-07 | `parecer_citation_catalog.py` (`_PRIORITY_ROOTS`, `select_catalog_entries`) | semear pelo conjunto visível |
| RV8-07b | `parecer_evidencia.py` (`log_evidencia_kpi`) | `itens_sem_ancora` vira KPI logado **e** gate do golden mensal |
| RV8-16 | `parecer_pos_llm_guardrails.py` (`_classify_campo`, `_ABSENCE_SENTINELS`) | novo reason + placeholder de domínio como `empty` |

## Critério de aceite

**Corretude** — `measure_anchorability` sobre o **E5 real** (não o sintético)
≥ 80%. Rodável in-process, custo zero: é assim que o número desta lane foi obtido.

**Completude** — os seis campos de incerteza projetados, e o gate de drift
E5↔manifest reprovando quando o schema ganha campo de incerteza que o manifest
ignora. `field_requests_spurious` volta a **0** neste payload, com os dois pedidos
reaparecendo no output.

**Consistência** — o predicado que classifica pedido de campo consulta o **mesmo
universo** sobre o qual o modelo se pronunciou (catálogo, não E5). Duas perguntas
diferentes, dois reasons diferentes.

**Precisão** — o KPI publicado distingue *"a âncora resolve?"* de *"houve
âncora?"*. `coverage_failed` fica como está; a densidade
(`itens_sem_ancora / itens_total`) entra ao lado. Um número que só pode dar zero
não é medida.

**Prova de fecho (predicado do r9)** — parecer com ≥1 ressalva em item de tema
`Alocação`; ancorabilidade sobre E5 real acima do piso; e `itens_sem_ancora`
presente na telemetria com valor não-trivial ou zero **explicado**.

## Delegação

Co-design `prompt-engineer` (projeção, catálogo, eval) + `financial-planner`
(que ressalva o parecer deve emitir quando a fatia sem dono cruza o piso —
é regra de domínio, não de prompt). `senior-cto` decide se o drift
E5↔manifest vira `fail` bloqueante.

## Rastro

RV8-05, RV8-07 e RV8-16 do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`,
2026-08-24). Medições refeitas nesta lane. Cru off-git em
`storage/<uuid>/reviews/20260824-2235-d0f6260a/`.

## Fecho — 2026-08-25 (#1707 · #1709 · #1712 · #1714 · #1716 · [[ADR-206]] §Emenda)

Cinco peças, cinco PRs. **Ancorabilidade sobre o E5 real do run `d0f6260a`: 0/36 → 32/37
(86,5%)**, contra piso de 80% no §Critério.

| peça | PR | o que mudou |
|---|---|---|
| RV8-07 | #1707 | catálogo semeado pelo conjunto visível; `citation_catalog_for` vira produtor único |
| RV8-07b | #1709 | `itens_sem_ancora` + `itens_total` no KPI logado; `parecer_prose_money.py` extraído |
| RV8-16 | #1712 | filtro 4-vias + `field_request_out_of_catalog`; emenda datada na [[ADR-206]] |
| RV8-05 | #1714 | os 6 campos de incerteza projetados; manifest 2.3.0 |
| RV8-05b | #1716 | drift E5↔manifest com baseline na base de merge, `fail` para campo novo |

### Cinco correções ao enunciado

**1. O 0% não era "baixo" — era disjunção.** As raízes visíveis (`fluxo_caixa` 18,
`investimentos` 11, `consumo_consciente` 4, `patrimonio` 2, `exposicao_cambial` 1) e as
do catálogo renderizado (`reserva_emergencia` 11, `endividamento` 5) não tinham **uma**
interseção. A lane lia como cobertura ruim; era universo trocado.

**2. O remédio do RV8-07b não serve.** O §Escopo mandava `itens_sem_ancora` virar
"gate do golden mensal". Esse eval **nunca executou**: o secret
`ANTHROPIC_API_KEY_GOLDEN_MONTHLY` não existe no repo, os 4 runs agendados desde
2026-06 pularam reportando `success` em 16–34s, e `tests/golden_baselines/` está vazia.
Gatear ali seria um check fail-open dentro de um workflow fail-open. Entregue o KPI
logado, que é o que o painel lê. O secret é **owner-gated**.

**3. O RV8-05b era pior que `warn`: era inerte.** O check decidia por
`git diff --name-only HEAD`, e o job de lint roda `pre-commit --all-files` sobre árvore
limpa — **0 paths, retorno imediato**. Ele só existia no pre-commit local do commit
exato que tocasse o schema. Promover `warn`→`fail` sem mover o baseline para a base de
merge teria produzido um gate igualmente cego, agora com aparência de rigor.

**4. O joelho de `max_bytes` não é constante — ele anda com o manifest.** 2400 dava
86,1% com 36 folhas visíveis; a projeção do RV8-05 levou a 37 e derrubou para **81,1%**.
Re-medido, 2600 devolve 86,5%. A armadilha do §Armadilhas ("re-meça antes de escolher")
disparou dentro da própria lane.

**5. `'desconhecida'` estava certo, mas a regra não é a palavra — é a posição.** Varri
o E5 real: `faixa_etaria="desconhecida"`, `status_contrato="desconhecido"` e
`classes[].status="indisponivel"` ocupam o **lugar** do dado. Já
`categoria="nao_identificado"` (balde real de despesa), `motivo="saldo_desconhecido"` e
`autoridade="sem_match"` **são** o dado, e ficaram fora de propósito — incluí-los faria
o erro simétrico, manter pedido que é espúrio.

### O §Critério, aferido no payload real (não em unit test)

Replay do `_meta.field_request_audit` do r8 contra o código novo e o catálogo renderizado
do mesmo E5:

| pedido | estado no E5 | no catálogo? | antes | depois |
|---|---|---|---|---|
| `$.composicao_familiar.membros[2].faixa_etaria` | `empty` (sentinela) | não | `spurious` | `None` — **mantido** |
| `$.passive_income.renda_passiva_mensal_brl` | `present` | **não** | `spurious` | `out_of_catalog` — **mantido** |

`field_requests_spurious`: **2 → 0**, e os dois pedidos **reaparecem no output do
usuário**. Um por cada mecanismo que a lane diagnosticou — sentinela de domínio ausente
e universo trocado —, o que confirma que os dois fixes são independentes e ambos
necessários. Note que `renda_passiva_mensal_brl` segue fora do catálogo mesmo após o
RV8-07: `out_of_catalog` é a classificação **correta** ali, não um contorno.

### Nenhum limiar novo foi inventado

Os hints do manifest **consomem** vereditos que já existiam e que o parecer não recebia:
`diagnostico_confianca.nivel` é da [[ADR-353]] (`parcial` >10%, `insuficiente` >30%) e
`guarda_de_sinal.motivo_supressao` é da [[ADR-394]] §Emenda. No run r8 o nível estava em
**`insuficiente`** (30,7% de despesa não identificada) e o parecer prescrevia sem saber.

**Errei essa citação e corrigi antes do merge.** O hint dizia [[ADR-400]], que governa o
`motivo_supressao` de `$.goals.alocacao_alvo.derived` — **mesmo nome de campo, outro
campo, outra regra**. O gate de ADR em prosa verifica que o número existe, não que é o
certo, então nada reprovou. O comentário do bloco agora nomeia os dois lado a lado.

### A armadilha central não foi fechada — foi nomeada

O snapshot que gateia **segue otimista**: 92,9% no corpus sintético contra 86,5% em
produção (antes do fix: 39,3% contra 0%). A causa é cardinalidade — onde produção tem
**31** linhas de endividamento e **28** de reserva, o corpus tem **2** e **4**, e são as
duas raízes que consomem o catálogo. O colapso de produção é irreproduzível ali.

Rebaselinar sem registrar isso re-certificaria a cegueira, então o `_comment` do snapshot
passou a carregar os dois números lado a lado. Pior: **subir o orçamento encolheu o sinal
do corpus sintético**. Reverter a semente vale 86,5pp em produção e apenas 7,2pp no
sintético sob `max_bytes` 2400 — valia 53,6pp sob 1600. O mecanismo segue gateado por
diff de conjunto e por `test_semente_ocupa_o_prefixo_do_catalogo`; o percentual é que
ficou cego. **Corpus com cardinalidade real segue aberto** — [[A40.l85]].

### Residuais nomeados

1. **Duas fontes decidem "isto é dinheiro?"** — o `format: brl` declarado no manifest e
   o palpite por nome de `_MONEY_KEY_TOKENS`. Discordaram em 3 campos medidos:
   `investimentos_nao_atribuidos` (resolvido adicionando o token, raio medido de +6
   entries, todas monetárias), `transferencia_patrimonial` e `teto_sugerido` (seguem
   inancoráveis). O fix de fundo é proveniência, não mais tokens — [[A40.l86]].
   ⚠️ **Anotação 2026-08-30:** `teto_sugerido` foi extinto do contrato ([[ADR-422]] D2 ·
   #1828), então o resíduo que a [[A40.l86]] herda é só `transferencia_patrimonial`. A
   medição acima é datada e fica como está.
2. **`_MAX_LIST_ITEMS=5` vs `max_rows=10`** — 3 linhas de `tabela_classes` visíveis sem
   rota por *ranking*, não por bytes. Já documentado em
   `parecer_ancorabilidade.py`; nenhum ajuste de orçamento alcança.
3. **84 folhas do E5 fora do manifest** — débito herdado (eram 92 antes de o RV8-05
   projetar os campos de incerteza). Sai como contagem no gate novo em vez de virar
   allowlist, que seria carimbada de uma vez.

### Achado do closeout: a [[ADR-353]] está `Proposto` e esta lane ampliou o raio dela

`status: Proposto` desde 2026-07-27, mas o código está **vivo em produção** —
`NAO_IDENTIFICADO_PARCIAL_PCT = 10.0` e `NAO_IDENTIFICADO_INSUFICIENTE_PCT = 30.0`
governam `_apply_confianca_gate` e o campo `diagnostico_confianca` que o E5 publica.

Até esta lane, o consumidor era só o diagnóstico comportamental. Agora o **parecer**
também consome o veredito: o `narrative_hint` do bloco de incerteza manda condicionar
toda prescrição a `diagnostico_confianca.nivel`, e um teste
(`tests/test_parecer_projecao_incerteza.py`) trava essa dependência.

**Não flipei o status** — os critérios de aceite da ADR-353 são do dono dela, e afirmar
que foram cumpridos seria exatamente a inferência que este closeout existe para pegar.
Fica nomeado: decisão shipada e agora load-bearing para duas superfícies, declarada
como proposta.

### Prova de fecho (predicado do r9)

Mantido como o §Critério define, e agora aferível: parecer com ≥1 ressalva em item de
tema `Alocação`; ancorabilidade sobre E5 real acima do piso (**86,5%** na entrega); e
`itens_sem_ancora` presente na telemetria — que passou a existir no KPI logado.
