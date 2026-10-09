---
id: ADR-449
type: adr
title: "Major npm bloqueado por peer vira pausa versionada; desbloqueado vira migração"
status: Decidido
date: "2026-10-09"
relates_to:
  - "[[ADR-069]]"
  - "[[ADR-114]]"
  - "[[ADR-254]]"
  - "[[ADR-249]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 449"
  - "pausa de major npm"
  - "dependabot-major-pauses"
tags:
  - type/adr
  - status/decidido
  - area/ci
  - area/frontend
---

# ADR-449 — Major npm bloqueado por peer vira pausa versionada

## Contexto

Em 2026-10-09 havia 14 PRs do Dependabot abertos. Cinco eram majors npm que só
sabiam ficar vermelhos, porque um vizinho no lock declara peer que exclui o major:

| major | PRs | bloqueador no lock (peer) |
|---|---|---|
| eslint 10 (+ `@eslint/js`) | #2232 (frontend), #2230 e #2181 (ops) | `eslint-plugin-react@7.37.5`: `^3 … ^8 \|\| ^9.7` |
| typescript 7 | #2132 (frontend), #2180 (ops) | `@typescript-eslint/*@8.71.1`: `>=4.8.4 <6.1.0` |
| msw 3 | #2187 (frontend) | `@vitest/mocker@5.0.3`: `^2.4.9` (opcional) |

O `eslint-plugin-react` não tem release desde 2025-04, e o ESLint 9 é EOL desde
2026-08-06 ([version-support](https://eslint.org/version-support/)): esperar pelo
upstream não é plano. No msw 3, o npm 11 instala com o peer opcional fora do
range. O que quebra é o `tsc` (`onUnhandledRequest` virou `onUnhandledFrame`).

A política vivia espalhada: comentários do `dependabot.yml`, o runbook
[python_dependencies](../reference/runbooks/python_dependencies.md) (§Triagem:
`ignore` com data e condição de retomada, nunca `@dependabot ignore`) e o CLAUDE.md.
Faltava a regra de major npm e um gate que fizesse a pausa expirar.

**Por que ADR nova, e não emenda.** O architect sugeriu emendar a [[ADR-116]],
que decide a stack F7F-Local do console interno. Política de major cobre os dois
apps e todo o toolchain; pendurá-la ali quebra a atomicidade da [[ADR-182]] (uma
decisão por nota) e a esconde de quem procura por dependências. O sre-devops
propôs nota nova pequena que cita o runbook, e é o que esta é.

## Decisão

**D1 — Toolchain é um conjunto.** eslint, typescript e os plugins deles sobem de
major nos dois apps (`frontend`, `frontend-ops`). Grupo do Dependabot junta só o
que sobe junto (famílias do #2229). Teto de peer atrasado não se resolve com
grupo: o PR do grupo fica vermelho do mesmo jeito. Ele vira pausa (D2).

**D2 — Major bloqueado por peer não fica em PR aberto.** Ele vira:

1. `ignore` no `.github/dependabot.yml` com `versions: [">=N"]`, e com data, PR de
   origem, gatilho e prazo no comentário;
2. uma linha em `PAUSES` de `dev/check_dependabot_major_pauses.py` (hook
   `dependabot-major-pauses`, no Lint), que reprova:
   - o `ignore` sem pausa e a pausa sem `ignore` (igualdade de conjunto);
   - o **gatilho**: nenhuma entrada do `<app>/package-lock.json` exclui mais o
     major no `peerDependencies`. Isso vale tanto para o bloqueador que liberou
     quanto para o que saiu do lock;
   - o **prazo**: `review_by` vencido. Renovar é commit com justificativa.

Depois de mergeada a pausa, os PRs do Dependabot são fechados com link para ela.
`@dependabot ignore` segue proibido, porque guarda a supressão fora do git.

**D3 — Major desbloqueado entra como migração**, em PR humano, com rede de testes.
O PR leva o bump, a remoção do `ignore` e a linha de `PAUSES`; o Dependabot fecha
o dele sozinho. Regra nova de lint entra em `warn` num PR separado, e só depois
sobe para `error` ([[ADR-114]]).

**D4 — `eslint-plugin-react` sai pelo `@eslint-react/eslint-plugin`** (mantido,
peer `eslint: *`). O frontend usa 3 regras (`jsx-key`, `jsx-no-target-blank`,
`no-direct-mutation-state`), e o ops usa o `recommended`. Como o ESLint 9 já é
EOL, o prazo da pausa do eslint 10 é **2026-11-30**. TS 7 e msw 3 dependem de
upstream ativo e têm prazo **2027-01-31**.

**D5 — Pausas de 2026-10-09:**

| app | pausa | gatilho | prazo |
|---|---|---|---|
| frontend, ops | `eslint`, `@eslint/js` ≥10 | plugin com peer ^10, ou plugin fora do lock (D4) | 2026-11-30 |
| frontend, ops | `typescript` ≥7 | typescript-eslint aceitar o 7; a migração valida o `next build` | 2027-01-31 |
| frontend | `msw` ≥3 | Vitest aceitar o msw 3; a migração troca `onUnhandledFrame` e revalida o golden do `msw-lint.mjs` ([[ADR-069]]) | 2027-01-31 |

No ops, o `typescript` é pausado por `versions` e não por `semver-major`: o
5.9→6.0 segue abrindo, para o ops alcançar o 6.0 do frontend (D1).

## Alternativas rejeitadas

- **Deixar o PR aberto** "enquanto sobrar vaga" (runbook, saída 2). Serve para
  major que pede trabalho, não para major que nem instala. Vermelho permanente
  treina a ignorar vermelho.
- **`update-types: ["version-update:semver-major"]`.** Segura também majors que
  não estão bloqueados, como o TS 6 do ops.
- **Teste em `tests/`** (molde do `test_dependabot_redis_ceiling.py`). O
  `pipeline-tests` não roda em PR que só muda `<app>/package*.json`, então o
  gatilho dispararia atrasado, num PR alheio. O pytest fica só para a lógica, com
  data fixada; o relógio é do hook.
- **`engines`/`devEngines`/`packageManager`.** O updater do Dependabot avalia
  esses campos antes de existir PR (medido no #2157; docstring do
  `node-version-parity`).

## Consequências e limites

- A doc do Dependabot não diz se um `ignore` por `versions` também segura
  security update. As quatro dependências pausadas são devDependencies fora do
  bundle, e o `npm audit` do `security.yml` segue reportando CVE nelas.
- O mesmo peer `<6.1.0` barra o TS 6.1, que ainda não existe. Quando sair, o PR
  de minor fica vermelho: o gate desta ADR não o vê, porque só lê `>=N` de major.
- Range npm avaliado por subconjunto do semver. Hyphen range reprova
  (fail-closed).
- **Deferimento (2026-10-09; dono: owner do repo):** gate de mesma major entre os
  dois apps (D1). Hoje o TS diverge (6.0 vs 5.9), e o gate nasceria vermelho.
  Retomar quando o ops mergear o 6.0.

## Aceite

- `pytest tests/dev/test_dependabot_major_pauses.py`: 30 casos. A sonda matou
  9/9 mutantes, entre eles gatilho que nunca dispara, prazo ignorado, igualdade
  de conjunto quebrada nos dois sentidos, forma livre de `ignore`, peer ignorado,
  caret sem teto, hyphen aceito e `<` inclusivo.
- Hook no repo real: 5 pausas, todas com bloqueador lido do lock.
