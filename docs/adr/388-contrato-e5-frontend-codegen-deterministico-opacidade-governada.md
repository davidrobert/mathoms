---
id: ADR-388
type: adr
title: "Contrato E5 para frontend usa codegen determinístico e opacidade governada"
status: Decidido
phase: A40.l5
date: "2026-08-14"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-102]]"
  - "[[ADR-114]]"
  - "[[ADR-217]]"
  - "[[ADR-284]]"
  - "[[ADR-338]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 388"
  - "codegen do contrato E5"
  - "opacidade governada do view-model"
size_lines: 142
tags:
  - type/adr
  - status/decidido
  - area/frontend
  - area/pipeline
  - area/dx
  - phase/a40-l5
---

# ADR-388 — Contrato E5 para frontend por codegen determinístico

> Origem: co-design da [[A40.l5]] com `data-engineer` e
> `information-architect`, após os apertos producer-backed dos PRs 1, 2 e 4.

## Contexto

O artefato E5 era descrito simultaneamente pelo JSON Schema, por tipos TypeScript
manuais e por leitores permissivos. Objetos sem `properties`, arrays sem `items`
e index signatures permitiam ler uma chave que nenhum produtor emitia sem erro de
compilação. Fixtures manuais podiam repetir a mesma crença errada do leitor.

O schema também tem múltiplos writers e artefatos históricos. Fechar o topo ou
promover todo campo observado a `required` quebraria evolução aditiva e poderia
rejeitar writes válidos. A solução precisa distinguir contrato canônico de escrita,
compatibilidade de leitura histórica e dívida de blocos ainda sem shape.

## D1 — JSON Schema é a fonte do tipo canônico

`config/schemas/e5_analysis.schema.json`, incluindo `$defs` e `$ref` externos
irmãos, gera `frontend/src/generated/report-analysis.ts`. O gerado é espelho do
contrato: campo em `required` é obrigatório; campo apenas em `properties` é
opcional; tupla fechada preserva aridade; enums viram uniões literais.

O emitter é determinístico e fail-closed. Keyword estrutural não suportada,
referência inexistente ou tuple schema ambíguo aborta a geração. O fallback não é
`unknown`, `any` nem index signature.

## D2 — Objeto aberto no writer não abre o leitor

`additionalProperties: true` no topo permite que outro stage acrescente bloco ao
artefato sem autorizar o frontend a ler qualquer chave. O codegen não emite index
signature para esse caso. Objetos fechados continuam exatos; mapas deliberados só
nascem de `patternProperties` ou de `additionalProperties` com schema de valor.

Isso preserva a decisão de múltiplos writers sem reintroduzir a classe que a lane
elimina: `data.campo_inventado` não compila.

## D3 — Opacidade é exceção rastreada

Objeto top-level sem shape exige `x-codegen` com exatamente `opaque: true`,
`reason` e `owner` não vazios. Bloco tipado não pode manter o marcador. O gerado
representa a exceção como `Record<string, never>`.

Uma baseline explícita funciona como ratchet: opacidade nova falha; opacidade
removida exige baixar a baseline no mesmo change. Qualquer leitor TypeScript de um
bloco opaco também falha. Em A40.l5, somente `programa_milhas` permanece opaco e
sem consumidor, candidato à deleção sob [[ADR-364]].

## D4 — Escrita canônica estrita, leitura histórica tolerante

`E5AnalysisArtifact` permanece o tipo canônico exato para writers, goldens e
codegen. O boundary do GET de relatório aplica `DeepPartial` somente ao snapshot
histórico, porque artefatos antigos não são revalidados nem recebem backfill.

Antes de um bloco histórico entrar num componente financeiro estrito, um guard
verifica os campos que o componente usa. Bloco incompleto é ocultado ou degradado;
o frontend não usa cast local, non-null assertion nem default financeiro inventado.

Campo emitido não vira automaticamente `required`. A promoção exige prova dos
writers e do corpus, conforme [[ADR-284]]. Campos aditivos de score como
`breakdown`, `context` e `conclusion` ficam opcionais no objeto para preservar
artefatos antigos, enquanto cada item de `breakdown` é fechado e completo quando
presente.

## D5 — Gate único fecha sincronização e consumo opaco

`dev/check_view_model_contract.py` roda como hook `always_run` e verifica:

- arquivo gerado byte-a-byte em sync;
- metadata e ratchet dos blocos opacos;
- ausência de leitores TypeScript de opacidade;
- nomes literais de schema usados por `validate_dict` apontando para arquivo real.

`tsc --noEmit` permanece reforço para diffs frontend. A terceira perna,
schema × produtor, fica nos goldens E5 com validação strict e nos testes de
mutação producer-backed; o codegen não substitui essa prova.

## Alternativas rejeitadas

- **Manter tipos manuais:** preserva drift e index signatures permissivas.
- **Gerar `unknown` para construção não suportada:** deixa o gate verde e inútil.
- **Fechar `additionalProperties` no topo:** confunde consumidores fechados com
  writers múltiplos e quebra merges aditivos.
- **Tornar todo campo observado obrigatório:** invalida artefatos históricos e
  transforma uma amostra em contrato.
- **Aplicar `Partial` ao tipo canônico:** perde a garantia dos writers e goldens.

## Consequências

- Mudança intencional de schema exige regenerar o TypeScript e o hash E5.
- Leitores de snapshots antigos precisam de guard explícito antes de componentes
  que calculam ou formatam números.
- O dialeto suportado pelo emitter é pequeno e deliberado; expandi-lo exige teste
  golden e mutação fail-closed.
- O flip global `warn → strict` continua fora desta decisão, em [[A40.l58]].

## Critério de aceite

- Gerar duas vezes produz bytes idênticos; editar o gerado faz o gate falhar.
- Campo inexistente e leitura de bloco opaco falham antes do merge.
- Keyword não suportada, `$ref` ausente e nome literal de schema inválido falham.
- Payload real de score e arrays aninhados valida strict; mutações de item falham.
- Artefato legado sem campos aditivos continua válido e a UI não fabrica número.
- `npm run type-check`, goldens producer-backed e hook de pre-commit ficam verdes.

## Referências

- [[A40.l5]] — inventário, decomposição PR0–PR5 e medição da classe.
- `dev/report_analysis_codegen.py` — emitter.
- `dev/check_view_model_contract.py` — gate composto.
- `frontend/src/lib/api/reports.ts` — boundary de leitura histórica.
