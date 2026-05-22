---
id: ADR-259
type: adr
title: "Boundary LLM unificado — Decimal monetário + PII (cpf_present + Fernet + UX decrypt)"
status: Proposto
phase: A18.W1α + A20.W1β
date: "2026-05-22"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-111]]"
  - "[[ADR-246]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 259"
  - "Boundary LLM unified"
  - "LLM Decimal Pii boundary"
tags:
  - area/llm
  - area/pipeline
  - area/security
  - area/money
  - status/proposto
  - type/adr
---

# ADR-259 — Boundary LLM unificado: tipos monetários, PII e contratos de output

**Status:** Proposto • **Data:** 2026-05-22 • **Relaciona** [[ADR-081]] (regex→LLM→needs_review), [[ADR-090]] (`Decimal` para dinheiro), [[ADR-097]] (services recebem value objects tipados), [[ADR-111]] (stateless rigoroso + Fernet vault singleton), [[ADR-246]] (dedup imóveis comunhão).

## Contexto

Revisão paralela (`prompt-engineer` + `senior-cto` + `data-engineer` + `financial-planner`) dos 9 prompts LLM em `pipeline/llm/prompts/` em 2026-05-22 identificou **2 classes de violação no boundary LLM** que se manifestam de forma inconsistente entre prompts:

1. **Violação [[ADR-090]] (dinheiro como `float`)**:
   - `pipeline/llm/schemas/e15_baseline.py:20,31-33` declara `value_brl: float`, `total_assets_brl: float`, `total_liabilities_brl: float`, `net_worth_brl: float`. **Schema Pydantic** (não só prompt) viola ADR-090.
   - `pipeline/llm/prompts/e15_baseline.py:24` e `pipeline/llm/prompts/e2_llm.py:35` instruem o LLM a emitir `"150000.00, não R$ 150.000,00"` — number JSON, não string decimal.
   - `pipeline/llm/schemas/e16_irpf_full.py:23` já tem `_coerce_decimal` validator como padrão correto a replicar.

2. **Vazamento de PII (CPF cru no output do LLM)**:
   - `pipeline/llm/schemas/e1_members.py:28` aceita `cpf: Optional[str]` 11 dígitos crus. `pipeline/llm/prompts/e1_members.py` instrui explicitamente "extraia: CPF ... apenas os 11 dígitos".
   - `pipeline/llm/schemas/informe_aluguel.py:147-154` permite `locador_cpf: Optional[str]`.
   - `apolice`, `crlv`, `informe_previdencia` já fazem mask Python pós-extração corretamente — padrão a generalizar.
   - `FamilyMember.cpf_encrypted: Mapped[Optional[str]]` já existe em `backend/app/models/family_member.py:34` — coluna Fernet pronta, sub-utilizada.

A inconsistência cria 3 problemas:

- **LGPD/CMN 4.658/ANPD**: CPF cru viaja para Anthropic, loga em provider logs, persiste em `pipeline_artifacts.payload` antes do mascaramento. Gate [PHASES.md F7 R4](../reference/PHASES.md) bloqueia passagem dogfood → beta fechado.
- **Precisão monetária**: `float` em `e15_baseline` propaga para `extract_baseline → consolidate_baseline → e4_categorizer → E5`, com drift de 0,01 em cenários Perini IF / AUVP desvio de classe / partilha/sucessão.
- **UX**: relatório do cliente em `/reports/[id]` precisa **mostrar CPF de volta** (cliente vê o próprio CPF). Sem decisão de boundary, dev fica reinventando mascaramento em N call-sites.

## Decisão

**Política unificada de boundary LLM em 4 regras:**

### 1. Monetário no boundary LLM = `Decimal` com `_coerce_decimal` validator

Todo campo monetário em schema Pydantic de prompt LLM **deve** ser `Decimal` (nunca `float`), com `field_validator(..., mode="before")` que aceita `int | str | float` e converte via `Decimal(str(v))`. Padrão canônico em [pipeline/llm/schemas/e16_irpf_full.py:23](../../pipeline/llm/schemas/e16_irpf_full.py:23) e [pipeline/llm/schemas/informe_aluguel.py:14-22](../../pipeline/llm/schemas/informe_aluguel.py:14-22).

System prompt **deve** instruir explicitamente: `"valores como string decimal '150000.00' — o validator converte para Decimal no boundary"`. Nunca `"valor em formato numérico (150000.00, não R$ 150.000,00)"` que induz number JSON.

Serializer downstream (`pipeline/stages/extract_*.py` ao gravar em `pipeline_artifacts`) **deve** emitir string decimal, nunca `float(value)`. Schema JSON em `config/schemas/*.schema.json` valida com `"type": "string", "pattern": "^-?\\d+(\\.\\d{1,2})?$"`.

### 2. PII no boundary LLM = `cpf_present: bool`, nunca CPF cru

Schema Pydantic de prompt LLM que processa documentos com PII **deve** declarar `cpf_present: bool = False` (apenas sinaliza presença), nunca `cpf: Optional[str]` 11 dígitos. Equivalente para outros documentos de identidade quando o documento puder conter PII bruta.

System prompt **deve** instruir: `"NÃO emitir CPF no output. Apenas sinalizar cpf_present=true quando documento contém CPF. Mascaramento e persistência são responsabilidade do adapter Python pós-extração."`

Exceções permitidas (CNPJ): números de inscrição de pessoa jurídica (CNPJ, IPTU municipal, código RFB) são informação pública e podem trafegar no output bruto. **Comentar política de anonimização em logs** quando o consumer downstream loga payload.

### 3. CPF cifrado em `FamilyMember.cpf_encrypted` via `vault.py` Fernet

Adapter Python pós-extração — `backend/app/services/family_member_pii_service.py` (novo) — usa regex sobre o documento original (não o output do LLM) para extrair CPF e:

1. Persiste em `FamilyMember.cpf_encrypted` via `backend/app/services/vault.py` (singleton lazy idempotente, aderente [[ADR-111]]).
2. Match com `member_key` (`titular`, `conjuge`, etc.) por fuzzy name/role.
3. **Nunca grava CPF cru** em `pipeline_artifacts.payload` ou `LLMCallLog.input_text`.

Tabela nova **não** é criada — `cpf_encrypted` já existe no modelo `FamilyMember` desde [migration histórica].

### 4. UX decrypt no boundary HTTP autenticado, mascarado por default

Relatório do cliente em `/reports/[id]` decriptografa Fernet **apenas no boundary HTTP autenticado** (request com JWT do owner do workspace). Renderiza:

- **Default**: mascarado `***.***.789-00` (mostra 3 últimos dígitos + último dígito de verificador).
- **Opção "ver completo"**: clique do usuário decriptografa e renderiza CPF completo + audit log em `cpf_view_audit` (tabela nova ou extensão de `event_log` — definir em ADR de UX se necessário).

Nunca decriptografar em background job, em logs estruturados ou em export PDF gerado sem interação ativa.

## Implicações

- **3 schemas Pydantic mudam** (breaking schema, tag `breaking/schema`): `e15_baseline.py`, `e1_members.py`, `informe_aluguel.py`. Bumps de `PROMPT_VERSION` coordenados em W1α + W1β do plano [[PLAN-llm-prompts-hardening]].
- **2 schemas JSON mudam**: `config/schemas/baseline_patrimonial.schema.json` (string decimal pattern), `config/schemas/e2_extract.schema.json` (auditar similar).
- **3 prompts ganham regra explícita de mask CPF** (system prompt §regras).
- **1 service novo**: `family_member_pii_service.py` em `backend/app/services/` (boundary respeitado — pipeline não importa `backend.app`).
- **Migration de payloads históricos**: `pipeline_artifacts` com CPF cru em payload precisa backfill (decisão por contagem do audit em W1α-T01).
- **UX nova** em `/reports/[id]`: componente de CPF mascarado + audit log de "ver completo".
- **Goldens atualizados**: `e15_baseline`, `e1_members`, `informe_aluguel` ganham fixtures com `cpf_present=true` e valores string decimal.

## Alternativas consideradas

**A. Manter `cpf: Optional[str]` no schema + mascarar pós-LLM.** Rejeitado: CPF cru ainda viaja para Anthropic + persiste em `LLMCallLog.input_text`. Mascaramento pós-LLM mitiga UI mas não fecha LGPD/F7 R4.

**B. Criar tabela `family_member_pii` separada.** Rejeitado pelo `data-engineer` em 2026-05-22: `FamilyMember.cpf_encrypted` já existe. Tabela nova é overengineering.

**C. Decriptografar CPF em todos os call-sites server-side.** Rejeitado: viola princípio de least-privilege; PII só vai a UI sob request ativo do owner.

**D. Manter `float` em `e15_baseline` e converter para `Decimal` no consumer.** Rejeitado pelo `financial-planner`: drift de 0,01 já entra no relatório antes da conversão. Perini IF e AUVP desvio são sensíveis.

## Referências

- Plano canônico: [[PLAN-llm-prompts-hardening]]
- Lane W1α-T02 (e1_members): `docs/sprint/A18/lanes/A18-l4-llm-w1-alpha-lgpd.md`
- Lane W1β-T02 (e15_baseline): `docs/sprint/A20/lanes/A20-l11-llm-w1-beta-adr090.md`
- LGPD art. 46 (segurança de dados pessoais); CMN 4.658 §segregação PII; ANPD Guia de Anonimização (2024).
