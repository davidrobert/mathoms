# Runbook — Trem de auto-merge travado

> **ADR:** [[ADR-322]] (Decidido · 2026-07-09).
> **Owner:** davidrobert (único humano com poder de criar/rotacionar o PAT).
> **Sinal de entrada:** issue "CI: trem de auto-merge travado — ação
> necessária" (aberta pelo watchdog), warning `AUTOUPDATE_PAT ausente`
> no Actions, ou **cabeça** do trem parada >1h (é o que o watchdog mede —
> PR no meio da fila parado horas é vazão normal, ver Modelo mental).

---

## Modelo mental (30 segundos)

O Ruleset exige branch up-to-date com main (strict). O trem anda assim:
merge em main → `auto-update-prs.yml` faz update-branch em **1** PR (o
auto-merge mais antigo elegível) com a identidade do `AUTOUPDATE_PAT` →
CI roda → auto-merge squasha → push em main dispara o próximo ciclo.
Rede de segurança: schedule 2×/h no advance + watchdog 2×/h
(`automerge-watchdog.yml`).

**Vazão: 1 PR por ciclo completo de CI.** Com a fila cheia, esperar é o
estado normal — não sintoma. Medido em 2026-08-21: ~13 min por PR, ~2h
para drenar 9 PRs armados. Antes de procurar o que destravar, confirme
que não é só a fila andando.

**Congelar squash de docs** enquanto houver >2 PRs de código com
auto-merge: cada docs no `main` zera o verde da fila. DIRTY não entra no
trem — rebase + `--auto` só na cabeça, um de cada vez. Não rebaseie os
outros na mão.

**Invariante:** update-branch/push NUNCA pode sair como
`github-actions[bot]` — runs nascem `action_required` (0 jobs) e o CI
nunca roda. Por isso não existe fallback para `GITHUB_TOKEN`.

## 1. Diagnóstico rápido (nesta ordem)

```bash
# Estado da fila — quem está BEHIND/BLOCKED, quem tem auto-merge
gh pr list --state open \
  --json number,mergeStateStatus,autoMergeRequest,createdAt \
  --jq 'sort_by(.createdAt) | .[] | "\(.number) \(.mergeStateStatus) automerge=\(.autoMergeRequest != null)"'

# O que o trem decidiria agora (leitura pura, sem efeito)
python3 dev/ci_advance_automerge_train.py --dry-run

# Runs órfãos no head de um PR suspeito (action_required = CI nunca roda)
gh run list --commit "$(gh pr view <N> --json headRefOid --jq .headRefOid)" \
  --json status,conclusion,name
```

**A última linha do `--dry-run` separa os estados** — `update-branch #N` (vai
andar agora), `trem segurando: cabeça #N …` (cabeça em voo, fila atrás:
esperar), `trem em dia: nenhum PR elegível BEHIND` (fila vazia de verdade).
Até 2026-08-21 os dois últimos compartilhavam a mesma frase, e o hold com 5
PRs esperando aparecia como trem parado.

Desde 2026-08-25 ([[ADR-322]] §Emenda 2026-08-25) há mais dois, ambos
precedidos de `N update-branch recusado(s) em #…`: **teto de recusas atingido**
(`teto de 3 recusas atingido — a fila NÃO foi esgotada`) e **fila esgotada após
recusas** (`nada mais a atualizar`). A distinção importa: no primeiro caso
sobraram PRs que nem chegaram a ser tentados.

| Sintoma | Causa provável | Ação |
| --- | --- | --- |
| `trem segurando: cabeça #N em andamento` com PRs `BEHIND` atrás | Enfileiramento normal: o trem é serial por desenho ([[ADR-322]] §D1) e não pula cabeça rodando CI | esperar — atualizar o próximo desperdiça runs e pode livelock |
| PR nunca avança; log diz `skip #N: conflito de merge` | `DIRTY` — o trem só resolve `BEHIND`; conflito ele pula e o PR fica fora da fila | autor rebasa e pusha da própria conta |
| Warning `AUTOUPDATE_PAT ausente` no advance | Secret nunca criado ou PAT expirou | §2 |
| Runs `action_required` (0 jobs) no head | Push saiu como bot (fonte externa ao trem) | §3 |
| `All checks green` FAILURE em ~2-5s, 0 steps | Budget de Actions esgotado (runner não inicia) OU agregador stale de run superseded | §4 |
| PR verde, up-to-date, sem auto-merge | GitHub desabilitou auto-merge silenciosamente (agregador stale) | §4 |
| Trem parado com cabeça vermelha | Required check FAILURE real — o trem pula; PR sai da fila | autor corrige o PR |
| `N update-branch recusado(s) em #…` com `HTTP 403` | PAT sem escopo `workflow` diante de merge que traz mudança em `.github/workflows/**`. Desde 2026-08-25 a recusa é terminal só para aquele PR: **o run continua e tenta o próximo** | autor do PR recusado rebasa e pusha da própria conta (~30s) — push normal não passa pela API de update-branch. **Não** dar escopo `workflow` ao PAT: ele passaria a poder escrever um workflow que exfiltra os secrets do repo |
| `teto de 3 recusas atingido` | Merge de `main` trouxe mudança de workflow: **todos** os PRs BEHIND recusam pela mesma causa | esperar o run seguinte (~15min) ou rebasar os PRs afetados à mão; o teto existe para não varrer a fila inteira em vão |

## 2. PAT ausente/expirado (causa nº 1 de trem parado)

1. Criar fine-grained PAT em <https://github.com/settings/personal-access-tokens/new>:
   - **Repository access:** only `davidrobert/mathoms`
   - **Permissions:** Contents → Read and write · Pull requests → Read and write ·
     Issues → Read and write (issue de stall) · Actions → Read-only (estado dos
     required checks via `gh run list --commit`). Não use `statusCheckRollup`
     em script novo: fine-grained PAT não acessa check-runs via GraphQL
     (`Resource not accessible`; escopo Checks não existe mais para PATs).
   - **Expiration:** ≤90 dias
2. `gh secret set AUTOUPDATE_PAT` (cola o token)
3. Kick: `gh workflow run "Auto-update PR branches"`
4. Validar: próximo run do advance sem warning; update-branch aparece com
   `triggering_actor` = davidrobert, CI do PR dispara (não `action_required`).

> A identidade do PAT **não** pode entrar na bypass list do Ruleset
> (`gh api repos/davidrobert/mathoms/rulesets/15884038`) — token com
> contents:write + bypass = push direto em main latente.

## 3. Runs órfãos `action_required`

O watchdog kicka sozinho (empty commit via Git Data API) quando o PAT
existe. Manual, para 1 PR:

```bash
git fetch origin <branch>
git commit-tree "$(git rev-parse "origin/<branch>^{tree}")" -p "$(git rev-parse "origin/<branch>")" \
  -m "chore(ci): kick — re-dispara CI de runs action_required orfãos" \
  | xargs -I{} git push origin {}:refs/heads/<branch>
```

(push com sua credencial local = atribuição correta, CI dispara).

## 4. Auto-merge sumiu / agregador falhou em segundos

- **Budget esgotado:** annotation do job fala em spending limit. Rerun não
  resolve; é billing do owner. O trem retoma sozinho depois (schedule).
- **Agregador stale (run superseded):** o watchdog re-habilita sozinho se o
  head atual está verde. Manual: `gh pr merge <N> --squash --auto`.
- **Opt-out humano:** para o watchdog NÃO re-habilitar auto-merge de um PR,
  adicione label `wip`, `do-not-merge` ou `blocked`.

## 5. Andar o trem na mão (PAT indisponível, pressa)

```bash
python3 dev/ci_advance_automerge_train.py            # decide e atualiza 1 PR
python3 dev/ci_automerge_watchdog.py --dry-run       # o que o watchdog faria
```

Ambos usam sua identidade `gh auth` local — atribuição correta por
construção. Repita a cada merge até drenar a fila.

## 6. Rollback do mecanismo

```bash
gh workflow disable "Auto-update PR branches"
gh workflow disable "Auto-merge watchdog"
```

e drene a fila manualmente (§5). Revert do PR da [[ADR-322]] restaura o
estado anterior (action de terceiro + GITHUB_TOKEN) — **não recomendado**:
volta a classe `action_required` em lote.
