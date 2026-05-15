---
id: ADR-217
type: adr
title: "Score patrimonial canônico — composição, fórmula e ciclo de vida"
status: Proposto
phase: A12
date: "2026-05-15"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-097]]"
  - "[[ADR-117]]"
  - "[[ADR-143]]"
  - "[[ADR-188]]"
  - "[[ADR-212]]"
  - "[[ADR-218]]"
  - "[[ADR-219]]"
supersedes: []
superseded_by: []
aliases: ["ADR 217", "score-patrimonial-canonico", "score-gauge-s1"]
tags:
  - area/relatorio
  - area/pipeline
  - area/methodology
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - phase/a12
  - status/proposto
  - type/adr
---

## Contexto

`S1.score_gauge` é o KPI agregado da capa do relatório — primeira leitura
que o cliente faz da própria saúde patrimonial. O componente
[`ui/ScoreCard.tsx`](../../frontend/src/components/report/ui/ScoreCard.tsx)
consome `analise_financeira.score.{valor, max, classificacao, componentes,
breakdown, formula}`. Revisão card-a-card 2026-05-15 (workspace 5@5.com,
relatório `6307646a-06ee-4e16-96fb-e04cbd6a713c`) detectou:

- Chave `score` **não é emitida** pelo E5 — zero ocorrências no artifact
  194 (`pipeline_artifacts.content_json`).
- Renderer faz `{score && ...}` em
  [`S1PatrimonioSection.tsx:70`](../../frontend/src/components/report/sections/S1PatrimonioSection.tsx) —
  esconde silenciosamente. Cliente vê seção S1 sem o card hero.
- Não existe ADR de fórmula, não há service de domínio, não há teste
  de regressão. A feature é stub.

Três decisões pendentes: (a) qual é a composição metodologicamente
defensável, (b) como tratar componente sem dado (caso S9/seguros, hoje
zerada), (c) onde mora a fórmula e como evoluir sem quebrar runs
antigos.

## Decisão

### D1 — Composição fixa de 5 componentes

Todo score é a soma ponderada de cinco componentes determinísticos,
sempre os mesmos, sempre nos mesmos pesos:

| Componente | Peso | Fonte de domínio | Faixa |
|---|---|---|---|
| `reserva_emergencia` | 30% | `analise_financeira.reserva_emergencia.meses_cobertos_essencial` ([[ADR-218]]) | 0–6m → 0–80; ≥6m → 80–100 (saturado em 12m) |
| `endividamento` | 25% | `analise_financeira.endividamento.percentual_patrimonio` | ≥30% → 0; 10–30% → 0–80; <10% → 80–100 |
| `diversificacao_auvp` | 20% | `goals.alocacao_alvo` vs. `investimentos.tabela_classes` | desvio máx por classe: 0pp → 100; >30pp → 0 |
| `taxa_poupanca` | 15% | `ratios.taxa_poupanca_recorrente_pct` | <10% → 0; 10–30% → 30–80; ≥30% → 80–100 |
| `cobertura_seguros` | 10% | (futuro) `seguros.gap_cobertura_pct` ([[ADR-220]] · S9) | 100% gap → 0; 0% gap → 100 |

**Pesos congelados** no código (`frozen dataclass`
`pipeline/domain/services/score_calculator.py`), não em DB. Mudança de
peso exige ADR sucessora — operador não muda fórmula via console.
Justificativa: comparabilidade longitudinal (workspace acompanhando ao
longo de 12 ciclos) é inegociável.

### D2 — Componente sem dado declara `status` explícito, denominador permanece 100

Componente sem dado **não** re-normaliza. Score natural fica menor enquanto
não houver dado — é **feature**, não bug: incentiva onboarding. O payload
expõe honestamente o que falta:

```json
{
  "score": {
    "valor": 67,
    "max": 100,
    "score_version": "1.0",
    "classificacao": "bom",
    "componentes": [
      {"id": "reserva_emergencia", "peso": 30, "valor": 25, "status": "emitted"},
      {"id": "endividamento",      "peso": 25, "valor": 23, "status": "emitted"},
      {"id": "diversificacao_auvp","peso": 20, "valor": 8,  "status": "emitted"},
      {"id": "taxa_poupanca",      "peso": 15, "valor": 11, "status": "emitted"},
      {"id": "cobertura_seguros",  "peso": 10, "valor": 0,  "status": "absent_normalized"}
    ],
    "breakdown": {...},
    "formula": "score = Σ(componentes[i].peso × componentes[i].valor / 100)"
  }
}
```

`status` enum: `emitted` (dado presente, valor computado), `absent_normalized`
(dado não declarado, peso conta como 0 — natural penalty),
`absent_penalized` (futuro, ex.: dado declarado inválido — penalty
explícito). Renderer mostra honestamente "Cobertura de seguros — não
avaliado, declare para destravar 10 pp do score" via badge condicional.

Decisão (vs. alternativa "re-normalizar quando ausente"): re-normalização
introduz incomparabilidade silenciosa entre workspaces (score 75 sem
seguros ≠ score 75 com seguros, sem como saber). Denominador fixo
preserva comparabilidade.

### D3 — `score_version` obrigatório no payload

`score.score_version: "1.0"` em todo emit. Quando a fórmula mudar (v2),
runs antigos continuam interpretáveis (renderer escolhe lógica por
versão; comparação multi-ciclo fica explícita). Versionamento da fórmula
é o gate de evolução sem breaking — sem ele, qualquer ajuste de peso
contamina histórico retroativamente.

### D4 — Service puro de domínio em `pipeline/domain/services/score_calculator.py`

Service novo, puro (sem I/O), recebe inputs já tipados:

```python
@dataclass(frozen=True)
class ScoreInputs:
    reserva: ReservaEmergenciaSnapshot  # de ADR-218
    endividamento: EndividamentoSnapshot
    alocacao_atual: AllocationByClass
    alocacao_alvo: AllocationByClass | None
    taxa_poupanca_pct: Decimal
    cobertura_seguros: GapProtecaoSnapshot | None  # None → status: absent_normalized

@dataclass(frozen=True)
class ScoreResult:
    valor: int            # 0..100
    max: int              # = 100
    score_version: str    # "1.0"
    classificacao: str    # critico|atencao|bom|excelente
    componentes: tuple[ScoreComponent, ...]
    breakdown: dict[str, Any]
    formula: str
```

Service é testável por valores de referência sem fixture pesado. Stage
`analyze_finances` (E5) chama o service e injeta o resultado no payload
sob `score`. Não inline no `e5_analyze.py` — viola SRP do stage e impede
reuso (parecer E6 pode consultar componentes individuais; API ad-hoc
futura idem).

### D5 — Classificação por faixa (estável)

| Faixa | Classificação |
|---|---|
| 0–49 | `critico` |
| 50–69 | `atencao` |
| 70–84 | `bom` |
| 85–100 | `excelente` |

Faixas fixas no `score_version: "1.0"`. Renderer
[`ScoreCard.tsx`](../../frontend/src/components/report/ui/ScoreCard.tsx)
já consome este shape — apenas remover o `{score && ...}` defensivo após
emit estabilizar.

### D6 — Schema evolution: aditivo, modo `warn`, recompute on-read

Schema E5 ganha `score?: ScoreSchema` em
[`config/schemas/e5_analysis.schema.json`](../../config/schemas/e5_analysis.schema.json),
**opcional aditivo**. Modo `warn` (default, [[ADR-212]] hook
`validate_dict`) até flip strict — flip só quando S9/seguros emite
(`cobertura_seguros.status: emitted` em todos os goldens canônicos).

**Backfill: recompute on-read.** Service `ScoreReader` lê o E5 e, se
`score` ausente, computa em memória usando os mesmos inputs (não
persiste). Evita migration em massa de `pipeline_artifacts`
(viola idempotência de runs históricos) e mantém o renderer
determinístico para artifacts antigos.

## Custos & Trade-offs

- **Comparabilidade vs. naturalidade.** Denominador fixo significa que
  workspace sem seguros nunca atinge 100. Para alguns clientes isso pode
  parecer "score injusto" — mitigado pela explicação "10 pp ainda em
  potencial". Trade-off aceito: rigor metodológico > UX confortável.
- **Versionamento da fórmula.** `score_version` adiciona overhead de
  governance — toda mudança exige ADR. Aceito: comparabilidade
  longitudinal é load-bearing num produto premium de planejamento.
- **Recompute on-read.** Custo computacional desprezível (5 valores
  derivados, sem LLM). Custo cognitivo: leitor precisa saber que o
  número pode ter sido computado pelo `ScoreReader`, não emitido pelo
  E5. Documentar em [`docs/reference/PIPELINE_ARTIFACTS.md`](../reference/PIPELINE_ARTIFACTS.md).

## Alternativas consideradas

- **Composição com 4 componentes (sem seguros)** — funciona hoje mas não
  cria alavanca de onboarding para destravar S9. Rejeitada.
- **Re-normalização quando seguros ausente** — esconde a decisão de
  produto, quebra comparabilidade cross-tenant. Rejeitada (senior-cto +
  data-engineer).
- **Score qualitativo (excelente/bom/atenção/crítico) sem nota numérica** —
  mais robusto a edge cases mas quebra o `ScoreCard` pronto e perde a
  utilidade de "delta vs ciclo anterior" pedida na revisão. Rejeitada.
- **Fórmula em DB (configurável por operador)** — flexibilidade vs. rigor
  metodológico. Rejeitada — métodos congelam por ADR, não por raw SQL.

## Implementação

PR único, escopo:

- `pipeline/domain/services/score_calculator.py` (novo) — service puro
  + dataclasses tipadas + testes por valor de referência (3 cenários:
  completo, sem seguros, sem investimentos).
- `config/schemas/e5_analysis.schema.json` — adicionar `score?:`.
- `pipeline/stages/e5_analyze.py` — emit `score` chamando o service.
- `backend/app/services/score_reader.py` (novo) — recompute on-read para
  artifacts antigos.
- `frontend/src/components/report/sections/S1PatrimonioSection.tsx` —
  remover `{score && ...}` defensivo; tratar `status: absent_normalized`
  como caso explícito no `ScoreCard`.
- Golden de regressão em `tests/test_e5_golden_execution.py` para o
  workspace 5@5.com (valor de score esperado documentado).
- Registrar `ScoreReader` em
  [`docs/reference/STATELESS_AUDIT.md`](../reference/STATELESS_AUDIT.md)
  §2 se ganhar singleton.

**Dependências:**

- Bloqueado por [[ADR-218]] (D1 reserva_emergencia usa `meses_cobertos_essencial`,
  que esta ADR introduz).
- Bloqueado parcialmente por [[ADR-219]] (componente
  `diversificacao_auvp` referencia premissas econômicas para alocação
  alvo metodologicamente justificada — mas v1 aceita alvo configurado
  pelo usuário sem essa cadeia).
- Flip strict pendente de S9 (`seguros` emit no E5).

## Critério de aceite

- [ ] Service calcula 100 para inputs perfeitos (reserva 12m, endivid. 0%,
      alocação alinhada ±2pp, taxa poup. 30%, gap seguros 0%).
- [ ] Score natural decresce quando `cobertura_seguros.status =
      absent_normalized` — comparável entre runs antigos e novos.
- [ ] `score_version: "1.0"` presente em todo emit.
- [ ] Renderer S1 não usa mais o guard `{score && ...}` defensivo.
- [ ] Golden no workspace 5@5.com não regride.
