---
id: A40.l58
type: lane
title: "schema_validation warn → strict: o PR5 que a l5 declarou como outra lane"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1668
ship_date: "2026-08-24"
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
'acreditamos que zero')"*. **Não é zero: 1.905 dos 16.158 artefatos mapeados
(11,8%) violam o próprio schema.**

> 🔧 **Correção de 2026-08-24 (closeout): eram 1.905, não 1.902.** A tabela do corpus
> inteiro logo abaixo sempre somou 1.905; a prosa carregava o total da **primeira
> passada**, feita contra a árvore do repo principal (pré-#1604), onde `e5_analysis`
> media 60 em vez de 63. Ou seja: o parágrafo três acima, que avisa *"medição de flip
> precisa declarar qual árvore produziu o número"*, citava um número da árvore errada.
> Re-medido no fecho com `dev/measure_schema_drift.py --all`: **1905/16158**. Os 11
> vereditos per-schema da [[ADR-409]] §D batem linha a linha. Fora de `SCHEMA_BY_STAGE`, 134 artefatos
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

### Deferimento datado (2026-08-24) · dono: `data-engineer`

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

> **Correção 2026-08-31 — a premissa "do produtor E1.5c" está errada, e executar este
> escopo ao pé da letra escolhe o shape errado.** Medido no tratamento dos achados da
> [[A42.l19]]:
>
> 1. **O produtor declarado é o E4 pós-normalização, não o E1.5c.** A `description` do
>    próprio schema diz: *"A normalização em E4 converte v2 → v1 canonical **antes da
>    validação**"*.
> 2. **São dois produtores** desde a [[ADR-427]] D3, e a divergência entre eles é de
>    **exatamente 2 campos** — `pipeline_stage` e `data_processamento`, os mesmos 2
>    `required` fósseis, que têm **zero leitor** de produção. Não é "duas formas do
>    mesmo payload": é uma forma e um enxerto.
> 3. **`additionalProperties` não pode ser decidido antes** de os 2 fósseis caírem nas
>    **duas** pontas. Se `false` for escolhido enquanto o `BaselineNormalizer` ainda
>    enxerta, consertar o E1.5c **quebra o E4**.
> 4. O enxerto do `data_processamento` cai em `date.today()` e é **gravado**: mesmo
>    input em dois dias civis produz `sha256` diferente. É quebra de idempotência em
>    artefato persistido, não só dívida de contrato.
>
> A execução passa a ser a [[A40.l110]], em dois PRs (A atômico → B re-deriva). Este
> deferimento permanece como origem e não se reescreve — a correção é aditiva.

### Estado dos itens (todos roteados — ver §Fecho)

1. ~~**Kill-switch provado por teste**~~ — ✅ 2026-08-24, §Passo 2.
2. **`e2_extract`: contrato do stub de fallback** — vira §Deferimento datado no §Fecho.
3. ~~**Runbook de incidente**~~ — ✅ 2026-08-24, §8 do runbook (§Passo 3).
4. ~~**§Escopo 4 — flip órfão**~~ — ✅ 2026-08-24, §Passo 4.
5. **O flip em si** — **não é entregável desta lane**; é procedimento operacional do
   runbook §3. Ver §Fecho.

### Passo 2 (2026-08-24) — kill-switch provado, e o critério tinha uma metade não testada

O §Critério de aceite pede *"com a env de rollback setada, payload inválido volta a
**logar-e-passar** — teste, não prosa"*. Medido: a metade **passar** já estava coberta
(`test_env_global_vence_override`); a metade **logar**, não. Um rollback que passasse
**calado** era indistinguível do correto — e tiraria do operador o sinal de drift
exatamente quando ele precisa dele para decidir se re-promove.

Quatro testes novos, cada um com a mutação que o mata registrada:

| teste | mutação que o derruba |
| --- | --- |
| `test_rollback_por_env_volta_a_logar_E_passar` | `_emit_drift_records` para de emitir |
| `test_lever_de_emergencia_despromove_TODOS_os_schemas` | precedência invertida (override vence env) |
| `test_revert_no_disco_so_vale_apos_restart` | `load_json_config` deixa de cachear |
| `test_rollback_por_env_faz_o_store_persistir_apesar_do_override` | env deixa de vencer no caminho do store |

O terceiro é **tripwire entre runbook e código**: se alguém implementar hot-reload de
`pipeline.json`, ele fica vermelho e o §5 perde o "restart" **no mesmo PR**, em vez de
o runbook seguir pedindo um passo que virou inútil.

O segundo pinna o blast radius que a [[ADR-409]] §C declara: com **2** schemas
promovidos, a env de emergência despromove **os dois**. Enquanto houver 1, os dois
levers empatam — é do 2º em diante que a escolha do lever passa a importar.

**Resíduo que eu mesmo criei e corrigi:** o §1.1 do runbook ganhou `# 6 passed
(2026-08-24)` no closeout; com estes testes viraria 7. Contador pinado em runbook
apodrece a cada teste novo e treina o operador a ignorar a divergência — trocado por
`# verde`.

### Passo 3 (2026-08-24) — runbook de incidente, e o defeito que ele revelou

§8 novo no [runbook](../../../reference/runbooks/schema_validation_strict_flip.md):
confirmar o abort (30s) → decidir rollback × fix-forward **pela medição** → executar
→ fechar. Escrito sobre campos conferidos no DB e no snapshot OpenAPI, não de
memória — a primeira versão citava `POST /v1/pipeline/runs/{id}/resume`, e a rota real
é `/api/v1/workspaces/{workspace_id}/pipeline/runs/{run_id}/resume`.

**O defeito que escrever o runbook revelou.** O §8.1 precisava dizer ao on-call por
qual `reason_class` filtrar. Medido: o abort do flip gravava **`internal_error`** —
"bug nosso" — e não `output_invalid`.

A causa é estreita e provável: `reason_from_exception` classificava por
`error_type`, um atributo de erro de **provider**. A `ValidationError` do flip vem
de `DBArtifactStore.write`, é **nua**, e caía no ramo genérico. A ironia é que
`_run_stage_with_retry` **já sabe** que é erro de schema — usa
`_is_schema_validation_error(exc)` duas linhas antes, para não gastar backoff — e
descarta essa informação na linha seguinte.

O módulo já carregava a doutrina certa para o caso irmão:
`LLMErrorType.validation → output_invalid`, com o comentário *"é output REJEITADO
pelo schema, não bug nosso"*. O fix aplica a mesma regra ao abort de contrato; não
inventa política.

Consequência se tivéssemos flipado antes: o primeiro incidente real apareceria no
card de `/admin/metrics` como defeito de código, e o on-call filtraria pela classe
errada. Runs anteriores a 2026-08-24 têm o `reason_class` errado gravado — o §8.1
avisa para não confiar nele em triagem retroativa.

### Passo 4 (2026-08-24) — o flip órfão fecha em `tests/`, e o backend fica de fora com razão medida

`tests/conftest.py` passa a fazer
`os.environ.setdefault("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")`. `setdefault` de
propósito: quem quiser reproduzir produção roda com `=warn` e vence a linha.

**A decisão veio da medição, não do escopo escrito.** Rodei a suíte nos dois modos
antes de tocar em nada:

| | resultado |
| --- | --- |
| `tests/` em `warn` (como o CI rodava) | 7391 passed, 38 skipped |
| `tests/` em `strict` | **7391 passed, 38 skipped** |

Custo zero hoje. O ganho é **prospectivo**, e eu o quantifiquei instrumentando
`validate_dict` durante um run inteiro: **23 chamadas por run rodavam em `warn`
vindas do config** — 23 pontos onde um payload em drift passaria calado. Com a chave
virada, viram falha.

> Isto **refuta** a nota que eu carregava de agosto (*"em strict a contagem sobe,
> 6238 → 6272"*). Era verdade em 2026-08-11; os contadores convergiram desde então.
> Contagem lembrada não substitui contagem medida.

**Tripwire:** `tests/test_suite_valida_em_strict.py` — prova a env, o **modo efetivo**
(que é o que o hook de write consulta, não a env em si) e o **efeito** (payload
inválido devolve `False`, não `True`). Removida a linha do conftest, os 3 caem.

**Passo de CI removido:** `Pipeline JSON schema strict (MATHOMS_PIPELINE_SCHEMA_MODE)`
rodava `tests/test_schema_validation.py` em strict — agora é o mesmo arquivo, no mesmo
modo, duas vezes. O passo irmão em `nightly.yml` fica: o workflow está
`disabled_manually`, e mexer nele seria editar código morto.

#### Por que `backend/tests` NÃO entra — medido, não presumido

`backend/tests` **quebra** em strict: **42 falhas** na superfície de schema
(`-k "schema or artifact_store or pipeline_task or failure_reason"`). A classe é
legítima e não é drift:

```python
store.write("E5", "analise", {"v": 1})   # test_db_artifact_store_retention.py:124
```

São payloads **sintéticos deliberados**, de testes sobre mecânica de storage
(retenção, overwrite, escopo por workspace) que não têm relação com o contrato do E5.
Torná-los schema-válidos exigiria construir payload E5 completo em teste de retenção —
ruído, e acoplaria retenção ao contrato do E5.

⇒ A fronteira do flip é **onde produtor real é exercitado**: `tests/` sim (o golden de
execução roda o produtor ponta a ponta), `backend/tests` não. Quem for "completar" o
trabalho virando o backend vai gastar um dia nessas 42 — está medido aqui para não
gastar.

## Fecho (2026-08-24) — `shipped` pelo próprio critério, e o flip nunca foi o entregável

> **Correção de leitura minha, registrada porque quase custou a lane.** Eu vinha
> tratando "nenhum schema flipado" como razão para manter a lane aberta. Reli o
> §Critério de aceite: **nenhum dos quatro itens exige executar o flip.** Os quatro
> pedem estar *pronto* para flipar — ADR mergeada, drift medido e citado, kill-switch
> provado, runbook de incidente. Todos fechados, todos com teste.
>
> E a doutrina já estava escrita: a [[ADR-284]] §Não-decisões rejeitou *"flipar strict
> nesta lane"* pela razão de que **o flip é operacional**, gated por baseline — não
> entregável de lane. Manter a l58 aberta esperando runs seria manter viva uma lane
> cujo trabalho acabou, à espera de um evento de calendário: a mesma patologia de
> status stale que esta lane documenta ter custado 3 dias, na direção oposta.

### O que shipou

| | PR |
| --- | --- |
| Drift medido no corpus real — 11,8% dos artefatos violam o próprio schema | #1650 |
| [[ADR-409]] + `dev/measure_schema_drift.py` + 12 testes | #1656 |
| Kill-switch provado — 4 testes, 4 mutações | #1664 |
| `reason_class` do abort corrigido + §8 runbook de incidente | #1665 |
| §Escopo 4 — `tests/` valida em strict por default | #1667 |

**A alavanca de longo prazo não é o flip; é o gate ter virado comando.** Antes, o
go/no-go dependia de agregar logs JSON que nenhum sink coleta — na prática ninguém
conseguia responder *"posso flipar?"*, e é por isso que a fila ficou parada desde
2026-06-09. Hoje é `dev/measure_schema_drift.py --gate`, com exit code, sobre um
corpus durável e retroativo. Cada flip vira um PR de 1 linha com o número re-medido
no corpo, executável por qualquer agente em qualquer sessão. É isso que faz a fila
andar **sem esta lane existir**.

### O flip em si — procedimento, não lane

Runbook §3.1, gated pelo §1.3. A fila medida está na [[ADR-409]] §D: `e3_reconciled`
(111 documentos) e `e15_baseline_extract` (11) têm massa para a primeira promoção.
**Não abro lane para isso** — seria lane cujo critério é esperar o calendário, e a
§Triagem de fecho desta sprint já recusou lane catch-all. Quando houver runs, o
comando responde e o PR é de 1 linha.

### Deferimento datado (2026-08-24) · dono: `data-engineer` — contrato do stub de fallback do E2

`generate_llm_fallback` (`scripts/extract_bank_documents.py:101`) persiste um stub sem
`banco`/`moeda` sob `extract_statements`/`extract_invoices`; por isso `e2_extract` mede
NO-GO em 6/6 runs. É a **terceira instância da classe da [[ADR-407]]** — stage com N
formas de payload e mapa 1:1 para schema.

Forma do fix: o `tipo` do stub (`fatura_desconhecida` / `extrato_desconhecido`) já **é**
discriminador declarado — despacho por `if/then`, nunca afrouxar o `required` nem usar
`oneOf` (colapsaria o path em `$` e cegaria a telemetria que é o gate).

Condição de retomada: é pré-requisito do flip de `e2_extract`, o schema de maior massa
(136 documentos, 812 artefatos por run). Não bloqueia os outros elegíveis. Atenção:
`tests/test_e2_schema_strict_corpus.py` **não alcança** o stub por construção (enumera
`registry._ALL_PARSERS` e rejeita o shape por asserção) — quem pegar isto precisa de
cobertura nova, não de rodar o corpus existente.

### Deferimento datado (2026-08-24) · dono: `data-engineer` — re-derivar `baseline_patrimonial` do produtor E1.5c

> Este é o **maior risco de produto** dos dois deferimentos desta lane. Escopo, forma
> e condição de retomada estão no §Deferimento datado do §Passo 1 (mesmo dono); esta
> seção existe para que o item não fique visível só dentro do registro de execução.

`baseline_patrimonial`. O contrato do baseline
patrimonial — a fundação do relatório — declara **5 de 13** chaves do payload real, e 8
properties que produtor nenhum jamais emitiu. Enquanto assim, mudança de forma no E1.5c
não é detectada por nada, e o flip desse schema (que a [[A40.l67]] §Deferimento
re-homeou para cá) permanece impossível. Dos dois deferimentos, **é este que decide se
o relatório do cliente pode mudar de forma em silêncio.**
