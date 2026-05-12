---
id: ADR-196
type: adr
title: "Reconciliação dos cards PGBL S7 (fluxo PJ inferido) × S_IRPF_OTIMIZACAO (IRPF declarado) por priorização condicional"
status: Decidido
phase: "A12"
date: "2026-05-12"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-189]]"
  - "[[ADR-194]]"
  - "[[ADR-195]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 196"
  - "PGBL reconciliação S7 IRPF"
  - "Card A informativo quando IRPF authoritativo"
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

O relatório premium publica hoje **dois cards distintos sobre PGBL**, em
seções diferentes, alimentados por fontes diferentes, sem qualquer
cross-link entre eles:

### Card A — `previdencia_pgbl` em §S7

[frontend/src/components/report/cards/PrevidenciaPgblCard.tsx](../../frontend/src/components/report/cards/PrevidenciaPgblCard.tsx)
+ [pipeline/domain/services/previdencia_analyzer.py](../../pipeline/domain/services/previdencia_analyzer.py).

- **Natureza: prospectivo, prescritivo.**
- Lê receita PJ identificada no fluxo bancário (E4 / `flow_classifier`),
  anualiza, aplica lucro presumido (32%) e calcula renda tributável
  estimada, limite PGBL anual (12%), **"aporte sugerido/mês"**,
  alíquota marginal e "economia de IR/ano" estimada.
- Variante `feature`. **Sem disclaimer** "Não é recomendação".

### Card B — `pgbl_capacidade` em §S_IRPF_OTIMIZACAO

[frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx](../../frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx)
+ [pipeline/domain/services/irpf_analyzer.py](../../pipeline/domain/services/irpf_analyzer.py).

- **Natureza: retrospectivo, descritivo.**
- Lê IRPF Full declarado (E1.6) — fonte authoritativa, assinada à RFB.
- ADR-189 tipificou em 4 estados (`capacidade_disponivel`,
  `modelo_simplificado`, `no_teto`, `sem_renda_tributavel`) com copy
  literal aprovada por G0 `financial-planner`. ADR-195 modula variante
  via AUVP-fit no estado `capacidade_disponivel`. Disclaimer "Não é
  recomendação" restrito a `capacidade_disponivel`.

### Problema concreto

Workspace com IRPF Full + receita PJ no fluxo do mesmo período → **dois
cards convivem sem reconciliação**. Quatro situações ruins:

1. **IRPF em `modelo_simplificado`** (caso majoritário em renda PF
   brasileira): Card B diz "PGBL não se aplica no regime simplificado".
   Card A continua dizendo **"aporte sugerido R$ X/mês, economia IR
   R$ Y/ano"**. Card A está **prescrevendo aporte que não vai gerar a
   dedução anunciada** — falha pedagógica direta (Cerbasi puro), viola
   posição G0 de ADR-157 ("capacidade ≠ recomendação automática") e
   pode levar o usuário a aportar pensando que está deduzindo.

2. **IRPF em `no_teto`**: Card B diz "Você esgotou os R$ Y dedutíveis
   em {ano}". Card A continua sugerindo "aporte de R$ X/mês". Card A
   sugere ação **já feita** — menos perigoso, mas confuso.

3. **IRPF em `sem_renda_tributavel`**: Card B diz "Apenas isentos —
   PGBL não se aplica". Card A pode ainda mostrar receita PJ
   (categorizada mas declarada isenta/exclusiva, edge raro). Provável
   incoerência marginal.

4. **IRPF em `capacidade_disponivel`**: Card B diz "Aportou R$ X dos
   R$ Y dedutíveis" (com disclaimer AUVP). Card A diz "Sugiro aportar
   R$ K/mês = R$ 12K/ano". K (PJ × 32% × 12%) ≠ Y/12 (renda tributável
   declarada × 12%), porque Y agrega CLT + PJ + outros. **Card A
   subestima espaço fiscal vs. a fonte autoritativa.**

ADR-189 §6 deferiu explicitamente: "Não reconciliar com card
`previdencia_pgbl` em S7 — lane separada". **Esta é a lane separada.**

### Sign-offs paralelos (co-design 2026-05-12)

Decisão arquitetural foi co-designada antes de codificação:

- **G0 `financial-planner`** ([sessão paralela](../../.claude/agents/financial-planner.md)):
  classificou o cenário 1 como **bug de produto financeiro P0/severidade
  alta** sob Cerbasi/AUVP. Veredito explícito: **Alternativa B**.
  Forneceu copy literal aprovada (§4 abaixo) para 6 modos do Card A.
- **G2 `data-engineer`**: aprovou contrato técnico minimalista —
  helper TS no frontend, **zero churn em schema E5 / goldens /
  OpenAPI snapshot**. Backend `_e5_load_irpf_kpis` permanece intocado
  (continua escolhendo `anos[-1]` como hoje).
- **G4 `product-designer`**: aprovou Alternativa B com ajustes:
  Card A em modo informativo é sempre `neutral` (não `feature`) para
  não competir com Card B autoritativo; grid de 4 KPIs suprimido em
  informativo (valores inline na copy); cross-link via `<a
  href="#S_IRPF_OTIMIZACAO">` real (funciona em HTML e PDF
  Playwright); `aria-label="Métrica não aplicável"` no "—".

## §2 — Alternativas avaliadas

### A. Dois cards independentes + cross-link sutil

**Pros:** baixíssimo custo, sem mudança semântica.
**Contras:** **não resolve o cenário 1**. Cross-link não desfaz
prescrição errada — usuário lê Card A primeiro com "aporte sugerido"
proeminente e fica com essa âncora. **Rejeitada.**

### B. Priorização condicional (recomendada)

Quando há IRPF Full do ano-base "relevante", Card B vira
source-of-truth e Card A degrada para **modo informativo**:
- **suprime** "aporte sugerido" e "economia IR" (as prescrições
  problemáticas) em todos os estados informativos;
- exibe copy factual específica por estado IRPF (4 variantes);
- cross-linka para `#S_IRPF_OTIMIZACAO`;
- variante visual cai de `feature` para `neutral` (hierarquia).

Quando **não há IRPF Full** ou IRPF é **defasado ≥2 anos**, Card A
mantém comportamento atual + **ganha disclaimer** "Não é recomendação"
espelhando linguagem do Card B.

**Pros:**
- Resolve o cenário 1 (eliminação da prescrição errada).
- Preserva ADR-189 §6.1 integralmente — Card B não muda.
- Boundary `flow_classifier` ↔ `IRPFAnalyzer` preservado: a
  reconciliação é **decisão de display**, não de domínio.
- Custo proporcional: 1 helper TS + refactor do Card A; **zero
  mudança em backend, schema E5, goldens, OpenAPI snapshot**.

**Contras:**
- Card A passa a ter 6 ramos (default, default-defasado, 4
  informativos) — superfície de teste cresce.
- Grid de KPIs do Card A "vazia-se" em modo informativo — UX
  intencional (G4), mas pode parecer redundante. Mitigado pelo
  cross-link explícito.
- Requer derivação de `primary_year` no frontend a partir de
  `fluxo_caixa.receita_despesa_mensal_detalhado.labels` (sem
  plumbing canônico em backend).

### C. Card unificado (aggregate de reconciliação ou view layer)

**Pros:** mensagem única; sem ambiguidade visual.
**Contras:**
- Viola restrição 1 (boundaries entre `PrevidenciaAnalyzer` e
  `IRPFAnalyzer` semanticamente importantes — fluxo observado ≠
  declaração assinada).
- Reconciliar período mensal × ano-calendário em data layer exige
  matcher de período complexo no domain — custo alto.
- Regrediria ADR-189 (Card B passou pela ADR; refundir agora
  destruiria contrato consolidado).
- C pode ser destino de longo prazo se UX validar; **não cabe nesta
  lane.** Lane futura.

**Rejeitada nesta lane.**

## §3 — Decisão

Implementar a **Alternativa B (priorização condicional)** com escopo
**exclusivamente frontend** (zero churn em backend, schema, goldens).

### D1 — Helper de estratégia (TS)

Novo módulo `frontend/src/lib/irpf/pgbl-card-strategy.ts`:

```typescript
export type PgblCardMode =
  | "default"
  | "default-defasado"
  | "informative-capacidade"
  | "informative-simplificado"
  | "informative-no-teto"
  | "informative-sem-renda";

export interface PgblCardStrategy {
  mode: PgblCardMode;
  /** Ano-base do IRPF authoritativo (ou último defasado). null quando
   *  workspace não tem IRPF Full processado. */
  anoBase: number | null;
  /** Defasagem em anos entre primaryYear e anoBase. null sem IRPF. */
  defasadoAnos: number | null;
}

export function derivePrimaryYear(labels: string[] | undefined): number | null;

export function matchIrpfToPeriod(
  anosDisponiveis: number[],
  primaryYear: number,
): { anoBase: number | null; defasadoAnos: number | null; authoritative: boolean };

export function getPgblCardStrategy(
  irpfKpis: IrpfKpis | null,
  primaryYear: number | null,
): PgblCardStrategy;
```

**Regra de transição** (determinística, derivada de G0):

| `irpfKpis` | `primaryYear` | `match` | `Card B status` | Modo Card A |
|---|---|---|---|---|
| `null` | qualquer | — | — | `default` |
| presente | `null` | — | qualquer | `default` |
| presente | número | `anoBase ≤ primaryYear + 1` (auth) | `capacidade_disponivel` | `informative-capacidade` |
| presente | número | auth | `modelo_simplificado` | `informative-simplificado` |
| presente | número | auth | `no_teto` | `informative-no-teto` |
| presente | número | auth | `sem_renda_tributavel` | `informative-sem-renda` |
| presente | número | `primaryYear - anoBase ≥ 2` | qualquer | `default-defasado` |

`derivePrimaryYear` extrai o ano do último label de
`fluxo_caixa.receita_despesa_mensal_detalhado.labels` (formato
`YYYY-MM`). Sem labels → `null` → fallback `default`.

### D2 — Refactor do `PrevidenciaPgblCard`

Componente passa a aceitar 2 props (mantendo retrocompat):

```typescript
interface PrevidenciaPgblCardProps {
  previdencia: PrevidenciaPgblData | undefined;
  /** ADR-196: modo de exibição resolvido pelo helper. Default
   *  `"default"` mantém comportamento legacy. */
  mode?: PgblCardMode;
  /** ADR-196: ano-base do IRPF authoritativo (modos informativos +
   *  default-defasado). */
  anoBase?: number;
}
```

Switch sobre `mode` (default, default-defasado, 4 informativos) com
copy literal de §4 abaixo. Em modos `default*`:
- Mantém grid de 4 KPIs.
- Variante `feature`.
- **Adiciona** disclaimer "Não é recomendação" inline no parágrafo
  (espelhando padrão Card B).
- `size: full` (md:col-span-2).
- Em `default-defasado`: nota inline no header "Última declaração
  disponível: {ano_base} (defasada)".

Em modos `informative-*`:
- Suprime grid; valores inline (`receita_pj_anual`,
  `limite_pgbl_anual`) na copy.
- **Suprime** `aporte_mensal` e `economia_ir_anual` (as prescrições).
- Variante `neutral` (G4: hierarquia rebaixada em favor do Card B).
- `size: half`.
- Cross-link `<a href="#S_IRPF_OTIMIZACAO">Otimização Tributária</a>`
  com `underline decoration-dotted underline-offset-2` (convenção de
  relatório financeiro impresso; funciona em PDF).

### D3 — Ajuste em `S7IndependenciaSection`

Section consome `irpfKpis` (via `isIrpfKpis` guard) + `primaryYear`
derivado de `data.fluxo_caixa`. Computa `strategy = getPgblCardStrategy(kpis,
primaryYear)` e passa `mode` + `anoBase` para `<PrevidenciaPgblCard>`.
`size` do card definido pelo modo (helper retorna ou caller decide via
`mode.startsWith("informative")`).

### D4 — A11y

- `<span aria-label="Métrica não aplicável">—</span>` em modos
  `informative-simplificado` e `informative-sem-renda`. Aplicar
  oportunisticamente ao Card B (mesma sessão).
- Link âncora cross-link: texto interno descritivo ("Otimização
  Tributária") suficiente; não precisa `aria-label` adicional.

### D5 — Variantes por modo (consolidado)

| Modo | Variante | Size | Disclaimer | Cross-link | Grid 4 KPIs |
|---|---|---|---|---|---|
| `default` | `feature` | full | **Sim** (novo) | — | sim |
| `default-defasado` | `feature` | full | **Sim** + nota defasagem | — | sim |
| `informative-capacidade` | `neutral` | half | não | sim | não (inline) |
| `informative-simplificado` | `neutral` | half | não | sim | não |
| `informative-no-teto` | `neutral` | half | não | sim | não |
| `informative-sem-renda` | `neutral` | half | não | sim | não |

### D6 — Backend inalterado

- `PrevidenciaAnalyzer` permanece com mesma assinatura e payload.
- `_e5_load_irpf_kpis` continua escolhendo `analyzer.anos_base_disponiveis()[-1]`.
- Schema `e5_analysis.schema.json` inalterado.
- Goldens `tests/test_e5_golden_execution.py` inalterados.
- OpenAPI snapshot inalterado.

**Justificativa:** a regra `matchIrpfToPeriod` é puramente de display
(decide `mode` do Card A) com **um único consumidor** — não satisfaz
critério de "regra universal" da ADR-143. Promover a domain Python só
quando houver segundo consumidor (ex: render PDF server-side
parametrizado por ano explícito). Débito anotado em §5.

## §4 — Copy canônica por modo (G0 sign-off)

Cabeçalho/subtitle inicial dos modos `informative-*`:

> **Estimativa sobre receita PJ — informativo · veja capacidade
> declarada em [Otimização Tributária](#S_IRPF_OTIMIZACAO)**

### Modo `default` (sem IRPF Full)

Layout atual mantido + **novo disclaimer inline**:

> **Não é recomendação:** valor estimado sobre receita PJ; benefício
> fiscal real depende de regime tributário declarado, alíquota
> efetiva, horizonte de resgate, taxa de administração e contribuição
> ao INSS.

### Modo `default-defasado` (IRPF disponível, defasado ≥ 2 anos)

Layout atual + nota inline no header:

> *Última declaração: {ano_base} · defasada · reveja após próxima
> entrega IRPF*

Disclaimer idêntico ao `default`.

### Modo `informative-simplificado`

> Sua declaração de {ano_base} é pelo modelo simplificado, que não
> permite dedução de PGBL. O potencial estimado sobre sua receita PJ
> anualizada (**R$ {receita_pj_anual}**) seria de até
> **R$ {limite_pgbl_anual}/ano** *caso houvesse migração para o modelo
> completo* — decisão que depende de comparação anual com o desconto
> simplificado da Receita.

### Modo `informative-no-teto`

> Em {ano_base} você esgotou os **R$ {teto_declarado}** dedutíveis
> (12% da renda tributável declarada). Capacidade adicional só no
> próximo ano-base. Estimativa sobre receita PJ anualizada deste
> período: **R$ {limite_pgbl_anual}**.

### Modo `informative-sem-renda`

> Sua declaração de {ano_base} registrou apenas rendimentos isentos
> ou de tributação exclusiva — PGBL deduz da base tributável e não se
> aplica nesse cenário. A receita PJ identificada no fluxo deste
> período (**R$ {receita_pj_anual}**) só geraria espaço dedutível se
> classificada como tributável no próximo IRPF.

### Modo `informative-capacidade`

> Capacidade dedutível autoritativa está em
> [Otimização Tributária](#S_IRPF_OTIMIZACAO) (baseada no IRPF
> {ano_base} declarado). Esta seção mostra apenas a estimativa sobre
> receita PJ anualizada deste período (**R$ {limite_pgbl_anual}/ano**),
> útil para projetar próximo ano-base.

## §5 — Consequências

### ✅ Ganhos

- Eliminação da prescrição contraditória em workspaces simplificado
  + receita PJ (~70-80% dos usuários BR — G0).
- Card A passa a ter disclaimer no modo prescritivo (`default*`),
  alinhando linguagem com Card B.
- Hierarquia visual coerente: Card B autoritativo (`info`/`feature`)
  > Card A satélite (`neutral`).
- Cross-link explícito permite navegação entre as duas leituras
  (fluxo prospectivo × declaração retrospectiva).
- Zero churn em backend, schema E5, goldens, OpenAPI snapshot.

### ⚠️ Riscos

- **Card A "redundante" em modo informativo.** Aceito: produto fica
  honesto. Se UX reclamar muito, abrir lane futura para evoluir para
  Alternativa C (card unificado).
- **VGBL não tratado.** `flow_classifier` hoje não distingue
  PGBL/VGBL — em workspace simplificado, Card A não pode afirmar
  categoricamente que o aporte detectado é PGBL. Mitigação: copy de
  `informative-simplificado` foca em mecanismo do regime, não no
  aporte específico. Lane futura para classifier VGBL/PGBL.
- **Divergência S7 (aportado observado) > IRPF (declarado)** não
  é abordada nesta lane — G0 recomendou alerta gentil
  ("Identificamos R$ X em aportes no fluxo; declaração registra R$
  Y. Revise antes do próximo IRPF"). Defer para lane dedicada;
  exige cruzar transações classificadas como "previdência" com
  `pgbl_aportado_brl` declarado, e cobertura de cenários (VGBL,
  defasagem temporal).
- **`primary_year` derivado de labels do fluxo** — não há fonte
  canônica server-side de `analysis_period`. Aceito: deriva é
  trivial (1 linha). Quando UI ganhar seletor de período, plumbar
  `analysis_period` no `ReportContext` server-side.

### 🔄 Reversibilidade

Alta. Para reverter:
1. `S7IndependenciaSection` volta a chamar `<PrevidenciaPgblCard
   previdencia={...} />` sem `mode`/`anoBase`.
2. `PrevidenciaPgblCard` mantém compat: `mode = "default"` default
   preserva comportamento legacy.
3. Helper `pgbl-card-strategy.ts` pode ser deletado sem regressão
   se ninguém mais o consumir.

Sem migração DB; sem mudança em domain Python; sem breaking de
contrato externo.

## §6 — Não-objetivos (esta ADR)

- **Não** unificar os dois cards num único componente / aggregate
  (Alternativa C — defer indefinido).
- **Não** modificar `PrevidenciaAnalyzer` ou `IRPFAnalyzer`.
- **Não** introduzir alerta de divergência S7 (aportado observado) >
  IRPF (declarado) — lane futura.
- **Não** distinguir PGBL/VGBL no `flow_classifier` — lane futura
  (`track_vgbl_pgbl_classifier`).
- **Não** plumbar `analysis_period` (start/end/primary_year) em
  `StageConfig`/`ReportContext` server-side — quando UI ganhar
  seletor de período.
- **Não** alterar Card B (`IrpfPgblCapacidadeCard`) — exceto
  oportunisticamente adicionar `aria-label` no "—" (a11y).

## §7 — Critério de aceite

Mergeada quando:

1. Helper `frontend/src/lib/irpf/pgbl-card-strategy.ts` com testes
   Vitest cobrindo a matriz da §D1 (7 linhas).
2. `PrevidenciaPgblCard` re-implementado com switch sobre `mode` —
   compat legacy preservada (`mode` opcional, default
   `"default"`).
3. `S7IndependenciaSection` consome `irpfKpis` + `primaryYear`,
   resolve `strategy`, passa props ao card.
4. Testes Vitest cobrem os 6 modos do Card A com asserções pontuais
   (variante, presença/ausência de disclaimer, presença do
   cross-link, copy literal por modo) — pattern de
   `IrpfSections.test.tsx`.
5. `aria-label="Métrica não aplicável"` adicionado ao "—" em modos
   `informative-simplificado`/`sem-renda` (Card A) e oportunismo no
   Card B.
6. `pre-commit run --all-files` verde.
7. `cd frontend && npm test -- --run` verde.
8. `pytest tests -q` e `pytest backend/tests -q` verdes (regressão —
   backend não muda).
9. CI verde no PR.
10. ADR flippa para `Decidido (A12)` no merge.

## §8 — Sign-off G0 (`financial-planner` · 2026-05-12)

Co-design paralelo (sessão `2026-05-12`):

- **Veredito explícito:** Alternativa B.
- **Severidade do cenário 1:** P0/severidade alta — bug de produto
  financeiro com potencial de dano patrimonial (usuário aporta
  esperando dedução que não vem no simplificado).
- **Copy literal §4** aprovada com refinamento (referência ao
  paralelismo lexical com Card B — "tabela regressiva", "horizonte",
  "taxa de administração", "INSS").
- **Janela authoritativa:** IRPF `ano_base = N` authoritativo para
  análise terminando em `N` ou `N+1`; ≥2 anos defasado volta ao
  `default-defasado`. Justificativa: ano fiscal BR fecha 31/12 e
  declaração até abril; 1 ano de defasagem é estado normal entre
  janeiro e abril de qualquer ano.
- **Disclaimer:** Card A ganha disclaimer apenas nos modos
  `default*` (modos `informative-*` desautorizam-se em favor do
  Card B explicitamente).
- **Divergência S7 > IRPF declarado:** sinalizar com calma (não
  silenciar, não acusar) — **defer para lane futura** nesta ADR.

Restrições inegociáveis preservadas: ADR-189 §6.1 intacta;
boundary `PrevidenciaAnalyzer` ↔ `IRPFAnalyzer` preservado;
posição ADR-157 ("capacidade ≠ recomendação") reforçada com
disclaimer no Card A.
