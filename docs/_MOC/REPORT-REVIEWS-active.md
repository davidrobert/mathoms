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
| RV3-06 — descrição cartorial crua do IRPF interpolada verbatim em `RealEstateYieldCard.tsx:194,303,373` e `EndividamentoCard.tsx:75` (CPF de terceiro, matrícula, inscrição municipal, endereço) sem gate de PII no view-model; [[ADR-337]] é escopada a `top_ativos[].nome` | correção | Alto | P1 | procede | procede-aberto | owner: data-engineer+sre · critério 4 da ADR-337 inexistente |
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
| RV3-18 — mesma matrícula com `property_id` distintos ⇒ lista de excluídos repete o mesmo imóvel; banner conta registros, não imóveis | consistência | Alto | P2 | procede | procede-aberto | JÁ-CONHECIDO **RV2-13** ([[ADR-246]]) |
| RV3-19 — `Metrica` (schema do parecer) sem campo `ancoras`; `_iter_items`/`stamp_ancora_values` cobrem riscos+horizontes ⇒ `valor_atual` é o único número autorado pelo LLM sem verify | qualidade-llm | Alto | P1 | procede | procede-aberto | JÁ-CONHECIDO **RV2-01** · 10/10 valores deste run re-derivados e **conferem** (zero fabricação realizada) |
| RV3-20 — `aporte_investimento` vazio na janela ⇒ mecanismo `despesa_consumo = total − aporte` no-op e `despesa_consumo == despesa_total` | solidez-financeira | Alto | P1 | procede | procede-aberto | JÁ-CONHECIDO **LC04-r3** · ver [[ADR-333]] |
| RV3-21 — `nao_identificado` por **valor** cruza o limiar de degradação na janela de 12m (maior que na janela `full`) | solidez-financeira | Alto | P2 | procede (medição) | procede-aberto | MEDIÇÃO de **LC05-r3** · [[ADR-353]] degrada, não bloqueia |
| RV3-22 — `ratios.*_pct` como string onde consumidores fazem aritmética (`conclusionUtils.ts:135-142` cai em fallback por `typeof !== "number"`) | consistência | Médio | P2 | procede | procede-aberto | JÁ-CONHECIDO **RV2-06** ([[ADR-090]]) |
| RV3-23 — KPIs do hero não passam por `<MonetaryValue/>` (`HeroKpiGrid.tsx:323-331` devolve string; `ui/Kpi.tsx:76-86` sem `tabular-nums`); definição do KPI protagonista só em `title` de `<span>` não-focável | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer · viola §Design System do CLAUDE.md + A11Y_CHECKLIST 4.1.2 |
| RV3-24 — jargão de implementação no bloco de premissas (`ReportPremissasBlock.tsx:97-104`: "snapshot E5", endpoint, hash de integridade) contra `COPY_GUIDELINES.md:263-280` | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer |
| RV3-25 — abreviação `k`/`M` em valor monetário (`ReceitaDespesaMensalChart.tsx:216-220`; narrativa E5.N verbatim em `PerfilFamiliaCard.tsx:29-30`) contra `COPY_GUIDELINES.md:196-197` (`mil`/`mi`/`bi`) | clareza-ux | Baixo | P3 | procede | procede-aberto | owner: prompt-engineer (fonte) + product-designer (render) |
| RV3-26 — `S7IndependenciaSection.tsx:96` lê `goals.trs_pct` (inexistente no payload; chave real `goals.if_trs`) e cai em default hardcoded que também alimenta o tone do KPI | correção | Médio | P2 | procede (latente) | procede-aberto | owner: senior-cto · coincide hoje, mente se o dono configurar outro alvo |
| RV3-27 — `real_estate.imoveis[].valor_imovel` zero tratado como valor real no render (`RealEstateYieldCard.tsx:202`) contra `COPY_GUIDELINES.md:199-207` (ausência ⇒ `—`) | clareza-ux | Médio | P3 | procede | procede-aberto | owner: data-engineer (origem do zero) + product-designer |
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
| RV4-02 — o cliente é um **segundo motor de agregação**: `periodUtils.ts` re-deriva os três insumos de qualquer agregado (substrato via `GET /transactions`, predicado via `isIncomeCategory:106`, denominador via `getPeriodMonths:83`). Número nascido no cliente é **inauditável por construção** — fora de `explain_number`, `_lineage`, golden de execução, snapshot do view-model e verificação de ancorabilidade | consistência | Crítico | P0 | CONFIRMADO | procede-aberto | owner: senior-cto · **[[ADR-377]]** `Proposto` (2026-08-11) + **[[A40.l44]]** · relaciona [[ADR-306]] D2/D3 · absorve RV4-01/03/05/06/07 e **fecha RV3-02 junto** |
| RV4-03 — taxonomia de receita duplicada no cliente diverge do produtor: categoria de crédito fora do whitelist sai da receita **e entra no balde de despesa** (`aggregateDespesasMediaMensal` usa `!isIncomeCategory`), rendendo teto de gasto a partir de um recebimento. O comentário de cobertura em `ReceitasFonteCard.tsx:11-14` não podia ser verdadeiro: o pipeline não tem lista fechada de categorias de receita | correção | Crítico | P0 | CONFIRMADO | procede-aberto | owner: data-engineer · **anti-fix registrado**: corrigir isto antes de RV4-01 faz o divisor parecer validado e o gate fechar verde com o número ainda errado |
| RV4-04 — três agregados distintos de "receita mensal" e três shares da mesma fonte convivem na mesma leitura, sem rótulo que reconcilie a base | consistência | Crítico | P0 | CONFIRMADO | procede-aberto | owner: product-designer + senior-cto · sintoma de RV4-02 + RV4-08 |
| RV4-05 — o estado de carregamento do card de orçamento renderiza um **dataset completo alternativo** (bloco estático de janela `full`) em vez de esqueleto: `OrcamentoProspectivoCard.tsx:46-58` só aplica a guarda `anchorDate && !isLoading` depois de cair no fallback ⇒ conteúdo monetário **não-determinístico** entre superfícies do mesmo relatório | correção | Alto | P0 | CONFIRMADO | procede-aberto | owner: senior-cto · observado: tela e print num caminho, PDF de produção no outro |
| RV4-06 — denominador de mensalização é a **constante do enum do toggle**, não os meses com dado ([[ADR-306]] D3 violado no consumidor; o gate de D2 vigia só o produtor) | correção | Alto | P0 | PARCIAL — fecha 41% do gap, não é o mecanismo dominante | procede-aberto | owner: senior-cto · **rebaixado e mantido aberto**: #1396 (`f1cad2e4`) removeu a causa dominante (âncora), o divisor constante segue no cliente e morre no PR5 da [[A40.l44]] |
| ~~RV4-07~~ — `page_size` no teto sem paginação; a resposta **já traz** `total` e um `summary` uncapped calculado antes do slice, e o hook descarta ambos (`usePeriodTransactions.ts:50`) ⇒ o fix mora no cliente, e o servidor já calcula o número certo | correção | Alto | P1 | PARCIAL — só janelas longas; janela default não trunca | **fechado** | **FECHADO** 2026-08-12 — #1398 (`38a7742d`, [[A40.l44]] PR2): hook devolve `isTruncated` e os 2 cards declaram degradação em vez de exibir média 42% baixa. Paginar não: é o código que o PR5 apaga |
| RV4-08 — `fluxo_caixa.receita_por_natureza` (contrato em `config/schemas/e5_analysis.schema.json`, consumido por `parecer_ancorabilidade.py` e pelo prompt do parecer) tem **zero consumidores** em `frontend/src`; a tela re-deriva pior a mesma resposta | completude | Alto | P1 | CONFIRMADO | procede-aberto | owner: data-engineer · mesma família de RV3-02 |
| ~~RV4-09~~ — card de exposição cambial: default do endpoint V2 (`tier = v2.data?.tier ?? "empty"`) **afirma ausência de exposição** em vez de abster-se, sobrescrevendo o bloco do E5 que classifica em faixa de atenção; o parecer prescreve sobre o valor do E5 | correção | Alto | P1 | CONFIRMADO — a hipótese de "estado vazio, não asserção" foi testada e caiu | **fechado** | **FECHADO** 2026-08-12 — #1393 (`d1b7c97c`): a raiz era o **produtor** — o endpoint V2 nasceu morto em #326 e devolvia `tier="empty"` há 3 meses; o fix distingue "sem base" de "zero medido" no DTO, tornando o zero falso infabricável no cliente |
| RV4-10 — rodapé do card declara meses que ele não mediu (expansão do próprio toggle); não existe estado para janela **parcial**, **truncada** ou **que termina no futuro** | clareza-ux | Alto | P1 | CONFIRMADO | procede-aberto | owner: product-designer · contrato de 5 estados especificado na síntese off-git |
| RV4-11 — chips de evidência do parecer rotulam pelo **root do JSONPath**, então campos distintos do mesmo bloco recebem rótulo idêntico; o cross-check exige exatamente a identidade que produz o erro ⇒ verificação tautológica, todas as entradas `verified` | qualidade-llm | Alto | P1 | CONFIRMADO | procede-aberto | owner: prompt-engineer · mesma família de `nome de chave decide semântica` |
| RV4-12 — sugestões do parecer não alcançam o Plano de Ação: a única rota automática lê uma chave do E5 **ausente do payload**, e nunca lê `parecer.sugestoes_*`; risco de severidade alta sem item acionável em nenhum horizonte | completude | Alto | P1 | CONFIRMADO ⚠️ **re-medir** | procede-aberto | owner: prompt-engineer + product-manager · **área com dono ativo**: [[PLAN-suggestion-lifecycle]] · medido antes de #1378, que mexeu nessas superfícies |
| RV4-13 — o campo de rentabilidade guarda taxa de **retirada** efetiva e o parecer a promove a meta de **retorno**, emitindo risco de severidade alta e métrica-alvo a partir disso | solidez-financeira | Alto | P2 | CONFIRMADO | procede-aberto | owner: financial-planner · raiz determinística; nem prompt nem verificador podem detectar · [[ADR-191]] registra as duas taxas coexistirem, não a promoção |
| RV4-14 — guardrail que rebaixa confiança sob premissa em fallback exige âncora num bloco que **nenhuma âncora do parecer toca** ⇒ cobertura zero por construção; os itens que dependem do bloco o citam em prosa, forma que o gate não lê | qualidade-llm | Médio | P2 | CONFIRMADO | procede-aberto | owner: prompt-engineer · correlato: `needs_review_triggered` é `False` literal |
| RV4-15 — faixas do classificador comportamental no código divergem da legenda publicada no apêndice do próprio relatório; um rótulo do código não existe na legenda e uma faixa da legenda não existe no código | solidez-financeira | Médio | P2 | CONFIRMADO | procede-aberto | owner: financial-planner |
| RV4-16 — `comparisons[].direction_positive` fixo em métrica **não-monotônica** (cobertura de reserva): piorar acima do alvo renderiza com sinal de melhora, na página que classifica a mesma métrica como excessiva | consistência | Médio | P2 | CONFIRMADO | procede-aberto | owner: data-engineer · polaridade tem de derivar do alvo, não do campo |
| RV4-17 — classificador de pedido-de-campo do LLM resolve o path e ignora a **dimensão ano**, marcando como espúrio um pedido legítimo e **deletando-o** antes de gravar | qualidade-llm | Médio | P2 | CONFIRMADO | procede-aberto | owner: prompt-engineer |
| RV4-18 — a composição líquida da reserva conta base maior que a carteira exibida na seção de investimentos; o acoplamento entre reduzir a classe e manter a cobertura não é divulgado | consistência | Médio | P2 | CONFIRMADO (residual de um cluster refutado) | procede-aberto | owner: financial-planner |
| ~~RV4-19~~ — separador decimal em duas convenções **na mesma tabela**: linhas usam `toFixed` (en-US) e a linha de total tem o valor pt-BR hardcoded | clareza-ux | Médio | P3 | CONFIRMADO | **fechado** | **FECHADO** 2026-08-12 — #1403 (`e1462a5f`): os 2 cards usam o `formatPercent` existente, **inclusive no total**, para as duas pontas não divergirem de novo. Achado adjacente aberto: 3 superfícies com a mesma violação **e teste fixando a convenção errada** |
**Ordem de ataque:** RV4-01 → RV4-03 → RV4-05 → RV4-06/07 → **RV4-02** (estrutural,
absorve os anteriores e fecha RV3-02) → RV4-04/08/10. A inversão de RV4-01 e RV4-03
produz gate verde com número errado — está registrada como anti-fix nas duas linhas.

**Aberta 2026-08-11:** a [[A40.l44]] executa essa ordem em 6 PRs, sob a
**[[ADR-377]]** `Proposto` (janela interativa é conjunto fechado pré-computado; o
cliente seleciona, não recomputa) + emenda datada na [[ADR-306]] (mês documentado
exclui futuro e mês em curso). Cobre RV4-01/02/03/05/06/07/08; RV4-04 e RV4-10
ficam habilitados mas são copy/estados, com dono `product-designer` em lane
própria. **Correção do registro na mesma data:** a linha do RV4-02 citava
[[ADR-282]] — conferido, aquela ADR é sobre `natural_key` de override de
transação e não tem relação com agregação no cliente; a citação saiu da linha.

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
