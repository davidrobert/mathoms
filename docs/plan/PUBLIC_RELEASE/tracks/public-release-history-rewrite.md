---
id: TRACK-public-release-history-rewrite
type: track
title: "Runbook — rewrite de histórico git para release pública (git-filter-repo)"
plan: PLAN-public-release
status: ready
created_at: "2026-07-08"
agent_role: general
tags:
  - type/track
  - area/security
  - area/ci
  - status/ready
---

# Runbook — rewrite de histórico git (`git-filter-repo`) para release pública

> **Missão em 1 frase:** reescrever o histórico completo do repositório
> `davidrobert/mathoms` (blobs de PII + mensagens de commit com patrimônio
> nominal + identidade de autoria) numa passada de `git-filter-repo` sobre um
> clone `--mirror`, validar em dobro que zerou, deletar as branches `agent/*`,
> e force-push com bypass owner do Ruleset — deixando o repo pronto para o flip.
>
> **Lane:** [[A34.l18]] (Onda 3 do [[PLAN-public-release]]). **ADR canônica:**
> [[ADR-315]] (estratégia) + [[ADR-317]] (mailmap). **Blast radius:** máximo — é
> a **única operação irreversível** do plano. Sem backup restaurável (W0), NÃO
> comece.

## ⚠️ Natureza da operação

- **Irreversível na prática.** `--replace-text`/`--replace-message`/`--mailmap`
  reescrevem **todos** os SHAs do histórico. Não há `git revert`; a única volta é
  restaurar do backup mirror ([[A34.l2]]).
- **Serial, adjacente ao flip.** É a penúltima onda (W3), executada com FREEZE de
  merges ativo ([[A34.l19]]) e imediatamente antes de W8 ([[TRACK-public-release-flip]]).
- **Dois executores.** A maior parte é **agente**; os passos de bypass do Ruleset e
  o `force-push` em `main` são **owner-only** (marcados 🔒 abaixo).

---

## 0. Pré-condições (bloqueiam o início — não pule)

Confirme **todas** antes de tocar em qualquer clone. Se uma falhar, PARE e reporte.

| # | Pré-condição | Como confirmar | Dono |
|---|---|---|---|
| 0.1 | Backup mirror off-site restaurável + tag `pre-public-flip-backup` no HEAD de `main` ([[A34.l2]]) | Clone de teste do backup: `git clone --mirror <backup-url> /tmp/restore-test && git -C /tmp/restore-test log -1`. Confirmar tag existe em `origin`: `git ls-remote --tags origin pre-public-flip-backup` | Owner + agente |
| 0.2 | Rotação Fernet confirmada em prod ([[A34.l3]] · [[ADR-171]]) — `failed=0` | Saída da task `rotate_fernet_secrets` (`celery -A backend.app.worker call …`, runbook `fernet_rotation.md`) com `failed` zerado em todos os targets. O rewrite remove o **blob** do `.env`, mas a key só é inócua se rotacionou em prod (não verificável do repo) | Owner |
| 0.3 | FREEZE de merges anunciado e ativo ([[A34.l19]]) até o fim de W8 | Anúncio no canal + auto-merge desabilitado em PRs abertos | Owner |
| 0.4 | [[ADR-315]] e [[ADR-317]] `Decidido` (estratégia + identidade de mailmap) | `git grep -l 'status: Decidido' docs/adr/315-*.md docs/adr/317-*.md` | Owner |
| 0.5 | Onda 1 (saneamento do HEAD) mergeada — o rewrite trata o **histórico**, não o HEAD | Gate G1 verde no plano | Agente |
| 0.6 | Espaço em disco ≥ 3× o tamanho do repo (clone mirror + working) | `df -h` | Agente |

---

## 1. Ferramenta: `git-filter-repo` (por que NÃO as alternativas)

Use **exclusivamente** [`git-filter-repo`](https://github.com/newren/git-filter-repo)
(recomendado oficial do próprio git; supersede `git filter-branch`). Instale:

```
pip install git-filter-repo   # ou: brew install git-filter-repo
git filter-repo --version
```

Rejeições registradas em [[ADR-315]]:

- **BFG Repo-Cleaner** — não faz `--replace-message` nem `--mailmap` numa passada;
  exigiria múltiplas ferramentas e múltiplos rewrites (cada um reescreve SHAs de
  novo → mais chance de erro). Além disso trata pior arquivos ainda no HEAD.
- **`git rebase -i` / squash-to-genesis** — colapsar 1.862 commits num só destrói a
  arqueologia de decisão (ADRs referenciam hashes; ver passo 6) e não remove blobs de
  branches não alcançáveis pelo `main`.
- **Shallow clone / `--depth`** — não reescreve nada; apenas trunca localmente. O
  histórico continua público no push. Não é solução.

`git-filter-repo` faz paths + regex de conteúdo + mensagens + identidade **numa única
reescrita determinística**, minimizando a janela de erro.

---

## 2. Clone `--mirror` dedicado (nunca reescrever o working tree ativo)

`git-filter-repo` recusa rodar num repo com working tree "sujo" e reescreve refs de
forma destrutiva — **sempre** opere num clone `--mirror` isolado.

```
cd /tmp
git clone --mirror git@github.com:davidrobert/mathoms.git mathoms-rewrite.git
cd mathoms-rewrite.git

# Snapshot local extra do estado pré-rewrite (rede além do backup off-site)
cp -a /tmp/mathoms-rewrite.git /tmp/mathoms-rewrite.git.PRE
```

**Verificação:** `git for-each-ref | wc -l` deve listar todas as refs (main + ~85
`agent/*` + tags). Anote o número — usado na conferência do passo 5.

---

## 3. Sequência de rewrite (uma passada lógica, na ordem)

> **Ordem importa:** paths primeiro (remove blobs inteiros), depois regex residual
> (limpa o que sobrou embutido em arquivos que ficam), depois mensagens, depois
> identidade. Cada sub-passo é um `git filter-repo` separado no **mesmo** mirror.
> Executor: **agente**. Referencie o anexo [audit-2026-07-08.md](../audit-2026-07-08.md)
> §2 para a lista viva de paths/hashes — **re-varra** (`git log --all -- <path>`)
> porque ocorrências novas podem ter surgido após a data da auditoria.

### 3.1 — `--invert-paths`: remover blobs de PII do histórico inteiro

Arquivos/diretórios que carregam PII real em qualquer ponto do histórico (audit §2):

```
git filter-repo \
  --invert-paths \
  --path config/family_members.json \
  --path config/decisions.md \
  --path config/goals.json \
  --path config/categorization.json \
  --path-glob 'members/*' \
  --path-glob 'processed/*' \
  --path .env \
  --path backend/.env \
  --path-glob '_archive/*'
```

**Verificação:** `git log --all --oneline -- config/family_members.json` deve
retornar **vazio**; idem para cada path. `git log --all -- _archive/ | head` vazio.

> **Nota `_archive/`:** se a Onda 1 ([[A34.l7]]) já deletou `_archive/` do HEAD, o
> `--path-glob '_archive/*'` aqui cobre os commits **históricos** onde ele existiu.
> Manter no comando por segurança (idempotente se já ausente).

### 3.2 — `--replace-text`: regex de PII residual em arquivos que permanecem

PII embutida em arquivos que **não** podem ser deletados (código, testes, docs que
ficam). Crie `/tmp/replacements.txt` (fora do repo, gitignored por natureza):

```
# formato: literal==>substituto   OU   regex:PADRÃO==>substituto
regex:\d{3}\.\d{3}\.\d{3}-\d{2}==>123.456.789-09
regex:Rua T[a-zç ]+ da S[a-zç ]+, ?61==>Rua Exemplo, 100
literal:<endereço-residencial-real>==>Rua Exemplo, 100
regex:[A-Z]{3}\d[A-Z0-9]\d{2}==>ABC1D23
literal:<sobrenome-da-família>==>Exemplo
```

```
git filter-repo --replace-text /tmp/replacements.txt
```

> **Regra de dados:** monte `/tmp/replacements.txt` a partir do audit **por
> path:linha + tipo** (CPF, endereço, placa, sobrenome), copiando os literais reais
> do repo local — **NUNCA** cole PII real neste runbook nem no commit. O arquivo de
> replacements é efêmero: apague (`shred -u /tmp/replacements.txt`) após o rewrite.

**Verificação:** `git grep -I -n -E '\d{3}\.\d{3}\.\d{3}-\d{2}' $(git rev-list --all)`
não deve retornar CPF com dígito verificador válido (o placeholder `123.456.789-09` é
inválido de propósito). Idem grep do endereço/placas/sobrenome.

### 3.3 — `--replace-message`: patrimônio nominal em ~100 mensagens de commit

`--invert-paths` **não** toca mensagens de commit (audit §2: ~100 msgs com nome da
família, ~20 com valores). Crie `/tmp/message-replacements.txt`:

```
regex:R\$ ?[\d\.]+(k|mil|M|milh(ão|ões))?==>R$ X
literal:<sobrenome-da-família>==>Exemplo
regex:patrim[ôo]nio de [\d\.,]+==>patrimônio de R$ X
```

```
git filter-repo --replace-message /tmp/message-replacements.txt
```

**Verificação:** `git log --all --format='%s %b' | grep -iE '<sobrenome>|R\$ [0-9]'`
= vazio (rode com o literal real localmente, não neste doc).

### 3.4 — `--mailmap`: identidade de autoria pública (813 commits)

Decisão de identidade pública vem de [[ADR-317]] (e-mail pessoal em 813 commits como
autor + 26 como committer; e-mail corporativo em 1.902). Crie `/tmp/public.mailmap`
com a identidade **decidida na ADR** (exemplo de forma — use os valores reais da ADR;
NÃO commite este arquivo nem cole os e-mails reais em doc público):

```
# Nome Público <email-publico> <EMAIL-PESSOAL-ANTIGO>
# Nome Público <email-publico> <EMAIL-CORP-ANTIGO>
```

```
git filter-repo --mailmap /tmp/public.mailmap
```

**Verificação:** `git log --all --format='%ae %ce' | sort -u` mostra somente a(s)
identidade(s) sancionada(s) por [[ADR-317]]. Nenhum Gmail pessoal se a ADR decidiu
suprimí-lo.

---

## 4. Validação DUPLA (gate G3 — ambos zero, sem exceção)

Uma única varredura não basta: uma cobre a **árvore final**, a outra o **histórico
completo** (blobs alcançáveis por qualquer ref). Ambas devem sair **zero**.

```
# (A) árvore reescrita — checkout do HEAD do mirror num working tree temporário
git -C /tmp/mathoms-rewrite.git worktree add /tmp/rw-head HEAD 2>/dev/null || true
gitleaks detect --no-git --source /tmp/rw-head --redact --exit-code 1

# (B) histórico completo — todo o diff de todos os commits de todas as refs
git -C /tmp/mathoms-rewrite.git log --all -p | \
  gitleaks stdin --redact --exit-code 1
```

Complementar (padrões de PII que gitleaks não pega por default):

```
# CPF válido, endereço, placa, sobrenome — nos blobs de todas as refs
git -C /tmp/mathoms-rewrite.git grep -I -n -E \
  '\d{3}\.\d{3}\.\d{3}-\d{2}' $(git -C /tmp/mathoms-rewrite.git rev-list --all) | head
```

**Critério:** as duas execuções gitleaks retornam exit 0 (nenhum leak) e o grep
complementar de PII = vazio. Qualquer hit → voltar ao passo 3, ajustar
replacements, **re-rodar do clone `.PRE`** (não empilhar rewrites sobre rewrites).

> ⚠️ **Validação verde ≠ Camada 3 limpa.** Este gate prova que a **árvore + o
> histórico do mirror** estão limpos — NÃO que o GitHub parou de servir o conteúdo
> antigo. Após o force-push (passo 7), o GitHub **mantém em cache os commits
> referenciados por PRs**: `/{repo}/pull/{n}/commits/{sha}` continua entregando o
> blob/mensagem pré-rewrite mesmo com o SHA órfão. O rewrite **não** purga isso.
> A remoção do cache é passo **T4 da [[A34.l21]]** (ticket ao GitHub Support com a
> lista de SHAs pré-rewrite) ou a deleção do repo (Opção 2, [[ADR-316]]). Exporte
> a lista de SHAs pré-rewrite agora (`git -C .PRE rev-list --all > /tmp/pre-rewrite-shas.txt`)
> — a l21 anexa ao ticket.

---

## 5. Deletar as ~85 branches `origin/agent/*` (agente)

Branches `agent/*` também vão a público e carregam blobs/mensagens não alcançáveis
pelo `main`. Delete **no mirror** antes do push (o push com `--mirror` sincroniza a
deleção para o remoto).

```
# Listar (conferir contagem vs. audit: ~85)
git -C /tmp/mathoms-rewrite.git for-each-ref --format='%(refname)' refs/heads/agent/ | wc -l

# Deletar todas as refs agent/* do mirror
git -C /tmp/mathoms-rewrite.git for-each-ref --format='%(refname)' refs/heads/agent/ | \
  xargs -n1 git -C /tmp/mathoms-rewrite.git update-ref -d
```

**Verificação:** `git -C /tmp/mathoms-rewrite.git for-each-ref refs/heads/agent/`
= vazio. Confirme que a tag `pre-public-flip-backup` **não** foi deletada (é a rede
de segurança) — decida em [[ADR-315]] se a tag deve ir ao público ou ficar só no
backup off-site; se privada, delete-a do mirror também.

---

## 6. Atualizar hash-refs em ADRs + nota de rewrite (agente)

O rewrite muda **todos** os SHAs. ~10 ADRs citam hashes literais (o audit §2 mapeou;
ex.: `docs/adr/315-*.md`, ADRs que referenciam `ae340c60`/`90279c68`/`e55fb489`).
Como os hashes antigos deixam de existir:

- **Não tente remapear 1:1** (o mapa velho→novo do filter-repo existe em
  `.git/filter-repo/commit-map`, mas a maioria das refs em ADR é ilustrativa).
- Substitua a citação por uma **anotação**: `<hash histórico, invalidado pelo rewrite
  de W3 — ver [[ADR-315]]>`. A mecânica descrita na ADR permanece válida; só o
  ponteiro muda.
- Adicione **entrada no changelog** (`docs/CHANGELOG.md`) registrando o rewrite:
  data, motivo (release pública), que o histórico pré-rewrite vive só no backup
  off-site [[A34.l2]], e que SHAs anteriores a essa data são inválidos.

> Estes edits são commits **normais** no HEAD saneado (via PR pós-rewrite ou no
> próprio flip), não parte do mirror reescrito. Docs-only → sem gate de suíte.

---

## 7. Bypass do Ruleset + force-push + reativação (🔒 OWNER-ONLY)

O Ruleset `main-protection` (id `15884038`) enforça `non_fast_forward` — colide com o
force-push do histórico reescrito. Sequência **owner-only**, janela mínima:

```
# 7.1 (🔒 owner) desabilitar/bypass temporário do Ruleset
gh api repos/davidrobert/mathoms/rulesets/15884038 --jq '.enforcement'   # anotar estado atual
gh api -X PUT repos/davidrobert/mathoms/rulesets/15884038 -f enforcement=disabled

# 7.2 (🔒 owner) force-push do mirror reescrito para origin
git -C /tmp/mathoms-rewrite.git push --mirror --force origin

# 7.3 (🔒 owner) REATIVAR o Ruleset imediatamente e verificar
gh api -X PUT repos/davidrobert/mathoms/rulesets/15884038 -f enforcement=active
gh api repos/davidrobert/mathoms/rulesets/15884038 --jq '.enforcement'    # deve ser "active"
```

> `push --mirror` **sincroniza deleções** — as branches `agent/*` removidas no passo 5
> somem do remoto, e tags removidas idem. Confirme o inventário de refs (passo 2) antes
> de rodar; um `--mirror` erroneamente sincroniza um estado incompleto.

**Verificação (owner + agente):**
- `gh api repos/davidrobert/mathoms/rulesets/15884038 --jq '.enforcement'` == `active`
  (KR5: zero janela aberta).
- `git ls-remote --heads origin 'refs/heads/agent/*'` = vazio.
- Re-rodar a validação dupla (passo 4) **contra o `origin` reescrito** (clone fresco):
  `git clone --mirror git@github.com:davidrobert/mathoms.git /tmp/verify.git` +
  gitleaks histórico. Deve sair zero.
- FREEZE de merges permanece ativo até W8 concluir.

---

## 8. Rollback (se qualquer verificação falhar antes do flip)

Enquanto o flip (W8) **não** ocorreu, o repo ainda é privado — o rollback é seguro:

```
# (🔒 owner) desabilitar Ruleset, restaurar do backup mirror, reativar
gh api -X PUT repos/davidrobert/mathoms/rulesets/15884038 -f enforcement=disabled
git -C /tmp/restore-test push --mirror --force origin   # /tmp/restore-test = clone do backup A34.l2
gh api -X PUT repos/davidrobert/mathoms/rulesets/15884038 -f enforcement=active
```

**Verificação pós-rollback:** `git ls-remote origin` reflete o estado do backup; tag
`pre-public-flip-backup` presente; a suíte de gates volta ao baseline pré-rewrite.
Investigar a causa da falha (replacements incompletos, path faltante), corrigir a
partir do clone `.PRE`, e **repetir a onda inteira** — nunca empilhar um segundo
rewrite sobre um rewrite parcial.

> **Após o flip (W8), o rollback deste passo NÃO desfaz a exposição pública** — daí a
> validação dupla (passo 4) e o smoke de clone anônimo (W8) rodarem **antes** do flip.
> Metadados GitHub (855 PRs/issues/logs de CI) são irredutíveis por git e ficam fora
> do escopo deste rewrite — tratados em [[A34.l21]] / [[ADR-316]].

---

## Critério de aceite (gate G3)

- [ ] Rewrite executado em clone `--mirror` (paths → replace-text → replace-message → mailmap).
- [ ] Validação dupla verde: gitleaks sobre árvore **e** sobre histórico completo = 0.
- [ ] Grep complementar de PII (CPF válido/endereço/placa/sobrenome) em todas as refs = vazio.
- [ ] ~85 branches `origin/agent/*` deletadas (`ls-remote` vazio).
- [ ] Hash-refs em ~10 ADRs anotadas + nota de rewrite no changelog.
- [ ] Ruleset `main-protection` (id `15884038`) **reativado e verificado** (`enforcement=active`).
- [ ] Backup mirror off-site íntegro e restaurável ([[A34.l2]]).
- [ ] FREEZE de merges ativo até W8.

## Referências

- Lane: [[A34.l18]] · Plano: [[PLAN-public-release]] (Onda 3).
- ADRs: [[ADR-315]] (estratégia de rewrite) · [[ADR-317]] (mailmap) · [[ADR-316]] (metadados residuais).
- Anexo de auditoria (mapa de paths/hashes, mascarado): [audit-2026-07-08.md](../audit-2026-07-08.md) §1–§2.
- Pré-condições: [[A34.l2]] (backup) · [[A34.l3]] (Fernet) · [[A34.l19]] (freeze) · [[ADR-171]] (rotação Fernet).
- Próxima onda: [[TRACK-public-release-flip]] ([[A34.l22]], W8).
