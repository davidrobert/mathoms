---
id: ADR-201
type: adr
title: "Persona do planejador como rules-as-code — `config/agents/planner_persona.md`"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-199]]"
  - "[[ADR-200]]"
  - "[[ADR-202]]"
  - "[[ADR-207]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 201"
  - "Persona planner rules as code"
  - "Planner persona versionada"
tags:
  - area/llm
  - area/methodology
  - area/pipeline
  - phase/a11
  - status/decidido
  - type/adr
---

# ADR-201 — Persona do planejador como rules-as-code — `config/agents/planner_persona.md`

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

> **Nota de estado (audit r6, 2026-07-03):** os 3 gates de D2/D3 —
> `docs/_schemas/persona.schema.json`, hook `dev/check_persona_version.py`
> e auto-compute do `persona_hash` no `dev/build_doc_index.py` — **não
> foram implementados** (o frontmatter da persona ainda carrega
> `persona_hash: "PENDING_AUTO_GENERATE"`); o hash é computado em
> **runtime** (`backend/app/services/parecer_orchestrator.py` /
> `planner_review_persistence.py`). O frontmatter real de
> `config/agents/planner_persona.md` usa `type: agent_persona` (não
> `type: persona`) e `version` semver (`"1.1.0"`), não int.

## Contexto

- O parecer LLM precisa de **postura fiduciária explícita**: metodologias de referência (Perini/Cerbasi/AUVP), tom (orientativo, não prescritivo), restrições (sigilo §13 — não citar nomes de metodologistas em output), ordenação de prioridades (P0 com cap, confiança declarada). Sem persona codificada, cada execução LLM produz drift de tom; cada provider/modelo novo exige re-tuning manual.
- [[ADR-143]] estabelece o princípio **methodology = code**: regras universais de produto vivem em docstrings co-localizados com o código enforcer + ADR canônica capturando o "porquê". A persona do planejador é uma extensão direta — não é metadado de prompt, é regra de produto que orienta como o LLM raciocina sobre dados do cliente.
- Hoje `.claude/agents/financial-planner.md` contém briefing do subagent usado em dev-time (revisão de features, co-design). Não há equivalente para runtime (stage LLM). Sem separação, ou (a) duplica conteúdo entre 2 arquivos com drift garantido, ou (b) carrega dev-context (BACKLOG, ADRs em voo) pro runtime do stage — overhead + leak de contexto interno pro prompt.
- Plano canônico: `docs/plan/PLANNER_REVIEW/_README.md` §"Ato 2" especifica persona como rules-as-code com frontmatter versionado + hash SHA-256 registrado no aggregate (auditoria).

## Alternativas consideradas

1. **Persona embutida no system prompt Python.** Hardcode em `pipeline/llm/prompts/parecer_planejador.py`. Pró: zero arquivo de config. Contra: viola [[ADR-143]]; tunning de persona = PR de código; impossível para `financial-planner` (subagent ou humano CFP) editar persona sem dependência de eng; perde versionamento canônico. **Rejeitada.**
2. **Persona em JSON estruturado** (`config/agents/planner_persona.json`). Pró: schema validation trivial. Contra: persona é texto prosa (instruções para LLM); JSON força escape de quebras de linha e perde legibilidade; não há benefício real de structured data para essa finalidade. **Rejeitada.**
3. **Persona em YAML com campo `instructions: |`** (block scalar). Pró: tipado, parseável. Contra: prosa longa em YAML é desconfortável; perde realce sintático Markdown que o editor humano espera; mistura semântica (frontmatter YAML + corpo YAML escapado). **Rejeitada.**
4. **Persona em Markdown com frontmatter YAML** — `config/agents/planner_persona.md`. Pró: prosa natural; frontmatter para metadata estruturada (`id`, `version`, `methodology_anchors`); paridade com pattern de ADRs (`docs/adr/*.md`); editor experience perfeito; hashing SHA-256 trivial. Contra: novo padrão de arquivo em `config/` (que historicamente era JSON/YAML). Aceito — pattern já existe em `config/agents/financial-planner.md` (dev-time briefing). **Aceita.**

## Decisão

Adotar **persona em Markdown com frontmatter YAML** em `config/agents/planner_persona.md`, versionada, hash registrado no aggregate.

### D1. Estrutura do arquivo

```markdown
---
id: planner-persona
type: persona
version: 1
persona_hash: <SHA-256 do corpo após frontmatter>   # auto-gerado
methodology_anchors:
  - perini
  - cerbasi
  - auvp
status: Proposto
date: "2026-05-13"
---

# Persona — Planejador Financeiro

Você é um planejador financeiro brasileiro com 15 anos de experiência.
Sua postura é fiduciária e orientativa, nunca prescritiva.

## Metodologias de referência (uso interno — não cite nomes)

- **Perini (`ancora_metodologica: perini`)** — patrimônio gera renda passiva
  ≥ custo de vida; índice financeiro é o KPI mestre.
- **Cerbasi (`ancora_metodologica: cerbasi`)** — equilíbrio presente-futuro;
  preserva qualidade de vida hoje enquanto constrói para amanhã.
- **AUVP (`ancora_metodologica: auvp`)** — disciplina de aporte, alocação
  por classe de ativo, rebalanceamento periódico.
- **Convergência (`ancora_metodologica: convergencia`)** — recomendação
  apoia ≥ 2 metodologias simultaneamente.

## Sigilo §13 (não-negociável)

Você **nunca** menciona "Perini", "Cerbasi", "AUVP", "Bruno Perini",
"Gustavo Cerbasi", "Raul Sena" no body textual do parecer. Emite
`ancora_metodologica` como enum interno; a UI mapeia para `tema_canonico`
user-facing (ver [[ADR-207]]).

## Output (resumido — schema completo em [[ADR-202]])

Você produz exatamente: diagnóstico curto, 3-5 pontos fortes, até 12
riscos com severidade, sugestões em 3 horizontes (execução/tático/
estratégico), métricas-alvo, notas metodológicas, lista de campos que
você pediria se pudesse iterar ([[ADR-206]]).
```

### D2. Frontmatter obrigatório

- `id: planner-persona` (constante).
- `type: persona` (novo tipo, validado por `docs/_schemas/persona.schema.json`).
- `version: <int>` — bump na mudança que altera comportamento do LLM (não em correção tipográfica). Política de bump documentada na persona.
- `persona_hash: <SHA-256 do corpo>` — auto-computado pelo `dev/build_doc_index.py` (similar a `size_lines`). Persistido no aggregate `PlannerReview` ([[ADR-199]]) — auditoria total: "este parecer foi gerado sob persona hash `abc123...`".
- `methodology_anchors: [perini, cerbasi, auvp]` — enum interno (não user-facing). Cross-ref com [[ADR-207]] mapeamento.
- `status: Proposto|Decidido` — espelha lifecycle de ADR.
- `date: "YYYY-MM-DD"` — data da versão.

### D3. Mudança de persona = nova ADR + bump

- Persona é regra de produto auditável. Mudança que altera output do LLM (tom, prioridade, sigilo, novas metodologias) **exige nova ADR** com `supersedes: [[ADR-201]]` ou supersedure parcial.
- Bump de `version` sem ADR é proibido. Hook pre-commit `check_persona_version` valida que diff em `config/agents/planner_persona.md` (corpo, não frontmatter de metadata) acompanha bump + ADR.

### D4. Shim em `.claude/agents/financial-planner.md`

- `.claude/agents/financial-planner.md` (dev-time, subagent invocado em co-design) **passa a referenciar** `config/agents/planner_persona.md` como base canônica.
- Dev-time agent adiciona overlay: contexto de BACKLOG, ADRs em voo, protocolo de delegação CLAUDE.md. Esse overlay não viaja pro runtime do stage LLM (separação shell dev × shell runtime — risco CTO-G10 mitigado).
- Runtime (stage) carrega `planner_persona.md` puro, injeta só `(persona + manifest_exec_context + tools)` como prompt.

### D5. Sigilo §13 — pré-condição da persona

Persona instrui LLM a:
1. **Nunca** citar nomes de metodologistas no body textual.
2. Emitir `ancora_metodologica` como enum interno: `perini | cerbasi | auvp | convergencia`.
3. Validar autoavaliação: se output gerado contém token proibido, marcar para retry (caught no `parecer_generator.py` via regex anti-token; ver [[ADR-207]]).

Lista de tokens proibidos versionada na própria persona (próximas releases podem ampliar). Validador `dev/check_sigilo_terms.py` complementa em CI sobre componentes React renderizando output.

### D6. Auditoria do hash

Aggregate `PlannerReview` persiste `persona_hash` no `_meta` do artifact JSONB. Re-geração de parecer:
- Mesma persona (hash idêntico) + mesmo E5 + mesmo manifest = cache hit ([[ADR-144]] pattern).
- Persona diferente (bump version) = cache miss, regeneração forçada.

Permite responder em incidente: "qual versão da persona produziu o parecer X que o cliente Y contestou em DD/MM?" via SELECT no `pipeline_artifacts._meta.persona_hash`.

## Consequências

**Positivas:**
- Persona evolui sem mudança de código Python — PR docs-only.
- Auditabilidade total: cada parecer rastreia versão exata da persona.
- Separation of concerns: dev-time agent ≠ runtime persona; sem cross-contamination.
- Pattern reusável para outras personas LLM futuras (ex.: persona de classificação, persona de cross-validation).
- Cumprimento explícito de [[ADR-143]] estendendo methodology-as-code ao domínio LLM.

**Negativas / trade-offs aceitos:**
- Mais um arquivo de config no repo; mais um schema (`persona.schema.json`).
- Persona em Markdown não é "tipo seguro" no sentido strict — depende do LLM seguir as instruções. Mitigação: validador anti-token (defesa em profundidade); golden estrutural mensal com modelo real ([[ADR-205]] Ato 6).
- Versionamento manual: dev precisa lembrar de bump na mudança comportamental. Mitigação: hook pre-commit.

**Riscos mitigados:**
- **Persona drift entre versões do modelo** (CTO-G1): hash + golden mensal detectam.
- **Dual-shell persona dev × runtime** (CTO-G10): separação explícita; runtime não carrega overlay.
- **Sigilo §13 vazando** (PD risk crítico): persona é primeira linha de defesa; validador é segunda; CI check é terceira.

## Implementação

- **Track(s) do plano:** T-08 (`planner-persona-rules-as-code`).
- **Files touched (Ato 2):**
  - `config/agents/planner_persona.md` — persona
  - `docs/_schemas/persona.schema.json` — validator de frontmatter
  - `.claude/agents/financial-planner.md` — atualizado para referenciar persona canônica
  - `dev/build_doc_index.py` — auto-compute `persona_hash`
  - `dev/check_persona_version.py` — hook pre-commit bump-on-change
- **Critério de aceite:**
  - Persona Markdown valida contra `persona.schema.json`.
  - `persona_hash` reproduz consistentemente (mesmo corpo → mesmo hash).
  - Dev-time agent shim valida que apontar para persona canônica.
- **Gates CI:** `validate-persona-frontmatter`, `check-persona-version-bump`, `dev/check_sigilo_terms.py` (defesa secundária).

**Decisão pendente para outros especialistas:**
- **Conteúdo concreto da persona V1** — `financial-planner` é o autor; co-design no Ato 2.
- **Mapeamento `ancora_metodologica → tema_canonico`** (1:N) — fechado em [[ADR-207]] co-design.
