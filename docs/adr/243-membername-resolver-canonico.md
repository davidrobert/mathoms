---
id: ADR-243
type: adr
title: "MemberNameResolver — normalizar `membro` extraído pelo LLM em chave canônica do workspace"
status: Proposto
phase: A17.incremental-correctness
date: "2026-05-21"
relates_to:
  - "[[ADR-127]]"
  - "[[ADR-137]]"
  - "[[ADR-226]]"
  - "[[ADR-241]]"
  - "[[ADR-242]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 243"
  - "MemberNameResolver"
tags:
  - area/pipeline
  - area/llm
  - status/proposto
  - type/adr
size_lines: 132
---

# ADR-243 — MemberNameResolver canônico

**Status:** Proposto • **Data:** 2026-05-21 • **Relaciona** [[ADR-127]] (family_members), [[ADR-137]] (family DB), [[ADR-226]] (AccountResolver), [[ADR-241]] (E2 workspace-scoped), [[ADR-242]] (LLM category hint)

## Contexto

`extract_with_llm` permite o LLM emitir `member_key` por transação/investimento no E2-llm. O modelo tende a inventar variações que não casam com a chave canônica do workspace (`family_members.key`):

- Workspace `Campos` tem `titular_key = "david_robert_camargo_ferreira_campos"` (key derivada do `full_name`).
- Informe IR Itaú extraído pelo LLM produziu `membro="david_robert_camargo_de_campos"` (slugificou o `nome_nascimento` — outro nome legal).
- Extrato Binance extraído pelo LLM produziu `membro="david_robert"` (slug do `short_name`).
- Nenhum dos dois bate em `titular_key`.

Consequência observada (workspace `Campos`, run `c36c4baf-…`):

- [`InvestmentsConsolidator.consolidate`](../../pipeline/domain/services/investments_consolidator.py:124) faz dedup por `(instituicao, membro)` e calcula `total_por_membro`. As 4 posições do informe IR Itaú (R$ 290k CDB + outros) ficaram sob `"david_robert_camargo_de_campos"`; as 8 do Binance sob `"david_robert"`. Nenhum agrega no `titular_key` canônico.
- [`analyze_patrimonio`](../../scripts/e5_analyze.py:989) em E5 lê `totais.get(_TITULAR_KEY, 0)` — recebe 0 quando totais tem chaves variantes. Card "Investimentos David Robert" mostrou R$ 317,24 (acidentalmente capturou o Binance sob algum match parcial) em vez de R$ 700k+ esperado.

Já existe [[ADR-226]] `AccountResolver` que resolve `(banco, conta_numero) → member_key`. **Não cobre** o caso do informe IR, que traz **nome** mas não conta. Falta um resolver simétrico para nome.

## Decisão

### D1. Novo service `pipeline/domain/services/member_name_resolver.py`

`MemberNameResolver(members: Iterable[MemberRecord])` resolve `name_raw → MemberNameResolution(canonical_key, confidence, matched_via)`. Stateless após construção; recicle entre chamadas.

Estratégias em ordem de precedência:

1. **`exact`** — slug do raw bate exatamente com `family_members.key`.
2. **`full_name`** — slug do raw bate exatamente com `full_name` slugificado.
3. **`short_name`** — idem com `short_name` (ex.: `"David Robert"`).
4. **`nome_nascimento`** — idem com `extra.nome_nascimento` (cobre o caso real do informe Itaú).
5. **`substring`** — raw é substring (≥5 chars) de algum slug canônico OU vice-versa, com candidato único.
6. **`ambiguous`** — substring bate em 2+ candidatos.
7. **`unknown`** — nada bateu (raw vazio, fora do roster).

Filtro `_MIN_SUBSTRING_LEN=5` evita falso-positivo de `"ana"` matchando `"fernanda"`.

### D2. Pontos de aplicação

**Camada 1 (fonte) — [extract_with_llm.py](../../pipeline/stages/extract_with_llm.py):** normaliza `member_key`/`membro` no momento de escrever o E2-llm. Resolver construído uma vez por run via `MemberNameResolver.from_family_config(ctx.load_config("family_members.json"))` e injetado em `_process_one_e2_llm_document`.

**Camada 2 (defensive) — [InvestmentsConsolidator](../../pipeline/domain/services/investments_consolidator.py):** segunda passada para artifacts carry-forwarded de runs pré-ADR-243 ([[ADR-241]] preserva E2 antigos via workspace-scoped). Resolver vive em `InvestmentsConsolidatorConfig.member_name_resolver`; `from_family` constrói automaticamente.

Quando o resolver não casa (confidence=`unknown`/`ambiguous`), preserva o raw — não inventa canonical. Telemetria + downstream `AccountResolver` ainda têm chance de resolver via banco+conta.

### D3. Telemetria estruturada

Cada chamada emite log `mathoms.pipeline.member_name_resolver.resolved` com fields `confidence`, `canonical_key`, `matched_via`. Permite medir em produção:

- Share de `exact` vs. fallbacks (qualidade do prompt LLM).
- Volume de `ambiguous`/`unknown` (drift do vocabulário do LLM).
- Drift incremental: se workspace produz muito `substring` em vez de `exact`, prompt precisa reforço.

## Alternativas consideradas

- **(a) Resolver via prompt do LLM com enum estrito de keys.** Passar `family_members.keys` no system prompt forçaria o LLM a usar a key canônica. Rejeitada por enquanto: muda contrato com o LLM (caro de testar regressão), e o resolver é necessário de qualquer forma para artifacts antigos. Pode virar follow-up (D5 do enum estrito de `categoria_sugerida` em [[ADR-242]]).
- **(b) Match fuzzy com Levenshtein/RapidFuzz.** Mais robusto a typos, mas adiciona dependência opcional + sensibilidade a tuning de threshold. Rejeitada para esta lane — substring + exact match cobrem 100% dos casos observados. Follow-up se telemetria mostrar `unknown` alto.
- **(c) Esconder o problema sob o `AccountResolver` (ADR-226).** Account resolver precisa de `(banco, numero_conta)`. Informe rendimento traz nome sem conta — não tem como aplicar account resolver. Cobertura insuficiente.

## Consequências

- ✅ **Fix observado**: informe rendimento Itaú resolve `"david_robert_camargo_de_campos"` (via `nome_nascimento`) → `"david_robert_camargo_ferreira_campos"` canônica. Posições do CDB R$ 290k agregam corretamente em `total_por_membro["titular_key"]`.
- ✅ **Atribuição por membro correta** em S2/S3/S5: cards "Investimentos David", "Cenários do cônjuge", split de receitas/despesas por pessoa, todos passam a usar a chave canônica.
- ✅ **Defesa em camadas**: normaliza no E2-llm (fonte) E no InvestmentsConsolidator (consumer). Artifacts E2 carry-forwarded de runs antigas (pré-ADR-243) também são corrigidos no consume.
- ✅ **Telemetria observável**: log estruturado mostra eficácia do resolver. Sem `unknown`/`ambiguous` em produção → vocabulário estável; alto → drift do LLM ou família sub-especificada.
- ⚠️ **Substring match pode dar falso-positivo** em famílias com nomes muito similares (gêmeos com mesmo sobrenome). Hoje aceitável — observa `ambiguous` para detecção; threshold pode subir se virar problema.
- ⚠️ **Resolver constrói por run** (snapshot do family_members no momento). Se família muda no meio de um run (caso raro), a normalização usa o snapshot inicial — coerente.

## Gates de regressão

- **T1** — `tests/unit/pipeline/test_member_name_resolver.py` (19 testes): cobre as 7 confidences, ambiguidade, vocabulário real do LLM, telemetria estruturada, casos de borda.
- **T2** — Manual/dogfood: regerar o relatório real (workspace `Campos`, run sobre dezembro/2025) e validar que `investimentos.total_por_membro` agrega corretamente sob `david_robert_camargo_ferreira_campos`.

## Follow-ups

1. **Enum estrito do `member_key` no Pydantic do LLM output**, alinhado com [[ADR-242]] D5: passar lista de keys do workspace no schema (`Literal[...]`). Reduz dependência do resolver para casos novos; preserva o resolver como defensive layer para artifacts antigos.
2. **Match fuzzy (RapidFuzz/Levenshtein)** se telemetria mostrar muitos `unknown` por typo do LLM (ex.: `"david robret"`).
3. **Aplicar resolver em outros call-sites** que ainda comparam `membro` directly (search por `data.get("membro")` em `pipeline/` revela ~6 outros pontos). Lane separada para evitar inflar este PR.
