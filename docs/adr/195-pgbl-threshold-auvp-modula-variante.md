---
id: ADR-195
type: adr
title: "PGBL: threshold AUVP (alíquota efetiva) modula variante visual no estado capacidade_disponivel"
status: Proposto
phase: "A12"
date: "2026-05-12"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-189]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 195"
  - "PGBL threshold AUVP"
  - "AUVP-aderente variante"
tags:
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
  - phase/a12
  - status/proposto
  - type/adr
---

## §1 — Contexto

ADR-189 (Decidida 2026-05-11) tipificou o card
`IrpfPgblCapacidadeCard` em 4 estados — `capacidade_disponivel`,
`modelo_simplificado`, `no_teto`, `sem_renda_tributavel` — com copy
literal congelada por G0 `financial-planner`. Dentro do estado
`capacidade_disponivel`, hoje a variante visual é `info` uniforme.

ADR-189 §6 listou explicitamente como follow-up: *"Não introduzir
threshold subjetivo (alíquota efetiva mínima, horizonte) para modular
variante — pode virar ADR futura (alternativa M2 do `financial-planner`
review)."* Esta ADR é essa M2.

O problema: dentro do estado `capacidade_disponivel`, o produto não
diferencia visualmente o usuário cuja **alíquota efetiva** sobre a
renda tributável é alta (PGBL faz sentido sob lente AUVP/Perini) do
usuário cuja alíquota é baixa (PGBL provavelmente não compensa, mesmo
com capacidade dedutível remanescente). Os dois caem na mesma
variante `info` com a mesma copy. A seção "Otimização Tributária"
informa que **existe capacidade** mas perde a oportunidade de
contextualizar **quanto essa capacidade vale**.

## §2 — Alternativas avaliadas

### A. Status quo — `info` uniforme

**Pros:** zero risco de cruzar linha ADR-157.
**Contras:** a granularidade visual perdida vira a métrica em
"você tem espaço dedutível" sem mais — mesma intensidade para alguém
na faixa 27,5% (PGBL alto valor) e alguém na faixa 7,5% (PGBL
marginal). **Rejeitada como destino final** — é o status pré-M2.

### B. Threshold determinístico sobre alíquota efetiva (recomendada)

**Pros:**
- Sinal honesto: alíquota efetiva é número exato vindo do IRPF, sem
  proxy/heurística mole. AUVP (Raul Sena) literal: PGBL faz sentido
  "nas faixas mais altas". Tradução do enunciado AUVP em **intensidade
  visual** (não recomendação).
- Determinístico, reversível, sem novos campos no payload.

**Contras:**
- Threshold é juízo de planejamento (X=20%, Y=12% definidos abaixo
  pelo `financial-planner`), não regra fiscal — revisitar se tabela
  IR/teto PGBL mudar.
- Ignora horizonte de resgate (sem campo idade no MVP — limitação
  registrada §5).

### C. Threshold sobre `aliquota_sobre_total_pct`

**Pros:** capta perfil PJ com muito isento/exclusiva.
**Contras (G0 financial-planner):** dilui o sinal — a dedução PGBL
incide sobre **renda tributável**, e usar alíquota sobre total
penalizaria justamente quem tem fatia tributável onde PGBL pode
operar. **Rejeitada por G0.**

### D. Diferenciador `feature` para tier alto

**Pros:** maior contraste visual.
**Contras (G4 product-designer):** `feature` hoje é semanticamente
reservado ao estado `no_teto` — reconhece **decisão fiscal
consumada**. Replicar `feature` numa **capacidade não-usada** vira
endorsement implícito ("você é AUVP-aderente → aporte"), cruzando
exatamente a linha ADR-157 que o card protege. **Rejeitada por G4.**

## §3 — Decisão

Adotar **alternativa B** com a calibração consolidada abaixo (síntese
de G0 `financial-planner` + G4 `product-designer`, resolvendo a
divergência D em favor de G4 — ver §3.1).

### D1 — Helper puro no frontend

Implementar `evaluatePgblAuvpFit(kpis: IrpfKpis) → AuvpFitResult` em
módulo dedicado (`frontend/src/lib/irpf/pgbl-auvp-fit.ts`),
testável de forma isolada.

```typescript
type AuvpFitTier = "auvp_aderente" | "neutro" | "abaixo" | "indeterminado";

interface AuvpFitResult {
  tier: AuvpFitTier;
  /** Alíquota efetiva sobre tributável usada na avaliação (0–100). */
  aliquota: number | null;
  /** Motivo legível — uso interno + debug. */
  reason: string;
}

export function evaluatePgblAuvpFit(kpis: IrpfKpis): AuvpFitResult;
```

Regra (determinística):

| Pré-condição                                    | Tier              |
|-------------------------------------------------|-------------------|
| `pgbl_status ≠ capacidade_disponivel`           | `indeterminado`   |
| `aliquota_sobre_tributavel_pct` ausente/inválida | `indeterminado`   |
| `aliquota ≥ 20%`                                | `auvp_aderente`   |
| `12% ≤ aliquota < 20%`                          | `neutro`          |
| `aliquota < 12%`                                | `abaixo`          |

### D2 — Thresholds numéricos

- **X = 20%** (corte aderente): pega quem está consolidado nas faixas
  marginais 22,5% / 27,5% da tabela IR 2024 (centro do argumento AUVP
  de "alíquotas mais altas"). Alíquota **efetiva** ≥ 20% implica que
  a maior parte da renda tributável paga na faixa alta.
- **Y = 12%** (corte abaixo): piso onde o ganho marginal de dedução
  começa a ser consumido por taxa de administração típica de PGBL +
  risco de regressiva mal calibrada. Abaixo, Cerbasi/Perini seriam
  neutros a céticos.
- Faixa 12% ≤ aliq < 20% é "neutro" — existe ganho potencial mas
  exige análise tabela × horizonte que o card explicitamente não faz
  (disclaimer "Não é recomendação" mantido).

### D3 — Mapeamento tier → variante + subtitle

| Tier              | Variante  | Subtitle                                                                       |
|-------------------|-----------|--------------------------------------------------------------------------------|
| `auvp_aderente`   | `info`    | `Espaço dedutível remanescente · {ano_base} · alíquota efetiva alta`           |
| `neutro`          | `info`    | `Espaço dedutível remanescente · {ano_base} · alíquota efetiva intermediária`  |
| `abaixo`          | `neutral` | `Espaço dedutível remanescente · {ano_base} · alíquota efetiva baixa`          |
| `indeterminado`   | `info`    | `Espaço dedutível remanescente · {ano_base}` (sufixo omitido — fallback)        |

Apenas tier `abaixo` muda **variante** (sai de `info` para `neutral`).
Os tiers `auvp_aderente` e `neutro` ficam visualmente idênticos por
**variante** — a distinção carrega no **sufixo do subtitle**. É
intencional: evita gradiente semafórico (verde/amarelo/cinza) que
viraria CTA visual.

### D4 — Parágrafo principal e disclaimer literalmente preservados

A copy literal de ADR-189 §4 Estado 1 fica intocada (frase "Você
aportou…" + disclaimer "Não é recomendação: contratar PGBL exige
análise de tabela regressiva vs. progressiva, horizonte de resgate,
taxa de administração e contribuição ao INSS."). Único delta textual
é o **sufixo do subtitle**, factual (descreve a alíquota observada,
não prescreve ação).

### D5 — Edge cases

- `aliquota_sobre_tributavel_pct` ausente, vazia, não-numérica ou
  negativa → `indeterminado` → fallback (variante `info`, subtitle
  sem sufixo).
- `pgbl_status` diferente de `capacidade_disponivel` → helper retorna
  `indeterminado`; card renderiza os outros 3 estados conforme
  ADR-189 (helper não é chamado / efeito nulo).
- Hero monetário `<MonetaryValue value={capacidade} />` **não muda**
  em nenhum tier — preserva hierarquia visual.

## §3.1 — Resolução de divergência G0 × G4

G0 (`financial-planner`) propôs em sua primeira passagem mapear
`auvp_aderente → variante feature` + subtitle "faixa de maior
benefício marginal", argumentando que o jargão fiscal correto
("benefício marginal") é o que melhor traduz AUVP/Perini.

G4 (`product-designer`) rejeitou `feature` em `auvp_aderente`:
`feature` hoje é o vocabulário visual de "decisão fiscal consumada"
(usado em `no_teto`); usar para **capacidade não-usada** corre risco
real de virar endorsement implícito ("você devia aportar"). Esse
risco É o que ADR-157 proíbe.

`senior-cto` (orquestrador) **fechou em 1 rodada (anti-loop):**

- **Variante** — G4 vence: `auvp_aderente → info` (não `feature`).
  Justificativa: a salvaguarda ADR-157 é o invariante mais forte; G4
  protege-o melhor, e o custo é apenas "menos contraste visual" — não
  perda de sinal (sufixo carrega).
- **Threshold numérico** — G0 vence: X=20%, Y=12% sobre alíquota
  efetiva sobre tributável.
- **Texto do sufixo** — G4 vence: "alíquota efetiva alta /
  intermediária / baixa" (factual descritivo do user, não do
  produto). "Benefício marginal" do G0 era informativo mas
  aproximava-se de prescrição.

Decisão registrada para futura revisão: se telemetria pós-GA
mostrar que dois `info` adjacentes (aderente vs. neutro) não são
distinguíveis no scan rápido, reabrir.

## §4 — Tabela canônica (frontend implementa)

```
tier              variante  sufixo_subtitle
─────────────────────────────────────────────────────────────────────
auvp_aderente     info      · alíquota efetiva alta
neutro            info      · alíquota efetiva intermediária
abaixo            neutral   · alíquota efetiva baixa
indeterminado     info      (vazio)
```

## §5 — Consequências

### ✅ Ganhos

- Granularidade dentro de `capacidade_disponivel` deixa de ser zero.
- Sinal **honesto e determinístico** — vem direto do IRPF, sem proxy.
- Disclaimer "Não é recomendação" mantido literal; parágrafo
  principal intocado.
- Helper puro testável isoladamente — futura evolução (alta idade
  → degrada tier; tabela regressiva conhecida → eleva tier) cabe no
  mesmo formato sem refactor de UI.

### ⚠️ Riscos / limitações

- **Horizonte de resgate fora do MVP.** Sem campo `data_nascimento`
  no payload, não dá para distinguir 25-aa (PGBL casa com horizonte
  longo) de 60-aa (PGBL talvez não compense). Lane futura com
  alteração de payload necessária.
- **Tendência de alíquota não captada.** Avaliação é sobre `ano_base`
  único. Usuário com renda subindo de faixa pode estar em "neutro"
  hoje mas "aderente" no próximo ano — invisível no card.
- **Regime de tributação PGBL implícito.** Threshold assume cenário
  regressiva long-hold; se o usuário fará regressiva curta ou
  progressiva, a calibração X/Y muda. Disclaimer já cobre, mas
  registrado.
- **Tier `abaixo` em variante `neutral`.** Pode ser lido como
  "métrica desligada" (igual a `modelo_simplificado` e
  `sem_renda_tributavel`). Mitigação: hero monetário permanece
  colorido (não vira `—`), preservando legibilidade do valor.
- **Sufixo "alíquota efetiva baixa" pode soar como julgamento
  implícito.** Testar com 2-3 usuários antes de GA (lane separada).
- **Dois `info` adjacentes (aderente, neutro)** só distinguem por
  texto — em scan rápido, podem se confundir. Aceito como custo de
  não usar gradiente semafórico; revisar se telemetria mostrar
  confusão.
- **WCAG 1.4.1** — variante sozinha é diferenciação só por cor.
  Reforço textual (sufixo) já carrega a distinção; screen reader
  ouve "alíquota efetiva alta/intermediária/baixa" antes do hero.

### 🔄 Reversibilidade

Alta. Para reverter:

1. `IrpfPgblCapacidadeCard` volta a usar `VARIANT_BY_STATUS` puro
   (já existe no código pós-ADR-189).
2. Helper `evaluatePgblAuvpFit` deletado; subtitle volta ao formato
   `{base} · {ano_base}`.

Sem migração DB; sem mudança no payload `irpf_kpis`; sem alteração
em `IRPFAnalyzer.pgbl_status`.

## §6 — Não-objetivos (esta ADR)

- **Não** introduzir CTA "contrate PGBL", "compare regimes" ou
  qualquer recomendação de produto/banco/regime. ADR-157 mantida.
- **Não** alterar `pgbl_status` ou qualquer campo de `irpf_kpis`.
  Threshold resolvido **inteiramente no client**.
- **Não** introduzir proxy de idade declarada — explicitamente
  fora do MVP.
- **Não** introduzir variante visual nova no design system. Usa
  exclusivamente o vocabulário existente em `CardVariant`.
- **Não** mudar copy literal do parágrafo do estado
  `capacidade_disponivel` — apenas o sufixo do subtitle.

## §6.1 — Sign-off G0 (`financial-planner` · 2026-05-12)

Decisão revisada em sessão paralela (registro completo §3.1):

- **Q1 (alíquota a usar):** APROVADO — `aliquota_sobre_tributavel_pct`
  (a dedução PGBL incide sobre essa base; usar `aliquota_sobre_total`
  diluiria sinal de perfil PJ com muito isento).
- **Q2 (threshold X/Y):** APROVADO — X=20%, Y=12%.
- **Q3 (horizonte):** APROVADO — fora do MVP, lane futura.
- **Q4 (subtitle):** APROVADO COM AJUSTE — sufixo G4 ("alíquota
  efetiva alta/intermediária/baixa") preferido a "benefício
  marginal" do G0 por ser mais factual e menos prescritivo.
- **Q5 (linha ADR-157):** OK — não há CTA, produto, banco ou regime
  sugerido; threshold determinístico; disclaimer literal preservado.

## §6.2 — Sign-off G4 (`product-designer` · 2026-05-12)

- **Mapeamento tier → variante:** APROVADO — sem `feature` em
  `auvp_aderente` (preserva `feature` exclusivo para "decisão
  consumada" em `no_teto`).
- **Subtitle:** APROVADO — sufixo factual, sem rótulo gamificado
  ("AUVP-aderente" como texto visível foi rejeitado).
- **Hierarquia da seção S_IRPF_OTIMIZACAO:** OK — só `no_teto`
  permanece `feature`, regra "verde só para fato consumado"
  preservada.
- **Edge case alíquota inválida:** APROVADO — fallback silencioso
  (variante `info`, subtitle sem sufixo).
- **A11y WCAG 1.4.1:** APROVADO COM CONDIÇÃO — sufixo do subtitle
  é o reforço obrigatório (não dependemos apenas de cor); confirmar
  contraste de `card-variant-neutral` em dark mode em revisão visual.

## §7 — Critério de aceite

Mergeada quando:

1. `evaluatePgblAuvpFit(kpis)` implementado em
   `frontend/src/lib/irpf/pgbl-auvp-fit.ts` (módulo dedicado,
   função pura, sem dependência de React).
2. `IrpfPgblCapacidadeCard` consome o helper **apenas** no estado
   `capacidade_disponivel`; copy literal do parágrafo principal +
   disclaimer literalmente preservada.
3. Subtitle do estado `capacidade_disponivel` ganha sufixo
   conforme §4.
4. Vitest cobre ≥ 4 cenários (auvp_aderente, neutro, abaixo,
   indeterminado por alíquota inválida) + persistência da copy
   ADR-189 (snapshot/string asserts).
5. `CI verde` + pre-commit + sem mudança no backend.
6. ADR flippa para `Decidido (A12)` no commit-merge.
