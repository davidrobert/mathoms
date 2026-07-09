---
id: A34.l4
type: lane
title: "Estender lint_no_real_pii a docs/ + padrões de domínio"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: extend-pii-lint-docs-domain
adrs: ["[[ADR-319]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/seguranca
---

# A34.l4 — `extend-pii-lint-docs-domain` (W2 · Gates)

## Problema

`tests/utils/lint_no_real_pii.py` é o gate anti-PII do repo, mas cobre **só
`tests/`** e detecta **só CPF**. A auditoria de 2026-07-08
([audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md) §4)
identificou esse buraco como a razão de a contaminação ter passado: o saneamento
do HEAD (Onda 1) editaria ~15 ADRs + docs de sprint + código, e **nada verificaria
o próprio commit de saneamento** nem barraria uma regressão futura.

Dois vetores de PII que o gate atual não vê, mas que o anexo lista como
CRÍTICO/ALTO fora de `tests/`:

- **Endereço residencial real** em ~27 arquivos, boa parte em `docs/` e código
  de produção (audit §1.3): `backend/tests/test_property_api.py`,
  `pipeline/llm/prompts/apolice.py`, `docs/adr/246-*.md`, entre outros.
- **Placa de veículo real** (3 ocorrências, audit §1.4) e **nº de contrato
  imobiliário** (audit §1.6, `docs/adr/261-*.md`), nenhum coberto por padrão.

O contrato negativo permanente vive em [[ADR-319]]; esta lane é a metade "lint
de PII" desse contrato (a metade "sigilo metodológico" é [[A34.l5]]; o bloqueio
de `_archive/` + gitleaks é [[A34.l6]]).

**Correção de ordem do co-design:** este gate é W2 e roda **antes** de W1
(saneamento). O critério de detecção é o gate rodar **VERMELHO no HEAD
contaminado** — gate instalado depois do saneamento não verifica nada.

## Escopo

1. **Ampliar o alcance** de `lint_no_real_pii.py` de `tests/` para o superset
   público: `docs/**`, raiz do repo (`*.md`, `*.py`, `*.yaml`) e código de
   produção (`backend/`, `frontend/`, `pipeline/`, `config/`, `scripts/`).
   Respeitar `.gitignore` (não varrer `storage/`, `_scratch/`, `data/`).
2. **Adicionar detectores de domínio** além do CPF já existente:
   - **Endereço residencial** — heurística de logradouro + número
     (`(Rua|Av\.|Avenida|Praça|Alameda|Travessa)\s+\w+.*,?\s*\d+`).
   - **Placa de veículo** — Mercosul (`[A-Z]{3}\d[A-Z0-9]\d{2}`) e formato antigo
     (`[A-Z]{3}-?\d{4}`). Manter o regex Mercosul idêntico ao dos smokes dos
     tracks (o 4º char é alfanumérico) — divergência gate↔smoke deixa passar o
     que o outro pega.
   - **Nº de contrato imobiliário / matrícula** — padrão numérico longo
     rotulado (`(matrícula|contrato)\s*n?º?\s*[\d.\/-]{6,}`).
3. **Allowlist curada** — endereço em texto livre gera falso-positivo alto.
   Não confiar só no regex: manter uma allowlist explícita de placeholders
   sintéticos aprovados (CPF `123.456.789-09`, `Rua Exemplo, 100`,
   `Titular`/`Cônjuge`, `R$ X`, matrícula `999.999`) e uma allowlist de paths
   pedagógicos legítimos (ex.: fixtures sintéticas). Toda entrada de allowlist
   exige comentário justificando — sem allowlist "solta".
4. **Rodar como gate `--all-files`** — integrar ao `pre-commit` e à
   `security.yml`. Modo estrito: qualquer hit fora da allowlist → exit não-zero.
5. **Não remover PII nesta lane** — apenas instalar e provar o detector. A
   remoção é W1 ([[A34.l7]]–[[A34.l12]]); esta lane deve rodar VERMELHO no HEAD
   até o saneamento passar.

## Critério de aceite (verificável)

- Rodar `lint_no_real_pii.py --all-files` no HEAD contaminado atual retorna
  **exit != 0** e reporta, por `path:linha + TIPO`, os achados do anexo:
  endereço em `pipeline/llm/prompts/apolice.py`, placa em
  `docs/sprint/A18/lanes/A18-l1-crlv.md`, contrato em `docs/adr/261-*.md`, CPF
  fora de `tests/` (`docs/archive/BACKLOG-pre-shim-2026-05-07.md`, audit §1.7).
- **Commit-teste sintético BARRADO:** um commit contendo um CPF com dígito
  verificador válido (não o placeholder allowlistado) + um endereço real
  sintético em `docs/scratch_pii_probe.md` é rejeitado pelo hook `pre-commit`.
- **Placeholders passam:** um arquivo contendo apenas os placeholders
  allowlistados (`123.456.789-09`, `Rua Exemplo, 100`, `Titular`) passa **verde**
  — o gate não pode gerar falso-positivo sobre o vocabulário sintético canônico.
- `tests/utils/` ganha teste do próprio detector (positivo + negativo) com
  fixtures sintéticas — **nenhum dado real na fixture do teste**.
- Não reproduz PII: mensagens de erro do gate exibem `path:linha + tipo`, nunca
  o valor casado (mesma regra do anexo).

## Rollback

Toca código/teste → **CI obrigatório**. Rollback = revert do PR do gate; como o
gate é aditivo (não altera conteúdo, só valida), o revert restaura o
comportamento anterior sem efeito em runtime. Se o gate gerar falso-positivo
bloqueante durante W1, ajustar a allowlist (com justificativa) em vez de
desabilitar o gate — desabilitar reabre o buraco que [[ADR-319]] fecha.

## Referências

- Contrato de gates anti-regressão: [[ADR-319]].
- Buraco de cobertura original: [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md) §4 (gate), §1.3 (endereço), §1.4 (placa), §1.6 (contrato), §1.7 (CPF em archive).
- Plano canônico: [[PLAN-public-release]] (Onda W2 · gate G2).
- Lanes-par em W2: [[A34.l5]] (sigilo metodológico) · [[A34.l6]] (`_archive/` + gitleaks bloqueante).
- Consumidoras (W1, sob este gate verde): [[A34.l9]] · [[A34.l10]] · [[A34.l11]].
- Vocabulário sintético canônico de placeholders: [[ADR-183]].
