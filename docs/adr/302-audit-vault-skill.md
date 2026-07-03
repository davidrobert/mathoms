---
id: ADR-302
type: adr
title: "Skill audit-vault — auditoria recorrente de vault como procedimento do loop principal"
status: Decidido
phase: A26
date: "2026-07-01"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-182]]"
  - "[[ADR-247]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 302"
  - "audit-vault skill"
  - "auditoria de vault"
tags:
  - type/adr
  - status/decidido
  - area/docs
  - area/tooling
  - phase/a26
---

## Contexto

Auditar o vault de documentação (MD/HTML/YAML/JSON/TOML/TXT) quanto a
**completude, corretude, consistência e precisão** é tarefa recorrente do dono
do repo. Hoje é feita ad-hoc: cada auditoria reinventa formato de finding,
escopo e roteamento. Precedentes provam o valor e o custo da falta de
convenção — a revisão multi-agente de 2026-04-24 ([PHASES §DOCS-REVIEW](../reference/PHASES.md))
e a `repo-audit-...-r2` (cujo relatório efêmero **se perdeu** e teve de ser
reconstruído da trilha, ver [AUDITS-active](../_MOC/AUDITS-active.md)).

Já existe infra parcial que uma auditoria nova **deve reusar em vez de duplicar**:

- **7 gates determinísticos** em `dev/` (`validate_frontmatter`,
  `check_doc_links`, `check_adr_anchors`, `check_doc_filename_id`,
  `validate_adr_format`, `build_doc_index --check`,
  `check_doc_markdown_links`) rodando em pre-commit — cobrem o **mecânico**.
- **`docs/_MOC/AUDITS-active.md`** — registro editorial com taxonomia de
  disposição (`procede-fechado`/`procede-aberto`/`refutado`/`não-acionável`/
  `aceito-wontfix`), cadência anti-zumbi e cobertura 100%.
- **`docs/archive/audits/`** — padrão de arquivamento de auditoria fechada.

O gap: não há **procedimento reutilizável** que orquestre gates → julgamento
LLM → síntese, plugando no registro existente. A pergunta "isso é skill, prompt
ou agente?" precisa de resposta canônica para não recorrer.

## Decisão

Auditoria de vault é **procedimento do loop principal** implementado como
**Skill** (`.claude/skills/audit-vault/`), não como agente novo nem prompt
solto.

**Rationale da forma:** um agente `vault-auditor` duplicaria os 5 especialistas
que já têm o domínio (`information-architect` julga forma, `senior-cto` ADR
técnica, `financial-planner` regra de domínio, `product-manager` plano
canônico, `prompt-engineer` prompt YAML). O valor é o **procedimento de
orquestração + roteamento + taxonomia de output** — não uma nova cabeça de
julgamento. No modelo deste repo, quem delega é o loop principal (§Subagentes
do CLAUDE.md); auditar **é** orquestração ⇒ é trabalho de skill.

Arquitetura em camadas (fronteiras sem sobreposição):

1. **Gates determinísticos primeiro** (fail-fast, 100% dos arquivos). Gate
   falho vira finding automático `corretude` **sem gastar token LLM**.
2. **Coleta determinística** (`references/collect_candidates.py`): candidatos a
   julgamento = `gate-fail ∪ git-diff ∪ amostra estratificada`. Não manda os
   ~956 markdown ao LLM; só o residual.
3. **Julgamento LLM** só nos candidatos, roteado por **`type:` do frontmatter**
   (não por path) ao especialista do §Subagentes. Ataca só os 4 gaps que gate
   não pega: precisão factual (doc↔código), consistência semântica cross-doc,
   supersedure de sentido, completude editorial.
4. **Verify barato** só em findings de severidade alta: exige citar o trecho do
   doc **e** da fonte-de-verdade que se contradizem; sem ambos, rebaixa.
5. **Síntese** com dois outputs: relatório bruto em `_scratch/` (efêmero) +
   **patch de seção para `docs/_MOC/AUDITS-active.md`** (curado, disposição).

**Severidade ancorada em consequência** (não herda P0/P1/P2 de runtime):
`DOC-BLOCK` (doc contradiz código/ADR vigente ⇒ agente decidiria errado — fix
agora), `DOC-DRIFT` (desatualizado mas não indutor de erro — batch em lane P2),
`DOC-POLISH` (cosmético — wontfix/batch). Só `DOC-BLOCK` interrompe.

**Baseline = o AUDITS-active.md.** Em estágio dogfood, a disposição triada no
registro editorial **é** o baseline; dedup entre runs por chave semântica
`(path, regra)` cruzada contra o `procede-aberto` da seção anterior. Um baseline
JSON separado fica **deferido** (gatilho de crescimento: quando o cross-ref
manual doer).

## Alternativas consideradas

### Opção A — Agente novo `vault-auditor`

**Rejeitada.** Duplica os 5 especialistas existentes; viola a filosofia de
"especialista estreito". Auditoria não é domínio novo, é orquestração.

### Opção B — Prompt/`track_*.md` copiável

**Rejeitada.** `track_*` é para 1 lane / 1 agente / 1 branch ligado ao BACKLOG.
Auditoria é recorrente e transversal, não lane. Prompt solto não é discoverable
via `/` e apodrece.

### Opção C — "Workflow salvo" como artefato de orquestração separado

**Rejeitada.** Criaria segundo orquestrador que **duplica** a tabela de
gatilhos do §Subagentes — diverge em poucas sprints. O que sobrevive dela é a
**coleta determinística** (`collect_candidates.py`), que não roteia agentes.

## Consequências

### Positivas

- Procedimento reutilizável via `/audit-vault`, versionado e descoberto.
- Zero duplicação de roteamento: a skill **referencia** o §Subagentes.
- Custo controlado: LLM só no residual, não nos 956 arquivos.
- Recorrência reproduzível: 2 runs sem mudança → mesmo conjunto de candidatos.
- Findings aterrissam no registro canônico existente, com dedup semântico.

### Negativas

- Introduz nova classe de artefato (`.claude/skills/`) — primeiro do repo.
- Manter o roteamento por `type:` alinhado aos schemas em `docs/_schemas/`.
- Triagem de disposição continua manual (custo humano, como os goldens).

## Validação

Critério de aceite da skill (prova de valor, não teatro):

- ≥1 `DOC-BLOCK` vira correção mergeada em `main` (docs-only).
- Taxa de falso-positivo dos `DOC-BLOCK` ≤ 20% na triagem.
- Determinismo: 2 runs sem mudança → diff de candidatos vazio
  (`collect_candidates.py --self-test`).
- Modo default não chama LLM em arquivo que passou gates e está inalterado.
- < 30% dos findings recriam o que o pre-commit já pega.

**Evidência do flip (2026-07-03):** critérios satisfeitos pelas execuções
`vault-2026-07-01-r3` (18 findings triados, DOC-BLOCKs com 0 falso-positivo,
correções mergeadas em `main`) e `vault-2026-07-02-r4` (gates 100% verdes,
3/3 DOC-BLOCKs reverificados, zero regressão r3→r4) registradas em
[AUDITS-active](../_MOC/AUDITS-active.md).

## Migração

1. `references/checklist.md` (4 critérios × tipo de arquivo + coluna "coberto
   por gate").
2. `references/collect_candidates.py` + `--self-test`.
3. `SKILL.md` (procedimento das 5 camadas, parâmetros `--scope`/`--mode`,
   armadilhas, referência ao §Subagentes).
4. Primeira execução real; nova seção em `AUDITS-active.md`.

## Riscos

- **LLM inventa contradição** — mitigado pela camada 4 (verify obrigatório em
  DOC-BLOCK) e pela lição SEC-03 (nunca auto-marcar `refutado` sem evidência
  empírica).
- **Escopo puxa histórico congelado** — `archive/` e sprint fechada ficam fora
  do julgamento (gates só); auditar precisão de snapshot gera falso-drift.

## Gatilho de reabertura

Estágio **dogfood** justifica cortar KR e cron. Ao cruzar para **beta** (docs
viram superfície para usuários), reabrir: cadência agendada, KR "% reference sem
DOC-BLOCK" e sweep amplo dos 5 agentes passam a ter ROI.

## Referências

- [[ADR-182]] — vault atômico (frontmatter + schemas).
- [[ADR-247]] — MD canônico, HTML derivado.
- [[ADR-081]] — padrão regex→LLM→needs_review (mesma filosofia de camadas).
- [AUDITS-active](../_MOC/AUDITS-active.md) — registro canônico de auditorias.
