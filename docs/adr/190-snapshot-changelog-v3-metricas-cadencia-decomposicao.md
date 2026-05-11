---
id: ADR-190
type: adr
title: "Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica"
status: Proposto
phase: A11
date: "2026-05-11"
relates_to:
  - "[[ADR-148]]"
  - "[[ADR-076]]"
  - "[[ADR-090]]"
  - "[[ADR-117]]"
  - "[[ADR-143]]"
  - "[[ADR-187]]"
supersedes: []
superseded_by: []
aliases: ["ADR 190", "Snapshot Changelog v3", "Variação vs. relatório anterior"]
tags:
  - area/report
  - area/methodology
  - area/pipeline
  - phase/a11
  - status/proposto
  - type/adr
---

## Contexto

ADR-148 introduziu o `SnapshotChangelogBuilder` (v2.D.1) que compara dois
snapshots de `analyze_finances` e produz:

- `ComparisonItem[]` — tabela "Antes/Depois/Δ" por seção (5 métricas
  default: `S1=Patrimônio Líquido`, `S2=Receita Total`, `S3=Patrimônio
  Bruto`, `T2=Aportes`, `T5=Despesas Totais`).
- `ChangelogEntry[]` — narrativa só para seções que cruzam threshold
  (filtra `stable`).

A UI renderiza ambos embutidos dentro de S1/S2/S3 do relatório via
`SectionSnapshotDiff` ([frontend/src/components/report/SectionSnapshotDiff.tsx](../../frontend/src/components/report/SectionSnapshotDiff.tsx)).

Em 2026-05-11 o produto-owner sinalizou que o card **não comunica**:
"esse card não diz nada, fica difícil de entender. Antes e Depois do
quê?". Revisão paralela `product-designer` + `financial-planner`
produziu diagnóstico convergente em três camadas:

1. **UX/forma:** sem moldura temporal, `stable` polui (linha com Δ 0,0%
   num card "o que mudou"), glifos sem legenda, localização por-seção
   perde paralelismo cross-section.
2. **Localização:** card embutido em cada seção dilui leitura
   comparativa — padrão Monarch/Copilot/Mercury põe "what changed"
   como bloco único no topo.
3. **Métricas/domínio:** S3 "Patrimônio Bruto" dentro de seção UI
   "Investimentos" é semanticamente errado; "Receita Total" sozinha
   carrega ruído sazonal (13º/bônus); falta taxa de poupança, distância
   até IF, max desvio AUVP, meses de reserva; comparação MoM crua tem
   volatilidade de mark-to-market que mascara mudança real (ex.: aporte
   R$ 200k + drawdown R$ 200k → PL "estável" mas tese executou).

Quick wins de UX (título + caption + supressão de `stable` + supressão
de card vazio) entraram em `agent/snapshot-diff-quickwins/*` como
mitigação imediata. Esta ADR formaliza a decisão estrutural para v3.

## Decisão

Promover o `SnapshotChangelogBuilder` para **v3** com 6 decisões
co-irrogadas (todas exigem coordenação backend ↔ pipeline ↔ UI):

### D1 — Métricas expandidas, alinhadas a Perini/Cerbasi/AUVP

Conjunto canônico de seções a comparar passa de 5 para até 10, agrupadas
por metodologia de referência:

| ID | Métrica | Path no E5 (proposto) | Polaridade |
|---|---|---|---|
| `M_PL` | Patrimônio Líquido | `patrimonio.liquido` | asset |
| `M_PI_LIQUIDO` | Patrimônio Investível Líquido (exclui imóvel uso próprio — Perini) | `patrimonio.investivel_liquido` | asset |
| `M_TAXA_POUPANCA` | Taxa de poupança = (receita − despesa) ÷ receita (Cerbasi) | `fluxo_caixa.taxa_poupanca_pct` | asset (pp) |
| `M_APORTES_PCT` | Aportes ÷ receita líquida média 3M (Cerbasi) | `fluxo_caixa.aportes_pct_receita` | asset (pp) |
| `M_DESPESA_MM3` | Despesa total — média móvel 3M (anti-sazonal) | `fluxo_caixa.despesa_total_mm3` | expense |
| `M_DIVIDA_PCT` | % renda comprometida com dívida (Cerbasi <30%) | `endividamento.pct_renda_comprometida` | expense |
| `M_RESERVA_MESES` | Meses de reserva de emergência | `reserva_emergencia.meses_cobertos` | asset |
| `M_IF_ANOS` | Anos até independência (Perini: PL_investível ÷ meta_300) | `independencia.anos_restantes` | expense |
| `M_AUVP_DESVIO` | Max desvio absoluto vs alocação alvo (pp) | `alocacao.max_desvio_pp` | expense |
| `M_SCORE` | Score patrimonial agregado | `score.valor` | asset |

`S2 Receita Total`, `S3 Patrimônio Bruto`, `T2 Aportes (R$)`, `T5
Despesa Total (R$)` saem do default — viram opt-in via
`SnapshotChangelogConfig.sections_to_compare` para retro-compat. A label
de S3 ("Patrimônio Bruto") dentro da seção UI "Investimentos" é
abandonada — substituída por `M_AUVP_DESVIO` ou `M_PI_LIQUIDO`,
conforme contexto.

### D2 — Cadência por métrica, configurável (anti-ruído)

`SnapshotChangelogConfig` ganha `cadence_for(metric_id) → Cadence`
(enum: `mom`, `mom_mm3`, `yoy`, `ytd`). Defaults:

- `M_PL`, `M_PI_LIQUIDO` → `yoy` (mark-to-market mensal é ruído).
- `M_TAXA_POUPANCA`, `M_APORTES_PCT` → `mom_mm3` (suaviza sazonalidade).
- `M_DESPESA_MM3` → MM3 já no path; cadência `mom` sobre MM3.
- `M_RESERVA_MESES`, `M_DIVIDA_PCT` → `mom`.
- `M_IF_ANOS`, `M_AUVP_DESVIO`, `M_SCORE` → `mom`.

`SnapshotPairLoader` ganha `load_snapshot_window(workspace_id, anchor,
cadence) → (prev, curr)` que resolve o snapshot prev conforme cadência
(mês anterior para `mom`, mesmo mês ano anterior para `yoy`, etc.).
Snapshot prev `None` ⇒ item suprimido individualmente (não o card
inteiro).

### D3 — Direção semântica explícita por métrica

`SECTION_POLARITY` em `narratives.py` é promovido a contrato público em
`SnapshotChangelogConfig.direction_positive: Mapping[str, "up"|"down"]`.
Default seguindo a tabela D1 (asset → up positivo; expense → down
positivo). UI consome via DTO e aplica cor inversa quando
`direction_positive == "down"` (ex.: dívida ↑ pinta vermelho mesmo com
`delta_signal == "up"`).

`ComparisonItemRead` ganha campo `direction_positive: Literal["up",
"down"]` no wire. `ComparisonItemsBlock` lê o campo e calcula
`is_positive_for_user = (delta_signal === direction_positive)` —
`is_positive_for_user=true` → verde; `false` → vermelho; `stable` →
neutro.

### D4 — Threshold por métrica, em pp ou R$ absoluto

`SnapshotChangelogConfig.thresholds` aceita override por métrica. Default
recomendado pela revisão `financial-planner`:

| Métrica | Stable se |
|---|---|
| `M_PL` MoM | \|Δ\| < 2% ou < R$ 20k |
| `M_PL` YoY | \|Δ\| < 5% |
| `M_PI_LIQUIDO` | \|Δ\| < 3% |
| `M_TAXA_POUPANCA` | \|Δ\| < 3 pp |
| `M_APORTES_PCT` | \|Δ\| < 3 pp |
| `M_DESPESA_MM3` | \|Δ\| < 5% |
| `M_DIVIDA_PCT` | \|Δ\| < 2 pp |
| `M_RESERVA_MESES` | \|Δ\| < 0,5 mês |
| `M_IF_ANOS` | \|Δ\| < 0,3 ano |
| `M_AUVP_DESVIO` | \|Δ\| < 2 pp |

Threshold em pp **ou** R$ absoluto: `ThresholdRule` value object aceita
`pct: Decimal | None` e `abs_brl: Decimal | None`; signal é `stable` se
**ambos** abaixo do respectivo limite (lógica OR).

### D5 — Decomposição patrimonial (Δ aporte vs. Δ mercado)

Dado o risco metodológico identificado (aporte + drawdown que se
cancelam → PL "estável" mascara movimento), o E5 passa a emitir
`patrimonio.variacao_decomposta`:

```json
{
  "delta_total_brl": "3500.00",
  "delta_aporte_brl": "10000.00",
  "delta_resgate_brl": "-5000.00",
  "delta_rendimento_brl": "2000.00",
  "delta_valuation_brl": "-3500.00"
}
```

Soma deve fechar com `delta_total_brl` (invariante de teste). Quando
disponível, o card v3 substitui a linha única "Patrimônio Líquido — Δ
0%" por **waterfall mini-chart** (Aporte / Resgate / Rendimento /
Valuation → Δ total) — tese AUVP+Cerbasi: cliente precisa distinguir
mérito do hábito (aporte) de sorte do mercado (valuation).

Decomposição é opt-in em v3 — se `patrimonio.variacao_decomposta`
ausente no E5 (relatórios antigos), card cai no fallback v2.8 (tabela
plain). Não é breaking.

### D6 — Localização cross-section dedicada

Card "Variação vs. relatório anterior" sai de S1/S2/S3 e vira
**seção própria** logo após `<ExecutiveSummarySection>`, com `id="V0"`
(`V` de _variação_) em [config/report_layout.yaml](../../config/report_layout.yaml).
Justificativa:

1. Comparação é cross-section por natureza — ler "Patrimônio ↑2%,
   Despesas ↑18%, Aportes ↓40%" junto conta a história.
2. Reduz ruído em S1/S2/S3 (composição "agora" vs. evolução
   temporal competem cognitivamente).
3. Padrão Monarch/Copilot/Mercury: "what changed this month" é
   destaque, não nota de rodapé por seção.

Wrappers `<SectionSnapshotDiff sectionId="S1|S2|S3" />` removidos. O
codegen `dev/codegen_report_layout.py` propaga a mudança para o
`frontend/src/generated/report-layout.ts`.

## Trade-offs

**Pró:**

- Card passa a comunicar — moldura temporal explícita + métricas com
  semântica financeira clara + decomposição que revela aporte vs.
  mercado.
- Direção semântica por métrica resolve viés positivo do verde
  cromático (dívida ↑ vermelho).
- Cadência por métrica reduz ruído MoM em patrimônio (revisão FP).
- Schema E5 expandido viabiliza outros cards (score temporal, drift de
  alocação) sem nova ADR.

**Contra:**

- Schema E5 cresce (~12 campos novos em ~5 paths). Migration de E5
  cache não é destrutiva (campos opcionais), mas exige re-emit para
  relatórios mais antigos verem v3 — ou cair no fallback v2.8.
- 10 métricas vs. 5 atuais → ruído potencial se mal configurado. Mitigar
  com defaults conservadores e card limitado a top-N por relevância
  (Δ% absoluto).
- Mover para seção dedicada (D6) quebra paridade visual com
  `EXEMPLO_DE_RELATORIO.html` — exige update do exemplo + revisão
  product-designer da seção `V0`.
- Decomposição patrimonial (D5) exige cálculo no E5 que depende de
  rastreamento de aportes vs. resgates por classe — pode demandar
  enriquecimento de `analyze_finances` que ainda não está pronto.
  Risco rastreado no plano canônico.

## Alternativas consideradas

1. **Manter v2.8 com só quick wins (título + caption + suprimir
   stable).** Mantém embutido, mantém métricas atuais. Rejeitado: a
   crítica do usuário ("não diz nada") é semântica, não só de moldura
   — quick wins não cobrem decomposição nem cadência.

2. **Adicionar só decomposição (D5) sem expandir métricas (D1).**
   Resolve o pior risco metodológico mas mantém "Receita Total" sazonal
   e ausência de taxa de poupança. Rejeitado: revisão FP foi explícita
   que receita bruta MoM é estruturalmente ruidosa.

3. **Card cross-section (D6) sem expandir métricas.** Resolve
   localização e paralelismo mas mantém problemas de fundo. Rejeitado
   pelo mesmo motivo.

## Plano de execução

Detalhado em `docs/plan/SNAPSHOT_CHANGELOG_V3/_README.md` — 4 ondas:

- **W1 (quick wins):** ✅ entregue em `agent/snapshot-diff-quickwins/*`.
- **W2 (direção semântica + threshold):** D3 + D4 — backend +
  pipeline + UI; sem mudança de E5.
- **W3 (métricas + cadência):** D1 + D2 — expande schema E5,
  `SnapshotPairLoader` ganha janela, defaults novos.
- **W4 (decomposição + cross-section):** D5 + D6 — schema E5
  ganha `variacao_decomposta`, layout do relatório ganha `V0`.

Cada onda é independente e pode mergear sozinha — defaults conservadores
garantem que ondas parciais não regridem v2.8.

## Critério de aceite

1. ADR `Proposto` → `Decidido (A11)` no merge do PR de W2 (primeira onda
   estrutural).
2. Testes empíricos: `tests/pipeline/domain/services/test_snapshot_changelog.py`
   cobre 6 cenários por métrica (asset/expense × up/down/stable),
   `backend/tests/test_reports.py` valida payload com `direction_positive`
   no wire, `frontend/tests/components/report/snapshotChangelog.test.tsx`
   valida cor invertida para `expense` com `delta_signal=up`.
3. Schema E5 validado contra `config/schemas/analyze_finances.schema.json`
   atualizado (campos opcionais — não-breaking).
4. Decomposição (D5): soma `delta_aporte + delta_resgate +
   delta_rendimento + delta_valuation` == `delta_total` (teste de
   invariante).
5. Smoke test humano: card V0 num relatório real entrega "consigo
   responder em <15s o que mudou desde o último relatório".
