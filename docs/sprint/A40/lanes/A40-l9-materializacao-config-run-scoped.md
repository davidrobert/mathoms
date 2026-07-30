---
id: A40.l9
type: lane
title: "Materialização de config run-scoped: input zerado por resolver o run corrente antes do E4 existir"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l9-materializacao-config-run-scoped
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/pipeline
---

# A40.l9 — `materializacao-config-run-scoped` (RV3-11)

> Promovido de P2 para **P1** pelo painel, e ordenado **à frente** da [[A40.l10]].

## Problema

O agregado tributário é materializado em `build_config_overrides_from_db` →
`_setup_run_context` no **início** do run, e `_latest_run_id` resolve para o run
**corrente**, cujo E4 ainda não existe. Todo input run-scoped sai zerado, em
silêncio, e **regen nunca corrige**.

Duas razões para P1:

1. **É reincidência.** O MOC registra "RV2-18 FU-2 medido (rótulo *FIXADO* era
   falso)". Um achado declarado corrigido que não estava é falha de **verificação**,
   não só bug — o custo real é que o processo de fix produz falso verde.
2. **É causa da [[A40.l10]]** (P1): o gatilho do CTA que aquela lane quer construir
   depende de a receita PJ ser > 0, que esta zera. Ela poderia ser "corrigida"
   preenchendo o perfil e continuar entregando cascata zerada.

**Erro de categoria:** o agregado não é config — é **read-model derivado do E4**.
`build_config_overrides_from_db` existe para *configuração*. Valor que só existe em
t=E4 não tem lugar num mapa materializado em t=0.

## Escopo — 2 PRs, sem stop-gap

- **PR1 — teste vermelho + telemetria.** O teste de regressão abaixo, mais um
  contador em WARNING. Hoje a falha é 100% silenciosa; **sem o contador, o próximo
  "FIXADO" volta a ser falso**.
- **PR2 — mover para resolver injetado** no `WorkspaceContext`, no padrão já
  existente de `_db_resolvers` (`run_context_factory.py:89-97`). Invocado quando a
  cascata é necessária, momento em que o E4 do run já está escrito. Zero
  arquitetura nova; respeita a proibição de sqlalchemy em `pipeline/**` (protocol
  no domínio, impl no backend).

Não vale um PR intermediário plumbando `exclude_run_id`.

## Critério de aceite

Três casos em `backend/tests/test_tributario_run_scoped_inputs.py`, invocando o
**entrypoint de produção** (não a função interna):

1. **Regressão (vermelho hoje):** run anterior concluído com E4 não-zero + run
   corrente sem E4 ⇒ o input resolve para o **run anterior completo**, não zero.
2. Só o run corrente, sem E4 ⇒ marcado **explicitamente indisponível**, nunca zero
   silencioso.
3. Perfil incompleto ⇒ o motivo declarado é o perfil, não o input vazio.

- **Declarar o sinal esperado do delta** (decisão nº 5 do painel): `↑` em
  `receita_pj_anual` e nos números tributários derivados — o defeito zerava o
  input, então corrigi-lo só pode subir o valor. Delta `=` significa que o
  entrypoint de produção não passa pelo caminho corrigido; delta `↓` significa
  que o run resolvido é o errado. `dev/golden_diff.py` confere.
