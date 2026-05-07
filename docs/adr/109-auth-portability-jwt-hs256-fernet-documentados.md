---
id: ADR-109
type: adr
title: "Auth portability: JWT HS256 + Fernet documentados como contratos portáveis (A6f.5a)"
status: Decidido
date: "2026-04-20"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 109"]
tags:
  - type/adr
  - status/decidido
size_lines: 79
---

# ADR-109 — Auth portability: JWT HS256 + Fernet documentados como contratos portáveis (A6f.5a)

**Status:** Decidido • **Data:** 2026-04-20 • **Plano:** §18 A6f.5

**Contexto:** A6f.5 pede "auth portátil" — cenário hipotético em que backend
migra para Go. Auditoria (2026-04-20) revelou que o estado atual já é
language-neutral:

- **JWT**: `python-jose` com HS256, payload canônico `{sub, exp, tv}` —
  RFC 7519 puro, qualquer biblioteca Go (`golang-jwt/jwt`), TS
  (`jsonwebtoken`) ou Rust (`jsonwebtoken`) lê sem ajuste.
- **Fernet** (`cryptography.fernet`): AES-128-CBC + HMAC-SHA256 no formato
  documentado, 5 campos binários (version, timestamp, IV, ciphertext,
  HMAC). Existem libs Go (`fernet-go`), TS (`fernet`) e Rust (`fernet`).

Três caminhos considerados:

1. **Migrar para AES-256-GCM + HKDF-SHA256** agora — ganho marginal (Fernet
   já é seguro), custo alto (re-encrypt de `LLMConfig.api_key_encrypted`
   em produção, migration de `vault_entries` multi-tenant, compat
   backward no decrypt por N versões).
2. **Documentar o contrato e adiar AES-GCM** — Fernet é portátil, o gap é
   só ausência de documentação formal e teste de parity. ROI alto, risco
   zero.
3. **Migrar JWT de HS256 para RS256** — ganha separação key signing vs.
   validation, mas HS256 é suficiente até múltiplos serviços precisarem
   validar tokens sem compartilhar segredo.

**Decisão:**

1. **Manter JWT HS256** com payload canônico `{sub: str, exp: int,
   tv: int}`. Documentar em ADR que qualquer cliente Go/TS lê com a
   mesma `SECRET_KEY`.
2. **Manter Fernet** para symmetric encryption de segredos em banco
   (LLM keys, futuros vault entries). Documentar vetor de teste que
   qualquer lib Fernet-compatível (Go, TS, Rust) deve decriptar.
3. **Criar sub-fase A6f.5b** (deferida) para migrar Fernet → AES-256-GCM
   com HKDF-SHA256 + migration de dados encriptados. Gatilho de ativação:
   *(a)* requisito de auditoria (ex: SOC 2 type II exige AEAD moderno)
   OU *(b)* migração Go real em curso OU *(c)* qualquer CVE contra
   Fernet.
4. **Criar sub-fase A6f.5c** (deferida) para migrar JWT HS256 → RS256 se
   houver separação real entre serviço emissor e validador (ex: pipeline-
   service precisa validar tokens emitidos pelo backend).

**Contratos a testar em `test_auth_portability.py`:**

- JWT: roundtrip com a `SECRET_KEY` mockada — payload RFC 7519, algoritmo
  HS256 no header, claim `tv` propagado.
- Fernet: decrypt de um vetor canônico (ciphertext base64 + plaintext
  esperado) — garante que o valor em banco permanece legível mesmo se
  reimplementarmos o decrypt em outra linguagem.

**Política de documentação A6f** (aplicável a todas as sub-fases):

- ADR por sub-fase com decisão não-trivial.
- Entrada em `docs/CHANGELOG.md`.
- Status atualizado em `docs/BACKLOG.md`.
- Regra operacional nova em `CLAUDE.md` se afetar dia-a-dia.

**Consequências:**

- ✅ Contrato de auth documentado e testado sem tocar dados produtivos.
- ✅ Zero risco de perder `LLMConfig.api_key_encrypted` em prod por
  migração de cripto.
- ✅ Cliente Go hipotético hoje consegue fazer login e ler segredos
  encriptados — sem retrabalho.
- ⚠️ AES-GCM fica deferido — se virar requisito de compliance, abre
  A6f.5b.
- ❌ Formato Fernet (AES-128-CBC + HMAC) é "moderno o suficiente" mas
  não AEAD — aceito conscientemente por ora.

**Artefatos:**

- [BACKLOG §A6f.5](BACKLOG.md#a6f--language-neutral-boundaries-adr-102-r18-r20) (A6f.5a entregue, A6f.5b/.5c deferidos).
- `backend/tests/test_auth_portability.py` (parity tests).
- `docs/reference/api/v1/openapi.json` (snapshot que qualquer codegen consome).
