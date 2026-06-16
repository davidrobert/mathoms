---
id: A26.l1
type: lane
title: "Fix de citação do evidencia_path — catálogo de paths disponíveis + eval golden LLM"
sprint: A26
plan: PLAN-data-lineage
status: planned
priority: P1
branch_slug: evidencia-prompt-catalogo
adrs:
  - "[[ADR-279]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/planned
  - priority/p1
  - area/data-lineage
  - area/llm
---

# A26.l1 — `evidencia-prompt-catalogo` (Regime A · sem gate · elegível fora da sprint)

> **Plano:** [[PLAN-data-lineage]] · carry-over de [[A25.l7]] (decisão do flip strict).
> **NÃO depende de tráfego** — corrige um bug de prompt que polui a própria métrica do
> gate de flip. Elegível para pickup imediato mesmo com a A26 `candidate`. Co-design
> `prompt-engineer` 2026-06-16.

## Problema (telemetria A25.l7)

Modo `warn`, `prompt_version` 1.5.0: taxa de violação de citação ~89% (n=3 dogfood).
**72% das falhas são conformidade de citação** — `resolve_null` (38%, path cita campo
ausente/nulo no payload do cliente) + `whitelist_miss` (34%, segmento raiz fora da
`section_whitelist` ou sintaxe JSONPath inválida). Só 19% é `value_mismatch` (alucinação
de valor). **Causa-raiz:** o LLM **não vê** a whitelist de paths citáveis — adivinha
paths plausíveis (`$.reserva.total` vs. o real `$.reserva_emergencia.total_liquida`).
Expandir a whitelist NÃO ajuda (o problema não é path legítimo recusado).

## Objetivo

Derrubar a conformidade de citação para o nível que viabilize o flip strict ([[A26.l2]]),
sem esperar tráfego, e instrumentar um eval golden que meça o gate de forma determinística.

## Escopo

1. **Diagnóstico (antes de corrigir):** dump dos paths citados nas 3 gerações dogfood;
   classificar cada `whitelist_miss` em (root-fora-da-whitelist / sintaxe-inválida /
   root-certo+leaf-errado). Decide se a correção é whitelist vs. catálogo. Registrar no PR.
2. **Catálogo de citação (maior alavanca, ~70% das falhas):** injetar no exec context do
   manifest um bloco `evidencia_paths_disponiveis` — os leafs monetários **presentes e
   não-nulos** do E5 daquele cliente, como lista fechada. O LLM cita de uma lista, não
   adivinha. Bump `version` do manifest (invalida cache Redis). Co-design
   `information-architect` se mexer na **forma** da DSL do manifest (conteúdo é desta lane).
3. **Prompt:** reforçar regra 11 — "cite EXCLUSIVAMENTE paths de `evidencia_paths_disponiveis`;
   campo ausente da lista → não cite valor, use `campos_faltantes_pediria_se_iterasse[]`".
   + 2-3 few-shot de citação correta (token R$ na prosa → leaf path exato). Bump
   `PROMPT_VERSION` 1.5.0→1.6.0; atualizar `_PROMPT_BASELINE_CHARS` no teste de budget.
4. **Eval golden do LLM** (`tests/test_parecer_evidencia_llm_eval.py`, `@pytest.mark.llm_eval`,
   fora do PR gate por custo+flakiness): 25 fixtures E5 PII-zero representativas (happy,
   sem-previdência, sem-imóvel, leaf-nulo, período `999999`, casal vs. solteiro),
   **15 tuning / 10 holdout**. Roda LLM real + verificador real, 3 runs por fixture, agrega
   **% pareceres com ≥1 violação** com banda (min/max/média), não ponto único.

## Critério de aceite

- Diagnóstico dos 3 dumps classificado (root/sintaxe/leaf) — decisão whitelist vs. catálogo no PR.
- Conformidade de citação ≥95% sobre as gerações disponíveis (KR1).
- Eval golden **holdout** (10 fixtures nunca-vistas no tuning): % pareceres com ≥1
  violação **<5%**, 3 runs cada, banda reportada. Anti-overfit: holdout separado do tuning.
- `tests/test_parecer_evidencia_path.py` verde (não-regressão do verificador determinístico).
- `PROMPT_VERSION` + `version` do manifest bumpados; teste de budget de token verde (se o
  catálogo + few-shot estourar >5%, é mudança consciente → re-baseline com justificativa).
- PII grep zero nas fixtures novas (`rg 'CPF|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}' tests/`).

## Notas

- O eval golden **antecipa** o gate; NÃO substitui o gate de produção da [[A26.l2]]
  (≥20 gerações reais). Documentar os dois papéis para não confundir o owner.
- `resolve_null` legítimo (cliente sem o campo) → o LLM **não deve citar valor**, não
  relaxar a camada para aceitar null (reabriria a porta da alucinação).

## Owner

Agente da lane; co-design `prompt-engineer` (estratégia) + `information-architect` (forma do manifest, se tocada).
