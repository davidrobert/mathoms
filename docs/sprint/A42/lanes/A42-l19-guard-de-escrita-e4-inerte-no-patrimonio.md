---
id: A42.l19
type: lane
title: "O guard de escrita do E4 resolve por stage e tem ramo placeholder: o balde do patrimônio reprova hoje e é gravado assim mesmo"
sprint: A42
status: shipped
ship_pr: 1871
ship_date: "2026-08-31"
priority: P1
branch_slug: a42-l19-guard-de-escrita-e4-inerte-no-patrimonio
owner: data-engineer
depends_on: []
adrs: ["[[ADR-212]]", "[[ADR-409]]", "[[ADR-427]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p1, area/dados]
---

# A42.l19 — `guard-de-escrita-e4-inerte-no-patrimonio`

> **Origem:** `N2` da rodada unificada **U4** ([[LEDGER-CERTIFY-active]] §r8).
> Levantado pela lente de razão, **ampliado pelo cético** (que achou instância viva onde o
> enunciado só via risco hipotético) e **re-verificado pelo loop principal**.

## O defeito, em três camadas

1. **A validação resolve por `stage`, nunca por `artifact_key`.** Os **7** baldes do E4
   (`despesas`, `receitas`, `fluxo_mensal_detalhado`, `patrimonio`, `investimentos`,
   `seguros`, `pontos_milhas`) batem contra **um** `e4_unified.schema.json`.
2. **Esse schema é um `oneOf` de 5 ramos, e um deles é placeholder** —
   `{required: ['status'], properties: {status: {type: string}}}`, descrito no próprio
   arquivo como *"Placeholder (seguros, pontos_milhas)"*. Medido: `{"status": "vazio"}`
   **valida**. Um balde transacional escrito no shape de placeholder passaria limpo.
3. **E a instância viva:** o `patrimonio` **real** deste run (15 chaves de topo, 87 itens,
   63 posições consolidadas) **reprova em `$`** contra esse schema. Sob o modo `warn`
   — que é o **default** de `pipeline.json → schema_validation.mode` — ele é **gravado
   assim mesmo**, com `schema_validation_drift` no log.

**A jusante o silêncio se completa:** `_non_ledger_verdict` procura `dados`/`apolices`/
`composicao` e imprime **"coberto · 0 itens"** para esse mesmo `patrimonio` de 87 itens.
Duas guardas, a mesma cegueira, no balde que carrega o patrimônio da família.

## Medição de reprodução

> **Estado PRÉ-fix (2026-08-30).** O bloco abaixo e o §*O defeito, em três camadas*
> descrevem o mundo **antes** do PR #1871 — são a evidência do achado, e não se
> reescrevem. Rodado hoje, o snippet devolve o oposto: `{"status": "vazio"}`
> **reprova**, e o `patrimonio` **valida**. O estado corrente está em
> §*O que foi entregue*.

```bash
MATHOMS_PIPELINE_SCHEMA_MODE=strict .venv/bin/python - <<'PY'
import json, pathlib, jsonschema
schema = json.loads(pathlib.Path("config/schemas/e4_unified.schema.json").read_text())
jsonschema.validate({"status": "vazio"}, schema)          # valida
# e o balde `patrimonio` do run reprova em `$`
PY
```

## Critério de aceite

- [x] O ramo placeholder deixa de casar com balde transacional — seja por resolução por
      `artifact_key`, seja por `oneOf` com discriminador explícito.
- [x] O schema do `patrimonio` passa a descrever o payload que o produtor emite hoje
      (**ordem obrigatória:** corrigir o schema **antes** de gatear, senão `strict`
      derruba o stage — mesmo precedente do `RV4-23`/[[A42.l6]]).
- [x] `_non_ledger_verdict` deixa de imprimir `coberto` para balde cujo shape ele não
      reconhece; o veredito correto ali é `não-verificável`.
- [x] **Controle positivo:** escrever um balde transacional no shape `{status: ...}` e
      verificar que o guard **reprova**. Hoje ele aceita.

## Relação com o registro

`PV9-27` já registra a classe (*"`schema_validation_drift` em 6 de 18 stages, todos
passando em modo `warn`"*, P2). **O que esta lane acrescenta é o mecanismo:** a resolução
por stage e o ramo placeholder são o motivo de o guard **não poder** pegar o caso, e o
`patrimonio` é a instância viva. Não duplica a fila da [[ADR-409]] — a decisão de flip
global segue rejeitada; aqui o conserto é do **schema e do discriminador**, não do modo.

---

## Medição de execução — 2026-08-30

Rodado o **produtor real** (`main_with_store`) sobre fixtures commitadas
(`minimal-conta-3_reconciled.json` + `minimal-baseline-1.5_consolidated.json`),
não sobre o payload de um run. **O enunciado subestimou o defeito em três pontos.**

**(a) Não era um ramo placeholder; eram dois ramos mortos e um catch-all.**

| Ramo do `oneOf` | Quem casava, medido |
|---|---|
| `{schema_version, apolices}` | `seguros`, só com apólice |
| `{periodo: object, total_geral}` — "receitas ou despesas" | **ninguém** — o produtor emite `periodo` **string** |
| `{meses_ordenados}` | `fluxo_mensal_detalhado` |
| `{dados}` com `dados: {}` — "patrimônio ou investimentos" | `receitas`, `despesas`, `investimentos`, `seguros` v1, `pontos_milhas` — **5 baldes**, e o ramo não restringe nada |
| `{status: string}` — placeholder | **ninguém** |
| — | `patrimonio`: **zero** ramos ⇒ reprova em `$` |

**(b) O ramo morto de receitas/despesas era sustentado por uma fixture.**
`tests/fixtures/pipeline_golden/e4/minimal-receitas-4_unified.json` era
`{periodo: {objeto}, total_geral}` — o shape do **ramo**, não o do produtor (que emite
`periodo` string + 8 campos) — e era seu **único** consumidor. O teste passava há duas
sprints sem afirmar nada sobre o E4. Reescrita para espelhar
`ReceitasUnified.to_legacy_dict`.

**(c) O falso `coberto` não era só do `patrimonio`.** `_non_ledger_verdict` sondava
`dados`/`apolices`/`composicao`; `fluxo_mensal_detalhado` (contêiner `meses_ordenados`)
também caía no `[]` final. E `composicao` é campo do bloco `patrimonio` do **E5** — nunca
do balde E4. O `or` encadeado ainda confundia contêiner **vazio** com **ausente**.

**(d) O golden do E4 já sabia o contrato certo e registrava a isenção.**
`test_e4_execution_with_baseline_patrimonial` validava `patrimonio` contra
`baseline_patrimonial.schema.json` **e** fazia `if key == "patrimonio": continue` no laço
do `e4_unified`. O mapa certo estava no teste; faltava no guard.

## O que foi entregue

Decisão canônica: [[ADR-427]] (D1–D6).

- `SCHEMA_BY_STAGE_KEY` + `resolve_schema_name(stage, key)` no `DBArtifactStore`;
  `_validate_schema` e `_schema_version_token` passam a resolver por `(stage, key)`.
- 5 contratos novos em `config/schemas/` (`e4_cashflow`, `e4_fluxo_mensal`,
  `e4_investimentos`, `e4_seguros`, `e4_pontos_milhas`); `patrimonio` aponta para
  `baseline_patrimonial.schema.json` — **o mesmo schema que já gateia sua fonte E1.5c**.
- `e4_unified.schema.json` vira backstop `anyOf` de `$ref`; o ramo `{status}` sai.
- `_non_ledger_verdict` resolve o contêiner pela chave; shape desconhecido é
  `não-verificável`. Rubrica extraída para `dev/ledger_unit_verdicts.py` (o núcleo
  cruzou as 500 linhas do P2).
- **Dois consumidores do mesmo mapa que herdariam a resolução velha**, achados por
  varredura e consertados no mesmo PR:
  - `dev/measure_schema_drift.py` — o instrumento que gateia a fila do flip. Por stage,
    os 7 baldes bateriam contra o backstop `anyOf` e sairiam `GO` **sem contrato nenhum
    checado**: o falso-verde migraria do guard para quem o audita.
  - `dev/check_artifact_read_keys.py` — só descia por `allOf[].then.$ref`; com o backstop
    virando `anyOf` sem `properties` no topo, o conjunto sairia **vazio** e todo
    `payload["x"]` de um futuro leitor de E4 seria reprovado. Passa a computar o fecho
    transitivo das três formas (`allOf[].then.$ref`, `properties` inline no `then`,
    `anyOf[].$ref`).

## Evidência contra o critério

| Critério | Evidência |
|---|---|
| Placeholder não casa com balde transacional | `test_shape_de_placeholder_reprova_em_balde_transacional` (4 baldes) + `test_troca_de_balde_reprova` |
| Schema do `patrimonio` descreve o produtor | `test_baldes_reais_validam_em_strict`: **7/7** validam em `MATHOMS_PIPELINE_SCHEMA_MODE=strict` (antes o `patrimonio` reprovava em `$`) |
| `_non_ledger_verdict` não diz `coberto` sobre shape que não lê | `test_e4_non_ledger_shape_desconhecido_nao_verificavel` + 4 testes irmãos |
| Controle positivo | A/B contra o schema de `HEAD~1`: **5 payloads, 5 flips** de `ACEITA` → `reprova` |

**Não-inércia medida, por subconjunto** — os dois consertos são gateados
independentemente:

- mapa por chave esvaziado (= volta a resolver por stage) → **5 testes vermelhos**,
  entre eles `test_troca_de_balde_reprova`;
- ramo `{status}` de volta no backstop → **2 testes vermelhos**.

O controle do placeholder **sozinho passa** sob a primeira mutação: ele não discrimina
"resolve por chave" de "o ramo morto saiu". É por isso que o remédio menor — só apagar o
ramo — seria inerte contra a classe, e o teste que discrimina é o de **troca de balde**.

## Fora de escopo, registrado

- `save_json` em `scripts/categorize_transactions.py:975` é **dead code** (zero
  call-sites pós-[[ADR-212]]) e cita o umbrella por nome.

  > **Fechado 2026-08-31** ([#1889](https://github.com/davidrobert/mathoms/pull/1889)).
  > Função deletada. Os call-sites foram re-verificados por cinco vetores, não só
  > pelo literal: `getattr`/`globals()`/`vars()`/`eval`/`exec` com nome montado,
  > despacho por `dir()` + `startswith`, `from ... import *`, `__all__` e
  > monkeypatch de teste — nenhum alcança o nome. Com a remoção, o único sítio
  > **executável** que cita o umbrella por nome literal volta a ser o próprio
  > `SCHEMA_BY_STAGE`; o resto é docstring (`e4_serialization.py`) e teste.
- O flip `warn→strict` do E4: esta lane **não flippa nada**.

  > **Correção 2026-08-31 — o "7/7 validam em `strict`" que eu havia escrito aqui era
  > sobre a FIXTURE GOLDEN, não sobre o corpus**, e a frase dizia "re-medido na `main`",
  > que se lê como corpus. O go/no-go da [[ADR-409]] §B é medição sobre
  > `pipeline_artifacts`. Medido depois, no corpus real (71 runs, 98 dias):
  >
  > | schema | artef | drift | payloads | veredito |
  > |---|---:|---:|---:|---|
  > | `e4_cashflow` | 142 | 0 | 142 | **GO** |
  > | `e4_investimentos` | 71 | 0 | 40 | **GO** |
  > | `e4_seguros` | 71 | 0 | **5** | massa insuficiente |
  > | `e4_pontos_milhas` | 71 | 0 | **1** | massa insuficiente |
  > | `e4_fluxo_mensal` | 71 | **2** | 21 | NO-GO → consertado em #1894 |
  > | `baseline_patrimonial` (`patrimonio`) | 169 | **101** | 116 | fora da fila (§F) |
  >
  > São **2** elegíveis, não 7. E na primeira tentativa a medição saiu **100% ilegível**
  > (o `.env` com a chave do vault não existe no worktree) — "não-validado não é
  > validado-sem-drift" é guarda da própria §B.

  **Decidido:** promover **2** (`e4_cashflow` + `e4_investimentos`), arbitrado pelo
  `senior-cto` após divergência `sre-devops` (4) × `data-engineer` (1). Pré-requisitos
  **mergeados** em [#1894](https://github.com/davidrobert/mathoms/pull/1894) (`c9d643d0`).
  Falta o log de startup do worker e o flip. `owner: data-engineer`; fila viva na
  disposição **PV9-27** de [[PIPELINE-REVIEWS-active]].
- Achados colhidos no caminho e roteados: [[A40.l110]] (fóssil do baseline +
  `date.today()` em artefato persistido) e [[A40.l111]] (valor não apurado em item
  físico), abertas em [#1897](https://github.com/davidrobert/mathoms/pull/1897).
  **Marcador de entrega (2026-09-01):** a [[A40.l111]] está `shipped`
  ([#1917](https://github.com/davidrobert/mathoms/pull/1917), [[ADR-431]]); a
  [[A40.l110]] entregou o **PR-A** ([#1914](https://github.com/davidrobert/mathoms/pull/1914))
  e segue `open` pelo PR-B.
