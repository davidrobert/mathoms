---
id: ADR-376
type: adr
title: "Supersessão de PropertyIdentity é escopada ao que o run observou"
status: Proposto
phase: A40
date: "2026-08-11"
relates_to:
  - "[[ADR-225]]"
  - "[[ADR-246]]"
  - "[[ADR-265]]"
  - "[[ADR-282]]"
  - "[[ADR-324]]"
  - "[[ADR-334]]"
  - "[[ADR-375]]"
supersedes: []
superseded_by: []
aliases: ["ADR 376", "supersessao escopada ao run", "reconcile_supersession observed_pids"]
tags:
  - type/adr
  - status/proposto
  - area/persistence
  - area/pipeline
---

# ADR-376 — Supersessão de imóvel é escopada ao que o run observou

> Origem: investigação de 2026-08-11. A [[ADR-375]] fecha o write-path; esta
> decide como o passivo já acumulado é colapsado sem voltar no run seguinte.

## Contexto

O reconcile da [[ADR-324]] tratava o estado supersedido como função pura do dedup
corrente sobre **a tabela inteira**: toda row fora do mapa de perdedoras tinha
`superseded_at` limpo. O forward-path, por sua vez, monta esse mapa só com as
entries do run — que carregam apenas os `property_id` que o resolver devolveu
naquela execução.

Somadas, as duas coisas tornavam qualquer supersessão feita por sweep
**não-durável**: o sweep marcava as zumbis, e o E1.5c seguinte, que não as
enxerga, as reativava. O desfecho visível seria o pior possível — "consertaram e
desconsertou sozinho".

Havia ainda dois buracos que impediam o sweep de sequer formar os grupos:

- Grupos com canonical **idêntico** nunca fundiam: o passe cross-código exige um
  lado com código genérico, e o fuzzy recusa explicitamente `canon_a == canon_b`.
  Como entry com `property_id` vira um grupo por row, rows da mesma era ficavam
  separadas para sempre.
- O script de sweep lia o baseline consolidado de `content_json` **cru**, mas o
  artefato é envelope Fernet desde a [[ADR-231]]. O payload chegava vazio com
  `baseline_found=True`, os valores viravam `{}` e a eleição do vencedor degradava
  em silêncio para `created_at ASC` — invertendo os vencedores.

## Decisão

1. **O escopo do reconcile é explícito.** `SupersessionScope` carrega
   `workspace_id`, `winner_by_pid` e `observed_pids`, e valida no boundary que
   todo pid referenciado foi observado. Row fora do escopo **não é setada nem
   limpa**.
2. **Fora do escopo, o estado é absorvente.** A flip-safety da [[ADR-324]] §2
   sobrevive, porque o flip só ocorre entre rows que o run enxergou; o que deixa
   de existir é a reversão silenciosa do que ele nunca viu. Reverter passa a ser
   ato explícito de ops (`--clear`), não efeito colateral de run.
3. **O sweep observa a tabela inteira do workspace; o run observa suas entries.**
   É a mesma função com escopos distintos — não dois caminhos de código.
4. **Passe same-canonical no dedup**, entre o cross-código e o fuzzy, seguindo a
   ordem restritivo→tolerante da [[ADR-265]] §3. Reusa o predicado de divergência
   de complemento de `canonical_fuzzy_match` em vez de reimplementá-lo: sem o
   guard, duas unidades distintas do mesmo prédio fundiriam, porque o canonical
   carrega só via+número.
5. **Vencedor = o pid presente no baseline consolidado mais recente**; se o grupo
   não contiver exatamente um, o grupo **aborta** em vez de degradar. `created_at`
   é armadilha ativa: com valores vazios o sort estável degrada justamente para
   ele e elegeria uma row de run que falhou.
6. **O sweep lê o baseline decriptado e falha alto** quando o payload não traz
   `imoveis_consolidados`, distinguindo baseline ausente (warn legítimo) de
   ilegível (erro abortivo). A chave Fernet falsa que o script injetava no
   ambiente sai.
7. **Detector de zumbi sai do próprio escopo** (vivas − observadas), como warning
   tipado no log do E1.5c. Um segundo caminho de leitura para contar a mesma coisa
   foi o que fez forward-path e sweep divergirem na primeira vez.
8. **Desempate de trust por recência.** Com a mesma fonte nos dois lados, o
   critério anterior mantinha a classificação da vencedora e descartava a do
   usuário em silêncio, mesmo quando a descartada era a mais recente.
9. **Sweep único, não self-healing.** A prevenção mora no write-path
   ([[ADR-375]]); a remediação é do passivo existente; o detector é o gatilho para
   re-rodar. Supersessão DB-wide no caminho quente compra pouco e vende risco de
   over-merge.

## Consequências

- O passe same-canonical é **no-op no forward-path** do dogfood: o baseline
  corrente já traz um pid por imóvel real, e o strict do resolver colapsa por
  `(codigo_rfb, canonical)`. Ele existe para o sweep, onde cada row é um grupo.
  Medido: goldens de E1.5c/E5, invariantes de conservação e snapshot do view-model
  seguem idênticos.
- Ordem operacional obrigatória: deploy do escopo explícito → worker recarregado →
  pipeline ocioso → `--apply` → re-rodar E1.5c → diff. Aplicar o sweep com um
  worker de código antigo em voo faz o run reverter tudo.
- O guard de `residencia_principal` no repoint puro **não** foi adicionado: o
  partial-unique torna o estado de duas RP inalcançável, a ponto de o cenário não
  ser semeável em teste. Comentário no lugar para a próxima revisão não repropor.
- Entre o merge do write-path e a execução do sweep, o usuário continua vendo as
  rows duplicadas. O código impede a população de crescer; quem colapsa o passado
  é o sweep.

## Critério de aceite

- **Completude** — port, adapter DB, fake in-memory e os dois call-sites recebem o
  escopo. Protocol estrutural não quebra CI com fake desatualizado, então o fake
  entra no mesmo commit.
- **Corretude** — rodar o E1.5c duas vezes com uma zumbi pré-seedada fora do run
  mantém `cleared == 0` e a zumbi supersedida. Sem o escopo, o teste cai.
- **Consistência** — grupos com mesmo canonical e complementos divergentes não
  fundem; o teste anti-over-merge cai quando o guard é removido.
- **Precisão** — o dry-run lista por row o canonical armazenado, o recomputado, o
  complemento e a âncora no baseline, para que o gate humano do `--apply` não seja
  decorativo.
