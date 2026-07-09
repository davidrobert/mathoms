---
id: A34.l5
type: lane
title: "Estender check_sigilo_terms ao superset público"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: extend-sigilo-gate-superset
adrs: ["[[ADR-319]]", "[[ADR-183]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/seguranca
  - area/gtm
---

# A34.l5 — `extend-sigilo-gate-superset` (W2 · Gates)

## Problema

`dev/check_sigilo_terms.py` hoje cobre apenas `frontend/` + `docs/_marketing/`.
Esse escopo foi desenhado para copy de produto — **não** para o superset de
paths que sobrevive ao flip público. O resultado é um ponto cego crítico:
prompts de produto citam **Perini / Cerbasi / AUVP nominalmente**, e o gate de
sigilo não os enxerga.

Bloqueador que **4 dos 5 agentes do co-design não capturaram** (só o
`gtm-strategist`): `config/prompts/parecer_planejador.yaml` e
`config/prompts/section_summaries.yaml` fazem atribuição nominal a autores e
marcas de terceiros. Publicar isso = exposição de marca de terceiros sem
licença — violação de sigilo metodológico, bloqueante de flip e **mecanizável**.

O vocabulário canônico substituto já existe: [[ADR-183]] ("metodologia
consagrada de planejamento patrimonial brasileiro"), detalhado em
`COPY_GUIDELINES §13.2`. O gate deve enforçar essa fronteira em **todo path
público**, não só na copy de produto.

## Escopo

1. Estender a superfície de varredura de `dev/check_sigilo_terms.py` para o
   **superset público** — todo path que sobrevive ao flip:
   - `docs/**` (ADRs, planos, sprint docs, reference)
   - `config/prompts/**` (o bloqueador: `parecer_planejador.yaml`,
     `section_summaries.yaml`)
   - `README*` (raiz + subpastas)
   - migrations de seed (paths de `backend/alembic/versions/**` que inserem
     dados de exemplo)
2. Bloquear atribuição nominal via termos-padrão (case-insensitive):
   `perini | cerbasi | auvp | raul sena | viver de renda`. Um hit não-vazio é
   **bloqueante de flip** (exit ≠ 0).
3. Mensagem de erro aponta `path:linha` + termo ofensor + o vocabulário
   canônico esperado ([[ADR-183]] / `COPY_GUIDELINES §13.2`), no padrão dos
   demais gates de doc (valor ofensor + shape esperado).
4. Preservar o comportamento atual sobre `frontend/` + `docs/_marketing/` —
   estender, não substituir.
5. Allowlist mínima e explícita para paths onde a citação é **legítima e
   privada** (ex.: a própria [[ADR-183]] que define a política, ADRs históricas
   que documentam a decisão) — cada exceção comentada inline com o porquê.
   Sem allowlist folksonômica; entrada nova exige justificativa.

## Critério de aceite (verificável)

- **Gate VERMELHO no HEAD:** `python3 dev/check_sigilo_terms.py` sai com código
  ≠ 0 no HEAD contaminado, listando pelo menos os hits em
  `config/prompts/parecer_planejador.yaml` e `config/prompts/section_summaries.yaml`
  (critério de detecção — prova que o gate enxerga o bloqueador).
- **Commit-teste sintético BARRADO:** um commit de teste que insira atribuição
  sintética (ex.: linha com `metodologia Cerbasi` em `docs/` ou
  `config/prompts/`) é rejeitado pelo gate; removida a linha, passa.
- **Cobertura provada por path:** o gate varre e reporta hits em `docs/**`,
  `config/prompts/**`, `README*` e migrations de seed — não só
  `frontend/`/`docs/_marketing/`.
- **Superfície legada intacta:** os hits que o gate já pegava em `frontend/` +
  `docs/_marketing/` continuam sendo pegos (sem regressão de cobertura).
- **Allowlist auditável:** cada path isento tem comentário inline justificando;
  a própria [[ADR-183]] não dispara falso-positivo.
- Registrado no hook de `pre-commit` (mesmo grupo dos demais gates de doc/PII),
  de modo que rode em todo PR pós-instalação.

Este gate **fica vermelho de propósito** no HEAD até a [[A34.l12]] redigir os
prompts — é o critério de detecção do gate G2, não uma falha a "consertar" aqui.
A neutralização do conteúdo é escopo da W1.

## Rollback

Toca código (`dev/check_sigilo_terms.py` + config de `pre-commit`) — **CI
obrigatório**. Rollback = reverter o PR; a superfície de varredura volta a
`frontend/` + `docs/_marketing/`. Sem migração de dado, sem estado; reversão é
puramente de código de gate. Nenhum artefato de produto é alterado por esta
lane (a redação de conteúdo é [[A34.l12]]).

## Referências

- Contrato de gates anti-regressão: [[ADR-319]].
- Vocabulário canônico substituto (narrativa sem atribuição nominal): [[ADR-183]]
  + `COPY_GUIDELINES §13.2`.
- Ondas e gate G2: [[PLAN-public-release]] §"Ondas, lanes e dependências" (W2).
- Neutralização do conteúdo dos prompts (consome este gate): [[A34.l12]].
- Lanes-par da W2: [[A34.l4]] (lint PII → docs+domínio) · [[A34.l6]]
  (`_archive/` + gitleaks bloqueante).
- KR de escopo: [[PLAN-public-release]] §KRs — KR2 (cobertura de gates) + KR3
  (zero atribuição nominal metodológica no público).
