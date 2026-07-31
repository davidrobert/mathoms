---
id: TRACK-public-release-flip
type: track
title: "Runbook — flip do repo para público + verificação pós-flip"
plan: PLAN-public-release
status: ready
created_at: "2026-07-08"
agent_role: general
tags:
  - type/track
  - area/security
  - status/ready
---

# Runbook — flip do repo para público + verificação pós-flip

> **Missão em 1 frase:** executar a última operação do plano
> [[PLAN-public-release]] — tornar `davidrobert/mathoms` público **in-place** —
> com um smoke de detecção que roda **ANTES** do flip (o flip é irreversível na
> prática) e uma verificação de hardening que roda **imediatamente depois**.
>
> **Quem executa:** o **owner**. É um ato de conta (Danger Zone / `gh api`) que
> agente nenhum tem permissão para disparar. O agente pode preparar/rodar o
> smoke pré-flip e a verificação pós-flip, mas o clique de `Change visibility`
> é do owner.
>
> **Pré-condição dura:** este runbook **só começa** com o gate **G8** habilitado
> — ou seja, todas as ondas anteriores (W0, W2, W1, W5, W6-min, W3, W4) verdes.
> Ver [[A34.l22]] e o critério de aceite global no [[PLAN-public-release]] §Verificação.

---

## Por que a ordem importa (leia antes de tudo)

O flip para público **não é reversível na prática**. Assim que o repo fica
público:

- crawlers/indexadores (Google, GitHub search, `grep.app`, arquivadores) podem
  capturar a árvore, o histórico e os metadados em **minutos**;
- voltar a privado **não desindexa** o que já foi lido — o dado vazado é
  permanente para quem já clonou/indexou;
- os **metadados GitHub** (855 PRs/issues/logs de CI) são imutáveis por git e
  o rewrite da Onda 3 **não os alcança** — o risco residual T3 já foi aceito em
  [[ADR-316]], mas isso é aceite de risco, não remediação.

Consequência operacional: **toda detecção acontece antes do flip**. O smoke
pré-flip (§1) é o último gate real; se ele acha qualquer coisa, **aborta-se o
flip** e volta-se ao saneamento (W1) ou ao rewrite (W3). O pós-flip (§3) só
verifica configuração de hardening que depende do estado público — nunca é
"ver se vazou PII" (tarde demais).

---

## 0. Checklist de gate G8 (todos MUST verdes antes de prosseguir)

Copiado do critério de aceite global do [[PLAN-public-release]] §Verificação.
Marque cada item; **qualquer NÃO aborta o runbook**.

- [ ] **(1) PII no git = zero** — gitleaks árvore **e** histórico verde (dupla),
      pós-rewrite W3.
- [ ] **(2) Gates W2 verdes** — `lint_no_real_pii` estendido, `check_sigilo_terms`
      estendido, `check_forbidden_paths` (bloqueia `_archive/`), gitleaks bloqueante
      ([[A34.l4]] · [[A34.l5]] · [[A34.l6]]).
- [ ] **(3) Branches zeradas** — 85 `origin/agent/*` deletadas ([[A34.l19]]).
- [ ] **(4) Ruleset reativado** — `main-protection` (id `15884038`) reativado e
      verificado pós-bypass do rewrite ([[A34.l20]]).
- [ ] **(5) GHAS + push protection ativos** — secret scanning + push protection
      ligados ([[A34.l15]]).
- [ ] **(6) 4 actions de terceiros SHA-pinned** — nenhuma tag flutuante ([[A34.l14]]).
- [ ] **(7) LICENSE + README EN presentes** — LICENSE coerente com [[ADR-313]];
      README com disclaimer e fronteira de idioma ([[A34.l16]]).
- [ ] **(8) Metadados T1 tratados** — itens T1 de PRs/issues/CI editados/deletados;
      residual T3 aceito em [[ADR-316]] ([[A34.l21]]).
- [ ] **(9) Fernet inócua** — rotação confirmada em prod (passe completo com
      `failed=0`, [[A34.l3]] / [[ADR-171]]); o blob histórico removido no rewrite.
- [ ] **(10) Backup íntegro por ≥30d** — mirror off-site restaurável + tag
      `pre-public-flip-backup` ([[A34.l2]]).
- [ ] **(11) FREEZE de merges ativo** — janela W3→W8 sem novos merges em `main`
      ([[A34.l19]]); confirmar que nenhum PR mergeou desde o rewrite.

> Se qualquer item acima estiver aberto, **PARE**. O flip não é o lugar de
> "resolver depois" — não há depois.

---

## 1. SMOKE PRÉ-FLIP (detecção — roda com o repo ainda PRIVADO)

O objetivo é reproduzir o que um observador externo veria **como se** o repo já
fosse público, sem depender de nenhum arquivo local não-commitado. Faça em um
**clone limpo** (não no working tree de trabalho — este tem `_scratch/`, venv,
artefatos gitignored que mascaram o resultado).

### 1.1 Clone limpo (árvore + histórico)

```bash
# diretório efêmero, fora do repo de trabalho
mkdir -p /tmp/mathoms-flip-smoke && cd /tmp/mathoms-flip-smoke
git clone --mirror git@github.com:davidrobert/mathoms.git mathoms.git
git clone mathoms.git worktree   # worktree materializa o HEAD
cd worktree
```

> **Por que `--mirror` + clone local:** o `.git` do mirror carrega **todo** o
> histórico e refs; o segundo clone materializa a árvore para os greps de
> working tree. Os dois juntos cobrem árvore **e** histórico sem baixar duas
> vezes da rede.

### 1.2 Gates de PII / sigilo (devem sair VERDES aqui — inverso do G2)

Em W2 esses gates rodaram **vermelhos** no HEAD contaminado (prova de detecção).
Aqui, pós-saneamento, devem sair **verdes**:

```bash
python3 tests/utils/lint_no_real_pii.py --all-files   # PII (CPF + endereço + domínio, estendido em A34.l4)
python3 dev/check_sigilo_terms.py                      # atribuição metodológica (superset, A34.l5)
python3 dev/check_forbidden_paths.py                   # _archive/ e paths bloqueados (A34.l6)
```

Todos devem retornar **exit 0 / zero hits**. Qualquer hit = abortar.

### 1.3 gitleaks — árvore E histórico (dupla varredura)

```bash
# árvore atual (working tree do clone materializado)
gitleaks detect --source=. --no-git --redact --exit-code=1

# histórico completo — TODAS as refs, direto do MIRROR bare (não do clone local,
# que só materializa o que é alcançável do HEAD e perderia branches/tags).
# Consistente com a validação dupla do rewrite (TRACK-public-release-history-rewrite §4).
git -C ../mathoms.git log --all -p | gitleaks detect --pipe --redact --exit-code=1
```

Ambos devem sair **exit 0**. Rodar o histórico contra o **mirror** (`../mathoms.git`)
cobre todas as refs que o rewrite tocou; rodar contra o clone `worktree` deixaria
refs não-alcançáveis do HEAD fora da varredura. `--redact` garante que o próprio
output do smoke não vira nova cópia de PII (este terminal/log pode ser capturado).

### 1.4 Grep manual dos padrões conhecidos (defesa em profundidade)

Os gates automáticos podem ter lacuna; varra os padrões do anexo
[audit-2026-07-08.md](../audit-2026-07-08.md) **por padrão**, nunca colando o
valor real. Rode contra árvore **e** histórico (`git grep` só vê o HEAD;
`git log --all -S` vê o histórico):

```bash
# CPF com máscara de formato (não o valor real) — árvore + histórico
git grep -nE '[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}' -- ':!*.lock' || echo "OK arvore"
git log --all -p -S'.' --pickaxe-regex \
  -G'[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}' | head -1 && echo "REVISAR" || echo "OK historico"

# atribuição metodológica nominal (KR3) — deve ser vazio no superset público
git grep -niE '(perini|cerbasi|auvp|raul sena|viver de renda)' \
  -- 'config/prompts/**' '*.md' 'README*' || echo "OK atribuicao"

# placa de veículo brasileira (formato antigo + Mercosul), endereço, matrícula
git grep -nE '[A-Z]{3}-?[0-9][A-Z0-9][0-9]{2}' -- 'docs/**' 'backend/**' 'pipeline/**' || echo "OK placas"

# path de máquina local (username vaza estrutura) — regex genérico, não hardcode
git grep -nE '/Users/[^/ ]+/' || echo "OK paths-locais"
```

> **Regra de dados:** ao registrar o resultado no PR/issue de fechamento, cite
> **padrão + path:linha**, nunca o valor. Placeholders permitidos no relato: CPF
> `123.456.789-09`, "Rua Exemplo, 100", "Titular"/"Cônjuge", "R$ X". O anexo de
> auditoria é MASCARADO por design — não o "atualize" com valores reais.

### 1.5 Veredito do smoke

- **Tudo zero** → o flip está liberado. Prossiga para §2.
- **Qualquer hit** → **ABORTE**. Não flipe. Classifique:
  - hit só na **árvore** → volta para W1 (saneamento do HEAD);
  - hit no **histórico** (não na árvore) → volta para W3 (rewrite incompleto);
  - hit de **atribuição/sigilo** → volta para [[A34.l12]] / gate [[A34.l5]].
  Corrija, re-rode W3 (se histórico) e **repita o smoke inteiro** do §1.1.

---

## 2. Ato de flip (SÓ o owner)

Pré-requisitos imediatos: §0 todo verde **e** §1 com veredito limpo **na mesma
janela** (não flipe com um smoke de dias atrás — um merge acidental durante o
FREEZE invalida o resultado; confirme que o SHA de `origin/main` não mudou desde
o smoke).

```bash
git ls-remote origin refs/heads/main   # deve ser o MESMO SHA do smoke §1.1
```

### 2.1 Via UI (recomendado — confirmação explícita)

1. `Settings` → role até **Danger Zone**.
2. **Change repository visibility** → **Make public**.
3. Digitar `davidrobert/mathoms` para confirmar.

### 2.2 Via `gh` (alternativa)

```bash
gh repo edit davidrobert/mathoms --visibility public --accept-visibility-change-consequences
```

> O flag `--accept-visibility-change-consequences` é a confirmação explícita que
> a API exige — é o equivalente ao "digite o nome do repo" da UI. Só o owner tem
> escopo para isso.

**Anuncie** no canal de operação: "repo `davidrobert/mathoms` flipado para
público em `<timestamp UTC>` — iniciando verificação pós-flip".

---

## 3. Verificação PÓS-FLIP imediata (nos primeiros minutos)

Roda **logo após** o flip. Não é detecção de PII (isso foi §1, tarde demais
agora) — é confirmar que o **hardening** que só faz sentido em repo público está
efetivamente ativo. Blast-radius de cada item é uma janela de exposição a partir
de agora.

### 3.1 Ruleset `main-protection` ativo

```bash
gh api repos/davidrobert/mathoms/rulesets | \
  jq '.[] | select(.id==15884038) | {name, enforcement}'   # enforcement == "active"
```

Deve estar `active` (o bypass do rewrite em [[A34.l20]] foi temporário; se
ficou aberto, **feche agora** — public + bypass = qualquer um com fork tenta
force-push regras). KR5 do plano.

### 3.2 GHAS + secret scanning + push protection

```bash
gh api repos/davidrobert/mathoms | \
  jq '.security_and_analysis | {secret_scanning: .secret_scanning.status,
      push_protection: .secret_scanning_push_protection.status}'   # ambos "enabled"
```

Ambos `enabled` ([[A34.l15]]). Em repo público GHAS é grátis; push protection
barra commit futuro que reintroduza segredo.

### 3.3 Permissions dos workflows = read-only default

```bash
git grep -L 'permissions:' .github/workflows/*.yml   # deve listar ZERO arquivos
git grep -n 'permissions:' .github/workflows/*.yml    # confirmar read-all/mínimo no topo
```

Nenhum workflow sem `permissions:` declarado; default mínimo ([[A34.l13]]).
Em repo público, um workflow com `write` implícito é superfície de supply-chain.

### 3.4 Actions require-approval para first-time contributors

`Settings` → `Actions` → `General` → **Fork pull request workflows** → "Require
approval for first-time contributors" (ou mais restritivo). Confirmar via UI —
não há campo estável na API pública para isto. Sem isso, o primeiro PR externo
roda Actions sem aprovação.

### 3.5 Actions de terceiros SHA-pinned

```bash
git grep -nE 'uses:.*(autoupdate-action|action-semantic-pull-request|labeler|pr-size-labeler)' \
  .github/workflows/ | grep -vE '@[0-9a-f]{40}' && echo "REVISAR: tag flutuante" || echo "OK: tudo SHA-pinned"
```

Zero hits sem `@<sha40>` ([[A34.l14]]).

### 3.6 LICENSE / README visíveis

```bash
gh api repos/davidrobert/mathoms | jq '{license: .license.spdx_id}'   # coerente com ADR-313
gh api repos/davidrobert/mathoms/readme | jq -r '.name'               # README presente
```

`license.spdx_id` bate com [[ADR-313]] (ex.: BSL-1.1 aparece como
`NOASSERTION`/custom — verificar que o arquivo `LICENSE` existe e o texto é o
decidido); README com disclaimer de dogfood e fronteira de idioma ([[A34.l16]]).

### 3.7 Backup íntegro por ≥30d

Confirmar que o mirror off-site ([[A34.l2]]) + tag `pre-public-flip-backup`
seguem restauráveis e retidos por ≥30 dias. É a única rede se o pós-flip revelar
algo que precise de revert-de-configuração (não de conteúdo — conteúdo não
reverte).

```bash
git ls-remote <backup-mirror-url> refs/tags/pre-public-flip-backup   # tag existe
```

---

## 4. Plano de resposta se algo vazar pós-flip

O flip é irreversível **para conteúdo indexado**. Distinga o que é remediável do
que só é mitigável:

### 4.1 O que NÃO é reversível (aceite de risco, não remediação)

- **Metadados GitHub já indexados** (PRs/issues/CI logs) — aceite T3 em
  [[ADR-316]]. Deletar/editar o item **agora** reduz exposição futura mas não
  desfaz o que já foi lido/arquivado.
- **Conteúdo de git já clonado/indexado** por terceiros — voltar a privado não
  desindexa. Assumir permanente.

### 4.2 Resposta imediata (minimizar exposição futura)

1. **Voltar a privado** (`Settings` → Danger Zone → Make private) **reduz a
   janela** de novos clones/indexação — faça-o se o vazamento for PII de
   terceiro ou segredo vivo, mesmo sabendo que não desfaz o passado.
2. **Rotacionar qualquer segredo** que apareça — se, contra o esperado, uma
   Fernet/API key viva aparecer: rotação imediata via a task
   `rotate_fernet_secrets` ([[ADR-171]]), invalidar tokens, e tratar como
   incidente de segurança
   (`SECURITY.md`).
3. **Editar/deletar o item de metadado** (PR/issue/comment/CI log) que vazou.
4. **Se PII de terceiro** (CPF, endereço, holerite de família/diarista):
   acionar a resposta LGPD do `SECURITY.md` — o dado é de titular que não é o
   owner; há dever legal de contenção e eventual notificação.

### 4.3 Postmortem

Registrar postmortem blameless: como o item passou pelo smoke §1 (gate que
falhou — lacuna de padrão? histórico não varrido? item de metadado fora do
escopo git?), com action item de estender o gate correspondente ([[A34.l4]] /
[[A34.l5]] / [[A34.l6]]) para que a regressão seja mecanicamente barrada. Um
vazamento pós-flip que o smoke deveria ter pego = falha do gate, não do operador.

---

## 5. Critérios de aceite (o track só fecha com todos)

- [ ] §0 checklist G8 completo (11 itens verdes).
- [ ] §1 smoke pré-flip com veredito **limpo** (gates verdes + gitleaks
      árvore/histórico zero + greps de padrão zero), no mesmo SHA do flip.
- [ ] §2 flip executado pelo owner; timestamp anunciado.
- [ ] §3 verificação pós-flip: Ruleset `active`, GHAS+push protection `enabled`,
      permissions mínimas, require-approval on, actions SHA-pinned, LICENSE+README
      presentes, backup restaurável.
- [ ] Registro de fechamento (PR/issue) cita achados **por padrão + path**, sem
      valor real.
- [ ] [[PLAN-public-release]] atualizado: G8 fechado; lane [[A34.l22]] concluída.

## Anti-escopo

- **Não** disparar o flip via agente — é ato do owner (§2).
- **Não** "consertar PII" no pós-flip — se o smoke §1 achou algo, o flip **não
  acontece**; se achou no pós-flip, é resposta a incidente (§4), não parte do
  fluxo feliz.
- **Não** reabrir decisões de W0 (licença, escopo, metadados) — estão em
  [[ADR-313]]–[[ADR-320]]; divergência é emenda de ADR **antes**, não aqui.
- **Não** tocar o histórico neste track — rewrite é [[TRACK-public-release-history-rewrite]]
  (W3), pré-requisito deste.
