---
id: ADR-271
type: adr
title: "Dedup de investimentos cross-IRPF (cross-year + cross-declarante) no consolidador E1.5c"
status: Proposto
phase: A17.invest-dedup
date: "2026-05-29"
relates_to:
  - "[[ADR-246]]"
  - "[[ADR-265]]"
  - "[[ADR-267]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 271"
  - "Investimento cross-IRPF dedup"
tags:
  - area/pipeline
  - area/methodology
  - status/proposto
  - type/adr
---

# ADR-271 — Dedup de investimentos cross-IRPF (cross-year + cross-declarante)

**Status:** Proposto • **Data:** 2026-05-29 • **Relaciona** [[ADR-246]] (dedup imóveis — precedente direto, regra de valor divergente), [[ADR-265]] (fuzzy canonical), [[ADR-267]] (identidade de membro por CPF — pré-requisito)

## Contexto

Quando o usuário sobe IRPFs de **anos diferentes** (ex.: 2023 + 2024) e/ou de **cônjuges** (titular + cônjuge), os investimentos aparecem **duplicados** em `baseline["investimentos_consolidados"]`, inflando o patrimônio líquido e deslocando a alocação-alvo AUVP (denominador inflado → sistema recomenda aportes errados).

[[ADR-246]] resolveu o mesmo problema para **imóveis** (dedup por `property_id`/`codigo_rfb`+`endereco_canonical`, regra "maior valor vence") e deixou investimentos como follow-up explícito — exige chave que não existia no schema.

Cadeia técnica:

1. `scripts/e15_consolidate.py` constrói `investimentos_consolidados` em duas funções: `consolidate` ([linha ~283](../../scripts/e15_consolidate.py)) e `consolidate_from_itens` ([linha ~499](../../scripts/e15_consolidate.py)). Ambas fazem `append(entry)` **sem dedup**.
2. Cada entry é `{descricao, tipo, proprietario, valores_31_12: {ano: valor}, instituicao?}`. **Não há identidade estável** — sem CNPJ, sem banco/agência/conta, sem código RFB. Só descrição textual + instituição opcional.
3. Consumidores (`scripts/e4_categorize.py`, `scripts/e5_analyze.py`, `TopAtivosAnalyzer`) leem a lista duplicada e somam.

**Diferença crítica vs. imóveis:** imóvel no IRPF é piso histórico de aquisição (raramente atualizado → "maior valor vence" faz sentido). Investimento é **marcado a saldo/mercado todo 31/12** → o valor do IRPF mais recente é a verdade corrente; usar o maior corromperia o rebalanceamento AUVP por aporte.

## Decisão

Dedup determinístico em `investimentos_consolidados` no estágio E1.5c (ambas as funções) + defesa em profundidade em `e4_categorize.py`. **Chave exata apenas** nesta ADR; pass fuzzy fica como follow-up (PR2, ver Próximos passos).

### Identidade

Chave de identidade do **ativo** (agnóstica a ano e a proprietário, para colapsar ambos os eixos no mesmo grupo):

```
INVESTMENT_KEY = (tipo_norm, instituicao_norm, descricao_norm)
investment_id  = hash estável de INVESTMENT_KEY
```

`descricao_norm` = lower + strip acento + colapsa espaço + remove sufixo numérico de conta/agência. Itens sem `descricao_norm` **e** sem `tipo` → `unidentified`, **passam intactos** (nunca fundem).

### Regra de reconciliação — dois eixos

Dentro de cada grupo `INVESTMENT_KEY`, sub-agrupa por `proprietario`:

**Eixo 1 — Cross-year (mesmo proprietário, anos sucessivos):**

| Cenário | Resultado |
|---------|-----------|
| Mesma chave, anos distintos | **merge: une `valores_31_12`** (ano novo não sobrescreve ano velho — preserva série temporal) |
| Conflito no **mesmo** ano (raro) | **maior valor vence** + `_dedup_warning: "valor_divergente_ano"` |

Valor corrente do PL = `valores_31_12[max(ano)]`. **Não somar anos.** Ativo presente em ano antigo e ausente no ano mais recente permanece na série (`valores_31_12` histórico) mas não conta no total corrente.

**Eixo 2 — Cross-declarante (proprietários distintos, mesmo ativo):**

| Cenário | Resultado |
|---------|-----------|
| Valores 31/12 **idênticos ao centavo** (overlap de ano) | **conta-conjunta → funde uma vez.** `proprietario = "casal"`, `proprietarios = [cpf_a, cpf_b]` ordenados, valor **não somado** |
| Valores **divergentes** | **NÃO funde** — posições individuais homônimas. Cada um mantém a sua. Opcional `_dedup_warning: "possivel_duplicata"` p/ auditoria visual |

**Discriminante "idêntico ao centavo":** conta conjunta é o **mesmo saldo** declarado 2×; duas poupanças/contas individuais batendo no mesmo centavo é estatisticamente improvável. É o sinal forte que substitui a âncora RFB que imóveis têm. Caixa (conta-corrente/poupança) entra no **mesmo motor** — caixa de cada cônjuge é tipicamente separado, então a exigência de valor idêntico já protege contra falso-merge.

### Calibração: falso-positivo > falso-negativo

Fundir ativos distintos **some** patrimônio real (silencioso, mina confiança); deixar duplicata **infla** PL (visível, auditável). Na dúvida, **não funde**. Por isso: chave exata (sem fuzzy nesta ADR), e cross-declarante exige valor idêntico.

### Schema

Aditivo/retrocompatível em `config/schemas/baseline_patrimonial.schema.json` › `investimentos_consolidados.items`:

```json
"instituicao": {"type": "string"},
"proprietarios": {"type": "array", "items": {"type": "string"},
  "description": "União de declarantes quando investimento é co-declarado (ADR-271). Default [proprietario]."},
"investment_id": {"type": ["string", "null"],
  "description": "Hash estável de (tipo|instituicao|descricao_norm). Identidade de dedup, não FK."},
"_dedup_warning": {"type": "object",
  "description": "Divergência de valor no mesmo ano ou possível duplicata co-declarada (ADR-271)."}
```

`proprietario` singular **preservado** para compat downstream; co-declarado → `proprietario = "casal"`.

## Consequências

**Positivas:**
- PL não infla mais por investimento duplicado (cross-year e conta-conjunta).
- `valores_31_12` multi-ano vira série temporal legítima (evolução patrimonial).
- Consistência com [[ADR-246]] — onboarding zero (mesmo `DedupResult`/`DedupWarning`).

**Negativas / trade-offs aceitos:**
- `investment_id` é hash de campos textuais → **não estável a rename de descrição** entre anos. Banco mudou o texto → item duplica. Mitigado por `descricao_norm`; resolução forte (CNPJ) fica como follow-up.
- Reclassificação de `tipo` entre anos (fundo→FII pós-reorg) quebra a chave → duplicata visível (falso-negativo aceito; é o lado seguro).
- Conta-conjunta com declaração **assimétrica** (um cônjuge 100%, outro 0%) não funde (valores ≠). Aceito: PL levemente inflado + flag > patrimônio sumido.
- Baselines existentes precisam re-rodar E1.5c. Sem migration destrutiva (payload JSON em `pipeline_artifacts`); incremental engine cobre. Defesa E4 limpa no caminho de leitura enquanto isso.

## Observabilidade

Log estruturado `consolidate.investimentos_dedup`:

```json
{"stage": "E1.5c", "count_before": 12, "count_after": 9,
 "dropped_keys": ["hash-a", "hash-b"],
 "warnings": [{"investment_id": "hash-c", "type": "valor_divergente_ano", "values": [10000.0, 10500.0], "diff_pct": 5.0}]}
```

## Critério de aceite

1. Workspace com IRPF 2023+2024 do mesmo membro, mesma carteira → **1 entry** com `valores_31_12 = {"2023": x, "2024": y}`; PL corrente usa `y`.
2. Conta conjunta declarada por David + Mariana com **valor idêntico** → 1 entry, `proprietario = "casal"`, `proprietarios = [...]`, valor **não somado**.
3. Poupança homônima de 2 cônjuges com **valores diferentes** → **2 entries** preservadas (não funde).
4. Item sem `instituicao` e descrição genérica isolada → passa intacto (`unidentified`).
5. `total_ativos` snapshot pré/pós: cai pelo valor do duplicado removido.
6. Idempotência: re-rodar dedup sobre saída já deduplicada = no-op.
7. Schema aceita `instituicao`/`proprietarios`/`investment_id`/`_dedup_warning` opcionais.
8. Logs estruturados com counts antes/depois.
9. Tests: golden cross-year + golden cross-declarante (idêntico e divergente) + idempotência + regressão E5.

## Alternativas consideradas

- **"Maior valor vence" (como imóveis):** rejeitado — investimento é marcado a mercado; o maior pode ser valor antigo de ativo que caiu, corrompendo alocação-alvo.
- **Fundir cross-declarante por nome+instituição (sem exigir valor idêntico):** rejeitado — falso-positivo provável com descrições genéricas ("Tesouro Selic", "Poupança"); some patrimônio real.
- **Resolver com persistência (análogo a `PropertyIdentityResolver`):** rejeitado — investimento não tem âncora RFB estável; persistir identidade fuzzy-derivada é gravar palpite (over-engineering + drift).
- **Estender extrator LLM E1.5 p/ capturar CNPJ:** adiado — frágil (nem todo bem-direito lista CNPJ legível) + nova superfície de eval LLM. Vira follow-up.

## Próximos passos

- **PR1 (este escopo):** helper `pipeline/domain/services/investimentos_dedup.py` (chave exata, ambos os eixos) + aplicação nas 2 funções de `e15_consolidate.py` + defesa em `e4_categorize.py` + schema bump + goldens.
- **PR2 (follow-up, fuzzy):** pass fuzzy **gated por instituição idêntica** (reusa `canonical_fuzzy_match`), atrás dos goldens do PR1 como rede de regressão + goldens negativos ("não fundir Selic-marido com Selic-esposa").
- **PR3 (follow-up, identidade forte):** extração de CNPJ/conta no E1.5 como chave estável a rename.
