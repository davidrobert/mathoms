---
id: ADR-332
type: adr
title: "Sanitização de PII no contexto do parecer + gate PII-scan"
status: Proposto
date: "2026-07-14"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-110]]"
  - "[[ADR-203]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
---

> Cluster **H1** (P1) do plano [[PLAN-dogfood-report-fix]] — achado da revisão
> dogfood 2026-07-13: identificador pessoal alcança o prompt do parecer via
> `investimentos.top_ativos[*].nome`, violando CLAUDE.md §Dados sensíveis.

## Contexto

O parecer holístico ([[ADR-203]]) monta contexto do LLM por dois caminhos que
leem o mesmo E5: o distiller (`parecer_distiller.py`, via path de manifest
`$.investimentos.top_ativos[*]` em `config/prompts/parecer_planejador.yaml:144`)
e as tools de drill-down (`pipeline/llm/tools/planner_drill_down.py`).

O campo `top_ativos[].nome` carrega texto livre da fonte:
`top_ativos_analyzer.py:225-235` (`_imovel_nome`) devolve
`description`/`descricao`/`endereco` do imóvel; `:156-172` (`_build_inv_candidate`)
usa `inv.get("nome")` cru, que pode conter nº de contrato/conta. Na fixture da
revisão, 5 de 15 ativos são imóveis com `nome` = endereço/descrição livre; 4
casam regex de identificador numérico. O parecer cita esses detalhes → PII de
papéis titular/cônjuge/dependente chega ao provider LLM.

Vetores reais pela tool jsonpath: `$.investimentos.top_ativos[*]` (dict inteiro)
e `$.investimentos.top_ativos[N].nome` (string). **Não** `[*].nome` — wildcard
intermediário é rejeitado em `planner_drill_down.py:219-238` (`_walk_segments`
levanta `intermediate wildcard not supported`).

## Decisão

Introduzir `backend/app/services/parecer_context_sanitizer.py`, invocado no topo
de `generate_parecer` (`parecer_orchestrator.py:296`), **antes** de
`compute_cache_key` (`:112`). Produz cópia rasa+profunda de `e5_data` na qual
cada `investimentos.top_ativos[i].nome` é reconstruído de forma determinística:

- discriminador `tipo_origem == "imovel"` (`top_ativos_analyzer.py:202`) → rótulo
  = `classe`;
- caso contrário (investimento) → rótulo = `classe` + `" (" + instituicao + ")"`
  **somente se** `instituicao` não-vazia; senão `classe`.

`valor` nunca é tocado (permanece `Decimal`/número — [[ADR-090]]). Como
defesa-em-profundidade, strings de contexto remanescentes passam por regex de
identificador (CPF/CNPJ/matrícula/nº contrato/apólice) cuja **fonte única** é
`pipeline/observability/redaction.py` ([[ADR-110]], já compartilhado
backend↔pipeline via `backend/app/core/logging.py:31`) — colocar em módulo
boundary-safe evita que `pipeline/**` importe `backend` ou que produção importe
`tests/`. O sanitizer mora no backend (import backend→pipeline permitido) e é
coeso com `parecer_distiller`/`parecer_red_lines`/`parecer_evidencia`.

Gate PII-scan: criar `tests/llm_golden/` com teste que roda o sanitizer sobre a
fixture e monta o contexto efetivo do LLM (distiller + saída das tools sobre
`top_ativos`); falha o CI se qualquer regex de identificador casar. Tests que
passam por `generate_parecer` (`test_parecer_orchestrator.py`) são auditados para
esperar o rótulo reconstruído.

**Bump: none.** O texto do prompt não muda (só o conteúdo interpolado). Como o
sanitizer roda antes de `compute_cache_key`, o `e5_hash` (`:123`) reflete o E5
já sanitizado → entradas de cache antigas (não sanitizadas) não colidem e o cache
re-gera uma vez no deploy.

## Rationale

- PII fora do prompt sempre que possível é regra do repo; redação de logs
  (`redact`) é key-based e cobre logs, não o payload enviado ao provider.
- Sanitizar na entrada única (`generate_parecer`) cobre distiller e tools de uma
  vez — os dois lêem o mesmo `e5_data` dali para frente.
- Reconstruir o rótulo preserva valor semântico (classe + instituição) que o
  parecer usa, sem vazar o identificador.

## Alternativas consideradas

- **Sanitizar dentro da tool** (`planner_drill_down`) apenas: o distiller renderiza
  `top_ativos[*].nome` por outro caminho → dois pontos, risco de drift. Rejeitada.
- **Redigir a string final do prompt** por regex: perde classe/instituição e não
  cobre `top_ativos[*]` (dict devolvido pela tool independe do texto). Rejeitada.
- **Corrigir a montante** (`top_ativos_analyzer` nunca gravar identificador em
  `nome`): muda o view-model do relatório React + shape do artefato E5 (breaking,
  exige bump de schema + rebase de golden); a superfície React legitimamente
  mostra o rótulo cru à família dona do dado. Rejeitada — só o contexto LLM
  precisa abstrair.
- **Nada / confiar em redação de log**: log redaction não intercepta o prompt
  enviado ao LLM. Rejeitada.

## Consequências

- PII (endereço/contrato/apólice/matrícula/CPF/CNPJ) não sai para o provider;
  CLAUDE.md §Dados sensíveis honrado; gate impede regressão.
- Custo: re-geração única de cache no deploy (~US$12/run, plano [[PLAN-dogfood-report-fix]]
  §orçamento) + um passe de cópia sobre `e5_data` (limitado — `top_ativos` ≤15).
- Neutro: superfície React inalterada (lê cópia própria do DB). Stage
  (`parecer_planejador.py:186`) e relatório lêem cópias DB independentes — não
  compartilham objeto, então cópia-de-retorno do sanitizer é **higiene de teste**,
  não correção de corrupção in-place.

## Critério de aceite

- **Completude** — nenhum campo do contexto LLM (distiller + saída das tools sobre
  `$.investimentos.top_ativos[*]` e `[N].nome`) emite CPF/CNPJ/matrícula/nº
  contrato/apólice/endereço; cobre os 2 vetores reais do jsonpath.
- **Corretude** — rótulo imóvel = `classe`; rótulo investimento = `classe (instituicao)`
  quando `instituicao` não-vazia, senão `classe`; discriminador = `tipo_origem`
  (enum), não `tipo`; `valor` inalterado ([[ADR-090]]).
- **Consistência** — regex de identificador têm fonte única em
  `pipeline/observability/redaction.py`; tests que passam por `generate_parecer`
  (`test_parecer_orchestrator.py`) esperam o rótulo reconstruído.
- **Precisão** — gate PII-scan em `tests/llm_golden/` (criado) roda o sanitizer
  sobre fixture PII-zero e sobre fixture com identificador sintético; falha o CI
  se identificador entrar no contexto. Sem bump: prompt inalterado, `e5_hash`
  re-invalida cache antigo.
