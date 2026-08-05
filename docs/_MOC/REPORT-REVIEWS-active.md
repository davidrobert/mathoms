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
| RV3-04 — `S_PROTECAO` `enabled: false` (`report_layout.yaml`) com componente entregue e testado + ausente de `MIGRATED_SECTIONS`; `buildNavGroups`/`tocGroups` em `ReportShell.tsx:107-126,187-207` não filtram `enabled` ⇒ âncora de nav sem alvo em 100% dos relatórios | completude | Alto | P1 | procede | procede-aberto | owner: product-designer · [[ADR-240]] §Entrega sem registro do flip |
| RV3-05 — `S9RiscosSection.tsx:87` colapsa a seção inteira por `narrativas.charts.bubble_riscos.data_state=="empty"`, imprimindo antes a linha-promessa de `conclusionUtils.ts:204`; `ParecerRisksTable.tsx:139` emite `§<section_id>` como texto puro ⇒ ponteiro do parecer leva a seção vazia | clareza-ux | Alto | P1 | procede | procede-aberto | owner: product-designer · lane a abrir |
| RV3-06 — descrição cartorial crua do IRPF interpolada verbatim em `RealEstateYieldCard.tsx:194,303,373` e `EndividamentoCard.tsx:75` (CPF de terceiro, matrícula, inscrição municipal, endereço) sem gate de PII no view-model; [[ADR-337]] é escopada a `top_ativos[].nome` | correção | Alto | P1 | procede | procede-aberto | owner: data-engineer+sre · critério 4 da ADR-337 inexistente |
| RV3-07 — ordenação do plano sem critério encodado: maior alavanca declarada (regime PJ / anexo) bloqueada por `tributario.regime=None`+`motivo_nao_suportado="perfil_incompleto"` e **sem pendência acionável** que peça regime/CNAE/pró-labore | solidez-financeira | Alto | P1 | procede | procede-aberto | owner: financial-planner+product-manager · absorve achado órfão FP-21 |
| RV3-08 — nenhum dos paths do manifest do parecer toca `$.real_estate`/`$.tributario`; a mesma `section_whitelist` gateia `get_e5_section` e `planner_drill_down.py:145` ⇒ dado renderizado na tela é inalcançável pela narrativa LLM | qualidade-llm | Alto | P1 | procede | procede-aberto | owner: prompt-engineer · gate próprio já emite WARNING com EXIT=0 |
| RV3-09 — `suggestion_rules.py:123` lê `meses_cobertura`; E5 emite `reserva_emergencia.cobertura_meses` ⇒ regra inerte. 10/10 regras retornam vazio neste payload (demais por campos de [[ADR-161]] latentes) | completude | Alto | P2 | procede | procede-aberto | owner: data-engineer · sub-claim "família não é alertada" **refutado** (`pontos_urgentes_analyzer:137` lê o nome certo) |
| RV3-10 — `dependentes_menores_18` como `rationale` de gap de proteção contra `irpf_kpis.dependentes.count=0`: premissa da recomendação nº 1 contestada dentro do próprio payload | consistência | Alto | P2 | procede | procede-aberto | owner: financial-planner · dado do dono, não análise |
| RV3-11 — `tributario` materializado em `build_config_overrides_from_db`→`_setup_run_context` no início do run, com `_latest_run_id` resolvendo para o run corrente cujo E4 ainda não existe ⇒ todo input run-scoped zerado; regen não corrige | correção | Alto | P2 | procede | procede-aberto | RV2-18 **FU-2 medido** (rótulo "FIXADO" era falso) |
| RV3-12 — `EndividamentoCard.tsx:77,80` lê `d.valor`/`d.taxa`; contrato E5 emite `saldo_devedor`/`taxa_juros`/`parcela_mensal` sem adapter no boundary | consistência | Alto | P2 | procede | procede-aberto | owner: senior-cto · `types/report-analysis.ts:137-145` desalinhado |
| RV3-13 — `diagnostico_confianca` é a única chave top-level do view-model com **zero consumidores**; `dataQualitySignals.ts:54-67` recomputa o share no cliente sobre outra janela ⇒ três percentuais para o mesmo conceito na mesma tela | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer · [[ADR-353]] degrada mas não surfaça |
| RV3-14 — prazo de IF impresso como fato (`HeroKpiGrid.tsx:266-271`, `Stat "Ano projetado"`) com `if_monte_carlo.prob_if_ate_idade_meta` e divergência vs `p50_ano_if` só em `text-xs` | clareza-ux | Médio | P2 | procede | procede-aberto | owner: product-designer+financial-planner |
| RV3-15 — `ParecerRisksTable.tsx:41,93`: `TOP_LIMIT` fixo com rótulo hardcoded "de baixa severidade" para o resto, enquanto a composição real do `extra` inclui severidade média | clareza-ux | Médio | P3 | procede | procede-aberto | owner: product-designer · print CSS já força expansão no PDF |
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
| RV3-28 — ponteiros `section_id` do parecer apontam seções que não hospedam o card citado; **o mapa de referência é ele mesmo incoerente** (`report_layout.yaml:356` titula S8 por um domínio cujo card vive em S7) | consistência | Médio | P2 | procede (reenquadrado) | procede-aberto | severidade Alto original presumia ponteiro navegável (é texto puro) |
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
