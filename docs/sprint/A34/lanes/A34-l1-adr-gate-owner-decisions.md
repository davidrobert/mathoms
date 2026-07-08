---
id: A34.l1
type: lane
title: "ADRs Proposto do gate de decisões (ADR-313 a ADR-320)"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: adr-gate-owner-decisions
adrs: ["[[ADR-313]]", "[[ADR-314]]", "[[ADR-315]]", "[[ADR-316]]", "[[ADR-317]]", "[[ADR-318]]", "[[ADR-319]]", "[[ADR-320]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/seguranca
---

# A34.l1 — `adr-gate-owner-decisions` (W0 · Gate)

## Problema

O plano [[PLAN-public-release]] só pode abrir a Onda 1 (saneamento do HEAD) depois
que **oito decisões owner-gated** estiverem travadas. Hoje elas vivem apenas na
tabela de §"ADRs `Proposto`" do `_README.md` — como recomendação leading, não como
decisão registrada. Sem ADR canônica por decisão:

- não há **rationale + alternativas** rastreável (protocolo P0/P1 do CLAUDE.md exige
  ADR `Proposto` antes de PR de escopo arquitetural);
- não há **cláusula de decisão do owner** por questão — o flip in-place é irreversível
  na camada de metadados ([[ADR-316]]), e falhar cedo (W0) evita desperdiçar W1–W3;
- o grafo do plano aponta para 8 wikilinks (`adrs_canonical`) que ainda não resolvem —
  `check_doc_links` quebra até os arquivos existirem.

Este é o **gate G0**: nenhuma lane W1+ abre antes das 8 ADRs mergeadas com decisão
textual do owner em cada questão.

## Escopo

Abrir **8 ADRs atômicas** `Proposto` (uma por decisão, [[ADR-182]] — NÃO uma
ADR-monstro), cada uma com: contexto, decisão, alternativas rejeitadas, consequências,
e — nas owner-gated — **cláusula explícita de decisão do owner** (bloco de sinal no topo
até a decisão ser assinada). Recomendação leading já registrada no `_README.md`:

1. **[[ADR-313]]** — Licença open-source. Leading: **BSL 1.1** source-available
   (Change License Apache-2.0, 4 anos); alt. AGPL-3.0; fallback MIT/Apache.
2. **[[ADR-314]]** — Escopo público (allowlist/blocklist de paths + IP). Split privado
   dos prompts de produto; redigir/mover [[PLAN-competitive-pierre]]; genericizar pricing.
3. **[[ADR-315]]** — Estratégia de rewrite de histórico. `git-filter-repo` (rejeita
   BFG/squash-to-genesis/shallow); backup antes; validação dupla; bypass owner do Ruleset.
4. **[[ADR-316]]** — Aceite de risco de metadados GitHub imutáveis (855 PRs/issues/logs).
   Triagem T1/T2/T3 + **cláusula de incompatibilidade lógica**: se o owner exigir
   zero-risco em metadados, o flip in-place reabre para repo novo.
5. **[[ADR-317]]** — Identidade de autoria no mailmap público (Gmail em 813 commits;
   tratamento de co-authors).
6. **[[ADR-318]]** — Fronteira EN-apresentação vs. PT-BR-vault. Ativa a cláusula §11
   (Pós-launch) já escrita em [[PLAN-i18n]] (sem emenda de [[ADR-130]]); confirma pt-PT fora.
7. **[[ADR-319]]** — Contrato de gates anti-regressão PII + sigilo (contrato negativo
   permanente + enforcement). Não owner-gated.
8. **[[ADR-320]]** — Hardening CI/CD + paridade estrutural do `EXEMPLO` sintético
   (invariante "zero seção removida, só dados sintéticos"). Não owner-gated.

**Verificar ID livre antes do push** — máximo atual é ADR-312; sessão longa criando ADR
pode colidir. Refetch de `docs/adr/` imediatamente antes de `git push`; reservar a faixa
313–320 cedo via PR `Proposto`.

## Critério de aceite (G0)

- **8 arquivos** `docs/adr/31{3..9}-<slug>.md` + `docs/adr/320-<slug>.md`, um conceito
  por arquivo, cada um ≤150 linhas ([[ADR-182]]; split se estourar).
- Frontmatter válido (`note-adr.schema.json`): `id: ADR-NNN`, `type: adr`, `title`,
  `status: Proposto`, `date` (ISO com aspas), tags hierárquicas. `size_lines` coerente.
- Cada ADR owner-gated (313–318) contém **decisão textual assinada do owner** OU, para
  [[ADR-316]], o aceite de risco de metadados assinado **OU** a restrição in-place
  reaberta para repo novo (cláusula de incompatibilidade lógica).
- ADRs não owner-gated (319, 320) fechadas pela síntese `senior-cto`.
- Wikilinks resolvem: os 8 `adrs_canonical` do [[PLAN-public-release]] deixam de ser
  dangling — `python3 dev/check_doc_links.py` verde.
- Anchors históricos + slug corretos — `python3 dev/check_adr_anchors.py` verde.
- Índice regenerado: `python3 dev/build_doc_index.py` mostra as 8 ADRs no
  [ADR_INDEX](../../../_MOC/_generated/ADR_INDEX.md) sob `Proposto`; `--check` verde.
- IDs sem colisão (`grep -l "^id: ADR-31[3-9]\|^id: ADR-320" docs/adr/` = 8 hits, um por ID).

## Rollback

**Docs-only — mergeia sem CI** (diff exclusivo em `docs/adr/**` + `docs/plan/**` +
`_generated/`; gate de PII/paths/commit-msg do `pre-commit` continua obrigatório).
Rollback é `git revert` do PR: ADR `Proposto` não altera runtime nem código. Se uma
decisão do owner mudar após o merge, emendar a ADR (`## Emenda ... YYYY-MM-DD` +
`amended_at` no frontmatter, padrão ADR-027) em vez de reescrever histórico.

## Referências

- Plano-mãe: [[PLAN-public-release]] §"ADRs `Proposto` (gate G0)".
- Decisões travadas: [[ADR-313]] · [[ADR-314]] · [[ADR-315]] · [[ADR-316]] · [[ADR-317]] ·
  [[ADR-318]] · [[ADR-319]] · [[ADR-320]].
- Pré-condições de W0 paralelas: [[A34.l2]] (backup mirror off-site) · [[A34.l3]]
  (confirmar rotação Fernet).
- Reconciliação de fronteira de idioma: [[ADR-130]] ([[PLAN-i18n]]).
- Vocabulário canônico substituto de atribuição metodológica: [[ADR-183]].
- Anexo de auditoria (fonte mascarada dos achados): [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
- Protocolo de ADR atômica: CLAUDE.md §"ADRs → notas atômicas em `docs/adr/`" ([[ADR-182]]).

## Owner

Agente da lane redige as 8 ADRs; **decisão de cada questão owner-gated é do owner** e
deve estar textual no corpo antes de fechar G0. Gate bloqueia TODA execução W1+.
