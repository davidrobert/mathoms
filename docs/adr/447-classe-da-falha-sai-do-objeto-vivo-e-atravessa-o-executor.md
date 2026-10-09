---
id: ADR-447
type: adr
title: "A classe da falha sai do objeto vivo e atravessa o executor no detail do stage"
status: Decidido
date: "2026-10-09"
relates_to:
  - "[[ADR-357]]"
  - "[[ADR-443]]"
  - "[[ADR-366]]"
  - "[[ADR-441]]"
  - "[[ADR-284]]"
  - "[[ADR-150]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 447"
  - "failure_class"
  - "classe da falha atravessa o executor"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
---

# ADR-447 — A classe da falha sai do objeto vivo e atravessa o executor no `detail`

> Co-design 2026-10-08 com `senior-cto` (dono do desenho no §Deferimento da [[ADR-443]]) e
> `data-engineer` (contrato do `detail` entre os executores). Os dois divergiram na forma da
> chave e da ADR; pelo protocolo anti-loop, decidiu o `senior-cto`. Nasce `Decidido` porque o
> enforcement é teste no mesmo PR (precedente da [[ADR-443]]).

## Contexto

O `reason_class` da [[ADR-357]] §2 só via o que cruzava o executor. Medido em 2026-10-09:

- **Dois achatamentos.** `orchestrator._run_stage` converte toda exceção do runner em
  `StageResult(success=False)` nos dois executores (in-process e o CLI do shell Go), e o backend
  só classificava objeto vivo em `_run_stage_once`, que nunca o recebe. O parecer achata antes:
  `_call_llm_safe` troca a exceção pelo rótulo `"LLM call failed: <tipo>"`, que vira `reason` em
  prosa. As duas rotas caíam em `reason_from_stage_detail` → `unknown`.
- **Consequência.** `budget_exhausted`, `timeout`, `provider_error` e o `output_invalid` do flip
  strict ([[A40.l58]]) nunca chegaram ao `output_summary`. O card de `/admin/metrics` conta só
  stages `degraded`; dos três degradáveis, o único com falha de LLM é o parecer. Consertar só o
  executor viraria o `xfail` da [[ADR-443]] em verde sem mover o card.
- **Onde a exceção chega viva** (levantamento dos runners). Propagam até o `_run_stage`:
  `extract_members`, `extract_baseline`, `extract_irpf_full` (LLM e budget) e todo writer cujo
  `store.write` fica fora de `try` — o abort strict de E1, E1.5, E1.5c, E1.6, informes anuais,
  comprovantes, E3, E4, E5 e `generate_narratives`. Capturam por documento: `extract_with_llm`
  e `extract_informe_aluguel` (LLM, budget e abort), `extract_informes_anuais` e
  `extract_comprovantes_bens` (LLM e budget). O E2 determinístico engole o abort e termina
  `completed`.
- **Restrições.** `pipeline/**` não importa `backend`. `StageResult` tem 5 campos, 5
  construtores campo-a-campo e a struct Go: campo novo seria descartado em silêncio
  ([[ADR-357]] §2, correção de 2026-08-07). `detail` é dict livre que todos repassam.

## Decisão

1. **O classificador mora em `pipeline/stage_failure_reason.py`.** Enum, os dois mapas,
   `reason_from_exception` e o decoder `reason_from_stage_detail` migram inteiros; o módulo do
   backend vira reexport. A classe sai do objeto, e o objeto só existe onde foi capturado —
   dividir o vocabulário entre os dois lados recriaria dois classificadores que derivam.
2. **Quem captura grava `detail["failure_class"]`**: chave plana, um membro do enum, nunca texto
   da exceção (invariante da [[ADR-441]]). Escritores:
   - o `except Exception` de `_run_stage` — `reason_from_exception(exc)`;
   - o `SystemExit ≠ 0` de script legado — `unknown` explícito: não há tipo, e a prosa do stderr
     é vetada; a presença da chave separa "não classificável" de produtor anterior ao contrato;
   - o `_call_llm_safe` do parecer — `reason_from_exception(exc)`, ou `llm_unavailable` quando
     não há LLM.

   O dono é o vocabulário e o construtor `failure_class_detail`, não o call-site: ele só aceita
   membro capturável.
3. **O decoder confia só no que uma captura pode afirmar.** Precedência fixa: `retention_reason`
   (`enforcement`) > `failure_class` > `reason` declarado > `unknown`. `failure_class` presente e
   fora da imagem de `reason_from_exception` vira `unknown`: `enforcement` e `missing_input` têm
   derivação própria e não entram por esta chave.
4. **No parecer, retenção e falha técnica são XOR.** `_needs_review` exige exatamente um entre
   `reason_code` ([[ADR-366]] §D3) e `failure_class`, os dois sem default; os dois juntos ou
   nenhum levantam `ValueError`. A colisão fica irrepresentável no produtor.
5. **Sem caminhar `__cause__`/`__context__`.** Bug levantado dentro de `except LLMError` seria
   lido como falha do provider. Quem embrulha exceção tipada classifica no próprio `except`, como
   o parecer.
6. `reason_class` segue **descritivo, nunca dispositivo** ([[ADR-357]] §2): nenhuma ramificação
   de status lê `failure_class`.

## Alternativas rejeitadas

- **Descritor de fatos aninhado** — `{reason_class, exception_type, llm_error_type, caught_at}`,
  posição do `data-engineer`. Preservaria `rate_limit` × overload e o qualname para backfill, mas
  nenhum leitor existe, o nome curto da classe já viaja no `log_tail`, e campo sem leitor é
  contrato a manter. Se ops pedir a distinção, divide-se o enum.
- **Fatos crus no `detail`, backend classifica.** Mapear nome de classe no backend é match de
  string sobre tipo, e as flags (`budget`, `schema_rejected`) já exigiriam `isinstance` no
  pipeline — meia classificação de cada lado.
- **Campo novo em `StageResult`.** Descartado em silêncio pelos construtores campo-a-campo e
  pela struct Go.
- **Emenda da [[ADR-357]].** Decisão nova, com alternativas e deferimento próprios; como terceira
  emenda de uma ADR de mais de 450 linhas, sumiria do índice.

## Consequências

- Sem migration e sem mudança de OpenAPI: `output_summary` é JSON livre e
  `StageExecuteResponse.detail` já é objeto livre. Row antiga sem a chave segue `unknown`. Skew de
  deploy: shell antigo não grava a chave (`unknown`, o estado anterior); backend antigo a persiste
  e a ignora.
- O card de `/admin/metrics` passa a ver budget, timeout e provider do parecer e o abort do
  `generate_narratives`; o §8.1 do runbook do flip strict volta a filtrar por `reason_class`.
- Perdem-se o qualname da exceção na triagem e a distinção `rate_limit` × overload (as duas são
  `provider_error`). `pipeline/` passa a hospedar uma taxonomia lida por ops.

## §Deferimento — classe por documento nos stages que capturam por documento (2026-10-09)

`extract_with_llm`, `extract_informe_aluguel`, `extract_informes_anuais` e
`extract_comprovantes_bens` capturam LLM e budget por documento (os dois primeiros também o abort
strict) e devolvem `success: False` com `errors: [{"file", "error"}]`: o stage segue `unknown`.
Fechar pede regra de agregação. Ponto de partida aceito: cada entrada de `errors` ganha a classe
da própria captura, e a do stage é a **unânime** entre elas — discordância ou entrada sem classe
dão `unknown`; maioria ou "a primeira" dependeriam de volume e de ordem.

- **Dono:** `data-engineer`.
- **Retomar antes de:** flipar para `strict` um schema escrito por esses stages
  (`e2_llm_artifact`, `informe_aluguel`), ou a primeira triagem de run `failed` nesses stages por
  `reason_class`.
- **Fora daqui:** o E2 determinístico que engole o abort strict é defeito de contagem, não de
  classe — bloqueador do flip de `e2_extract` no §1.1 do runbook.

## Critério de aceite

- `backend/tests/test_run_stage_once.py`: o ex-`xfail` passa, agora sobre `extract_members`, que
  propaga em produção; a composição de produção grava `budget_exhausted`, `timeout` e
  `output_invalid` (este pelo `DBArtifactStore.write` real em strict); e a mesma classe sai do
  stdout do CLI pelo client HTTP do shell Go.
- `backend/tests/test_reason_class_do_parecer_chega_ao_card.py` — gate de não-inércia: runner do
  parecer, `generate_parecer` e `LLMService` reais pelo loop, lidos pela query do card. Reprova com
  só o `_run_stage` consertado.
- `tests/unit/pipeline/test_stage_failure_reason.py`, `test_run_stage_failure_class.py` e
  `tests/test_parecer_failure_class.py`: imagem do classificador igual ao conjunto capturável,
  precedência, recusa de valor fora da imagem, cadeia não caminhada, chave com tail vazio,
  `SystemExit`, XOR.
- Mutações provadas, as 12 reprovam: chave só com tail não-vazio; classificador levantando no
  `except`; caminhar `__context__`; stage descartando o campo; `_run_stage` removendo a chave do
  retorno; precedência invertida; decoder aceitando qualquer membro; decoder ignorando a captura;
  builder gravando texto; `SystemExit` sem `unknown`; XOR removido; `_call_llm_safe` sem
  classificar.
