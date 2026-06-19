---
id: ADR-299
type: adr
title: "SEC-03 procede: requirements.lock congelava 17 CVEs reais — bump aiohttp/starlette/python-multipart/cryptography (resposta audit r2)"
status: Decidido
phase: "audit-r2 · SEC-03"
date: "2026-06-19"
relates_to:
  - "[[ADR-230]]"
  - "[[ADR-254]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 299"
  - "SEC-03 deps CVEs"
tags:
  - area/security
  - area/infra
  - status/decidido
  - type/adr
size_lines: 52
---

# ADR-299 — SEC-03 procede: lock congelava 17 CVEs reais

**Status:** Decidido (audit-r2 · SEC-03) • **Data:** 2026-06-19 • **Relaciona** [[ADR-230]] (gates de segurança), [[ADR-254]] (lockfile com hashes)

> Rastreado em [[AUDITS-active]] §r2.

## Contexto

A auditoria r2 (`repo-audit-mathoms.ai-2026-06-11-r2`) marcou **SEC-03** como gating: `requirements.lock` congelaria "17 CVEs HIGH/CRIT" em `aiohttp`/`cryptography`/`python-multipart`/`starlette`. Uma validação manual concluiu que o achado era **FALSO** — alegando que as versões pinadas já eram as corrigidas e que `aiohttp` é usado só como client.

Este ADR registra o veredito da revalidação automatizada de forma durável, **para evitar re-litígio em auditorias futuras e impedir reversão indevida do bump** (o caso de risco real aqui: a conclusão "FALSO" levaria alguém a reverter #676 achando que foi falso-positivo).

## Decisão / Veredito

**SEC-03 procede. A validação manual estava incorreta.** `pip-audit 2.10.1 -r requirements.lock --no-deps`:

| | aiohttp | python-multipart | starlette | cryptography | Total |
|---|---|---|---|---|---|
| Pinado (vulnerável) | 3.13.5 | 0.0.29 | 1.2.0 | 48.0.0 | — |
| CVEs | 11 | 3 | 2 | 1 | **17** |
| Fix aplicado (#676) | 3.14.1 | 0.0.32 | 1.3.1 | 49.0.0 | **0 vulns** |

Por que a validação manual falhou:

1. **"Versões pinadas já são as corrigidas"** — falso. Toda CVE tinha fix version **acima** da pinada. São CVEs `CVE-2026-*` divulgadas **após** o último recompile do lock (#504/#511), portanto o lock congelava versões hoje vulneráveis.
2. **"aiohttp é só client"** — parcialmente verdade (transitivo via `anthropic`/`litellm`, sem `import aiohttp` em código de app), mas **não cobre `python-multipart` (dep direta, parse de upload) nem `starlette` (ASGI sob FastAPI)** — 5 CVEs na superfície HTTP do produto.

## O que foi feito (#676, commit `4c9e71e1`)

- Floor das 2 deps diretas subido em `backend/requirements.in` (`cryptography>=48.0.1`, `python-multipart>=0.0.31`) — documenta o piso de segurança e evita regressão.
- `aiohttp`/`starlette` (transitivos) movidos via `pip-compile -P`; lock recompilado em container `linux/amd64` (`--generate-hashes`), validado com `--require-hashes` + import check. Apenas 4 versões mudaram (zero colateral).

## Consequências

- ✅ Auditorias futuras herdam o veredito (SEC-03 procedia; fixado) sem re-investigar, e o bump não será revertido como falso-positivo.
- ✅ Regressão coberta: gate `pip-audit` é blocking em qualquer vuln ([[ADR-230]]) e roda no schedule semanal mesmo sem PR de deps — sem gap.
- ⚠️ `cryptography` saltou major (48→49); paridade de runtime (Fernet/JWT) validada pelos Backend tests no merge de #676.
- 📌 Lição de processo: validar achado de CVE **sempre** com `pip-audit` contra o lock — a leitura manual de "versão X já é segura" decai com o tempo conforme novas CVEs são divulgadas.
