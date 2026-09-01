---
id: A42.l4
type: lane
title: "Check que não consegue avaliar evapora da conta em vez de virar skipped"
sprint: A42
status: planned
priority: P2
branch_slug: a42-l4-check-que-nao-avalia-evapora
adrs:
  - "[[ADR-342]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p2
  - area/pipeline
---

# A42.l4 — `check-que-nao-avalia-evapora` (RV4-20)

> **Origem:** [[PIPELINE-REVIEWS-active]] §r4 2026-08-04 — RV4-20 (veredito
> **CONFIRMED**, provado por mutação) · resíduo de RV2-05, re-medido inalterado no §r4.

## Problema

O relatório de execução afirma "16 de 16 checks OK". A afirmação é auto-referente e
o denominador é auto-normalizante:

- **Auto-referente:** os checks leem **um** artefato — o da própria camada de
  análise. Nenhum check lê as camadas de extração, reconciliação ou categorização.
  "Cross-validation" valida a análise contra si mesma.
- **Auto-normalizante:** um check que **não consegue** avaliar (input ausente)
  devolve vazio e **evapora da conta** em vez de aparecer como `skipped`. Provado por
  mutação: remover o input produz falso-verde — o denominador encolhe junto com o
  numerador e a razão continua "n de n".

O efeito composto é o pior tipo de instrumento: quanto menos ele consegue medir,
melhor ele parece. E o resíduo de RV2-05 agrava — o conjunto de checks que participa
do gate de pausa é menor que o conjunto que roda, então checks fora dele nunca
pausam nada.

## Decisão

1. **Três estados explícitos** por check: `pass` | `fail` | `skipped(motivo)`.
   Ausência de input é `skipped` com motivo, nunca desaparecimento.
2. **Piso de contagem por identificador de check.** O conjunto esperado é declarado;
   se um check declarado não reportou nenhum dos três estados, isso é falha do
   relatório de execução — não silêncio. É o piso que impede o denominador de
   encolher.
3. **Declarar o escopo real na saída.** Enquanto os checks lerem uma única camada, a
   afirmação impressa não pode sugerir cobertura de ponta a ponta. Ampliar o escopo
   para as camadas anteriores é fora desta lane (é o que as [[A42.l3]] e [[A42.l2]]
   instrumentam); **o que entra aqui é parar de afirmar mais do que se mede.**

Esta lane é deliberadamente estreita: possui um arquivo só, e por isso corre em
paralelo com as outras duas da Onda 1 sem colisão.

## Critério de aceite

- **Prova por mutação:** remover o input de um check ⇒ ele aparece como
  `skipped(motivo)` **e** o exit reflete o piso violado. Hoje o mesmo cenário produz
  "n de n OK" (medido no §r4).
- Nenhum check pode sair da contagem: o número de checks reportados é sempre igual
  ao número de checks declarados.
- O gate de pausa passa a enxergar o conjunto completo, ou a diferença entre "roda"
  e "pausa" fica **declarada** com rationale — o que não pode continuar é a
  divergência tácita.
- A string impressa sobre cobertura não afirma escopo maior que o medido.

---

## Aresta declarada — o resíduo do item 9 da [[A42.l3]], 2026-09-01

> **Não é ampliação de escopo do §Decisão acima.** Registra de onde vem trabalho que
> cai neste arquivo, para que ele não fique órfão.

A [[A42.l3]] carregava, como item 9, o `PV9-04` (*"a suíte de cross-validation tem
severidade constante: `info` em 17/17"*). Ele **não procede como escrito**, e o §r10 já
o re-triara como `PV10-03`. Re-medido em 2026-09-01, a re-triagem procede: a severidade é
**ternária condicional nos 17 checks** (`"error" if … else "info"` e variantes) — `info`
em 17/17 é **efeito** de tudo passar, não constante estrutural. O remédio que o item
pedia já é verdade no código.

O que sobrevive é `PV10-03`, e parte em duas — as duas neste arquivo:

1. **"17/17 OK" conta advisory como gate.** Só `_CONSERVATION_CHECKS = {CV1, CV2, CV3,
   CV6}` pausa o run; os 13 restantes são advisory. Isto **já é** o §Decisão 3 desta lane
   (*"parar de afirmar mais do que se mede"*) — a linha do registro dá a ele o número
   exato (4 de 17) e o nome do conjunto.
2. **Os 4 que gateiam são recompute de produtor único** — leem componentes **e** total do
   mesmo payload E5. É a classe que a [[ADR-418]] §D4 condena no mesmo arquivo: *"dois
   campos em que o SEGUNDO deriva do primeiro: não podia falhar"*. **Esta metade está sem
   dono:** a [[A42.l16]] decidiu escopo "só o CV18" e a deixou explicitamente de fora.

**Por que aqui e não em lane nova.** O §Teste de corte da [[A42.l3]] previa "lane irmã com
`depends_on` nesta" — mas foi escrito antes da refutação, quando o item ainda parecia ser
sobre severidade. Corrigido o enunciado, o dono natural é quem já possui
`scripts/validate_cross.py`, que é esta lane. `depends_on` na l3 seria dependência falsa:
nada do harness da l3 é insumo disto.

**Fora do DoD atual.** A metade (2) é decisão de desenho — cruzar três produtores
independentes, como o `CV5` já recebeu — e não cabe no escopo estreito que esta lane
declara. Se ela não entrar aqui, sai como lane própria **com o enunciado corrigido**, e
nunca como `PV9-04`.
