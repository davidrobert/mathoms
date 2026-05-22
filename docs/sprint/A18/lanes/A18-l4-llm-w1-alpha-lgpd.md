---
id: A18.l4
type: lane
title: "LLM Hardening — W1α LGPD compliance (gate F7 R4 → Beta fechado)"
sprint: A18
plan: PLAN-llm-prompts-hardening
status: planned
priority: P0
branch_slug: a18-l4-llm-w1-alpha-lgpd
parallel_with:
  - "[[A18.l1]]"
  - "[[A18.l2]]"
adrs:
  - "[[ADR-256]]"
  - "[[ADR-111]]"
  - "[[ADR-246]]"
tags:
  - type/lane
  - sprint/a18
  - status/planned
  - priority/p0
  - area/llm
  - area/security
  - breaking/schema
---

# A18.L4 — W1α LGPD compliance (3 PRs)

> **Onda 1α do plano [[PLAN-llm-prompts-hardening]].** Gate de [PHASES.md F7 R4](../../../reference/PHASES.md) → Beta fechado. Custo de não fazer = não abre beta. **Sinergia com [[A18.l2]]** (apólice também extrai CPF do segurado).

## Objetivo

Fechar 3 gaps LGPD identificados na revisão paralela (2026-05-22) de schemas LLM:

1. `pipeline/llm/schemas/e1_members.py:28` aceita `cpf: Optional[str]` 11 dígitos crus.
2. `pipeline/llm/schemas/informe_aluguel.py:147-154` permite `locador_cpf` cru.
3. `pipeline/llm/prompts/informe_aluguel.py` sem `PROMPT_VERSION` no arquivo de prompt (gate [[ADR-233]] cego).

Aderência a [[ADR-256]] (boundary LLM unificado): schema Pydantic emite `cpf_present: bool`; adapter Python pós-extração popula `FamilyMember.cpf_encrypted` via `backend/app/services/vault.py` Fernet ([[ADR-111]]).

## Critério de aceite (gate binário falsifiável)

- `grep -rn "cpf.*Optional\[str\]" pipeline/llm/schemas/` retorna 0 ocorrências.
- `jq` sobre `pipeline_artifacts` (stages `extract_members` + `extract_informe_aluguel`) retorna 0 rows com CPF cru em payload.
- 5 fixtures golden `informe_aluguel` mergeadas em `tests/fixtures/llm_golden/` cobrindo: PF→PF, multi-imóvel vacância, PF→PJ IR retido, **imóvel em comunhão (paridade [[ADR-246]])**, **PF locador com dedução IPTU/condomínio**.
- 1 fixture `e1_members` família 5 membros mergeada.
- **Checklist [F7 R4 LGPD](../../../reference/PHASES.md) verde** — auditoria interna do founder + checklist ANPD Guia de Anonimização sem item vermelho.
- `pytest tests -q -k "informe_aluguel or e1_members"` verde.
- `pre-commit run --all-files` verde.

## Sub-tarefas (3 PRs sequenciais)

### W1α-T01 — Audit gravação atual de CPF (foundation, ~1d)

- `grep -rn "cpf_encrypted" backend/app/services/` — mapear quem grava hoje (upload regex vs. LLM `extract_members`).
- Auditar `pipeline_artifacts` em dev/staging para presença de CPF cru em payload (`stages: extract_members + extract_informe_aluguel`).
- Backfill policy documentada: migration que **purga** ou **re-criptografa** payloads existentes (decisão por contagem).

### W1α-T02 — `e1_members` LGPD (split em PR-A + PR-B, ~2d)

- **PR-A (foundation, independente do schema)**: adapter Python pós-LLM em `backend/app/services/family_member_pii_service.py` (novo) usa `vault.py` Fernet para popular `FamilyMember.cpf_encrypted`. Backfill rotina + dry-run + apply.
- **PR-B (schema + prompt)**: `cpf: Optional[str]` → `cpf_present: bool = False`. Prompt: regra explícita de não emitir CPF. Bump `PROMPT_VERSION → "2.0.0"` (major — schema breaking).
- **Decisão UX**: relatório decriptografa Fernet no boundary HTTP autenticado; renderiza mascarado `***.***.789-00` por default + opção "ver completo" sob clique com audit log.
- Atualizar fixture + 1 fixture nova (família 5 membros, dependente sem CPF).

### W1α-T03 — `informe_aluguel` LGPD + PROMPT_VERSION + 5 goldens BR (~1d)

- Re-export `PROMPT_VERSION` do schema no arquivo de prompt (padrão `e16_irpf_full`).
- Schema: `locador_cpf: Optional[str]` → `cpf_present: bool = False`. `imobiliaria_cnpj`: mantém.
- Prompt: remover instrução de extração CPF.
- Bump schema → semver puro (`informe-aluguel-v1.1.0` → `1.2.0`; migration coordenada em [[A20.l12]]).
- **Criar 5 fixtures golden** (revisão FP — público-alvo alta renda PJ BR).

## Coordenação

Paralelo a [[A18.l1]] (CRLV) e [[A18.l2]] (apólice). [[A18.l2]] também extrai CPF (segurado) — sinergia: ADR-256 cobre boundary unificado para ambos. Não competir por arquivos.

**Depende de**: nada. Pode iniciar imediatamente após A18 abrir.

**Sequência interna**: T01 (audit) → T02 PR-A (foundation) → T02 PR-B + T03 (paralelos).

## Detalhe operacional

Plano canônico: [[PLAN-llm-prompts-hardening]] §W1α. ADR canônica: [[ADR-256]] (boundary LLM unificado).

**Capacity estimada**: ~4d eng-time.
