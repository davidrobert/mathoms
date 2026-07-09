---
id: ADR-267
type: adr
title: "Identidade canônica de membro do workspace via CPF (não slug-de-nome)"
status: Decidido
phase: A17.member-identity
date: "2026-05-23"
relates_to:
  - "[[ADR-225]]"
  - "[[ADR-243]]"
  - "[[ADR-246]]"
  - "[[ADR-255]]"
  - "[[ADR-265]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 267"
  - "Member CPF identity"
  - "MemberNameResolver CPF strategy"
tags:
  - area/pipeline
  - area/domain
  - area/identity
  - status/decidido
  - type/adr
---

# ADR-267 — Identidade canônica de membro via CPF

**Status:** Decidido • **Data:** 2026-05-23 • **Relaciona** [[ADR-225]] (PropertyIdentity invariante), [[ADR-243]] (MemberNameResolver slug-based, **supersedido parcialmente** por esta ADR), [[ADR-246]] (dedup imóveis cross-IRPF), [[ADR-255]] (dedup transações cross-document — paralelo metodológico), [[ADR-265]] (fuzzy PropertyIdentity).

## Contexto

Bug em produção no workspace `1b9f2cf5-…` (report `ffde7f63-…`): o consolidador `baseline_patrimonial` (E1.5c) trata a **mesma pessoa** como membros distintos quando IRPFs ao longo do tempo trazem **nomes variantes**.

**Caso Cônjuge** (CPF redacted — workspace dogfood):

| Ano | Slug em `itens[].membro` | n_bens | Total |
|---|---|---|---|
| 2023 | `conjuge_sobrenome_solteira` (sobrenome solteira) | 11 | R$ 800.000,00 |
| 2024 | `conjuge_sobrenome_casada` (sobrenome casada) | 19 | R$ 1.000.000,00 |

Mesma pessoa, anos sucessivos — só 2024 deveria valer (most-recent-year-wins, paridade com [[ADR-246]]). Atualmente **são somados** porque slugs disjuntos não casam em nenhuma das 5 estratégias de `MemberNameResolver` ([ADR-243](243-membername-resolver-canonico.md)):

- Estratégia 1-4 (exact slug em key/full_name/short_name/nome_nascimento): falham — slugs literalmente diferentes.
- Estratégia 5 (substring ≥ 5 chars): `"conjuge_sobrenome_solteira" ∉ "conjuge_sobrenome_casada"` e vice-versa.

**Inflação medida:** R$ 800k no patrimônio do workspace.

**Caso Titular** (CPF redacted — workspace dogfood): 6 IRPFs com nomes variantes:
- `"TITULAR EXEMPLO SOBRENOME COMPLETO"` (IRPF 2025, completo)
- `"TITULAR EXEMPLO SOBRENOME"` (IRPF 2026, abreviado)
- `"TITULAR EXEMPLO"` (IRPF 2026, variante)
- `"TITULAR EXEMPLO SOBRENOME LTDA"` (IRPF 2026 — **é PJ!**, contaminação)

Análogo: múltiplos membros emergem para mesma pessoa. (PF vs PJ filtragem é problema separado — escopo de ADR-267 futura.)

### Cadeia técnica

1. **E1** (`extract_members.py`) já **emite CPF** no payload `family_members.membros[key].cpf` quando o LLM extrai com sucesso ([linha 38-39](../../pipeline/stages/extract_members.py)).
2. **E1.5a** (`extract_irpf_full`) emite `payload.contribuinte.cpf` em todas as 10 declarações observadas.
3. **E1.5c** (`scripts/e15_consolidate.py`) usa o **slug-de-nome puro** como `membro` (linha 418: `(item.get("membro") or _TITULAR or "").strip().lower()`). **Não consulta CPF.**
4. **`MemberNameResolver`** ([ADR-243](243-membername-resolver-canonico.md)) tem 5 estratégias slug-based, **sem CPF**.

CPF está **disponível** no pipeline mas **ignorado** no momento da consolidação. Slug-de-nome é frágil — falha em todo evento de vida que mude nome (casamento, divórcio, retificação cartorial, abreviação).

### Impacto

- **Patrimônio inflado:** workspaces com múltiplos IRPFs do mesmo titular ao longo do tempo somam itens em vez de manter only-most-recent. R$ 800k inflado medido no workspace dogfood.
- **KPIs derivados:** total_ativos, patrimonio_liquido, distribuição alocação-alvo, score AUVP — todos inflados.
- **Parecer LLM (E6):** raciocina sobre patrimônio fictício.
- **Cascata fiscal PJ ([[ADR-236]]):** rendimento PJ pode estar associado a slug errado se nome PJ casa parcialmente com PF.
- **Universalidade:** afeta **todos os workspaces** com mudança de sobrenome ou variantes ortográficas. Casamento é evento comum no público-alvo (Mathoms é planejamento patrimonial familiar).

## Decisão

**Inverter a hierarquia do resolver: CPF passa a ser identidade primária (estratégia 0); slug-de-nome vira fallback degraded.**

### D1 — Estratégia 0: CPF como chave canônica

Em `pipeline/domain/services/member_name_resolver.py`:

- `MemberRecord` ganha campo `cpf: str | None = None` (normalizado: só dígitos, 11 chars).
- `MemberNameResolver.from_family_config` lê `family.membros[key].cpf` quando presente.
- Novo método `resolve_by_cpf(cpf: str) -> MemberNameResolution`:
  - Normaliza CPF (`"".join(filter(str.isdigit, cpf))[:11]`).
  - Match exato contra `MemberRecord.cpf` normalizado.
  - Retorna `MemberNameResolution(canonical_key=member.key, confidence="cpf", matched_via="cpf")`.
- `Confidence` enum ganha valor `"cpf"` no topo da hierarquia (mais forte que `"exact"`).

### D2 — Cascata em call-sites

Consumers que recebem ambos CPF e nome (ex.: items vindos de IRPF) chamam:

```python
resolution = resolver.resolve_by_cpf(cpf) if cpf else MemberNameResolution(None, "unknown")
if resolution.canonical_key is None:
    resolution = resolver.resolve(nome)
```

Padrão consistente. CPF ausente (workspace sem IRPF, baseline manual) cai naturalmente no name resolver.

### D3 — Normalização de CPF

```python
def normalize_cpf(value: str | None) -> str:
    """Strip não-dígitos, trunca em 11 chars. Retorna '' se vazio/inválido."""
    if not value:
        return ""
    digits = "".join(c for c in str(value) if c.isdigit())
    return digits[:11] if len(digits) >= 11 else ""
```

Aceita ambos `"123.456.789-09"` (mascarado) e `"12345678909"` (sem máscara). Rejeita strings sem exatamente 11 dígitos (proteção contra CNPJ 14 dígitos e CPF parcial mascarado). CNPJs completos (14 dígitos) **não** são membros PF — filtrados em ADR-267.

### D4 — Schema invariante (cross-stage)

`itens[].membro` (em `baseline_patrimonial`, `e4_patrimonio`, `e5_*`) **DEVE** ser uma key existente em `family_members.membros` quando não-vazio. Hoje é convenção implícita. Esta ADR torna explícito:

- Schema JSON (`config/schemas/baseline_patrimonial.schema.json`) — invariante documentado.
- Hook de validação pós-write em `DBArtifactStore.write` ou check ad-hoc em `dev/check_*` — **diferido para PR2/PR3** (ver §"Próximos passos").

### D5 — Sem schema breaking

`itens[].cpf` opcional emergente em E1.5c (quando IRPF traz CPF) — **aditivo**, não obrigatório. Workspaces pré-fix continuam válidos (CPF ausente nos items pré-existentes).

### D6 — Out of scope desta ADR (mas relacionado)

- **PF vs PJ filter no E1.5a** — quando IRPF emite `"TITULAR EXEMPLO SOBRENOME LTDA"`, o extractor deveria filtrar (sufixo `LTDA`, `S.A.`, `EIRELI`, `ME`, `EPP`, `MEI`, ou CNPJ no documento). **ADR-267 separada.**
- **Self-healing enrichment** — quando IRPF traz CPF e `family_members.membros[key]` ainda não tem, escrever de volta. **Decisão diferida** — risco de associação errada em substring match; melhor manter explícito por enquanto.
- **Dependente menor sem CPF** — co-design com `financial-planner` para edge cases (dependente menor declarado pelo titular, cônjuge estrangeiro). Fallback name resolver cobre quando CPF ausente.

## Consequências

**Positivas:**

- Cônjuge solteira ↔ casada colapsam em 1 membro canonical. Patrimônio cai de R$ 4.000k → R$ 3.200k (Δ −R$ 800k) no workspace dogfood.
- Titular com 6 IRPFs colapsa em 1 membro (descontando ADR-267 que filtra o LTDA).
- Identidade estável entre runs — slug-de-nome volátil deixa de ser sintoma.
- Habilita features futuras: rastreabilidade por CPF entre stages, dedup cross-year robusto, audit "qual IRPF trouxe qual bem".
- Paralelo metodológico com [[ADR-255]] it.2 e [[ADR-225]] — invariante imutável (CPF) vence string mutável (nome/slug).

**Negativas / trade-offs aceitos:**

- **CPF é PII** (LGPD) — já está em `family_members` (campo opcional encriptado pela Fernet vault do workspace, [[ADR-111]]). Não há nova superfície de exposição.
- **Workspaces sem CPF** — fallback name resolver. Confiabilidade degradada mas não pior que hoje.
- **Recompute necessário** — workspaces afetados precisam re-rodar `consolidate_baseline` para colapsar duplicações pré-fix. Stage determinístico sem LLM — barato. Trigger ad-hoc OU via `recompute_consolidate_baseline` (deferido para PR3).
- **Não cobre PJ-mistura** (ADR-267 cuida disso).

## Observabilidade

`MemberNameResolver._emit` ganha campo `matched_via="cpf"` no log estruturado. Drift detection: ratio de resoluções por estratégia por workspace por run. Sinais:

- Aumento súbito de `unknown` com CPF presente → `family_members` desatualizado (gatilho de re-extração E1).
- Queda em `cpf` ratio → E1.5a parou de emitir `contribuinte.cpf` (regressão upstream).
- Ratio `cpf` ≥ 95% por 30 dias → fallback name resolver vira candidato a deprecation (force-error em workspaces novos).

## Critério de aceite

1. **Resolver API** — `MemberNameResolver.resolve_by_cpf("123.456.789-09")` retorna `canonical_key="conjuge_sobrenome_casada"` (ou equivalente) quando family_members tem `conjuge_sobrenome_casada.cpf == "12345678909"`.
2. **Normalização CPF** — `normalize_cpf("123.456.789-09") == normalize_cpf("12345678909") == "12345678909"`.
3. **Cascata** — quando CPF ausente, resolver volta para 5 estratégias name-based (compat com workspaces sem IRPF).
4. **`Confidence` enum** — `"cpf"` é valor válido, no topo da hierarquia.
5. **Telemetria** — log JSON com `matched_via="cpf"` emitido quando estratégia dispara.
6. **Goldens** — `tests/unit/pipeline/test_member_name_resolver.py` ganha goldens cobrindo:
   - Cônjuge solteira+casada via CPF → mesma canonical_key.
   - Titular 6 IRPFs (5 PF, 1 PJ) via CPF → 1 canonical_key (LTDA ainda contamina até ADR-267, registrar como warning).
   - CPF ausente → cai no name resolver (regression preservada).
   - CPF mascarado vs não-mascarado → mesma resolução.
   - CNPJ 14-dígitos → rejeitado (retorna `unknown` se nome também não casa).

## Plano de rollout

**PR1 (este escopo — API)**:
- Estende `_tx_identity.py`-style: novo módulo NÃO, extende `member_name_resolver.py` com CPF estratégia 0.
- Adiciona `normalize_cpf` em novo arquivo `pipeline/domain/services/_cpf_identity.py` (similar a `_tx_identity.py`).
- Testes unitários cobrindo critério #1-6.
- ADR-267 publicada como `Proposto`.
- **Não toca consumers ainda** — API estabelecida, consumers adotam em PR2.

**PR2 (consumers, este sprint)**:
- `scripts/e15_consolidate.py::consolidate_from_itens` chama `resolver.resolve_by_cpf(item.get("cpf"))` antes de cair em slug.
- Schema `baseline_patrimonial.schema.json` ganha campo `cpf?` em items (aditivo).
- Extractor E1.5 (`pipeline/llm/schemas/e1_5_baseline.py` + prompt) emit `cpf` por item quando IRPF traz.
- Goldens regen.
- Critério #13 da ADR-255: análogo aqui — workspace dogfood com Cônjuge colapsada em 1 membro, R$ 800k removidos.

**PR3 (audit + backfill)**:
- `dev/audit_member_identity_drift.py` — itera workspaces, agrupa itens por CPF, reporta colisões.
- `backend/app/services/internal_ops/recompute_consolidate_baseline.py` — padrão idêntico a `recompute_e4` ([[ADR-255]] §PR3).
- Marca `pipeline_runs.stale=true` em consumers downstream.
- Runbook em `docs/reference/runbooks/`.

**PR4 (lane futura — ADR-267)**: filtro PF vs PJ no E1.5a.

**Flip ADR-267 → Decidido** após PR2 confirmar critério no workspace dogfood em produção.

## Alternativas consideradas

- **(A) Estender `MemberNameResolver` com CPF estratégia 0** (escolhido): mínima superfície de mudança, cascata natural, mantém compat com workspaces sem CPF. Trade-off: mistura name + identity num único service. Aceito porque consumers compartilham contexto (precisam ambos CPF-first E name fallback).
- **(B) Service novo `MemberIdentityResolver` CPF-only**: separação de responsabilidades. Trade-off: 2 resolvers paralelos com 80% código compartilhado → débito. Rejeitado.
- **(C) Refactor schema `family_members.membros[cpf]`** (CPF como chave do dict): mais radical, força CPF obrigatório. Quebra ABI. Rejeitado.
- **(D) Dedup ad-hoc downstream em cada consolidator** (workaround): não toca resolver, cada consolidator agrupa por CPF se disponível. Workaround, não fix de raiz. Rejeitado.

## Próximos passos

- **PR1 (este)**: API + ADR + tests.
- **PR2 (este sprint)**: schema extension + consumer adoption + goldens regen.
- **PR3 (este sprint)**: audit + backfill via console interno ([[ADR-116]]).
- **PR4 (lane futura)**: ADR-267 — PF vs PJ filter no E1.5a.
- **Brief financial-planner** (paralelo, não-bloqueante): edge cases regulatórios BR (dependente menor sem CPF, cônjuge estrangeiro).
- **Deprecation deadline** do fallback name resolver: 95% `cpf` coverage por 30 dias → force-error em workspaces novos (tracked separadamente).
