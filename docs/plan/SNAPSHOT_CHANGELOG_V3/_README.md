---
id: PLAN-snapshot-changelog-v3
type: plan
title: "Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica"
status: in_progress
sprint_origem: A11
sprint_atual: null
sprints_envolvidas: ["A11", "A40"]
created_at: "2026-05-11"
last_review: "2026-08-10"
adrs_canonical:
  - "[[ADR-190]]"
  - "[[ADR-148]]"
tags:
  - type/plan
  - area/report
  - area/methodology
  - area/pipeline
  - sprint/a11
  - status/in-progress
---

# Plano canônico — Snapshot changelog v3

> Plano multi-onda para evoluir o `SnapshotChangelogBuilder` ([[ADR-148]]
> · v2.D.1) → **v3** ([[ADR-190]] · A11). Decisões D1–D6 são
> independentes em onda, mas convergem para um único card "Variação
> vs. relatório anterior" que comunica de verdade.

## Origem

Sessão 2026-05-11 — usuário (CEO + planejador financeiro do produto)
sinalizou: _"esse card não diz nada, fica difícil de entender. Antes e
Depois do quê?"_ Revisão paralela `product-designer` +
`financial-planner` produziu diagnóstico convergente em três camadas:
UX/forma, localização, métricas/domínio. Detalhe em [[ADR-190]] §Contexto.

## Premissas

1. **Schema E5 cresce, mas é não-breaking.** Campos novos em
   `analyze_finances.content_json` são opcionais — relatórios antigos
   continuam renderizando v2.8 (fallback) até regenerar com pipeline v3.
2. **Direção semântica precede expansão de métricas.** Sem
   `direction_positive` no wire, expandir métricas (D1) renderiza
   dívida ↑ verde — pior que problema atual.
3. **Decomposição patrimonial (D5) depende de rastreamento de aporte
   vs. resgate no E5.** Se o cálculo ainda não está disponível, W4
   entrega só D6 (cross-section) e D5 vira lane separada com
   pré-requisito de domínio.
4. **Defaults conservadores.** Threshold por métrica generoso de início
   (preferir falso-stable a falso-up); afinar com goldens reais após
   primeiros relatórios v3 em produção.

## Ondas

### W1 — Quick wins UX (✅ entregue 2026-05-11)

Branch `agent/snapshot-diff-quickwins/*`. Não exige ADR `Decidido` —
mitigação imediata do feedback do usuário.

- **Q1** ✅ Suprimir `stable` em `SectionSnapshotDiff` (filtro antes do
  primitivo).
- **Q2** ✅ Adicionar título "Variação vs. relatório anterior" + caption
  default no `ComparisonItemsBlock` (props `title`/`caption` opcionais).
- **Q3** ✅ Suprimir card vazio (já existia; coberto por teste novo).
- **Q4** ✅ Testes Vitest cobrindo Q1–Q3 (5 novos em
  `snapshotChangelog.test.tsx`).

Critério de aceite W1: usuário vê título + caption + card desaparece
quando todas as métricas da seção estão `stable`. **Atingido.**

### W2 — Direção semântica + threshold por métrica (D3 + D4)

**Status:** ✅ entregue 2026-07-03 — `direction_positive` fim-a-fim
(pipeline → DTO → UI com inversão de cor + `aria-label` de julgamento) e
`ThresholdRule(pct, abs_brl)` dual (`stable` só se ambos abaixo; boundary
`>=` sinaliza). Destrava W3/W4. ADR-190 já constava `Decidido (A11)`.

Lanes:

- **W2-T01** `pipeline`: estender `SnapshotChangelogConfig` com
  `direction_positive: Mapping[str, "up"|"down"]` (default
  `SECTION_POLARITY` de `narratives.py`); `ThresholdRule` value object
  (`pct` + `abs_brl`); `_classify_signal` consome `ThresholdRule.threshold_for`.
- **W2-T02** `backend`: `ComparisonItemRead` ganha campo
  `direction_positive: Literal["up", "down"]`. Update do snapshot OpenAPI
  + `_build_snapshot_diff` propaga.
- **W2-T03** `frontend`: `ComparisonItemView` ganha `direction_positive`;
  `ComparisonItemsBlock` calcula `is_positive_for_user` e inverte cor
  quando `direction_positive == "down"`. Tokens-only (verde/vermelho via
  `--semantic-success`/`--semantic-danger`).
- **W2-T04** `tests`: unit (`tests/pipeline/domain/services/test_snapshot_changelog.py`)
  cobre `expense` métrica com `up` → "ruim"; integ
  (`backend/tests/test_reports.py`) valida campo no payload; Vitest
  valida cor correta.

**Risco:** UI passa a ter 2 dimensões de cor (`delta_signal` × `direction_positive`).
Snapshot a11y precisa garantir que tab/aria leia "subiu — ruim" para
expense `up`, não só "subiu". Padrão `aria-label` proposto: `"{label}
{verbo} {valor} — {avaliação}"`.

Critério de aceite W2:
- `M_DIVIDA_PCT` com Δ +5% renderiza vermelho (`--semantic-danger`).
- `M_PL` com Δ +5% renderiza verde (`--semantic-success`).
- Threshold em pp E threshold em R$ ambos respeitados (`stable` se
  ambos abaixo dos respectivos limites).

ADR-190 transiciona Proposto → **Decidido (A11)** no merge de W2.

### W3 — Métricas expandidas + cadência (D1 + D2)

**Status:** ✅ entregue **em forma reduzida** na janela 2026-07-09 (ver
§Emenda 2026-07-09 da [[ADR-190]]): builder compara os campos E5 **reais**
(`taxa_poupanca_recorrente_pct` · `reserva.cobertura_meses` ·
`goals.alocacao_alvo.derived.desvio_max_pct` · `patrimonio.liquido`) em
**MoM uniforme** com par resolvido por período (colapso latest-por-período).
**Cortado desta janela (defer explícito):** `load_snapshot_window`
multi-cadência + `cadence_for` (reabrem com W5, mesmo pré-requisito);
top-N filter (≤4 métricas por construção); `M_DIVIDA_PCT` (campo
`pct_renda_comprometida` não existe no E5 — lane de enriquecimento);
`M_SCORE`/`M_IF_ANOS`/`M_DESPESA_MM3` cortadas por anti-metodológicas em
delta mensal. Texto original das lanes abaixo mantido como histórico.

> **Residual W3 — sufixo de changelog não renderiza em seção nenhuma
> (registrado 2026-08-05, achado pela [[A40.l4]]).** A forma reduzida acima
> trocou o default de `sections_to_compare` por **ids de métrica** (`M_PL`,
> `M_TAXA_POUPANCA`, `M_RESERVA_MESES`, `M_AUVP_DESVIO`), mas o consumidor
> (`get_report_data.py:78`) casa por `section_id` de **layout** — nenhum
> `M_*` é id de seção, então o item é computado e não tem onde pousar. É
> defeito deste plano (nasceu no corte da W3), não da A40 — roteado para cá
> pela triagem de destino do PR #1197 (a atribuição anterior "A40.l5" nunca
> aterrissou no escopo daquela lane). **Condição de retomada:** junto da W5
> (multi-cadência), ou antes se a seção V0 voltar a exibir comparativos —
> o fix é casar o vocabulário do default com o que o consumidor espera
> (mapear `M_*` → seção hospedeira ou trocar o ponto de casamento).
> Dono: quem pegar a W5. Cabe na §Emenda 2026-07-09 da [[ADR-190]], sem ADR
> nova.

Lanes:

- **W3-T01** `data-engineer review` antes do PR: schema E5 expandido
  (12 paths novos em ~5 caminhos), invariantes de cálculo
  (`taxa_poupanca_pct ∈ [-∞, 100]`, `aportes_pct_receita ∈ [0, ∞)`,
  `meses_cobertos ≥ 0`, `anos_restantes ≥ 0`).
- **W3-T02** `pipeline`: `analyze_finances` E5 calcula e emite as 10
  métricas canônicas. Onde input ausente (cliente sem dívida → sem
  `endividamento.pct_renda_comprometida`), campo é `null` e item é
  suprimido individualmente.
- **W3-T03** `pipeline`: `SnapshotPairLoader` ganha
  `load_snapshot_window(anchor, cadence) → (prev, curr)`. Cadência
  `mom_mm3`/`yoy`/`ytd` resolve via `snapshot_index` por `period_yyyymm`.
- **W3-T04** `pipeline`: `SnapshotChangelogConfig.cadence_for(metric_id)`
  + builder consome janela por métrica.
- **W3-T05** `backend`: `SnapshotChangelogConfig` default ganha as 10
  métricas (defaults D1/D2/D4 do ADR-190). Retro-compat: chamadas com
  `sections_to_compare` ainda funcionam (override explícito).
- **W3-T06** `narratives`: 10 templates novos (asset/expense × up/down/stable
  × singular/plural), pluralizando "anos" / "meses" / "pontos
  percentuais".
- **W3-T07** `frontend`: top-N filter (Δ% absoluto) para não estourar
  cardinalidade da tabela quando todos 10 cruzam threshold; default
  N=5.

**Risco principal:** cálculo de `M_AUVP_DESVIO` exige alocação alvo por
classe (config_overrides do workspace) + alocação atual (E5). Se a
alocação alvo não está configurada, métrica suprimida individualmente.

Critério de aceite W3:
- Card V0 num workspace seed mostra `taxa_poupanca_pct`, `M_PL` YoY,
  `M_DIVIDA_PCT` MoM, `M_RESERVA_MESES` MoM.
- `S2 Receita Total`, `S3 Patrimônio Bruto`, `T2 Aportes R$`, `T5
  Despesa Total R$` saem do default (mas continuam disponíveis via
  override).

### W4 — Decomposição patrimonial + seção cross-section (D5 + D6)

**Status:** **D6 ✅ entregue na janela 2026-07-09** (seção V0 após o
sumário executivo, manchete Δ PL neutra + lista de comportamento,
`SectionSnapshotDiff`/`SnapshotChangelogList` removidos). **D5 deferida
para lane própria** conforme premissa 3 + R1: o cálculo pertence ao
builder (não ao E5) e o modelo honesto é 3 baldes residuais — pré-requisito
de agregação de `transferencias_internas` por classe ([[ADR-190]] §Emenda
2026-07-09 itens 1 e 4). Texto original das lanes abaixo mantido como
histórico; W4-T05 (product-designer) executada no co-design da janela.

Lanes:

- **W4-T01** `data-engineer review`: schema E5
  `patrimonio.variacao_decomposta` (5 campos `Money.brl`). Invariante:
  soma fecha com `delta_total_brl` (tolerância R$ 0,01 para arredondamento
  cents). Bloqueia merge se invariante falha.
- **W4-T02** `pipeline`: `analyze_finances` calcula decomposição.
  Fonte: aportes/resgates vêm de transações categorizadas
  (`transferencias_internas`); rendimento + valuation vêm do delta
  saldo por classe − fluxo líquido. Risco: cliente sem `extrato` de
  corretora em E2 → decomposição ausente, fallback v2.8.
- **W4-T03** `backend`: DTO `VariacaoDecompostaRead` no payload.
- **W4-T04** `frontend`: `WaterfallVariacaoCard` substitui linha M_PL
  quando `variacao_decomposta` presente. Stack vertical: Aporte ↑ |
  Resgate ↓ | Rendimento ↑ | Valuation ↑/↓ → Δ total. Tokens-only.
- **W4-T05** `product-designer review` antes do PR: layout da seção
  `V0`, ordem das métricas, copy do título contextual ("Em abril de
  2026, em comparação com março de 2026, ...").
- **W4-T06** `pipeline + codegen`: `config/report_layout.yaml` ganha
  seção `V0` após `executive_summary`. `dev/codegen_report_layout.py`
  regenera `frontend/src/generated/report-layout.ts` e
  `backend/app/generated/report_layout.py`.
- **W4-T07** `frontend`: deleta `<SectionSnapshotDiff />` de S1/S2/S3.
  Cria `<VariacaoSection />` consumida pelo layout gerado.
  **Nota 2026-06-12:** o card "Histórico de Ciclos" do APP_E (mesmo
  `data.changelog`, duplicado no apêndice) foi **removido em PR #618**
  via [[TRACK-remove-historico-ciclos-app-e]] — W4-T07 não precisa
  tocá-lo. Ao deletar `SectionSnapshotDiff`, `SnapshotChangelogList`
  perde o último consumidor — removê-lo junto.
- **W4-T08** `tests`: invariante decomposição (W4-T01), Vitest da
  seção V0 renderizando com payload sintético, golden de E5 com
  decomposição.

Critério de aceite W4:
- Smoke humano: relatório com 6 meses de histórico mostra card V0 com
  waterfall + lista de 3-5 métricas mais relevantes.
- Soma da decomposição fecha com Δ PL (invariante de teste).
- S1/S2/S3 não têm mais `<SectionSnapshotDiff />`.
- Em caso de fallback (E5 sem decomposição ou sem cálculo de cadência
  YoY), card V0 cai para tabela plain v2.8 com aviso `caption`
  contextualizado ("comparativo limitado — primeira janela com 6 meses
  disponível em ago/2026").

### W5 — Série temporal multi-ciclo de KPIs (backlog — **bloqueada por dado**)

**Status:** backlog, não datada. **Não é "pendente" como W2–W4** —
está bloqueada por pré-requisito que ainda não existe (ver entry gate).
Nenhum agente deve pegar esta onda antes do gate abrir.

#### O que é (e por que existe)

Um **chart de linha** com a evolução de KPIs de acompanhamento ao longo
de N ciclos de relatório — a "curva" que prova disciplina entre revisões
planejador↔cliente. Candidatos a KPI (subconjunto das 10 métricas
canônicas de W3, [[ADR-190]] D1):

- `taxa_poupanca_pct` — consistência de poupança (Cerbasi);
- `M_IF_PCT` — progresso rumo à independência financeira (Perini:
  a tese de IF se prova em muitos ciclos, não num delta);
- `M_AUVP_DESVIO` (pp) — aderência à alocação alvo (AUVP);
- `M_RESERVA_MESES` — robustez da reserva;
- `M_DIVIDA_PCT` — trajetória do endividamento.

**Origem:** a remoção do card "Histórico de Ciclos" do APP_E
([[TRACK-remove-historico-ciclos-app-e]], 2026-06-12). O rótulo daquele
card **prometia** série multi-ciclo, mas o dado era um único par
t vs. t-1 (mesmo `data.changelog` dos diffs por seção). A revisão
`financial-planner` confirmou: a necessidade metodológica real é a
**série** (accountability longitudinal), não o retrospecto single-pair.
Registrar W5 aqui evita que "remover duplicata pobre" seja confundido
com "decidir que histórico multi-ciclo não tem valor".

#### O que NÃO é

- **Não é o changelog v3** (card V0 de W4): V0 responde "o que mudou
  desde o último relatório" (par único, decomposição waterfall). W5
  responde "**estou melhorando ao longo do tempo?**" (tendência).
- **Não é tabela de auditoria** de relatórios passados ([[ADR-148]]
  D2.a já rejeitou essa forma).
- **Não ressuscita** o card do APP_E — a superfície provável é nova
  (seção própria ou expansão do V0), decidida em co-design com
  `product-designer` quando o gate abrir.

#### Entry gate (pré-requisitos quantitativos — todos obrigatórios)

1. **W3 entregue** — métricas canônicas calculadas no E5 + cadência
   (`load_snapshot_window` via `snapshot_index` por `period_yyyymm`,
   W3-T03).
2. **≥3 snapshots publicados imutáveis** no workspace
   (`published_at != null`, [[ADR-187]] — mesma exigência do R5).
   Com 2 pontos não há tendência; com 3 há o mínimo honesto.
3. **`load_snapshot_window` retorna janela ≥3** em workspace seed,
   consultável sem hack (instrumentação verificada, não presumida).

#### Escopo provável (refinar quando o gate abrir)

- `pipeline`: serializar série por métrica (lista de
  `{period_yyyymm, valor}`) no payload E5 — aditivo, não-breaking
  (premissa 1 do plano).
- `backend`: DTO da série no payload do relatório + OpenAPI snapshot.
- `frontend`: chart de linha (tokens-only, `<MonetaryValue/>` onde
  monetário, máscara em snapshot visual), com co-design
  `product-designer` + `financial-planner` para escolha de KPIs
  exibidos e copy.
- **Fallback obrigatório:** workspace com <3 snapshots mostra estado
  vazio honesto ("série disponível a partir do 3º relatório — próximo
  em <mês>"), nunca chart degenerado — mesmo padrão de fallback
  contextual de W4-T08.

#### KR de valor (medido pós-entrega, separado do entry gate)

**≥2 de 3 usuários beta leem corretamente a *direção*
(melhora/piora/estável) de 2 KPIs distintos em <15s, sem ajuda.**
Task-success (HEART), anti-Goodhart: mede leitura de tendência, não
existência do chart nem tempo de tela. Consistente com o critério
global #4 deste plano.

#### Riscos próprios

| ID | Risco | Mitigação |
|---|---|---|
| W5-R1 | Workspace dogfood demora a acumular 3 snapshots publicados | Gate explícito; não promover lane antes; fallback honesto especificado |
| W5-R2 | Série de KPI com mudança de metodologia entre ciclos (ex.: recalibração de threshold W2-D4) quebra comparabilidade | Snapshot imutável ([[ADR-187]]) congela o valor da época; anotar quebras de série no chart (marcador), nunca recalcular retroativo |
| W5-R3 | Goodhart no KR (entregar só a linha "bonita" de poupança) | KR exige 2 KPIs **distintos**; seleção de KPIs é co-design, não default do dev |

### W6 — Par não-comparável: julgamento sob mudança de método (✅ caso single-pair entregue 2026-08-10)

**Status:** o caso **single-pair da V0** foi entregue por [[A40.l2]] (PR3c2b) — não é
pendência. Permanece aberta a **generalização** do predicado (ver §Deferido abaixo). Registrado
aqui porque a noção pertence ao **contrato de comparação**, não à lane que forneceu a primeira
razão para ela existir.

#### O que é (e por que existe)

A V0 **julga** cada linha: `deltaColor` pinta `--semantic-success`/`--semantic-danger` e
`deltaAriaLabel` anuncia literalmente *"avaliação boa"* / *"avaliação ruim"*
(`VariacaoSection.tsx:66-71,85-101`). Isso é correto para movimento real do dinheiro e **falso**
quando a linha se move porque a **base de cálculo mudou** — correção de método, recalibração de
threshold (W2-D4), mudança de janela canônica ([[ADR-306]]).

Origem medida: o colapso cross-documento de [[A40.l2]] remove lançamentos duplicados do razão.
No primeiro relatório pós-flip do workspace dogfood, a **única** linha renderizada da seção é
`Taxa de Poupança 34,0% → 19,6% ▼14,4 pp`, vermelha, com `aria-label` terminando em *"avaliação
ruim"* — uma acusação isolada, sem linha verde ao lado, atribuída a nada. O caso **elogioso**
existe e é estrutural (`M_RESERVA_MESES` sobe sempre que se remove despesa: numerador idêntico,
denominador menor) — hoje inerte por defeito de path (o builder aponta `reserva.cobertura_meses`;
o E5 emite `reserva_emergencia`).

**Princípio:** delta cuja composição não se conhece **não se julga** — é o mesmo que a §Emenda
2026-07-09 da [[ADR-190]] (item 4) já aplicou à manchete do M_PL ("julgar sem o waterfall induz
erro"). Aqui a causa é *conhecida e não-meritória*, o que torna o caso mais forte, não mais fraco.

#### Entregue (por [[A40.l2]] · PR3c2b)

- `comparison_base_changed` derivado em `_build_snapshot_diff` (único escopo com `prev` e `curr`),
  emitido report-level ao lado de `comparisons`/`changelog`/`comparison_periods`.
- Sob `base_changed`: cor → `--surface-muted-foreground`, `aria-label` sem cláusula de
  julgamento e com **estado nomeado**, glifo de direção **preservado**, marcador na linha com
  `aria-describedby` ancorando o caption.
- Teste de **paridade cor ≡ texto** (a R3 exige paridade entre canais, não a existência de um
  julgamento; sem o gate ela se desfaz no próximo refactor, em verde).
- Cruza zero nos **dois** sentidos: flip (0 → N) e rollback (N → 0).

#### Deferido — o predicado genérico (dono: este plano · gatilho: [[A42.l5]] ou a 2ª mudança de método)

O gatilho entregue usa `fluxo_caixa.consolidacao_cross_documento` como **proxy de método**. Ele
erra em **um** caso, **uma vez por workspace**: o workspace que adquire seu primeiro par
sobreposto pós-flip cruza 0 → N e acende o marcador sem que o método tenha mudado. Erro
conservador (suprime julgamento a mais), não bloqueante.

O predicado correto é um **identificador de método no artefato** (ausência ≡ legado; presente ≡
`cross_doc_collapse_v1`), que dispara exatamente no flip e no rollback, nunca por variação de
corpus, e generaliza para o marcador de quebra de série que a **W5-R2** vai precisar. Custa uma
trinca E3→E4→E5 + `$def`. Gatilhos de especialista ao reabrir: `data-engineer` (contrato E5) +
`product-designer` (copy do marcador).

#### Riscos próprios

| ID | Risco | Mitigação |
|---|---|---|
| W6-R1 | Alguém "conserta" o path morto `reserva.cobertura_meses` **antes** da neutralização e liga o falso-positivo **elogioso** (`+1,8 mês`, estrutural) | Ordem explícita: o conserto do path só depois de W6 shipada. Registrado no §Deferimento de [[A40.l2]] |
| W6-R2 | Proxy de presença dá falso-positivo uma vez por workspace | Aceito e nomeado acima; direção conservadora. Fecha com o identificador de método |
| W6-R3 | Neutralização report-level suprime veredito verdadeiro de métrica não-ledger no mesmo ciclo | Custo medido ≈ zero: o veredito do desvio AUVP vive no card de alocação com severidade própria. Allow-list por métrica **recusada** — acoplaria o changelog ao grafo de dependência do pipeline |

## Critério de aceite global do plano

1. **ADR-190 Decidido em `main` ao final de W2.**
2. **Schema E5 atualizado em `config/schemas/` ao final de W3.**
3. **Card V0 substitui `<SectionSnapshotDiff />` ao final de W4.**
4. **Smoke humano:** apresentar relatório com card V0 a 3 usuários
   beta; ≥2 conseguem responder em <15s "o que mudou desde o último
   relatório" (qualitativo, mesmo critério dos quick wins).
5. **Sem regressão:** relatórios pré-v3 continuam renderizando (modo
   fallback v2.8 sem cor invertida, sem decomposição) — testado via
   golden retrocompat.

## Riscos rastreados

| ID | Risco | Mitigação |
|---|---|---|
| R1 | Decomposição patrimonial (D5) exige rastreamento de aporte vs. resgate por classe — pode não estar pronto em E5 | W4-T01 valida invariante antes de mergear; se cálculo indisponível, D5 vira lane separada com pré-requisito de domínio (rastreamento de transferências internas em transações categorizadas) |
| R2 | Cardinalidade alta — 10 métricas × N sections faz card explodir visualmente | W3-T07 limita top-N (default 5) por Δ% absoluto; resto colapsável |
| R3 | Direção semântica confunde a11y — usuário com daltonismo perde sinal | W2-T04 garante `aria-label` contextual ("subiu R$ X — avaliação ruim"); não depende só de cor |
| R4 | Cadência YoY exige snapshot de mesmo mês ano anterior — workspace novo não tem | Item suprimido individualmente quando snapshot prev ausente; caption do card informa janela disponível |
| R5 | Pré-requisito `relatorio_publicado_imutavel` ([[ADR-187]]) — comparação contra snapshot antigo precisa snapshot ser imutável | Coordenar com lane A11.report-publication; comparação só usa snapshots `published_at != null` |

## Tracks operacionais

Lanes ficam em `docs/sprint/A11/lanes/snapshot-changelog-v3-{wave}.md`
quando promovidas para sprint. W1 + W2 entregues (W2 ✅ 2026-07-03, ver §W2 acima); W3-W4
priorizadas mas ainda não datadas.

## Histórico

- **2026-08-10:** aberta **W6** (par não-comparável sob mudança de método). Caso single-pair da
  V0 entregue por [[A40.l2]] no mesmo dia; predicado genérico (identificador de método no
  artefato) deferido com gatilho [[A42.l5]]. Emenda datada na [[ADR-190]]. Decisão do
  `senior-cto` após medição M1/M2 refutar a premissa do deferimento original da §D6 da lane —
  o falso-positivo previsto era elogioso; o medido é **acusatório e isolado**.
- **2026-07-09:** janela de execução (co-design 4 especialistas:
  `financial-planner` + `product-manager` + `data-engineer` +
  `product-designer`; conflito PL-sem-decomposição resolvido em 1 rodada —
  manchete neutra). W3 entregue em forma reduzida + W4/D6 entregue; D5 e
  cadência multi-janela deferidas com gatilhos explícitos. Emenda datada na
  [[ADR-190]]. Aceite da janela = smoke do owner no dogfood ("o que mudou
  e por quê em <15s"); critério global #4 (3 usuários beta) reetiquetado
  como gate de beta, permanece.
- **2026-06-12:** card "Histórico de Ciclos" (Apêndice E) marcado para
  remoção fora de W4 via [[TRACK-remove-historico-ciclos-app-e]]
  (revisão `product-designer` + `financial-planner` +
  `product-manager`: duplicata single-pair do `data.changelog`, rótulo
  enganoso, apêndice forward-looking); aberta **W5** (série temporal
  multi-ciclo de KPIs) como backlog bloqueado por dado — a lacuna
  metodológica real que o card não cobria.
- **2026-05-11:** plano criado pós-revisão paralela
  `product-designer` + `financial-planner` (sessão).
  [[ADR-190]] como Proposto, W1 entregue mesmo dia.
