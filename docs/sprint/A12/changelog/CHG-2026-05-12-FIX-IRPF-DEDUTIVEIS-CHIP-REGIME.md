---
id: CHG-2026-05-12-FIX-IRPF-DEDUTIVEIS-CHIP-REGIME
type: changelog-entry
date: "2026-05-12"
sprint: A12
lane: "[[TRACK-irpf-otimizacao-cards-revival]]"
adrs:
  - "[[ADR-198]]"
prs: []
commits: []
summary: |
  fix(frontend): chip "Espaço de R$ X" no card Dedutíveis Aplicados vira
  "Sem efeito neste regime" (neutral) em pgbl_status simplificado/sem-base
  — encerra débito ADR-194 §6.4 (ADR-198 Decidida em A12).
tags:
  - type/changelog-entry
  - sprint/a12
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# fix(report): chip "Espaço de R$ X" condicional ao pgbl_status

Encerra débito explicitamente flagged em [[ADR-194]] §6.4 (PR #236,
mergeado 2026-05-12): o subtítulo do card `IrpfDedutiveisAplicadosCard`
já era condicional ao `pgbl_status`, mas o **chip** "Espaço de R$ X" no
ramo de subutilização continuava implicando gap acionável de IR nos
regimes `modelo_simplificado` / `sem_renda_tributavel` — onde o efeito
fiscal não existe.

**Co-design 2026-05-12** — `financial-planner` G0 ratificou:

- **Opção B aprovada:** chip neutro "Sem efeito neste regime"
  (variante `neutral`), aplicada quando
  `pgbl_status ∈ {modelo_simplificado, sem_renda_tributavel}` AND
  ramo seria "Espaço de" (teto > utilizado, sem teto aplicado).
- Copy literal congelada após avaliação de 4 alternativas
  ("Fora da base de cálculo" — ambíguo em simplificado; "Não aplicável
  neste regime" — soa erro de sistema; "Sem efeito no IR deste ano"
  — insinua prescrição temporal; **"Sem efeito neste regime"** —
  neutro, factual, cobre os 2 estados).
- Posição AUVP/Cerbasi preservada — "diagnóstico cru sem prescrição".
- Variante do **card** (`resolveVariant`) também passa a respeitar o
  split: simplificado/sem-base nunca escala para `info`, mesmo com
  subutilização ([[ADR-198]] §3.2).

**Caso patológico que motiva:** workspace em simplificado declarou
R$ 2.100 em educação no E1.6 (colegial dos filhos) e optou pelo
desconto fixo na declaração. Antes: chip "Espaço de R$ 1.461,50"
sugeria oportunidade de redução fiscal inexistente. Agora: chip
"Sem efeito neste regime" (neutral).

**Entregue:**

- `frontend/src/components/report/cards/IrpfDedutiveisAplicadosCard.tsx`:
  - Helper `semEfeitoFiscal(pgblStatus): boolean`.
  - `resolveVariant` recebe `pgblStatus` e suprime escalação para
    `info` em simplificado/sem-base.
  - `DedutivelLinhaRow` propaga `pgblStatus` para
    `DedutivelStatusChip`.
  - `DedutivelStatusChip` recebe `pgblStatus` e adiciona ramo
    intermediário "Sem efeito neste regime" antes do "Espaço de".
  - Chips "Sem teto legal" / "No teto" inalterados em qualquer regime
    — são factuais sempre.
- `docs/adr/198-dedutiveis-chip-espaco-condicional-pgbl-status.md`:
  ADR escrita + Decidida em A12 com G0 sign-off literal incluído.

**Testes:**

- Vitest `frontend/tests/components/IrpfSections.test.tsx`:
  novo describe block "ADR-198 — chip 'Espaço' condicional ao regime"
  com 9 cenários:
  - 2 cenários "Sem efeito neste regime" para simplificado +
    sem_renda_tributavel.
  - 2 regression guards para chip "Espaço de" em capacidade_disponivel
    + no_teto.
  - 2 cenários de variante neutral preservada em simplificado/sem-base
    mesmo com subutilização.
  - 1 regression guard de variante `info` em capacidade_disponivel.
  - 2 cenários assegurando que "Sem teto legal" e "No teto" continuam
    sendo emitidos nesses regimes (não vira "Sem efeito").
- Caso existente "título, chips e disclaimer inalterados em
  simplificado" reescrito para refletir nova copy (assertion antiga
  buscava "Espaço de" no simplificado — comportamento corrigido).
- Suíte completa `IrpfSections.test.tsx`: **47/47 verde**.

**Não-objetivos** (ver [[ADR-198]] §6):

- Tooltip explicativo no hover (lane futura se houver pedido UX).
- Comparativo simplificada↔completa no card (vetado G0 em ADR-189;
  ADR-197 endereçou via ponteiro PGD/MIR no card PGBL).
- Cruzar com histórico de regimes de anos anteriores.
- Prescrição de troca de regime (escopo do Plano de Ação E7).
