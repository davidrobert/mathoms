---
id: ADR-198
type: adr
title: "Chip \"Espaço de R$ X\" condicional ao pgbl_status no card Dedutíveis Aplicados (encerra débito ADR-194 §6.4)"
status: Decidido
phase: "A12"
date: "2026-05-12"
relates_to:
  - "[[ADR-189]]"
  - "[[ADR-194]]"
  - "[[ADR-197]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 198"
  - "Dedutíveis chip Espaço condicional"
  - "IRPF dedutíveis chip simplificado"
tags:
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
  - phase/a12
  - status/decidido
  - type/adr
---

## §1 — Contexto

O card `IrpfDedutiveisAplicadosCard`
([frontend/src/components/report/cards/IrpfDedutiveisAplicadosCard.tsx](../../frontend/src/components/report/cards/IrpfDedutiveisAplicadosCard.tsx))
renderiza uma linha por categoria dedutível declarada em E1.6 (Saúde,
Educação, Pensão alimentícia, INSS) com um **chip de status** à direita
do valor, regido pela função `DedutivelStatusChip`:

| Condição | Chip | Variante |
|---|---|---|
| `teto_brl == null` | "Sem teto legal" | `neutral` (cinza) |
| `teto_aplicado == true` OR `utilizado >= teto_brl` | "No teto" | `neutral` (cinza) |
| `teto_brl > 0 AND utilizado < teto_brl` | "Espaço de R$ {teto - utilizado}" | `info` (azul) |

[[ADR-194]] §6.4 corrigiu o **subtítulo** do card para regimes
`modelo_simplificado` / `sem_renda_tributavel` (de "Valores deduzidos do
imposto" → "Pagamentos elegíveis a dedução"), eliminando a afirmação
factual incorreta de que houve efeito fiscal. Mas o sign-off G0
explicitou um **débito imediato** na ADR-194 §6.4:

> **Débito imediato (lane separada):** chip "Espaço de R$ X" também
> implica gap acionável para reduzir IR — em simplificado é igualmente
> falso. Tratar em ADR separada (variante condicional do chip por
> `pgbl_status`); não bloqueia este amend.

Esta ADR encerra esse débito.

### §1.1 — Caso patológico

Workspace em `pgbl_status == modelo_simplificado` declarou despesas
dedutíveis em educação no E1.6 (ex.: R$ 2.100 em colegial dos filhos)
mas optou pelo simplificado na declaração entregue. Hoje o card mostra:

```
Educação    R$ 2.100,00  [====     ]    [Espaço de R$ 1.461,50]
                                         ^^^^^^^^^^^^^^^^^^^^^^
                                         Implica gap acionável que
                                         não existe nesse regime.
```

O chip "Espaço de R$ 1.461,50" sugere que "pode capturar mais economia
se gastar mais em educação", quando o efeito fiscal **não existe nesse
regime**. O desconto fixo do simplificado já substituiu qualquer dedução
legal. Em `sem_renda_tributavel`, o caso é ainda mais explícito — não há
base de cálculo (só rendimentos isentos/tributação exclusiva — Estado 4
de [[ADR-189]]).

## §2 — Alternativas avaliadas

### A — Esconder o chip (`return null` quando regime ∈ {simpl, sem_base} e subutilizado)

- **Prós:** card mais limpo; chip sumido = nenhuma sugestão.
- **Contras:** perde informação visual de que existe subutilização do
  teto; usuário vê valor R$ 2.100 em Educação e zero contexto sobre por
  que outras categorias têm chip e essa não — pior que dizer algo.

### B — Chip neutro substituto ("Sem efeito neste regime", variante `neutral`)

- **Prós:** mantém estrutura visual consistente (linha sempre tem chip);
  variante `neutral` (cinza) não compete por atenção; copy factual
  cobre os dois estados sem prescrever ação.
- **Contras:** copy precisa ser robusta a leitores diferentes — "regime"
  refere-se ao regime de declaração (completa vs. simplificada) ou ao
  status PGBL? Risco baixo: contexto da seção "Otimização Tributária"
  + card PGBL adjacente em Estado 2 (com explicação de "modelo
  simplificado") + ADR-197 (componentes elegíveis) tornam a referência
  inequívoca.

### C — Manter chip + sufixo informativo ("Espaço de R$ X · modelo completo", variante `info`)

- **Prós:** preserva o número exato; informa que o gap é condicional.
- **Contras:** ainda usa variante `info` (azul), que escala atenção; sufixo
  "modelo completo" prescreve implicitamente a troca de regime — viola
  "uma decisão por tela" (Cerbasi). G0 vetou: "soa como 'considere mudar
  para completa', e mudança de regime é trabalho do Plano de Ação (E7),
  não do card factual."

### Copy literal — opções consideradas para B

| Copy | Avaliação |
|---|---|
| "Fora da base de cálculo" | Tecnicamente correto em `sem_renda_tributavel` (literal — não há base IR); ambíguo em `modelo_simplificado` (a despesa **é** dedutível em tese; o regime que neutraliza). Rejeitada. |
| "Não aplicável neste regime" | Soa como erro de sistema ("não se aplica ao seu caso") em vez de fato fiscal. Rejeitada. |
| "Sem efeito no IR deste ano" | Bom, mas "deste ano" insinua que ano que vem pode mudar (prescrição temporal). Rejeitada. |
| **"Sem efeito neste regime"** | Neutro, factual, cobre os dois estados, não prescreve, deixa subentendido que regime é a variável sem dizer "troque". **Escolhida.** |

## §3 — Decisão

**Opção B**, com **copy literal "Sem efeito neste regime"** e variante
`neutral`, aplicada quando:

```
pgbl_status ∈ {modelo_simplificado, sem_renda_tributavel}
  AND teto_brl > 0
  AND utilizado < teto_brl
  AND !teto_aplicado
```

Pseudo-código alvo na função `DedutivelStatusChip`:

```tsx
function DedutivelStatusChip({ linha, utilizado, teto, pgblStatus }) {
  if (teto === null) return <chip neutral>Sem teto legal</chip>;
  if (linha.teto_aplicado || utilizado >= teto)
    return <chip neutral>No teto</chip>;

  const semEfeitoFiscalAnoBase =
    pgblStatus === "modelo_simplificado" ||
    pgblStatus === "sem_renda_tributavel";

  if (semEfeitoFiscalAnoBase) {
    return <chip neutral>Sem efeito neste regime</chip>;
  }
  return <chip info>Espaço de R$ {teto - utilizado}</chip>;
}
```

### §3.1 — Split binário confirmado

A regra é **binária** sobre o eixo "regime que permite dedução **neste
ano**":

| `pgbl_status` | Chip em ramo subutilizado |
|---|---|
| `capacidade_disponivel` | "Espaço de R$ X" (variante `info`) — inalterado |
| `no_teto` | "Espaço de R$ X" (variante `info`) — inalterado (é regime **completa** com 12% PGBL esgotados, mas demais dedutíveis seguem reduzindo base) |
| `modelo_simplificado` | "Sem efeito neste regime" (variante `neutral`) |
| `sem_renda_tributavel` | "Sem efeito neste regime" (variante `neutral`) |

Outros chips (`"Sem teto legal"`, `"No teto"`) **não mudam** em nenhum
regime — são factuais sempre.

### §3.2 — Variante `info` do card

A função `resolveVariant` (linhas 51-57 de
`IrpfDedutiveisAplicadosCard.tsx`) hoje escala para `info` quando há
**qualquer** linha em subutilização (`hasSubutilizacao`). Em regime
simplificado/sem-base, essa escalação visual é coerente com a mesma
ofensa do chip — o card todo vira "azul" sinalizando oportunidade que
não existe. Variante do **card** também segue o split binário:
`info` só escala se `pgbl_status ∈ {capacidade_disponivel, no_teto}`;
em simplificado/sem-base, permanece `neutral` independente de
subutilização. Override (`variantOverride`) continua válido se o
chamador precisa fixar.

## §4 — Sign-off G0 (`financial-planner` · 2026-05-12)

**APROVADO Opção B com copy "Sem efeito neste regime"**, variante
`neutral`.

Posição AUVP/Cerbasi articulada:

- **AUVP (Raul Sena)** trata IR como **otimização dentro do regime
  escolhido**, não como gatilho para mudar regime. Mostrar "Espaço de
  R$ X" num regime onde o espaço não existe contradiz "decisão sob
  restrição atual". Vota A ou B.
- **Cerbasi** prefere card educativo que **informa sem induzir ação
  enviesada**. "Espaço de R$ X · modelo completo" empurra para
  decisão tributária de outro escopo — viola "uma decisão por tela".
  Vota B.
- **Perini** (renda fixa/dividendos) — neutro no domínio, mas
  princípio "não criar métrica que induz mau comportamento" aplica.

Notas G0 incorporadas:

- Variante visual é `neutral` (cinza), não `info` (azul) — não compete
  por atenção com chips factualmente acionáveis em outros cards.
- **Tooltip opcional** (não-bloqueante, **fora de escopo desta ADR**):
  ao hover, "Em modelo simplificado/sem renda tributável, despesas
  dedutíveis não reduzem o IR deste ano." Lane futura se houver
  pedido de UX; não bloqueia merge.
- **Edge case histórico:** se workspace alternou regimes entre anos,
  card mostra **apenas** o ano-base atual via `pgblStatus` daquele ano.
  Histórico fora de escopo.
- **Out of scope:** prescrição de troca de regime fica no Plano de
  Ação (E7), não neste card factual.

## §5 — Critério de aceite

ADR flippa para `Decidido (Sprint A12)` quando:

1. Função `DedutivelStatusChip` em
   [IrpfDedutiveisAplicadosCard.tsx:175-204](../../frontend/src/components/report/cards/IrpfDedutiveisAplicadosCard.tsx)
   recebe `pgblStatus: PgblStatus` e adapta o ramo "Espaço de" conforme
   §3.
2. Função `resolveVariant` (linhas 51-57) recebe `pgblStatus` e suprime
   escalação para `info` quando `pgblStatus ∈ {modelo_simplificado,
   sem_renda_tributavel}` (§3.2).
3. Vitest em
   [frontend/tests/components/IrpfSections.test.tsx](../../frontend/tests/components/IrpfSections.test.tsx)
   cobre:
   - `modelo_simplificado` com linha subutilizada → chip "Sem efeito
     neste regime", variante `neutral`.
   - `sem_renda_tributavel` com linha subutilizada → chip "Sem efeito
     neste regime", variante `neutral`.
   - Os 2 casos existentes que cobrem `capacidade_disponivel` com chip
     "Espaço de" **preservados sem regressão**.
4. Card resta com mesmo título, barra de progresso e disclaimer-rodapé
   — apenas o ramo "Espaço de" muda nos 2 regimes.

## §6 — Não-objetivos

- Não recalcular regra fiscal no frontend (regime continua resolvido em
  E1.6 → `irpf_kpis.pgbl_status`).
- Não tocar nos chips "Sem teto legal" / "No teto" — factuais em
  qualquer regime.
- Não tocar nos chips do `IrpfPgblCapacidadeCard` / `IrpfDependentesCard`.
- Não introduzir tooltip (lane futura).
- Não introduzir comparativo simplificada↔completa no card (vetado
  G0 em ADR-189; ADR-197 endereçou via ponteiro PGD/MIR no card PGBL).
