---
type: moc
title: REPORT-REVIEWS-active — Rastreamento de revisões do relatório entregue
aliases: ["REPORT-REVIEWS", "REPORT-REVIEWS-active", "report-review-registry"]
---

# REPORT-REVIEWS-active — Rastreamento de revisões do relatório entregue

> **Editorial.** Curado manualmente — **não é gerado**. Registro durável dos
> achados **sistêmicos/defeito** da skill `report-review`, que julga o
> **relatório já entregue** sob rubrica de produto. Cita [[ADR-343]] para a
> disciplina de estado durável (sistêmico no git · instância off-git).
> Uma seção por rodada; rodadas 100% fechadas viram histórico aqui mesmo.

> **Numeração:** começa em `r3` — a 1ª rodada nasceu na
> [[PIPELINE-REVIEWS-active]] e foi **movida sem renumerar**, porque os códigos
> `RV3-*` já são identificadores duráveis citados em commit e trilha de owner.

## O que entra aqui (e o que NÃO entra) — [[ADR-343]]

- ✅ **Sistêmico / defeito** — afirmação sobre o **produto** (contrato do
  view-model, renderer, manifest do parecer, layout, copy, regra de domínio).
  Recorre entre rodadas e é **PII-free por construção**. Ex.: "componente lê
  `a.B` maiúsculo, payload emite `a.b` minúsculo como string". **Entra aqui**,
  keyed por `(dimensão, evidência-âncora, regra)` — âncora = `campo.dot.path` ou
  `arquivo:linha`, **nunca** um valor.
- ❌ **Instância / dado** — afirmação sobre os números **deste workspace neste
  report** (carrega PII, não recorre). **Fica off-git** em
  `storage/<uuid>/reviews/<data>-<run8>/`.

**Commit-safe:** zero literal monetário, zero nome próprio. O título do achado
tem de ser um **defeito**, não um dado. Discriminador de workspace na seção =
`ws-<uuid8>`.

## Fronteira com os registros vizinhos

| Registro | O que rastreia |
|---|---|
| **Este** | Mérito do **relatório entregue** para a família (rubrica de produto) |
| [[PIPELINE-REVIEWS-active]] | Saúde de **execução** de um run disparado |
| [[LEDGER-CERTIFY-active]] | Perda/dupla-contagem no razão E3+E4 |
| [[PARSE-CERTIFY-active]] | Perda/corrupção na ingestão E0→E2 |

Achado que pertence a um vizinho **vai para o MOC do vizinho**, não para este.
A cadência anti-zumbi não cruza registros.

## Namespace de código

Códigos `RV*` anteriores à rodada unificada `U1` são **ambíguos** entre este
registro e {vizinho}: `RV4-08` nomeia defeitos distintos nos dois, e o §r4 do
[[REPORT-REVIEWS-active]] já cita um `RV5-02` que mora no vizinho. Cite sempre
**qualificado** — `RV4-08 (PIPELINE §r4)` — porque o par `(registro, rodada)`
desambigua.

A ambiguidade é inofensiva e **não se conserta renomeando**: o dedup deste registro
é `(dimensão, evidência-âncora, regra)` e nunca dependeu do código, e os códigos são
identificadores duráveis já citados em commit e trilha de owner.

A partir de `U1` o prefixo é o do **registro de destino** — `LC*` razão · `PV*`
execução · `RR*` produto ([[ADR-416]] D3), com o procedimento em
[runbook-unified-certify-review](../reference/runbooks/unified_certify_review.md).

## Convenção de rastreamento (timeless)

1. **Cobertura 100%.** Cada rodada cobre **todos** os achados sistêmicos —
   inclusive refutados, inertes e não-acionáveis.
2. **Achado inerte é estado, não veredito.** Defeito real que não alcança o
   usuário nesta configuração não entra na fila de prioridade, mas **é
   reavaliado** quando o achado que o torna inerte fechar.
3. **Aberto exige gatilho.** `procede-aberto` **deve** ter prioridade (P0-P3) +
   owner + link para lane ou ADR `Proposto`.
4. **Débito de método é entregável.** Cada rodada registra os furos do próprio
   processo (Passo 6 da skill) — é o insumo mais reusável que ela produz.
5. **Número medido traz caminho de re-medição.** Toda afirmação numérica de
   **instância** (medida de um run/corpus — não derivável do repo com `rg`/`ls`)
   citada em doc canônico traz, **na primeira menção de cada documento**, um de
   três: (a) o path off-git **mascarado** (`storage/<uuid>/…`), (b) o comando que
   a re-mede, ou (c) wikilink para o registro que traz (a) ou (b). O escape (c)
   existe para o número não obrigar N edições em N documentos — o custo cai sobre
   o **produtor** do número, e é uma linha. Vale para qualquer skill de
   certificação, não só a `report-review`. **Não** vale para contagem derivável do
   vault (nº de lanes, de testes, de ADRs): essas se re-medem com `rg`. **Sem
   gate** — é convenção no olho do revisor, mesma família da lição da emenda da
   [[ADR-111]] (*afirmação de audit sem gate é dívida*). Se um 2º registro
   precisar da mesma cláusula, ela **migra para ADR** em vez de ser copiada nos 4
   MOCs. (Origem: [[A40]] §Pendência de decisão nº 8, 2026-08-05.)

## Formato de seção

```
## rN — ws-<uuid8>-<AAAA-MM-DD>

> Objeto: report <id8> sobre run <run8> (pré-existente) · lentes: <n> + braço cego
> · clusters <n> · céticos <n> (<C>/<P>/<R>) · crítico de completude: sim/não.
> Cru + síntese com valores: storage/<uuid>/reviews/ (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
```

Colunas: **Dimensão** ∈ correção · consistência · completude · clareza-ux ·
solidez-financeira · qualidade-llm · saúde-execução. **Trilha** = lane do
BACKLOG, ADR de veredito, ou commit que fechou.

---

## r3 — ws-1b9f2cf5-2026-07-29

> **Revisão de relatório**, não execução de pipeline ([[ADR-343]]) · report `7a7e9333`
> sobre run `573a54a7` (pré-existente, tier premium) · código `origin/main` **#1111**.
> Nenhum stage foi re-executado; o objeto é o **artefato entregue** (view-model E5 +
> parecer + renderer). Julgamento: 6 lentes especializadas em paralelo + 1 lente de
> design + **braço cego** (leu só os dados determinísticos, sem ver o parecer, para
> testar convergência da recomendação nº 1). 188 achados brutos → 36 clusters + 23 de
> design → **verificação adversarial de 44 céticos** (7 CONFIRMADO, 37 PARCIAL, 0
> REFUTADO) + **crítico de completude** que auditou o próprio processo.
> Fechamento determinístico: `dev/certify_ledger_local.py` (conservação tol-zero,
> 105/105 — re-medível com `python3 dev/certify_ledger_local.py <workspace> --run
> 573a54a7…`; síntese congelada do run em
> `storage/<uuid>/ledger_certify/20260731T012427Z-573a54a7/synthesis.md`, off-git
> por [[ADR-343]]) + medição própria de duplicação cross-grupo.
> Cru + síntese com valores: `storage/1b9f2cf5-…/reviews/2026-07-29-573a54a7/` (off-git).
>
> **Correção de âncora (2026-07-30, painel A40):** o mecanismo original do RV3-01 citava caixa de
> `banco` como carrier. Está errado — `normalize_banco` (`_tx_identity.py:75`) já faz lowercase +
> strip-accents **antes** do hash, em v1 e v2. Os carriers reais são `tipo_conta` (vocabulário) e
> `titular` vazio. A duplicação medida **não muda**; a causa sim. Sem a correção, a lane shiparia
> um no-op e fecharia verde.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV3-01 — dupla contagem cross-grupo no razão E4: `tipo_conta` com vocabulário divergente (`extrato` vs `extratoconta`, que `normalize_tipo_conta` não colapsa) + `titular` vazio numa das pernas ⇒ `transaction_hash` divergente fura o dedup K4; mesmo lançamento entra por dois grupos-fonte | correção | Crítico | P0 | procede (medido) | procede-aberto | owner: data-engineer · [[A40.l2]] · [[ADR-354]] |
| RV3-02 — `fluxo_caixa.janela_12m.*` tem **zero consumidores** em `frontend/src`; todo número de fluxo na tela/PDF vem do bloco de janela `full` (`FluxoMensalChart.tsx:82,92`, `conclusionUtils.ts:109`) enquanto o valor canônico de 12m existe no payload | consistência | Alto | P0 | procede (causa-raiz) | procede-aberto | owner: senior-cto · absorve RV3-16/RV3-17 |
| RV3-03 — `SectionSummary.tsx:23` lê `narrativas[<ID maiúsculo>]`; builder emite `narrativas.summaries.<id minúsculo>` como **string** (componente espera objeto) ⇒ 16/16 parágrafos de abertura não renderizam; gate CV9 verde mede geração, não entrega | completude | Alto | P0 | procede | procede-aberto | owner: senior-cto · lane a abrir |
| ~~RV3-04~~ — `S_PROTECAO` `enabled: false` (`report_layout.yaml`) com componente entregue e testado + ausente de `MIGRATED_SECTIONS`; `buildNavGroups`/`tocGroups` em `ReportShell.tsx:107-126,187-207` não filtram `enabled` ⇒ âncora de nav sem alvo em 100% dos relatórios | completude | Alto | P1 | procede | **fechado** | **FECHADO** 2026-08-08 — #1337 (`ed7b1dc4`, [[A40.l7]]): nav/ToC filtram `enabled` e `validate_nav_targets` (no codegen, antes de emitir) barra os dois sentidos. Decisão de produto: entrada de nav removida, seção segue desligada — ligar publicaria ausência de cobertura falsa. Achado extra: a âncora entregava **copy** (título da seção) no drawer mobile |
| RV3-05 — `S9RiscosSection.tsx:87` colapsa a seção inteira por `narrativas.charts.bubble_riscos.data_state=="empty"`, imprimindo antes a linha-promessa de `conclusionUtils.ts:204`; `ParecerRisksTable.tsx:139` emite `§<section_id>` como texto puro ⇒ ponteiro do parecer leva a seção vazia | clareza-ux | Alto | P1 | procede | procede-aberto | owner: product-designer · lane a abrir |
| RV3-06 — descrição cartorial crua do IRPF interpolada verbatim em `RealEstateYieldCard.tsx:194,303,373` e `EndividamentoCard.tsx:75` (CPF de terceiro, matrícula, inscrição municipal, endereço) sem gate de PII no view-model; [[ADR-337]] é escopada a `top_ativos[].nome` | correção | Alto | P1 | procede | **fechado** | owner: data-engineer+sre · **estreitado 2026-08-24** ([[A40.l6]] §Ataque A1-A2): a instância nomeada e o "critério 4 inexistente" **caducaram** — o #1569 (`dfd561b9`) tirou `descricao` crua do card e a [[ADR-337]] tem `amended_at: ["2026-08-19"]`. O residual **não** é o que esta célula descreve: `endereco_canonical` (= `canonicalize(descricao)`, cascata que devolve `mat:<matrícula>`/`iptu:<inscrição>`) é o que o card renderiza, **não** é redigido por `redact_cartorial` e **não** está em `DESCRIPTION_KEYS`. Medido: a mesma string dá 4 hits em `descricao` e **0** em `endereco_canonical`; nas 6 fixtures e2e do repo o gate diz 0 e a sonda com o campo diz **4**. Some-se `scan_view_model_pii` **sem chamador**. Dono segue a [[A40.l6]]. **FECHADO 2026-08-24** ([[A40.l6]] §Fecho): o gate passa a varrer o VALOR (toda string), não o nome do campo; `endereco_display` só publica canonical que passa nele; `imobiliaria_cnpj` sai do payload; `get_report_data` redige na LEITURA (alcança artefato já gravado); 3 chamadores — payload produzido, lint público (2 waivers queimados) e spec renderizada em DOM + PDF. [[ADR-337]] §Emenda 2026-08-24 |
| RV3-07 — ordenação do plano sem critério encodado: maior alavanca declarada (regime PJ / anexo) bloqueada por `tributario.regime=None`+`motivo_nao_suportado="perfil_incompleto"` e **sem pendência acionável** que peça regime/CNAE/pró-labore | solidez-financeira | Alto | P1 | **procede-parcial** (2026-08-05, [[A40.l10]]) | procede-aberto | owner: financial-planner+product-manager · absorve achado órfão FP-21. **Duas sub-claims medidas:** (a) "sem pendência acionável" é **impreciso** — `CascataFiscalCard.states.tsx::PerfilPendenteState` renderiza um empty state que nomeia os 4 campos que faltam e diz a quem pedir; o que falta é **âncora e posição no plano**, não superfície. (b) "nenhum critério de ordenação encodado" **erra o alvo**: a fila de `Decision` tem critério em SQL ([[ADR-179]], `_top5_decisions_stmt`) — que degenera para ordem de criação, ver [[ADR-179]] §Emenda 2026-08-05 — enquanto o ranking **sem** critério é o de `pontos_urgentes_analyzer`, que é a ordem literal dos `out.append`. Segue aberto sobre (b) |
| RV3-08 — nenhum dos paths do manifest do parecer toca `$.real_estate`/`$.tributario`; a mesma `section_whitelist` gateia `get_e5_section` e `planner_drill_down.py:145` ⇒ dado renderizado na tela é inalcançável pela narrativa LLM | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: prompt-engineer · gate próprio já emite WARNING com EXIT=0 |
| ~~RV3-09~~ — `suggestion_rules.py:123` lê `meses_cobertura`; E5 emite `reserva_emergencia.cobertura_meses` ⇒ regra inerte. 10/10 regras retornam vazio neste payload (demais por campos de [[ADR-161]] latentes) | completude | Alto | P2 | procede | **fechado** | **FECHADO** 2026-08-08 — #1336 (`845a4041`, [[A40.l5]]): passou a ler `cobertura_meses`. Sub-claim "família não é alertada" segue **refutado**. Achado que o registro não tinha: os 3 testes da regra **passavam** porque a fixture repetia a chave errada do código — teste novo é alimentado pelo produtor (snapshot de dogfood); mutação derruba 7, antes derrubava 0 |
| RV3-10 — `dependentes_menores_18` como `rationale` de gap de proteção contra `irpf_kpis.dependentes.count=0`: premissa da recomendação nº 1 contestada dentro do próprio payload | consistência | Alto | P2 | **refutado** (2026-08-05, [[A40.l10]]) | não-acionável | as duas contagens medem **populações diferentes** e divergir é legítimo: `protecao_wiring.py::_snapshot_membro` deriva `is_dependente` do cadastro da família (`papel ∉ {titular, conjuge}` + idade de `data_nascimento`), `irpf_analyzer.py::dependentes_count` conta a ficha da declaração do ano-base ([[ADR-305]]: último ano **completo**, defasado 1-2 anos). Divergem nos 2 sentidos sem erro: filho nascido após o ano-base, declarado pelo outro genitor, modelo simplificado; e `RelacaoDependente` inclui `conjuge_companheiro`/`pai_mae`/`sogro_sogra`, que no cadastro **não** são dependentes. Tratar `count == 0` como refutação encodaria regra falsa e alarmaria toda família com filho pequeno. **Substituído em escopo** por [[A40.l10]] §Correção de premissa: taxonomia por proveniência da premissa |
| RV3-11 — `tributario` materializado em `build_config_overrides_from_db`→`_setup_run_context` no início do run, com `_latest_run_id` resolvendo para o run corrente cujo E4 ainda não existe ⇒ todo input run-scoped zerado; regen não corrige | correção | Alto | P2 | procede | procede-aberto | RV2-18 **FU-2 medido** (rótulo "FIXADO" era falso) |
| ~~RV3-12~~ — `EndividamentoCard.tsx:77,80` lê `d.valor`/`d.taxa`; contrato E5 emite `saldo_devedor`/`taxa_juros`/`parcela_mensal` sem adapter no boundary | consistência | Alto | P2 | procede | **fechado** | **FECHADO** 2026-08-08 — #1336 (`845a4041`, [[A40.l5]]): card lê `saldo_devedor`/`taxa_juros` e o tipo espelha o schema E5. A causa não era o arquivo ser escrito à mão: era `[key: string]: unknown` em `dividas[]`, que fazia o `tsc` aceitar qualquer nome — removida, as 2 fixturas do critério viram erro de compilação. As **3** index signatures restantes do arquivo seguem abertas na [[A40.l5]] |
| RV3-13 — `diagnostico_confianca` é a única chave top-level do view-model com **zero consumidores**; `dataQualitySignals.ts:54-67` recomputa o share no cliente sobre outra janela ⇒ três percentuais para o mesmo conceito na mesma tela | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer · [[ADR-353]] degrada mas não surfaça |
| RV3-14 — prazo de IF impresso como fato (`HeroKpiGrid.tsx:266-271`, `Stat "Ano projetado"`) com `if_monte_carlo.prob_if_ate_prazo_declarado` e divergência vs `ano_if_cenario_central` só em `text-xs` (chaves renomeadas na [[ADR-369]], 2026-08-07 — a probabilidade passou a medir o prazo declarado pela família; o achado de UX permanece aberto) | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer+financial-planner |
| ~~RV3-15~~ — `ParecerRisksTable.tsx:41,93`: `TOP_LIMIT` fixo com rótulo hardcoded "de baixa severidade" para o resto, enquanto a composição real do `extra` inclui severidade média | clareza-ux | Médio | P3 | procede | **fechado** | **FECHADO** 2026-08-10 — #1355 (`15e373da`, [[A40.l7]]): Crítica/Alta nunca colapsam e o rótulo deriva da composição real do conjunto escondido. ⚠️ **A nota anterior deste achado — *"print CSS já força expansão no PDF"* — era FALSA:** `SParecer.print.css:19-22` tem `details.parecer-details > summary { display: none }` no `@media print`, ou seja o rótulo **não existe** no PDF. O dano era na tela (o leitor lê "baixa", não expande, e não lê uma Crítica). Achado extra do mesmo PR: a caption `Mostrando 5 de 8 riscos` **essa sim** mentia no PDF, acima das 8 linhas impressas — corrigida junto |
| RV3-16 — `FluxoMensalChart.tsx:76-88` `buildContext` declara a janela do slice e cita agregado de janela `full`; substitui `narrativas.charts.fluxo_mensal.context` | consistência | Alto | P1 | procede | procede-fechado-em | sintoma de **RV3-02** |
| RV3-17 — `ConsumoConscienteCard.tsx:45` exibe `consumo_consciente.total_pontuais` (janela `full`) em bloco que declara 12m; `total_pontuais_janela` tem 0 hits em `frontend/src`; `consumo.analise` emitida como string pré-formatada en-US | consistência | Alto | P2 | procede | procede-fechado-em | sintoma de **RV3-02** + string formatada no E5 |
| RV3-18 — mesma matrícula com `property_id` distintos ⇒ lista de excluídos repete o mesmo imóvel; banner conta registros, não imóveis | consistência | Alto | P2 | procede | procede-aberto | JÁ-CONHECIDO **RV2-13** ([[ADR-246]]) · [[TRACK-property-identity-cross-era]] · [[ADR-385]] |
| RV3-19 — `Metrica` (schema do parecer) sem campo `ancoras`; `_iter_items`/`stamp_ancora_values` cobrem riscos+horizontes ⇒ `valor_atual` é o único número autorado pelo LLM sem verify | qualidade-llm | Alto | P1 | procede | procede-aberto | JÁ-CONHECIDO **RV2-01** · 10/10 valores deste run re-derivados e **conferem** (zero fabricação realizada) |
| RV3-20 — `aporte_investimento` vazio na janela ⇒ mecanismo `despesa_consumo = total − aporte` no-op e `despesa_consumo == despesa_total` | solidez-financeira | Alto | P1 | procede | procede-aberto | JÁ-CONHECIDO **LC04-r3** · ver [[ADR-333]] |
| RV3-21 — `nao_identificado` por **valor** cruza o limiar de degradação na janela de 12m (maior que na janela `full`) | solidez-financeira | Alto | P2 | procede (medição) | procede-aberto | MEDIÇÃO de **LC05-r3** · [[ADR-353]] degrada, não bloqueia |
| RV3-22 — `ratios.*_pct` como string onde consumidores fazem aritmética (`conclusionUtils.ts:135-142` cai em fallback por `typeof !== "number"`) | consistência | Médio | P2 | procede | procede-aberto | JÁ-CONHECIDO **RV2-06** ([[ADR-090]]) |
| RV3-23 — KPIs do hero não passam por `<MonetaryValue/>` (`HeroKpiGrid.tsx:323-331` devolve string; `ui/Kpi.tsx:76-86` sem `tabular-nums`); definição do KPI protagonista só em `title` de `<span>` não-focável | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer · viola §Design System do CLAUDE.md + A11Y_CHECKLIST 4.1.2 |
| RV3-24 — jargão de implementação no bloco de premissas (`ReportPremissasBlock.tsx:97-104`: "snapshot E5", endpoint, hash de integridade) contra `COPY_GUIDELINES.md:263-280` | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer |
| RV3-25 — abreviação `k`/`M` em valor monetário (`ReceitaDespesaMensalChart.tsx:216-220`; narrativa E5.N verbatim em `PerfilFamiliaCard.tsx:29-30`) contra `COPY_GUIDELINES.md:196-197` (`mil`/`mi`/`bi`) | clareza-ux | Baixo | P3 | procede | procede-aberto | owner: prompt-engineer (fonte) + product-designer (render) |
| RV3-26 — `S7IndependenciaSection.tsx:96` lê `goals.trs_pct` (inexistente no payload; chave real `goals.if_trs`) e cai em default hardcoded que também alimenta o tone do KPI | correção | Médio | P2 | procede (latente) | procede-aberto | owner: senior-cto · coincide hoje, mente se o dono configurar outro alvo |
| RV3-27 — `real_estate.imoveis[].valor_imovel` zero tratado como valor real no render (`RealEstateYieldCard.tsx:202`) contra `COPY_GUIDELINES.md:199-207` (ausência ⇒ `—`) | clareza-ux | Médio | P3 | procede | procede-aberto | owner: data-engineer (origem do zero) · **perna de `product-designer` fechada 2026-08-24** — #1569 shipou `valorApurado` (`0` ⇒ `—`, `imovelDisplay.ts`) com teste. A perna **viva** é a origem do zero: a [[ADR-385]] segue `Proposto`, então a linha fantasma virou `—` com o override preso vivo — exatamente o cenário que a [[A40.l6]] §Problema previu ([[A40.l6]] §Ataque A10). **A l6 fechou 2026-08-24 declarando esta perna fora do seu escopo** (§Fecho): ela depende da [[ADR-385]] sair de `Proposto`, e decidi-la de passagem é o que o §Problema alerta. Owner segue `data-engineer`, sem lane — candidata a sucessora |
| RV3-28 — ponteiros `section_id` do parecer apontam seções que não hospedam o card citado; **o mapa de referência é ele mesmo incoerente** (`report_layout.yaml:356` titula S8 por um domínio cujo card vive em S7) | consistência | Médio | P2 | procede (reenquadrado) | procede-aberto | severidade Alto original presumia ponteiro navegável (é texto puro). **Parcialmente endereçado** 2026-08-10 — #1355 ([[A40.l7]]) fechou a incoerência de **título** (heading e índice passam a derivar do YAML; APP_B/APP_D/S9 retitulados). **Segue aberto o núcleo:** re-medido em 2026-08-10, `S8` é `"Previdência — PGBL e Fiscalidade"` com `cards: []`, enquanto `previdencia_pgbl` está declarado sob `S7` e renderiza em `S7IndependenciaSection.tsx:103` — a seção titulada pelo domínio não hospeda o card. Dono: [[A40.l7]] (§Escopo "validador de hospedagem de componente") |
| RV3-29 — base do rebalanceamento (`goals.alocacao_alvo.derived.carteira_liquida_brl`) difere de 4 outras bases patrimoniais do payload sem rótulo que declare o escopo | clareza-ux | Médio | P2 | procede (rebaixado) | procede-aberto | rebaixado pelo crítico: são **5** bases, e o delta é escopo deliberado (reserva/ilíquido fora), não dinheiro ignorado |
| RV3-30 — conversões de câmbio aparecem em `nao_identificado` e novamente como receita na moeda destino | correção | Médio | P2 | procede | procede-aberto | owner: data-engineer · faceta de RV3-01 |
| RV3-31 — duas taxas de retirada (yield-alvo na meta vs SWR na estimativa) | solidez-financeira | Baixo | P3 | **refutado** | não-acionável | decisão explícita: [[ADR-191]] §Emenda 2026-07-15 + `FORMULAS.md:94` "nunca colapsar"; aceite cumprido nas 2 superfícies |
| RV3-32 — `pipeline_run_costs` órfã (SSOT é `llm_call_log`) | saúde-execução | Baixo | P3 | procede (higiene) | procede-aberto | JÁ-CONHECIDO **RV2-22** |
| RV3-33 — achados **inertes** (defeito real sem alcance ao usuário nesta config): ranking de despesa na narrativa (não renderiza por RV3-03), `alertas[]` dead-field, e 5 correlatos — **os 7 deixam de ser inertes no instante em que [[A40.l4]] mergeia** | — | (intrínseca de cada um) | P2 | procede-bloqueado | procede-aberto · `depends_on: A40.l4` | owner: product-designer · re-triagem item-a-item é critério de aceite bloqueante da [[A40.l4]], não follow-up |

**Residual pós-r3, achado ao executar a [[A40.l4]] (2026-08-05):** "Base da
cascata" — `tributario_input_builder` usa `receita_bruta = receita_pj_anual` (a
anualização do input do wizard) em vez de
`FinanceiroPJSnapshot.receita_bruta_total_anual` ([[ADR-238]], já passthrough e não
usada). Confirmado por leitura de código; **materialidade não medida**. Não é RV3-xx
(não fazia parte dos 188 achados brutos da r3) e não tem dono vivo: o arquivo é da
[[A40.l9]] (`shipped`) e [[PLAN-tributario-pj]] está `done`. Disposição: entra na
próxima re-triagem (r4) com uma medição de entrada — delta entre `receita_pj_anual`
e `receita_bruta_total_anual` no corpus dogfood. Delta material ⇒ abre lane com
emenda a ADR-236/238 antes de qualquer código (mudança de cálculo). Delta imaterial
⇒ `aceito-wontfix`. Ver [[A40]] §Fora do sprint e §Pendências de decisão nº 11.

**Positivos verificados:** conservação do razão fecha em tol-zero (105/105 grupos-fonte,
baldes `despesas`/`receitas` fechando em cents); zero-write do harness confirmado;
`PremissasFallbackAlert` dispara corretamente quando as premissas são parciais;
`formatProbability` evita 0%/100% enganosos; card de rentabilidade rotula desvio vs meta
com variante crítica correta (hipótese de "vender ok ao usuário" **refutada**);
apêndice sem dado é omitido em vez de renderizar vazio.

**Débito de método desta rodada** (o crítico de completude auditou o processo e achou
três furos que valem mais que vários achados):
1. **A lente de design não entrou no circuito de clusterização/ceticismo** na primeira
   passagem — a dimensão `clareza-ux` ficou com zero cobertura verificada até uma
   passagem cética dedicada ser rodada depois. Gate para a próxima: conferir que o campo
   `lentes` dos clusters cobre o conjunto de lentes executadas.
2. **O merge vazou 96 dos 188 achados de lente** (21 vivos órfãos, 5 deles Alto). Exigir
   disposição explícita por achado antes de fechar a etapa de clusterização.
3. **Zero REFUTADO em 36 clusters** — calibração frouxa do passo cético (tudo virou
   PARCIAL com severidade rebaixada). As refutações reais vieram do crítico e da medição
   determinística, não dos céticos.
4. **Conservação por grupo não detecta duplicação entre grupos** — este run passa em
   tol-zero com duplicação material (RV3-01). `ledger-certify` precisa de check
   cross-grupo por `(data, valor, descrição-normalizada, contraparte)`.
5. **Ninguém renderizou tela nem PDF** — toda afirmação de `clareza-ux` é inferência de
   código cruzada com payload, e está rotulada como tal.

## r4 — ws-1b9f2cf5-2026-08-11

> Objeto: report `7a7d7115` sobre run `ee124571` (pré-existente, tier premium) ·
> código `origin/main` **#1377**; captura de render sob o SHA do checkout de
> execução, 6 commits atrás (gap medido: não toca as linhas citadas em
> `clareza-ux`, ver §Débito de método) · lentes: 5 + braço cego · clusters: 7 ·
> céticos: 7 (**2 CONFIRMADO / 3 PARCIAL / 3 REFUTADO**) · crítico de completude: sim.
> Fechamento determinístico: 7 medições próprias do loop, das quais duas
> **derrubaram achados do próprio loop** (a causalidade do RV4-01 estava invertida
> na primeira passagem; a tabela de perda por truncagem estava errada por
> conflação de janelas).
> Disparada por report de uso: o card de receita por fonte parecia subcontar. **Procede.**
> Cru + síntese com valores + render: `storage/<uuid>/reviews/<data>-<run8>/` (off-git).
> Re-medição dos números de instância: scripts em `scratchpad/` do round folder.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| ~~RV4-01~~ — âncora da janela interativa derivada do **último label da série mensal** (`S1PatrimonioSection.tsx:57-58` via `parseChartMonthLabel`); lançamento com data futura estica a série além do mês corrente e a janela de média passa a cair sobre meses sem atividade. **Contrafactual medido: consertar só a âncora fecha 100% do gap** | correção | Crítico | P0 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-12 — #1396 (`f1cad2e4`, [[A40.l44]] PR1): corte no produtor + `fluxo_caixa.data_corte`; âncora do cliente lê o corte. Contrafactual medido antes: só a âncora fecha 100% do gap |
| ~~RV4-02~~ — o cliente é um **segundo motor de agregação**: `periodUtils.ts` re-deriva os três insumos de qualquer agregado (substrato via `GET /transactions`, predicado via `isIncomeCategory:106`, denominador via `getPeriodMonths:83`). Número nascido no cliente é **inauditável por construção** — fora de `explain_number`, `_lineage`, golden de execução, snapshot do view-model e verificação de ancorabilidade | consistência | Crítico | P0 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-14 — #1456 (`5194115a`, [[A40.l44]] PR5): o relatório seleciona `janelas[period]`; `rg usePeriodTransactions frontend/src/components/report` → 0. [[ADR-377]] `Decidido` |
| ~~RV4-03~~ — taxonomia de receita duplicada no cliente diverge do produtor: categoria de crédito fora do whitelist sai da receita **e entra no balde de despesa** (`aggregateDespesasMediaMensal` usa `!isIncomeCategory`), rendendo teto de gasto a partir de um recebimento. O comentário de cobertura em `ReceitasFonteCard.tsx:11-14` não podia ser verdadeiro: o pipeline não tem lista fechada de categorias de receita | correção | Crítico | P0 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-14 — #1456 (`5194115a`, [[A40.l44]] PR5): o predicado do cliente foi **deletado**; a taxonomia é a do produtor |
| ~~RV4-04~~ — três agregados distintos de "receita mensal" e três shares da mesma fonte convivem na mesma leitura, sem rótulo que reconcilie a base | consistência | Crítico | P0 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-14 — #1456+#1462 ([[A40.l44]] PR5+PR6): um card, um toggle, um KPI. Residual de **copy** (rótulo que reconcilie bases se "receita mensal" ainda aparecer com outra janela na mesma leitura) é achado novo — dono `product-designer`, lane a abrir. Não aponta para a l44 |
| ~~RV4-05~~ — o estado de carregamento do card de orçamento renderiza um **dataset completo alternativo** (bloco estático de janela `full`) em vez de esqueleto: `OrcamentoProspectivoCard.tsx:46-58` só aplica a guarda `anchorDate && !isLoading` depois de cair no fallback ⇒ conteúdo monetário **não-determinístico** entre superfícies do mesmo relatório | correção | Alto | P0 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-14 — #1456 (`5194115a`, [[A40.l44]] PR5): sem fetch no cliente não há loading que renderize dataset alternativo |
| ~~RV4-06~~ — denominador de mensalização é a **constante do enum do toggle**, não os meses com dado ([[ADR-306]] D3 violado no consumidor; o gate de D2 vigia só o produtor) | correção | Alto | P0 | PARCIAL — fecha 41% do gap, não é o mecanismo dominante | **fechado** | **FECHADO** 2026-08-14 — #1456 (`5194115a`, [[A40.l44]] PR5): `janela_meses` vem do payload. A causa dominante já tinha saído no #1396 |
| ~~RV4-07~~ — `page_size` no teto sem paginação; a resposta **já traz** `total` e um `summary` uncapped calculado antes do slice, e o hook descarta ambos (`usePeriodTransactions.ts:50`) ⇒ o fix mora no cliente, e o servidor já calcula o número certo | correção | Alto | P1 | PARCIAL — só janelas longas; janela default não trunca | **fechado** | **FECHADO** 2026-08-12 — #1398 (`38a7742d`, [[A40.l44]] PR2): hook devolve `isTruncated` e os 2 cards declaram degradação em vez de exibir média 42% baixa. Paginar não: é o código que o PR5 apaga |
| ~~RV4-08~~ — `fluxo_caixa.receita_por_natureza` (contrato em `config/schemas/e5_analysis.schema.json`, consumido por `parecer_ancorabilidade.py` e pelo prompt do parecer) tem **zero consumidores** em `frontend/src`; a tela re-deriva pior a mesma resposta | completude | Alto | P1 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-14 — #1462 (`8d07c4fb`, [[A40.l44]] PR6): a faixa Por tipo lê `janelas[period].tabela_receita_por_natureza_mensal`. O bloco top-level (full) não entra no toggle |
| ~~RV4-09~~ — card de exposição cambial: default do endpoint V2 (`tier = v2.data?.tier ?? "empty"`) **afirma ausência de exposição** em vez de abster-se, sobrescrevendo o bloco do E5 que classifica em faixa de atenção; o parecer prescreve sobre o valor do E5 | correção | Alto | P1 | CONFIRMADO — a hipótese de "estado vazio, não asserção" foi testada e caiu | **fechado** | **FECHADO** 2026-08-12 — #1393 (`d1b7c97c`): a raiz era o **produtor** — o endpoint V2 nasceu morto em #326 e devolvia `tier="empty"` há 3 meses; o fix distingue "sem base" de "zero medido" no DTO, tornando o zero falso infabricável no cliente |
| ~~RV4-10~~ — rodapé do card declara meses que ele não mediu (expansão do próprio toggle); não existe estado para janela **parcial**, **truncada** ou **que termina no futuro** | clareza-ux | Alto | P1 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-14 — #1456 (`5194115a`, [[A40.l44]] PR5): o rodapé imprime `janela_meses · mes_inicio — mes_fim` do payload |
| ~~RV4-11~~ — chips de evidência do parecer rotulam pelo **root do JSONPath**, então campos distintos do mesmo bloco recebem rótulo idêntico; o cross-check exige exatamente a identidade que produz o erro ⇒ verificação tautológica, todas as entradas `verified` | qualidade-llm | Alto | P1 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-17 — #1487 (`cb9253eb`, [[A40.l49]]): pairing contra `citation_labels` (rotulo_id da folha); mutação que volta ao root falha |
| RV4-12 — sugestões do parecer não alcançam o Plano de Ação: a única rota automática lê uma chave do E5 **ausente do payload**, e nunca lê `parecer.sugestoes_*`; risco de severidade alta sem item acionável em nenhum horizonte | completude | Alto | P1 | CONFIRMADO ⚠️ **re-medir** | procede-aberto | owner: prompt-engineer + product-manager · **área com dono ativo**: [[PLAN-suggestion-lifecycle]] · medido antes de #1378, que mexeu nessas superfícies |
| RV4-13 — o campo de rentabilidade guarda taxa de **retirada** efetiva e o parecer a promove a meta de **retorno**, emitindo risco de severidade alta e métrica-alvo a partir disso | solidez-financeira | Alto | P2 | CONFIRMADO | procede-aberto | owner: financial-planner · raiz determinística; nem prompt nem verificador podem detectar · [[ADR-191]] registra as duas taxas coexistirem, não a promoção · **[[A40.l47]]** (aberta 2026-08-12) |
| ~~RV4-14~~ — guardrail que rebaixa confiança sob premissa em fallback exige âncora num bloco que **nenhuma âncora do parecer toca** ⇒ cobertura zero por construção; os itens que dependem do bloco o citam em prosa, forma que o gate não lê | qualidade-llm | Médio | P2 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-17 — #1487 (`cb9253eb`, [[A40.l49]]): S7+lemma na prosa; `needs_review_triggered` espelha evidencia/red-line ([[ADR-295]]), não o 0,7 da [[ADR-081]] |
| RV4-15 — faixas do classificador comportamental no código divergem da legenda publicada no apêndice do próprio relatório; um rótulo do código não existe na legenda e uma faixa da legenda não existe no código | solidez-financeira | Médio | P2 | CONFIRMADO | procede-aberto | owner: financial-planner · **[[A40.l47]]** (aberta 2026-08-12) |
| RV4-16 — `comparisons[].direction_positive` fixo em métrica **não-monotônica** (cobertura de reserva): piorar acima do alvo renderiza com sinal de melhora, na página que classifica a mesma métrica como excessiva | consistência | Médio | P2 | CONFIRMADO | procede-aberto | owner: data-engineer · polaridade tem de derivar do alvo, não do campo · **[[A40.l48]]** (aberta 2026-08-12) |
| ~~RV4-17~~ — classificador de pedido-de-campo do LLM resolve o path e ignora a **dimensão ano**, marcando como espúrio um pedido legítimo e **deletando-o** antes de gravar | qualidade-llm | Médio | P2 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-17 — #1487 (`cb9253eb`, [[A40.l49]]): motivo que nomeia um ano sem cobertura completa no E5 deixa de ser SPURIOUS |
| RV4-18 — a composição líquida da reserva conta base maior que a carteira exibida na seção de investimentos; o acoplamento entre reduzir a classe e manter a cobertura não é divulgado | consistência | Médio | P2 | CONFIRMADO (residual de um cluster refutado) | procede-aberto | owner: financial-planner · **[[A40.l47]]** (aberta 2026-08-12) |
| ~~RV4-19~~ — separador decimal em duas convenções **na mesma tabela**: linhas usam `toFixed` (en-US) e a linha de total tem o valor pt-BR hardcoded | clareza-ux | Médio | P3 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-12 — #1403 (`e1462a5f`): os 2 cards usam o `formatPercent` existente, **inclusive no total**, para as duas pontas não divergirem de novo. Achado adjacente aberto: 3 superfícies com a mesma violação **e teste fixando a convenção errada** |
**Ordem de ataque:** RV4-01 → RV4-03 → RV4-05 → RV4-06/07 → **RV4-02** (estrutural,
absorve os anteriores e fecha RV3-02) → RV4-04/08/10. A inversão de RV4-01 e RV4-03
produz gate verde com número errado — está registrada como anti-fix nas duas linhas.

**Aberta 2026-08-11:** a [[A40.l44]] executa essa ordem em 6 PRs, sob a
**[[ADR-377]]** `Proposto` (janela interativa é conjunto fechado pré-computado; o
cliente seleciona, não recomputa) + emenda datada na [[ADR-306]] (mês documentado
exclui futuro e mês em curso). Cobre RV4-01/02/03/05/06/07/08; RV4-04 e RV4-10
ficam habilitados mas são copy/estados, com dono `product-designer` em lane
própria.

**Correção do registro na mesma data (2026-08-11):** a linha do RV4-02 citava
[[ADR-282]] — conferido, aquela ADR é sobre `natural_key` de override de
transação e não tem relação com agregação no cliente; a citação saiu da linha.

**Apêndice 2026-08-14:** a l44 `shipped` (#1462, [[ADR-377]] `Decidido`).
RV4-01/02/03/05/06/07/08/10 fechados. RV4-04 fechado no mecanismo; residual
de copy → `product-designer`, lane a abrir. RV3-02 **não** fecha aqui.

**Apêndice 2026-08-17:** a l49 `shipped` (#1487, emenda [[ADR-296]]).
RV4-11/14/17 fechados. RV5-02 (dependente fantasma) ficou fora desta lane.

**Refutados / rebaixados nesta rodada** (taxa de refutação ≠ 0 é requisito de
calibração, não acidente): projeção de IF apoiada em aporte irrealista —
**REFUTADO**, o campo comparado era outra categoria e o aporte é meta declarada
pelo dono, surfaçada como premissa; excedente de liquidez prescrito inexecutável —
**REFUTADO**, o valor não existe no artefato (era aritmética do revisor) e o
produto prescreve rebalanceamento por aporte sem vendas; cap de paginação explica
o card da janela default — **REFUTADO**, a janela não trunca; duas janelas longas
exibem número idêntico — **REFUTADO**, idêntico é o conjunto truncado, não o
número renderizado; parecer desaparece na mídia print — **PARCIAL**, é estado de
loading de fetch assíncrono e o artefato capturado é provavelmente timing do
harness.

**Q6 — direção sustentada, ordenação indeterminada.** O braço cego **divergiu** do
parecer na recomendação nº 1, e a divergência não absolve nem condena: o braço
cego é inadmissível duas vezes — dimensionou uma alavanca **contra o produtor**
(o payload declara a capacidade inexistente por regime, e a superfície imprime
"não se aplica"), e reciclou para desempate a premissa que a r3 já refutou em
RV3-10. A direção do parecer tem terceiro braço independente no bloco
determinístico de pontos urgentes. Mas a ordenação segue **indeterminada**: esse
bloco tem n=1 (não é ranking, é item único) e as sugestões do parecer não têm
critério encodado — prioridade e impacto qualitativo, sem delta esperado nem
custo. **Subproduto material:** um leitor competente do mesmo payload fabricou, na
primeira tentativa, uma dedução que o payload **suprime** — demonstração medida do
risco que a [[ADR-375]] endereça, e evidência utilizável pela [[A40.l34]].

**Positivos verificados:** CV 16/16 · as três superfícies de render geram sem
truncagem e o PDF de produção sai íntegro · `receita_por_natureza` fecha com o
total de receita ao centavo · **o parecer leu o número certo** (ancorou em campo
determinístico da janela de 12m, não no card quebrado) — para receita, o parecer é
a fonte confiável e o card é a derivação quebrada · limite previdenciário zerado
sob modelo simplificado é decisão registrada ([[ADR-305]]) com prosa que inclui o
pré-requisito · nenhuma âncora de navegação órfã · degradações de perfil
tributário e de milhas são declaradas, não silenciosas.

**Débito de método da r4:**
1. **Achados não persistidos.** Os ~86 brutos e os clusters viveram só no contexto
   do loop; 3 dos 5 gates de cobertura ficaram inauditáveis. Gravar `achados.md` +
   `clusters.md` no round folder **antes** do passo cético.
2. **Captura sob SHA diferente do citado.** O gap foi medido e não afeta as linhas
   usadas — mas isso foi sorte, não método. Capturar sob o SHA que se vai citar.
3. **Fechamento por reimplementação de lógica do cliente em outra linguagem** só
   vale com âncora externa (o valor renderizado). Predição do espelho sem
   observação é PARCIAL — foi assim que a tabela de perda por truncagem saiu
   errada. Capturar **as quatro janelas do toggle**, não só a default.
4. **Q5 medido no payload, não na superfície do agregado de decisões.** Exigir dump
   do agregado + delta explícito sugestões ↔ decisões.
5. **Braço cego sem travas.** Entregar a ele o índice de refutados da rodada
   anterior e exigir que declare **qual campo do payload autoriza o sizing**.
6. **Um cético morreu por limite de gasto de API** e seu cluster foi fechado pelo
   loop principal. Painel sem orçamento reservado perde cluster silenciosamente —
   e o loop só percebeu porque conferiu a lista de vereditos contra a de clusters.

---

## r5 — ws-1b9f2cf5-2026-08-26

> Rodada unificada **U1** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r5 · [[PIPELINE-REVIEWS-active]] §r9.
> Objeto: report `97a76360` sobre run `c97b97c2` — **produzido nesta rodada**, não pré-existente.
> Lentes: 5 + braço cego · céticos: 7 (**1 confirmado / 6 parciais / 0 refutados** — zero
> sobreviveu inteiro) · crítico de completude: sim.
> **Cobertura de `clareza-ux` observada**, não inferida: tela, print e PDF capturados.
> Cru + síntese com valores + render: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).

**Manchete: o produto gera a ressalva e a descarta na entrega.** Cinco notas metodológicas
foram produzidas e **nenhuma renderiza** — o tipo existe no frontend e nenhum componente
itera o array. Elas carregam a disclosure de incerteza inteira, incluindo a que declara o
diagnóstico patrimonial com confiança **insuficiente**. O cético refutou o "0 de 5" no
sentido estrito (uma converge com um risco que é renderizado) e manteve **Crítico**: quatro
de cinco se perdem inteiras, num run que pausou com seis avisos retidos.

**Segundo eixo: o produtor suprime o limiar e a entrega o republica.** Quatro alvos de KPI
estão suprimidos com `procedencia: null` e motivo nomeado. **Três dos quatro vazaram** — a
tabela de métricas renderizada publica alvo para dois deles, e o plano de ação renderiza uma
decisão fixando alvo pontual para exatamente a métrica que o produtor declara sem alvo
canônico.

**A rodada procede sobre 6 avisos retidos** (§[[PIPELINE-REVIEWS-active]] §r9). Toda linha de
`solidez-financeira` e as perguntas Q2/Q4/Q6 herdam a condição.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RR5-01 — `notas_metodologicas` não tem renderer: o tipo é declarado e nenhum componente itera o array; tier premium, sem truncagem no backend. A nota que declara a confiança do diagnóstico como insuficiente não alcança quem lê o diagnóstico | completude | Crítico | P0 | PARCIAL (1 de 5 converge com um risco renderizado; 4 de 5 se perdem) | **procede-fechado** ([[A40.l88]] · #1755) | `ParecerNotasMetodologicas` renderiza o array **antes** dos achados — ressalva que chega depois da conclusão já falhou. Tier free (`FREE_TIER_LIMITS.notas = 0`) recebe o contador, senão o silêncio seria o mesmo, só que por política. Gate estrutural: `check_emitter_without_reader` (`PARECER_FIELD`) |
| RR5-02 — o produtor suprime o limiar por falta de procedência, o LLM o republica como alvo, e a superfície entrega: 3 de 4 supressões vazaram para a tabela de métricas e para o plano de ação | contrato | Crítico | P0 | procede (novo — a célula que ninguém reivindicou) | procede-aberto | prosa e plano só publicam alvo cujo limiar seja não-nulo; supressão é contrato, não sugestão · **partida em 2026-08-27**: a metade `metricas[]` (write-path + read-path subtrativo) é da **[[A40.l89]]**, que declara no §Critério não alcançar as outras duas — *"o critério anterior prometia a prosa e o plano de ação, que esta lane não alcança"*; **prosa** (exec context) e **plano de ação** (`trs_target_pct`) passaram à **[[A40.l90]]** §Escopo 5-6 (#1773). Fechar RR5-02 exige as **duas** · **metade `metricas[]` ENTREGUE 2026-08-27** pela [[A40.l89]] em 3 PRs (#1770 `0f4ad12d` → #1772 `78b06986` → #1779 `4fbfb91b`): o catálogo é leitor único do alvo publicado, o modelo emite `metrica_key` e não pode emitir alvo/observado/rótulo, e o artefato congelado é coberto por supressão na leitura. **Braço da [[A40.l90]] ENTREGUE 2026-08-29** (#1815 `a272531a` + #1816 `63aed78c`), e a frase acima ficou falsa: `trs_target_pct` e `rule_trs_desalinhada` saíram **juntos** (`rg trs_target_pct pipeline/` → zero), sob emenda datada da [[ADR-191]] §D6 — cujo Aceite fechava em *"nos dois consumidores"* e este era o **terceiro**, com `section_id="S7"`: dentro do escopo declarado, fora do que ele mediu. O veredito de domínio: SWR 4% é **decumulação**, `taxa_retirada_efetiva_pct` é **yield observado** — prescrever "reduza a retirada" sobre um yield é inexecutável, a família não escolhe quanto os ativos pagam. A **prosa** (exec context) também caiu: deixou de afirmar "acima da referência de 30%", limiar que o catálogo declara órfão por rivalidade (25 vs 30, RV2-24). A linha vizinha de endividamento **fica** — fonte única — e ganhou gate de neutralidade. **RR5-02 FECHADA pelas duas metades.** |
| RR5-03 — a seção de proteção está **desligada no layout** (`enabled: false`) e a ação nº 1 do parecer é seguro de vida: o relatório não tem nenhuma superfície de cobertura de seguro | completude | Crítico | P0 | procede (novo) | **procede-fechado** ([[A40.l88]] · #1755) | ⚠️ **a disposição escrita aqui em 2026-08-26 era falsa, e a execução a corrigiu**: dizia que o componente "já tem hide-when-empty (`return null`)". Não tem — `readProtecaoPatrimonial` é guarda de **shape**, e `compute_protecao` devolve o bloco **completo** para workspace sem apólice (medido 2026-08-27: 11 chaves, prêmio `"0.00"`, `saude` acesa). Ligar só a flag publicaria a seção zerada, com veredito "Atenção", para todo cliente sem apólice — a objeção da [[A40.l7]] estava **certa no mérito** e errou só o campo que citou (`protection_bundle` é da S9). Entregue com `temCoberturaContratada` + `MIGRATED_SECTIONS` + `case` + flag + entrada de nav |
| RR5-04 — o PDF entrega 5 de 12 riscos e **apaga o aviso de que há mais**: o CSS de print esconde o resumo e tenta abrir o bloco com uma propriedade inerte; a metade que funciona é a que esconde. O comentário no componente registra a crença oposta, e com base nela a legenda foi enfraquecida | completude | Alto | P0 | procede (novo) | **procede-fechado** ([[A40.l88]] · #1755) | estado React sobre **classe** (`hidden print:flex`), não `<details>` nem atributo `hidden`: os dois são `display:none !important` na folha da **UA**, que vence `!important` de autor — a 1ª tentativa de fix caiu nisso e o spec de print a reprovou nos 3 engines. Legenda volta a "N de M" **só enquanto a lista está partida na tela**. Gate: `parecer-degradacao.@critical` sob `emulateMedia({media:"print"})` |
| RR5-05 — o classificador de desfecho do run ignora a pausa: testa apenas status terminal e ausência de stage degradado, não olha o stage log que permanece pausado nem a review aprovada com aviso ⇒ classifica o run como completo, o único valor que autoriza a barra de "sem pendências" | correção | Alto | P1 | PARCIAL · **inerte nesta configuração** (3 outros sinais dispararam) | procede-aberto | o caminho é vivo: run aprovado com N avisos e sem os outros sinais imprime a afirmação de ausência. É a metade user-facing de PV9-28 |
| RR5-06 — a lacuna de classificação é modelada como **classe de alocação com alvo zero**, ganhando desvio em pp e barra como qualquer classe conhecida; a nota funde classe conhecida deliberadamente fora do plano com ativo desconhecido sob o mesmo rótulo | clareza-ux | Alto | P1 | procede (mede RV8-17 por outro flanco: o agregado **é** consumido, com semântica trocada; sem consumidor segue a **itemização**) | procede-aberto | sai da tabela de desvio e vira faixa de incerteza, com traço em Alvo/Desvio + lista dos itens + CTA de classificar |
| RR5-07 — o painel de qualidade tem 5 slots e nenhum expressa as 4 classes de lacuna que pausaram o run | completude | Médio | P2 | PARCIAL — "conjunto fechado" **cai**: a frase é cardinal, o trade-off é decisão registrada ([[ADR-357]]), e duas das três linhas deste run declaram o conjunto aberto | procede-aberto | o termo vivo migrou para RR5-05; aqui resta o slot ausente para lacuna de atribuição |
| RR5-08 — a reserva é "excessiva" no card e "bem dimensionada" em dois pontos fortes, no mesmo pilar e com a mesma confiança | clareza-ux | Alto | P1 | procede (novo) | procede-aberto | cobertura acima da meta renderiza **um** rótulo; a composição marca a fatia sem dono como ressalva, não como linha de membro |
| RR5-09 — a meta de IF não declara qual custo mensal ela financia, e o relatório publica três, com razão de mais de 3× entre o maior e o menor | solidez-financeira | Alto | P1 | procede (novo) | procede-aberto | a regra codificada está **certa**; o defeito é de divulgação. O card nomeia o denominador e exibe a cobertura contra os três |
| RR5-10 — o KPI de patrimônio investível contradiz a definição publicada no apêndice do mesmo relatório, e circulam **cinco denominadores** sem tabela de equivalência | consistência | Alto | P1 | procede (novo; vizinho de RV4-18) | procede-aberto | renomear o KPI para o que ele mede, ou trazer a fórmula para a face do card |
| RR5-11 — três números diferentes para "despesa sem categoria", **dois deles declarando a mesma base**; é a métrica que dispara o CTA nº 1 e o P1 do parecer | consistência | Alto | P1 | procede (novo) | procede-aberto | denominador nomeado por superfície, explícito no rótulo |
| RR5-12 — o banner de qualidade publica a fração **menor**, em janela não rotulada, na primeira linha que a família lê sobre confiabilidade | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | a regra permite janela completa **apenas com rótulo** |
| RR5-13 — ancoragem existe só para dinheiro e a prosa migrou para percentual: um literal monetário nos corpos textuais contra dezenas de percentuais, todos estruturalmente inverificáveis | qualidade-llm | Alto | P1 | procede (novo) | procede-aberto | admitir folhas de percentual no catálogo de citação e estender a verificação |
| RR5-14 — ancorabilidade **por item** é de um terço, e o instrumento mede a **oferta** (folhas com rota) e não o **consumo** (itens que citam) | qualidade-llm | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-07) | procede-aberto | acrescenta: as raízes citadas subiram de duas para seis — a semeadura da [[A40.l83]] **funcionou**; o que não fechou é a cobertura por item |
| RR5-15 — `pontos_fortes` e `metricas` não têm slot de âncora nem de confiança no schema: a classe de item mais persuasiva do parecer é a única inverificável, e a regra de rebaixar confiança não tem onde pousar | qualidade-llm | Alto | P1 | procede (novo) | procede-aberto | bump breaking do schema de output |
| RR5-16 — a instrução de declarar incompletude em todo percentual de carteira tem adesão **zero** e nenhum contador; a regra escrita para impedir o falso-positivo conhecido é hint sem medição | qualidade-llm | Alto | P1 | procede (novo) | procede-aberto | promover a guardrail contável e rebaixar a confiança do item ofensor |
| RR5-17 — a ressalva de lacuna cobre 2 de 4 classes: o parecer nunca recebe os **avisos** que fizeram o run pausar, só os campos | completude | Alto | P1 | procede (novo) | procede-aberto | bloco de avisos retidos no manifest + hint de ressalva obrigatória |
| RR5-18 — códigos internos de tipo de documento vazam como rótulo de instituição em 12 de 19 linhas, na tabela cuja pergunta é "onde meu dinheiro está" | clareza-ux | Alto | P1 | procede (novo; família de RV8-24) | procede-aberto | rótulo = instituição · produto traduzido; sufixo técnico só em auditoria |
| RR5-19 — mobile: a página tem ~1,6× a altura do desktop, sem índice, e a tabela de maiores ativos perde a coluna que desambigua exatamente abaixo do breakpoint | clareza-ux | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-27) | procede-aberto | acrescenta o mecanismo e que **não é defeito de mobile**: para imóvel não há desambiguador em nenhum breakpoint |
| RR5-20 — agência e número de conta em claro, enquanto o CPF é mascarado no mesmo documento — inclusive no PDF que circula por e-mail | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | mesma política dos dois lados |
| RR5-21 — quem imprime pelo navegador leva um documento com o link de sair e o e-mail de login no cabeçalho | consistência | Médio | P2 | procede (novo) | procede-aberto | esconder o shell da aplicação em mídia print, onde o índice já é escondido |
| RR5-22 — no PDF, colunas estreitas quebram palavras no meio, inclusive nos cabeçalhos das duas tabelas mais orientadas a ação | clareza-ux | Médio | P2 | procede (novo) · **caveat declarado**: lido do texto extraído, não do PDF renderizado | procede-aberto | revisar larguras em print; confirmação visual antes de dimensionar |
| RR5-23 — o contador de próximos passos não reconcilia com nenhuma lista visível, e há três inventários de ação concorrentes na mesma página | consistência | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de RV4-12) | procede-aberto | um inventário por relatório, com identidade estável entre parecer e plano de ação |
| RR5-24 — chave crua do payload como rótulo de chip de evidência: o mapa de tradução falha **aberto**, então toda âncora nova entra em produção como identificador | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | preencher a chave e trocar o fallback para falha fechada; teste cruzando o enum com o mapa |
| RR5-25 — a legenda do gráfico usa slug de categoria enquanto a tabela duas seções abaixo usa o rótulo humano correto; o mapa já existe | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | a legenda consome o mesmo mapa |
| RR5-26 — separador decimal en-US convive com pt-BR **dentro da mesma tabela**, com a linha de total no formato certo e as linhas no errado | consistência | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-25) | procede-aberto | acrescenta: alcança coluna determinística e KPI, não só prosa gerada. Gate possível barrando percentual formatado sem o helper |
| RR5-27 — o token de seção nomeia duas coisas na mesma página: nenhuma âncora está morta, e o problema é pior — alvo **vivo** apontando para a seção errada | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | desacoplar os namespaces |
| RR5-28 — o índice salta um número, tem título em inglês e aninha conteúdo de pessoa física sob um cabeçalho de pessoa jurídica que é stub sem dados | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | renumerar (o número é editorial, a âncora permanece); promover os filhos a irmãos |
| RR5-29 — o único desambiguador de imóvel é o rótulo cru, e existe numa só tabela; na tabela onde a distinção decide concentração, os rótulos são idênticos | clareza-ux | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de RV8-24 + RV8-27) | procede-aberto | apelido de imóvel no cadastro, usado nas duas |
| RR5-30 — o glossário publica um ideal **central** que a escada de classificação, monotônica, não persegue | solidez-financeira | Baixo | P3 | procede (novo) | procede-aberto | ou a escada vira faixa com teto, ou o glossário para de anunciar o ideal |
| RV4-12 · RV4-13 · RV4-15 · RV4-16 · RV4-18 (§r4) | — | — | P1/P2 | — | **procede-aberto (re-ancorados acima)** | RR5-23 mede RV4-12; RR5-13/PV9-36 medem RV4-13; RR5-30 mede RV4-15; RR5-10 vizinha RV4-18 |

**Q6 — a divergência não existia, e a correção é do método.** O braço cego escolheu
reconstruir a base de custo de vida; o parecer prescreve seguro de vida. A rodada leu isso
como divergência porque comparou o braço cego contra o inventário de **um item** do E5, em
vez de contra a lista de sugestões de execução do parecer — onde as duas escolhas são o **P0
e o P1 da mesma lista**. O desempate é **categórico**: o alvo de cobertura de proteção tem
procedência nula por regime, e pela regra 2 da própria rodada isso torna a alavanca
**inadmissível — retirada**, não "não dimensionada". A lente de materialidade aplicou a regra
de sobrevivência ao pior extremo a uma alavanca que a regra de admissibilidade já havia
removido; **admissibilidade é filtro, não peso**. Veredito: **o braço cego acertou**; a
alavanca de seguro sai como `condicionada`, com a medição que a destrava nomeada pelo próprio
produto. Ironia medida: a decisão do plano de ação renderizado **já é** categorizar as
despesas — o braço cego redescobriu o que o relatório prescreve, e ninguém notou porque
ninguém leu aquela seção.

**Refutados / rebaixados nesta rodada:** "conjunto fechado" no painel de qualidade (frase
cardinal + decisão registrada) · "diversificação de fontes é falsa" (o eixo é regime e tem
lastro determinístico — o achado é a contradição interna, PV9-08) · `alertas` como superfície
de risco (alvo errado; o correto é PV9-06) · "notas 0 de 5 entregues" (uma converge com um
risco renderizado).

**Débito de método da r5.** Registrado no §Débito de método do
[runbook](../reference/runbooks/unified_certify_review.md) — doze itens, entre eles: a
condição declarada ("procede sobre N avisos") não foi enumerada no brief das lentes; a tabela
de condicionamento foi chaveada na taxonomia do **produtor** (7 baldes) quando toda decisão é
tomada sobre a do **consumidor** (23 blocos), deixando a maioria das âncoras de decisão sem
graduação; o PDF foi capturado e **não foi disponibilizado** às lentes; a viewport mobile
ficou sem dump de texto; nenhuma das medições publicou seu comando de re-medição; e
particionar por lente criou uma costura — o plano de ação renderizado caiu entre duas lentes
e ninguém o leu.

## r6 — ws-1b9f2cf5-2026-08-29

> Rodada unificada **U2** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r6 · [[PIPELINE-REVIEWS-active]] §r10 · [[REPORT-REVIEWS-active]] §r6 (este).
> Objeto: report `c011c40c` sobre run `79a61e33` — **produzido nesta rodada**, não pré-existente.
> Lentes: 5 + braço cego com trava · céticos: 3 lotes (**2 REFUTADO / 14 PARCIAL / 2 CONFIRMADO**) · crítico de completude: sim.
> **Cobertura de `clareza-ux` observada, não inferida:** tela 1280, mídia print, PDF de produção e **viewport mobile 390 com dump de texto** — o mobile ficou integralmente não-observado no §r5 e o harness foi consertado nesta rodada.
> Cru + síntese com valores + render: `storage/<uuid>/reviews/U2-2026-08-29/` (off-git).
> **A rodada procede sobre 7 avisos retidos, enumerados em [[PIPELINE-REVIEWS-active]] §r10.** Toda linha de `solidez-financeira` e as perguntas Q2/Q4/Q6 herdam a condição.

**Manchete: dois números de "quanto sobra" na mesma página, mesma base, e a diferença é
exatamente o gasto pontual — a maior é a que prescreve.** Identidade fechada ao centavo
(o resíduo é arredondamento): `folga_mensal = (poupança 12m + gastos pontuais 12m) / 12`. Os dois
percentuais dividem o **mesmo** denominador (`fluxo_caixa.janela_12m.receita_recorrente`
== `equilibrio_cerbasi.componentes.base`) e divergem em **19,4 pp**. Quem dimensiona
aporte pela folga dimensiona **27% acima** do que a poupança medida sustenta. É a classe
sum-preserving que a rodada existe para pegar, e ela **alcançou o usuário**.

**Segundo eixo: um KPI publicado inverte de veredito ao remover do numerador um ativo que
o próprio motor exclui duas seções antes.** A concentração imobiliária é 50,62% porque o
numerador soma um bem que `real_estate.excluded_properties` exclui com o motivo literal
*"não gera caixa nem está disponível para venda livre"*. Sem ele: **49,08%**, abaixo do
limiar 50,0 com operador `<` — e caem juntos o ponto urgente, um risco ALTA do parecer, o
KPI vermelho e uma nota 4,0/10 com peso 12,5% no score.

> **Emenda 2026-08-30 ([[A40.l94]] · [[ADR-422]] · #1828 `05561dc0`).** A manchete acima
> descreve o estado do run e **não se reescreve**. O defeito que ela nomeia está **fechado**:
> `folga_mensal` passou a ser `receita_recorrente_mensal − despesa_consumo_mensal`, os dois
> "quanto sobra" viraram um, `teto_sugerido` saiu do contrato e `equivalente_meses_aporte`
> virou `equivalente_meses_poupanca` (46,1 → 4,1 meses no dogfood). O invariante que a Trilha
> propunha existe e é verde. **Segue aberto** o que a [[ADR-422]] §"O que esta ADR NÃO conserta"
> declarava: a base dos pontuais continua contaminada — dono [[A40.l98]].
> ✅ **FECHADO em 2026-08-31 (#1865).** A base publicada exclui a união das duas
> famílias de transferência e o balde `nao_identificado` ([[ADR-425]] §D1), e o
> resíduo vai declarado por causa em `consumo_consciente.base_pontuais`. A frase
> acima **não descreve mais o publicado**: o que resta é a qualidade do detector
> (`PV9-12`, `procede-aberto`), que a l98 declarou fora de escopo.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RR6-01 — `folga_mensal` reclassifica gasto pontual **realizado** como folga recuperável; a soma fecha dos dois lados e a página publica dois "quanto sobra" incompatíveis sobre a **mesma base**, sem rótulo que os distinga | correção | Crítico | P0 | procede (MEDIÇÃO-DE-CONHECIDO de `PV9-13`, agora com a **identidade exata** fechada ao centavo) | **procede-fechado** ([[A40.l94]] · #1828 `05561dc0` · [[ADR-422]]) | invariante: `\|folga − taxa_poupança × receita recorrente\| ≤ ε` — ~~falha hoje~~ **entregue e verde** (`test_folga_mensal_nao_soma_pontual_realizado`); falhava por exatamente `total_pontuais_janela`. E `equivalente_meses_aporte` (hoje `equivalente_meses_poupanca`) media contra o aporte **declarado**, não contra a poupança realizada ⇒ fator de inflação **4,9×** na percepção do gasto pontual |
| RR6-02 — o numerador da concentração imobiliária inclui bem que o motor declara **não-gerador e não-vendável**; removê-lo faz o KPI cruzar o limiar no sentido oposto e desarma 4 superfícies de risco de uma vez | correção | Crítico | P0 | procede (novo) · **medido e re-enunciado** — o defeito é real, o **corte proposto estava errado** | ✅ **fechado** → [[A40.l95]] `shipped` 2026-09-01 (7 PRs) · [[ADR-420]] `Decidido` | o discriminador não é fluxo de caixa, é **rebalanceabilidade**: `especulacao` **fica** no numerador (a trava da [[ADR-340]] está certa nessa metade) e `uso_pessoal` **sai** junto com `nu_proprietario`. Cortar por `geradores`, como o enunciado pedia, daria **0% de concentração** a quem tem a carteira inteira em terreno especulativo. Três correções ao enunciado: `investivel_efetivo` **não** é o denominador publicado (ele já exclui o não-gerador); a queixa do braço cego de que a base "não reconstrói de nenhum escalar" está **obsoleta** desde o PR4 da [[A40.l80]] (#1782); e o score **não cai** (7,438 → 7,463, arredonda 7,4 nos dois) — quem se move são as 4 superfícies de limiar binário. O rótulo é o vetor e é anterior à [[ADR-340]]: a [[ADR-215]] P3 renomeou o balde cat_2 para "Imóveis de Renda" justamente para *"comunicar o critério econômico real (geração de caixa)"*. ~~⚠️ **bloqueante:** nenhuma fixture do repo tem `imoveis_geradores > 0` — as duas leituras são extremos degenerados no golden, e verde pós-conserto não provaria conserto~~ **caiu em 2026-08-31 (#1904)**: o golden do dogfood passou a ter os cinco destinos de cat_2 com valores dois-a-dois distintos, e a discriminação é guardada por contrafactual (sem override, `imoveis_geradores` colapsa a zero). O numerador também passou a ser declarado no payload (**#1901**). ~~**O passo 3 segue aberto**, por bloqueio documental~~ **fechado em 2026-09-01**: o bloqueio era a §D2 gatear a nota inteira numa dependência de UMA cláusula, e a emenda de 2026-08-31 restringiu-a ao **piso de cobertura** (re-roteado para quem executar a [[A40.l11]]). Numerador corta por rebalanceabilidade — **82,19% → 77,19%** no dogfood, com `bruto`/`liquido`/cat_2 **byte-idênticos** — ver a [[A40.l95]] §Fecho |
| RR6-03 — a tabela de ativos mais lida atribui titular em **15/15 linhas** enquanto o mesmo relatório publica que uma fatia material da carteira **não tem titular identificado**; por aritmética forçada, valor que o sistema declara órfão está exibido com `Membro` preenchido | correção | Crítico | P0 | **CONFIRMADO** — a refutação proposta ("as órfãs não estão entre as maiores") é **aritmeticamente impossível**: as 15 linhas somam 92,7% da base ⇒ o residual não comporta a fatia órfã, por 2,4× · **direção MEDIDA 2026-08-29** ([[A40.l96]] §Medição): o **mecanismo** deste veredito cai — as duas porcentagens têm denominadores distintos (o Top 15 soma 92,90% de `investimentos.total`, do qual **50,16% são imóveis**; os 49,03% são sobre `investivel_financeiro`), logo não há residual a comparar. A **conclusão** sobrevive por outra rota, e **o dano INVERTE** | procede-aberto | é a rota pela qual o aviso retido nº 7 vira **decisão de sucessão errada** — e a prescrição de sucessório do parecer é a única que **não** condiciona à titularidade. ~~⚠️ direção não determinada~~ — **RESOLVIDA 2026-08-29 pela [[A40.l96]]**, e por uma terceira via: as duas hipóteses do brief caem. O roll-up está certo (`papel_da_chave` trata vazio como `sem_dono`, [[ADR-412]] §D3) e o Top 15 **não** lê o extrato — lê `fonte: irpf_bens`, e o extrato é justamente o lado sem titular (`itau`/`rico` emitem `titular: None`; `c6bank`/`binance` não emitem o campo). **O sinal existe e morre entre o E1 e o E4:** o artefato E1 `members` deste run traz `banco_membro` com 11 instituições e `contas[]` com 18 — incluindo as 3 instituições órfãs — mas o E4 lê o `family_members.json` materializado de `bank_accounts`, tabela com **0 rows no banco inteiro** (único escritor é o endpoint manual). Somam-se `AccountResolver` declarando `ambiguous` por **cardinalidade de contas** e não por divergência de membro (`itau` e `rico` têm 2 contas cada, **ambas do mesmo membro**) — comportamento **encodado em teste** (`test_none_account_number_with_two_same_member_still_ambiguous`) que **contradiz a lista de casos da própria [[ADR-226]]** (*"ambiguous (2+ **membros** sem account_number)"*), logo é divergência ADR↔teste a decidir por emenda, não bug a consertar — e a saída do resolver entrando **sem** canonicalização de chave ([[ADR-243]]). Contrafactual medido sobre os **8 subconjuntos** (a redação anterior — *"68,15% com qualquer subconjunto próprio"* — era **falsa**, corrigida no closeout de 2026-08-29): 5 dos 6 próprios não-vazios são inertes, mas **`{D1,D3}` move para 46,25% órfão / ~33,3% publicado e segue acima do `piso_pct: 1.0`** — é o conserto que um PR prudente tentaria, por não tocar a decisão encodada em teste, e ele mantém as 8 superfícies acesas. Só `{D1,D2,D3}` leva a **0,13% / ~0,10%**, abaixo do piso. Portanto o risco ALTA, a `motivo_supressao` da realocação, a confiança *"insuficiente"* do diagnóstico e a ação P1 *"reconciliar a titularidade"* (que a família **não pode** executar) são **espúrios** — 8 superfícies. Trilha: **[[A40.l96]]** |
| RR6-04 — a fonte de verdade do layout declara **os 5 componentes** de uma seção `enabled: false` enquanto a superfície publica ao menos 4 deles, nas quatro capturas | contrato | Alto | P1 | procede (novo) · **verificado literalmente** | procede-aberto | quem consultar o YAML (que dirige o codegen, [[ADR-076]]) para saber o que a família vê acerta zero. O `RR5-03` **segurou no render e quebrou no manifesto** |
| RR6-05 — um campo do view-model é **emissor sem leitor em todos os canais** (tipo declarado, zero componente, ausente do manifest do parecer) **e** está em base temporal de 12 meses dentro de um bloco que declara janela cheia; ele soma **49,3%** do total de receita do próprio bloco, enquanto os três irmãos somam 100% | contrato | Alto | P1 | procede (novo) · **verificado** | procede-aberto | são **dois** defeitos que se protegem: o emissor-sem-leitor some se alguém **deletar** o campo; a base errada some se alguém **renderizar** o campo — o conserto de um é o gatilho do outro. O invariante do produtor é gateável: nenhum valor derivado da fatia de 12m pode ser atribuído a chave do dict de topo (**1 ofensor, 1 sítio legítimo** — razão sinal/ruído ideal para ratchet) |
| RR6-06 — o gate criado no `U1` para emissor-sem-leitor tem **escopo igual ao conjunto de incidentes que o pariu**: cobre campo do parecer, seção sem dispatch e custom property CSS, e **não alcança o view-model E5** | gate silencioso | Alto | P1 | procede (novo) | procede-aberto | ⚠️ **armadilha nomeada:** o regex de declaração de campo só captura campo **top-level** de interface. Estender o escopo sem trocá-lo produz **verde sobre o ofensor conhecido** — o modo de falha exato que a [[ADR-372]] §Emenda pagou. O predicado tem de iterar **todas** as interfaces exportadas do arquivo |
| RR6-07 — o **único** snapshot de view-model do repo tem `janela_meses: 1`, e com `n_janela = min(12, 1)` as duas janelas **colapsam na identidade** ⇒ nenhum golden do repo pode discriminar defeito de janela, nem antes nem depois do conserto | gate silencioso | Alto | P1 | procede (novo) · **verificado** | procede-aberto — ⚠️ **metade fechada em 2026-08-29** (#1828 criou `pontuais-com-aporte-3_reconciled.json`, 13 meses, + `test_fixture_discrimina_folga`, que vigia a fixture contra vacuidade); **sobrevive** o snapshot de view-model com `janela_meses: 1`, que segue sem discriminar | **precede** qualquer teste de regressão que o `RR6-05` gere: escrever o gate contra esta fixture é escrever um gate que passa nos dois mundos. É o item que trava a ordem de conserto |
| RR6-08 — a supressão de alvo **não tem read-path para linhas persistidas antes dela**: o alvo suprimido sobrevive no plano de ação via uma row do `Decision` aggregate escrita três meses antes do fix, com `target_field`/`target_value` **NULL** e `context_snapshot` apontando outro relatório | contrato | Alto | P1 | **re-enunciado** — a leitura inicial (`RR5-02` não segura) está **errada** e mandaria re-remover regra que já não existe | procede-aberto · **`RR5-02` confirmada FECHADA** | o numeral vive em texto livre, onde nem o write-path nem o catálogo de KPI governam. Ou o renderer do plano resolve alvo pelo catálogo, ou existe migration que marca as rows anteriores — **sem uma das duas, toda supressão futura nasce com o mesmo furo** |
| RR6-09 — o parecer publica a participação de uma classe de ativo **~92× menor** que a tabela de alocação da mesma página, **nomeando como base a própria tabela que o contradiz** | consistência | Alto | P1 | procede (novo) · **verificado** | procede-aberto | o par internacional bate; não há denominador que reconcilie o outro. E o risco que contradiz a tabela **só aparece no print e no PDF** — a tela colapsa a lista de riscos |
| RR6-10 — o score e o catálogo de KPI leem **bases diferentes do mesmo indicador nomeado**, com 8,92 pp de diferença, e a escolha é **assimétrica** entre indicadores, sem regra declarada em lugar nenhum | consistência | Alto | P1 | PARCIAL — **cai** "o piso não chega a nenhuma superfície" (ele **é consumido**: o score lê o piso; o catálogo lê o teto); materialidade medida: a classificação do score **não vira** | procede-aberto | o `kpi_targets` **já faz certo** (`base` + `rotulo`); `score.componentes[*]` ganha `base` + `observado_path` e a superfície deriva o rótulo daí. **Conserta 5 casos de uma vez** — inclusive dois campos **homônimos** de "cobertura de despesas" com bases distintas, dos quais o score escolhe um sem dizer qual |
| RR6-11 — a seção de tributário PJ é **estruturalmente inalcançável** para todo workspace self-serve: o endpoint de perfil existe e tem role de escrita, e `rg` no frontend por ele devolve **zero** — não há tela, tipo gerado nem chamada | completude | Alto | P1 | PARCIAL — **cai** "único estado vazio sem CTA" (há outros) e **cai** "o dado é inferível do fluxo" | procede-aberto | a copy "solicite ao seu consultor" **não é escolha de tom, é a descrição literal do único caminho existente**. E inferir regime a partir de um pagamento observado é rejeitado como arquitetura: não amarra o CNPJ pagador ao gerador da receita, e moveria o usuário de um estado vazio para **outro** (anexo + CNAE ainda faltam) |
| RR6-12 — o contador de próximos passos é coerente sobre um **13º inventário que o documento nunca renderiza**: o componente de sumário consulta o inbox **live** do workspace sem filtrar por relatório, enquanto o irmão inline filtra. Um snapshot datado publica um número que muda sozinho | consistência | Alto | P1 | **re-enunciado** — `RR5-23` dizia "contador não reconcilia"; ele **não está quebrado**, está contando outra população | procede-aberto | a correção anti-vazamento foi aplicada **só na metade inline**; e o inline existe em apenas 2 seções, então as sugestões do inbox nunca têm onde aparecer |
| RR6-13 — não existe **uma** resposta para "o que faço agora": **12 inventários de ação**, três primeiras-ações concorrentes e **nenhuma precedência declarada** entre elas | clareza-ux | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de `RR5-23`, com os números) | procede-aberto | as três: reclassificar transações (banner, único acionável acima da dobra) · contratar seguro (pontos urgentes + P0 do parecer) · reduzir a taxa de retirada (plano de ação + prioridade 1 da síntese) |
| RR6-14 — a decisão de prioridade 1 do plano **eleva a meta de independência financeira em 25%**, derruba o progresso publicado e empurra o ano projetado — e é rotulada como *"otimizar a trajetória"* | consistência | Alto | P1 | procede (novo; **contém refutação** do precedente do §r5 — o produto **distingue** corretamente a premissa de retirada do yield observado, e a prescrição nomeia a premissa) | procede-aberto | o efeito publicado é o **oposto** de otimizar: é reconhecer que a meta estava subdimensionada. Nenhuma das duas superfícies declara o impacto, e a coluna de valor da decisão vem vazia |
| RR6-15 — o título da seção de riscos afirma o cálculo que o corpo, três linhas abaixo, declara não fazer; e o parecer ancora **4 itens** nessa seção, incluindo o P0 e o P2 | clareza-ux | Médio | P2 | PARCIAL — **cai** "5 componentes ligados e entrega vazio" como defeito de fiação: o gate de runtime é **tri-estado, declarado e tem ADR**; hide-when-empty é legítimo | procede-aberto | o título é **incondicional**. A âncora existe; o destino se retrata |
| RR6-16 — a instrução de declarar incompletude em todo percentual de carteira tem adesão de **5 de 11 itens**, e 4 das 5 são auto-referenciais; mas o defeito material não é a taxa — é **onde ela cai** | qualidade-llm | Médio | P2 | PARCIAL — **cai** "a instrução é incondicional" (é explicitamente condicional) e **cai** "as aderências são todas auto-referenciais" (há 1 genuína) | procede-aberto · re-enuncia `RR5-16` | o balde não classificado é **216× maior** que a menor afirmação de classe que o parecer publica sem ressalva; já na concentração imobiliária a incompletude não contamina numerador nem denominador. **A regra é larga demais e cega ao que importa:** o gate deve disparar por **ordem de grandeza** (`nao_classificado_pct > valor_citado`), não por presença |
| RR6-17 — dois dos quatro caps de geração **saturam** (`riscos` e `metricas`), e truncagem-por-cap é indistinguível de cardinalidade real: a ausência do item de 13ª posição não é observável em lugar nenhum | qualidade-llm | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de `PV9-32`; **`metricas` é extensão nova**) · verificado | procede-aberto | emitir sinal quando o cap morde |
| RR6-18 — o score é **aritmeticamente insensível** ao único risco de severidade alta do motor determinístico; o composto que ocupa o card de capa não se move com uma lacuna de proteção apurada | solidez-financeira | Médio | P2 | PARCIAL — **cai** "é drift": há **decisão registrada e impressa** ([[ADR-387]] aparece no próprio PDF), e pontuar proteção sem inventário confirmado produziria nota falsa | procede-aberto | conserto barato é **uma linha de copy** no card ("o score mede 5 dimensões; **não considera proteção** — ver a seção de riscos"), não um 6º componente, que reabriria a calibração de pesos |
| RR6-19 — um percentual de carteira aparece com **duas bases, ambas rotuladas "do total"**, uma delas sem declarar a janela; e um percentual de renda tem **três** valores, com o denominador mudando de "renda total" para "renda do trabalho" sem aviso | consistência | Médio | P2 | procede (novo; família de `RR5-10`/`RR5-11`) | procede-aberto | o mesmo parecer publica "diversificação de fontes" como ponto forte e, dezoito linhas depois, "renda concentrada" como agravante do risco de maior severidade — **os dois estão impressos** |
| RR6-20 — o cenário de estresse testa a remoção de uma contribuição que o próprio bloco declara **já ser zero**, aplicando um fator de redução sobre premissa que ele mesmo refuta | correção | Médio | P2 | procede (novo) | procede-aberto | o "cenário de estresse" **é a linha de base real**, e o cenário-base embute capacidade de aporte de uma fonte declarada inexistente |
| RR6-21 — ausência renderizada como afirmação de descoberto: uma lista vazia que significa *"nenhum gap apurado"* é traduzida como *"nenhuma cobertura identificada"*, na mesma seção que publica apólices vigentes do tipo em questão | clareza-ux | Médio | P2 | procede (novo; mesmo modo de falha de `PV9-34`, outro sítio) | procede-aberto | leva a família a contratar cobertura duplicada — ou a descontar o selo de atenção por percebê-lo como falso, e com ele o gap que é real |
| RR6-22 — o colofão publica ao cliente um identificador de build com marca de árvore suja, e o PDF entregue **não tem sumário nem numeração de página** enquanto a tela tem índice completo | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | ⚠️ a perna de paginação é afirmação sobre **texto extraído**; se houver paginação em elemento não-extraível, essa metade cai |
| RR6-23 — no mobile, a coluna que identifica o titular some da tabela de maiores ativos: é exatamente a dimensão que a ação prioritária do próprio relatório endereça | clareza-ux | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de `RR5-19`, com o mecanismo) | procede-aberto | supressão responsiva apaga a dimensão da ação prioritária. Idem o cap rate por imóvel, cujo alerta imediatamente abaixo argumenta com ele |
| RR6-24 — o alvo de reserva publicado excede as três metodologias de referência **e o glossário da própria peça**, que define a reserva numa faixa menor | solidez-financeira | Médio | P2 | procede (novo) | procede-aberto | drift, não decisão registrada — a divergência é defensável para renda volátil, mas precisa de ADR e de conciliação com o glossário. Ou o glossário sobe para a faixa por perfil, ou o alvo desce |
| RR6-25 — o indicador de dívida publicado mede **alavancagem** e a métrica doutrinária (comprometimento de renda) **não existe no artefato**: taxa de juros e parcela mensal são nulas em todas as dívidas | completude | Médio | P2 | **REFUTADO como enunciado** — a conclusão publicada está **certa pelas duas réguas** (a régua alternativa dá folga de 6× a 16× contra o teto doutrinário); o defeito é de instrumento, não de veredito | procede-aberto | **o resíduo é outro achado:** sem a taxa de juros, a única triagem em que as três metodologias convergem — amortizar dívida cujo juro supera o retorno esperado — é **inexecutável**, e nas 3 decisões do plano + 9 ações do parecer **zero** tocam dívida. O campo já existe no schema e está vazio: é **captura**, não fórmula nova |
| RR6-26 — o gate que suprime o destino do aporte compara a incerteza com um **piso absoluto**, não com o desvio da classe mais defasada; a incerteza medida não pode reordenar as classes, e mesmo assim a prescrição é desligada | solidez-financeira | Médio | P2 | procede (novo; adjacente a `RR5-06`) | procede-aberto | suprime a única prescrição genuinamente de rebalanceamento-por-aporte do produto e empurra a decisão para o canal editorial, **que a faz sem rateio** |
| RR6-27 — identificadores internos de rastreio (código de revisão, número de ADR) aparecem em célula de texto declarada como copy publicada ao leitor | clareza-ux | Baixo | P3 | procede (novo) | procede-aberto | o produtor é o catálogo de KPI, não o modelo |
| RR6-28 — os percentuais de peso do score, **como renderizados**, somam 101 | clareza-ux | Baixo | P3 | **re-escopado** — os pesos do modelo somam exato; é arredondamento de exibição | procede-aberto | — |
| RR5-01 · RR5-03 · RR5-04 (§r5) | — | — | — | **consertos VERIFICADOS neste run** | mantidos fechados | as ressalvas metodológicas renderizam nas 4 superfícies · o PDF entrega a lista de riscos **completa**, com o aviso · a seção de proteção publica conteúdo real ⇒ o risco declarado (seção zerada para família sem apólice) **não se materializou**. ⚠️ `RR5-03` **quebrou no manifesto** — ver `RR6-04` |
| RR5-02 (§r5) | — | — | — | **FECHADA, confirmada por query** | fecha | nenhum produtor emite o alvo; o resíduo é `RR6-08` e é outro defeito |
| RR5-05 (§r5) | — | — | — | ⚠️ **classificação suspeita** | re-triagem devida | teve conserto mergeado entre os dois runs (`#1740`/`#1743`) e o brief a declarou aberta |
| Demais linhas do §r5 não re-medidas | — | — | — | **procede-aberto (sem alteração)** | registrado para não decaírem em silêncio | — |

**Q6 — a ordenação é indeterminada, e a trava é quem diz isso.** O braço cego varreu os
35 blocos contra a regra de base conservada e **um único** passa. A recomendação nº 1 que
ele emitiu — separar movimentação financeira de consumo no inventário de gastos pontuais,
antes de dimensionar qualquer corte — sai da única base que autoriza número pontual, e
**converge** com `RR6-01` e `LC6-05` medidos por outro caminho. Ele reconheceu
explicitamente que a alavanca de maior magnitude econômica (titularidade das posições
órfãs) **é maior**, e que a trava a impede de ser nº 1: `condicionada` nunca é nº 1. Cinco
alavancas saíram **RETIRADAS por inadmissibilidade**, cada uma com o campo nulo ou
sentinela que a retirou — entre elas as três decisões tributária, previdenciária e
cambial. E a alavanca de concentração imobiliária foi marcada `indeterminado-por-viés`
pelo braço cego **antes** de a lente de materialidade achar o mecanismo que a derruba
(`RR6-02`) — duas rotas independentes no mesmo alvo.

> **Emenda 2026-08-29 ([[A40.l96]] §Medição).** A frase acima sobre a alavanca de
> titularidade envelheceu junto com o `RR6-03`: medida a proveniência, a fatia
> órfã é **artefato de wiring**, não posição da família. A alavanca de "maior
> magnitude econômica" que o braço cego identificou e a trava suprimiu **não
> existe como alavanca do usuário** — some no conserto do pipeline, e com ela a
> condicionalidade que barrava as prescrições de realocação. A leitura de que a
> trava agiu certo ao rebaixá-la **segue válida** (o braço cego não tinha como
> distinguir dado ausente de dado descartado); o que cai é a premissa de que
> havia ali uma decisão para a família tomar.

**Refutados / re-escopados nesta rodada:** o precedente do §r5 sobre prescrição de
retirada inexecutável **não se aplica** — o produto distingue a premissa do yield
observado · o veredito de dívida está **certo pelas duas réguas** · o campo de evidência
do parecer **tem** validator de sigilo (o achado era falso; sobra só o gap de ticker) · o
contador de próximos passos **não está quebrado** · o gate tri-estado da seção de riscos é
**declarado e tem ADR** · o cap de iterações de tool é **duplicata** de achado já
registrado, e o defeito é falta de **sujeito**, não de canal.

**Ressalva de método sobre esta seção.** Três linhas do §r5 (`RR5-05`) e três do §r10
tiveram conserto mergeado entre os dois runs e o brief das lentes as declarou **ABERTAS**
— o que faz a lente **descartar** o sinal como re-descoberta em vez de verificar se o
conserto segura. As suspeitas estão marcadas; a re-triagem é do r7/r11.

## r9 — ws-1b9f2cf5-2026-09-01

> Rodada unificada **U5** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r9 · [[PIPELINE-REVIEWS-active]] §r13 · [[REPORT-REVIEWS-active]] §r9 (este).
> Run `40d1af2a` `completed` 18/18 · 25,0 min · executor `8217041c` · report `685536d6` (baseline `7ed5aa09`) · preflight 12 PASS · 4 WARN · 0 FAIL (o `worker` reprovou com código de 43h e foi reiniciado antes do disparo).
> Cru + síntese com valores: storage/<uuid>/reviews/U5-2026-09-01/SINTESE.md + .html (off-git).
> Escrituração: [[A40.l113]] · [[A40.l114]] · [[A40.l115]] · [[A40.l116]] · [[A40.l117]] · [[A42.l24]] · [[A42.l25]] · [[A42.l26]] · [[A27.l3]] alocadas nesta rodada; efeito nos gates de saída escrito no `_README` da [[A40]] e da [[A42]].
> Propósito: **DIAGNÓSTICO** a pedido do dono, com os dois gates fechados — registrado antes do disparo. Não pontua gate.
> Cobertura: matriz 7×3 — 21 células, **13 respondidas**, 2 `BLOQUEADA` com o veredito que falta nomeado (`REPORT × correção`, `REPORT × solidez-financeira`), 6 sem cobertura com motivo, **zero silenciosas**. Varredura no grão de componente: 16 de 60 não produzem nada visível; **25,3%** da altura do relatório vem de seções que declaram zero componentes.
> Céticos: exercidos **dentro** da F3.b (desvio declarado) — o painel corrigiu 4 artefatos meus e **2 confirmaram, 2 refutaram**.
> Delta desde o executor do `U4`: **32** commits de produto · **28** de instrumento ⇒ nenhum "idêntico" publicável (§10 `U3` item 1).

**Manchete da rodada: o mesmo corpus documental publicou um relatório 48% menor, e nada
bloqueou.** Sem um documento novo entre os dois runs, **95 de 400** escalares numéricos do
payload publicado se moveram: `patrimonio.bruto` **−48,1%**, `patrimonio.residencia` e
`patrimonio.imoveis_geradores` **→ zero**, `endividamento.total_dividas` **→ zero**,
`patrimonio.liquido` **idêntico ao bruto**, `goals.if_gap` **+27,3%**. O run saiu
`completed` com 2 avisos de pausa e **nenhum** sinal bloqueante. Nas três rodadas
unificadas anteriores o mesmo corpus produzia os números anteriores — é **regressão de 2
dias**, não dívida antiga. São **duas cadeias independentes** ([[A40.l113]] e
[[A40.l114]]), e as duas nascem de **extração LLM não-determinística** sobre documentos que
não mudaram.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RR9-01 — **a identidade de imóvel churna entre runs e os dois classificadores falham FECHADOS**: descrição ganha caractere duplicado ⇒ `endereco_canonical` e `property_id` colapsam juntos (**5 de 7 → 1 de 9**) ⇒ `patrimonio_imovel_classifier.py:58-62` e `:76-78` mandam `pid` nulo para o `else` ⇒ `patrimonio.residencia` e `patrimonio.imoveis_geradores` publicados **como zero** | correção | Crítico | P0 | CONFIRMADO · NOVO — medido A/B sobre **corpus documental idêntico** | procede-aberto | o produto afirma que a família **não tem casa própria nem imóvel de renda**, sem aviso: os classificadores não distinguem *"não é"* de *"não sei"*. Os 9 campos da consolidação seguem 9/9, o que prova que o enricher **rodou e falhou** (se não tivesse rodado seriam 0 de 9). Sem `property_id` o dedup cross-IRPF ([[ADR-246]] passo 3b) **vira no-op** ⇒ 3 pares duplicados no publicado. Dona [[A40.l113]] |
| RR9-02 — **o ano de referência é saída crua do LLM e o total de dívida vira zero**: `extract_baseline.py:96` faz `"ano_referencia": output.reference_year` (`_meta.source: "E1.5-llm"`) sem confrontar com os anos dos documentos ⇒ `patrimonio_por_ano` re-rotulado com conteúdo **byte-idêntico** ⇒ `patrimonio_resolvers.py:561` `_split_dividas` lê `saldo.get(ano_ref, 0)` **sem fallback** | correção | Crítico | P0 | CONFIRMADO · NOVO | procede-aberto | `endividamento.total_dividas` **zero** com 4 financiamentos listados; `score.componentes[taxa_endividamento]` `nota=10,0` com peso **18,8%** e `status="emitted"`; superfície publica "Endividamento Mínimo/Nulo" como **Ponto Forte** em 2 inventários. O irmão `_resolve_saldo` ([[ADR-401]]) **tem** fallback — daí a lista somar certo **na mesma página**. ⚠️ **correção de atribuição**: o comentário em `endividamento_analyzer.py:138` nomeia `_total_dividas_for`, defeito real mas **dormente**. Dona [[A40.l114]] |
| RR9-04 — `#S4` **afirma e nega** imóveis de investimento: abre afirmando ~34,8% do bruto, o card abaixo diz que **não há nenhum classificado**, o KPI repete a negativa e o ranking lista **dois em #1/#2** — 3 asserções de ausência contra 3 de presença; a seção mede **338px**, só o estado vazio | consistência | Crítico | P0 | CONFIRMADO · NOVO | procede-aberto | **é o `RR9-01` visto pela superfície**: sem id não existe classificação, e cada consumidor resolve o vazio do seu jeito. Dona [[A40.l113]] |
| RR9-16 — **o sanitizer de PII mede o contexto de ENTRADA e nunca o output**: CPF com dígitos finais em claro em prosa **e** em `evidencia`, e agência/conta **completas** na mesma página | contrato | Alto | P1 | CONFIRMADO · NOVO | procede-aberto | a política protege 1 identificador e publica 2. A docstring afirma "CPF/CNPJ redigidos" enquanto o conjunto coberto tem 1 elemento que não é nenhum dos dois — **asserção falsa valendo como justificativa de ausência de gate**. Dona [[A40.l115]] |
| RR9-20 — "4 anos para a IF" convive com uma reserva que o **próprio relatório chama de excessiva**, e nenhuma seção reconcilia as duas leituras | solidez-financeira | Médio | P2 | CONFIRMADO · NOVO | procede-aberto | **sem lane** — decisão: o eixo é doutrina de reserva vs. prazo de IF, e a matriz saiu `BLOQUEADA(veredito do razão por bloco)` nesta dimensão. Reabre quando houver bloco em `conservado` |
| RR9-21 — os **4 achados de clareza-ux do `U4` reproduzem** integralmente nas duas viewports | clareza-ux | — | — | MEDIÇÃO-DE-CONHECIDO | **não é achado novo** | reproduzem porque as lanes seguem `open`: [[A40.l105]] · [[A40.l106]] · [[A40.l107]] · [[A40.l108]]. Registrado para não contar duas vezes |
| RR8-04 (§r8) — `_compute_por_fonte_detalhado:592` `if v > 0:` derruba meses negativos | correção | Baixo | P3 | **reproduz ao centavo** (1 de 12 meses) | procede-aberto | **terceira rodada consecutiva sem lane. A decisão de não abrir É a decisão** — registrada aqui para que a próxima rodada não a re-descubra como nova |

**Positivos verificados.** Os **4** achados de superfície do `U4` que tinham conserto
mergeado seguem consertados · o índice de seção emite no desktop · as 27 citações do
parecer **resolvem, 27 de 27** · print e PDF alcançam **12 de 12** blocos de risco (⚠️
refutação da lente, que afirmava *"nem o PDF alcança"* — meu próprio proxy de contagem
por rodapé de confiança quase certificou o falso; a presença por **título** mostrou 12/12).


> **Nota 2026-09-01 — a régua de prioridade virou derivada (§6.1 do runbook), e ela
> discorda de 2 linhas desta seção.** A régua computa `P` de quatro predicados medidos
> (`alcança` · `reproduz` · `falsifica` · `move decisão`), e o contrafactual rodou sobre as
> 43 linhas do `U4` e do `U5`. **Nada aqui é reescrito** — registro entregue é evidência
> datada; a divergência fica como nota, por decisão da própria régua. O que ela diz desta
> seção:
>
> - `RR8-04` → **`P2` latente** (cláusula 4). O valor publicado é **errado** e reproduz há
>   **três rodadas**, mas **nenhum consumidor o expõe**: `fluxo_caixa.por_fonte_detalhado`
>   embarca no payload e o único hit no frontend é a declaração de tipo em
>   `report-fluxo.ts:155`. `P3` subestima — o tipo declarado é exatamente como alguém liga o
>   campo a um card, e aí o número errado publica sem sinal. ⚠️ **A primeira redação desta
>   nota dizia `P1`**, aplicando `alcança` por presença no payload; corrigido ao medir o
>   consumidor. A régua **não** pede lane própria para a instância — pede gate de classe,
>   que é a [[A40.l118]].
> - `RR9-16` (PII) **confirma-se em `P1`** por cláusula própria — exposição não falsifica
>   número, e ainda assim é `P1`.
> - `RR9-20` **confirma-se em `P2`**: duas leituras não reconciliadas são ambiguidade.
>
> Sob a régua, `P1` fica **4 no `U4` contra 6 no `U5`** — não 2 contra 12. O que sobra de
> diferença é real.

## r8 — ws-1b9f2cf5-2026-08-30

> Rodada unificada **U4** · [[LEDGER-CERTIFY-active]] §r8 · [[PIPELINE-REVIEWS-active]] §r12 · [[REPORT-REVIEWS-active]] §r8 (este).
> Run `7d860f0b` · report `7ed5aa09` · executor `04551a0b` · preflight: 4 WARN declarados. **`frontend` no ar** ⇒ `clareza-ux` foi respondida **sobre a captura de render real** nas duas viewports, não por inferência de código.
> Cru + síntese com valores: `storage/1b9f2cf5-.../reviews/U4-2026-08-30/SINTESE.md` (off-git).
> Escrituração: [[A42.l18]] e [[A42.l19]] — **nenhuma lane de produto**: os achados de produto desta rodada saíram Médio/Baixo, e a taxa de duplicação contra o registro foi de ~2/3 (ver §nota de método abaixo). Efeito nos gates em `docs/sprint/A40/_README.md` §Gate de saída e encerramento.
> Cobertura: matriz 7×3 — 13 respondidas · **2 `BLOQUEADA`** (`REPORT × correção` e `REPORT × solidez-financeira`, com o veredito que falta nomeado) · 6 sem cobertura com motivo · zero silenciosas.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RR8-01 — o relatório **não emite índice de seção algum na viewport de 390px**: o desktop emite o índice completo logo após o breadcrumb (`VISÃO GERAL · O que mudou · Perfil · 1 Patrimônio · …`), o mobile vai direto para a capa. São **32.728 px** de rolagem sem navegação | clareza-ux | Médio | P2 | procede (novo · **verificado pelo loop**, por comparação de faixa de linha entre os dois dumps; o shell do app é byte-idêntico nas duas, então o que falta é a navegação **do relatório**) | procede-aberto | [[A40.l106]] |
| RR8-02 — a conversão tabela→card no mobile é aplicada **por componente, não por regra**: **11** tabelas com ≥3 colunas não convertem, incluindo as 3 mais largas, e existe um **terceiro** comportamento não previsto (o ranking de ativos nem converte nem preserva — descarta coluna e segue tabela) | clareza-ux | Médio | P2 | procede (novo · **CONFIRMADO** pelo cético, que corrigiu a contagem **para cima**: o enunciado dizia ≥6) | procede-aberto | [[A40.l107]] · caveat declarado: overflow horizontal não é observável em dump linearizado |
| RR8-03 — **`2036` nomeia duas coisas não relacionadas**: é o ano do cenário **central** estocástico *e* o do cenário de **estresse** sem segunda renda, enquanto o cenário **base** do mesmo apêndice é **2035**. Dois motores de projeção com anos-base diferentes, colidindo no ano que o leitor não consegue classificar | consistência | Médio | P2 | procede — **residual afiado** que o enunciado original perdeu: o cético **refutou** *"três anos sem rótulo"* (o prazo declarado é rotulado 3× e o central é rotulado), e ao refutar achou a colisão | procede-aberto | [[A40.l108]] |
| RR8-04 — `_compute_por_fonte_detalhado` (`fluxo_caixa_enricher.py:592`) tem `if v > 0:` e **descarta o mês negativo** ao somar a janela de 12m por fonte: **1 de 12** fontes tem mês negativo e é a **única** que diverge — o total publicado excede a soma das próprias barras da mesma janela **pelo valor exato desse mês**; as outras 11 casam ao centavo | correção | Baixo | P3 | procede (novo) · **distinto de `PV9-24`**, que filtra sobre o **total** da fonte noutra função (`_build_tabela_receitas:435`) — consertar aquele sítio **não fecha este** | procede-aberto | sem lane · ressalva: **não é dead code** — o campo viaja no payload servido ao browser e ao PDF, e está a um `read` de componente de deixar de ser inerte |
| RR8-05 — os denominadores de *"despesa sem categoria"*, nomeados: o painel de qualidade (o que carrega o **CTA**) divide pelo **período completo**; as outras cinco superfícies dividem pela **janela de 12m**. Nenhum dos dois rotula a sua janela, e a diferença é de **8,5 pp** — com o número **menor** ao lado do botão | consistência | — | — | MEDIÇÃO-DE-CONHECIDO de `RR5-11`, que prescreve *"denominador nomeado por superfície"*: esta rodada **fornece os denominadores** e mostra que são **quatro** rótulos, não três | procede-aberto | — |
| RR8-06 — a mesma assimetria de janela vive **dentro** de `fluxo_caixa` sem nada no nome que a distinga: `despesas_por_categoria` é o `totais_por_categoria` do E4 (**período completo**, `enricher:363`) e `por_fonte_detalhado` é a janela de `janela_meses` (**12m**, `:579`) | contrato | Baixo | P3 | procede (novo) — evidência de que a assimetria engana quem lê o payload: **o instrumento desta própria rodada caiu nela** e produziu 11 divergências falsas antes da correção | procede-aberto | sem lane |

**Verificação dos fechados do `U3`:** `RR7-01` ([[A40.l100]]) **segura** — na superfície renderizada o valor da renda-alvo aparece **1×** e sob o rótulo *"a renda-alvo declarada"*, ancorado na meta; o PMT aparece separado, no cone. `RR7-02` ([[A40.l101]]) **segura e é inerte neste workspace**: a folga publicada é positiva, então o ramo guardado não é exercitado — o conserto está certo e este corpus não o testa.

**Nota de método desta rodada, e ela vale mais que a tabela acima.** Dos candidatos de produto levantados, **~2/3 já estavam registrados**: no rastreio do loop, **5 de 5**; no lote do cético, **4 de 6**, e **três deles mediam MENOS do que o registro existente já media** (`RR5-10` já contava cinco denominadores de *"investível"*, não dois). Um corpus revisado quatro vezes não devolve achado novo de produto na mesma taxa — devolve **denominador** para achado que já existe. A rodada que não distingue *novo* de *medição-de-conhecido* infla o próprio placar e faz o gate de saída da sprint parecer mais perto do que está.

## r7 — ws-1b9f2cf5-2026-08-30

> Rodada unificada **U3** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r7 · [[PIPELINE-REVIEWS-active]] §r11 · [[REPORT-REVIEWS-active]] §r7.
> Run `3a5b9c7d` `completed` 18/18 · 25,7 min · executor `f0ac69a2` · report `939ee69c` · preflight: 4 WARN.
> Cru + síntese com valores: storage/<uuid>/reviews/U3-2026-08-30/SINTESE.md (off-git).
> Escrituração: [[A40.l100]] · [[A40.l101]] · [[A42.l17]] alocadas nesta rodada.
> Cobertura: matriz 7×3 — **`REPORT × solidez-financeira` NULA** (100% dos blocos de doutrina em `sem-veredito` ⇒ a resposta legítima era `BLOQUEADA`) · `PIPELINE × qualidade-llm` fraca.
> Céticos: **3 CONFIRMADO / ~10 PARCIAL / 2 REFUTADO**.
> Objeto: report `939ee69c` sobre run `3a5b9c7d` — produzido nesta rodada.

**Manchete: o conserto da folga segura, e deixou o irmão quebrado.** Os dois "quanto sobra"
convergiram para o mesmo número — delta **19,38 pp → 0,00 pp** — e a identidade
sum-preserving **rompeu**. Mas o campo vizinho ficou **auto-referente**: o denominador virou
a mesma referência mensal de consumo da qual o numerador é **45,4%**.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RR7-01 — o cartão rotulado **"necessário"** publica a **renda-alvo**, não o aporte que o motor calcula; ~~o PMT correto já existe e aparece em **cinco** superfícies~~ **falso, medido na [[A40.l100]]:** o PMT só existe na rota `/plano` (`goal_service`), nunca no payload do relatório — as superfícies do documento publicam o aporte **declarado**. O núcleo segura: o cartão era o único ponto fora da cadeia | correção | Crítico | P0 | PARCIAL (o núcleo segura e fica **mais forte**; o cético **refutou o discriminador da lente**) | **procede-fechado** ([[A40.l100]] · #1845) | ⚠️ o critério de aceite proposto pela lente **não discrimina**: neste workspace o goal declarado e o PMT coincidem, então "batem" passa nas duas implementações. Exige fixture em que difiram — ~~falta~~ **entregue** com três valores distintos (renda-alvo `333.333` · declarado `20.000` · PMT `42.111`), contrafactual verificado **em subconjuntos**. **O remédio caiu na medição:** o PMT que o enunciado dizia existir em cinco superfícies **não existe no relatório** — o único produtor é `goal_service.compute_if_derived` (agregado Goal, rota `/plano`), e as superfícies do documento publicam o aporte **declarado**. O bloco saiu em vez de ser rerrotulado: o `S7Stat` já publica o mesmo número com o nome certo, e a presença incondicional dele tornava inalcançável o estado honesto "Meta de aporte não configurada" |
| RR7-02 — o conserto da folga deixou `equivalente_meses_poupanca` **auto-referente** | correção | Alto | P1 | PARCIAL · triagem **`REGRESSÃO-DE-CONSERTO`** | **procede-fechado** ([[A40.l101]] · [[ADR-422]] §Emenda 2026-08-30) | cai a alegação de que a razão ser superlinear é defeito — é a forma legítima de todo indicador tipo dívida/renda. O defeito é o **polo** e o colapso |
| RR7-03 — a janela canônica divide por **12** enquanto a cobertura de despesa desaba nos últimos cinco meses, terminando em **zero**; ÷12 contra ÷11 = **+9,09%**, e o divisor alimenta o alvo de reserva (×18) e o veredito de liquidez | correção | Alto | P1 | PARCIAL (MEDIÇÃO-DE-CONHECIDO de [[A42.l8]] + causa nova; o sub-achado de roteamento foi **refutado**) | procede-aberto | ⚠️ a [[A42.l8]] se demarcou do **mês em curso**, que é o ofensor medido aqui — no escopo em que está escrita, ela **não** conserta este run. **Refutação:** a taxa de poupança **não** está inflada — o sinal é oposto ao esperado |
| RR6-01 (§r6) — folga reclassificava gasto realizado | — | — | — | ✅ **FECHADO, verificado neste run** | fecha | `05561dc0` · [[ADR-422]] · [[A40.l94]] |
| RR6-02 · RR6-03 (§r6) | — | — | — | RR6-02 ✅ **fechado** ([[A40.l95]] `shipped`); RR6-03 segue `in_progress` | — | [[A40.l95]] · [[A40.l96]] |
| Demais linhas do §r6 | — | — | — | **procede-aberto (não re-medidas)** | registrado | — |

> **Emenda 2026-08-30 ([[A40.l101]] · [[ADR-422]] §Emenda 2026-08-30).** A manchete e a
> tabela acima descrevem o estado do run e **não se reescrevem**. Duas precisões, medidas:
>
> 1. *"o numerador é 45,4% do denominador"* — os 45,37% são a fração do **subtraendo**
>    (`total_pontuais_janela ÷ despesa_consumo`, verificado no `report_data.json` deste run:
>    394.525,39 ÷ 869.511,63). Do **denominador** (a folga) o numerador mensalizado é 33,79%.
> 2. *"o numerador é subconjunto"* — **falso em 5 eixos medidos**. Dois deles são achados
>    novos e foram para a [[A40.l98]]: `data_corte` é aplicado ao denominador e não ao
>    numerador (populações diferentes), e estorno negativo líquida no denominador e não no
>    numerador.
>    ✅ **Disposição 2026-08-31 (#1865).** O 1º **fechou** (o adapter entrega o realizado;
>    um corte, um produtor). O 2º **não procede como enunciado** e o mecanismo é outro:
>    despesa negativa não existe (`transaction_classifier` grava `abs(valor)`), o estorno
>    é CRÉDITO e o E4 o manda para **receitas** — medido fim-a-fim, ele infla
>    `receita_recorrente` e deixa o par mais **otimista** (equivalente 5,6 → 4,0), não
>    mais alarmante. É rota do E4, com blast radius na taxa de poupança inteira: **segue
>    aberto**, dono `financial-planner` + `data-engineer`.
>
> **Fechado:** o campo publica `null` fora do domínio de definição, com `motivo_supressao`;
> `folga_pct` cai pelo mesmo guard transplantado. **Aberto e deferido com dono:** o polo
> (`folga = R$ 0,01` → `3.000.000,0`) é problema de **legibilidade**, não de correção — o
> piso de materialidade foi **rejeitado por medição** (sensibilidade relativa 1:1 em todo o
> domínio; o número suprimido seria verdadeiro e acionável). Dono [[A40.l15]].

**Cobertura — a célula que reprova esta fase.** `REPORT × solidez-financeira` ficou **nula
e não declarada**: 100% dos blocos que carregam doutrina estão em `sem-veredito`, logo não
havia substrato desbloqueado e a resposta legítima era `BLOQUEADA(veredito do razão)`. É o
**mesmo mecanismo** que o `U2` flagrou em `REPORT × correção` — ele migrou de célula, a
rodada consertou a caixa e não notou a migração.
