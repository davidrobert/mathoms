---
id: A42.l19
type: lane
title: "O guard de escrita do E4 resolve por stage e tem ramo placeholder: o balde do patrimônio reprova hoje e é gravado assim mesmo"
sprint: A42
status: open
priority: P1
branch_slug: a42-l19-guard-de-escrita-e4-inerte-no-patrimonio
owner: data-engineer
depends_on: []
adrs: ["[[ADR-212]]", "[[ADR-409]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/dados]
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

```bash
MATHOMS_PIPELINE_SCHEMA_MODE=strict .venv/bin/python - <<'PY'
import json, pathlib, jsonschema
schema = json.loads(pathlib.Path("config/schemas/e4_unified.schema.json").read_text())
jsonschema.validate({"status": "vazio"}, schema)          # valida
# e o balde `patrimonio` do run reprova em `$`
PY
```

## Critério de aceite

- [ ] O ramo placeholder deixa de casar com balde transacional — seja por resolução por
      `artifact_key`, seja por `oneOf` com discriminador explícito.
- [ ] O schema do `patrimonio` passa a descrever o payload que o produtor emite hoje
      (**ordem obrigatória:** corrigir o schema **antes** de gatear, senão `strict`
      derruba o stage — mesmo precedente do `RV4-23`/[[A42.l6]]).
- [ ] `_non_ledger_verdict` deixa de imprimir `coberto` para balde cujo shape ele não
      reconhece; o veredito correto ali é `não-verificável`.
- [ ] **Controle positivo:** escrever um balde transacional no shape `{status: ...}` e
      verificar que o guard **reprova**. Hoje ele aceita.

## Relação com o registro

`PV9-27` já registra a classe (*"`schema_validation_drift` em 6 de 18 stages, todos
passando em modo `warn`"*, P2). **O que esta lane acrescenta é o mecanismo:** a resolução
por stage e o ramo placeholder são o motivo de o guard **não poder** pegar o caso, e o
`patrimonio` é a instância viva. Não duplica a fila da [[ADR-409]] — a decisão de flip
global segue rejeitada; aqui o conserto é do **schema e do discriminador**, não do modo.
