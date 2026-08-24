---
id: A40.l58
type: lane
title: "schema_validation warn → strict: o PR5 que a l5 declarou como outra lane"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P2
branch_slug: a40-l58-flip-do-schema-para-strict
owner: sre-devops
adrs: ["[[ADR-409]]"]
depends_on:
  - "[[A40.l5]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/pipeline
---

# A40.l58 — `flip-do-schema-para-strict`

> 🔓 **Desbloqueada em 2026-08-17 — o bloqueador morreu em 2026-08-14 e ninguém
> viu.** A condição escrita abaixo era *"os PRs 2–4 da l5"*: **#1440** (PR2,
> 08-13), **#1441** (PR4, 08-14) e **#1450** (PR3, 08-14) estão **todos
> mergeados**. A lane ficou `blocked` por **3 dias** sobre dep satisfeita.
>
> `depends_on: [[A40.l5]]` **permanece** — a dep é real e agora está terminal
> (`shipped`, 2026-08-17). O que estava errado era o `status`, não o grafo.
>
> **O instrumento funcionou; o insumo é que estava podre.** O
> [`_sprint_current_renderer`](../../../../dev/_sprint_current_renderer.py) **já**
> dá seção própria ao `blocked` — exatamente para que lane bloqueada não suma no
> instante em que vira pegável (comentário no `:44`) — e ainda imprime a dep
> pendente. O que ele imprimia era **`⛔ dep pendente: A40.l5 (in_progress)`**:
> uma frase que lê como bloqueio legítimo, porque o `status` da l5 também estava
> stale.
>
> **Dois status stale se mascararam mutuamente.** Nenhum leitor humano tinha
> como suspeitar: a linha do painel era coerente consigo mesma. Só cruzar o
> frontmatter com os PRs mergeados em `main` desfaz — que é a checagem que
> nenhum gate fazia.
>
> **Classe, não incidente.** O merge da dep não tem escritor no `status` da lane
> dependente: quem fecha a dep não sabe quem depende dela. É a mesma classe que a
> [[A40.l59]] gateia na transição — registrada lá como caso de origem.
>
> **Motivo original do bloqueio (preservado — era correto quando escrito):**
>
> > **`blocked` por [[A40.l5]]** — o flip exige *"o drift medido em mãos"*
> > (§Forma da l5), e o drift só existe depois que os PRs 2–4 da l5 tiparem os
> > blocos restantes do `e5_analysis.schema.json`. Flipar antes é converter
> > lacuna de tipagem em run de cliente abortado.
>
> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Origem: [[A40.l5]] §Forma, PR5 — *"Proposta `warn → strict` …
> **Outra lane.** ADR própria + gatilho `sre-devops` (blast radius = run de
> cliente)"*. Esta lane materializa a rota que a l5 prometeu; "outra lane" que
> não existe é rota que aponta para o nada.

## Problema

A validação de schema do pipeline roda em modo `warn` em produção
(`pipeline.json → schema_validation.mode`, override
`MATHOMS_PIPELINE_SCHEMA_MODE`): payload que viola o contrato **loga e passa**.
O gate real de schema é o golden de execução — que a l5 descobriu ter ficado
**anos sem validar nada** (o `pipeline.json` de teste era `{}`, `enabled`
defaultava `False`). A l5 ligou a validação `strict` **fixa** na suíte; falta o
flip em produção, onde o blast radius é run de cliente.

## Escopo

1. **ADR `Proposto` antes do PR** (exigência registrada na l5) — decide o modo
   de rollout: strict direto, ou observação → strict com kill-switch.
2. Medição do drift real: com os PRs da l5 mergeados, quantos payloads de
   produção violariam `strict` hoje? (Zero é hipótese, não premissa.)
3. Flip com kill-switch documentado (`MATHOMS_PIPELINE_SCHEMA_MODE=warn` como
   rollback de 1 env var, sem deploy).
4. Re-adoção do "flip órfão" que a l5 registrou: a suíte valida com `strict`
   fixo, não dependente de CI lembrar de setar env.

## Coordenação declarada — RV6-06 (escrita em 2026-08-17, Onda 0 do [[PLAN-deterministic-authority]])

Esta lane **permanece dona do `mode_overrides` e do kill-switch como infra**. O
que mudou de mãos é o *consumo* dessa infra para dois schemas específicos: o item
1e do [[PLAN-deterministic-authority]], materializado na [[A40.l67]], flippa
`baseline_patrimonial` e o schema irmão do E1.5a **per-schema**, via
`mode_overrides`, com drift medido por ≥7 dias de dogfood. A [[A42.l6]] cedeu o
mesmo eixo e mantém retenção/`SCHEMA_BY_STAGE`.

**Tensão que o dono desta lane precisa resolver — não a resolvo aqui.** O §Escopo
acima trata do flip **global** (`pipeline.json → schema_validation.mode`), e o
plano carrega anti-decisão explícita em sentido contrário: *"NÃO subir
`schema_validation.mode` global — só per-schema com janela medida."*

**Correção de 2026-08-17 (closeout): o contraditor não é o plano.** A primeira
escrita desta seção enquadrou isto como plano `draft` × lane, e enumerou como
saída *"a ADR desta lane supera a anti-decisão do plano, que então é emendada"*.
Está errado no artefato e, portanto, na altura da barra. Quem já decidiu é a
[[ADR-284]] (**`Decidido`**, 2026-06-09), cujo runbook operacional
[`schema_validation_strict_flip.md`](../../../reference/runbooks/schema_validation_strict_flip.md)
diz na abertura: *"O flip é por schema (`mode_overrides`), **nunca global de uma
vez**: strict global abortaria runs em qualquer stage com drift não-mapeado."* O
§Anti-decisões do plano não cria posição nova — **repete** essa doutrina.

Dois pontos concretos em que o §Escopo acima diverge da ADR-284, e que a ADR
desta lane precisa endereçar por escrito:

- **O lever de rollback.** O item 3 nomeia `MATHOMS_PIPELINE_SCHEMA_MODE=warn`
  como kill-switch. A [[ADR-284]] §C posiciona essa env como **global, de
  CI/escape**, e o §Rollback do runbook define o lever de produção como *"revert
  de 1 linha em `mode_overrides`"*. São mecanismos diferentes com blast radius
  diferente.
- **A unidade do flip.** O §Escopo trata o modo como chave única; a [[ADR-284]]
  §C estabelece precedência `env > mode_overrides[schema] > mode`, e o §Não-decisões
  já rejeitou *"flipar strict nesta lane"* — o flip é operacional, gated por
  baseline ≥7 dias zero-WARN **por schema alvo**.

Encaminhamentos possíveis, todos do `sre-devops` — com a barra real:

1. a ADR desta lane decide o rollout global e **supersede a [[ADR-284]]**
   (frontmatter `supersedes`/`superseded_by` nos dois lados + atualização do
   runbook, [[ADR-182]]) — não basta emendar o plano;
2. esta lane se re-escopa para "entregar e provar a infra per-schema" — que é o
   que a ADR-284 já manda — e o global vira deferimento datado;
3. as duas convivem com o global **depois** de N schemas flipados per-schema, com
   o N declarado; como isto contraria o *"nunca global de uma vez"* do runbook,
   exige emenda datada na [[ADR-284]], não só nota aqui.

Nenhuma das três estava citando a ADR-284: até este closeout, `rg "ADR-284"`
retornava **zero** nesta lane, no plano e na [[A42.l6]] — as três pernas da
disposição discutiam o eixo sem citar quem já o decidiu.

Enquanto não houver decisão, vale a regra operacional da fila (§0d do plano):
esta lane e a [[A40.l67]] **não podem estar abertas na mesma janela de
rebaseline** — J2 é da l67.

## Critério de aceite

- ADR mergeada antes do PR de flip, com a decisão de rollout e o rollback
  declarados.
- O drift pré-flip está **medido e citado** na ADR (não "acreditamos que zero").
- Kill-switch provado: com a env de rollback setada, payload inválido volta a
  logar-e-passar — teste, não prosa.
- Runbook de incidente: o que fazer quando um run de cliente aborta por schema
  (gatilho `sre-devops`).

## Aporte da [[A40.l74]] — dois schemas saem da inelegibilidade, um continua nela (2026-08-21)

**Entra na baseline.** `crlv.schema.json` e `apolice.schema.json` eram
**permanentemente inelegíveis** ao flip: o stage `extract_comprovantes_bens` tem dois
produtores e o mapa 1:1 apontava para o schema de veículo, então todo write de apólice
emitia WARN (25 paths em drift, medidos). [[ADR-407]] fecha isso; o merge da l74 é o
**dia 0** da baseline de ≥7 dias zero-WARN destes dois.

**Continua fora — e é maior:** `e4_unified.schema.json` tem 5 ramos em `oneOf` que
discriminam por `required`. Medido: com **um** drift real, `oneOf` emite path `$` e
`if/then` emite o campo. `iter_errors` não faz union dos erros de ramo — emite um erro
no keyword `oneOf` com os sub-erros em `error.context`, onde `_validation_paths`
([[ADR-284]] §B) não desce. O drift do E4 é portanto **indiagnosticável**: a baseline
zero-WARN pode até ser atingida, mas um WARN nunca diz qual das 7 artifact keys
regrediu, nem em que campo.

Medido com payload E4 **válido** do ramo `seguros v2` como baseline (atenção: o
`const` de `schema_version` é a string `"2"`, não o inteiro — payload de controle
errado mede drift sobre baseline já quebrado):

| drift de UM campo | path emitido |
| --- | --- |
| falta `seguradora` num item de `apolices[]` | `$` |
| `premio_total_brl` como `number` (viola [[ADR-090]]) | `$` |
| outro ramo, falta `total_geral` | `$` |

A segunda linha é a que dói: **violação de float-monetário**, a classe que este
repo mais gateia, reporta como `$` em vez de `$.apolices[].premio_total_brl`.

Consequência para o critério desta lane: "drift pré-flip medido e citado" **não é
satisfazível** para `e4_unified` no desenho atual. Ou o schema migra para despacho por
discriminador ([[ADR-407]] D2), ou o E4 sai do escopo do flip com a razão declarada.

## Ataque (2026-08-24) — o drift foi medido; três alvos do flip são inelegíveis por construção

> Medido **antes do pickup**, com o código de `main` (`47c0988e`) contra o corpus
> real (16.292 artefatos, `pipeline_artifacts`), em `MATHOMS_PIPELINE_SCHEMA_MODE=strict`,
> usando a **mesma chave do gate** — `_count_drift_paths`/`_validation_paths` de
> [`schema_drift_telemetry.py`](../../../../scripts/schema_drift_telemetry.py), não uma
> reimplementação. Lane segue `open`; nada de código foi tocado.
>
> **Cuidado de método que muda o resultado:** a primeira passada usou a árvore do
> repo principal, que estava numa branch de agosto/19 — pré-#1604. Ali
> `extract_comprovantes_bens` ainda apontava para `crlv.schema.json` e o drift
> saía 25 paths. Contra `main` de hoje o mapa é `comprovante_base.schema.json` e o
> retrato é outro. Medição de flip precisa declarar **qual árvore** produziu o número.

### §2 do runbook, executado — a janela de 7 dias que o §1.3 exige

Último write do corpus: **2026-08-18**. Janela 2026-08-12..08-18, 6 runs, **1 workspace**.

| schema | artef. | drift | runs c/ drift | veredito |
| --- | ---: | ---: | ---: | --- |
| `e2_extract` | 812 | 54 (6,7%) | 6/6 | **NO-GO** |
| `comprovante_base` | 36 | 36 (100%) | 6/6 | NO-GO *(histórico — ver abaixo)* |
| `baseline_patrimonial` | 6 | 6 (100%) | 6/6 | **NO-GO estrutural** |
| `e4_unified` | 35 | 5 (14%) | 5/5 | NO-GO *(path `$`, indiagnosticável)* |
| `e5_analysis` | 5 | 5 (100%) | 5/5 | NO-GO *(histórico — ver abaixo)* |
| `e15_baseline_extract` | 66 | 0 | 0/6 | GO |
| `e3_reconciled` | 555 | 0 | 0/5 | GO |
| `e16_irpf_full` | 24 | 0 | 0/6 | GO |
| `informe_base` | 30 | 0 | 0/6 | GO |
| `informe_aluguel` | 18 | 0 | 0/6 | GO |
| `e2_llm_artifact` | 2 | 0 | 0/1 | GO *(n=2 — não é evidência)* |

O §Critério de aceite pedia *"o drift pré-flip está medido e citado (não
'acreditamos que zero')"*. **Não é zero: 1.902 dos 16.158 artefatos mapeados
(11,8%) violam o próprio schema.** Fora de `SCHEMA_BY_STAGE`, 134 artefatos
(`extract_members`/`E1`, `review_finances_holistic`/`E6-parecer`) nunca são
validados — o parecer tem schema em `config/schemas/` e não tem stage mapeado.

### A1 — `baseline_patrimonial` não pode ser flipado, e é o alvo declarado da [[A40.l67]]

**100% de drift em 91/91 artefatos do corpus inteiro**, incluindo o run mais
recente. Causa medida, não inferida:

[`baseline_patrimonial.schema.json:6`](../../../../config/schemas/baseline_patrimonial.schema.json)
exige `required: ["pipeline_stage", "data_processamento"]`, com
`pipeline_stage` travado em `const: "E1.5_Baseline_Patrimonial"` — nome de stage
da era disco, que nem existe no vocabulário da [[ADR-093]]. O writer
([`consolidate_baseline.py:1003`](../../../../scripts/consolidate_baseline.py)) não
estampa nenhum dos dois. Quem estampa é o `BaselineNormalizer`, e ele roda **na
leitura, dentro do E4**
([`e4_categorizer_adapter.py:272`](../../../../pipeline/domain/services/e4_categorizer_adapter.py))
— em memória, nunca reescrito no artefato.

**É o mesmo defeito que a [[ADR-284]] §D removeu do `e2_extract`** — *"`required`
exigia `pipeline_stage`, que **nenhum** writer estampa (vestígio da era disco;
pós-[[ADR-212]] o stage é coluna do DB) — todo write E2 em prod geraria WARN de
ruído"*. A ADR fechou a **instância** e deixou a **classe**: varri os 30 schemas
de `config/schemas/`, e `baseline_patrimonial` é o único outro com o vestígio.

Consequência dura para a coordenação declarada no §RV6-06 acima: o item 1e do
[[PLAN-deterministic-authority]], materializado na [[A40.l67]], promete flipar
`baseline_patrimonial` *"com drift medido por ≥7 dias de dogfood"*. **A baseline
zero-WARN é inalcançável sem consertar antes o schema ou o produtor** — flipar
aborta *todo* write de `consolidate_baseline`, ou seja, todo run, em E1.5c.

E o irmão que a mesma lane carrega tem veredito **oposto**: `e15_baseline_extract`
mede **0/66 na janela**. Os dois alvos de uma lane só, um elegível e outro
estruturalmente inelegível, e nenhum dos dois medido até aqui.

### A2 — o drift de `e2_extract` não é vocabulário: é um segundo produtor sob o mesmo stage

O §1.2 do [runbook](../../../reference/runbooks/schema_validation_strict_flip.md)
declara `e2_extract` com a pré-condição de corpus *"integralmente fechada — o gate
restante é só o baseline (§1.3)"*. Medido: drift em **6/6 runs** da janela, 54
artefatos, 9 `artifact_key` distintas, sempre os mesmos dois paths — `required
$.banco` e `$.moeda`.

Os 9 payloads têm **um único shape**, e não é o de nenhum parser:

```
['arquivo_origem', 'nota', 'requires_llm_fallback', 'texto_extraido_preview', 'tipo', 'transacoes']
```

É o stub de
[`generate_llm_fallback`](../../../../scripts/extract_bank_documents.py) (`:101`) —
escrito quando o parser determinístico não reconhece o documento, com `tipo` em
`{fatura_desconhecida, extrato_desconhecido}` e **sem `banco`, sem `moeda`**. Ele
é persistido sob `extract_statements`/`extract_invoices`, logo validado contra o
contrato dos parsers.

**Isto é a terceira instância da classe da [[ADR-407]]** (stage polimórfico com
mapa 1:1 para schema): a [[A40.l74]] fechou `crlv`×`apolice`, o §Aporte acima
deixa `e4_unified` aberto, e ninguém nomeou o E2. É também a de **pior blast
radius**: flipar `e2_extract` aborta o write exatamente dos documentos que o
parser não soube ler — o run morre em E2 **antes** de o fallback LLM existir.

O gate não podia ver isso. [`test_e2_schema_strict_corpus.py:353`](../../../../tests/test_e2_schema_strict_corpus.py)
enumera `registry._ALL_PARSERS`, e o stub não é parser registrado; pior, o helper
do corpus **rejeita o shape por asserção** (`:363`,
`assert ... not result.get("requires_llm_fallback")`). O instrumento que o runbook
cita como prova de fechamento **exclui o caso que falha em produção, por
construção** — e o `22/22` continua verde.

### A3 — o rollback canônico do runbook é inerte no worker que está rodando

`load_json_config` **cacheia** `pipeline.json` em `_config_cache`
([`pipeline_common.py:146`](../../../../scripts/pipeline_common.py)). Medido, no
mesmo processo:

| passo | modo efetivo |
| --- | --- |
| repo como está | `warn` |
| `mode_overrides={"e2_extract.schema.json":"strict"}` gravado no disco | **`warn`** |
| idem, após limpar o cache (≡ restart do worker) | `strict` |
| **revert da linha no disco** (= §5 do runbook) | **`strict`** ← o rollback não aconteceu |
| idem, após restart | `warn` |

O §5 diz *"revert do PR de config … Deploy de config. RTO ~minutos"* e **não
manda reiniciar o worker**. Seguido à letra, o rollback não surte efeito e o
incidente continua.

O lever do §Escopo 3 desta lane (`MATHOMS_PIPELINE_SCHEMA_MODE=warn`) **funciona**
— e é global: medido, com dois schemas em `mode_overrides`, a env derruba o strict
**dos dois**. Enquanto houver 1 schema promovido os dois levers são equivalentes;
a partir do 2º, o kill-switch da lane despromove silenciosamente tudo. A tensão
que o §RV6-06 enquadrou como disputa de doutrina tem, portanto, um lastro
mecânico medido: **hoje nenhum dos dois levers é quente**, e o que a ADR desta
lane precisa decidir inclui *"reinicia o worker"* escrito no runbook.

### A4 — a baseline de 7 dias não tem conteúdo estatístico, e agora está vazia

O corpus inteiro tem **1 workspace**. Na janela, "n artefatos" é o mesmo documento
repetido por run:

| schema | artef. na janela | documentos distintos |
| --- | ---: | ---: |
| `baseline_patrimonial` | 6 | **1** |
| `e5_analysis` | 5 | **1** |
| `e2_llm_artifact` | 2 | **2** (1 run) |
| `informe_aluguel` | 18 | 3 |
| `e16_irpf_full` | 24 | 4 |
| `informe_base` | 30 | 5 |
| `e15_baseline_extract` | 66 | 11 |
| `e3_reconciled` | 555 | 111 |

Um "GO" daqui afirma *"o conjunto de documentos desta família não drifta"*, não
*"nenhum cliente drifta"* — e o blast radius do flip é todo cliente. Para
`e2_llm_artifact` (n=2, 1 run) o zero-WARN não é evidência de nada.

Pior: a cadência é de ~2 runs/semana e **o último run foi em 2026-08-18 — seis
dias sem nenhum**. O §Aporte da [[A40.l74]] declara o merge dela (2026-08-21) como
*"dia 0"* da baseline de `crlv`/`apolice`; medido, esse dia 0 tem **zero runs
dentro**. O §1.3 pede *"7 dias corridos **com pipeline ativo**"*.

### O que a medição REFUTOU — não re-litigar

Levantei estas hipóteses e elas **caíram**; ficam registradas para a próxima
sessão não gastar a rodada de novo.

- **A telemetria não é inerte.** Emiti um record real pelo `MathomsJsonFormatter`
  de produção: o filtro `jq` do §2 casa, e `logger`, `schema_name`,
  `validation_path`, `workspace_id`, `validator_keyword` e `occurrence_count`
  sobrevivem. Nome de campo em `validation_path` (`…locatario_cpf_cnpj`,
  `…valor_brl`) passa sem mascaramento — a denylist da [[ADR-273]] casa **chave**,
  e é o que a [[ADR-284]] §B decidiu de propósito. `setup_logging()` é chamado no
  worker Celery ([`worker.py:134`](../../../../backend/app/worker.py)).
- **O enforcement strict é real:** `backend/tests/test_db_artifact_store_schema_strict.py`
  → 6 passed (o §1.1 do runbook diz "5 passed" — envelheceu, não é defeito).
- **O golden do E5 não é cego aos blocos que driftam.** Instrumentei
  `validate_dict` durante `tests/test_e5_golden_execution.py`: os 4 payloads
  carregam `gap_qualitativo` n=2, `escopo_cobertura` com as 4 chaves,
  `fluxo_caixa.janelas` n=4, e `endividamento.dividas` n=1 em 2 deles — e passam em
  strict. Logo o drift de `e5_analysis` no corpus é **histórico** (o schema andou
  22 apertos em 180 dias; o último em 08-21, depois do último run), não lacuna de
  produtor.
- **`comprovante_base` 100% também é histórico, não fix inerte:** o produtor
  estampa `tipo_comprovante`
  ([`extract_comprovantes_bens.py:170,218`](../../../../pipeline/stages/extract_comprovantes_bens.py)).
  Os 36 artefatos são pré-#1604 medidos contra o schema pós-#1604.
- **Churn de schema NÃO torna a janela de 7 dias inalcançável.** Contei os commits
  que *apertam* contrato (linha nova em `required` / `additionalProperties:false`)
  em 180 dias: o maior intervalo sem aperto é de 23 a 116 dias por schema. O
  gargalo é atividade de pipeline, não cadência de schema.
- **A [[A40.l66]] estava certa sobre negativo em balde de ativo:** 3 ocorrências no
  corpus inteiro (`$.imoveis_consolidados[].valores_31_12`, `minimum`), todas em
  ≤2026-08-16, nenhuma depois do fix de 08-18.

### Encaminhamento — o que muda no §Escopo desta lane

Não decido pelo `sre-devops`; registro o que a medição obriga a endereçar.

1. **O §Escopo 2 está satisfeito** (o drift está medido acima) e **derruba a
   hipótese de zero**. A ADR desta lane cita esta seção ou remede.
2. **Ordem dura:** `baseline_patrimonial` e `e2_extract` precisam de fix de
   contrato/produtor **antes** de qualquer janela de baseline — hoje a janela deles
   não pode fechar. **A rota é esta lane** (`owner: sre-devops`), não a
   [[A40.l67]]: a l67 está `shipped` e o §Deferimento datado dela (2026-08-18)
   re-homeou o flip dos 2 schemas de baseline **para cá**. Mandar o fix de volta
   para lá fecharia ciclo sobre lane morta — corrigido no closeout de 2026-08-24,
   com marcador datado no §Deferimento da l67.
3. **O §Escopo 3 precisa de emenda:** o kill-switch por env é global e nenhum dos
   dois levers é quente. Ou o runbook ganha "reiniciar o worker" no §5, ou
   `pipeline.json` deixa de ser cacheado para esta chave.
4. **O §1.2 do runbook precisa de correção datada** — o ✅ de `e2_extract` não
   cobre `generate_llm_fallback`, e o gate 22/22 não pode alcançá-lo.
5. **Elegíveis medidos hoje**, se e quando houver runs: `e3_reconciled` (111 docs,
   0/555) e `e15_baseline_extract` (11 docs, 0/66) são os dois únicos com massa
   para uma primeira promoção.

## Execução (2026-08-24) — [[ADR-409]] `Proposto` + o gate vira comando

> `open` → `in_progress`. O §Escopo 2 fechou no §Ataque acima; esta seção registra
> o que a ADR decidiu e o que sobra.

### Entregue

**[[ADR-409]] `Proposto`** — decide a fila e o lever, e **não** executa flip:

- **§A** — unidade per-schema confirmada; o *flip global* do §Escopo 3 desta lane
  fica **revogado** (encaminhamento 2 da §Coordenação RV6-06). Não supersede a
  [[ADR-284]] — conforma.
- **§B** — o go/no-go do runbook §2 passa a ser
  [`dev/measure_schema_drift.py`](../../../../dev/measure_schema_drift.py) sobre
  `pipeline_artifacts`, não a agregação de logs: durável, retroativo, re-medível
  por 1 comando e usável como gate de PR (`--gate` → exit ≠ 0).
- **§C** — dois levers de rollback, **ambos exigindo restart**, declarados por
  situação; hot-reload de `pipeline.json` recusado com razão.
- **§D** — a fila de elegibilidade é a medição: 5 elegíveis, 1 recusado por massa
  (`e2_llm_artifact`, n=2 em 1 run), 2 a reavaliar, 3 bloqueados.
- **§E/§F** — `e2_extract` e `baseline_patrimonial` saem do balde "drift" e viram
  **defeito de contrato nomeado**.

**Predicado de GO com duas guardas que não são óbvias:** janela sem artefato não é
GO (é ausência de medição — a cadência do dogfood é ~2 runs/semana), e artefato
ilegível não é GO. A segunda nasceu de um **falso-verde no próprio instrumento**,
pego pelo teste que eu escrevi para ele: `unreadable` contava como massa e
devolvia `go=True`. O gate do flip quase nasceu com a doença que existe para
detectar.

### Deferimento datado (2026-08-24) · dono `data-engineer`

**Re-derivar `baseline_patrimonial.schema.json` do produtor E1.5c.** Medido: 8 das
13 properties declaradas nunca foram emitidas, 8 chaves emitidas não são
declaradas (3 delas em 100% dos artefatos), sobreposição de **5 de 13**. Não é
drift — é contrato de outro payload.

Escopo: declarar as 13 chaves reais (`resumo`, `_meta`, `itens`,
`informe_pf_saldos_31_12`, `wise_fiscal_flags`, `payload_version`,
`prompt_version`, `validation` + as 5 que já existem), decidir
`additionalProperties`, aposentar as 8 fantasmas, e tirar os 2 `required` da era
disco **junto** com o resto — nunca sozinhos ([[ADR-409]] §F recusa a correção
mínima: torna o número verde sem tornar o contrato real).

Condição de retomada: é pré-requisito de qualquer flip deste schema, e portanto do
que a [[A40.l67]] §Deferimento re-homeou para cá. Não bloqueia os outros 5
elegíveis.

### Segue aberto nesta lane

1. **Kill-switch provado por teste** (§Critério de aceite) — os dois levers do
   §C, incluindo a despromoção global da env.
2. **`e2_extract`: contrato do stub de fallback** (classe [[ADR-407]]) — o `tipo`
   já é discriminador declarado.
3. **§Escopo 4 — flip órfão:** a suíte de `tests/` roda em `warn` hoje; só o passo
   `Pipeline JSON schema strict` do CI roda strict, e sobre **1 arquivo**. O
   `nightly` que rodava o outro está `disabled_manually`. Medir o custo de virar a
   suíte inteira antes de decidir.
4. **Runbook de incidente** (§Critério de aceite) — o que fazer quando um run de
   cliente aborta por schema.
5. **O flip em si** — gated no que a lane não controla: precisa de runs. Último do
   corpus é 2026-08-18.
