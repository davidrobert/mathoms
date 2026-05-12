---
id: TRACK-auvp-threshold-pgbl-variant
type: track
title: "Track AUVP threshold modula variante PGBL (M2 do ADR-189)"
sprint: A12
status: consumed
created_at: 2026-05-12
consumed_at: 2026-05-12
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/consumed
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# Track AUVP threshold modula variante PGBL no estado `capacidade_disponivel`

> **Lane ID:** auvp-threshold-pgbl-variant
> **Branch prefix:** `agent/auvp-threshold-pgbl-variant/*`
> **Depende de:** [[ADR-157]] (capacidade ≠ recomendação), [[ADR-189]]
> (PGBL diagnóstico tipificado em 4 estados), [[ADR-194]] (cards
> Dependentes + Dedutíveis reativados — mesma seção).
> **Origem:** ADR-189 §6 listou esta lane como M2
> ("threshold subjetivo para modular variante — pode virar ADR futura").
> **Supervisão obrigatória:** **G0 (`financial-planner`)** — define
> threshold subjetivo (alíquota mínima + horizonte) que **toca a linha**
> "capacidade ≠ recomendação" do [[ADR-157]]. **G4 (`product-designer`)**
> — escolha de variante por tier sem virar scorecard/gamificação.
> **G2 (`data-engineer`) dispensado:** payload `irpf_kpis` intocado.

> **Objetivo (1 frase):** dentro do estado `capacidade_disponivel`,
> modular variante (`info`/`neutral`) + sufixo factual do subtitle em
> função de threshold determinístico sobre alíquota efetiva
> (`aliquota_sobre_tributavel_pct`), preservando literal o parágrafo
> + disclaimer congelados por G0 anterior em ADR-189 §6.1.

---

## Por que esta lane

### Sintoma

ADR-189 entregou o card em 4 estados, mas dentro de
`capacidade_disponivel` a variante é `info` uniforme — não diferencia
usuário com alíquota efetiva ~28% (AUVP pleno: PGBL faz sentido) de
usuário com alíquota ~7,5% (PGBL marginal/contra-indicado). Seção
"Otimização Tributária" perde a oportunidade de contextualizar
**quanto vale** a capacidade dedutível mostrada.

### Restrição

[[ADR-157]] estabeleceu: capacidade ≠ recomendação. Zero CTA, zero
endorsement de produto. Threshold AUVP modula **intensidade visual**
(variant) + sufixo factual ("alíquota efetiva alta/intermediária/
baixa") — não cruza para prescrição. Linha protegida pelo G0.

---

## Co-design consolidado · 2026-05-12

Vereditos paralelos:

- **G0 (`financial-planner`):** APROVA COM AJUSTE. Alíquota a usar =
  `aliquota_sobre_tributavel_pct` (a dedução PGBL incide sobre essa
  base). Threshold X=20% (corte aderente; faixas marginais 22,5/27,5%
  IR 2024) / Y=12% (corte abaixo; ganho marginal consumido por taxa
  adm.). Horizonte fora do MVP (sem campo idade). Linha ADR-157
  preservada.
- **G4 (`product-designer`):** APROVA COM AJUSTE. Rejeita `feature`
  no tier `auvp_aderente` (colide semanticamente com `no_teto` que é
  "decisão consumada" — usar `feature` em capacidade não-usada vira
  endorsement implícito). Mapeamento conservador:
  `auvp_aderente/neutro → info` (visualmente iguais), `abaixo →
  neutral` (apaga sutil sem julgar). Sufixo factual obrigatório
  ("alíquota efetiva alta/intermediária/baixa") para WCAG 1.4.1.

**Divergência G0 × G4 resolvida pelo senior-cto (1 rodada, anti-loop):**

- Variante: **G4 vence** — `auvp_aderente → info` (não `feature`).
  Salvaguarda ADR-157 é o invariante mais forte; G4 protege-o melhor.
- Threshold X/Y: **G0 vence** — 20% / 12%.
- Sufixo: **G4 vence** — "alíquota efetiva alta/intermediária/baixa"
  é factual descritivo do user, sem aproximar de prescrição.

ADR canônica: **[[ADR-195]]** (Proposto → Decidido (A12) no merge).

---

## Regras inegociáveis

- **Sem CTA, sem recomendação de produto/banco/regime.** [[ADR-157]]
  é cláusula pétrea.
- **Não alterar payload `irpf_kpis`.** Threshold resolvido
  inteiramente no client — `aliquota_sobre_tributavel_pct`,
  `pgbl_status` já existem.
- **Parágrafo principal + disclaimer literal** do estado
  `capacidade_disponivel` (ADR-189 §4 / §6.1) **não muda**. Único
  delta é o **sufixo do subtitle**.
- **Sem variante visual nova** no design system — só vocabulário
  existente (`info`, `neutral`).
- **Sem proxy de idade declarada no MVP.** Horizonte é
  explicitamente fora do MVP — registrado §5 do ADR-195 como lane
  futura.

---

## Passos executados

1. **Co-design paralelo (S0):** `financial-planner` (G0) +
   `product-designer` (G4) invocados em 1 mensagem. Senior-cto
   resolveu divergência em 1 rodada (anti-loop).
2. **ADR-195 escrita** (`docs/adr/195-pgbl-threshold-auvp-modula-variante.md`)
   como `Proposto`. §3.1 documenta a divergência G0×G4 + resolução.
3. **Helper puro:** `frontend/src/lib/irpf/pgbl-auvp-fit.ts`
   exporta `evaluatePgblAuvpFit(kpis) → AuvpFitResult` + constantes
   `AUVP_ADERENTE_THRESHOLD_PCT = 20`, `AUVP_ABAIXO_THRESHOLD_PCT = 12`.
4. **Wiring no card:** `IrpfPgblCapacidadeCard.tsx` consome o helper
   **apenas** no estado `capacidade_disponivel`. Outros 3 estados
   inalterados.
5. **Vitest:** `frontend/tests/lib/pgblAuvpFit.test.ts` (cobertura
   helper 13 cenários, edge limites X/Y) + extensão de
   `frontend/tests/components/IrpfSections.test.tsx` com 4 cenários
   visuais (aderente, neutro, abaixo, indeterminado) preservando
   asserts ADR-189.
6. **Gates locais:** `pre-commit run --all-files` + `npm test`.
7. **PR:** `feat(report): threshold AUVP modula variante PGBL
   (capacidade_disponivel) — ADR-195`.

---

## Critério de aceite (espelha ADR-195 §7)

1. ADR-195 Proposto → Decidido no commit-merge.
2. Helper puro testável fora de React.
3. Card consome helper **apenas** em `capacidade_disponivel`.
4. Vitest cobre ≥ 4 cenários + persistência ADR-189.
5. CI verde + zero mudança no backend / payload.

---

## Não-objetivos (explícitos)

- **Proxy de idade declarada** — lane futura quando payload tiver
  `data_nascimento` por declarante.
- **Tendência de alíquota** (`evolucao_renda_anos`) — fora do MVP.
- **Comparativo regime regressiva vs progressiva** — disclaimer já
  cobre.
- **Reconciliar S7 `previdencia_pgbl` × IRPF declarado** — lane
  separada (já registrada em [[ADR-189]] §6).
- **Cross-card com `IrpfDedutiveisAplicadosCard`** (subcategoria
  `pgbl`) — ambos coexistem; reconciliação visual não escopo aqui.
