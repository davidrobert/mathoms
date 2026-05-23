---
id: ADR-265
type: adr
title: "Fuzzy lookup de PropertyIdentity por proximidade numérica (extensão ADR-225 Case C)"
status: Proposto
phase: A17.canonical-fuzzy
date: "2026-05-23"
relates_to:
  - "[[ADR-215]]"
  - "[[ADR-225]]"
  - "[[ADR-239]]"
  - "[[ADR-246]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 265"
  - "Fuzzy canonical property"
  - "Property fuzzy via num"
tags:
  - area/persistence
  - area/pipeline
  - area/methodology
  - phase/a17
  - status/proposto
  - type/adr
---

# ADR-265 — Fuzzy lookup de PropertyIdentity por proximidade numérica

**Status:** Proposto · **Data:** 2026-05-23 · **Relaciona** [[ADR-215]] (PropertyIdentity), [[ADR-225]] (canonicalize cascade), [[ADR-239]] (comprovantes de bem), [[ADR-246]] (dedup cross-IRPF).

## Contexto

[[ADR-225]] §1 introduziu cascata `via_numero → matrícula → QA → IPTU` para `endereco_canonical`. Output é **string-exato**: dois canonicals casam se e só se são idênticos. [[ADR-246]] (PR #468) introduziu dedup cross-codigo no `imoveis_dedup.py` para fundir `(cod=01, canonical X)` + `(cod=11, canonical X)` quando canonical é idêntico. Resolver `DBPropertyIdentityResolver` tem cascade strict → loose → insert ([[ADR-225]] §2).

**Caso real** (workspace founder, run `a90ce448-7e3f-4c09-b3f9-06edb064a5c1`, 2026-05-23):

| Fonte | Descrição | `endereco_canonical` |
|---|---|---|
| IRPF (`codigo_rfb=11`) | `APARTAMENTO - CONDOMINIO BARAO DE CAPANEMA - APTO 34 - PRACA BENEDITO CALIXTO 190` | `benedito calixto 190` |
| Comprovante de bem (`codigo_rfb=01`, [[ADR-239]]) | `Apartamento - Praça Benedito Calixto, 186 - Ap 34, São Paulo - SP` | `benedito calixto 186` |

É o **mesmo imóvel físico** (mesmo prédio, mesmo apto 34) — uma fonte traz número do prédio (186), outra traz número da torre/condomínio (190). Divergência editorial típica entre escritura, IPTU e IRPF.

Como canonical é string-exato:

- `_find_by_canonical_loose` não casa → 2 rows em `property_identity`.
- `_merge_cross_codigo` em `imoveis_dedup.py` não casa (chave de identidade é `(codigo_rfb_strip, endereco_canonical)`) → duplicata sobrevive até relatório.

[[ADR-225]] §Follow-ups linha 274 explicitamente registra este caso como follow-up adiado: "Case C — typos numéricos em via+numero entre fontes (ex.: 190 vs 186 mesmo imóvel). Futura ADR pode inverter ordem com backfill de rows legadas". Esta ADR resolve o Case C **sem inverter ordem da cascata** e **sem migration destrutiva** — via extensão do **lookup** apenas.

## Decisão

Introduzir **fuzzy match por proximidade numérica em canonicals do tipo `<via> <numero>`** como **3º nível** da cascata de lookup do resolver e como **passe 4** dos dedupers (helper E1.5c + script de backfill). **`canonicalize()` não muda** — coluna persistida `endereco_canonical` continua determinística ([[ADR-225]] §1). **`codigo_rfb` continua imutável** (invariante de agregação E5 em `real_estate_e5_integration._match_identity`; memória `feedback_codigo_rfb_invariant`).

### 1. Helper puro `matches_fuzzy`

Novo módulo `pipeline/domain/services/canonical_fuzzy_match.py`. Pure, sem I/O, determinístico.

```python
def matches_fuzzy(
    canonical_a: str,
    canonical_b: str,
    *,
    max_number_diff: int = 4,
    max_with_complemento_match: int = 8,
    complemento_a: str | None = None,
    complemento_b: str | None = None,
) -> bool:
    """True se mesmo imóvel via proximidade numérica."""
```

**Regras:**

1. Canonicals com prefixo forte (`mat:`, `qa:`, `iptu:`) só casam **string-equal**. Fuzzy não se aplica (identificador estável é evidência mais forte que via+numero).
2. Canonicals do tipo `<via> <numero>` são extraídos via regex `^(.+?)\s+(\d+)$`. Sem match → False.
3. Via **idêntica** (já normalizada por `canonicalize`) é requisito.
4. **K=4 default** (`max_number_diff`). Cobre o caso real (Δ=4) e rejeita falsos positivos em zona densa (Av Paulista: 1500 vs 1490 = Δ=10, não funde).
5. **K=8 se complemento bate** (`max_with_complemento_match`). Quando `complemento_a == complemento_b` (string-equal, ambos não-vazios) — ex.: ambos têm "apto 34" — tolerância expande.
6. **Guard de complemento divergente:** se `complemento_a != complemento_b` E ambos não-vazios, NÃO funde mesmo com via+número compatíveis. "Apto 51" vs "Apto 34" no mesmo endereço = imóveis distintos.

### 2. Resolver com 3º nível na cascata

`DBPropertyIdentityResolver.match_or_create` ganha `_find_by_canonical_fuzzy` após `_find_by_canonical_loose` e antes do insert:

```
strict (codigo_rfb + canonical)
  → loose (canonical only, same workspace)
  → fuzzy (matches_fuzzy via Python, same workspace)
  → insert + reconciliation read
```

Query: `SELECT * FROM property_identity WHERE workspace_id = ? ORDER BY created_at ASC`. Filter Python via `matches_fuzzy`. Skip rows com canonical `mat:`/`qa:`/`iptu:` (não candidates a fuzzy).

**Justificativa load-all + filter Python:** workspace tem dezenas de imóveis (não milhares); custo desprezível; reusa o mesmo `matches_fuzzy` helper que o dedup usa (single source of truth); evita SQL `LIKE` com escape frágil de espaços/`%` em via.

### 3. Passe 4 em `imoveis_dedup.py`

Após `_merge_cross_codigo` (PR #468), novo `_merge_fuzzy_via_num` agrupa entries por via (extraída do canonical) e funde candidatos via `matches_fuzzy`. **Reusa o critério de não-conflito específico** do passe 3 (cod=11 vs cod=12 não funde mesmo com fuzzy).

**Ordem dos passes:**

```
1. _group_by_identity (chave de identidade exata)
2. _merge_cross_codigo (PR #468 — cross-codigo_rfb mesmo canonical)
3. _merge_fuzzy_via_num (novo — mesma via, Δ ≤ K)
```

Justificativa: cross-codigo é exato; fuzzy é tolerante. Restritivo antes do tolerante. Para o caso real (190+cod=11 vs 186+cod=01, **duas dimensões divergem**) a ordem não muda o resultado — o fuzzy funde direto via mesma + complemento (apto 34) presente em ambas as descrições. Em workspace com 3 fontes (190+cod=11 + 190+cod=01 + 186+cod=01), cross-codigo primeiro funde os dois `190`; fuzzy depois funde com `186`.

### 4. Passe 4 em `dev/dedup_property_identity.py`

Backfill espelhando regra do helper. `--dry-run` default; output JSON com:

```json
{
  "passe_4_fuzzy": [
    {
      "canonical_id": "<winner-uuid>",
      "dupes_dropped": ["<loser-uuid>"],
      "via": "benedito calixto",
      "numero_winner": "190",
      "numero_loser": "186",
      "match_distance": 4,
      "complemento_match": true,
      "codigos_fundidos": ["01", "11"],
      "overrides_realocados": 0
    }
  ],
  "passe_4_red_flags": [
    {
      "candidates": ["<uuid-a>", "<uuid-b>"],
      "reason": "complemento_divergente | valor_divergente_30pct | matricula_divergente",
      "audit_required": true
    }
  ]
}
```

Idempotente; `--apply` exige auditoria humana 100% dos merges propostos antes (especialmente quando `match_distance` ≥ 5 ou red flag dispara).

### 5. Observabilidade

- Counter `mathoms.property_identity.cascade_hit{level=fuzzy}` no resolver (já tem `strict`/`loose`).
- Log estruturado em `consolidate.imoveis_dedup` ganha campos:
  - `match_strategy: "exact" | "cross_codigo" | "fuzzy_via_num"`
  - `match_distance: int` (apenas para fuzzy)

## Alternativas consideradas

- **(B) Match por prefixo de via SEM número.** Cobre 100% editorial mas falso-positivo garantido em vias longas. **Rejeitado.**
- **(C) Aprendizado assistido por LLM (`address_aliases` table).** Persistir mapping `(via, 190) ↔ (via, 186)` quando matrícula/IPTU coincidem. Zero falso-positivo (depende de evidência). Custo: schema novo, gatilho de aprendizado, infra. **Adiado para ADR sucessora.**
- **(D) K=10 (proposta original do track).** Track sugeriu K=10 como ponto de partida. Co-design com `data-engineer` + `financial-planner` convergiu em **K=4 conservador** porque (i) caso real é Δ=4 → cobre com folga 0; (ii) numeração brasileira de via é densa (pares/ímpares lado a lado, passos de 2-4m entre prédios); K=10 captura 5 imóveis consecutivos.
- **(E) K=3 (proposta `financial-planner`).** Defensiva, mas Δ=4 do caso real ficaria fora — a ADR perderia o motivador imediato. K=4 + guard de complemento atinge o mesmo nível de segurança sem perder o caso.
- **(F) Inverter ordem da cascata em `canonicalize`** (matrícula primeiro). Migration substantiva de rows legadas; lacuna de duplicatas até rodar. Mais invasivo; rejeitado em [[ADR-225]] §Follow-ups.

## Consequências

**Positivas:**

- ✅ Caso founder resolvido: 7 → 6 imóveis em `imoveis_consolidados` (Benedito Calixto consolidado).
- ✅ Sem mudança de DDL nem coluna `endereco_canonical`; lookup é o único ponto tocado.
- ✅ Determinismo preservado: mesmo input + K → mesmo output.
- ✅ Aplicável retroativamente via Passe 4 do script com auditoria humana.
- ✅ Resolve "Case C" da [[ADR-225]] §Follow-ups.
- ✅ Cascade observability via counter `level=fuzzy`.

**Negativas:**

- ⚠️ K=4 é heurística calibrada via caso real + intuição de domínio. Pode precisar ajuste pós-dogfood (mais workspaces, mais sinal). Mitigado por counter + dry-run obrigatório.
- ⚠️ Pequeno overhead no resolver (load-all em vez de SELECT específico). Volume é dezenas; desprezível.
- ⚠️ Cresce a superfície de manutenção do helper de dedup (4 passes em vez de 3).

**Consumers que dependem da invariante `codigo_rfb`:**

| Site | Uso | Impacto |
|---|---|---|
| `real_estate_e5_integration._match_identity` | Filtro estrito por `codigo_rfb` | **Preservado** — winner do passe 4 segue regra do passe 3 (específico vence genérico) |
| `WorkspacePropertyOverride.classification` | Sticky por `property_id` | Realocação no Passe 4 do script (mesmo padrão do Passe 3) |
| `PropertyResponse.codigo_rfb` (DTO) | Label UI | Sem impacto direto |

**Riscos:**

| Risco | Mitigação |
|---|---|
| Falso-positivo: 2 imóveis distintos colapsam | K=4 conservador; guard de complemento divergente; red flags no dry-run (matrícula divergente, valor >30% Δ) |
| Property_ids pré-fix cristalizados (workspaces existentes) | Passe 4 do `dev/dedup_property_identity.py` com `--dry-run` obrigatório + auditoria humana |
| Override órfão pós-merge | Realocação automática no passe 4 do script (idem passe 3) |
| Numeração condominial em Alphaville | Guard de complemento divergente captura; sem complemento, K=4 default rejeita Δ>4 |

## Follow-ups (fora do escopo)

- **(Opção C deferida)** `address_aliases` table com aprendizado assistido por LLM/matrícula. ADR sucessora própria.
- **K varia por região/tipo de via** (CEP + lat/lng). Heurística cara, sem infra geo no domain layer hoje. Só vale ADR se golden mostrar miss recorrente.
- **UI human-in-loop para merge manual** (endpoint `POST /workspaces/{ws}/properties/merge` + checkbox). Cobre casos onde Passe 4 não casa (complemento ausente em uma fonte, valor muito divergente). Já registrado em [[ADR-225]] §Follow-ups.
- **Auto-apply do Passe 4** sem auditoria humana quando golden estiver maduro (≥3 workspaces dogfood validados sem falso-positivo).

## Gates

- **Helper unit tests** em `tests/unit/pipeline/test_canonical_fuzzy_match.py`:
  - Δ=0 (string-equal, casa)
  - Δ=4 sem complemento (casa)
  - Δ=8 sem complemento (não casa)
  - Δ=8 com complemento idêntico (casa)
  - Δ=12 com complemento idêntico (não casa)
  - Δ=4 com complemento divergente (NÃO casa — guard)
  - Via diferente (não casa, qualquer Δ)
  - Canonical com `mat:`/`qa:`/`iptu:` (não casa, retorna False imediatamente)
  - Canonical malformado (sem número parseável, retorna False)
- **Backend resolver test** em `backend/tests/test_db_property_identity_resolver.py`:
  - Match fuzzy retorna row existente (`benedito calixto 190` + lookup `benedito calixto 186` → mesma identity).
  - Fuzzy não cross-workspaces (tenancy preservado).
- **Integration test** em `tests/test_e15_consolidate_dedup.py`:
  - Cenário founder (`190+cod=11` + `186+cod=01`) → 1 entry.
  - Cenário condomínio (`apto 34` + `apto 51` mesma via, números próximos) → 2 entries.
  - Cenário Av Paulista (`1500` + `1490` mesma via, sem complemento) → 2 entries.
- **Backfill test** em `tests/test_dedup_property_identity.py`:
  - Passe 4 fuzzy funde rows com Δ≤4; idempotente.
  - Red flag para complemento divergente (sem fundir).
  - Overrides realocados ao winner.
- **`dev/check_code_style_regression.py`** — sem regressões.
- **Sample empírico:** dry-run em todos workspaces dogfood antes do merge; auditoria humana 100% dos merges propostos.

## Referências

- [[ADR-215]] — Modelo base PropertyIdentity.
- [[ADR-225]] — Cascata canonicalize + resolver loose + dedup script. Esta ADR endereça §Follow-ups "Case C".
- [[ADR-239]] — Comprovantes de bem (motivador imediato — fonte de canonicals com cod=01).
- [[ADR-246]] — Dedup cross-IRPF (motivador imediato — extensão direta do helper).
- Co-design 2026-05-23: `data-engineer` (threshold, ordem dos passes, query do resolver, backfill, red flags); `financial-planner` (impacto patrimonial, alocação-alvo AUVP, guard de complemento, telemetria).

## Status — Proposto

ADR aberta antes do PR de implementação (`CLAUDE.md` §"Política operacional — ADR `Proposto` antes de PR P0/P1"). Flippa para `Decidido (Sprint A17.canonical-fuzzy)` no merge do PR.
