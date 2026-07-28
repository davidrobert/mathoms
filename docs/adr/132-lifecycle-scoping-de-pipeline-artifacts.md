---
id: ADR-132
type: adr
title: "Lifecycle scoping de `pipeline_artifacts` (workspace vs run)"
status: Decidido
date: "2026-04-25"
relates_to: ["[[ADR-082]]", "[[ADR-241]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 132"]
tags:
  - area/multitenancy
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 204
---

# ADR-132 — Lifecycle scoping de `pipeline_artifacts` (workspace vs run)

**Status:** Decidido • **Data:** 2026-04-25 • **Relaciona**
[ADR-082](#adr-082--pipelineartifact-artefatos-computacionais-no-banco),
[ADR-120](#adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco)

**Contexto:**

`DBArtifactStore.read()`
([backend/app/services/storage/db_artifact_store.py:69-71](../../backend/app/services/storage/db_artifact_store.py:69))
filtra exclusivamente por `pipeline_run_id`. A premissa subjacente é
que todo artefato é output **per-run** — derivado das rodadas de
pipeline e descartável quando uma nova rodada começa.

A premissa quebra para artefatos de **referência** que vivem mais
que uma rodada. Caso concreto observado em 2026-04-25 (workspace
`6b63...`, 7 rodadas no dia):

- Quando o usuário re-executou a pipeline sem reprocessar IRPFs
  (run `83572a7f` às 22:42), o stage E1.5/E1.5c **não** rodou — não
  havia novos PDFs de IRPF a processar.
- O E4
  ([e4_categorizer_adapter.load_baseline](../../pipeline/domain/services/e4_categorizer_adapter.py:149))
  chamou `store.read("E1.5c", "baseline_patrimonial")` →
  devolveu `None` (artefato existe no DB sob
  `pipeline_run_id=d2e03585`, mas o filtro por run atual o esconde).
- `BaselineNormalizer.normalize(None)` retornou baseline vazio →
  `build_patrimonio_artifact(empty)`
  ([e4_serialization.py:57-58](../../pipeline/domain/services/e4_serialization.py:57))
  gravou `{"dados": []}` (13 bytes), **sobrescrevendo** silenciosamente
  o E4 patrimônio do run.
- E5
  ([e5_analyzer_adapter.py:382](../../pipeline/domain/services/e5_analyzer_adapter.py:382))
  leu E4 patrimônio vazio → composição patrimonial zerou Residência,
  Imóveis Investimento, Veículos e Investimentos do cônjuge. Usuário
  viu R$ 440k onde deveriam aparecer R$ 5,0M.

A causa **não** é falha de extração: os 5 E1.5a (PDFs IRPF) e os
3 E1.5c (baseline consolidado) existem corretamente no DB. A IRPF
de Mariana está lá. O bug é que rodadas posteriores **não enxergam**
o trabalho persistente de rodadas anteriores.

Padrão se repete: `family_members.json` (E1) e baseline IRPF
(E1.5/E1.5c) são datasets que mudam com **eventos de domínio**
(atualização anual de IRPF, edição manual de membro), não com cada
`POST /pipeline/run`. Tratar como per-run força reprocessamento
integral em toda rodada — caro (LLM em PDFs grandes) e fonte de bug
quando o reprocessamento é pulado.

Alternativas consideradas:

- **(a) Forçar E1.5 a sempre rodar.** Reprocessa IRPF a cada
  pipeline → custo de LLM e latência inaceitáveis; também não resolve
  `family_members` editado manualmente.
- **(b) Orquestrador copia forward artefatos de referência.** Toda
  nova run copia E1/E1.5/E1.5c do último run para o atual. Funciona
  mas duplica payloads em cada rodada (~70 KB × N rodadas) e exige
  conhecer a lista de stages "de referência" no orquestrador.
- **(c) `read()` com fallback workspace-wide para stages
  declaradamente workspace-scoped.** `DBArtifactStore.read()` tenta
  primeiro o `pipeline_run_id` atual; se ausente **e** o stage está
  em `_WORKSPACE_SCOPED_STAGES`, busca o artefato mais recente por
  `(workspace_id, stage, key)`. Sem migration, sem duplicação. Stages
  run-scoped (E2/E3/E4/E5) inalterados.

**Decisão:** **(c)** — adicionar fallback de leitura *seletivo* em
`DBArtifactStore.read()`. O conjunto de stages workspace-scoped vive
em uma constante única e fica **explícito** no código:

```python
_WORKSPACE_SCOPED_STAGES = frozenset({"E1", "E1.5", "E1.5a", "E1.5c"})

def read(self, stage: str, key: str) -> Optional[dict]:
    row = self._get(stage, key)
    if row is not None:
        return row.content_json
    if stage in _WORKSPACE_SCOPED_STAGES:
        row = (
            self._session.query(PipelineArtifact)
            .filter_by(workspace_id=self._workspace_id, stage=stage, artifact_key=key)
            .order_by(PipelineArtifact.created_at.desc())
            .first()
        )
        return row.content_json if row else None
    return None
```

Stages futuros (F9.2+ com nomes descritivos, ADR-093) que forem por
natureza de referência declaram a flag no momento de inclusão;
stages run-scoped continuam o default seguro (sem fallback).

> **Atualização (2026-05-21):** [[ADR-241]] estende `_WORKSPACE_SCOPED_STAGES`
> para incluir os 6 nomes de E2 (`E2-extratos`/`E2-faturas`/`E2-llm` + descritivos).
> Critério adicional: artefato é **per-documento idempotente** (re-extrair
> o mesmo PDF/CSV produz o mesmo payload). E3/E4/E5 permanecem run-scoped —
> têm invariantes cross-account que exigem recomputação a cada run.

Salvaguarda complementar:
`e4_serialization.build_patrimonio_artifact()` deixa de escrever o
placeholder `{"dados": []}` quando o baseline é vazio — passa a
**omitir** a chave, preservando o artefato existente do run anterior
caso o fallback ainda assim falhe. Defesa em profundidade contra
futuro stage que esqueça do scope.

**Gates de regressão (4 camadas):**

O bug ficou invisível por 7 rodadas no workspace observado porque
nenhum teste cobria o caminho cross-run. Os gates abaixo são
desenhados para falhar **rápido** (segundos, não minutos) e o mais
**próximo** possível do ponto de regressão — quanto mais cedo na
pirâmide, mais barato o sinal.

**T1 — Unit (`backend/tests/services/test_db_artifact_store.py`).**
Cobre a primitiva `read()`. Setup: dois stores no mesmo
`workspace_id` com `pipeline_run_id` distintos (A e B); store A
escreve `("E1.5c", "baseline_patrimonial", {"itens": [...]})` e
`("E2-extratos", "x", {...})`. Asserções:

- Store B `.read("E1.5c", "baseline_patrimonial")` retorna o payload
  de A (fallback workspace ativo).
- Store B `.read("E2-extratos", "x")` retorna `None` (run-scoped, sem
  fallback).
- Quando A e B têm payloads distintos para o mesmo
  `(stage, key)` workspace-scoped, B vê o **mais recente por
  `created_at`**.

Gate falha em <100ms se alguém remover o `_WORKSPACE_SCOPED_STAGES`
ou inverter a ordem do `ORDER BY`.

**T2 — Unit
(`tests/unit/pipeline/test_e4_serialization.py`).**
Cobre a salvaguarda. Dado um `CategorizationResult` com
`baseline=None` ou `baseline.data == {}`,
`serialize_e4_artifacts(result)` **não** inclui a chave
`"patrimonio"` no dict retornado (era `{"dados": []}` no legado).
Garante que um futuro `build_patrimonio_artifact` "esperto" que
voltar a gravar placeholder seja pego antes de chegar ao DB.

**T3 — Unit
(`tests/unit/pipeline/test_patrimonio_calculator.py`).**
Invariante de output do calculator: dado um baseline com
`imoveis_consolidados` não-vazio + `patrimonio_por_ano["2024"]
.total_bens > 0` + `MemberIdentity` válido, o retorno satisfaz
`composicao[].valor` somando ao menos `total_bens × 0.5` (i.e., a
maior parte do IRPF chega à composição). Falha se o calculator
voltar a "engolir" silenciosamente o baseline — o cenário exato do
bug observado.

**T4 — Integração
(`backend/tests/integration/test_pipeline_cross_run_baseline.py`).**
Smoke test cross-run completo, single source para detectar a classe
de bug fim-a-fim. Sequência:

1. Cria workspace; ingere fixtures de IRPF + 1 extrato bancário;
   roda pipeline completa (run A) → assert `E5.patrimonio.bruto`
   reflete soma de IRPF + extrato.
2. Mesmo workspace, ingere **apenas** 1 novo extrato (sem novos
   IRPFs); roda pipeline (run B) → assert
   `bruto_B >= bruto_A × 0.99` (tolerância p/ flutuação de saldo).
3. Inspeciona artefatos: `pipeline_artifacts` do run B contém
   E2/E3/E4/E5 novos mas **não** E1.5c novo. E4 patrimônio do run
   B é > 13 bytes ou ausente (nunca o placeholder).

Roda em <5s com SQLite in-memory + fixtures pequenas (1 PDF IRPF
mockado, 1 OFX). Único teste que pegaria o bug se T1/T2/T3 falharem
juntos por engano de cobertura.

**Onde NÃO testar:** evitar mock de `DBArtifactStore` em testes do
calculator/E5 — ADR-097 D2 já manda usar fakes nomeados
(`InMemoryArtifactStore`). Mock implícito esconderia exatamente este
tipo de regressão. T1 valida o store real; T3/T4 validam o consumer
contra fake/real respectivamente.

**Consequências:**

- ✅ **Fix imediato do bug observado.** Composição patrimonial volta
  a refletir IRPF mesmo em rodadas que não reprocessam baseline.
- ✅ **Sem migration.** Coluna `pipeline_run_id` permanece; só a
  leitura ganha fallback.
- ✅ **Performance neutra para o caminho quente.** Stages run-scoped
  (>95% das leituras) não ganham query extra; só o miss em stage
  workspace-scoped paga uma segunda query.
- ✅ **Lifecycle explícito.** Quem ler `_WORKSPACE_SCOPED_STAGES`
  entende imediatamente quais artefatos sobrevivem entre rodadas.
- ⚠️ **Determinismo enfraquecido para reprodução de runs antigos.**
  Reler um run histórico pode pegar baseline mais novo (postura
  aceita: relatórios sempre refletem o melhor dado disponível;
  histórico imutável vive em snapshots versionados, não em
  re-leituras).
- ⚠️ **Escrita continua run-scoped.** Stage E1.5c que rodar duas
  vezes na mesma run sobrescreve dentro do run; entre runs são
  linhas distintas — `created_at desc` resolve a ambiguidade.
- ❌ **Não substitui ADR futuro de versionamento explícito.** Se
  aparecer caso de uso para "qual baseline IRPF estava ativo no
  relatório X de 3 meses atrás", precisaremos coluna
  `valid_from`/`valid_to` ou tabela separada. Por ora YAGNI.

Relaciona-se a
[ADR-082](#adr-082--pipelineartifact-artefatos-computacionais-no-banco)
(modelo `pipeline_artifacts`),
[ADR-093](#adr-093--rename-completo-de-identificadores-de-stage-opção-a)
(stage rename — futuras keys descritivas declaram scope no momento
de adição),
[ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)
(a constante `_WORKSPACE_SCOPED_STAGES` é constante imutável,
satisfaz exceção (a) do stateless audit),
[ADR-120](#adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco)
(readers DB-first, agora com fallback workspace-wide).
