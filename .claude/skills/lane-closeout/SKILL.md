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

## Procedimento (6 camadas)

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

**Rode de uma árvore que esteja em `origin/main`.** O escopo é resolvido no
histórico remoto (`--pr`/`--recent` leem `origin/main`), mas a auditoria lê o
**working tree** — e o script não podia conciliar os dois até 2026-08-30:

```bash
git fetch origin && git checkout origin/main   # ou rebase a sua branch
python3 .claude/skills/lane-closeout/references/check_closure.py --pr <N>
```

Cobre a metade **estrutural**: `ship_pr`/`ship_date` ausentes · deferimento
órfão em lane fechada · PR invisível no `_README` da sprint · contador de lanes
· rota de trabalho futuro para lane morta · `blocked` cuja dependência já
shipou. Cada achado é finding **sem julgamento** — corrija e siga.

A camada 3 **nunca** re-verifica o que este script cobre. Escopo é a lane
pedida: as ~159 lanes `shipped` legadas sem `ship_pr` são dívida histórica e
não entram.

**Três desfechos, não dois** (desde 2026-08-26): `exit 0` estrutural limpo ·
`exit 1` achados · **`exit 2` NÃO VERIFICADO** — nenhuma lane no escopo, a
camada 1 não olhou nada. O terceiro existe porque escopo vazio saía como
"estrutural: 0 achados" + `exit 0`: a Onda 0 do `PLAN-ci-trust`, que entregou
por **track** e não por lane, recebeu esse verde em 3 PRs sem uma única
asserção ter rodado. Em `exit 2`, vá direto às camadas 2-4 e **não** registre
"camada 1 limpa".

**Banner de SUBSTRATO** (`CLOSE-BLOCK-07`/`CLOSE-DRIFT-05`, desde 2026-08-30).
Antes de qualquer achado o script imprime, se for o caso, que o conteúdo
auditado **não é** o conteúdo que o escopo resolveu — árvore que não contém o
merge do PR pedido, docs do universo auditado divergindo de `origin/main`, ou
árvore suja. Medido em 2026-08-29 no fechamento da [[A42.l15]]: rodado de um
checkout **2 commits atrás**, `--pr 1824` listou **2** citadores; da árvore em
`origin/main`, **4** — e os dois que sumiram (`A40.l96` e a
`LEDGER-CERTIFY-active`) eram exatamente onde o drift morava. O sub-reporte era
**silencioso**: nada na saída indicava substrato velho, e o closeout registrou
"camada 1 limpa" sobre a árvore errada.

O predicado é **divergência dentro do universo auditado** (`docs/sprint`,
`docs/_MOC`), não "árvore atrás" — commit atrás que não toca esses paths não
pode causar o sub-reporte, e acusá-lo seria ruído. E git que **não responde**
vira achado próprio, nunca silêncio: ausência de sinal não é sinal de frescor.

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

⚠️ **Essa lista vale o que a árvore vale.** `citers_of` lê o working tree; se o
banner de SUBSTRATO acendeu, a lista está incompleta e reler "a lista inteira"
ainda deixa drift de fora. Sincronize e rode de novo **antes** da camada 3.

### Camada 3 — Julgamento nas 4 dimensões

Receitas completas, com o que procurar e como provar:
[`references/checklist.md`](references/checklist.md).

| Dimensão | A pergunta | O erro que ela pega |
|---|---|---|
| **Completude** | O que shipou está registrado? O que ficou tem dono? | deferimento órfão; PR invisível; ADR ainda `Proposto` |
| **Corretude** | Os números ainda são verdade **depois** do merge? | KR-A dizendo "5 → 0" quando eram 2 (#1341) |
| **Consistência** | Lane, `_README`, ADR e plano contam a mesma história? | critério de aceite **invertido** vs. o co-design (#1247) |
| **Precisão** | A afirmação é o que foi **medido** ou o que se **inferiu**? | "se o job falhar, a regravação é esperada" — o job nunca rodou (#1341) |

**Pergunta condicional de consistência — custo zero quando a resposta é não.** Este
PR **encerrou** painel, pendência ou onda no `_README` da sprint? Se sim, o ponteiro
para o `_HISTORY` sai **no mesmo PR**:

```bash
python3 dev/split_sprint_history.py --sprint <X> --section '<label exato>'
```

⚠️ **O comando só move `h2`** — `--section` casa label de `h2` (`split_sprint_history.py`
§`--section`: *"label h2 a mover"*). **Painel é quase sempre `h3` dentro de `h2` vivo**, e
aí o comando **não move nada**: medido em 2026-09-01 no §Pendência de filiação da
[[A40.l110]], as duas formas do label devolveram *"nenhuma seção casou"* e o `_README`
ficou intacto. Mover o `h2` pai seria pior — no caso dele, o pai é o §Gate de saída, que
hospeda o contador vivo. **Para painel `h3`, mova à mão** com o mesmo ponteiro do
`POINTER_TEMPLATE`, e deixe no lugar de origem a linha que diz o que **continua
governando**. Ensinar `h3` ao script é trabalho próprio, não feito.

Não é varredura: é a pergunta que só quem encerrou sabe responder. **Não** rode o
`--dry-run` aqui — medido na A40 em 2026-09-01, ele marca 4 seções (987 linhas) das
quais **3 governam hoje**, e a saída é idêntica em todos os fechos. Varredura de
`_HISTORY` é da `audit-vault`.

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

### Camada 4b — Auditoria dos mortos

Se a camada 4 **descartou** algum achado, audite os descartados antes de fechar —
pergunta invertida ("esta refutação é boa?"), **testemunha mecânica obrigatória**,
`indeterminado` quando não houver. Herdado da camada 4b da `audit-vault`, com o
caso de origem lá: dois céticos deram veredito oposto sobre a mesma substância, e
agir sobre o confirmado pôs um risco falso sobre uma frase verdadeira em `main`.

O conjunto é limitado (os mortos, não os vivos), então a camada é barata. **Não**
acrescente uma passada simétrica sobre os achados vivos — ver o porquê na
`audit-vault` §Camada 4b.

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
  **Isso inclui varredura de `_HISTORY`.** Rodar
  `split_sprint_history.py --dry-run` a cada fecho foi proposto e **recusado** em
  2026-09-01 (`information-architect` + `product-manager`): a saída é estável em
  todos os fechos, o aviso S2 de `check_sprint_readme_size.py` **já** a imprime em
  todo `pre-commit run --all-files` com taxa de ação ~0, e a precisão medida do
  `--dry-run` no grão h2 é **1 em 4** — marcar o §Gate de saída como histórico
  gravaria "não governa decisão de hoje" sobre o contador que decide o fim da
  sprint. O que a skill faz é a **pergunta condicional** da camada 3; a varredura
  fica aqui, na `audit-vault`.
- **Não é gate — mas a metade estrutural já é, desde 2026-08-24.** Este
  `check_closure.py` continua fora do pre-commit e não bloqueia commit. O
  gatilho de promoção que esta seção previa **foi executado** pela [[A40.l59]]:
  `dev/check_lane_transition.py`, hook `lane-transition`, cobre `ship_pr` +
  `ship_date` + PR no registro da sprint (`_README` ∪ `_HISTORY`), lane nova sem
  linha de tabela, e lane não-terminal cujo `ship_pr` já mergeou.
  **Não reconstrua o gate** — estenda o que existe.

  Efeito, medido em 2026-08-25 e **re-medido no mesmo dia** porque o número anda:
  as transições da A40 **anteriores** ao gate (`6d3721ee`) dão **19 passa / 25
  barra** — esse lado é histórico e não muda; as **posteriores** deram 5/0 pela
  manhã e **6 passa / 0 barra** à tarde. Não congele a contagem aqui: o lado
  novo cresce a cada lane que fecha. O que vale é a **direção** — nenhuma
  transição posterior ao gate deixou de carregar o registro — e ela se
  re-verifica cruzando `ship_pr` do frontmatter com o `_README`/`_HISTORY` no
  commit do flip, separando pelo merge do gate. Limite herdado e declarado:
  `T1`/`T2` leem
  `git diff --cached`, logo passam vazios sob `pre-commit run --all-files` (o
  caminho do CI) — são enforcement local. Só o `C1` lê estado e vale nos dois.
- **Não cria lane nem ADR automaticamente.** Propõe; o pickup é decisão do
  dono.
- **Não conhece `track`.** `check_closure.py` indexa só
  `docs/sprint/*/lanes/*.md`; entrega via `docs/**/tracks/*.md` cai em
  `exit 2` (acima). Suporte a track foi avaliado em 2026-08-26 e **não** feito:
  track é ~10% do churn de doc (107 toques contra 930 de lane em 90d), e o
  achado que ele pegaria no caso real — follow-up "vai para a Onda 1" ausente
  no track de destino — foi pego pelas camadas 2-4. Reabrir se track virar
  veículo majoritário de entrega.

## Critério de aceite

- ≥1 achado por run vira correção mergeada, **ou** o veredito `FECHADO` se
  sustenta numa releitura do dono.
- Falso-positivo dos `CLOSE-BLOCK` ≤ 20% (a camada 4 é o filtro).
- **Todo achado descartado na camada 4 passa pela 4b**, com testemunha mecânica ou
  `indeterminado` — nunca com o silêncio, que é indistinguível de morte correta.
- Nenhum achado da camada 3 recria o que a camada 1 já pega.
- Run triável em < 15min para 1 lane.
