---
id: A36.l3
type: lane
title: "E7: invariante de conservação (CV1-CV14) pausa o run em vez de ser advisory"
sprint: A36
status: planned
priority: P0
branch_slug: a36-l3-e7-conservation-gate
adrs: ["[[ADR-272]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p0
  - area/pipeline
  - area/dados
---

# A36.l3 — `e7-conservation-gate` (DAT-01)

> **Tier P0 (revisão 2026-07-10).** Client-facing: um plano cujos números não
> fecham chega ao cliente sem flag, no exato gate dogfood→beta. Mas o fix
> "só encanamento" descrito originalmente **protegia o alvo errado** — ver
> "Correção de escopo" abaixo. A parte load-bearing é a **re-tag de severidade**,
> não o `validation.valid`.

## Problema

O E7 (`validate_cross`) roda 14 checks de consistência sobre o E5 mas **sempre
retorna `success: True`**, mesmo com `errors_count > 0`
(`scripts/validate_cross.py:530-539`). O loop do pipeline só pausa um run como
`needs_review` quando o resultado tem `detail["validation"]["valid"] == False`
(`backend/app/tasks/pipeline_task.py:1109-1115` e `:1203-1211`) — e o
`validate_cross` **não emite esse bloco**. Resultado: um plano com invariante de
conservação violada pode ser entregue ao cliente **sem flag**.

A boa notícia: o mecanismo de pausa **já existe** e é reusável (foi construído
para os checks determinísticos via [[ADR-272]]). O contrato `validation` também
**propaga intacto** pela cadeia (`orchestrator._with_tail` faz dict-merge, não
strip → `pipeline_client` → `_has_validation_errors`). Basta o E7 falar a mesma
língua — **e falar sobre os checks certos**.

## Correção de escopo (revisão 2026-07-10) — o fix original protegia o alvo errado

Dos 14 checks, **só CV1, CV9 e CV10 emitem `severity="error"`** (verificado em
`scripts/validate_cross.py:117-406`). E o `errors_list` conta **só** os de
severity `error`:

```python
errors_list = [r for r in cv_results if not r.passed and r.severity == "error"]
```

Logo o fix proposto (`"valid": len(errors_list) == 0`) dispararia:

- **CV9/CV10** — narrativas/gráficos ausentes → **defeito de renderização,
  não número errado**. (Pausaria por cosmético.)
- **CV1** — score bate com a própria fórmula → legítimo.

…e **NÃO** dispararia nos checks que são a razão de ser do achado — os "números
que não fecham" — porque são `warning`:

| Check | Valida | Hoje | Deve gatilhar? |
|---|---|---|---|
| CV1 | score × fórmula | `error` | Sim (já) |
| **CV2** | composição do patrimônio × bruto | `warning` | **Sim — promover a `error`** |
| **CV3** | receita − despesa = fluxo líquido | `warning` | **Sim — promover** |
| **CV6** | progresso IF × patrimônio investível | `warning` | **Sim — promover** |
| CV5 / CV7 / CV8 | IF mensal / endividamento / cobertura reserva | `warning` | Sim (borderline) |
| CV4 | taxa de poupança (tol. 5pp) | `warning` | Advisory ok |
| CV9 / CV10 | summaries / charts presentes | `error` | **Render-gate — separar de "número errado"** |
| CV11–CV14 | tarefas / diagnóstico / label / formato | `warning` | Advisory |

## Achado empírico — medição sobre 26 runs de dogfood (2026-07-10)

Guarda pré-execução rodada (`dev/measure_conservation_gate.py --from-db`) sobre
os 26 runs reais de dogfood. Resultado **muda o escopo** e valida a ordem
"medir antes de flipar":

- **A conservação numérica real está saudável:** CV1, CV2, CV3, CV5, CV7, CV8
  **passam em 26/26**. Nenhum relatório saiu com números que não fecham.
- **Dois checks estão obsoletos vs o schema atual do E5 e falham em 26/26 —
  não por dado ruim, por drift do check:**
  - **CV6** lê `patrimonio.investivel`, campo **inexistente** hoje (o E5 emite
    `investivel_financeiro` / `investivel_efetivo`) → assume 0 → "0% de progresso
    IF" → falha sempre. **Bug pré-existente do check.**
  - **CV10** exige o gráfico `alocacao_atual_vs_alvo`, **não mais emitido** (os
    outros 6 obrigatórios estão presentes/completos) → falha sempre. CV10 já é
    `error`.
  - *(CV4 falha em 23/24 — advisory, fora de gate; provável drift de fórmula.)*
- **Consequência crítica:** o fix "só emitir o bloco `validation`" pausaria
  **100% dos runs** no dia 1 (via CV10, que já é `error`) — over-firing
  catastrófico. Por isso a ordem abaixo antepõe o conserto dos checks obsoletos.

### Escopo corrigido pela medição (antecede o "Escopo" abaixo)

0. **Consertar os dois checks obsoletos primeiro** (bugs independentes):
   CV6 → apontar para `investivel_efetivo`/`investivel_financeiro`; CV10 →
   remover/atualizar `alocacao_atual_vs_alvo` da lista de obrigatórios (ou
   restaurar a emissão). Enquanto falharem em 100%, **não podem** estar em gate
   de pausa. Só **CV2/CV3** estão prontos para promover hoje (passam 26/26);
   **CV6 entra no gate só depois de consertado**.

## Escopo

1. **Re-tag de severidade (load-bearing):** promover **CV2, CV3, CV6** (e avaliar
   CV5/CV7/CV8) de `warning`→`error`. Idealmente introduzir um tier próprio
   (`conservation`) para os checks numéricos e gatilhar nele, deixando
   **CV9/CV10 num render-gate à parte** (ausência de gráfico não é "número
   errado"). Isto reabre parcialmente o "fora de escopo" original — a
   *disposição do resultado* sem a severidade certa é falsa garantia.
2. Em `scripts/validate_cross.py`, adicionar ao dict de retorno:
   `"validation": {"valid": len(errors_list) == 0, "errors_count": len(errors_list)}`.
   **Manter `success: True`** — `success` = "rodou sem crashar"; `validation.valid`
   = "achou problema pro humano". Flipar `success` rotearia para `failed_at_stage`,
   não `needs_review`.
3. **Emitir `review_reason`** carregando *qual* CVn quebrou + `details` — o
   revisor precisa do porquê, não só do bloqueio (schema `review_reason` existe).
4. Com isso, o `_has_validation_errors` já existente dispara e o run pausa como
   `needs_review` automaticamente — sem código novo no consumidor.
5. Testes em **dois níveis**: (a) **unit** sobre `main_with_store` —
   `errors_count>0 ⇒ validation.valid==False` e `==0 ⇒ True` (barato, sem DB, é
   o teste load-bearing); (b) **golden/integração** — fixture com CV2/CV3/CV6
   violado pausa o run; run limpo passa igual.

## Política (decidida — não deferir)

Erro de conservação **pausa** como `needs_review`, **não** bloqueia publicação
hard. Razões: (a) checks têm potencial de falso-positivo (thresholds, tolerâncias,
`return None` em dado ausente) — hard-block sobre falso-positivo = nenhum
relatório; (b) `needs_review` mantém humano no loop (no B2B2C futuro, o planejador
*é* o revisor); (c) needs_review **já é** o bloqueio de publicação daquele run
(run que não completa não publica). Warnings remanescentes seguem advisory
(`valid` só conta severity `error`). Registrar via **emenda a [[ADR-272]]**, não
ADR nova.

**Fora de escopo:** reescrever a *lógica* interna dos 14 checks (só a
severidade + disposição). Backfill retroativo (abaixo) é lane P2 separada.

## Gaps conhecidos a nomear (não regressões do fix)

- **Free tier / `skip_llm`:** sem narrativas o E7 retorna
  `success:False, reason:missing_narrativas` (`validate_cross.py:506-508`) e
  **nem roda os checks** — conservação não é verificada nesse caminho.
- **Ausência ≠ erro:** CV2/CV5/CV6 fazem `return None` quando o input está
  ausente/zero. O gate pega *contradição entre números presentes*, não *dado
  faltante*. Um check de completude dos agregados-núcleo é follow-up.
- **Backfill (P2 follow-up):** runs `completed` já entregues com violação nunca
  flagueada. O E7 é read-only e **não persiste verdict** (sem row `stage="E7"`);
  a varredura precisa **reconstruir** os checks sobre o E5 persistido
  (`analyze_finances/analise_financeira`) — script read-only idempotente, zero
  migration. Gated por o fix aterrissar primeiro.

## Critérios de aceite

- Run com **CV2/CV3/CV6** falhando (patrimônio/fluxo/IF que não reconciliam)
  pausa como `needs_review`; run limpo passa sem regressão.
- `review_reason` do run pausado nomeia o CVn violado + `details`.
- CV9/CV10 (render) tratados em gate separado — não conflatados com "número errado".
- Unit sobre `main_with_store` (`errors_count>0 ⇒ valid==False`) + golden de
  conservação-violada travando; golden limpo verde.
- `success: True` preservado (não vira `failed_at_stage`).

**Esforço:** M. **Origem:** auditoria r4 (DAT-01).
