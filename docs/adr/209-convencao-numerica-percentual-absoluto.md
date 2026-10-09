---
id: ADR-209
type: adr
title: "Convenção numérica de percentual no contrato E5 — valor absoluto"
status: Decidido
phase: "Pré-requisito PR-2 do PLANNER_REVIEW"
date: "2026-05-13"
amended_at: ["2026-10-09"]
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-143]]"
  - "[[ADR-199]]"
  - "[[ADR-201]]"
  - "[[ADR-202]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 209"
  - "Convencao numerica percentual"
  - "Pct absoluto E5"
tags:
  - area/pipeline
  - area/llm
  - area/data-contract
  - phase/a11
  - status/decidido
  - type/adr
---

# ADR-209 — Convenção numérica de percentual no contrato E5 (valor absoluto)

**Status:** Decidido (pré-requisito PR-2 do PLANNER_REVIEW) • **Data:** 2026-05-13

> **Emendada em 2026-10-09** — o `formatPercent` deixou de ser legado: é o formatador
> canônico de percentual do relatório. A §D3 (Camada 4) e o risco de "limpeza em
> sprint+1" ficam superados; a regra de que o formatador não multiplica continua.
> Ver §Emenda 2026-10-09.

> **Emendada em 2026-10-09 (b)** — a emenda acima apoia a segurança do formatador na
> D1, mas a D1 não vale em quatro campos `*_pct` do E5: eles chegam como razão 0..1, e
> o frontend multiplica por 100 antes de formatar. Só um deles tem registro (RV4-51).
> Ver §Emenda 2026-10-09 (b).

## Contexto

- Brainstorm 2026-05-12 do plano `docs/archive/PLANNER_REVIEW-2026-07-09.md` (achado **DE-I.2** do `data-engineer`) identificou que o E5 (`config/schemas/e5_analysis.schema.json`) tem risco de inconsistência de unidades de percentual entre campos `*_pct`: alguns absolutos (`44.7` = 44,7%), outros fracionais (`0.447` = 44,7%).
- Classificado como **bloqueador do Ato 4** ("Sem isso, hallucination numérica garantida: LLM dirá 'rentabilidade 0,45% ao ano' quando real é 45%").
- Auditoria executada nesta lane (`_scratch/pr2_pct_audit_20260513-1012.md`) cobriu 25+ services em `pipeline/domain/services/`, 7 schemas em `config/schemas/`, 12+ tipos no frontend e todos os scripts `e5_*`. **Conclusão:** a convenção **atual de produção é uniformemente ABSOLUTA**. Não há campo emitindo fracional para o E5. Mas:
  - A convenção **nunca foi codificada como regra** (ADR-143 cobre methodology, não convenção numérica de contrato).
  - 3 pontos dormentes carregam risco futuro (heurística frontend `conclusionUtils.format("pct")`, `formatPercent` legado, type TS `MetaIfData.progresso_pct // 0..1`).
  - Persona do planejador ([[ADR-201]]) tem 20 regras (R1-R20) mas **nenhuma** sobre convenção numérica — LLM pode confundir `cobertura_despesa_essencial_pct: 350.0` (válido, 3,5× cobertura) com erro de unidade.
- [[ADR-143]] (methodology = code) estabelece: regras universais de produto vivem co-localizadas com enforcer + ADR canônica. Convenção numérica é regra de domínio — merece tratamento formal análogo a [[ADR-090]] (Money nunca é float).

## Alternativas consideradas

1. **Status quo:** confiar que a convenção é óbvia pela leitura dos services. Pró: zero custo. Contra: novo dev/agente acaba importando fracional num campo novo; LLM tem precedente em literatura financeira para ambas convenções (regulação CVM usa `0.045` em alguns docs; produtos varejo usam `4,5%` direto); risco DE-I.2 permanece latente. **Rejeitada.**
2. **Migrar tudo para fracional (0..1):** mais alinhado com APIs financeiras internacionais (ex.: `decimal.Decimal("0.045")` para taxa). Pró: precisão de uma casa extra; alinhado com `Decimal` natural. Contra: **breaking** (~30 campos, todos os schemas, todos os goldens, todos os outputs históricos); frontend formatter natural espera fracional (`Intl.NumberFormat({style:"percent"})`) — mas todo o resto do código assume absoluto; ganho marginal. **Rejeitada.**
3. **Manter absoluto e codificar como ADR + enforcer multi-camada.** Pró: zero migração de dados, zero schema bump breaking, alinha com a convenção real de produção (`44.7`), legível para LLM em prompts (`"rentabilidade 4,7% a.a."` é mais natural que `"rentabilidade 0,047"`), legível em debug/log. Contra: discordante do `Intl.NumberFormat({style:"percent"})` — exige `formatPercent` custom no frontend. **Aceita.**
4. **Rename de campos** (`valor_pct` → `valor_pct_abs`) para tornar a unidade explícita no nome. Pró: zero ambiguidade. Contra: breaking massivo em ~30 campos, schemas, frontend types, queries SQL, ADRs históricas; custo desproporcional. **Rejeitada.**

## Decisão

**Adotar convenção absoluta** como regra de domínio do contrato E5/E4/E1.5/goals/pipeline + enforcers multi-camada (schema + persona + manifest + frontend formatter).

### D1. Regra canônica

Todo campo no contrato cujo nome contém `*_pct`, `pct_*`, `percentual_*` é **valor numérico absoluto**: `44.7` significa **44,7%**. Casos limítrofes:
- Valores `> 100` são válidos quando semanticamente possível (ex.: `cobertura_despesa_essencial_pct: 350.0` = renda passiva cobre 3,5× a despesa).
- Valores `< 1` são válidos (ex.: `valor_pct: 0.5` = 0,5% a.a. para uma rentabilidade real baixa).
- Valores negativos são válidos quando o campo descreve variação (ex.: `delta_pct: -12.3` = caiu 12,3%).

### D2. Exceção documentada — strings legadas

Quatro campos serializam o **valor absoluto como string** com 2 casas decimais (legado de `"N/D"` fallback). Mantidos por compat:

| Campo | Local | Exemplo |
|---|---|---|
| `ratios.rentabilidade_pct` | `ratios_calculator.py:125` | `"3.20"` ou `"N/D"` |
| `ratios.aliquota_efetiva_ir_pct` | `ratios_calculator.py:126` | `"22.50"` ou `"N/D"` |
| `irpf_kpis.aliquota_sobre_tributavel_pct` | `e5_analyze.py:2969` | `"22.50"` |
| `irpf_kpis.aliquota_sobre_total_pct` | `e5_analyze.py:2970` | `"15.30"` |

Consumidores devem fazer cast `float(str.replace(",", "."))` antes de operação numérica. Não substituir por número puro neste PR — breaking sem ganho. Future ADR pode unificar quando houver outro motivo de breaking change.

### D3. Defesa em profundidade — 4 camadas

**Camada 1 — Schema documentação ([[ADR-202]] estende):**
- `config/schemas/e5_analysis.schema.json`: cada campo `*_pct` declarado tem `description` explícita.
- Padrão: `"Percentual absoluto (44.7 = 44,7%). Sentinela: ..."`.
- Não breaking — apenas documentação. Validador JSON Schema continua tipando como `number`.

**Camada 2 — Persona do planejador ([[ADR-201]] R21):**
- Nova regra `R21` em `config/agents/planner_persona.md` instrui LLM sobre convenção e exceção (strings).
- Persona hash recalculado no próximo run → audit trail.

**Camada 3 — Manifest declarativo ([[ADR-200]]):**
- `narrative_hints_global` em `config/prompts/parecer_planejador.yaml` carrega regra explícita no exec context.
- Bump `version: 1.0 → 1.1` invalida cache Redis automaticamente.

**Camada 4 — Frontend formatter:**
- `frontend/src/components/report/utils/conclusionUtils.ts` (`format(value, "pct")`) remove heurística `value <= 1 ? value * 100 : value` (bomba-relógio para `valor_pct < 1`).
- `frontend/src/lib/format.ts` (`formatPercent`) flagada como legado (não chamada pelo report; permanece para uso interno em `formatDelta`).
- Type morto `MetaIfData.progresso_pct // 0..1` corrigido para refletir convenção real.

### D4. Aplicabilidade — escopo do contrato

Todos os campos em:
- `config/schemas/e5_analysis.schema.json` (E5 — analise_financeira)
- `config/schemas/baseline_patrimonial.schema.json` (E1.5)
- `config/schemas/e4_unified.schema.json` (E4)
- `config/schemas/goal.*.schema.json` (Goals — IF, alocação, aporte mensal)
- `config/schemas/pipeline.schema.json` (thresholds)
- `config/schemas/parecer_planejador.schema.json` (output do parecer)
- Exec context destilado entregue ao LLM em qualquer stage
- Respostas de tool `get_e5_section` e `get_e5_jsonpath` ([[ADR-203]])

**Fora do escopo:**
- Snapshot DB do `pipeline_artifacts` (DataAPI agnóstica). Convenção propaga porque os bytes são iguais.
- `decimal.Decimal` interno em domain services (já é Decimal absoluto antes de serializar).
- Tabela `fiscal_parameters.ir_brackets.aliquota_pct` — input config, não output runtime. Mesma convenção, sem mudança.

## Plano de cutover

**Esta ADR + os 4 fixes em sequência são um único PR atômico** (~120 linhas):

1. **ADR criada** (este arquivo) `Proposto`.
2. **Persona R21** em `config/agents/planner_persona.md` §5.
3. **Manifest narrative_hints_global** em `config/prompts/parecer_planejador.yaml`. Bump `version` 1.0→1.1.
4. **E5 schema descriptions** em `config/schemas/e5_analysis.schema.json` para os 6 campos `_pct` declarados.
5. **Frontend hardening** em `frontend/src/components/report/utils/conclusionUtils.ts` e `frontend/src/types/report-analysis.ts`.
6. Testes do frontend e do pipeline atualizados ou criados.

ADR vira `Decidido (A12 — pré-PLANNER_REVIEW Ato 4)` no merge.

## Critério de aceite

- [x] Auditoria documentada (`_scratch/pr2_pct_audit_20260513-1012.md`).
- [ ] ADR-209 criada com frontmatter validado por `dev/validate_frontmatter.py`.
- [ ] Persona R21 mergeada.
- [ ] Manifest hint global mergeado; `version` bumped.
- [ ] Schema descriptions mergeadas (não breaking).
- [ ] Frontend `conclusionUtils.format("pct")` sem heurística.
- [ ] Testes verde: `pytest tests -q`, `pytest backend/tests -q`, `cd frontend && npm test -- --run`.
- [ ] `dev/check_planner_manifest_coverage.py` continua verde.
- [ ] PR mergeado em `main` antes do início do Ato 4 do PLANNER_REVIEW.

## Riscos

- **Baixo:** falsos negativos da Camada 2 (persona). LLM tem 1-3% de chance de ignorar regra; mitigado pela Camada 3 (manifest no exec context — exposto a cada call).
- **Baixo:** alguma chamada futura ao `formatPercent` legado supondo fracional permanece dormente; flag para limpeza em sprint+1.
- **Baixo:** workspace com `valor_pct < 1` (rentabilidade < 1% a.a.) hoje renderizado errado pelo `conclusionUtils.format("pct")`. Frontend fix corrige.

## Emenda 2026-10-09 — `formatPercent` é o formatador canônico, não legado

A §D3 (Camada 4) flagou `formatPercent` (`frontend/src/lib/format.ts`) como legado, "não
chamada pelo report", e o §Riscos pediu limpeza na sprint seguinte. A prática inverteu
as duas coisas:

- #1403 (2026-08-12, RV4-19 do [[REPORT-REVIEWS-active]]) passou a usá-lo nos cards da
  tabela de composição, inclusive na linha de total, para as duas pontas não divergirem.
- #2091 (2026-10-09) trocou por ele os percentuais com ponto do relatório e criou o gate
  ESLint de `toFixed(n)` colado ao `%`. O COPY_GUIDELINES §4.6 o prescreve como a
  renderização de percentual.
- #2126 (2026-10-09) levou os 35 `toFixed(n).replace(".", ",")` restantes para
  `formatPercent`/`formatNumber`, com gate para a vírgula escrita à mão.

Re-medido em 2026-10-09: 59 chamadas em 28 arquivos de `frontend/src/components/report/`
(`rg -c 'formatPercent\(' frontend/src/components/report`).

**O que continua valendo:** o formatador recebe o valor absoluto e não multiplica
(`44.7` é 44,7%) — é a D1 que torna seguro usá-lo no relatório inteiro. O risco do
§Riscos muda de natureza: deixa de ser uma função dormente e passa a ser qualquer
chamador que receba fração. A proteção é a D1 (campos `*_pct` absolutos no contrato),
não a remoção da função.

## Emenda 2026-10-09 (b) — a D1 não vale em quatro campos do E5

A §Emenda 2026-10-09 conclui que a proteção contra chamador que recebe fração "é a D1
(campos `*_pct` absolutos no contrato)". Medido no mesmo dia (`main` @ `6918df1b`):
quatro campos `*_pct` do E5 chegam como razão 0..1, e o frontend compensa
multiplicando por 100 antes de chamar `formatPercent`.

| Call-site (em `frontend/src/components/report/`) | Campo do E5 | O que o schema declara |
| --- | --- | --- |
| `sections/SProtecao/ProtecaoKpiHero.tsx` | `protecao_patrimonial.pct_renda_anual` | "0..1 como decimal; 0.025 = 2.5%" |
| `sections/SProtecao/ProtecaoGapVeiculos.tsx` | `protecao_patrimonial.bens_com_gap_cobertura[].gap_pct` | nada; o produtor emite `(fipe - lmi) / fipe` |
| `cards/CascataFiscalCard.layers.tsx` | `tributario.cascata.carga_total_pct` | "RAZÃO 0–1 (…), não percentual" |
| `cards/CascataFiscalCard.header.tsx` | `tributario.cascata.fator_r_pct` | "razão 0–1" |

Quem chamar `formatPercent` num desses campos confiando na D1 publica um valor 100×
menor (`formatPercent(0.025)` → `"0,0%"`). Método: `*_pct` com descrição fracionária
em `config/schemas/`, mais `* 100` em `frontend/src` (fora do relatório não há
compensação). Campo fracionário sem unidade declarada e sem compensação no call-site
escapa aos dois.

Os quatro estão no escopo da §D4: o bloco de proteção ([[ADR-240]]) entra no E5 por
`$ref`. Agravantes medidos:

- **A mesma chave tem duas unidades no bloco.** `tributario.cascata.triggers[].params.fator_r_pct`
  sai absoluto (`_pct_str` multiplica por 100), e `cards/CascataFiscalCard.triggers.ts`
  o formata, corretamente, sem compensar.
- **A [[ADR-236]] escreve o `fator_r_pct` com `× 100`**, que o produtor
  (`_compute_fator_r`) não aplica.
- **Dois textos afirmam a D1 sem exceção:** a R21 da persona (Camada 2), contrariada
  pela dica de proteção em `pipeline/llm/prompts/parecer_planejador.py`
  (`pct_renda_anual > 0.05`), e o COPY_GUIDELINES §4.6, segundo o qual os `*_pct`
  "já chegam absolutos".

Só o `pct_renda_anual` tem registro: o achado RV4-51 em
[PIPELINE-REVIEWS-active](../_MOC/PIPELINE-REVIEWS-active.md) (P3, `procede-aberto`,
trilha `data-engineer`). Migrar os produtores ou declarar exceção à D1 (na forma da
§D2) é decisão de quem tratar o RV4-51; esta emenda só registra a medida.

**Duas notas de cronologia.** O item da §Riscos nasceu sem objeto: o #246, que tirou
de `formatPercent` o `style: "percent"` (a multiplicação por 100), mergeou 3 h antes do
#245, que trouxe esta ADR. E o #2123 (2026-10-09) estendeu o formatador e o gate de
`toFixed(n)` colado ao `%` a `src/**`, fora do relatório.

## Referências

- Achado DE-I.2 — `docs/archive/PLANNER_REVIEW-2026-07-09.md` §Pré-requisitos bloqueantes
- Auditoria — `_scratch/pr2_pct_audit_20260513-1012.md`
- Pattern análogo — [[ADR-090]] (Money nunca é float)
- Methodology = code — [[ADR-143]]
- Schema E5 e additionalProperties — W6-T01 PLATFORM_REVIEW (PR-1, paralelo)
