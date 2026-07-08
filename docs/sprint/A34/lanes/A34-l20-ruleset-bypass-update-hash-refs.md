---
id: A34.l20
type: lane
title: "Bypass owner do Ruleset + atualizar hash-refs em ADRs"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: ruleset-bypass-update-hash-refs
adrs: ["[[ADR-315]]"]
depends_on: ["[[A34.l19]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/ci
  - area/seguranca
---

# A34.l20 — `ruleset-bypass-update-hash-refs` (W3 · Rewrite)

## Problema

O force-push do clone `--mirror` reescrito (produto de [[A34.l18]]) **colide
com o Repository Ruleset `main-protection`** (id `15884038`): a regra
`non_fast_forward` bloqueia qualquer push que não seja fast-forward, e o rewrite
de histórico por definição não é. Sem intervenção deliberada do owner, a última
operação irreversível do plano ([[ADR-315]]) trava no gate de proteção.

Isso cria dois riscos que esta lane fecha:

1. **Footgun de janela aberta.** A única forma de aplicar o force-push é
   desabilitar `enforcement` do Ruleset. Se a janela ficar aberta além do
   estritamente necessário — e sobretudo se o flip para público ([[A34.l22]])
   ocorrer antes da reativação — o repo público fica **sem proteção de branch**
   (push direto em `main`, deleção, sem required checks). O bypass é auditável e
   **nunca automatizável por agente** (CLAUDE.md §Git — bypass de Ruleset exige
   autorização explícita do owner).
2. **Hash-refs quebradas pós-rewrite.** O `git-filter-repo` de [[A34.l18]]
   reescreve **todos** os SHAs. Cerca de 10 ADRs e o changelog citam commit
   hashes literais na prosa (ex.: refs de auditoria a `ae340c60` /
   `90279c68` do blob Fernet). Pós-rewrite esses hashes deixam de resolver —
   arqueologia de decisão quebra silenciosamente ([[ADR-182]]).

## Escopo

**Parte A — bypass e reativação do Ruleset (owner, manual, auditável):**

1. **Antes do force-push** — owner desabilita o enforcement:
   ```
   gh api -X PUT repos/davidrobert/mathoms/rulesets/15884038 -f enforcement=disabled
   ```
   Registrar timestamp de abertura no log da operação (runbook [[A34.l18]]).
2. Aplicar o force-push do mirror reescrito (executado pela [[A34.l18]]) dentro
   da janela — este é o único push permitido enquanto o enforcement está off.
3. **Imediatamente após** — owner reativa:
   ```
   gh api -X PUT repos/davidrobert/mathoms/rulesets/15884038 -f enforcement=active
   ```
4. **VERIFICAR** que a reativação restaurou as regras críticas — não confiar no
   retorno do PUT:
   ```
   gh api repos/davidrobert/mathoms/rulesets/15884038 \
     --jq '{enforcement, rules: [.rules[].type]}'
   ```
   Confirmar `enforcement == "active"` e que a lista de `rules` contém
   `non_fast_forward` **e** `required_status_checks` (além de `pull_request`,
   `required_linear_history`, `deletion`). Registrar timestamp de fechamento.

**Parte B — atualizar hash-refs (docs-only):**

5. Levantar as ocorrências de hash literal na prosa de docs (não em
   frontmatter):
   ```
   git grep -nE '\b[0-9a-f]{7,40}\b' -- docs/adr docs/CHANGELOG.md
   ```
   Filtrar para os hashes que **eram** commits reais pré-rewrite (~10 ADRs +
   changelog). Referir os achados por path:linha, nunca colar valores de PII
   associados.
6. Para cada ref: substituir o hash antigo pelo hash reescrito **quando houver
   mapa 1:1 estável**, OU — quando o commit foi absorvido/removido pelo rewrite
   — anotar a ref como histórica (ex.: `commit pré-rewrite, não mais resolúvel`)
   em vez de deixar SHA morto apontando para o nada.
7. Adicionar **uma nota de rewrite no changelog** (`docs/CHANGELOG.md`)
   documentando data, motivo ([[ADR-315]]) e que hashes anteriores a essa data
   não resolvem no histórico público — preserva a arqueologia de decisão
   ([[ADR-182]]) para quem cruza PRs antigos.

## Critério de aceite (verificável)

- `gh api repos/davidrobert/mathoms/rulesets/15884038 --jq .enforcement` retorna
  `"active"` ao fim da lane; a query de verificação (passo 4) confirma
  `non_fast_forward` + `required_status_checks` presentes.
- **Zero janela aberta pós-flip:** timestamp de reativação do Ruleset é
  **anterior** ao flip de visibilidade ([[A34.l22]]); log da operação registra
  abertura → force-push → reativação em sequência contígua.
- `git grep -nE '\b[0-9a-f]{7,40}\b' -- docs/adr docs/CHANGELOG.md` não retorna
  nenhum hash pré-rewrite sem tratamento (substituído OU anotado como histórico).
- Nota de rewrite presente em `docs/CHANGELOG.md` com data + [[ADR-315]].
- `dev/check_adr_anchors.py` e `dev/check_doc_links.py` verdes (a Parte B não
  toca `id`/filename/anchors — só prosa).

## Rollback

- **Parte A (Ruleset):** rollback é a própria reativação — o estado-alvo é
  `enforcement=active`. Se o script falhar entre desabilitar e reativar, a ação
  de recuperação é **executar o PUT de reativação manualmente** (idempotente) e
  auditar `gh api .../rulesets/15884038` até `active`. **Nunca** deixar o repo
  em `disabled` ao encerrar a sessão.
- **Parte B (docs):** revert do commit de docs (mudança textual pura,
  reversível sem consequência de runtime).
- O force-push em si é irreversível — a rede de segurança é o backup off-site +
  tag `pre-public-flip-backup` de [[A34.l2]] / G0, não esta lane.

## CI

- **Parte A é operação de owner via `gh api`** (não passa por CI; é ação de
  configuração de repositório, auditável).
- **Parte B é docs-only** — mergeia sem CI de código, mas os gates de doc
  (`check_adr_anchors`, `check_doc_links`, `validate_frontmatter`) rodam no
  pre-commit.

## Referências

- Estratégia de rewrite e bypass: [[ADR-315]].
- Runbook do force-push (produz o mirror reescrito): [[A34.l18]]
  ([[TRACK-public-release-history-rewrite]]).
- Depende de: [[A34.l19]] (freeze de merges + deleção das 85 branches `agent/*`
  antes do rewrite).
- Backup/tag que serve de rede antes do force-push: [[A34.l2]].
- Flip que **não** pode ocorrer antes da reativação: [[A34.l22]].
- Plano canônico e gate G3: [[PLAN-public-release]] §Ondas (W3).
