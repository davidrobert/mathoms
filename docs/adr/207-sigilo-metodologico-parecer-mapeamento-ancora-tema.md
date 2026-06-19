---
id: ADR-207
type: adr
title: "Sigilo metodológico no parecer LLM — mapeamento `ancora_metodologica` → `tema_canonico`"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-199]]"
  - "[[ADR-201]]"
  - "[[ADR-202]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 207"
  - "Sigilo §13 parecer"
  - "Ancora metodologica tema canonico"
tags:
  - area/llm
  - area/methodology
  - area/copy
  - area/frontend
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-207 — Sigilo metodológico no parecer LLM — mapeamento `ancora_metodologica` → `tema_canonico`

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- COPY_GUIDELINES §13 (sigilo metodológico) estabelece: **nomes de metodologistas** (Bruno Perini, Gustavo Cerbasi, Raul Sena/AUVP) e **siglas** (AUVP) **não aparecem em copy user-facing** (relatório, app, PDF, landing). O Mathoms é "metodológico-auditável" sem expor seu lineage editorial — vantagem competitiva e proteção legal (cita autor sem licença = risco).
- Parecer LLM ([[ADR-199]]) é o caminho mais arriscado para vazamento: LLM treinado em corpus público "sabe" os nomes e tende a citá-los (`"Conforme Perini, ..."`). Sem defesa em profundidade, vaza no body do parecer e quebra sigilo §13.
- Risco crítico PD1 do plano canônico: "Sigilo §13 vazando — LLM cita Perini/Cerbasi/AUVP no output e vaza pra UI". Categorizado como **bloqueador de shipping pra cliente pagante**.
- [[ADR-143]] (rules-as-code) estabelece: regras de produto vivem co-localizadas com enforcer + ADR canônica. Sigilo §13 é uma regra de produto; merece tratamento formal.

## Alternativas consideradas

1. **Confiar só na persona** ([[ADR-201]]) instruindo LLM a não citar nomes. Pró: simples. Contra: LLM ocasionalmente disobedece (~1-3% mesmo com persona forte); modelos novos podem regredir; single point of failure. **Rejeitada.**
2. **Confiar só em validador post-LLM** (regex bloqueia termos proibidos no output). Pró: defesa robusta. Contra: rejeita output válido por falso positivo (palavra "perini" em contexto não-metodologista?); retry custa $; sem schema duplo, frontend ainda recebe enums internos misturados com user-facing. **Rejeitada parcialmente** — usar como camada 2.
3. **Schema duplo: LLM emite enum interno `ancora_metodologica`, UI traduz para enum user-facing `tema_canonico`.** Pró: separação clara de concerns; LLM nunca emite string user-facing diretamente; mapeamento auditável; defesa em profundidade. Contra: precisa de mapeamento explícito (1:N possível) decidido com `financial-planner`. **Aceita.**
4. **Schema duplo + validador + CI check** (defense in depth: persona + schema + regex + CI). Pró: máxima robustez. Contra: overhead de manutenção. **Aceita** — vazamento é evento de quebra de produto, vale o overhead.

## Decisão

Adotar **schema duplo (enum interno + enum user-facing)** com **mapeamento 1:N**, validador anti-token no body textual, e **CI check** sobre componentes React. Estende COPY_GUIDELINES §13 ao domínio LLM.

### D1. Schema duplo

**Enum interno (LLM emite):**
- Campo: `ancora_metodologica` (em cada sugestão, risco, nota).
- Valores: `perini | cerbasi | auvp | convergencia` (4 valores fechados).
- Persistido no `pipeline_artifacts._meta` e no DTO da API HTTP.
- **Nunca renderizado em UI** — frontend usa apenas para mapping.

**Enum user-facing (UI exibe):**
- Campo derivado: `tema_canonico` (9 valores fechados, decididos no plano D-0.1).
- Valores: `Proteção | Alocação | Renda passiva | Liquidez | Custo tributário | Saúde de balanço | Diagnóstico de dados | Equilíbrio presente-futuro | Convergência metodológica`.
- Computado no frontend a partir de `ancora_metodologica + contexto`.

### D2. Mapeamento 1:N (1 âncora → tema dependendo do contexto)

Mapeamento depende do **tema do conteúdo**, não só da âncora. Tabela de referência (fechada por `financial-planner` no Ato 2):

| `ancora_metodologica` | Possíveis `tema_canonico` | Critério |
|---|---|---|
| `perini` | Renda passiva · Alocação · Saúde de balanço · Diagnóstico de dados | Foco em índice financeiro e renda passiva → Renda passiva; foco em alocação → Alocação; foco em valuation/cálculo → Diagnóstico de dados. |
| `cerbasi` | Equilíbrio presente-futuro · Liquidez · Proteção · Custo tributário | Foco em equilíbrio temporal → Equilíbrio presente-futuro; reserva → Liquidez; proteção familiar → Proteção. |
| `auvp` | Alocação · Saúde de balanço · Custo tributário · Diagnóstico de dados | Foco em disciplina/aporte/rebalanceamento → Alocação; balanço → Saúde de balanço. |
| `convergencia` | Convergência metodológica | Sempre — quando ≥ 2 metodologias suportam a sugestão. |

Mapping resolver: `frontend/src/lib/methodology_mapping.ts` (TypeScript) cruzado por `pipeline/llm/methodology_mapping.py` (Python, para validação em backend antes de serializar). **Single source of truth:** `config/methodology_mapping.yaml` (gerado para os dois lados via codegen — paridade [[ADR-076]] pattern). Bump exige `financial-planner` review.

### D3. Defesa em profundidade — 3 camadas

**Camada 1 — Persona ([[ADR-201]]):**
- Persona instrui LLM: "Nunca cite 'Perini', 'Cerbasi', 'AUVP', 'Bruno Perini', 'Gustavo Cerbasi', 'Raul Sena' no body textual. Emita `ancora_metodologica` (enum interno) para indicar metodologia."
- Lista de termos proibidos versionada na própria persona.

**Camada 2 — Validador anti-token no schema ([[ADR-202]]):**
- `pipeline/domain/services/parecer_generator.py` aplica regex sobre strings em `diagnostico`, `pontos_fortes[].descricao`, `riscos[].descricao`, `sugestoes_*[].acao`, `notas_metodologicas[]`.
- Regex: `/\b(perini|cerbasi|auvp|bruno\s+perini|gustavo\s+cerbasi|raul\s+sena)\b/i` (word boundary, case-insensitive).
- Hit → `status="needs_review"`, retry 1× com prompt reforçado citando o problema; 2ª falha → artifact não-publicado + alerta operacional.
- **Falso positivo aceito como custo:** se cliente literalmente se chama "Bruno Perini", parecer falha — caso raríssimo, vale a robustez.

**Camada 3 — CI check sobre componentes React (`dev/check_sigilo_terms.py`):**
- Script novo (Ato 5 do plano) lê `frontend/src/components/report/sections/SParecer*.tsx` e `frontend/src/lib/methodology_mapping.ts`.
- Rejeita literais string contendo termos proibidos. Hardcoded fence; humano não consegue acidentalmente colar "Perini" em copy.
- Roda em pre-commit + CI.

### D4. Renderização final — frontend resolve mapping

- API HTTP retorna `ancora_metodologica` no DTO ([[ADR-202]]).
- Frontend imediatamente mapeia para `tema_canonico` via `methodology_mapping.ts` antes de renderizar.
- **Em nenhum ponto** o frontend renderiza `ancora_metodologica` raw — exceto em modo dev (`?dev=1`) atrás de feature flag interna para debug.

### D5. PDF (Playwright) usa mesma transformação

- PDF é renderizado sobre a rota React `/reports/[id]` ([[ADR-129]]).
- Reusa `methodology_mapping.ts` automaticamente. Zero código novo no `pdf_renderer.py`.

### D6. Persistência e auditoria

- `ancora_metodologica` persiste no `pipeline_artifacts` (auditoria interna: "qual metodologia o LLM usou").
- `tema_canonico` **não** persiste — é derivado em runtime. Garante que mudança no mapping não exige re-gen de artifact.
- Bump de mapping (revisão `financial-planner`) re-renderiza UI sem tocar artifacts; histórico preservado.

## Consequências

**Positivas:**
- Defesa em profundidade: 3 camadas independentes; falha em qualquer 1 não vaza.
- Sigilo §13 fica codificado (rules-as-code [[ADR-143]]), não em documentação informal.
- Mapping evolui sem regenerar pareceres: mudança de tema sem custo LLM.
- Persistência de `ancora_metodologica` permite análise interna sem expor cliente.
- Pattern reusável: outras features LLM futuras seguem o mesmo schema duplo.

**Negativas / trade-offs aceitos:**
- 3 camadas a manter (persona + validator + CI). Aceito — risco de vazamento é existencial para o produto.
- Mapping em YAML + codegen para Python/TS adiciona infra. Aceito — paridade frontend/backend é não-negociável.
- Falsos positivos do regex (cliente "Perini Family") são possíveis — caso raríssimo, parecer falha gracefully com `needs_review`.
- Mapping 1:N exige decisão `financial-planner` por cada cell; tabela longa em [[ADR-201]] persona.

**Riscos mitigados:**
- **PD1 crítico (sigilo §13 vazando):** defesa em profundidade.
- **Modelo novo regride:** persona é primeira camada mas não única; validador pega.
- **Copy hardcoded acidental:** CI check pega antes de PR.
- **Vazamento via PDF:** PDF reusa render React, mesma defesa aplica.

## Implementação

- **Track(s) do plano:** estende T-08 (persona) + T-19/T-20 (componentes React) + T-22 (sigilo CI).
- **Files touched:**
  - `config/methodology_mapping.yaml` — single source of truth (Ato 2)
  - `pipeline/llm/methodology_mapping.py` — Python resolver (codegen)
  - `frontend/src/lib/methodology_mapping.ts` — TS resolver (codegen)
  - `pipeline/domain/services/parecer_generator.py` — validador anti-token (Ato 4)
  - `dev/check_sigilo_terms.py` — CI check (Ato 5)
  - `config/agents/planner_persona.md` — lista de termos proibidos (Ato 2)
- **Critério de aceite:**
  - Validador rejeita output com termo proibido (teste regression em fixtures sintéticas).
  - CI check rejeita `frontend/src/components/report/sections/SParecer*.tsx` se hardcodar termo proibido.
  - Mapping codegen produz Python e TS sincronizados em pre-commit.
  - 0 violações em PR de Ato 5 (componentes novos).
- **Gates CI:** `dev/check_sigilo_terms.py`, `pytest pipeline/domain/tests/test_anti_token_validator.py`, codegen check.

**Decisão pendente para outros especialistas:**
- **Tabela final de mapping** (4×N specifics) — `financial-planner` co-design no Ato 2.
- **Lista exata de termos proibidos** (incluir variações com hífen? acentos? plurais?) — `financial-planner` + COPY_GUIDELINES § revisão.
- **UX em caso de `needs_review`** (cliente premium vê "parecer indisponível" ou retry transparente?) — `product-designer` no Ato 5.
