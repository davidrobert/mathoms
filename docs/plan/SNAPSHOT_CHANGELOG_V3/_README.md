---
id: PLAN-snapshot-changelog-v3
type: plan
title: "Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica"
status: in_progress
sprint_origem: A11
sprint_atual: A11
sprints_envolvidas: ["A11"]
created_at: "2026-05-11"
last_review: "2026-05-11"
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

**Status:** pendente — pré-requisito de W3/W4.

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

**Status:** pendente — depende de W2.

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

**Status:** pendente — D5 pode separar para lane com pré-requisito.

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
quando promovidas para sprint. Hoje só W1 entregue; W2-W4 estão
priorizadas mas ainda não datadas.

## Histórico

- **2026-05-11:** plano criado pós-revisão paralela
  `product-designer` + `financial-planner` (sessão).
  [[ADR-190]] como Proposto, W1 entregue mesmo dia.
