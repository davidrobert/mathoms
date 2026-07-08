---
id: ADR-317
type: adr
title: "Identidade de autoria no mailmap público"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[ADR-315]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/seguranca
---

# ADR-317 — Identidade de autoria no mailmap público

**Status:** Proposto · **Data:** 2026-07-08 · Owner-gated (dado pessoal do
próprio owner). Consumida pela lane de rewrite [[A34.l18]] do
[[PLAN-public-release]]; o `mailmap` é aplicado dentro da mesma passagem
`git-filter-repo` de [[ADR-315]].

## Contexto

O rewrite de histórico (Onda 3 do [[PLAN-public-release]]) reescreve blobs,
mensagens de commit e **autoria**. A autoria é dado pessoal do owner e
precisa de decisão explícita antes do flip público — não é saneamento
mecânico de PII de terceiros.

Dois vetores concretos no histórico de 1.862 commits:

1. **E-mail pessoal do owner em 813 commits** — Gmail pessoal como
   `author`/`committer`. Público, torna trivial correlacionar a persona
   real do owner com todo o timeline de desenvolvimento (inclui os ~100
   commits com patrimônio nominal que a Onda 1 redige nas *mensagens*, mas
   cuja *autoria* permanece se não reescrita).
2. **Co-authors de agente** — commits carregam trailer
   `Co-Authored-By: Claude <noreply@anthropic.com>` (e variantes por modelo).
   Preservar ou remover é decisão de percepção, não de segurança.

O `git-filter-repo` aplica `--mailmap <arquivo>` na mesma passagem que
reescreve paths e mensagens — o custo marginal de reescrever autoria é
próximo de zero **se** a decisão de identidade estiver travada antes. Depois
do flip, corrigir autoria exige novo rewrite irreversível (novo bypass de
Ruleset, nova janela de FREEZE). Por isso a decisão é gate de W0, não de W3.

`git-filter-repo` também é irreversível na prática (reescreve todos os
SHAs). O `.mailmap` deve ser **exaustivo** — um endereço não mapeado passa
intacto para o público.

## Decisão

**Leading:** reescrever a autoria do owner para uma identidade de projeto
estável e não-pessoal — nome público de exibição + e-mail `noreply` sob o
domínio do projeto (ex.: `owner@users.noreply.github.com` ou
`noreply@mathoms.ai`), **preservando** os co-authors de agente.

Racional:

- Remove a correlação Gmail-pessoal↔timeline sem apagar autoria (histórico
  permanece atribuível a uma identidade única e consistente).
- Preservar `Co-Authored-By: Claude <noreply@anthropic.com>` é honesto sobre
  o fluxo de desenvolvimento assistido por agente (que a apresentação
  pública — [[ADR-318]], README — já assume) e não expõe dado pessoal: o
  endereço já é um `noreply` de terceiro.
- Um `.mailmap` exaustivo com todas as variantes de `name <email>`
  encontradas no histórico, validado por `git log --format='%aN <%aE>' |
  sort -u` **pós-rewrite** = conjunto esperado (sem Gmail pessoal, sem
  endereço não mapeado).

Enforcement: o smoke de clone anônimo de G8 ([[PLAN-public-release]]
§Verificação) inclui grep dos padrões do e-mail pessoal em `git log` de
todas as refs — hit = falha do gate.

## Alternativas consideradas

- **Preservar o Gmail pessoal** (não reescrever autoria): zero esforço, mas
  publica correlação persona-real↔1.862 commits, incluindo commits cuja
  mensagem foi redigida por conter patrimônio. Incoerente com o objetivo de
  KR1 (PII zero em HEAD e histórico).
- **Reescrever para identidade de organização** (ex.: `Mathoms
  <dev@mathoms.ai>`) em vez de identidade do owner: apaga totalmente a
  autoria individual. Válido se o owner quiser projetar autoria
  organizacional; custo é perder o crédito individual de ~4 anos de trabalho
  solo — decisão de percepção que só o owner faz.
- **Remover os co-authors de agente**: "esconde" o uso de IA. Sem ganho de
  segurança (o trailer é `noreply` de terceiro) e cria dissonância com a
  narrativa pública. Só faz sentido se o owner preferir omitir o fluxo
  assistido — decisão do owner.
- **Um e-mail `noreply` diferente para cada persona/modelo de agente**:
  granularidade sem valor público; infla o `.mailmap` sem reduzir risco.

## Consequências

- Todos os SHAs mudam (efeito do rewrite de [[ADR-315]]) — as hash-refs em
  ~10 ADRs atualizadas por [[A34.l20]] cobrem isso; autoria não adiciona
  novo trabalho de refs.
- `.mailmap` vira artefato versionado do repo público (documenta o mapa de
  identidade de forma reproduzível). Não contém e-mail pessoal no lado
  direito (destino); o lado esquerdo (origem) contém o e-mail pessoal
  histórico e por isso o **`.mailmap` não deve ser commitado com o e-mail
  de origem em claro** — usar apenas o formato `Nome Público <noreply>` sem
  a linha de origem quando a origem for PII, ou aplicar o mapa via arquivo
  efêmero fora do repo durante o filter-repo.
- Reescrever autoria não é reversível pós-flip sem novo rewrite — decisão
  travada em G0 é definitiva para o público.
- GitHub atribui commits reescritos à conta cujo `noreply` for usado; se o
  owner usar o próprio `users.noreply.github.com`, o grafo de contribuição
  da conta é preservado sem expor o Gmail.

## Decisão do owner

Owner-gated. Status permanece `Proposto` até marcação abaixo. Escolha **uma**
opção de identidade e **uma** de co-authors.

**Identidade pública do owner (813 commits):**

- [ ] **A (leading)** — `noreply` do owner (`owner@users.noreply.github.com`
      ou `noreply@mathoms.ai`), nome de exibição público estável. Preserva
      crédito individual sem expor Gmail pessoal.
- [ ] **B** — identidade de organização (`Mathoms <dev@mathoms.ai>`). Autoria
      organizacional; perde crédito individual.
- [ ] **C** — manter Gmail pessoal público (aceite explícito do risco de
      correlação — anexar justificativa).

**Tratamento de co-authors de agente:**

- [ ] **A (leading)** — preservar `Co-Authored-By: Claude
      <noreply@anthropic.com>` e variantes (transparência do fluxo assistido).
- [ ] **B** — remover todos os trailers de co-author de agente do histórico.

**Confirmação operacional:** o `.mailmap` final (exaustivo, validado por
`git log --format='%aN <%aE>' | sort -u` pós-rewrite = conjunto esperado) é
anexo do runbook [[TRACK-public-release-history-rewrite]] e revisado pelo
owner antes do force-push.
