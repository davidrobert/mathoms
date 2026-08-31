---
id: A40.l110
type: lane
title: "O baseline grava `date.today()` no artefato e o §F da ADR-409 nomeia o produtor errado: matar o fóssil nas duas pontas"
sprint: A40
status: open
priority: P1
branch_slug: a40-l110-fossil-do-baseline-e-idempotencia
owner: data-engineer
depends_on: []
adrs: ["[[ADR-409]]", "[[ADR-427]]", "[[ADR-093]]", "[[ADR-212]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/dados, area/pipeline]
---

# A40.l110 — `fossil-do-baseline-e-idempotencia`

> **Origem:** tratamento dos achados da [[A42.l19]]. Co-design `data-engineer`,
> 2026-08-31. Herda o §Deferimento datado da [[A40.l58]] (§F da [[ADR-409]]).

## O defeito, em três camadas

**1. `date.today()` é gravado em artefato persistido — quebra de idempotência.**
`BaselineNormalizer` passo 2 cai em `self._resolve_today()` quando
`data_consolidacao` não existe — e `consolidate_baseline` **não emite** essa chave.
Medido, mesmo input em dois dias civis:

```
dia 2026-08-12  sha256[:12]=77467dd93aca
dia 2026-08-16  sha256[:12]=69cd9157bdc4   ⇒ NÃO idempotente
```

Envenena qualquer métrica de massa por conteúdo (o balde `patrimonio` conta 1
evidência nova por dia civil) e viola a idempotência radical do CLAUDE.md.

**2. Os 2 `required` fósseis não têm leitor.** `pipeline_stage` e
`data_processamento` só aparecem, no payload de baseline, no normalizer, nos testes
dele, na fixture e no schema. Zero consumidores de produção — verificado por `rg` em
`pipeline/`, `backend/app`, `scripts/`. O `pipeline_stage` chega a exigir
`const: "E1.5_Baseline_Patrimonial"`, nome que a [[ADR-093]] não reconhece.

**3. A premissa do §F da [[ADR-409]] está errada.** Ele manda re-derivar o contrato
*"do produtor E1.5c"* — mas a `description` do próprio schema declara outro:
*"A normalização em E4 converte v2 → v1 canonical **antes da validação**"*. Executar
o §F ao pé da letra escolhe o shape errado.

**A divergência entre os dois produtores é de exatamente 2 campos** — os mesmos 2
fósseis. Não são "duas formas do mesmo payload": é uma forma e um enxerto.

## O circuito que escondeu isso

O normalizer **sintetiza** os campos e a fixture
`tests/fixtures/pipeline_golden/e2/dois-membros-anos-disjuntos-1.5_consolidated.json`
os **hardcoda** no topo — três campos que `consolidate_baseline` nunca emite. Produtor
e teste concordando na crença errada. É a segunda instância, na mesma família de
schema e na mesma sprint, da patologia que a [[ADR-427]] §Consequências pegou em
`minimal-receitas-4_unified.json`.

## Ordem dura (o dilema evapora se as pontas caírem juntas)

**PR-A — matar o fóssil nas duas pontas, atômico.** Remove os 2 `required` + as 2
`properties` do schema; deleta os passos 1 e 2 do `BaselineNormalizer` (**o
`date.today()` sai aqui**); deleta `normalize_baseline` + `load_patrimonio` de
`scripts/categorize_transactions.py` (dead code de disco pós-[[ADR-212]], zero
call-sites, e único outro sítio do repo com a string do `const`); reescreve a fixture
para espelhar o produtor. `additionalProperties` **fica sem setar**. Medir os dois
produtores de novo — não presumir.

**PR-B — re-derivar do shape único.** Declarar as chaves reais, aposentar as
fantasmas restantes, colapsar o `oneOf` de raiz (o Format B `declarations` é ramo
morto pela medição do próprio §F — mesma classe que a [[ADR-427]] D4 consertou no E4)
e **então** decidir `additionalProperties`.

## Critério de aceite

- [ ] Dois runs em dias civis distintos, mesmo input → `sha256` **idêntico** do balde
      `patrimonio`. Gate mede o **efeito** (hash), nunca o relógio.
- [ ] `measure_schema_drift --schema baseline_patrimonial.schema.json --all` com o
      número **antes e depois** no corpo do PR, para os dois produtores.
- [ ] Controle negativo: reinserir `pipeline_stage` na fixture **reprova**.
- [ ] PR-B: `additionalProperties: false` com os dois produtores em 0 de drift no
      corpus, medido. Gate de completude por **igualdade de conjunto** entre chaves
      declaradas e emitidas, nos dois sentidos ([[ADR-427]] D5).
- [ ] §Deferimento da [[A40.l58]] corrigido: o produtor declarado é o E4
      pós-normalização; são dois produtores desde a [[ADR-427]] D3; e
      `additionalProperties` não se decide antes do PR-A.

## Fora de escopo

O `valores_31_12` negativo (3/71) é defeito de **dado** com regra de domínio própria —
vive na [[A40.l111]], dono `financial-planner`. Mantê-lo fora é o que permite a medição
do PR-B ser honesta.
