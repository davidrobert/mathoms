---
id: TRACK-a19-l1-card-protecao
type: track
title: "Track A19 L1 — Card S_PROTECAO no relatório: ProtecaoAnalyzer + report_layout + componente React + reposicionamento AUVP"
lane: "[[A19.l1]]"
sprint: A19
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: product-designer
tags:
  - type/track
  - sprint/a19
  - status/ready
  - area/report
  - area/methodology
  - area/frontend
  - methodology/auvp
  - methodology/cerbasi
---

# Track A19 L1 — Card S_PROTECAO (4º pilar AUVP)

> **Lane:** [[A19.l1]] · **ADR canônica:** [[ADR-240]] §D1-D9 + §Gates · **Pré-requisito rígido:** Sprint A18 inteira em `main` (L1 + L2 + L3) · **Branch prefix:** `agent/a19-l1-card-protecao-P<N>/*`
> · **Tamanho estimado:** ~6-8d eng em 4 PRs sequenciais

## Briefing

Sem este card, ingestão da Sprint A18 (CRLV + apólice + FIPE) fica invisível — owner sobe 6 PDFs e nada aparece no relatório. Card S_PROTECAO formaliza **4º pilar AUVP (Proteção Patrimonial)** posicionado **entre S2 (Reserva) e S4 (Patrimônio)** seguindo ordem AUVP — não como anexo informativo.

[[ADR-240]] decidiu **4 KPIs canônicos V1** (G hero / B faixa / F gap qualitativo / C gap por bem auto), **3 subgrupos visuais** (Bens / Pessoas / PJ), **linguagem CRC**, **status de vigência**, **cross-link S8 Previdência**, **gating heurístico** para flag de seguros ausentes.

## Decisões já fechadas (do co-design `financial-planner` · [[ADR-240]])

- **Posicionamento AUVP-coerente** — ordem visual S2 → **S_PROTECAO** → S4 → S3 → S8 ([[ADR-240]] D1).
- **4 KPIs V1**: G (prêmio total + decomposição) hero, B (% renda em prêmios, faixas Cerbasi 1-5%), F (seguros ausentes qualitativo), C (gap cobertura por bem auto-V1) ([[ADR-240]] D2).
- **KPIs descartados V1** (V2 condicional): A (% patrimônio coberto — denominador problemático), D (multi-corretor — vira nota neutra), E (bônus em risco — exige histórico de renovação).
- **Card único com 3 subgrupos visuais**: Bens (auto + residencial), Pessoas (V2 placeholder), PJ (V2 placeholder) ([[ADR-240]] D4).
- **Status vigência por apólice**: vigente / vencendo em 30d / vencida ([[ADR-240]] D5).
- **Multi-corretor neutro com nota** — sem warning V1 ([[ADR-240]] D6).
- **Cross-link textual S8 Previdência** — componente de proteção para beneficiários ([[ADR-240]] D7).
- **Linguagem CRC estrita** — zero verbo prescritivo ("deve", "precisa", "recomendamos"); só "considere", "vale avaliar", "verifique" ([[ADR-240]] D3).
- **Gating heurístico KPI F vida**: `family_members < 18` OU `cônjuge sem renda` OU `passivo/PL > 30%`. KPI F saúde: `sem dedução IRPF` E `sem categoria E4 saúde 3+ meses`.

## Plano de fases

### P1 — Schema + fórmulas + `ProtecaoAnalyzer` (~2d)

- `config/schemas/protecao_patrimonial.schema.json` — wire string decimal ([[ADR-090]]), validação hook [[ADR-212]].
- Adicionar bloco `protecao_patrimonial` em `analise_financeira` (E5) — schema do E5 ganha campo.
- `docs/reference/FORMULAS.md` — registrar 4 fórmulas (`protecao.pct_renda`, `protecao.gap_bem_auto`, `protecao.flag_vida`, `protecao.flag_saude`) **antes** de implementar.
- `pipeline/domain/services/protecao_analyzer.py` — calcula 4 KPIs determinísticos.
- Goldens determinísticos `tests/test_protecao_analyzer.py`: 3 cenários ([[ADR-240]] G6).

**Gate P1:** `pytest tests/test_protecao_analyzer.py -q` verde + schema validation hook verde.

### P2 — Codegen `report_layout.yaml` + reposicionamento (~1d)

- [`config/report_layout.yaml`](../../../../config/report_layout.yaml) — adicionar seção `S_PROTECAO` entre `S2` e `S4`. Renumerar/reposicionar S3 (Renda) para depois de S4.
- Rodar codegen: `python3 dev/codegen_report_layout.py` ([[ADR-076]]) — regenera `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py`.
- Atualizar referências em componentes existentes que dependem da ordem (visual review).

**Gate P2:** codegen verde, snapshots de relatório (existentes) não regridem.

### P3 — Componente React `<S_ProtecaoSection/>` (~3d)

- `frontend/src/components/report/sections/S_ProtecaoSection.tsx` — segue padrão de S2/S3/S4 (hierarquia tipográfica idêntica).
- 3 subgrupos visuais:
  - **Bens** (auto + residencial — tabela LMI + FIPE + gap C)
  - **Pessoas** (V2 placeholder com copy CRC)
  - **PJ** (V2 placeholder com copy CRC)
- KPI Hero (G) — pizza com decomposição.
- KPI B — barra com faixas Cerbasi (1-3% ok, 3-5% ok+, <1% / >5% atenção).
- KPI F — chips "Vida: não identificada" / "Saúde: não identificada" quando flag dispara, com copy CRC inline.
- KPI C — por veículo: badge gap (verde <10%, amarelo 10-25%, vermelho >25%) com tooltip explicativo.
- Status vigência por apólice (vigente / vencendo / vencida com cor).
- Multi-corretor metadata neutra ("3 corretoras: Corretora Exemplo 1, Corretora Exemplo 2, Corretor PF Exemplo").
- Cross-link S8 textual no rodapé do card.
- E2E `@critical` em `frontend/e2e/protecao.spec.ts` — 3 cenários ([[ADR-240]] G6).

**Gate P3:** `cd frontend && npm run test:e2e -- protecao` verde. UI review manual: linguagem CRC, hierarquia tipográfica, ordem AUVP.

### P4 — Extensão E6-parecer + cutover + flip (~1d)

- [[ADR-199]] E6-parecer ganha narrativa de proteção quando KPI F flag dispara — extensão do prompt persona AUVP/Cerbasi (instrução: "não recomende produto específico; padrão CRC").
- Eval do parecer atualizado para refletir nova narrativa.
- Telemetria: log estruturado `mathoms.relatorio.protecao_rendered` com `{kpis_status, has_gap_vida, has_gap_saude, has_apolice_vencida}` (sem PII).
- Atualizar [docs/CHANGELOG.md](../../../CHANGELOG.md) via `docs/sprint/A19/changelog/CHG-YYYY-MM-DD-a19-l1-protecao.md`.
- Flippar [[ADR-240]] de `Proposto` para `Decidido (Sprint A19 L1)`.
- Atualizar [[A19.l1]] status → `shipped` + `ship_pr` + `ship_date`.
- Atualizar [[MOC-sprint-a19]] §Lanes com checkmark.

**Gate P4:** PR de Decidido + flip. Card aparece no relatório de dogfood do owner.

## Critério de aceite (lane completa)

Em [[A19.l1]] §Critério de aceite. Cobre card S_PROTECAO completo com 4 KPIs, 3 subgrupos visuais, linguagem CRC, reposicionamento AUVP.

## Trade-offs já decididos (não reabrir)

- KPI A (% patrimônio coberto) **descartado V1** — denominador problemático.
- Multi-corretor **neutro V1** (não warning) — fragmentação pode ser intencional.
- Vida/Saúde/PJ **placeholder V1** — schema preparado, ativar quando V2.
- Recomendação de produto **proibida** — viola CRC + memória [[ADR-238]] D8.
