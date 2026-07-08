---
id: ADR-319
type: adr
title: "Contrato de gates anti-regressão PII + sigilo metodológico pós-público"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[A34.l4]]", "[[A34.l5]]", "[[A34.l6]]", "[[ADR-183]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/seguranca
  - area/ci
---

# ADR-319 — Contrato de gates anti-regressão PII + sigilo metodológico pós-público

**Status:** Proposto · **Data:** 2026-07-08 · Enforcement da Onda 2 de
[[PLAN-public-release]] ([[A34.l4]]/[[A34.l5]]/[[A34.l6]]); consome o
vocabulário canônico de [[ADR-183]].

## Contexto

A auditoria de 2026-07-08 (anexo `audit-2026-07-08.md`) mostrou que a
disciplina recente funcionou (zero API key viva, fixtures golden
sintéticas, prompts sem PII de cliente), mas os **gates que deveriam ter
prevenido a contaminação têm cobertura incompleta**:

- `tests/utils/lint_no_real_pii.py` cobre só `tests/` e só **CPF** — não
  vê `docs/`, raiz, endereço, placa de veículo, número de contrato.
- `dev/check_sigilo_terms.py` cobre só `frontend/` e `docs/_marketing/` —
  não vê `docs/**`, `config/prompts/**`, `README`, migrations. Foi o
  buraco que deixou passar prompts de produto citando **Perini/Cerbasi/
  AUVP nominalmente** (marca de terceiro sem licença) — bloqueador que 4
  dos 5 agentes do co-design não capturaram.
- `dev/check_forbidden_paths.py` bloqueia `storage/`, `.env`, `*.db` etc.,
  mas **não** `_archive/` — a maior concentração de PII do HEAD.
- gitleaks (em `security.yml`) roda **informativo**, não bloqueia, e não
  varre o histórico completo.

Sem fechar esses buracos **antes** do saneamento (Onda 1), qualquer
edição de anonimização pode regredir sem sinal, e não há critério
mecânico de detecção do estado contaminado. A correção de ordem do
co-design (senior-cto vence PM/IA/SRE) é: **W2 antes de W1** — o gate
rodando VERMELHO no HEAD contaminado É o critério de detecção, e trava
regressão durante as ~15 edições. Gate-after-clean é anti-padrão (não
verifica o próprio commit de saneamento).

Esta é decisão **técnica/de-processo** — não owner-gated. O owner decide
licença/escopo/rewrite (ADR-313–318); o contrato de gate é engenharia.

## Decisão

Estabelecer um **contrato negativo permanente** — o que `docs/**`,
prompts, migrations, raiz e histórico **NÃO podem conter** — e mecanizá-lo
em quatro extensões de gate que rodam no pre-commit e no CI.

**Contrato negativo (invariante permanente):**

1. **Zero PII de terceiro** em qualquer arquivo tracked ou mensagem de
   commit: CPF com dígito verificador válido, endereço residencial,
   matrícula de imóvel, placa de veículo, número de contrato de crédito,
   nome de terceiro (familiar/diarista/empregador) em contexto financeiro,
   patrimônio/renda nominal atribuível a pessoa real.
2. **Zero atribuição nominal metodológica**: `perini`, `cerbasi`, `auvp`,
   `raul sena`, `viver de renda` (case-insensitive) no superset público.
   Substituto canônico: "metodologia consagrada de planejamento
   patrimonial brasileiro" ([[ADR-183]]).
3. **Zero path de máquina local** (`/Users/...`, homedir) em arquivo
   tracked.

**Enforcement:**

1. **[[A34.l4]]** — `lint_no_real_pii` estendido de `tests/`+CPF para
   `docs/`+raiz+migrations e para os padrões de domínio (endereço, placa,
   matrícula, contrato), com **allowlist curada** para os placeholders
   sintéticos permitidos (CPF `123.456.789-09`, "Rua Exemplo, 100",
   `Titular`/`Cônjuge`, "R$ X") — sem allowlist, texto pedagógico de ADR
   vira falso-positivo massivo.
2. **[[A34.l5]]** — `check_sigilo_terms` estendido de
   `frontend/`+`docs/_marketing/` para todo o superset público (`docs/**`,
   `config/prompts/**`, `README`, migrations). Fecha o gap que 4/5 agentes
   não capturaram.
3. **[[A34.l6]]** — `_archive/` + `archive/` adicionados a
   `check_forbidden_paths`; gitleaks flipado para **bloqueante** e varrendo
   **histórico completo** (não só a árvore do HEAD).
4. **Ordem W2→W1**: os quatro gates são instalados e provados VERMELHOS no
   HEAD contaminado **antes** de qualquer commit de saneamento. Um
   commit-teste sintético (PII/atribuição conhecida) deve ser BARRADO —
   critério de aceite de G2.

## Alternativas consideradas

- **Gate-after-clean (W1 antes de W2).** Instalar gates só depois de
  sanear. Rejeitada: não verifica o commit de saneamento, não detecta o
  estado contaminado (sem baseline vermelho), e deixa a janela de ~15
  edições sem trava de regressão. É o anti-padrão que produziu o passivo.
- **Um único gate monolítico novo.** Reescrever tudo num scanner só.
  Rejeitada: duplica cobertura existente, descarta a curadoria de
  `lint_no_real_pii`/`check_sigilo_terms` (que já funcionam no seu escopo)
  e infla superfície de manutenção. Estender > reescrever.
- **gitleaks informativo + revisão humana.** Confiar no olho humano para
  o superset. Rejeitada: a auditoria provou que revisão humana não escala
  para 1.862 commits + ~200 arquivos internos; sigilo metodológico é
  mecanizável e determinístico.
- **Allowlist por regex ampla vs. lista curada.** Uma regex genérica de
  "ignore exemplos" abre buraco por onde PII real passa. Escolhida a
  allowlist **curada** de placeholders exatos — falso-negativo é pior que
  ruído de falso-positivo aqui.

## Consequências

- **KR2/KR3 do plano ficam mecanizáveis**: cobertura do gate sobre o
  superset e zero atribuição nominal viram `grep` verde, não julgamento.
- **Custo de manutenção da allowlist**: novo placeholder sintético em doc
  exige entrada na allowlist curada de `lint_no_real_pii` — dívida nomeada
  e barata; o alternativo (regex ampla) é inseguro.
- **Ruído de falso-positivo esperado** na primeira execução sobre `docs/**`
  (texto livre com números que parecem CPF/valor). Absorvido pela
  allowlist na própria [[A34.l4]]; não bloqueia a Onda 1.
- **Contrato permanente pós-flip**: os gates continuam ativos após o repo
  ser público — protegem contra reintrodução de PII/atribuição por PR
  futuro (interno ou de contribuidor externo). Não são one-shot de
  saneamento.
- **Não cobre a Camada 3** (metadados GitHub imutáveis) — fora do alcance
  de git-gate; tratada por [[A34.l21]] + aceite de risco em ADR-316.
- **Dependência de ordem**: G2 é pré-requisito duro de G1 no
  [[PLAN-public-release]]; nenhuma lane de saneamento (W1) abre com os
  gates ainda verdes/inexistentes.

## Critério de aceite

- `lint_no_real_pii` roda sobre `docs/`+raiz+migrations com allowlist
  curada; commit-teste com CPF/endereço/placa sintéticos-conhecidos é
  BARRADO.
- `check_sigilo_terms` roda sobre `docs/**`+`config/prompts/**`+README+
  migrations; commit-teste citando `perini`/`cerbasi`/`auvp` é BARRADO.
- `check_forbidden_paths` bloqueia staging de `_archive/`; gitleaks
  bloqueante retorna não-zero na árvore E no histórico contaminados.
- Os quatro gates rodam VERMELHO no HEAD atual (prova de detecção) —
  registro em G2 do plano antes de W1 abrir.
