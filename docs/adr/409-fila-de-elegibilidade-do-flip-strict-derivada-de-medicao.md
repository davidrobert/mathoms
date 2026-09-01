---
id: ADR-409
type: adr
title: "Fila de elegibilidade do flip warn→strict é derivada de medição no corpus, e o rollback exige restart"
status: Decidido
phase: A40.l58
date: "2026-08-24"
amended_at: ["2026-08-31"]
relates_to:
  - "[[ADR-284]]"
  - "[[ADR-407]]"
  - "[[ADR-212]]"
  - "[[ADR-093]]"
  - "[[ADR-110]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 409"
  - "fila de elegibilidade do flip strict"
  - "measure_schema_drift"
  - "rollback de schema exige restart"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/observability
---

# ADR-409 — Fila de elegibilidade do flip `warn→strict` é derivada de medição no corpus, e o rollback exige restart

**Status:** Decidido (A40.l58 · PRs #1656/#1664/#1665/#1667) • **Data:** 2026-08-24 • **Relaciona** [[ADR-284]]
(mode_overrides, enforcement, telemetria — a decisão que esta complementa),
[[ADR-407]] (stage polimórfico despacha por discriminador), [[ADR-212]] (hook
pós-write), [[ADR-093]] (nomes de stage), [[ADR-110]] (logs JSON).

> ⚠️ **Emendada em 2026-08-31** — a cláusula de massa do §B nunca mediu documentos,
> e a cadência do §B está desatualizada por ~2,5×. E o §F media o produtor errado: o
> enxerto que ele diz ser "em memória" está persistido em 71/71 artefatos. Ver as duas
> §Emenda no fim.

## Contexto

A [[ADR-284]] entregou a fundação do flip: `mode_overrides` per-schema,
enforcement strict real e telemetria de drift. Deixou o flip como **operação**,
gated por *"baseline ≥7 dias zero-WARN para o schema alvo"*, medido por
agregação dos logs JSON (runbook
[`schema_validation_strict_flip.md`](../reference/runbooks/schema_validation_strict_flip.md) §2).

Em 2026-08-24 a [[A40.l58]] mediu o corpus real pela primeira vez — 16.292
artefatos em `pipeline_artifacts`, com o código de `main` e a mesma chave do gate
(`_count_drift_paths`). O §Ataque da lane tem a medição completa. Três fatos que
a ADR-284 não tinha como saber:

1. **O gate por log depende de um sink que ninguém agrega, e o mesmo número é
   derivável do próprio corpus** — retroativamente e sem depender de retenção.
2. **O rollback do §5 do runbook é inerte no worker vivo.** `load_json_config`
   cacheia `pipeline.json` (`scripts/pipeline_common.py:146`); reverter
   `mode_overrides` no disco **não** muda o modo efetivo do processo que está
   rodando. Medido.
3. **Dois schemas da fila não têm drift transitório — têm defeito de contrato.**
   `baseline_patrimonial` mede 100% em 91/91 e `e2_extract` drifta em 6/6 runs
   por um segundo produtor sob o mesmo stage.

## Decisão

### A — A unidade do flip continua per-schema; o global sai por deferimento datado

Conforma a [[ADR-284]] §C e o *"nunca global de uma vez"* do runbook — **não a
supersede**. O §Escopo 3 da [[A40.l58]], que tratava `schema_validation.mode`
como chave única global, fica **revogado** (encaminhamento 2 da §Coordenação
RV6-06 da lane). Flip global é deferido sem data de retomada: só volta à mesa se
N schemas forem promovidos per-schema e alguém declarar o N.

### B — O go/no-go é `dev/measure_schema_drift.py` sobre `pipeline_artifacts`, não a agregação de logs

A telemetria da [[ADR-284]] §B **permanece** — ela é o detector em tempo real e o
sinal de incidente pós-flip (§4 do runbook). O que muda é **quem responde o
go/no-go de promoção**:

```bash
python3 dev/measure_schema_drift.py --schema <alvo> --days 7 --gate
```

Razões, nesta ordem:

- **Durabilidade.** O artefato fica em `pipeline_artifacts` com `created_at`; a
  linha de log não fica em lugar nenhum por padrão. Um gate que depende de sink
  configurado é gate que reprova por ausência de infra, não por ausência de drift.
- **Re-medição.** O repo já paga caro por número citado em prosa que envelhece.
  Com o comando, o número do PR de flip **se re-mede em segundos** em vez de se
  reler.
- **Gate de PR.** `--gate` sai com exit ≠ 0 quando há drift, então o PR de flip
  pode ser travado no CI em vez de depender de o operador ter rodado o `jq`.
- **Retroatividade.** A janela é uma cláusula `WHERE`, não uma espera. Descobrir
  que a janela precisa recomeçar não custa 7 dias de novo.

**Predicado de GO** (implementado em `SchemaDrift.is_go`):
`artifacts > 0 AND drifted == 0 AND unreadable == 0`.

As duas guardas além do óbvio são deliberadas:

- **Janela sem artefato não é GO** — é ausência de medição. A cadência do dogfood
  é de ~2 runs/semana e houve 6 dias sem nenhum run em agosto; sem esta guarda a
  janela vazia se lê como aprovação.
- **Artefato ilegível não é GO** — não-validado não é validado-sem-drift. (Esta
  guarda nasceu de um falso-verde no próprio instrumento, pego pelo teste.)

O instrumento reporta ainda **`documents` distintos**, não só `artifacts`: 6
artefatos do mesmo documento em 6 runs não são 6 evidências. O PR de flip cita a
massa em documentos.

### C — Dois levers de rollback, ambos exigindo restart do worker, declarados por situação

| Situação | Lever | Blast radius | Custo |
| --- | --- | --- | --- |
| Rollback durável (o schema volta a `warn` de vez) | revert de `mode_overrides` + deploy | só o schema revertido | deploy normal — **e o deploy reinicia o worker, que é o que aplica** |
| Emergência (segundos, sem build) | `MATHOMS_PIPELINE_SCHEMA_MODE=warn` + restart | **global** — despromove todos os schemas | restart |

**Não se adota hot-reload de `pipeline.json`.** O arquivo é versionado no repo:
mudá-lo já é um deploy, e um deploy já reinicia o worker. Hot-reload custaria uma
leitura de arquivo por write e não compraria janela nenhuma. O que faltava não era
mecanismo — era o runbook **dizer** que o revert só vale após restart, corrigido
em 2026-08-24 no §5.

Consequência declarada do lever de emergência: enquanto houver **1** schema
promovido, os dois levers são equivalentes; **do 2º em diante**, usar a env
despromove tudo em silêncio. Quem a usar registra no §7 do runbook os schemas que
voltaram a `warn`.

### D — Ordem dura: contrato antes de janela; a fila é a medição, não a intenção

Medido em 2026-08-24, janela 2026-08-12..08-18 (6 runs, 1 workspace):

| schema | artef. | drift | docs | decisão |
| --- | ---: | ---: | ---: | --- |
| `e3_reconciled` | 555 | 0 | 111 | **1º da fila** |
| `e15_baseline_extract` | 66 | 0 | 11 | **2º da fila** |
| `informe_base` | 30 | 0 | 5 | elegível, massa declarada no PR |
| `e16_irpf_full` | 24 | 0 | 4 | elegível, massa declarada no PR |
| `informe_aluguel` | 18 | 0 | 3 | elegível, massa declarada no PR |
| `e2_llm_artifact` | 2 | 0 | 2 | **não promove** — n=2 em 1 run não é evidência |
| `e5_analysis` | 5 | 5 | 1 | reavaliar após 1 run novo (drift histórico) |
| `comprovante_base` | 36 | 36 | 6 | reavaliar após 1 run novo (drift histórico; produtor pós-[[ADR-407]] estampa o discriminador) |
| `e4_unified` | 35 | 5 | 7 | **bloqueado** — `oneOf` colapsa o path em `$` ([[ADR-407]] D2) |
| `e2_extract` | 812 | 54 | 136 | **bloqueado** — ver §E |
| `baseline_patrimonial` | 6 | 6 | 1 | **fora da fila** — ver §F |

"Drift histórico" = o schema apertou depois do último run; o artefato não é
inválido para o contrato sob o qual nasceu. Não se corrige produtor por isso — se
mede de novo depois do próximo run.

### E — `e2_extract`: o drift não é vocabulário, é um segundo produtor sob o mesmo stage

`generate_llm_fallback` (`scripts/extract_bank_documents.py:101`) persiste um stub
sem `banco`/`moeda` sob `extract_statements`/`extract_invoices` quando nenhum
parser reconhece o documento. É a **terceira instância da classe da [[ADR-407]]** —
stage com N formas de payload e mapa 1:1 para schema.

Flipar hoje aborta o write exatamente dos documentos que o parser não soube ler: o
run morre em E2 **antes** de o fallback LLM existir. O `tipo` do stub
(`fatura_desconhecida` / `extrato_desconhecido`) já **é** um discriminador
declarado — a forma do fix é a da ADR-407, não afrouxar o `required`.

O corpus 22/22 (`tests/test_e2_schema_strict_corpus.py`) não alcança o stub por
construção: enumera `registry._ALL_PARSERS` (`:353`) e **rejeita o shape por
asserção** (`:363`). Pré-condição de corpus de `e2_extract` reaberta no runbook
§1.2.

### F — `baseline_patrimonial` sai da fila até o contrato ser re-derivado do produtor

Medido sobre os 91 artefatos do corpus (4 shapes de topo, 2026-05-15..08-18):

- **8 das 13 properties declaradas nunca foram emitidas por artefato nenhum**:
  `anos_base`, `data_processamento`, `declarations`, `membros`, `pipeline_stage`,
  `properties`, `receipts`, `summary`.
- **8 chaves emitidas não são declaradas**, 3 delas em 100% dos artefatos
  (`resumo`, `_meta`, `itens`). Passam porque `additionalProperties` não está
  setado.
- Sobreposição: **5 de 13**. `summary`/`resumo` e `membros`/`itens` são o
  vocabulário anterior a um rename que o schema não acompanhou.

Os 2 `required` que hoje derrubam 100% dos writes (`pipeline_stage`,
`data_processamento`) são o mesmo vestígio da era disco que a [[ADR-284]] §D
removeu do `e2_extract` — `pipeline_stage` chega a exigir
`const: "E1.5_Baseline_Patrimonial"`, nome que a [[ADR-093]] não reconhece e que
pós-[[ADR-212]] é coluna do DB. Quem os preenche é o `BaselineNormalizer`, e ele
roda **na leitura, dentro do E4** (`e4_categorizer_adapter.py:272`), em memória,
nunca reescrito no artefato.

**A correção mínima é recusada explicitamente.** Tirar os 2 `required` levaria o
schema a 0 de drift e o tornaria "elegível" pelo predicado do §B — e o flip seria
**verde sobre contrato que descreve 5/13 do payload**. Promover isso a strict não
protege nada e passa a afirmar proteção. Ou o contrato é re-derivado do produtor
(declarar as 13 chaves reais, decidir `additionalProperties`, aposentar as 8
fantasmas), ou o schema fica em `warn` com a razão escrita.

Re-derivar o contrato **não é trabalho desta lane** — é contrato do produtor
E1.5c, gatilho `data-engineer`. Fica como §Deferimento datado com dono na
[[A40.l58]].

## Não-decisões (rejeitadas / adiadas)

- **Hot-reload de `pipeline.json`** — o arquivo é versionado; mudá-lo é deploy, e
  deploy reinicia. Custo por write sem ganho de janela.
- **Aposentar a telemetria de log da [[ADR-284]] §B** — ela é o detector em tempo
  real e o sinal de incidente do §4; o corpus responde promoção, não incidente.
- **Tirar só os 2 `required` de `baseline_patrimonial`** — ver §F. Torna o número
  verde sem tornar o contrato real.
- **Flipar qualquer schema nesta ADR** — o flip é operacional e per-schema, com o
  número citado no PR (§B). Esta ADR decide a fila e o lever, não executa.
- **Alerta automático de drift contínuo** — segue como follow-up da [[ADR-284]],
  não antes do primeiro flip.

## Consequências

- O go/no-go do runbook §2 passa a ter **um comando**, reprodutível por qualquer
  agente, com exit code utilizável em CI.
- A fila de promoção existe e é derivada de medição: 5 schemas elegíveis, 1
  recusado por massa, 2 a reavaliar, 3 bloqueados com razão nomeada.
- Duas classes de defeito de contrato ficam **nomeadas e roteadas** em vez de
  aparecerem como "drift" transitório — `e2_extract` (classe ADR-407) e
  `baseline_patrimonial` (contrato de outro payload).
- Custo: zero mudança de comportamento em produção. `mode` segue `warn`,
  `mode_overrides` segue `{}`.
- O primeiro flip real continua gated no que a lane não controla: **precisa de
  runs**. A janela de 7 dias exige pipeline ativo, e o último run do corpus é de
  2026-08-18.

## Critério de aceite

> ✅ **Os cinco fechados em 2026-08-24** — `Proposto` → `Decidido`. Cada um tem
> teste, não prosa; ver §Passo 2 e §Passo 4 da [[A40.l58]].

- `dev/measure_schema_drift.py --schema X --days 7 --gate` sai 0 para schema sem
  drift com massa, e ≠ 0 com qualquer drift.
- Janela sem artefato e artefato ilegível **não** produzem GO — teste, não prosa.
- O path de drift emitido pelo instrumento é o mesmo da telemetria
  (`$.banco`, não `$`) — teste parametrizado sobre o drift real medido.
- Kill-switch provado: com a env de rollback setada, payload inválido volta a
  logar-e-passar.
- Runbook §5 declara o restart; §1.2 declara a pré-condição de `e2_extract`
  reaberta.

## Emenda 2026-08-31 — dois números do §B não sobreviveram à re-medição

Levantado ao preparar o **primeiro flip do repositório** ([[A42.l19]], schemas por balde
do E4). Ambos verificados em `pipeline_artifacts` (18.246 rows, corpus de dogfood).

**1. "O PR de flip cita a massa em documentos" é inerte — e sempre foi.**
`dev/measure_schema_drift.py` faz `stats.documents.add(row.document_id or row.artifact_key)`,
e **`document_id` é NULL em 18.246/18.246 rows**: nenhum writer o preenche (o parâmetro
existe em `db_artifact_store.py`, o caller em `pipeline/artifact_store.py`, e nada o
exercita). Logo `documents` ≡ `artifact_key` distintas, **em toda a fila**, não só no E4.

Para `e3_reconciled` isso lê certo **por acidente** — a key é per-documento
(`itau_extratoconta_BRL_202212_202604`) — e a tabela do §D herda o acidente. Para
artefato de agregado o número degenera: `e4_pontos_milhas` reporta `docs=1` sobre
**71 cópias byte-idênticas** do mesmo `{"dados": []}` e ainda assim sai `GO`. Era essa
leitura que fazia "promover em lote" parecer defensável no instrumento.

**Correção:** enquanto `document_id` não for preenchido, a massa citada no PR de flip é
**payloads distintos** (`sha256` do JSON canônico), com artefatos e runs ao lado. Medido
para os baldes E4: `receitas`/`despesas` 71/71, `investimentos` 40/71,
`fluxo_mensal_detalhado` 21/71, `seguros` 5/71, `pontos_milhas` **1**/71. Preencher
`document_id` no writer, ou trocar a métrica no instrumento, fica como trabalho próprio —
`owner: data-engineer`.

**2. A cadência que o §B usa para dimensionar a janela está desatualizada.** O §B fala em
*"~2 runs/semana"*. Medido sobre os 71 runs de E4 em 14 semanas: **mediana de 5
runs/semana** (mín 1, máx 14) e **26 runs nos últimos 35 dias**. A janela do §4 do runbook
(*48h ou ≥10 runs*) fecha em **~2 semanas** típicas, não em ~5. O número importa porque é
ele que precifica serializar promoções — e precificá-lo errado por 2,5× já produziu
recomendação oposta entre dois especialistas na mesma decisão.

## Emenda 2026-08-31 — o §F media o produtor errado, e o enxerto **era** persistido

> Sinal: o §F afirmava que o `BaselineNormalizer` roda "em memória, nunca reescrito
> no artefato". Medido no corpus inteiro: **71/71** artefatos `patrimonio` do E4
> carregam os 2 campos, persistidos. A [[A40.l110]] executou a remoção que o §F
> recusava — por outra razão, e sem destravar o flip que ele protege.

**1. "Quem os preenche é o `BaselineNormalizer`, e ele roda na leitura, dentro do E4,
em memória, nunca reescrito no artefato" — falso.** O balde `patrimonio` do E4 **é** um
artefato persistido, e desde a [[ADR-427]] D3 é validado contra este mesmo schema pela
`artifact_key`. Medido em `pipeline_artifacts` (corpus inteiro, 0 ilegíveis):

| produtor | artefatos | com os 2 campos |
| --- | --- | --- |
| `E4`/`categorize_transactions` · `patrimonio` | 71 | **71** |
| `E1.5c`/`consolidate_baseline` · `baseline_patrimonial` | 98 | **0** |

**2. "Re-derivar do produtor E1.5c" nomeia um produtor só, e são dois.** A
`description` do próprio schema declarava o outro. O §F escolheu o shape de quem
**não** emite os campos; executá-lo ao pé da letra escolheria o shape errado.

**3. A não-decisão "tirar só os 2 `required`" não cai — muda de razão, e a razão dela
segue viva.** O §F recusava a remoção por ela tornar *o número* verde sem tornar *o
contrato* real. Isso continua verdade. A [[A40.l110]] PR-A removeu os 2 campos assim
mesmo porque o defeito não era de número: o enxerto do `data_processamento` caía em
`date.today()` e era **gravado**, então o mesmo input em dois dias civis produzia
`sha256` diferente — quebra de idempotência em artefato persistido. Contrato incompleto
é dívida; relógio em artefato é defeito.

**4. O que o §F protegia passa a ser enforçado, não descrito.** Antes desta emenda a
elegibilidade era só a medição, e o §F vivia em prosa: com o drift indo a 0, o
predicado do §B diria `GO` para um contrato que descreve 5/13 do payload. `baseline_patrimonial`
entra em `_CONTRATO_NAO_DERIVADO` em [`dev/measure_schema_drift.py`](../../dev/measure_schema_drift.py)
— o veredito é `NO-GO` **independente do drift**, com a razão e a lane que o levanta
([[A40.l110]] PR-B) na própria mensagem.

Drift medido no corpus inteiro, antes → depois do PR-A (169 artefatos, 105 runs,
116 payloads distintos, 0 ilegíveis):

| produtor | antes | depois | paths residuais |
| --- | --- | --- | --- |
| `consolidate_baseline` (E1.5c) | 98/98 (100%) | **3/98 (3,1%)** | `imoveis_consolidados[].valores_31_12` `minimum` |
| E4 `patrimonio` | 3/71 (4,2%) | **3/71 (4,2%)** | idem |
| agregado | 101/169 (59,8%) | **6/169 (3,6%)** | idem |

Os 2 `required` respondiam por 392 das 398 ocorrências. As 6 restantes são
`valores_31_12` negativo — defeito de **dado**, não de contrato, roteado para a
[[A40.l111]]. Os dois produtores convergiram no mesmo path e no mesmo item: a
divergência entre eles era exatamente os 2 campos.

A [[A40.l111]] mergeou no mesmo dia ([[ADR-431]], #1917) e as 6 **continuam** —
re-medido. O saneamento dela vale para run nova; o corpus histórico guarda os
negativos já persistidos, e o `minimum: 0` segue reprovando-os. O drift deste
schema chega a 0 quando as runs virarem o corpus, em data que ninguém agenda — e é
exatamente por isso que o §4 acima precisa ser enforcement, e não uma promessa de
revisitar o assunto quando o número mudar.
