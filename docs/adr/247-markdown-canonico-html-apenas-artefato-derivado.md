---
id: ADR-247
type: adr
title: "Documentação canônica permanece em Markdown; HTML apenas como artefato derivado/efêmero"
status: Decidido
phase: A11
date: "2026-05-22"
relates_to:
  - "[[ADR-182]]"
  - "[[ADR-129]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 247"
  - "markdown vs html"
  - "html docs migration rejected"
  - "vault format policy"
tags:
  - area/docs
  - area/process
  - phase/a11
  - status/decidido
  - type/adr
---

# ADR-247 — Documentação canônica permanece em Markdown; HTML apenas como artefato derivado

## Contexto

Artigo da Anthropic [*Using Claude Code: The Unreasonable Effectiveness of
HTML*](https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html)
argumenta que HTML > Markdown como formato para Claude Code porque
permite tabelas ricas, CSS, SVG inline, sliders/knobs interativos,
botões "copy as JSON" e layouts espaciais. Levantada a hipótese de
**migrar a vault `docs/` (755 arquivos `.md`) para HTML**.

Estado atual da vault (pós-[[ADR-182]] DOC_REORG, concluído 2026-05-07):

- 755 arquivos `.md`, organizados como vault Obsidian (PARA/Zettelkasten/LYT).
- Frontmatter YAML validado por JSON Schema (`docs/_schemas/*.schema.json`).
- Wikilinks `[[ADR-NNN]]`, graph view, backlinks, full-text search nativos.
- Índices auto-gerados por `dev/build_doc_index.py` (`CONTEXT_INDEX`,
  `ADR_INDEX`, `SPRINT_CURRENT`).
- 6 gates de CI: `validate_frontmatter.py`, `check_doc_filename_id.py`,
  `check_doc_links.py`, `check_adr_anchors.py`, `build_doc_index.py
  --check`, `validate_adr_format.py`.
- 175 ADRs atômicas; shims (`DECISIONS.md`, `BACKLOG.md`, `CHANGELOG.md`)
  preservam âncoras históricas em PRs antigos.

Consumidores: agentes LLM (via Read/Grep, formato MD tokeneficiente),
humanos no Obsidian (graph + backlinks), PRs no GitHub (render nativo).

## Decisão

**Vault `docs/` permanece 100% Markdown.** Invariante de formato
mantida. HTML é permitido **exclusivamente** como artefato
derivado/efêmero — nunca como substituto de `.md` canônico.

## Rationale

A tese do artigo aplica-se a **artefatos efêmeros gerados pelo Claude**
(specs ad-hoc, code reviews descartáveis, dashboards one-off,
protótipos). A vault `docs/` é **conhecimento durável versionado em
git** — ADRs imutáveis, planos canônicos, runbooks, sprints declarativos.
Tratar os dois como o mesmo formato é category mistake.

Pontos concretos contra migração total:

1. **Token cost para agentes LLM.** HTML semântico custa 1.5–2.5× tokens
   vs MD equivalente (tags fechantes, atributos, boilerplate). Ataca
   diretamente o orçamento de context window que `CONTEXT_INDEX` já
   gerencia com cuidado.
2. **Obsidian quebra catastroficamente.** Graph view, backlinks
   plugin-driven, Dataview, tags hierárquicas (`type/adr`, `status/decidido`),
   wikilinks `[[ADR-NNN]]` — toda a infra editorial pós-[[ADR-182]] morre.
3. **Diff em PR review.** Mudança semântica de 1 linha em ADR vira 200
   linhas de ruído de tags/CSS em HTML. Review de mudança editorial fica
   3–5× mais lento. Os 175 ADRs do DOC_REORG só foram viáveis em MD.
4. **Wikilinks são refactor-friendly.** `[[ADR-090]]` resolve por id;
   rename de arquivo é grep+replace. `<a href="adr/090-slug.html">`
   acopla path → rename quebra N referências.
5. **`build_doc_index.py` parseia YAML rápido.** DOM-parsing 755 HTMLs
   com BeautifulSoup é 5–10× mais lento e introduz fragilidade (HTML
   mal-formado, encoding, whitespace). Hot-path no CI.
6. **`cat` em terminal/IDE.** Agente LLM e dev consomem docs no pipe.
   `cat 090.md` é legível; `cat 090.html` é ruído de tags.
7. **Render nativo em GitHub.** Markdown renderiza em PR/file view;
   HTML aparece como código fonte.
8. **Two-way interaction em ADR `Decidido`** é antipadrão. ADR é registro
   imutável; sliders e knobs não cabem em decisão arquitetural.
9. **Custo de migração.** Reescrever 755 arquivos + 6 gates de CI +
   janela de 4–6 semanas com risco de regressão silenciosa em âncoras
   históricas. RICE colapsa (Reach = 1 + LLM; Impact baixo; Confidence
   baixa; Effort alto). Não há sinal documentado de que MD bloqueia
   algum JTBD da doc hoje.

## Política operacional

**Markdown é source-of-truth.** `docs/**/*.md` é a vault canônica;
gates atuais permanecem ativos.

**HTML permitido apenas em:**

- `_scratch/<slug>.html` — exploratório, gitignored, descartável.
- `docs/plan/<X>/assets/<nome>.html` — anexo a um plano específico,
  não-canônico, ignorado por gates de doc (`check_doc_links`,
  `validate_frontmatter`).
- Rotas internas em `ops.mathoms.ai` (console interno,
  [docs/plan/INTERNAL_ADMIN/_README.md](../plan/INTERNAL_ADMIN/_README.md))
  — dashboards persistentes, código em `frontend/`/`backend/`, não doc.
- Relatório do produto (`/reports/[id]`) — já é HTML/React via
  [[ADR-129]]; fora do escopo desta ADR.

**Casos de uso legítimos para HTML derivado:**

- Dashboard interativo dos 138 findings do PLATFORM_REVIEW (filtro por
  wave/severidade/agente).
- Comparativo de approach em ADR `Proposto` (matriz de critérios
  colorida) anexado como asset.
- Relatórios sintéticos de revisão multi-agente.
- Mockups de UX (já vivem em `frontend/`).

**Proibido:**

- HTML em `docs/**` substituindo `.md` canônico.
- HTML em `docs/adr/`, `docs/sprint/`, `docs/plan/<X>/_README.md`,
  `docs/reference/`, `docs/agent_prompts/track_*.md` — todos `.md`.
- HTML referenciado como fonte primária em wikilinks de outros docs
  canônicos.

## Consequências

- Sem migração; sem reescrita de gates; sem janela de drift.
- Tese do artigo permanece explorável via artefato derivado — reversível,
  baixo custo, sem tocar `docs/`.
- Próximo agente que cogitar migrar tem rationale gravado; não-decisão
  vira não-debate.

## Alternativas consideradas

| Alternativa | Veredicto |
|---|---|
| Migração total MD → HTML | **Rejeitada** — custo 2–3 sprints + quebra Obsidian + infla tokens + diff polution. |
| Híbrido seletivo (esta ADR) | **Aceita** — MD canônico + HTML como artefato derivado. Reversível, low cost. |
| Status quo puro (sem permitir HTML em lugar algum) | Rejeitada — descarta valor real do artigo em casos como dashboard de 138 findings. |

## Referências

- Artigo Anthropic — *Using Claude Code: The Unreasonable Effectiveness
  of HTML*: https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html
- [[ADR-182]] — DOC_REORG (formato atual da vault).
- [[ADR-129]] — relatório React único renderer (HTML como produto, não
  como doc).
- Política reflexa em `CLAUDE.md` §"Planos → `docs/`" subseção
  "HTML: apenas como artefato derivado".
