---
id: ADR-146
type: adr
title: "E3 source hierarchy + `BankAccount.source_tier` schema"
status: Decidido
phase: "Sprint A7.6 · CTO sign-off 2026-04-27"
date: "2026-04-27"
relates_to: ["[[ADR-143]]", "[[ADR-097]]", "[[ADR-278]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 146"]
tags:
  - area/multitenancy
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 48
---

# ADR-146 — E3 source hierarchy + `BankAccount.source_tier` schema

**Status:** Decidido (Sprint A7.6 · CTO sign-off 2026-04-27) • **Data:** 2026-04-27 • **Relaciona** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76), [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy).

**Contexto:** O stage E3 (reconciliação) consolida transações de múltiplas fontes (extratos bancários parseados, faturas de cartão, screenshots de app, deduções IRPF, declarações editorais) e precisa decidir qual fonte tem precedência quando há conflito (ex.: mesma transação aparece em extrato + fatura de cartão por causa de pagamento intermediado).

A regra histórica está em `config/methodology/source_hierarchy.md` (movido para `docs/methodology/` em A7.4) misturando hierarquia universal com mapeamento workspace-specific (David's Itaú vs Mariana's BTG). ADR-143 elimina o markdown; esta ADR registra hierarchia universal + abre schema migration para tier per `BankAccount`.

Alternativas consideradas:

- **(a) Hierarquia hardcoded global.** Toda banco tipo X é tier 1, banco tipo Y é tier 2. **Trade-off:** ignora variação por workspace (cliente A pode confiar mais em Itaú; cliente B em BTG). Insuficiente.
- **(b) Hierarquia universal + override por workspace via campo `BankAccount.source_tier`.** Mathoms define tier default por *tipo* de fonte; cada workspace pode overrideá-lo per-account quando há razão.
- **(c) Hierarquia 100% workspace-defined (sem default Mathoms).** Cliente novo abre conta = tem que configurar tier de cada banco. UX ruim; sem onboarding default.

**Decisão:** Adotar **(b)**.

Hierarquia universal default (tier ascendente — tier 1 = mais confiável, tier 5 = menos):

1. **Tier 1 — Extração LLM de extrato OFX/PDF estruturado** (alta confiança: dados estruturados, datas precisas, descrições completas).
2. **Tier 2 — Extrato bancário parseado por regex** (alta confiança quando o parser cobre o formato; pode perder transações em formatos não cobertos).
3. **Tier 3 — Fatura de cartão de crédito** (cobertura parcial: só transações no cartão; pode duplicar com extrato quando há pagamento intermediado).
4. **Tier 4 — Screenshot de app extraído por LLM** (média confiança: dependente da qualidade da imagem; bom para contas de investimento sem extrato).
5. **Tier 5 — Declaração editorial / dedução IRPF / planilha manual do cliente** (baixa confiança automatizada, mas alta confiança humana — usado como ground truth para reconciliar discrepâncias finais).

Regra de reconciliação: quando duas fontes reportam a mesma transação (matched por valor + data ± 2 dias + descrição similarity), a fonte de **tier menor (mais alto na hierarquia)** vence. Ties dentro do mesmo tier resolvem via timestamp da extração (mais recente vence) — evita instabilidade quando o pipeline reroda.

Schema migration (Alembic backwards-compat — add nullable + populate + flip):

```python
class BankAccount(Base):
    # ... campos existentes ...
    source_tier: int | None = Column(SmallInteger, nullable=True, default=None)
    # None = usar default Mathoms baseado em tipo (account_type / institution.parser).
    # Não-None = override workspace-específico.
```

Function que enforce a hierarchy vai para docstring em `pipeline/domain/services/income_origin_resolver.py` (ou similar identificado pelo Explore da A7.6). Override workspace-specific resolvido via `ResolvedBankAccount.tier(workspace_id, db)` que consulta `source_tier` e fallback para regra default.

**Consequências:**
- ✅ Pipeline E3 deterministicamente reconciliável: ties têm regra explícita.
- ✅ Workspace tem flexibilidade de override quando o default não reflete sua realidade (ex.: cliente que tem screenshot mais confiável que o extrato porque parser falha no formato).
- ✅ Onboarding default funciona — não exige configuração tier-by-bank pelo cliente.
- ⚠️ Schema migration adiciona coluna nullable ao `bank_accounts`. Backwards-compat sob ADR-097 (add nullable + populate + flip — sem DROP no mesmo PR).
- ⚠️ Documentação da regra default fica em docstring de **uma** função (income_origin_resolver). Se a função for refatorada/extraída, o docstring deve migrar junto. Mitigação: regra documentada em ADR-146 mesmo (esta) é o índice canônico.
- ⚠️ **Test fixture obrigatório:** dois artefatos mesmo-tier reconciliados deterministicamente entre runs (regra de tie-breaking via timestamp). Sub-task de A7.6 que migra o resolver deve incluir `tests/unit/pipeline/test_e3_source_tier_tie_breaking.py` com 2 specs: (a) tier mais alto vence ainda que extração mais antiga; (b) mesmo tier → timestamp mais recente vence.
- ❌ `source_tier` per-account ignora granularidade temporal (banco pode ter parser melhorando ao longo do tempo). Aceito — granularidade temporal exige ADR específica futura.

## Emenda (A23 — plano [[PLAN-data-lineage]], blocker B1)

O tie-break original (§Regra de reconciliação, linha 45: "ties dentro do mesmo
tier resolvem via timestamp da extração — mais recente vence") é
**não-determinístico** entre re-extrações e contradiz o invariante "zero
timestamp em `_lineage`" da [[ADR-279]]. Ao promover `pick_winner` a base da
`SourcePrecedencePolicy` cross-source ([[ADR-278]]), o tie-break passa a ser
`(tier, kind-priority, alfabético por artifact_key)` — alinhado ao survivor
estável da [[ADR-255]]. Reusa só a **hierarquia de tier** de `pick_winner`, não
o desempate por `extracted_at`.

**Impacto:** muda o tie-break do reconciler E3 → rebaseline de goldens E3
esperado (commit isolado). O `pick_winner` deixa de ser dead code órfão (hoje
declarado mas ignorado pelo dedup) e passa a ser exercido pela policy.
