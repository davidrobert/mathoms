---
id: ADR-246
type: adr
title: "Dedup de imóveis co-declarados em IRPFs de titular + cônjuge no consolidador E1.5c"
status: Decidido
phase: A17.imovel-dedup
date: "2026-05-21"
relates_to:
  - "[[ADR-215]]"
  - "[[ADR-225]]"
  - "[[ADR-235]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 246"
  - "Imóvel co-declarado dedup"
tags:
  - area/pipeline
  - area/methodology
  - status/decidido
  - type/adr
---

# ADR-246 — Dedup de imóveis co-declarados em IRPFs de titular + cônjuge

**Status:** Decidido • **Data:** 2026-05-21 • **Relaciona** [[ADR-215]] (PropertyIdentity), [[ADR-225]] (dedup cascade canonical), [[ADR-235]] (nu-proprietário invariante)

## Contexto

Bug reportado em prod no relatório `/reports/<id>`, seção "Top 15 Ativos Financeiros": o mesmo apartamento (matrícula 453.527, COND. EXEMPLO B) aparece duplicado — uma vez como pertencente ao titular (R$ 477.436,58), outra como pertencente ao cônjuge (R$ 530.000,00). É o mesmo imóvel físico, declarado nos dois IRPFs individuais (típico em comunhão parcial de bens — regime padrão BR).

Cadeia técnica:

1. `scripts/e15_consolidate.py:consolidate_from_itens` ([linha 408-446](../../scripts/consolidate_baseline.py)) itera `itens[]` (1 entrada por linha de IRPF unificado) e faz `imoveis_consolidados.append(entry)` **sem dedup por `(codigo_rfb, endereco_canonical)`**. Duas entradas distintas no baseline.

2. `pipeline/domain/services/property_identity_enricher.py` anexa `property_id`. `DBPropertyIdentityResolver.match_or_create` ([backend/app/services/db_property_identity_resolver.py:31](../../backend/app/services/db_property_identity_resolver.py)) faz cascade `(codigo_rfb, endereco_canonical)` ignorando `titular_key` ([[ADR-225]]) — então ambas as entradas recebem o **mesmo `property_id`**. Mas a lista continua com 2 itens.

3. `pipeline/domain/services/e5_member_resolver.py:_split_by_conjuge` distribui pelos cônjuges baseado em `proprietario` singular. Cada um vê "seu" imóvel.

4. `TopAtivosAnalyzer._collect_candidates` itera member-a-member e concatena — duplicação visível no top.

**Impactos:**
- Top 15 mostra duplicata visível.
- Patrimônio total **inflado** pelo `min(valor_david, valor_mariana)` (R$ 477k somado a R$ 530k = R$ 1.007k para o mesmo imóvel).
- Alocação-alvo AUVP deslocada (denominador inflado → alvos imobiliários "ocupados" indevidamente, sistema recomenda **menos** imóvel).
- `real_estate_e5_integration` ([backend/app/services/real_estate_e5_integration.py](../../backend/app/services/real_estate_e5_integration.py)) já agrega corretamente via `property_id` (single id, mesmo com duplicata na lista) — não é afetado.

## Decisão

Introduzir **dedup determinístico em `imoveis_consolidados`** no estágio E1.5c (`consolidate_from_itens` + função legada `consolidate`) e como defesa em `e4_categorize.py` (caminho onde E4 lê baseline antigo sem re-rodar E1.5c).

### Regra de identidade

Chave de identidade (herda [[ADR-225]]):

```
PRIMÁRIA:    property_id (quando enricher já rodou)
FALLBACK:    (codigo_rfb_strip, endereco_canonical)  — ambos não-vazios
```

Quando nenhuma chave é resolvível (`property_id is None` E `endereco_canonical is None` E `codigo_rfb` vazio), **não deduplicar** — registrar warning estruturado e deixar passar. Falso-positivo de merge (imóveis distintos colapsados) é pior que falso-negativo (duplicata visível).

### Regra de reconciliação de valor (resposta à pergunta de domínio do financial-planner)

Quando o mesmo imóvel aparece em N entries:

| Cenário | Resultado |
|---------|-----------|
| Só 1 declarante | preserva entry literal — `proprietario` = membro declarante. **Não inferir 50/50 sem evidência.** |
| 2+ declarantes, mesmo `valores_31_12[ano]` | merge: `proprietario = "casal"`, `proprietarios = [titular_key, conjuge_key]` ordenados |
| 2+ declarantes, valores divergem ≤10% | **maior valor vence**. Tie-break: ano mais recente; depois titular. Warning informativo |
| 2+ declarantes, valores divergem >10% | **maior valor vence** + flag `_dedup_warning: "valor_divergente"` na entry + log estruturado `consolidate.imoveis_dedup_warning` |

**Justificativa do "maior valor vence" sob Perini/Cerbasi/AUVP:**

- Cônjuge que declarou maior valor refletiu correção/atualização (valor de aquisição vs. mercado).
- Menor tende a ser histórico de aquisição ("valor pago") que o outro IRPF nunca atualizou.
- Consistente com [[ADR-235]] (nu-proprietário): valor IRPF é piso conservador; valor real pode ser maior.
- Soma é **proibida** — é o mesmo imóvel; somar produz patrimônio fantasma e desloca alocação-alvo.

### Schema

Aditivo em `config/schemas/baseline_patrimonial.schema.json`:

```json
"proprietarios": {
  "type": "array",
  "items": {"type": "string"},
  "description": "Lista de titular_keys quando imóvel é co-declarado. Quando ausente, default é [proprietario]."
}
```

`proprietario` singular **preservado** para compat downstream. Quando co-declarado, `proprietario = "casal"` e `proprietarios = [...]` lista ordenada.

### Regime de bens

**NÃO** introduzir campo de regime de bens no `family_members`. Default BR é comunhão parcial (70%+ dos casamentos pós-1977). Casos atípicos (separação total) detectáveis por sinal indireto: cônjuges declaram patrimônios disjuntos (nenhum imóvel duplicado) — neste caso, o dedup não é acionado e cada um mantém o seu.

Caso real de cliente reclamar do agrupamento, abrir ADR sucessora introduzindo `family_member.extra.regime_bens` + UI de marcação manual via `WorkspacePropertyOverride.classification`. YAGNI até lá.

### Camada de defesa em profundidade

`TopAtivosAnalyzer._collect_candidates` ([pipeline/domain/services/top_ativos_analyzer.py:110](../../pipeline/domain/services/top_ativos_analyzer.py)) também deduplica por `property_id` (safety net). Sem mudar invariante de domínio — só dedup pós-coleta.

## Consequências

**Positivas:**
- Patrimônio total não infla mais (testável: snapshot pré/pós-fix, `total_ativos` cai pelo `min(valor)` do imóvel co-declarado).
- Top 15 mostra cada imóvel **uma única vez** com `membro = "Casal"` (label preservado em downstream UI).
- Override `WorkspacePropertyOverride` (residência principal, classificação) continua sticky pós-dedup — `property_id` único.
- Alocação-alvo AUVP corrige denominador.

**Negativas / trade-offs aceitos:**
- Valor patrimonial single-source de verdade quando IRPFs divergem (escolha = maior); auditável via `_dedup_warning` flag e log estruturado.
- Workspaces existentes com baseline já duplicado precisam re-rodar E1.5c para sanar. Sem migration destrutiva; incremental engine cobre.
- Adição de campo `proprietarios` cria contrato implícito que outros consumers (futuros) precisam respeitar.

## Observabilidade

- Log estruturado `consolidate.imoveis_dedup`:
  ```json
  {
    "stage": "E1.5c",
    "count_before": 7,
    "count_after": 5,
    "dropped_property_ids": ["uuid-a", "uuid-b"],
    "warnings": [{"property_id": "uuid-a", "type": "valor_divergente", "values": [477436.58, 530000.00], "diff_pct": 11.0}]
  }
  ```
- Entry com merge marca `_dedup_warning` quando divergência >10% — sobrevive como flag in-payload (consumível por audit dashboard).

## Critério de aceite

1. Workspace David + Mariana → 1 row em `imoveis_consolidados` por imóvel co-declarado, `valor_31_12 = 530000` (maior), `proprietarios = ["david_robert", "mariana_xxx"]`, `proprietario = "casal"`.
2. Top 15 mostra imóvel uma vez com `membro = "Casal"`.
3. Workspace com 1 imóvel só do titular → continua aparecendo apenas no titular, `proprietario = titular_key` literal (não muda para "casal").
4. PL consolidado snapshot pré/pós: `total_ativos` cai por `min(valor_co_declarados)`.
5. `WorkspacePropertyOverride.residencia_principal=True` continua filtrando o imóvel co-declarado do Top 15 (single property_id).
6. Tests: golden 2-IRPFs/1-imóvel em `tests/test_e15_consolidate_dedup.py`, regression em `tests/unit/pipeline/test_e5_member_resolver.py`, integration em `backend/tests/integration/test_pipeline_cross_run_baseline.py`.
7. Schema: `config/schemas/baseline_patrimonial.schema.json` aceita `proprietarios` opcional.
8. `_dedup_warning` flag presente em entry com divergência >10% e ausente quando ≤10%.
9. Logs estruturados emitidos com counts antes/depois.

## Alternativas consideradas

- **Dedup em `enrich_imoveis_with_property_ids`** (anexar property_id E remover duplicatas): mistura responsabilidades (enrichment vs. dedup). Rejeitado.
- **Dedup em `e5_member_resolver._split_by_conjuge`**: tarde demais — `total_bens` e demais agregadores já leram lista duplicada upstream. Rejeitado.
- **Soma de valores com divisão 50/50** (regime comunhão parcial): introduz invariante de "regime de bens" sem suporte de configuração, e diverge da declaração literal IRPF. Rejeitado por YAGNI + acurácia.
- **Manter duplicata e marcar "co-propriedade" só na UI**: corrige sintoma visual mas mantém PL inflado, alocação-alvo deslocada e demais agregadores enganados. Rejeitado.

## Próximos passos

- PR1 (este escopo): helper `pipeline/domain/services/imoveis_dedup.py` + aplicação em `scripts/e15_consolidate.py` × 2 funções + `scripts/e4_categorize.py` + schema bump + testes.
- PR2 (defesa em profundidade): `TopAtivosAnalyzer` dedup por `property_id` em `_collect_candidates`.
- PR3 (UX cosmético, paralelo): renomeação "Top 15 Ativos Financeiros" → "Top 15 Ativos da Carteira" com subtítulo/tooltip explicando exclusão de residência.
- Follow-up tracked: dedup cross-IRPF de **investimentos** (conta conjunta declarada em ambos IRPFs) — escopo separado, exige chave `(codigo_rfb, banco, agência, conta)` que não existe no schema atual.
