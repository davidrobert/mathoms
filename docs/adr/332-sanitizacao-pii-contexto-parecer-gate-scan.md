---
id: ADR-332
type: adr
title: "Sanitização de PII no contexto do parecer + gate PII-scan"
status: Decidido
phase: R3.3
date: "2026-07-14"
decided_at: "2026-07-17"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-090]]"
  - "[[ADR-110]]"
  - "[[ADR-199]]"
  - "[[ADR-203]]"
  - "[[ADR-337]]"
  - "[[ADR-338]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
---

> **Reescrita 2026-07-17 (Onda R3.3 · co-design senior-cto + prompt-engineer):** a
> Decisão original mirava `top_ativos[].nome` (endereço/descrição de terceiro),
> vetor já fechado na fonte pela [[ADR-337]]. Este documento reescopa para o vetor
> vivo — o **nome do próprio membro** em valores/chaves — e para os **dois egressos**
> do parecer. Ver [§Contexto](#contexto).

## Contexto

O parecer holístico ([[ADR-203]]) monta o contexto do LLM a partir do E5 por **dois
egressos** que leem o mesmo `e5_data`:

1. **Distiller** (`backend/app/services/parecer_distiller.py`): projeta apenas os
   paths declarados no manifest `config/prompts/parecer_planejador.yaml`.
2. **Tool `get_e5_section`** (`pipeline/llm/tools/planner_drill_down.py`): devolve
   **seções top-level inteiras, sem truncar**, para os ~26 roots do whitelist do
   manifest (`patrimonio`, `fluxo_caixa`, `investimentos`, `cenarios_conjuge`, …).

A [[ADR-337]] sanitizou `top_ativos[].nome` (PII de terceiro — endereço/descrição
cartorial) **na fonte E5**. O que sobra é o **nome próprio do membro da família**
('David'/'Mariana') em valores e chaves de seções whitelistadas:

- `investimentos.top_ativos[*].membro` (nome do membro; projetado pelo distiller,
  manifest `:149`, **e** devolvido inteiro pela tool);
- chaves de `fluxo_caixa...por_fonte_detalhado` (labels de origem podem embutir nome);
- `patrimonio.composicao[].categoria` = `"Investimentos David"`;
- `fluxo_caixa...receita_datasets[].label` = `"CLT David"`.

Os dois últimos **só** chegam pela tool (o distiller não os projeta) — um gate que
olhasse só o distiller seria falso-verde. `cenarios_conjuge` já está role-keyed pós
[[ADR-338]] (constante `_LABEL` + premissas por papel) e não vaza nome.

## Decisão

Sanitizar o objeto `e5_data` **uma vez no boundary** `generate_parecer`
(`backend/app/services/parecer_orchestrator.py`), **antes** de `compute_cache_key` —
um choke point cobre distiller **e** tool por construção. Novo módulo
`backend/app/services/parecer_context_sanitizer.py`:

- **Substitui nome próprio de membro por PAPEL** (Titular / Cônjuge / Dependente[ N]):
  scrub global word-boundary + case-insensitive sobre **toda string E chave-de-dict**
  da cópia. Cobre os 4 vetores conhecidos **e** a cauda de qualquer seção que a tool
  devolva inteira. Ordinal (`Dependente 1/2`) estável por ordem de key quando há 2+
  dependentes. Em ativo em comunhão o rótulo `Casal`/papel é **mais** preciso que o
  nome (que atribuiria a um só, [[ADR-246]]).
- **Redige CPF/CNPJ** por regex de conteúdo — novo `pipeline/observability/pii_patterns.py`.
  `pipeline/observability/redaction.py` é **key-based** ([[ADR-110]]) e não intercepta
  o valor; por isso um módulo de regex de conteúdo separado, boundary-safe (o sanitizer
  backend importa pipeline; nunca o inverso).
- `valor`/número **nunca** é tocado ([[ADR-090]]).

O mapa nome→papel vem do `family_members` (via `ParecerOrchestratorConfig.name_role_pairs`,
`repr=False` — nunca ecoa nome em log/exceção). O stage constrói as tuplas `(nome, papel)`
com `build_name_role_pairs` e injeta no config; a identidade nunca entra no prompt nem
na cache key (`workspace_id` já escopa a chave).

**Bump: manifest `1.8→1.9` (Onda R3.3).** A sanitização muda o input do LLM (não é
neutra) → entra no eval coordenado da onda, não isolada. Como o sanitizer roda antes de
`compute_cache_key`, o `e5_hash` reflete o E5 já sanitizado — entradas de cache antigas
(não sanitizadas) não colidem e o cache re-gera uma vez no deploy.

## Rationale

- PII fora do prompt sempre que possível é regra do repo (CLAUDE.md §Dados sensíveis);
  a análise patrimonial opera sobre **papéis** (titular/cônjuge/dependente), não nomes —
  o nome é ornamental para o LLM, e a superfície do dono (React) mantém o nome real.
- Sanitizar na entrada única (`generate_parecer`) cobre distiller **e** tool de uma vez;
  per-egresso seria frágil (o que vaza pelo distiller depende do `_short(300)`).
- Scrub global por nome (não só nos campos conhecidos) resiste a campo novo adicionado
  a uma seção whitelistada no futuro.

## Alternativas consideradas

- **Sanitizar só no distiller/tool**: dois pontos, drift; a tool devolve seções inteiras
  → deixa a cauda aberta. Rejeitada.
- **Corrigir na fonte E5** (como a [[ADR-337]] fez com `.nome`): `membro`/`categoria`/
  `label` carregam o nome do **próprio** membro, que o React legitimamente exibe à
  família dona do dado — strip na fonte quebraria o view-model. Rejeitada; só o contexto
  LLM precisa abstrair.
- **Genericizar por posição** (dropar membro sem mapa): ordem não é garantidamente
  titular-first → atribuiria renda/patrimônio à pessoa errada (erro semântico pior que o
  vazamento). Rejeitada.
- **Confiar em redação de log**: `redact` é key-based e não intercepta o payload enviado
  ao provider. Rejeitada.

## Consequências

- Nome de membro e CPF/CNPJ não saem para o provider por **nenhum** egresso; gate impede
  regressão. CLAUDE.md §Dados sensíveis honrado.
- Custo: re-geração única de cache no deploy + um passe de reescrita sobre a cópia do
  `e5_data` (limitado). `name_role_pairs` fora da cache key e de logs (`repr=False`).
- Neutro na superfície React (lê cópia própria do DB). Verificação de citação/red-lines
  passa a comparar contra o E5 sanitizado — o único que o LLM viu → consistente.

## Critério de aceite

- **Completude** — nenhum campo do contexto efetivo do LLM (distiller ∪ `get_e5_section`
  sobre a whitelist inteira) emite nome de membro ou CPF/CNPJ.
- **Corretude** — `membro`/`categoria`/`label`/chaves de `por_fonte_detalhado` viram
  papel; `valor` inalterado ([[ADR-090]]); ordinal estável para 2+ dependentes.
- **Consistência** — regex de identificador em `pipeline/observability/pii_patterns.py`
  (conteúdo), distinto do `redaction.py` (key-based); mapa nome→papel invertido do
  contrato role-keyed ([[ADR-338]]).
- **Precisão** — gate PII-scan em `tests/llm_golden/test_pii_scan_parecer_context.py`
  monta o contexto efetivo dos **dois** egressos sobre a whitelist e falha (red→green)
  se nome de membro ou identificador aparecer.
