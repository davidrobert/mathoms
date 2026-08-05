---
id: A42.l1
type: lane
title: "Stage de unlock aborta o run inteiro, e o secret dele é inalcançável em deploy limpo"
sprint: A42
status: planned
priority: P0
branch_slug: a42-l1-unlock-aborta-run-e-secret-inalcancavel
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p0
  - area/pipeline
  - area/backend
---

# A42.l1 — `unlock-aborta-run-e-secret-inalcancavel` (RV4-01)

> **Origem:** [[PIPELINE-REVIEWS-active]] §r4 2026-08-04 — RV4-01 (P0, `saúde-execução`).
> Reproduzido por mutação **e** por run real com status `failed`. Veredito adversarial
> PARTIAL; a parte confirmada é a que importa.

> 🔑 **Gatilho de promoção desta lane, nomeado 2026-08-05: o mesmo evento da [[A41]]** —
> *decisão de abrir o beta fechado / 2º usuário*. Foi avaliado promover esta lane para a
> [[A40]] agora (é a única P0 da sprint com `depends_on: []`) e **recusado** por
> `product-manager` + `senior-cto`: ela falha a condição 1 da exceção da cláusula 2 do
> §Critério de admissão — *"P0 que **alcança o usuário**"*. Não alcança ninguém hoje: o
> dogfood é N=1 e tem o arquivo residual, e o 2º usuário só existe depois do gate de
> saída da A40, que é o **mesmo evento** que promove esta sprint. As ordens coincidem, e
> adotá-la furaria por nada a regra que a A42 acabou de escrever.
>
> **O que substitui a promoção, e morde mais cedo que ela:** entrada em
> [[OWNER-GATED]] §3 bloqueando o provisionamento de **qualquer** workspace novo —
> beta, 2º usuário **ou tenant de teste do próprio dono** — antes desta lane shipar. A
> lane cobriria só o beta; o gate cobre o tenant de teste, que é o caminho por onde o
> defeito chega primeiro. Custo zero de capacidade.
>
> **Autorizado a executar já, fora da contabilidade de lane:** a ADR `Proposto` abaixo
> (docs-only). O poste longo desta lane **não é o código** — são duas correções de ordem
> de predicado — é a pergunta de operação *"onde mora o material de senha num tenant
> provisionado do zero, dado que o diretório atual é path proibido"*. Escrita agora, a
> lane fica pegável em horas quando o gatilho disparar. Precedente de "ADR antes de
> autorizar a lane": a [[A40]] §Fora do sprint sobre a [[A41.l3]].

## Problema

O primeiro stage do pipeline carrega o arquivo de senhas **antes** de verificar se
existe algum documento cifrado, e aborta o processo em falha. Consequência: um
workspace **sem nenhum documento cifrado** tem o run inteiro morto no stage 1 de 18.

O agravante é que o arquivo de senhas só chega ao tenant por cópia de um diretório
que é **bloqueado por `.gitignore` e por `dev/check_forbidden_paths.py`**. Ou seja:
num deploy limpo, não existe caminho suportado para criar esse arquivo. O defeito
não é "falta configurar" — é que a configuração exigida é inalcançável.

**Por que não apareceu no dogfood:** neste workspace o arquivo existe (resíduo de
sessão antiga) e o run completa 18/18. O defeito morde no **segundo usuário** e em
qualquer ambiente provisionado do zero. É por isso que esta lane está em onda solo
com gate externo: o critério de aceite **não pode** ser "o dogfood roda".

## Decisão

Duas mudanças independentes, na ordem:

1. **Ordem do predicado** — verificar a existência de documento cifrado **antes** de
   tocar o material de senha. Sem documento cifrado, o stage é no-op de sucesso.
2. **Ausência de secret não é falha abortiva** — é ausência de trabalho. Se há
   documento cifrado e não há material de senha, o caminho correto é escalar para
   revisão (o documento fica pendente, o run segue), nunca derrubar o run.

**ADR nova `Proposto` obrigatória** antes do PR de implementação: provisionamento de
secret por tenant em ambiente limpo é decisão de arquitetura e de operação —
co-design `senior-cto` + `sre-devops`. A ADR precisa responder onde o material vive
num tenant provisionado do zero, dado que o diretório atual é path proibido.

## Critério de aceite

- Teste de regressão **antes** do fix: workspace sem documento cifrado e **sem**
  arquivo de senhas ⇒ stage completa como no-op; hoje o processo morre.
- Teste de regressão: workspace **com** documento cifrado e sem material de senha ⇒
  o documento é escalado para revisão e o run **prossegue**; nenhum caminho aborta.
- **O aceite não usa o corpus dogfood** (onde o arquivo existe): fixture de tenant
  limpo. Um teste que passe só porque o ambiente local tem o resíduo é falso-verde —
  a mesma classe que esta sprint existe para matar.
- Nenhum workaround assado em fixture: se a suíte hoje cria o arquivo para fazer o
  stage passar, esse setup sai no mesmo PR (é ele que esconde o defeito).
- ADR `Proposto` mergeada antes do PR de implementação.
