---
id: CHG-2026-05-12-FEAT-REPORT-S9-EXPANSION
type: changelog-entry
date: "2026-05-12"
sprint: A11
lane: "[[A11.w5]]"
adrs:
  - "[[ADR-192]]"
prs: []
commits: []
summary: |
  feat(report): S9 expandida — 4 cards + bubble re-enquadrado
  (ADR-192 §D4, S9-T04 · Sprint A11.W5 · s9-riscos-expansion).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/frontend
  - area/design-system
---

# feat(report): S9 expandida — 4 cards + bubble re-enquadrado (S9-T04)

Track `s9-riscos-expansion` — onda 2 (T04). Materializa os 5 blocos
consensuais da ADR-192 §D4 no renderer React. Bundle ainda vem vazio
até T03 mergear; cards renderizam estados degradados coerentes
(KPIs "a calcular", checklist com pendências, lista de ações vazia).

**Implementação:**

- `config/report_layout.yaml` §S9 expandido: 4 cards (`hero_gap_protecao`,
  `cobertura_seguros`, `sucessao`, `acoes_mitigacao`) + bubble re-enquadrado
  (`bubble_riscos` agora só plota compliance/sucessório).
- `python3 dev/codegen_report_layout.py` regenerou
  `frontend/src/generated/report-layout.ts` +
  `backend/app/generated/report_layout.py` (commitados juntos).
- 4 cards novos em `frontend/src/components/report/cards/`:
  - `HeroGapProtecaoCard.tsx` — KPI protagonista (Capital × Recomendado ×
    Gap) com 4 estados (empty/covered/partial/critical), ícone
    `AlertOctagon` quando gap material, lista de categorias com gap.
  - `CoberturaSegurosCard.tsx` — tabela 6×5 (categoria × status × capital ×
    prêmio/mês × vigência); mobile (`<md`) vira cards empilhados; padrão
    tipográfico de `PrevidenciaPgblCard`.
  - `SucessaoCard.tsx` — checklist de 4 items (testamento, beneficiários
    previdência, holding, ITCMD); `ReportCard variant="warn"` quando há
    gap; ITCMD aparece quando T03 popular `gap_analysis.sucessorio.ideal_brl`.
  - `AcoesMitigacaoCard.tsx` — lista priorizada de recomendações + bloco
    "Riscos auto-inferidos" com botão "Aceitar como Risco" (placeholder
    estático até T05 implementar o handler real).
- `NarrativeChartCard.tsx` ganha prop `mitigationLegend` para a 3ª
  dimensão (cor) do bubble: verde coberto / amarelo parcial / vermelho
  descoberto. Tokens via `var(--semantic-gain/warning/loss)`.
- `S9RiscosSection.tsx` consome o bundle via `data.protection_bundle` e
  compõe os 4 cards + bubble re-enquadrado; preserva empty state T01.
- `protectionBundle.types.ts` — interfaces TS espelhando
  `pipeline/domain/protection_bundle.py` + DTOs Pydantic.

**Disclaimers fiduciários:** COPY_GUIDELINES.md §13.2 — atribuição
direta a fontes metodológicas é proibida; usamos a substituição
canônica "metodologia consagrada de planejamento patrimonial brasileiro"
+ contexto (wealth management, sucessório BR). Disclaimer presente em
cada card que cite cobertura recomendada.

**Acessibilidade:**

- `role="region"` + `aria-labelledby`/`aria-describedby` em cada card.
- Tabela em `CoberturaSegurosCard` ganha `<caption>` + `aria-label`.
- Status badges com `aria-label` semântico (Contratado/Parcial/Ausente).
- Botão "Aceitar como Risco" com `aria-label` descritivo por risco.

**Responsive:** mobile (`<md`) — tabela de seguros vira cards empilhados;
desktop mantém grid.

**EXEMPLO_DE_RELATORIO.html §S9:** trecho substituído pelos 5 blocos
paritários (mesma estrutura React) — fonte viva de paridade visual
atualizada no mesmo PR.

**Testes:** `frontend/tests/components/report/S9ProtectionCards.test.tsx`
— 15 specs cobrindo estados vazio/preenchido, ordenação por prioridade,
ARIA, disclaimers (15/15 passing).

**Goldens visuais Playwright:** não regenerados neste PR — CI vai
detectar drift no `S9-light-visual` e `S9-dark-visual`; baselines serão
re-aprovadas em PR de follow-up (visual snapshot drift é esperado em
mudança de seção desta magnitude).

**Próximos passos:** T03 mergea calculators (4 calculators + bundle
populado); T05 implementa UI de cadastro `/protecao` + handler do
botão "Aceitar como Risco"; T06 reseta goldens E5.
