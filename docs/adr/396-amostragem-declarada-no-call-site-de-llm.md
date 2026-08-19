---
id: ADR-396
type: adr
title: "Amostragem de LLM é declarada no call-site, não herdada do config"
status: Proposto
phase: §r7 PE-2
date: "2026-08-19"
relates_to:
  - "[[ADR-233]]"
  - "[[ADR-270]]"
  - "[[ADR-307]]"
  - "[[ADR-394]]"
tags:
  - type/adr
  - area/llm
---

## Contexto

O §r7 (`PE-2`) mediu que o orquestrador do parecer roda com `temperature` **sem
`seed`**, enquanto os stages de extração já têm gate exigindo os dois
([[ADR-394]] cauda). A superfície de maior variância do produto era a única sem
o gate.

Ao trocar o eixo do gate de *path + nome do receptor* para *assinatura da
chamada*, o inventário real apareceu: **5 call-sites** violavam, não 1. Dois
deles (`comprovantes_bens_llm.py:57,109`) são **extração** e escapavam do gate
antigo só porque o arquivo não casava o glob `extract_*.py`. Um terceiro
(`extract_llm_drift.py:152`) é o **harness de eval de drift de extração** — ele
media a 0.1 herdado um prompt que produção roda a 0.0, isto é, media um regime
que produção não usa.

`ParecerOrchestratorConfig.temperature = 0.1` nunca foi decisão: é o default de
`LLMConfig` (`service_config.py:44`) copiado. Não há ADR, comentário ou eval que
tenha comparado 0.1 com 0.0 para esta superfície, o único construtor do config
não passava o campo, e a superfície irmã de síntese aberta
(`section_summary_orchestrator`) já rodava 0.0.

## Decisão

**D1 — A amostragem (`temperature`, `seed`) é declarada no call-site de
`LLMService.call`, nunca herdada do `LLMConfig`.** Valor em objeto de config é
injetável por workspace e invisível a gate sintático; provar que o config que
chega na chamada carrega o default certo é dataflow, não sintaxe. O campo
`ParecerOrchestratorConfig.temperature` é **removido** — dois escritores do mesmo
número, um deles invisível ao gate, é como o valor volta a 0.1 sem ninguém notar.

**D2 — A `temperature` do parecer passa de 0.1 para 0.0**, declarada como
`PARECER_TEMPERATURE`. O parecer congela uma amostra por 7 dias
(`cache_ttl_s`), então a variedade que `temp>0` compraria é entregue **uma vez** e
repetida a semana toda: o usuário não recebe variedade, nós recebemos
irreprodutibilidade. É o mesmo raciocínio que [[ADR-307]] enforça uma camada
abaixo (`ValueError` se `use_cache=True` com `temperature > 0`) e do qual o
parecer escapava apenas por cachear numa camada acima. Some-se o reask de
validação do Instructor, cujo próprio call-site registra "único retry útil a
temp baixa" ([[ADR-270]]).

**D3 — As constantes de amostragem do parecer moram em
`pipeline/llm/prompts/parecer_planejador.py`**, ao lado de `PROMPT_VERSION`.
Esse diretório é varrido por `check_prompt_version_bumped.py`, então re-afinar a
amostragem sem bumpar a versão fica **impossível por construção**. O bump é
load-bearing, não burocracia: `prompt_version` compõe a cache key (TTL 7d) e
janela o `parecer_drift_monitor` — sem ele a mudança não chega em produção por
uma semana e os dois regimes de amostragem se misturam na mesma janela de drift.
Trade-off aceito: um knob numérico num módulo de "prompts" é levemente fora do
rótulo; a alternativa (módulo neutro) é invisível aos dois gates. A topologia de
gate decide.

**D4 — O gate casa por assinatura, não por path nem por nome de variável.**
`dev/check_llm_sampling.py` (sucede `check_extraction_sampling.py`) casa
`ast.Call` cujo `func.attr == "call"` e cujos kwargs contenham **`system_prompt`
e `output_schema`** — par único de `LLMService.call` e obrigatório em toda
chamada real. Consequência desejada: call-site novo em arquivo novo, com
receptor de qualquer nome, é pego por construção. Gate ancorado em path é
derrotado por `git mv`; ancorado em nome de variável, por `client = ...`.
**Sem allowlist** — allowlist que nasce populada ensina que a allowlist é a saída.

## Claim honesto

Isto **reduz variância; não produz determinismo.** `seed` é descartado por
`litellm.drop_params` em `anthropic/*` (`get_supported_openai_params` não o lista
para `claude-sonnet-4-6`), e `seed=None` satisfaz o kwarg sem valer nada. O gate
fecha **sintaxe**: garante que um call-site novo não nasça herdando 0.1 sem
decisão. Passamos o kwarg porque custa zero e o ganho aparece no dia em que o
provider mudar. Nenhuma frase deste PR deve dizer "parecer determinístico".

Consequência direta para o §r7: **o `seed` não é o que estabiliza o
`metricas[].target`.** Estabilizar o alvo exige tirá-lo do contrato do LLM — é
decisão à parte, não corolário desta.

## Consequências

- O braço diagnóstico `temp=0` de `test_parecer_evidencia_llm_eval.py` foi
  removido: com produção em 0.0 ele virou subconjunto estrito do braço de gate
  (mesmo regime, menos runs) e custava 10 gerações reais para não contrastar com
  nada. A pergunta que ele respondia ("design ou variância?") passa a ser
  respondida pelo próprio gate.
- `PROMPT_VERSION` do parecer: `2.2.0 → 2.3.0` (minor — mesmo prompt, envelope de
  amostragem outro; formato semver estrito por [[ADR-233]]).
- O `files:` do hook precisa ser largo (`pipeline/**`, `backend/app/**`): o hook é
  `pass_filenames: false` e só **roda** quando um path casado muda. Com o padrão
  antigo, call-site novo em `backend/app/services/` não disparava o hook e o gate
  ficaria verde por não ter rodado.

## Follow-up (dono: data-engineer)

`llm_call_log` **não persiste** `temperature` nem `seed`
(`backend/app/models/llm_call_log.py`). Enquanto não persistir, o regime de
amostragem de uma chamada só é inferível via `prompt_version` — que é
exatamente por que o bump de D3 é load-bearing. Coluna nova é mudança de schema
e não entra neste PR.
