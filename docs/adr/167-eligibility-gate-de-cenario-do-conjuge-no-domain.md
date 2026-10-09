---
id: ADR-167
type: adr
title: "Eligibility gate de cenário do cônjuge no domain service"
status: Decidido
phase: "A8.4 PR2"
date: "2026-05-06"
amended_at: ["2026-10-09"]
relates_to: ["[[ADR-143]]", "[[ADR-166]]", "[[ADR-177]]", "[[ADR-387]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 167"]
tags:
  - area/backend
  - area/multitenancy
  - area/pipeline
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 125
---

# ADR-167 — Eligibility gate de cenário do cônjuge no domain service

> **Emenda 2026-10-09 (correção de implementação e de premissa):** o gate desta ADR
> nunca teve chamador em produção — `should_render_conjuge_scenarios` nasceu órfã no
> #81 e o E5 publicava o cenário para todo workspace com data de nascimento e meta IF,
> solteiro incluído. E o critério de renda media num sinal que não existe: o label de
> receita não carrega o membro. O gate passa a ser ligado pelo que o cadastro sabe;
> os critérios de renda ficam deferidos. Ver §Emenda 2026-10-09.

**Status:** Decidido (A8.4 PR2) • **Data:** 2026-05-06 • **Relaciona** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76), [ADR-166](#adr-166--schema-estável-cenarios_conjuge-no-payload-e5).

**Contexto:** O analyzer `cenarios_conjuge_analyzer.py` (PR2 reduz a 1 cenário "Sem renda do cônjuge") computa stress test de IF para casais com 2 rendas. Aplicar universalmente — para solteiros, casais com 1 renda, ou famílias onde cônjuge tem renda <15% — gera ruído: tabela com cenário irrelevante, narrativa LLM forçada, APP_C ocupando página em PDF premium sem servir o cliente. financial-planner (consultado em A8.4 / 2026-05-06) é taxativo: cenário é universal **conditionado**, não universal **obrigatório**.

**Decisão:** Função pura `should_render_conjuge_scenarios(family_members, fluxo, goals) -> bool` no domain service (`pipeline/domain/services/cenarios_conjuge_analyzer.py`) decide se o bloco entra no payload. Pipeline E5 omite o bloco quando `False`. Frontend só checa presença (`if (!data.cenarios_conjuge) return null`) — zero lógica de elegibilidade duplicada em TS (ADR-143 combate drift backend↔frontend).

**Critérios de elegibilidade (universal, Cerbasi/Perini, ≤20 linhas):**

```python
def should_render_conjuge_scenarios(*, family_members, fluxo, goals) -> bool:
    """ADR-167: cenário 'cônjuge sem trabalhar' é elegível?

    Critérios:
    - Meta IF presente (if_meta > 0)
    - ≥2 membros com renda recorrente
    - Renda do cônjuge ≥15% da renda familiar total

    Casos:
      Solteiro / 1 renda                → False (sem o que stressar)
      Casal sem meta IF                 → False (sem âncora de impacto)
      Casal 95/5 (cônjuge < 15%)         → False (impacto < ruído)
      Casal 70/30 + meta IF              → True
      Casal 60/40 + meta IF              → True
    """
```

**Alternativas avaliadas:**

- (a) Frontend decide (sempre recebe payload, oculta quando vazio) — duplica regra em TS; risco de drift que ADR-143 combate.
- (b) `section_summary_orchestrator` decide quais seções listar — orchestrator é seção-level, gate é chart-level; granularidade errada.
- (c) **Pipeline E5 emite ou omite** ✅ — uma camada decide; frontend confia no payload.

**Consequências:**

- ✅ Regra co-localizada com enforcer (ADR-143).
- ✅ APP_C dinâmico: workspace solteiro → APP_C ausente; workspace casal 70/30 → APP_C presente.
- ✅ Numeração estável A/B/C/D/E preservada — APP_C oculto não recompõe APP_D para "C" (D4 do plano A8.4).
- ⚠️ Mudança de elegibilidade entre ciclos do mesmo workspace (ex.: cônjuge passa a ter renda) muda payload — esperado e desejável; planner explica ao cliente.

**Critério de aceite (PR2):**

- 4 unit tests cobrindo: 1 renda, 2 rendas casal elegível, 2 rendas solteiro, casal sem renda do cônjuge.
- Workspace de teste com 1 renda → payload sem `cenarios_conjuge`.
- Workspace de teste com 2 rendas 70/30 + meta IF → payload com `cenarios_conjuge` (1 cenário).

**Follow-ups:**

1. Cenários adicionais (perda de renda do titular, aposentadoria antecipada) propostos pelo financial-planner — backlog futuro (A8.4 §8 backlog).

## Emenda 2026-10-09 — o gate é ligado pelo que o cadastro sabe; a divisão de renda é deferida

Lane [[A40.l125]]. Co-design: `financial-planner` (regra), `data-engineer` (contrato E5),
`product-designer` (front); desempate do card de aportes pelo `senior-cto`.

**Os fatos, medidos.**

1. `should_render_conjuge_scenarios` não tinha chamador fora do teste unitário. O
   `E5AnalyzerAdapter` calculava o cenário sempre que havia analyzer e projeção IF.
2. O gate atribuía renda por membro procurando o `nome_curto` como substring de
   `receita_datasets[].label`. Esse label é o **valor** de `pj_source_mapping` /
   `clt_source_mapping`, lido só do template global
   (`pipeline_adapter._categorization_override` → `get_categorization_metadata`, sem
   `workspace_id`) — não há mapeamento por workspace. Desde a A34.l11 (#890) o seed traz
   **papel** (`"(Cônjuge - CLT)"`), não nome, e não re-roda em DB existente. Ligado como
   estava, o gate devolveria `False` para todo casal fora de um DB legado.
3. Casar pela palavra de papel também não serve: receita CLT sem keyword cai no primeiro
   valor do mapping, `"(Cônjuge - CLT)"`, de quem quer que seja — o salário do titular
   viraria renda do cônjuge.
4. Os testes do gate usavam labels `"Receita CLT Alice"`, forma que o produtor nunca
   emitiu: a fixture fabricava a precondição do gate.

**Decisão.** `veredito_cenario_conjuge(conjuge_key, if_meta)` substitui a função
órfã e devolve `elegivel` / `sem_conjuge_cadastrado` / `sem_meta_if`; o adapter decide
antes de calcular e loga o veredito (`mathoms.pipeline.e5.cenario_conjuge`, com
`nao_avaliado` quando falta insumo).

- **(a) meta IF > 0** — mantido.
- **(b) ≥2 membros com renda** — reduzido à condição necessária que o cadastro prova:
  cônjuge declarado (`papel = conjuge`). Dependente adulto com renda não conta: papel
  não prova renda, e é outro cenário (follow-up 1 desta ADR).
- **(c) cônjuge ≥15% da renda** — deferido (abaixo).

Casal com divisão não mensurável fica **elegível** (fail-open). Esconder o stress test
de um casal 70/30 é pior que mostrar uma hipótese rotulada a um casal de uma renda, e
sem evidência positiva não se declara inaplicabilidade ([[ADR-387]] D3).

**Contrato.** "Omite o bloco" é `cenarios_conjuge: {}` — a forma que o produtor já
emitia e o schema já descrevia; omitir a chave criaria um terceiro estado para todo
leitor sem ganho. O front lê presença em **um** lugar (`readCenariosConjuge`, que trata
`{}` como ausência) para S3, APP_C e o card de aportes; o card de aportes decide "Meta
de aporte não configurada" pelo aporte declarado, não pela ausência do cenário. O
chart do cenário só existe nas narrativas quando o E5 publicou o cenário, e o
validador do E5.N o trata como opcional-mas-completo — exigido, ele reprovava o E5.N
de todo solteiro.

**Deferimentos datados — 2026-10-09.**

1. **Critérios de renda (b)/(c) e magnitude calibrada.** Dono: `financial-planner`
   (regra); posição no roadmap: `product-manager`. **Retomada:** existir um escritor de
   `protection_income_declarations` ([[ADR-387]]) — a tabela já guarda renda ativa
   líquida por membro e já entra no E5, mas hoje só tem leitor e export LGPD. O IRPF por
   declarante entra depois, como fonte `document_derived` da mesma tabela. Na retomada
   o fator 0,66 ([[ADR-177]]) vira fallback rotulado: com despesa constante,
   aporte de estresse / aporte = 1 − c/s, e num casal 70/30 poupando 20% o aporte fica
   negativo — o fator fixo é otimista justamente no caso elegível.
2. **Projeção do bloco no manifest do parecer.** `format: scalar` com `value_format:
   raw` imprime `: {}` para o inelegível (e `measure_block_coverage` o conta como
   `com_dado`). Conserto escopado: `key_value` com as folhas declaradas, que omite o bloco
   quando nada resolve (precedente `irpf_kpis`). Dono: `prompt-engineer`, com eval.
   **Retomada:** antes do primeiro workspace não-casal em produção.
3. **Suprimir o cenário sem aporte declarado** (4º veredito `sem_aporte_declarado`,
   proposto pelo `financial-planner` no #2171 e recusado lá por ser elegibilidade). Dono:
   `financial-planner`. **Retomada:** junto da [[A40.l126]], que desenha o caminho do
   casal; publicar a ausência do aporte como ausência é escopo do #2171.
