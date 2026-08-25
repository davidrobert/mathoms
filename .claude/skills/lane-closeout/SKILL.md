---
name: lane-closeout
description: >-
  Verifica se a documentação de uma lane recém-entregue está atualizada com
  completude, corretude, consistência e precisão — cruzando o que os PRs
  mergearam contra o que a vault afirma — e responde se a sessão pode ser
  arquivada. Use quando o dono perguntar "a documentação está atualizada com
  tudo o que você fez e os follow-ups?", "posso arquivar esta sessão?",
  "terminei a lane, falta algo?", ou ao fechar qualquer lane com PR em `main`.
  Escopo é 1+ lane, não a vault inteira (isso é `audit-vault`). Canônica:
  ADR-302 (classe).
---

# lane-closeout

Procedimento do **loop principal** para o fechamento de uma lane: a doc reflete
o que foi entregue, e o que ficou aberto tem dono. Não é agente — orquestra o
check determinístico e delega julgamento aos especialistas do §Subagentes do
CLAUDE.md. Instância da classe decidida em [[ADR-302]] (skill = procedimento de
orquestração, não cabeça de julgamento nova).

**O problema que resolve, medido:** entre 2026-06-01 e 2026-08-09, 25 dos 770
commits em `main` foram corretivos de documentação de lane já entregue —
*"fecha as 8 lacunas de documentacao da A40.l18/l19"* (#1247), *"corrige 5
divergências entre a l21 shipada e o que estava escrito"* (#1254), *"nota da
A40.l24 afirmava fechado o que ficou aberto em 2 pontos"* (#1245). ~2,5 PRs por
semana que existem porque a pergunta foi feita **depois** do merge.

## Parâmetros

- `--lane <id>` (repetível) — escopo explícito. Preferido quando você sabe.
- `--pr <N>` — resolve as lanes do PR (por `ship_pr` **e** pelos arquivos que o
  merge tocou). Preferido logo após mergear.
- `--recent <N>` (default 5) — lanes tocadas pelos N últimos commits de
  `origin/main`. Use quando a sessão mergeou mais de um PR.

## Procedimento (5 camadas)

### Camada 0 — O par de verdade (obrigatória, antes de tudo)

Fixe os **dois lados** que vão ser comparados. Sem isso o julgamento vira
opinião sobre prosa:

1. **O que shipou** — `gh pr view <N> --json title,body,files` + `git show
   --stat <merge-sha>` de cada PR da lane. O corpo do PR é a declaração de
   intenção; o diff é o que de fato entrou. Onde divergirem, **o diff vence**.
2. **O que a vault afirma** — a lane em `docs/sprint/<X>/lanes/<id>.md`, o
   `_README` da sprint, e as ADRs que a lane declara em `adrs:`.

Nunca `rg --no-ignore` (varre worktrees e multiplica token sem contexto novo).

### Camada 1 — Check determinístico (sem token de LLM)

```bash
python3 .claude/skills/lane-closeout/references/check_closure.py --pr <N>
```

Cobre a metade **estrutural**: `ship_pr`/`ship_date` ausentes · deferimento
órfão em lane fechada · PR invisível no `_README` da sprint · contador de lanes
· rota de trabalho futuro para lane morta · `blocked` cuja dependência já
shipou. Cada achado é finding **sem julgamento** — corrija e siga.

A camada 3 **nunca** re-verifica o que este script cobre. Escopo é a lane
pedida: as ~159 lanes `shipped` legadas sem `ship_pr` são dívida histórica e
não entram.

> ⚠️ Verde aqui **não responde a pergunta do dono**. O script não lê sentido:
> não sabe se um número virou falso nem se um critério de aceite está
> invertido. Verde na camada 1 é pré-requisito, nunca veredito.

### Camada 2 — Universo semântico

A saída do script traz `docs que citam <lane>` — desde 2026-08-21 incluindo os
registros `docs/_MOC/*-active.md`. **É ali que o drift mora** — o #1341
corrigiu o `_README` da sprint, o #1340 corrigiu uma *outra* lane, e os 2
CLOSE-BLOCK reais da revisão de método de 2026-08-21 moravam em linha de
achado da `PIPELINE-REVIEWS-active`. Linha com `Disposição` viva citando a
lane que você está fechando **se reconcilia agora**: este closeout é o
detector primário da linha-zumbi (a `audit-vault` só a pega como rede de
segurança, com latência de rotação). Ler só o arquivo da lane é o erro que
faz a pergunta do dono render toda vez.

Some a esse conjunto: as ADRs em `adrs:`, o plano em `plan:`, e qualquer doc
que o PR tocou fora de `docs/sprint/`.

### Camada 3 — Julgamento nas 4 dimensões

Receitas completas, com o que procurar e como provar:
[`references/checklist.md`](references/checklist.md).

| Dimensão | A pergunta | O erro que ela pega |
|---|---|---|
| **Completude** | O que shipou está registrado? O que ficou tem dono? | deferimento órfão; PR invisível; ADR ainda `Proposto` |
| **Corretude** | Os números ainda são verdade **depois** do merge? | KR-A dizendo "5 → 0" quando eram 2 (#1341) |
| **Consistência** | Lane, `_README`, ADR e plano contam a mesma história? | critério de aceite **invertido** vs. o co-design (#1247) |
| **Precisão** | A afirmação é o que foi **medido** ou o que se **inferiu**? | "se o job falhar, a regravação é esperada" — o job nunca rodou (#1341) |

Regra que vale mais que as outras: **número citado se re-mede, não se relê.**
Se o PR mudou o que um número conta, rode a medição de novo agora. Achado com
medição citada de antes do merge é achado não verificado.

Delegue por gatilho do §Protocolo de delegação (paralelo, 1 mensagem, N `Agent`
calls) — `information-architect` para forma/roteamento, `product-manager` para
KR e critério de aceite, o especialista do domínio para o número. Peça
**decisão ou revisão**, nunca código.

### Camada 4 — Verify por citação dupla

Todo achado de severidade alta cita **o trecho do doc** e **o trecho da fonte**
(diff, código, ADR, output de medição) que se contradizem. **Sem os dois, o
achado é rebaixado ou descartado.** Herdado da camada 4 da `audit-vault`, pelo
mesmo motivo: sem isso a skill inventa lacuna e você paga PR por ruído.

### Camada 5 — Saída (responde as duas perguntas, nessa ordem)

```
## 1. A documentação está atualizada?
   completude   ✅ | ⚠️ <o quê> | ❌ <o quê>
   corretude    …
   consistência …
   precisão     …

## 2. Posso arquivar esta sessão?
   FECHADO | FECHADO COM RESSALVA | ABERTO

## 3. O que continua aberto (com dono)
   - <item> → [[lane-viva]] | dono nomeado | owner-gated
```

- **FECHADO** — camada 1 limpa, 4 dimensões verificadas, nada aberto sem dono.
- **FECHADO COM RESSALVA** — só `CLOSE-DRIFT`, e todo item aberto tem dono
  declarado. Arquiva; a ressalva vai no §3.
- **ABERTO** — ≥1 `CLOSE-BLOCK` ou ≥1 afirmação falsa. **Não arquiva.** Sai PR
  docs-only antes (docs-only dispensa `pytest`, mas `pre-commit run
  --all-files` continua obrigatório).

Nunca responda "está tudo certo" sem ter rodado a camada 1 e lido a camada 2.

## O que esta skill NÃO faz

- **Não audita a vault** — isso é `audit-vault` (escopo bucket, amostra
  rotativa, síntese em `AUDITS-active.md`). Aqui o escopo é 1 lane e o gatilho
  é o merge.
- **Não é gate — mas a metade estrutural já é, desde 2026-08-24.** Este
  `check_closure.py` continua fora do pre-commit e não bloqueia commit. O
  gatilho de promoção que esta seção previa **foi executado** pela [[A40.l59]]:
  `dev/check_lane_transition.py`, hook `lane-transition`, cobre `ship_pr` +
  `ship_date` + PR no registro da sprint (`_README` ∪ `_HISTORY`), lane nova sem
  linha de tabela, e lane não-terminal cujo `ship_pr` já mergeou.
  **Não reconstrua o gate** — estenda o que existe.

  Efeito medido em 2026-08-25, um dia depois: das 49 transições da A40, as **44
  anteriores** ao gate dão 19 passa / 25 barra; as **5 posteriores** dão
  5 passa / **0 barra**. Limite herdado e declarado: `T1`/`T2` leem
  `git diff --cached`, logo passam vazios sob `pre-commit run --all-files` (o
  caminho do CI) — são enforcement local. Só o `C1` lê estado e vale nos dois.
- **Não cria lane nem ADR automaticamente.** Propõe; o pickup é decisão do
  dono.

## Critério de aceite

- ≥1 achado por run vira correção mergeada, **ou** o veredito `FECHADO` se
  sustenta numa releitura do dono.
- Falso-positivo dos `CLOSE-BLOCK` ≤ 20% (a camada 4 é o filtro).
- Nenhum achado da camada 3 recria o que a camada 1 já pega.
- Run triável em < 15min para 1 lane.
