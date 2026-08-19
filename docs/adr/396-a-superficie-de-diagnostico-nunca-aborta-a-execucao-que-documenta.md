---
id: ADR-396
type: adr
title: "A superfície de diagnóstico nunca aborta a execução que documenta"
status: Proposto
phase: r7/CTO-6
date: "2026-08-19"
relates_to:
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-165]]"
  - "[[ADR-272]]"
  - "[[ADR-273]]"
  - "[[ADR-309]]"
  - "[[ADR-371]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 396"
  - "diagnostico nao aborta"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/observabilidade
size_lines: 132
---

# ADR-396 — A superfície de diagnóstico nunca aborta a execução que documenta

**Status:** Proposto (r7/CTO-6) · **Data:** 2026-08-19

## Contexto

O run `140ac8d7` (dogfood, §r7) morreu no stage **12/18**. Não foi o caminho de
dados: foi o de **reporte**. Um produtor projetou o filename de um skip em
`review_reasons.document_id` — coluna com FK enforçada desde [[ADR-371]] — e o
`IntegrityError` do INSERT derrubou a execução inteira. Doze stages de custo,
zero relatório, e nenhum diagnóstico sobre o documento que a row existia para
tornar visível.

O #1535 fechou **a instância**: id não-resolvível vira `None` antes do INSERT.
A **classe** ficou aberta, e a proteção vivia como comentário acima da função.
Comentário não é gate.

Medido contra `origin/main` (`ab91f7ec`), três payloads de produtor ainda matam
o run — e **nenhum é largura de coluna**:

| Munição | Falha | Onde |
| --- | --- | --- |
| `offending_value` como `dict` numa coluna `Text` | `sqlite3.ProgrammingError: type 'dict' is not supported` | bind do driver |
| entrada `str` no lugar de objeto | `AttributeError: 'str' object has no attribute 'get'` | `_resolvable_document_ids` |
| `occurrence_count` não-numérico | `ValueError: invalid literal for int()` | `_apply_one_reason` |

O agravante é estrutural: **uma sessão** cobria a mutação do `stage_log`, o
`StageReview`, a transição `run.status = needs_review` e a materialização das
`review_reasons`, com um único `commit()` e **sem** `try/except` — enquanto o
commit de artefato imediatamente acima já era protegido (`pipeline_task.py`,
ramo `needs_review` do loop). O caminho analítico e o de controle
compartilhavam transação e domínio de falha.

A perda é **permanente**: `resume_pipeline_run` retoma de `FULL_ORDER[idx+1:]`,
então o stage pausado nunca re-executa e o diagnóstico não é re-materializado.
E o desfecho não é deadlock — `_on_pipeline_task_failure` marca o run `failed`
terminal.

## Decisão

**Escrita de diagnóstico nunca custa a execução.** Três camadas, nesta ordem.

**D1 — Plano de controle commita primeiro, sozinho e alto.** `stage_log`,
`StageReview` e `run.status`/`paused_at_stage` ficam numa sessão só, sem
`try/except`. Falhar aqui é falhar a execução e tem de estourar.

**D2 — `StageReview` é controle, não diagnóstico.** `resume_run` recusa a
retomada enquanto houver `StageReview` `pending`. Um `StageReview` fail-open que
falhasse deixaria `pending == 0` → o botão Retomar funciona → o pipeline avança
sobre output que ninguém revisou. Isso é **pior** que o abort: o abort é
ruidoso e recuperável por re-disparo; o bypass do gate de revisão é silencioso
e entrega artefato sobre dado não-revisado. O critério não é "destrava por
humano?" — é **"engana?"**. `StageReview` ausente engana; `review_reasons`
ausente, não.

**D3 — O sink de diagnóstico abre a própria sessão e não aceita `Session`.**
`record_review_reasons` vive em `backend/app/services/diagnostics/` e é
fail-open. Compartilhar transação deixa de ser proibido e passa a ser
impossível. A sessão é **uma só para o loop inteiro**: o bump por `(run, code)`
depende do autoflush, e é ele que torna o redelivery do Celery idempotente.

**D4 — Boundary tipado antes do INSERT.** DTO Pydantic normaliza tipo e largura.
Larguras vêm de `ReviewReason.__table__`, nunca transcritas — número mágico
dessincroniza no próximo `alter column` (RV6-11 do §r7 é essa classe). Política por
campo, na ordem "degrade o campo, depois a row, nunca o run":

- `artifact_key` — trunca preservando a **cabeça** (o prefixo `content_hash[:12]`
  resolve a identidade do documento).
- `document_id` — nulifica o que não cabe ou não resolve (mantém #1535).
- `code` fora de `ReviewReasonCode` — **descarta a row** com ERROR nomeando o
  stage: `(run, code)` é a chave de consolidação e code fabricado a envenena.
  Doutrina herdada de `_warn_unmapped`.
- `offending_value`/`expected`/`message` — coage a texto redigido, teto sanitário
  de 4 KB.
- `stage` — é do **orquestrador**, não do produtor; o payload dele é ignorado.

**D5 — Sem traceback no log do sink.** `StatementError` carrega os bound
parameters (medido: a saída da mutação imprime `[parameters: (...)]` com o
`artifact_key` inteiro). `redact_pii` cobre CPF e BRL; o `_redact` do formatter
mascara por **chave** ([[ADR-273]]); stem de filename com nome próprio escapa dos
dois. O evento é ERROR estruturado com `exc_info=False` e valor ofensor **por
shape** (`field`, `length`, `declared_limit`), nunca por valor. ERROR e não
CRITICAL: é ticket, não page. Todo campo vai explícito no `extra` — o worker
Celery não popula os contextvars de correlação, então o formatter é cego lá.
Contador in-memory é proibido ([[ADR-111]]); **o evento é a métrica**.

## Fronteira — o que esta ADR NÃO revoga

Vale para superfície **diagnóstica**, definida como *tabela sem consumidor no
caminho de decisão do usuário*. `review_reasons` qualifica hoje: nenhum endpoint
a lê, e a UI de review consome `StageReview.validation_issues`, projetado em
memória.

**[[ADR-309]] continua fail-closed.** O audit do console interno é trilha de
compliance: `append_audit` roda na MESMA transação da operação, e
`append_audit_autonomous` emite CRITICAL quando falha. Audit não é diagnóstico.
Idem `AuditLog` e `InternalOpsAudit`.

## Alternativas rejeitadas

- **Só try/except em volta da sessão única.** Salva o run e perde a transição
  junto com o diagnóstico: `run.status` nunca commita e o run fica órfão.
- **Só o DTO.** Fecha as munições conhecidas de hoje. O produtor de amanhã
  inventa a próxima — foi exatamente o que o #1535 provou ao fechar uma e
  deixar três.
- **`StageReview` do lado fail-open.** Ver D2: troca abort ruidoso por bypass
  silencioso do gate de revisão.
- **Regressão pendurada num Postgres do CI.** `VARCHAR(n)` é cego no SQLite, mas
  teste que só roda com env var num job é o padrão auto-pulável que o repo já
  documentou. A prova de largura é **estática**: percorre `__table__.columns` e
  exige que toda coluna `String(n)` escrita pelo produtor passe pelo `_fit` —
  dialect-independent, e cobre coluna que ainda não existe.

## Consequências

- Perder o diagnóstico é **permanente** (o resume pula o stage). O fail-open
  troca "apaga o run" por "apaga a razão de UM stage, com ERROR nomeando-a" —
  e a razão sobrevive em `StageReview.validation_issues`, que é controle.
- Três sessões onde havia uma, num caminho que roda ≤1× por run pausado.
- Os consumidores de `review_reasons` seguem lendo `dict`; o ganho é a
  normalização garantida. Tipar ponta-a-ponta fica como follow-up.
- Gate `dev/check_diagnostic_session_isolation.py` fecha três formas: construção
  do model fora do sink, `Session` na API pública do sink, e log com traceback lá
  dentro. O check de sessão mista é mais fraco (só enxerga o mesmo módulo) e é
  declarado como tal — existe porque é a única cobertura das outras tabelas de
  diagnóstico, que ainda não têm sink. **Divergência registrada:** o co-design
  pediu para cortá-lo; foi mantido porque cortá-lo deixaria `LLMCallLog`,
  `PipelineRunCost` e `ArtifactLineageEdge` sem enforcement algum, e o self-test
  do gate prova que ele não é vácuo.
