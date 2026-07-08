---
id: A34.l12
type: lane
title: "Redigir/split COMPETITIVE_PIERRE + prompts de produto + pricing"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: redact-split-competitive-ip
adrs: ["[[ADR-314]]"]
depends_on: ["[[A34.l5]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/gtm
  - area/seguranca
---

# A34.l12 — `redact-split-competitive-ip` (W1 · Saneamento)

## Problema

A auditoria de PII de 2026-07-08 mediu **dados pessoais**, não **IP competitivo
e sigilo metodológico** — que é um bloqueador de flip do domínio GTM tão forte
quanto a PII (só o `gtm-strategist` capturou; 4/5 agentes não). Publicar o
superset como está expõe o motor de negócio do Mathoms:

1. **Playbook competitivo `COMPETITIVE_PIERRE`** — [[PLAN-competitive-pierre]] e
   seus assets contêm tese competitiva, análise de fraqueza do concorrente,
   scorecard de ICP, matriz de capacidades do próprio produto e pricing. Isto é
   *como o Mathoms pensa em vencer*: publicar entrega o roadmap de resposta a um
   concorrente que o lê de graça. O anexo de auditoria também marca
   `docs/plan/COMPETITIVE_PIERRE/assets/3e-discovery-2026-05-23.md` com valores
   plausivelmente reais (tratado como PII pela [[A34.l9]]) — aqui o alvo é o **IP**,
   não os números.
2. **Prompts de produto** — `config/prompts/parecer_planejador.yaml` e
   `config/prompts/section_summaries.yaml` citam **Perini/Cerbasi/AUVP/Raul Sena
   nominalmente** (violação de sigilo metodológico de marca de terceiros sem
   licença) e encapsulam o encadeamento fino de regras que diferencia o parecer.
   O gate de sigilo estendido pela [[A34.l5]] detecta a atribuição nominal; esta
   lane resolve a exposição.
3. **Pricing concreto** — [[PLAN-report-premium]] e [[ADR-183]] carregam faixas/
   valores de pricing específicos que não devem ser públicos por default.

**Não publicar capability matrix do próprio produto** é regra de escopo de
[[ADR-314]]: superset público é código + docs de referência técnica, não o dossiê
estratégico-comercial.

## Escopo

Conforme decisão de escopo público de [[ADR-314]] (owner-gated no G0):

1. **`COMPETITIVE_PIERRE`** — mover o plano + assets para o repositório privado
   (fora do superset público) **OU** redigir in-body a tese competitiva, a análise
   de fraqueza, o pricing e o ICP scorecard, preservando `id`/filename/wikilinks
   (invariante `filename ≡ id ≡ wikilink-target`). Decisão do owner registrada em
   [[ADR-314]]; a recomendação leading é **mover para privado** (redação parcial
   ainda vaza a existência e a estrutura do playbook).
2. **Prompts de produto** (`parecer_planejador.yaml`, `section_summaries.yaml`) —
   **approach B recomendado**: split para submódulo privado / `.gitignore` no
   público / injeção em build-time (o público vê a interface do prompt, não o
   conteúdo). Alternativa: **genericizar** removendo atribuição nominal e o
   encadeamento fino de regras, substituindo por vocabulário canônico de [[ADR-183]]
   ("metodologia consagrada de planejamento patrimonial brasileiro"). A decisão de
   B vs. genericização é de [[ADR-314]].
3. **Pricing** — genericizar os valores concretos em [[PLAN-report-premium]] e
   [[ADR-183]] para **faixas** (ou remover), sem números específicos no público.

**Coordenação:** depende de [[A34.l5]] (gate de sigilo estendido ao superset) —
o gate verde é o critério de detecção que prova que a atribuição nominal e os
termos competitivos foram zerados. Anonimização in-body é ortogonal à [[A34.l9]]
(PII em docs): esta lane trata **IP/atribuição**, a [[A34.l9]] trata **dados
pessoais**; ambas tocam alguns dos mesmos arquivos e coordenam o path.

## Critério de aceite (verificável)

- **Superset público sem IP competitivo:** se `COMPETITIVE_PIERRE` foi movido,
  `git ls-files docs/plan/COMPETITIVE_PIERRE/` no superset público = vazio; se
  redigido, `git grep` por tese/pricing/ICP-scorecard não retorna conteúdo
  estratégico (revisão manual do `gtm-strategist`).
- **Zero atribuição nominal metodológica:** `git grep -Ei "(perini|cerbasi|auvp|
  raul sena|viver de renda)"` no superset público = vazio (alinha KR3 do plano).
- **Prompts:** conteúdo dos prompts de produto ausente do público (split/gitignore/
  build-time) OU genericizado sem atribuição nominal; o build ainda resolve o prompt
  em ambiente com o submódulo privado (verificar que o público não quebra por prompt
  faltante — degrada explicitamente, não com stack trace).
- **Pricing genericizado:** nenhum valor concreto de pricing em
  [[PLAN-report-premium]] / [[ADR-183]] no público (faixas ou remoção).
- **Gate de sigilo verde:** `dev/check_sigilo_terms.py` (estendido pela [[A34.l5]])
  passa VERDE no HEAD saneado.
- **Grafo intacto:** `check_doc_links` + `check_adr_anchors` verdes — mover/redigir
  não quebrou wikilinks nem âncoras ([[PLAN-launch-trust]] depende de ADRs vizinhas).

## Rollback

Toca **docs + config de prompts + possivelmente `.gitignore`/submódulo** — não
toca runtime de produto. **CI obrigatório** apenas se o split alterar como o
backend carrega os prompts (`config/prompts/*.yaml`); nesse caso rodar a suíte de
parecer (`backend/tests` do stage E6) para garantir que a injeção build-time não
regride o carregamento. Se a mudança for docs-only + genericização de YAML sem
mudar o loader, **mergeia sem CI** (docs-only por CLAUDE.md).

Rollback: reverter o PR restaura os arquivos redigidos/movidos a partir do backup
off-site ([[A34.l2]]) — nada é destrutivo no HEAD além de mover paths, e o rewrite
de histórico (W3) só ocorre depois. Se `COMPETITIVE_PIERRE` foi movido para privado,
o conteúdo permanece íntegro no repositório privado; o rollback é `git mv` reverso.

## Owner

Decisão de escopo (mover vs. redigir, B vs. genericizar) é **owner-gated** em
[[ADR-314]] — não abrir PR antes do merge de G0. Execução da lane após decisão:
agente + validação do `gtm-strategist` (IP competitivo) no PR.

## Referências

- Escopo público: [[ADR-314]] · vocabulário canônico substituto: [[ADR-183]].
- Gate de sigilo (dependência): [[A34.l5]] · anonimização de PII em docs: [[A34.l9]].
- Plano: [[PLAN-public-release]] · anexo de auditoria §1.6 (COMPETITIVE_PIERRE assets),
  §5 (superfície) — [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
- Alvos: [[PLAN-competitive-pierre]] · [[PLAN-report-premium]] ·
  `config/prompts/parecer_planejador.yaml` · `config/prompts/section_summaries.yaml`.
- Reconciliação de grafo: [[PLAN-launch-trust]] (ADRs vizinhas).
