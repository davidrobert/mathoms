---
id: MOC-sprint-a26
type: moc
title: "Sprint A26 — Data Lineage: consolidação"
aliases: ["A26", "Sprint A26"]
sprint_status: current
date: "2026-06-16"
theme: "data-lineage"
---

# Sprint A26 — Data Lineage: consolidação

> **Status:** `current` (promovida 2026-06-16) — sucede [[MOC-sprint-a25]] (`done`).
> 5ª janela do plano [[PLAN-data-lineage]]: **remove as redes de segurança** criadas
> na A23–A25 (shims de identidade v1, modo `warn` permissivo do `evidencia_path`)
> depois que a observação em produção confirma que é seguro. Co-design 2026-06-16:
> `product-manager` + `information-architect` (forma) + `data-engineer` (migrações
> destrutivas) + `prompt-engineer` (flip strict) + `sre-devops` (runbook Fase E).
> Prompt de orquestração: [agent_prompts/orchestrator_a26_consolidacao.md](../../agent_prompts/orchestrator_a26_consolidacao.md).
>
> **[[A26.l1]] shipada (#654)** (fix de prompt do `evidencia_path`) — destravou a
> métrica dos gates seguintes. O resíduo `value_mismatch` migrou para **[[A26.l8]]**
> (`planned`, sem gate de tráfego; bloqueia o flip strict da [[A26.l2]]). As
> demais (l2–l5) seguem `blocked` por **gates de volume de produção** (≥20 gerações de
> parecer; ≥1 sprint com flags v2 a 100% + counter `dualread.v1_fallback` zerado **com
> uso real exercitado**) — pré-launch, fecham por **tráfego/dogfood**, não por calendário.
> Insumos para destravar: `ANTHROPIC_API_KEY` no ambiente + ~20 gerações de parecer +
> exercício do override v2 por ≥1 sprint + confirmar PITR do Postgres.

## Tese

Durante A23 (contrato aditivo) → A24 (de-leak + walking skeleton) → A25 (reverso +
produto N1/N2 + debug LLM), cada mudança de identidade entrou com uma **rede**: o shim
v1 vivo ao lado do v2 (rollback = flag off) e o `evidencia_path` em `warn` (observa, não
bloqueia). A A26 é a **sprint de consolidação**: desligar as redes — ligar o `strict`,
deletar os shims v1 — quando o uso real provar que é seguro. O custo de antecipar é
**assimétrico** (drops irreversíveis, bloqueios de parecer em massa); por isso cada
lane destrutiva tem um **gate verificável**, não um prazo.

## Dois regimes de bloqueio (organiza as lanes)

- **Regime A — bloqueado por bug de código, não por tráfego:** [[A26.l1]] (fix de
  citação do `evidencia_path`). Executável já; corrige a métrica que polui o gate do flip.
- **Regime B — bloqueado por observação de produção:** [[A26.l2]] (flip strict),
  [[A26.l3]] (drop shim dedup v1), [[A26.l4]] (override v2 ON + instrumentação),
  [[A26.l5]] (M2 override destrutiva). Todas gated por volume/tempo de tráfego.

## Lanes (co-design 2026-06-16)

| Lane | Slug | Regime | Status | Dep / Gate |
|---|---|---|---|---|
| [[A26.l1]] | `evidencia-prompt-catalogo` | A (sem gate) | ✅ shipped (#654) | — · ponto de entrada da sprint |
| [[A26.l2]] | `evidencia-flip-strict` | B | blocked | gate redefinido (2026-06-19): segurança binária (0 errado publicado — ✅ via l8) + budget needs_review ≤15% sobre ≥20 ger |
| [[A26.l3]] | `drop-dedup-v1-shim` | B (reversível) | blocked | dedup v2 100% + counter zerado ≥1 sprint |
| [[A26.l4]] | `override-v2-on-instrumentacao` | B (habilitador) | blocked | flip override flag→True + `v2_match_count` + query agendada `v1_fallback` |
| [[A26.l5]] | `m2-override-drop` | B (IRREVERSÍVEL) | blocked | l4 + G1/G2/G3 + PITR + owner go/no-go |
| [[A26.l6]] | `evidencia-coverage-kpi` | A (sem gate) | shipped (#660) | — · roda antes de l7 (baseline) |
| [[A26.l7]] | `evidencia-catalog-listas` | A (sem gate) | shipped (#662) | l1 · recomendada antes do flip l2, não bloqueante |
| [[A26.l8]] | `evidencia-value-mismatch` | A (sem gate) | planned | l1 · resíduo `value_mismatch` (eval 1.7.0: UB 49,9%); bloqueia l2 |
| [[A26.l9]] | `citacao-deterministica` | A (sem gate) | shipped (#687) | l1 · render valor da folha server-side (value_mismatch→0); **A27/Onda 6, Could, NÃO bloqueia l2** ([[ADR-296]]) |

**Ordem de execução (risco crescente):** l1 → l2 (flip precisa do prompt corrigido);
l3 (drop reversível, "canário") antes de l5 (drop irreversível); l4 habilita o gate de
l5. l3/l4/l5 independentes de l1/l2.

**Precedência de corte:** **Must** = l1 (destrava a métrica) + l2 (flip strict é o
núcleo do guardrail). **Should** = l3 (higiene de dead code; v1/v2 dual-read não custa
rodando) + l4 (habilita o gate da l5) + **l6** (instrumenta o gate de l2 — auditável,
mesma classe de l4) + **l7** (fecha a raiz comportamental do [[ADR-292]]; barato,
sem-gate, mas cortável p/ A27 — l2 flipa fail-open sem ela). **Could / cortável sem dó**
= l5 (M2 override — destrutivo + PITR, maior risco; corta para A27 se a janela de tráfego
for curta — nunca forçar sob gate apertado).

## Cobertura de citação (Onda 6 — adições pós-[[ADR-292]])

Ortogonal aos dois regimes de bloqueio acima: a [[A26.l6]] + [[A26.l7]] não removem
rede de segurança (tese da Onda 5) — **ampliam a cobertura** da citação verificada
E5→E6, fechando a raiz do incidente do parecer (2026-06-16, `claude-sonnet-4-6` emitia
JSONPath com filtros para citar valores de **lista** que o catálogo v1 não oferecia;
[[ADR-292]] coagiu path inválido→None, mas o gap de cobertura persiste). São **Regime A**
(sem gate de tráfego). Ordem: **l6 (KPI/baseline) → l7 (catálogo cobre listas)**, para
medir a redução de `missing_path`. Conformam [[ADR-279]] §E + [[ADR-292]] — **sem ADR
nova**. O follow-up mais profundo (citação de lista por chave estável + materializar a
citação como edge no grafo de lineage) é **A27 / Onda 6**, atrás de [[ADR-293]] `Proposto`
(uma decisão só: edge sem chave = lineage podre; chave sem edge = código morto).

## KRs da janela (readiness/saúde, não "conclusão")

- **KR1** — conformidade de citação do `evidencia_path` (path ∈ whitelist + resolve
  não-nulo) **≥95%** sobre as gerações disponíveis (baseline A25: ~28% conforme).
  Controlável **hoje** via l1; é o que destrava os demais gates. **Pós-[[A26.l7]]** o
  denominador passa a incluir paths de **lista** (cobertura ampliada) — a meta ≥95% é
  re-ancorada na baseline medida pela [[A26.l6]]; é refinamento de definição, não KR novo.
- **KR2** — `mathoms.categorization.dualread.v1_fallback` **= 0 sustentado por ≥1
  sprint de tráfego v2 a 100%** com uso real exercitado (não zero por inatividade).
  Mede a *condição de gate* dos drops, não o ato de dropar (l4 instrumenta).
- **KR3** — consolidações destrutivas executadas **com gate fechado verificado antes do
  PR**: flip strict (l2) + drop shim dedup (l3) + M2 override (l5). Binário condicionado
  ao gate — não incentiva deletar cedo.
- **Gate do flip strict (REDEFINIDO 2026-06-19 — ver [[A26.l2]]):** o gate original
  "`needs_review` per-parecer <5%" misturava **segurança** com **UX** e era inatingível
  (eval 1.8.0: 22%, pois ~87% das falhas é `wrong_pairing` em itens severidade alta).
  Separado em: **(1) segurança (binário, bloqueia):** zero citação incorreta publicada —
  **a garantir pelo enforcement per-item** ([[A26.l8]] `planned` / [[ADR-295]]: item
  dropado ou `needs_review`, nunca número errado no output — landa quando l8 shipar); **(2) budget de UX
  (orçamento, não bloqueia):** `needs_review` per-parecer **≤15%** sobre ≥20 ger reais,
  re-ancorável no 1º tráfego — exceder prioriza [[A26.l9]] (A27), não reabre o flip.
  Reabre a decisão "per-parecer <5%" do orchestrator §5 com evidência empírica (mesma
  força da [[ADR-295]]); sem ADR nova (conforma [[ADR-279]] §E + [[ADR-295]]).

## Decisões herdadas (sem ADR nova)

- **ADR-279 §E** — contrato do `evidencia_path` (l1/l2 conformam; flip não reabre).
- **ADR-287 §Cutover** — `Decidido`; M2-A (drop shim dedup) é execução do runbook já decidido.
- **ADR-282** — `Proposto`; a M2-B ([[A26.l5]]) fecha a "Fase E" e **flippa ADR-282 →
  `Decidido (A26)`** no merge da implementação.

## Correções de fato registradas no co-design

1. `generate_transaction_hash` vive em `backend/app/services/transaction_service.py`
   (identidade do **override**, alvo da [[A26.l5]]); `compute_transaction_hash` vive em
   `pipeline/domain/services/_tx_identity.py` (shim do **dedup**, alvo da [[A26.l3]]).
   São funções distintas, módulos distintos, lanes distintas.
2. `override_natural_key_v2_enabled` é **default `False`** hoje — o gate "counter zerado"
   é vácuo até a [[A26.l4]] flipar o default e exercitar o caminho v2 em tráfego real.

## Bloqueadores duros antes de abrir a Fase E (sre-devops)

1. **Instrumentar a verificação do gate** — `dualread.v1_fallback` hoje é só
   `logger.info`, sem métrica/query agregável. [[A26.l4]] adiciona query agendada +
   `v2_match_count` para tornar o gate **auditável** (não grep ad-hoc).
2. **Confirmar PITR do Postgres (Coolify)** — `RUNBOOK §5` ainda trata DR off-site como
   pendente. Sem PITR contínuo, a contingência da [[A26.l5]] é restore do snapshot
   lógico com perda desde o dump. Confirmar a capacidade real **antes** do drop.

- **Plano dono:** [[PLAN-data-lineage]] ([plan/DATA_LINEAGE/_README.md](../../plan/DATA_LINEAGE/_README.md)) §Onda 5.
- **Carry-overs de origem:** [[A25.l7]] (decisão evidencia_path) · [[ADR-287]] §Cutover (M2 dedup) · [[A25.l1]] §5 (gate M2 override).
