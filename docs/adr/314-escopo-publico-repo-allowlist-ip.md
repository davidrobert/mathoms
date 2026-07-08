---
id: ADR-314
type: adr
title: "Escopo público do repo — allowlist/blocklist de paths e IP excluído"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[ADR-183]]", "[[ADR-319]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/gtm
  - area/seguranca
---

# ADR-314 — Escopo público do repo: allowlist/blocklist de paths e IP excluído

**Status:** Proposto · **Data:** 2026-07-08 · Owner-gated (parte do gate **G0**
de [[PLAN-public-release]]). Define o **superset público** que os gates
anti-regressão de [[ADR-319]] passam a proteger.

## Contexto

A auditoria de 2026-07-08 mediu **PII e segredos** — CPF, endereço, valores
nominais, chaves. Ela declarou `config/prompts/*.yaml` "limpos" porque não
carregam dados de cliente. Mas essa medida **não cobre IP e negócio**, que são
uma dimensão de exposição ortogonal à PII:

1. **Prompts de produto** — `config/prompts/parecer_planejador.yaml` e
   `config/prompts/section_summaries.yaml` são o **moat** do Mathoms (a
   qualidade do parecer é o diferenciável) **e** citam **Perini/Cerbasi/AUVP
   nominalmente**. Isso é duas exposições numa: (a) o motor competitivo copiável
   em texto claro; (b) atribuição nominal de marca metodológica de terceiros sem
   licença — bloqueante de sigilo, mecanizável por [[ADR-319]]/KR3.
2. **`COMPETITIVE_PIERRE`** (`docs/plan/COMPETITIVE_PIERRE/`) — playbook
   competitivo: onde atacar, fraqueza do concorrente, janela de mercado,
   scorecard de ICP, discovery com valores plausivelmente reais
   (`assets/3e-discovery-2026-05-23.md`). Publicá-lo entrega a estratégia ao
   próprio alvo.
3. **Pricing concreto** — tiers, MRR-alvo e faixas de receita em
   [[PLAN-report-premium]] e no rationale de [[ADR-183]]. Número exato é
   negociação; faixa é posicionamento.
4. **Diagnósticos de dogfood com valores** — outputs de eval e revisão que
   carregam patrimônio/renda reais em prosa. Sobrepõe-se à camada-1 de PII, mas
   a lente aqui é "quanto do funcionamento interno do produto fica legível".

A tese do plano é explícita: o MLP é **"público SEGURO"**, e a objeção GTM
registrada questiona se expor o motor competitivo inteiro serve a algum objetivo
de negócio validado ([[PLAN-public-release]] §Objeções). Esta ADR resolve, por
categoria, o **trade-off transparência-vs-vantagem**: cada decisão é binária
(público / redigido-genericizado / movido-para-privado).

Co-design 2026-07-08 (`gtm-strategist` + `senior-cto`, síntese de fechamento).

## Decisão

Recomendação leading por categoria (o owner ratifica a matriz na §Decisão do
owner — status permanece `Proposto` até lá):

1. **Prompts de produto → split privado (opção B).** `parecer_planejador.yaml` e
   `section_summaries.yaml` saem do superset público. Mecanismo: submódulo git
   privado **ou** `.gitignore` + injeção em build-time, com um stub sintético
   versionado público que documenta o contrato (schema de I/O do prompt) sem o
   conteúdo do prompt. Preserva o moat e resolve a atribuição nominal de uma vez
   — o texto que cita Perini/Cerbasi/AUVP simplesmente não fica público.
2. **`COMPETITIVE_PIERRE` → mover para privado.** O plano competitivo inteiro
   sai do repo público (mesmo mecanismo de exclusão da categoria 1). Se algum
   fragmento tiver valor pedagógico neutro, ele é **redigido** (concorrente
   genérico, sem janela/fraqueza/ICP scorecard) antes de qualquer publicação —
   decisão de fragmento fica com [[A34.l12]].
3. **Pricing → genericizar para faixas.** Tiers e MRR concretos viram faixas
   qualitativas no material público ("plano individual / plano família / tier
   premium"); número exato só em canal de vendas. In-body em docs, sem tocar
   `id`/wikilink.
4. **Diagnósticos de dogfood → cobertos pela camada-1** ([[A34.l9]]/[[A34.l10]]):
   qualquer valor real é anonimizado com placeholders sintéticos; nenhum
   diagnóstico com número real fica público.

O **vocabulário canônico substituto** para tudo que hoje cita metodologia
nominal é o de [[ADR-183]]: *"metodologia consagrada de planejamento patrimonial
brasileiro"*. Isso vale para README, narrativa pública e qualquer doc que
sobreviva ao superset.

Esta matriz **define o superset público**. Tudo fora dela é blocklist, e
[[ADR-319]] instala o gate que barra reintrodução (o grep de KR3 sobre
`(perini|cerbasi|auvp|raul sena|viver de renda)` = vazio no superset).

## Alternativas consideradas

- **A — publicar tudo (transparência máxima).** Ganho: percepção de
  open-source "de verdade", zero mecanismo de split. Custo: entrega moat +
  playbook competitivo + atribuição nominal de terceiros. Rejeitada — o dano
  competitivo e o risco de marca superam o ganho de percepção, que a objeção GTM
  do plano já apontou como alavanca não-validada para o ICP.
- **C — redigir os prompts in-body (manter público, cortar só as citações).**
  Removeria só a atribuição nominal, deixando o moat público. Rejeitada: o
  conteúdo do prompt **é** o diferenciável independentemente das citações;
  redigir citação sem tirar o prompt resolve sigilo mas não o moat, e ainda
  deixa um artefato de manutenção frágil (regride a cada edição do prompt).
- **D — whitepaper público separado.** Publicar um documento de transparência
  metodológica em vez do motor. Não é alternativa à decisão de escopo — é
  **complementar** e recomendada como caminho para o objetivo de "confiança do
  cliente" citado na objeção GTM. Fora do escopo desta ADR (não bloqueia o flip).

## Consequências

- **Split introduz um mecanismo de build/deploy** (submódulo ou injeção): o
  prompt privado precisa estar presente no ambiente de execução do backend, e o
  stub sintético público precisa manter paridade de contrato para os testes que
  não dependem do texto real. Custo de manutenção nomeado e aceito.
- **`COMPETITIVE_PIERRE` sai do grafo público** — wikilinks internos para ele a
  partir de docs públicos quebrariam; a exclusão exige varrer refs
  ([[A34.l12]] + `check_doc_links`).
- **KR3 fica mecanizável**: com prompts fora e docs genericizadas, o grep de
  atribuição nominal no superset é o critério objetivo de "limpo".
- **Trade-off assumido**: o repo público mostra a arquitetura, o pipeline, os
  gates e a disciplina de engenharia — não o motor competitivo. É "referência de
  como construímos", não "receita de o que vendemos".

## Decisão do owner

Esta ADR é owner-gated. Marque uma opção por categoria; o status flippa para
`Decidido (Sprint A34)` no merge do PR que registra a decisão.

**Categoria 1 — prompts de produto (`parecer_planejador.yaml`, `section_summaries.yaml`):**
- [ ] **B (leading)** — split privado (submódulo/gitignore + injeção build-time; stub sintético público)
- [ ] C — redigir só as citações nominais, manter prompt público
- [ ] A — publicar integral

**Categoria 2 — `COMPETITIVE_PIERRE`:**
- [ ] **Mover para privado (leading)**
- [ ] Redigir fragmentos neutros e publicar o resto
- [ ] Publicar integral

**Categoria 3 — pricing concreto (tiers/MRR em REPORT_PREMIUM/ADR-183):**
- [ ] **Genericizar para faixas (leading)**
- [ ] Manter concreto público

**Categoria 4 — diagnósticos de dogfood com valores:**
- [ ] **Anonimizar via camada-1 (leading)** — coberto por [[A34.l9]]/[[A34.l10]]
- [ ] Excluir do superset por completo

**Complemento (não bloqueia):**
- [ ] Autorizar whitepaper público de transparência metodológica (opção D) como caminho GTM separado
