---
id: ADR-234
type: adr
title: "Adicionar `paused` ao vocabulário de `sprint_status` (4º valor)"
status: Proposto
phase: A15
date: "2026-05-20"
relates_to:
  - "[[ADR-182]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 234"
  - "sprint_status paused"
  - "Sprint pausada"
tags:
  - area/docs
  - area/methodology
  - phase/a15
  - status/proposto
  - type/adr
---

## Contexto

[[ADR-182]] (DOC_REORG · F1) estabeleceu o contrato declarativo de
sprint corrente: o campo `sprint_status` no frontmatter de cada
`docs/sprint/<X>/_README.md` é a fonte única, validado por
`dev/build_doc_index.py` com vocabulário **fechado** de 3 valores:

```python
_VALID_SPRINT_STATUSES: frozenset[str] = frozenset({"current", "candidate", "done"})
```

A semântica é estritamente sequencial:

- `current` — sprint corrente única, lanes aparecem em `SPRINT_CURRENT.md`.
- `candidate` — próxima sprint, abre quando `current` fecha.
- `done` — encerrada com escopo total entregue.

Sprint A15 (FU-3 imóvel financiado, [[ADR-227]]) tem 2 bugs silenciosos
em produção que precisam ser priorizados sobre A11 (Platform review,
6 ondas, 9 itens abertos em W3-W6) e A12 (Categorization learning loop,
P4 condicional + gate dogfood pendente). Decisão de produto 2026-05-20:
A15 vira `current`, A11 e A12 cedem prioridade.

O vocabulário atual não comporta essa transição honestamente:

- **`done`** mente — A11 tem 9 itens abertos, A12 tem 5. Marcar
  `done` perde rastreabilidade do débito e quebra o invariante "done =
  escopo entregue".
- **`candidate`** colide — só uma sprint pode ser próxima; A12 já está
  lá com débito conhecido.
- **Mover itens abertos para A16/A17** — viável mas custa ~2h de
  curadoria de docs por sprint pausada, e fragmenta o contexto: lanes
  do W3 de A11 ficam num MOC sem o resto do platform review.

## Decisão

Adicionar **`paused`** como 4º valor do vocabulário `sprint_status`.

```python
_VALID_SPRINT_STATUSES: frozenset[str] = frozenset({"current", "candidate", "done", "paused"})
```

### Semântica

`paused` = sprint com escopo aberto cujo trabalho foi suspenso para
ceder prioridade. Diferente de `done` (escopo entregue) e diferente de
`candidate` (próxima na fila). Pode coexistir N sprints em `paused`
simultaneamente — não há restrição de unicidade.

### Invariantes preservados

- **`current` continua único** — validador em `validate_sprint_statuses`
  (`build_doc_index.py:245`) já enforça `len(current_sprints) > 1` é erro.
- **Renderer ignora** — `_sprint_current_renderer._declared_current`
  filtra apenas `status == "current"` (linha 96); sprints `paused` não
  aparecem em `SPRINT_CURRENT.md`. Sem mudança no renderer.
- **Sem JSON Schema para `type: moc`** — não há `docs/_schemas/note-moc.schema.json`,
  então a mudança fica isolada em 1 linha de Python.

### Transição operacional

Para mover sprint de `current`/`candidate` → `paused`:

1. Editar frontmatter do `_README.md` do sprint pausado.
2. Documentar **motivo** + **link reverso** ("retomada quando A15 fechar")
   no corpo do MOC.
3. Promover outra sprint a `current` no mesmo commit.
4. Regenerar `_generated/`.

Sprints `paused` aparecem em [`docs/_MOC/SPRINTS-active.md`](../_MOC/SPRINTS-active.md)
seção "Sprints pausadas" (criada nesta mesma flip), com link para o
plano canônico e nota do trabalho residual.

## Alternativas consideradas

- **A. Marcar `done` mesmo com débito** — rejeitada: mente schema,
  quebra invariante "done = escopo entregue", futuro leitor não sabe que
  faltou trabalho.
- **B. Mover lanes abertas para nova sprint (A16/A17)** — rejeitada
  como default: custa ~4h de curadoria total e fragmenta contexto
  (plano canônico do platform review aponta para A11; mover lanes
  exige re-link). Continua válido como caminho premium quando faz
  sentido reorganizar; `paused` é o caminho leve quando não faz.
- **C. Quebrar invariante de unicidade de `current`** — rejeitada:
  perde o sinal "qual sprint orquestra capacidade agora" e quebra
  pickup automático em `SPRINT_CURRENT.md`.
- **D. Manter A11 como `current`, A15 vira `candidate` em paralelo** —
  rejeitada: quebra protocolo de pickup (lanes ready vivem em
  `SPRINT_CURRENT` do current, não candidate) e força o agente a ignorar
  a fila.

## Consequências

**Positivas:**

- Permite priorização honesta sem perder rastreabilidade de débito.
- Mudança cirúrgica (1 linha de Python, 1 ADR, 1 update narrativo).
- Retomada barata: flip `paused → current` quando A15 fechar.

**Negativas:**

- Adiciona estado ao schema. Risco de uso indisciplinado ("pausa
  qualquer sprint que dê trabalho"). Mitigação: documentar em
  SPRINTS-active.md que `paused` exige motivo explícito + link de
  retomada.
- Sprint `paused` sem retomada vira lixo. Mitigação: revisão trimestral
  (PM) — sprint `paused` > 90d sem progresso vira `done` com débito
  migrado.

## Validação

- `python3 dev/build_doc_index.py --check` aceita `paused` sem erro.
- `python3 dev/validate_frontmatter.py` continua passando (não há
  schema MOC que restrinja sprint_status).
- `SPRINT_CURRENT.md` continua mostrando apenas o `current`.
- Nenhum gate de CI quebra.

## Referências

- [[ADR-182]] — DOC_REORG canônica.
- `dev/build_doc_index.py:23` — único lugar de enforcement.
- `dev/_sprint_current_renderer.py:94-96` — renderer (sem mudança).
- `docs/_MOC/SPRINTS-active.md:11` — contrato narrativo (atualizado).
