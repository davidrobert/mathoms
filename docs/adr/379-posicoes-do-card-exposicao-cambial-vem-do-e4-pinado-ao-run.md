---
id: ADR-379
type: adr
title: "Posições do card Exposição Cambial vêm do artefato E4, pinado ao run do relatório"
status: Proposto
phase: A40
date: "2026-08-12"
relates_to:
  - "[[ADR-224]]"
  - "[[ADR-215]]"
  - "[[ADR-212]]"
  - "[[ADR-378]]"
supersedes: []
superseded_by: []
aliases: ["ADR 379", "fonte das posições do V2", "exposição cambial E4"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/report
---

# ADR-379 — Posições do card Exposição Cambial vêm do artefato E4, pinado ao run

## Contexto

A [[ADR-224]] §5 decidiu que o endpoint read-time do card aplica catálogo de
lastro + overrides do workspace sobre **as posições de
`investimentos_atuais.dados` do artefato E5**. Essa premissa é falsa, e nunca
foi verdadeira.

Medido no artefato E5 do dogfood (`id=15424`, run `ee124571`): as chaves de
`payload["investimentos"]` são `fonte`, `instituicoes_por_membro`,
`n_imoveis_total`, `tabela_classes`, `top_ativos`, `total`, `total_financeiro`,
`total_imoveis_investimento`. **Não existe `dados`.** O E5 publica agregados de
investimento; as posições individuais vivem no artefato E4
(`categorize_transactions`, key `investimentos`).

Consequências que já se materializaram:

- O braço de ativos do endpoint contribuiu **zero desde o merge** do PR #326
  (2026-05-19). Corrigir apenas o nome da chave (`investimentos_atuais` →
  `investimentos`) é **no-op silencioso**: não há `dados` para ler.
- A emenda RV2-08 (2026-07-27) declarou o binding conforme depois de corrigir
  os nomes de campo *dentro* da posição, validando com
  `test_exposicao_cambial_v2_binding.py`, que chama `_aggregate_positions`
  direto e **pula `_extract_e5_inputs`**. O fix era inalcançável em produção, e
  a emenda canonizou em prosa um caminho que não existia.
- O único objeto sobre o qual o usuário declararia lastro — a posição — não
  está no payload que o endpoint lê. A feature de override nasceu sem alvo.

Correlato medido: `_load_latest_e5_artifact` ignora o run do relatório e pega o
E5 mais recente do workspace. Hoje coincide, mas ler dois artefatos torna a
divergência estrutural — numerador e denominador viriam de mundos diferentes.

## Decisão

**Posições vêm do artefato E4 do mesmo run; caixa e denominador continuam vindo
do E5 do mesmo run.** Ambos resolvidos a partir do `pipeline_run_id` do
relatório, nunca de "o artefato mais recente do workspace".

Condição de forma: o application service **não** vira agregador de dois payloads
crus. Um loader único (`load_exposicao_inputs(db, run_id)`) fala com os dois
artefatos e devolve um value object tipado; o service depende do VO, não de
`payload[...]` ([[ADR-089]] / [[ADR-097]] D2).

Pinagem aditiva e não-breaking: `report_id` opcional na query. Sem ele, resolve
o `pipeline_run_id` do relatório mais recente — nunca o artefato mais recente.
Torná-lo obrigatório é lane própria.

**Retratação nominal da emenda RV2-08.** A regra que ela viola, e que passa a
valer: *teste de binding que não atravessa o extrator do payload não prova
binding*. Sem essa frase escrita, a lição some no diff.

## Consequências

- O endpoint passa a depender de dois contratos de stage: rename em
  `categorize_transactions/investimentos` quebra o card. É exatamente o que
  `dev/check_artifact_read_keys.py` protege — sem esse gate, esta decisão troca
  um binding silencioso por dois.
- Ao ligar o braço de ativos, o total do card **muda sem que dado do usuário
  tenha mudado**. Duas decisões de domínio precisam entrar junto, ou o número
  fica errado de outro jeito: cripto não conta como proteção cambial (V1 exclui,
  o resolver do V2 dá `USD` — divergência medida de R$ 4.564,40), e
  `MIXED`/`OTHER` não podem somar 100% no KPI, contra o que a [[ADR-224]] §6 já
  havia decidido.
- Registre no PR o percentual antes/depois com o denominador corrigido. Nenhuma
  mudança pode ser aceita por "o tier melhorou".
- `backend/tests/test_exposicao_cambial_v2_api.py` tem tripwire que **quebra**
  quando a fonte for ligada — de propósito, para forçar quem ligar a asserir o
  novo comportamento em vez de herdar cobertura que media o vazio.

## Alternativas consideradas

- **E5 passa a publicar `investimentos.dados`.** Rejeitada: cria segunda fonte
  de verdade para o mesmo dado e infla o payload de análise.
- **V2 lê o `exposicao_cambial` já materializado e aplica overrides por cima.**
  Rejeitada: herda o V1, que hardcoda `USD` para todo ativo internacional — é o
  defeito que a [[ADR-224]] existe para corrigir.
- **Deletar o V2; override vira write-time no pipeline.** Rejeitada: reintroduz
  o stale que a §5 rejeitou (declarar lastro exigiria re-rodar o pipeline).
