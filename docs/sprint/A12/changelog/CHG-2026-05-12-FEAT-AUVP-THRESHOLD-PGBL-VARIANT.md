---
id: CHG-2026-05-12-FEAT-AUVP-THRESHOLD-PGBL-VARIANT
type: changelog-entry
date: "2026-05-12"
sprint: A12
lane: "[[TRACK-auvp-threshold-pgbl-variant]]"
adrs:
  - "[[ADR-195]]"
prs: [225]
commits: ["5766077"]
summary: |
  feat(report): threshold AUVP modula variante visual do card
  `IrpfPgblCapacidadeCard` no estado capacidade_disponivel — ADR-195
  Decidida (A12). Follow-up M2 do ADR-189 §6.
tags:
  - type/changelog-entry
  - sprint/a12
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# feat(report): threshold AUVP modula variante PGBL no estado capacidade_disponivel

Implementa o follow-up M2 listado em [[ADR-189]] §6 — threshold
determinístico sobre `aliquota_sobre_tributavel_pct` modula
intensidade visual (`variant`) + sufixo factual do subtitle dentro
do estado `capacidade_disponivel` do `IrpfPgblCapacidadeCard`.
[[ADR-195]] **Decidida (A12)** no merge ([apps#225](https://github.com/davidrobert/mathoms/pull/225)).

**Co-design 2026-05-12** — `financial-planner` (G0) +
`product-designer` (G4) em paralelo (1 mensagem, 2 vereditos);
`data-engineer` (G2) **dispensado** porque payload `irpf_kpis` não
muda. Threshold resolvido inteiramente no client.

- **G0 (financial-planner):** APROVA. Alíquota a usar =
  `aliquota_sobre_tributavel_pct` (a dedução PGBL incide sobre essa
  base; usar `aliquota_sobre_total` diluiria perfil PJ com muito
  isento). Threshold X=20% (corte aderente; centro das faixas
  marginais 22,5/27,5% IR 2024) / Y=12% (corte abaixo; ganho marginal
  consumido por taxa adm.). Horizonte fora do MVP (sem campo
  idade — lane futura). Linha [[ADR-157]] preservada (zero CTA).
- **G4 (product-designer):** APROVA COM AJUSTE. **Rejeita** `feature`
  no tier `auvp_aderente` (colide semanticamente com `no_teto`, único
  portador de `feature` por ser "decisão fiscal consumada"; usar em
  capacidade não-usada vira endorsement implícito). Mapeamento
  conservador: `aderente/neutro → info` (visualmente iguais), `abaixo
  → neutral` (apaga sutil sem julgar). Sufixo factual obrigatório
  para WCAG 1.4.1 ("alíquota efetiva alta/intermediária/baixa").

**Divergência G0 × G4 resolvida em 1 rodada pelo senior-cto (anti-loop):**

- Variante — G4 vence (salvaguarda [[ADR-157]] mais forte).
- Threshold X/Y — G0 vence (20% / 12%).
- Sufixo — G4 vence (factual descritivo, sem aproximar de prescrição).

Documentado em [[ADR-195]] §3.1.

**Mapeamento canônico ([[ADR-195]] §4):**

| Tier              | Variante  | Sufixo subtitle                          |
|-------------------|-----------|------------------------------------------|
| `auvp_aderente`   | `info`    | · alíquota efetiva alta                  |
| `neutro`          | `info`    | · alíquota efetiva intermediária         |
| `abaixo`          | `neutral` | · alíquota efetiva baixa                 |
| `indeterminado`   | `info`    | (omitido — fallback silencioso)          |

**Entregue:**

- **Frontend (helper puro):**
  - `frontend/src/lib/irpf/pgbl-auvp-fit.ts` —
    `evaluatePgblAuvpFit(kpis) → AuvpFitResult` com
    constantes `AUVP_ADERENTE_THRESHOLD_PCT = 20` e
    `AUVP_ABAIXO_THRESHOLD_PCT = 12`. Função pura, sem dependência
    de React, testável fora do componente. Decomposta em
    `indeterminado`/`tierResult`/`classifyByAliquota` para
    respeitar baseline T3 (funções ≤ 20 linhas).
- **Frontend (card):**
  - `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx`
    consome o helper **apenas** no estado `capacidade_disponivel`.
    Outros 3 estados (`modelo_simplificado`, `no_teto`,
    `sem_renda_tributavel`) inalterados. **Parágrafo + disclaimer
    literal de [[ADR-189]] §4 / §6.1 preservados** — único delta é
    o sufixo do subtitle.

**Testes:**

- Vitest `frontend/tests/lib/pgblAuvpFit.test.ts`: 16 cenários
  (4 tiers + edge limites X=20 / Y=12 exatos + alíquota = 0%
  + alíquota negativa + alíquota string vazia + alíquota
  não-numérica + 3 estados `pgbl_status` ≠ `capacidade_disponivel`
  + imutabilidade do input).
- Vitest `frontend/tests/components/IrpfSections.test.tsx` estendido
  com 4 cenários visuais novos (aderente, neutro, abaixo,
  indeterminado por alíquota inválida) preservando os 4 estados
  ADR-189 + persistência da copy literal (disclaimer "Não é
  recomendação", lista AUVP "tabela regressiva vs. progressiva /
  horizonte de resgate / taxa de administração / INSS").
- Suíte Vitest completa: **927/928 verde** (1 skipped
  pré-existente). Code-style baseline: **0 regressão**.
- Regressão pytest `tests/test_irpf_analyzer_pgbl_status.py`: 13/13
  ([[ADR-189]] não regride — backend intocado).

**Não-objetivos** (ver [[ADR-195]] §6):

- Proxy de idade declarada para inferir horizonte de resgate —
  lane futura quando payload tiver `data_nascimento` por declarante.
- Tendência de alíquota (`evolucao_renda_anos`) — fora do MVP.
- Comparativo regime regressiva vs progressiva PGBL — disclaimer
  literal já cobre.
- Reconciliação S7 `previdencia_pgbl` × IRPF declarado — lane
  separada (já registrada em [[ADR-189]] §6).
- Cross-card visual com `IrpfDedutiveisAplicadosCard` (subcategoria
  `pgbl`) — ambos coexistem; reconciliação visual não escopo aqui.

**Limitações registradas** (revisitar se telemetria pós-GA sinalizar):

- 2 tiers `info` adjacentes (`auvp_aderente` e `neutro`) só
  distinguem por texto — em scan rápido podem se confundir.
- Tier `abaixo` em variante `neutral` pode ser lido como "métrica
  desligada" (igual a `modelo_simplificado` / `sem_renda_tributavel`).
  Mitigação: hero monetário preservado colorido.
- Sufixo "alíquota efetiva baixa" pode soar como julgamento
  implícito — testar com 2-3 usuários antes de GA (lane separada).
