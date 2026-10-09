---
id: ADR-442
type: adr
title: "Valor monetário de workspace real não entra no repositório: denylist local com HMAC e gate em commit e push"
status: Decidido
date: "2026-10-08"
amended_at: ["2026-10-09"]
relates_to:
  - "[[ADR-319]]"
  - "[[ADR-435]]"
  - "[[ADR-313]]"
  - "[[ADR-315]]"
  - "[[ADR-316]]"
  - "[[ADR-231]]"
  - "[[ADR-210]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 442"
  - "gate de valor do dogfood"
  - "denylist local de valores do dogfood"
tags:
  - type/adr
  - status/decidido
  - area/security
  - area/ci
---

# ADR-442 — Valor monetário de workspace real não entra no repositório

> **Aditada 2026-10-09:** achado, decisão intacta — o tokenizador não lê milhar pontuado
> sem `R$` nem sufixo de escala, e o critério 6 só atesta o que ele lê (§Aditamento
> 2026-10-09).

## Contexto

O repositório é público ([[ADR-313]]). O CLAUDE.md proíbe valor monetário real em
commit, doc, docstring e fixture, e a [[ADR-319]] §Decisão (contrato negativo, item 1)
proíbe *"patrimônio/renda nominal atribuível a pessoa real"* em qualquer arquivo
versionado. As duas regras estavam de pé e **nenhuma era medida**:

- `lint-no-real-pii` ([[ADR-319]]) reconhece CPF, endereço, placa, contrato e homedir
  por regex. Número solto não tem forma que distinga o real do sintético;
- a [[ADR-435]] mede o que o produto **publica**, não o que entra no repositório;
- as skills de revisão (`pipeline-review`, `report-review`, `ledger-certify`,
  `parse-certify`) mandam escrever o registro sem literal monetário, mas a evidência
  seguia para lanes, ADRs, fixtures e docstrings escritas **depois**, ao corrigir o
  achado. A regra tinha escopo de skill; o vazamento acontecia fora dele.

Medido em 2026-10-08 com o dado local (decifrado em memória; saída só `path:linha`):
valores que existem nos artefatos do workspace de dogfood apareciam em dezenas de
arquivos versionados, a maioria ≥ R$ 10 mil com ≥ 6 dígitos significativos, faixa em
que coincidência com número sintético é desprezível. O saneamento do HEAD saiu em PR
próprio. Esta ADR decide o que impede a volta.

A dificuldade de desenho: a diferença entre real e sintético **não está no token**,
está no banco local. O gate precisa da lista derivada do banco, e a lista é ela mesma
sensível, num repositório cujos logs de CI são públicos.

## Decisão

**D1 — A lista vem do banco local e fica fora da árvore, como HMAC.**
`dev/build_dogfood_denylist.py` decifra os artefatos in-process ([[ADR-231]]), coleta
as folhas numéricas, mantém o tier A (≥ R$ 10.000,00 com ≥ 6 dígitos significativos
em centavos), subtrai constantes públicas (`fiscal_parameters` e `dev/dogfood_public_constants.json`,
com a fonte legal de cada uma) e grava o
HMAC-SHA256 de cada valor normalizado em centavos em `~/.config/mathoms/` (0600), com
a chave em arquivo separado e um manifesto (data, contagem, canário). Não imprime
valor algum, nem em exceção. Recusa escrever dentro do repositório. Roda na máquina
que tem o banco, nunca em CI.

**D2 — O gate lê só linhas adicionadas, em três pontos.** Pre-commit (diff staged),
commit-msg e pre-push **commit a commit** (`git show -U0` de cada commit do range,
nunca o diff líquido: valor que entra num WIP e sai no seguinte é publicado pelo push,
e o squash não desfaz isso). Tokeniza `1.234,56`, `1234.56`, `1,234.56`, `1_234.56` e
`R$ 8.000`, normaliza para centavos, aplica o HMAC e compara. A saída é
`path:linha: VALOR_DOGFOOD`, **nunca o valor**: saída de hook é colada em PR e chat.

**D3 — Política de falha.**

- Sem `~/.config/mathoms/` (CI, sessão cloud): sai 0 com aviso. No CI o id do hook
  entra no `SKIP` do step, para o log dizer "Skipped" e não "Passed".
- Com o diretório, mas com denylist, chave ou manifesto ausente ou corrompido: falha.
  Na máquina que tem o dado, ausência de lista é defeito, não "nada a checar".
- Manifesto com mais de 14 dias: avisa e passa. Travar agentes por uma ação que só o
  dono executa seria indisponibilidade auto-infligida.

**D4 — Sem baseline commitado e sem marcador inline.** No CPF o baseline não
acrescenta informação: a regex acha o hit sozinha. No valor, a lista **é** o que
separa real de sintético, então publicar `(path, VALOR_DOGFOOD)` publica o mapa que o
HMAC esconde, e um `# noqa` num hit diria em público "este número é da família".
Falso positivo em fixture: troque o número. Constante pública: o gerador exclui.

**D5 — A forma sancionada de evidência é ponteiro + relação.** Ponteiro
(`run · stage · campo`) e relação (sinal, igualdade, razão, Δ%). O valor absoluto vive
no cru off-git (`storage/<ws>/reviews/…`). Arredondar não é sanear: `R$ 123k` ainda é
o número.

**D6 — O pre-push precisa existir.** `default_install_hook_types: [pre-commit,
commit-msg, pre-push]` no `.pre-commit-config.yaml`, e `core.hooksPath` fora da config
local. Com ele setado o `pre-commit install` recusa, e até 2026-10-08 os dois hooks de
`stages: [pre-push]` declarados no config não rodavam no `git push` desta máquina.

## Consequências

- Agente na máquina do dono não comita nem pusha valor do tier A em arquivo de texto
  algum, nem em mensagem de commit.
- Sessão cloud e CI ficam sem a proteção, porque não têm o dado. É aceitável: não
  acessam o dogfood, só propagam o que já está no repositório, e o HEAD está saneado.
- O gerador precisa rodar de novo quando entra run novo; o manifesto avisa aos 14 dias.
- O histórico anterior a esta ADR não muda. A decisão sobre ele é do dono e está na
  [[ADR-315]] §Emenda 2026-10-08 e na [[ADR-316]] §Emenda 2026-10-08.

## Alternativas consideradas

1. **Detector por regex no `lint-no-real-pii`.** Rejeitada: número real e sintético
   têm a mesma forma.
2. **Lista em claro, ou sha256 puro, num arquivo gitignored.** Rejeitada: o domínio
   tem ≲ 10^10 centavos e se reverte por enumeração em minutos; o arquivo vaza em
   paste e backup.
3. **Lista como secret no CI.** Rejeitada: o CI roda depois do push (o valor já está
   publicado), o log é público, e secret de Actions é exfiltrável editando o workflow
   numa branch do próprio repositório.
4. **Push protection com padrão customizado do GitHub.** Indisponível: exige
   organização com Secret Protection, e o repositório é de conta pessoal.

## Deferimento datado (2026-10-08)

Dono da implementação: `sre-devops`. Dono da execução: o dono do repositório.

- **Tier B — par (data, valor) de linha de E2/E3.** Valor solto de transação
  (< R$ 10 mil) colide por acaso com fixture sintética em ~0,8% dos tokens; o par não.
  Retomar quando o tier A estiver estável por duas semanas.
- **Tier C — agregados de R$ 100 a R$ 10 mil (E1.5/E4/E5).** Só depois de medir falso
  positivo com `--tree`.
- **Arredondados** (`X,YZ mi`, `XYZ mil`) dos agregados de topo.
- **Chave no Keychain e regeneração por job local.** Hoje: regeneração manual e o aviso
  de 14 dias.

## Gates (critério de aceite)

1. Um teste por forma (`1.234,56`, `R$ 8.000`, `1234.56`, `1,234.56`, `1_234.56`), com
   denylist de fixture e chave de teste: cada caso sai com erro e
   `path:linha: VALOR_DOGFOOD`.
2. Pre-push: o commit 1 adiciona o valor e o commit 2 o remove; o push reprova. Uma
   implementação por diff líquido **falha** este teste.
3. A saída nunca contém o valor: hit plantado, token malformado e denylist corrompida
   não deixam forma alguma do número em stdout ou stderr.
4. Política de falha: sem diretório, 0; diretório sem denylist, 1; manifesto velho, 0
   com aviso.
5. Canário: `--self-test` planta o valor-canário num repositório temporário e exige hit.
6. `--tree` sobre o HEAD saneado: 0 hits no tier A.
7. O gerador recusa escrever dentro da árvore.

## Aditamento 2026-10-09 — o que o tokenizador não lê, e o que o critério 6 atesta

Achado, sem decisão nova: o gate não muda. Ampliar a cobertura é co-design `sre-devops` +
`information-architect`, pelo §Deferimento datado. Medido com formas **sintéticas** contra
`centavos_da_linha` e `e_tier_a`:

- **Milhar pontuado sem `R$` e sem centavos (`1.234.567`) não é lido.** `_BR` exige `,dd`,
  `_ISO` exige decimal no fim e `_REAIS_INTEIROS` exige o prefixo. Não é arredondamento —
  vale para valor exato em reais —, e o item "Arredondados" do §Deferimento não o cobre.
- **Sufixo de escala não é lido** (`1,2 mi`, `450k`, `450 mil`, `1,2M`); `1,23 mi` vira
  R$ 1,23. Arredondado com prefixo (`R$ 1.200.000`) é lido e sai pelo tier A, por desenho (D1).
- **O critério 6 atesta o instrumento, não a árvore.** `--tree` com 0 hits prova ausência só do
  que o tokenizador lê e o tier A admite. O achado nasceu de uma instância no HEAD, anterior ao
  gate, que escapava pelas duas camadas (forma não lida e arredondada), já relativizada. O
  inventário local (`path:linha`, nunca o valor) ficou com o dono.
- **"Arredondados" é o único item do §Deferimento sem condição de retomada.** Defini-la é parte
  do co-design.
