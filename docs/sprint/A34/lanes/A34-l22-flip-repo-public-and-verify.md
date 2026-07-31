---
id: A34.l22
type: lane
title: "Flip para público + verificação pós-flip (track)"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: flip-repo-public-and-verify
adrs: ["[[ADR-316]]"]
depends_on: ["[[A34.l20]]", "[[A34.l21]]", "[[A34.l15]]", "[[A34.l16]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/seguranca
---

# A34.l22 — `flip-repo-public-and-verify` (W8 · Flip)

## Problema

O flip do `davidrobert/mathoms` para público é a **última operação do plano
[[PLAN-public-release]]** e, na prática, **irreversível**: uma vez que o repo
foi clonado por um terceiro anônimo, PII ou IP que escapem já saíram do
controle — deletar o repo depois não desfaz o clone. Toda a defesa está em
**não errar a sequência**: o flip só pode acontecer depois que as ondas
must (W0→W2→W1/W5→W6-min→W3/W4) fecharam seus gates, e a verificação
pós-condição precisa provar que nenhuma das **três camadas de contaminação**
(HEAD, histórico git, metadados GitHub) ficou aberta.

Este é um **ato do owner** — envolve `gh repo edit --visibility public` +
reativação do Ruleset + smoke de percepção externa. Não é automatizável nem
delegável a agente sem decisão humana no laço. O **checklist operacional
passo-a-passo** (comandos, ordem, ponto-de-não-retorno) vive no track
self-contained [[TRACK-public-release-flip]]; esta lane define **o gate de
entrada, o critério de aceite e o rollback residual**.

## Escopo

1. **Pré-condição de dependências (must fechadas):**
   - [[A34.l20]] — Ruleset `main-protection` (id `15884038`) **reativado e
     verificado** após o bypass da janela W3; hash-refs de ADRs atualizadas.
   - [[A34.l21]] — itens T1 de metadados GitHub triados ([[ADR-316]]).
   - [[A34.l15]] — GHAS + push protection ativos; Fernet dummy em secret.
   - [[A34.l16]] — LICENSE + README EN com disclaimer presentes.
   - (Transitivas via o grafo do plano: W0/G0, W2/G2, W1/G1, W3/G3.)
2. **SMOKE de clone anônimo — ANTES do flip.** Clonar `main` como um terceiro
   sem credenciais veria (fresh `git clone` + `git log --all`), e rodar a
   varredura PII+sigilo uma última vez sobre árvore **e** histórico. Detalhe
   do comando no track; o critério é **zero hits** para os padrões de
   CPF / endereço / placa / nome-de-terceiro / patrimônio-nominal / atribuição
   metodológica nominal (`perini|cerbasi|auvp|raul sena|viver de renda`).
3. **Flip.** Executar a mudança de visibilidade conforme o track, com FREEZE
   de merges (W3) ainda ativo até a confirmação.
4. **Verificação pós-flip** (a pós-condição do plano, §Verificação G8): rodar
   a checklist de 11 itens e registrar o resultado. Só então liberar o FREEZE.
5. **Registro de aceite.** Anexar o resultado do smoke + da verificação G8 ao
   track e sinalizar o fechamento do marco "público-seguro" no
   [[PLAN-public-release]].

## Critério de aceite (verificável)

Critério de aceite **global G8** do plano ([[PLAN-public-release]] §Verificação)
satisfeito — os 11 itens, todos verdes:

1. `gitleaks` sobre árvore **e** histórico = 0 (validação dupla).
2. Gates W2 (PII + sigilo + secrets) verdes no HEAD público.
3. 85 branches `origin/agent/*` deletadas (`git branch -r | grep agent/` vazio).
4. Ruleset `main-protection` reativado e verificado (`gh api .../rulesets`).
5. GHAS + push protection ativos.
6. 4 actions de terceiros SHA-pinned (`git grep -n "uses:.*@v[0-9]" .github/workflows/` vazio para elas).
7. LICENSE (coerente com [[ADR-313]]) + README EN com disclaimer presentes.
8. Itens T1 de metadados GitHub tratados; residual T3 aceito em [[ADR-316]].
9. Fernet confirmada inócua (rotação [[ADR-171]] com `failed=0`, W0).
10. Backup off-site íntegro e restaurável (tag `pre-public-flip-backup`, W0).
11. **SMOKE FINAL** — clone anônimo + grep dos padrões PII/atribuição = **zero**,
    executado **ANTES** do flip.

Aceite da lane: **smoke = zero** e os 11 itens registrados no track. Enquanto
qualquer item estiver vermelho, o flip **não ocorre** — falha adjacente ao
marco é preferível a vazamento irreversível.

## Rollback

Operação **irreversível na prática** — não há rollback verdadeiro pós-clone
anônimo. As redes são todas **pré-flip**:

- **Sequência de segurança:** o smoke roda ANTES do flip; se der hit, aborta e
  reabre a onda de saneamento correspondente (W1/W3) — não flipar.
- **Contenção pós-flip parcial:** se um vazamento for detectado após o flip,
  o único caminho é (a) `gh repo edit --visibility private` imediato
  (reduz janela, não desfaz clones já feitos), (b) invalidar o segredo/PII
  exposto na fonte (rotação Fernet já feita em W0), (c) incidente LGPD via
  `SECURITY.md`. Isso é **mitigação**, não rollback.
- **Backup:** o mirror off-site (W0, [[A34.l2]]) preserva o estado privado
  original — serve para auditoria/recuperação de conteúdo, não para "desfazer"
  a exposição pública.

**CI obrigatório:** esta lane toca configuração de repo (visibilidade,
Ruleset) e depende de suíte + gates verdes no HEAD público; o smoke e a
verificação G8 rodam sobre o estado que o CI atesta. O ato de flip em si é
manual do owner, mas nenhum passo prossegue sem o gate verde.

## Referências

- Plano canônico e gate global G8: [[PLAN-public-release]] §Verificação.
- Checklist operacional passo-a-passo: [[TRACK-public-release-flip]].
- Aceite de risco de metadados imutáveis: [[ADR-316]].
- Dependências must: [[A34.l20]] (Ruleset) · [[A34.l21]] (metadados) ·
  [[A34.l15]] (GHAS + Fernet secret) · [[A34.l16]] (LICENSE + README).
- Pré-condições de W0: [[A34.l2]] (backup mirror) · [[A34.l3]] (rotação Fernet).
- Rewrite adjacente (penúltima operação): [[A34.l18]] ([[TRACK-public-release-history-rewrite]]).
