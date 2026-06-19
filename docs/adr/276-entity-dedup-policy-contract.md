---
id: ADR-276
type: adr
title: "EntityDedupPolicy: contrato comum de dedup de entidades patrimoniais no E1.5c"
status: Decidido
phase: A21.l3
date: "2026-05-30"
relates_to:
  - "[[ADR-246]]"
  - "[[ADR-265]]"
  - "[[ADR-271]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 276"
  - "EntityDedupPolicy"
tags:
  - area/pipeline
  - status/decidido
  - type/adr
---

# ADR-276 — EntityDedupPolicy: contrato comum de dedup de entidades patrimoniais

**Status:** Decidido (Sprint A21, lane l3) • **Data:** 2026-05-30 • **Relaciona** [[ADR-246]] (dedup imóveis), [[ADR-265]] (fuzzy canonical), [[ADR-271]] (dedup investimentos)

## Contexto

`E1.5c` roda dois serviços de dedup independentes sobre o baseline consolidado:

- `pipeline/domain/services/imoveis_dedup.py` (387 linhas, [[ADR-246]]/[[ADR-265]]) — chave `property_id` ou `(codigo_rfb, endereco_canonical)`, fase de re-agrupamento cross-código + fuzzy via/número, merge "maior-valor-vence", co-declaração → `"casal"`, warning `valor_divergente` quando valores divergem >10%.
- `pipeline/domain/services/investimentos_dedup.py` (264 linhas, [[ADR-271]]) — chave exata `(tipo, instituicao_norm, descricao_norm)`, merge cross-year por dono (une `valores_31_12`, marca-a-mercado), cross-declarante (funde só se valor idêntico ao centavo → `"casal"`; senão emite N entries `possivel_duplicata` sem fundir).

Os dois compartilham um **esqueleto** (agrupar por identidade → processar grupos → emitir → montar resultado tipado → log estruturado) mas têm **estratégias de merge estruturalmente diferentes** (e, no eixo de divergência de valor entre donos, **opostas**: imóveis sempre funde + warna; investimentos splita). Hoje o esqueleto está **duplicado** nos dois arquivos (`_group_by_identity`, `_emit_group`, `_log_if_deduped`, dataclasses de resultado quase idênticas). A lane A21.l4 (previdência) adicionaria uma **3ª** cópia.

A lane l3 ([[PLAN-launch-trust]] §F1-O2) pede unificar o esqueleto sem mudar comportamento, agora que a rede de segurança existe: invariantes INV-1..8 (l1) + métricas `fn_rate`/`fp_rate` sobre golden zero-PII (l2, mergeada PR #533).

## Decisão

Extrair o **esqueleto comum** para `pipeline/domain/services/entity_dedup.py` e reescrever os dois serviços como **policies**. Rejeitado o sketch original §F1-O2 (Protocol "gordo" com `merge_cross_year`/`is_joint`/`tie_break_winner`/`divergence_warning`) — força no-ops em metade das policies (viola ISP, [[ADR-089]]/[[ADR-097]]) e cria **caminhos mortos por design** num invariante crítico (`fp_rate = 0` red line).

### Contrato — Protocol de 3 membros

```python
GroupedEntries = list[tuple[tuple, list[dict]]]  # (identity_key, entries), ordenado

@dataclass(frozen=True)
class DedupWarning:
    entity_id: str | None
    type: str
    values: tuple[float, ...]
    diff_pct: float

@dataclass(frozen=True)
class DedupOutcome:
    items: list[dict]
    warnings: tuple[DedupWarning, ...]
    count_before: int
    count_after: int
    dropped_ids: tuple[str, ...]

class EntityDedupPolicy(Protocol):
    def identity_key(self, entry: dict) -> tuple | None: ...
    def remap_groups(self, grouped: GroupedEntries) -> GroupedEntries: ...
    def emit_group(
        self, group: list[dict]
    ) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]: ...

def run_entity_dedup(items, policy) -> DedupOutcome: ...
```

Decisões de forma que viram **contrato testável** (não convenção):

1. **`remap_groups` é total, não opcional.** A policy de investimentos retorna o grupo intacto (`return grouped`); a de imóveis executa cross-código + fuzzy. Identidade explícita > hook opcional com `if hasattr` — mantém o runner linear, sem ramo morto, e o diff declara "este domínio não reagrupa".
2. **Ordem de iteração é parte do invariante.** O runner preserva insertion-order de `_group_by_identity` (mesma ordem que hoje). `tie_break_winner` de imóveis e a reindexação cross-código são sensíveis à ordem de visitação — trocar `dict` por `sorted`/`set` poderia manter `fn`/`fp` verde e flipar um empate em produção. O runner **não reordena**; testado explicitamente.
3. **Warnings ficam no eixo da policy.** `emit_group` devolve `(entries, warnings, dropped_ids)`; o runner só concatena. Investimentos embute `_dedup_warning` **no entry** emitido; imóveis idem no winner. O runner **não re-injeta** warning em lugar nenhum — senão mudaria o shape do JSON E5 silenciosamente. (Extensão da 2-tupla `(entries, warnings)` para 3-tupla porque `dropped_ids` tem semântica por-domínio — `investment_id` repetido vs. `property_id` — que o runner não pode inferir de forma genérica.)

### Compatibilidade de API preservada

As funções públicas `dedup_imoveis_consolidados(...)` / `dedup_investimentos_consolidados(...)` e os tipos de retorno `DedupResult` / `InvestDedupResult` **permanecem** como wrappers finos que chamam `run_entity_dedup` e mapeiam `DedupOutcome` → o dataclass legado. Os call-sites em `e15_consolidate.py` (`.imoveis`/`.investimentos`, `.count_before/after`, `len(.warnings)`) e os 42 unit tests existentes **não mudam**. Os helpers de domínio (`_merge_cross_year`, `_is_joint_account`, `_winner_sort_key`, `matches_fuzzy`, cross-código…) permanecem privados nos módulos e são chamados de dentro de `emit_group`/`remap_groups`.

### Escopo — fora do contrato

Filtro PF×PJ ([[ADR-268]], `detect_pj_suffix`) **não** entra no contrato — vive antes, no `consolidate_from_itens` (INV-9, l1). O runner recebe só posições PF.

## Gate de merge

Refactor de invariante `fp_rate = 0` exige **diferencial, não só verde**. INV-1..8 + golden provam ausência de regressão *conhecida*; `fn`/`fp` são métricas lossy (um swap de `"casal"` por split idêntico-ao-centavo pode preservar a métrica e corromper o payload). Antes do merge:

1. Snapshot frozen do output **atual** (pré-refactor) de ambos os serviços sobre um corpus que exercita todo caminho → assert byte-a-byte (`json` sort_keys) pós-refactor.
2. 17 unit tests investimentos + 25 unit tests imóveis **verdes sem alteração**.
3. INV-1..8 (l1) + `fn_rate`/`fp_rate` (l2) verdes; **zero mudança** vs. baseline.

## Consequências

**Positivas:** esqueleto group/iterate/assemble/log testado uma vez; `DedupOutcome` unificado; l4 (previdência) entra como 3ª `emit_group` (regra dos 3×), não como cópia do esqueleto. Cada serviço encolhe honestamente (orquestração → runner), mantendo internals de merge intactos = risco mínimo ao invariante.

**Negativas / trade-offs aceitos:** indireção via Protocol adiciona um nível de chamada (custo de leitura). Não perseguimos "~30 linhas/policy" do sketch — encolher honestamente preservando a semântica de merge é o ganho real, não a contagem de linhas. Wrappers de compat mantêm 2 dataclasses de resultado legadas vivas (dívida pequena; cutover futuro opcional).

## Alternativas consideradas

- **(B) Seguir o sketch §F1-O2 (Protocol gordo):** rejeitado — no-ops por design violam ISP e criam caminhos não-exercitados num invariante FP=0; três policies implementando stubs do mesmo método são três oportunidades de divergir em silêncio.
- **(C) Rescopar l3 (só `DedupOutcome` compartilhado, imóveis como follow-up):** rejeitado — o esqueleto duplicado é o débito que l3 existe para pagar; adiar metade não fecha a lane nem previne a 3ª cópia em l4.
- **Mudar tipos de retorno públicos para `DedupOutcome`:** rejeitado neste PR — mudaria o shape que call-sites/tests veem; cutover é follow-up separado, fora do "sem mudar comportamento".

## Critério de aceite

1. `entity_dedup.py` com `EntityDedupPolicy` (3 membros), `run_entity_dedup`, `DedupOutcome`, `DedupWarning`.
2. `imoveis_dedup` e `investimentos_dedup` reescritos como policies; funções públicas + `DedupResult`/`InvestDedupResult` preservados como wrappers.
3. Snapshot diferencial byte-a-byte old↔new sobre corpus completo: idêntico.
4. 17 + 25 unit tests + INV-1..8 (l1) + golden `fn`/`fp` (l2) verdes, sem alteração de assert.
5. Ordem de iteração coberta por teste explícito.
6. `e15_consolidate.py` inalterado (call-sites compatíveis).
