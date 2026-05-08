---
id: ADR-183
type: adr
title: "Pilares narrativos da landing — reposicionamento Mathoms 2026 (Fase 4.B COMPETITIVE_PIERRE)"
status: Proposto
phase: A11
date: "2026-05-08"
relates_to:
  - "[[ADR-077]]"
  - "[[ADR-108]]"
  - "[[ADR-135]]"
  - "[[ADR-136]]"
  - "[[ADR-143]]"
  - "[[ADR-163]]"
  - "[[ADR-166]]"
  - "[[ADR-167]]"
  - "[[ADR-178]]"
supersedes: []
superseded_by: []
aliases: ["ADR 183", "Landing positioning pillars"]
tags:
  - area/marketing
  - area/methodology
  - area/report
  - phase/a11
  - status/proposto
  - type/adr
size_lines: 253
---

> ADR longa (>150 linhas) por design: consolida posicionamento + ICP scorecard
> + anti-personas + mapa de gates + leading indicators + handoffs num único
> artefato. Split em sub-ADRs criaria peças órfãs sem contexto cruzado.

## Contexto

A Fase 4.B do plano [[PLAN-competitive-pierre]] reescreve a landing
pública e a copy do produto Mathoms para reposicionar a marca de "ferramenta
de relatórios" para **advisor digital metodológico para o segmento HENRY
brasileiro**, sinalizando seriedade que o tier R$ 99-149/mês justifica e
diferenciando estruturalmente de Pierre Finance (budgeting copilot consumer
mass-market).

A primeira invocação do `gtm-strategist` (sessão 2026-05-08) produziu brief
exploratório com 4 pilares narrativos. O CEO marcou como decisão definitiva.
Esta ADR registra a decisão, fecha lacunas de execução (ICP scorecard,
anti-personas, dependências de gate, validação de capability, leading
indicators) e mapeia handoffs para `product-designer` e `product-manager`.

A regra inegociável de [§13 do COPY_GUIDELINES](../reference/COPY_GUIDELINES.md)
bloqueia atribuição pública de fontes metodológicas. Os 4 pilares foram
desenhados para comunicar **profundidade metodológica sem nomear autores** —
uso da substituição canônica §13.2.

ADRs vigentes que esta decisão respeita:

- [[ADR-108]] (URLs canônicas — landing fica em `mathoms.ai`).
- [[ADR-143]] (methodology = code — fundamento factual do P2).
- [[ADR-136]] (Decision aggregate — fundamento factual do P4).
- [[ADR-178]] (Risk aggregate — entra como sub-prova do P3).
- [[ADR-077]] (cutover goals.json finalizado — habilita narrativa "plano evolutivo").

Esta ADR **não decide** copy literal (escopo `product-designer`), sprint
placement (escopo `product-manager`), nem stack de landing/CMS (escopo
`build-vs-buy` se vier).

## Decisão

Adotar **4 pilares narrativos** como espinha dorsal da reescrita de copy da
Fase 4.B, em ordem de hierarquia:

| # | Pilar | Função narrativa | Capability ancorada |
|---|---|---|---|
| **P1** | Patrimônio do casal, decidido a quatro mãos | Hero — diferenciação competitiva direta vs. concorrente single-user | `pipeline/domain/services/cenarios_conjuge_analyzer.py` + [[ADR-166]] + [[ADR-167]] + `frontend/src/components/report/sections/S7IndependenciaSection.tsx` |
| **P2** | Método estruturado, não palpite | Posicionamento de categoria — sai de "app de finanças", entra em "advisor digital metodológico" | [[ADR-143]] (methodology = code) + `pipeline/domain/services/equilibrio_cerbasi_analyzer.py` + `pipeline/domain/services/financial_score_calculator.py` + `config/scoring.json` |
| **P3** | Patrimônio inteiro, fiscal incluso | Profundidade horizontal — cobre o que orçamento/agregador raso não cobre | `pipeline/domain/services/irpf_analyzer.py` + `config/schemas/e16_irpf_full.schema.json` + `pipeline/domain/services/passive_income_calculator.py` + [[ADR-135]] + [[ADR-178]] |
| **P4** | Plano de ação que evolui, não relatório que envelhece | Profundidade vertical — depth-of-service que justifica preço premium e ancora retenção | [[ADR-136]] + [[ADR-163]] + `pipeline/domain/services/suggestion_generator.py` + `frontend/src/components/report/sections/PlanoDeAcao/` |

**Vocabulário público canônico** (substituição §13.2 — todas as menções
públicas devem usar esta lista; nomear autor = bloqueia publicação):

| Conceito interno | Conceito público |
|---|---|
| Metodologia consagrada de planejamento patrimonial brasileiro | Idem — usar verbatim |
| Independência financeira | Independência financeira / Liberdade financeira |
| Patrimônio gerador de renda | Idem |
| Equilíbrio entre presente e futuro | Idem / Balanço presente-futuro |
| Patrimônio do casal / Decisão a quatro mãos | Idem |
| Alocação contracíclica | Idem / Estratégia adaptativa à curva de juros |

### ICP Score Card (HENRY brasileiro com cônjuge — 8 atributos × 3 níveis)

Pontuação por nível: alto = 2, médio = 1, baixo = 0. **Threshold de "ICP fit": ≥
12/16** (≥ 6 dos 8 em nível alto, sem mais de 2 em nível baixo).

| Atributo | Alto (2) | Médio (1) | Baixo (0) |
|---|---|---|---|
| Renda anual familiar | ≥ R$ 500k | R$ 250-500k | < R$ 250k |
| Patrimônio investível | R$ 500k-3M | R$ 200-500k | < R$ 200k ou > R$ 5M (ultra) |
| Estágio de vida | Casado/união, 30-50, 1+ filho | Casado, sem filho, 28-35 | Solteiro ou aposentado |
| Comportamento de planejamento | Já tentou planilha/CFP, frustrado | Pensa em planejar, ainda não agiu | Não vê valor em planejar |
| Sofisticação financeira | PJ + CLT, multi-conta, alguma alocação | CLT alta-renda, conta única | Só conta corrente, débito/crédito |
| Willingness-to-pay | Já pagou ≥ R$ 100/mês por SaaS profissional | Paga R$ 30-100/mês em ferramentas | Só usa apps gratuitos |
| Canal de descoberta | SEO long-tail, indicação CFP/contador, podcast nicho | Indicação de amigo HENRY, blog generalista | Anúncio rede social, influencer mass-market |
| Retenção esperada (1 ano) | Adiciona cônjuge no workspace, 6+ logins/mês | Login mensal para abrir relatório | Login único pós-trial |

Cliente que pontua ≥ 12 é **ICP fit**. Marketing qualifica leads contra este
card; produto mede "% trials no ICP fit" como leading indicator de saúde do
funil. Validação inicial: rodar contra os 5 dogfood/beta atuais e contra
10-15 entrevistas qualitativas da Fase 4.A.

### Anti-personas (não atender, não desenhar para)

| Anti-persona | Descrição (1 frase) | Por que o produto/canal/preço não serve |
|---|---|---|
| **Iniciante endividado** | Renda < R$ 8k/mês, dívida > 30% renda, busca "sair do vermelho". | Job-to-be-done é orçamento básico. Pricing R$ 99+/mês é proibitivo; profundidade metodológica é fricção. |
| **Day-trader / especulador ativo** | Foca em alpha de curto prazo, B3 + cripto, multi-corretora intraday. | Mathoms é planejamento patrimonial (longo prazo). Não há tela de cotação real-time, sem book, sem alerta. |
| **Ultra-high-net-worth (UHNW)** | Patrimônio > R$ 10M, holding patrimonial estruturada, family office humano. | Valor entregue por planejador humano dedicado supera SaaS. Mathoms é entrada **antes** de UHNW. |
| **Curioso AI-nativo / hobbyista** | Quer "Alexa das finanças" / MCP toy / explorar agente AI sobre dados próprios. | Job é novelty AI, não planejamento. Atrai sub-economic + ruído. |

Anti-personas guiam **o que NÃO entra na landing**: nada de "saia das dívidas
em 30 dias", nada de gráfico de candle/cotação intraday, nada de "concierge
family office", nada de "agente AI conversacional sobre suas finanças" como
hero.

### Dependências de gate (mapa do que pode ir ao ar quando)

A Fase 4.B publicação está gated por "Fase 2 (MCP) ou Fase 3 (chat) em beta
visível" (constraint do plano §3 Fase 4). Mas nem todo pilar tem o mesmo
gate:

| Pilar | Capability ancorada já live? | Pode ir ao ar antes de Fase 2/3 beta? |
|---|---|---|
| **P1 — Casal** | Sim (cenarios_conjuge_analyzer + S7Independencia) | **Sim** — capability existe há meses; landing pode comunicar hoje. |
| **P2 — Método estruturado** | Sim ([[ADR-143]] live; analyzers + scoring.json em produção) | **Sim** — fundamento metodológico não depende de Fase 2/3. |
| **P3 — Patrimônio inteiro + fiscal** | Sim (irpf_analyzer + e16 schema + Risk [[ADR-178]] em A11) | **Sim, com cuidado:** Risk aggregate é A11 W3; conferir se já está user-facing antes de comunicar "riscos cobertos". |
| **P4 — Plano evolutivo** | Sim ([[ADR-136]] live; PlanoDeAcao section em produção) | **Sim** — Decision event-sourced é diferenciação real e visível. |

**Conclusão:** todos os 4 pilares têm capability live hoje. O **gate Fase 2/3
beta** se aplica especificamente a:

- Comparativo público com concorrente (4.E) — espera Fase 2 (MCP) live.
- Narrativa "advisor conversacional" — espera Fase 3 (chat) beta. Por isso
  **chat NÃO entra como pilar** desta ADR; quando entrar, é P5 ou refresh do P4.

**Recomendação de soft launch:** publicar P1+P2+P3+P4 em landing reescrita
imediatamente após este ADR mergear, **sem** comparativo com concorrente e
**sem** narrativa conversacional. Comparativo entra em refresh quando MCP
live; narrativa conversacional entra quando chat beta.

### Leading indicators (mensuráveis em 30-60 dias)

Lagging indicators do plano §6 (CAC payback < 6m, NPS HENRY > 60, ≥ 30%
signups de canal pago) ficam mantidos como gates de longo prazo. Esta ADR
adiciona **leading indicators de narrativa** mensuráveis em 30-60 dias:

| Indicador | Sinal positivo | Janela | Onde medir |
|---|---|---|---|
| Dwell time no hero P1 (casal) | ≥ 40s média | 30 dias pós-launch | analytics da landing (sem PII) |
| Scroll depth para P2/P3/P4 | ≥ 60% dos visitantes que passam de P1 | 30 dias | mesma analytics |
| Taxa trial signup → primeiro report | ≥ 50% em 7 dias | 60 dias | backend |
| Repetição do vocabulário em entrevista | ≥ 3 das 10 entrevistas 4.A usam "patrimônio do casal", "plano que evolui", "patrimônio inteiro" sem prompt | 60 dias (paralelo a 4.A) | transcrições 4.A |
| Email open rate trial dia 1 (assunto cita P1 ou P4) | ≥ 35% | 30 dias | provedor email |
| % trials que pontuam ≥ 12 no ICP scorecard | ≥ 50% | 60 dias | qualificação manual + backend |

**Threshold de "narrativa pegou":** ≥ 4 dos 6 indicadores em sinal positivo.
Abaixo disso, refresh narrativo com `product-designer` antes de continuar
investindo em SEO/conteúdo (4.D, 4.E).

## Consequências

### Positivas

- **Diferenciação durável codificada na landing.** P1 e P4 ancoram em
  [[ADR-136]] + cenarios_conjuge — capabilities que concorrente leva ≥ 6
  meses para replicar.
- **Sigilo metodológico preservado.** P2 comunica profundidade sem nomear
  autor; substituições §13.2 codificadas no vocabulário canônico; auditoria
  automática (`dev/check_sigilo_terms.py`) cobre execução em frontend/.
- **Gate de qualificação operacional.** ICP scorecard transforma "HENRY
  brasileiro" de slogan em qualificador mensurável.
- **Anti-personas explícitas.** Reduz risco de lead-magnet acidental que
  polui métricas e desfaz percepção premium.
- **Soft launch viável.** Como todos pilares têm capability live, Fase 4.B
  pode publicar imediatamente sem violar constraint §3.

### Negativas / trade-offs

- **Pilar P3 depende de [[ADR-178]] estar user-facing.** Se A11 W3 atrasar,
  P3 perde 50% da prova. Mitigação: launch P3 com IRPF + balanço completos
  como prova suficiente; "riscos cobertos" entra em refresh quando Risk live
  na UI.
- **Sem hero conversacional.** Concorrente comunica AI-conversational como
  hero; nossa ausência pode soar "atrasado" para visitante AI-nativo.
  Aceito: nosso ICP não compra novelty AI, compra seriedade metodológica.
- **Vocabulário canônico exige disciplina contínua.** §13.2 é regra
  absoluta; toda copy nova passa pelo grep automático. Mitigação: hook
  `sigilo-terms` cobre frontend/; expandir para `docs/_marketing/` quando
  esse path existir.
- **ICP scorecard é hipótese inicial.** Pesos e thresholds não validados
  contra cohort histórico (não temos volume); refinar após Fase 4.A entregar
  10-15 entrevistas. Rotular como hipótese até segunda iteração.
- **4 pilares = 4 mensagens.** Risco de diluição se hierarquia não for
  respeitada na execução visual. P1 é hero **não-negociável**; P2-P4 são
  reforços.

### Risco assimétrico

- **Categoria** ("advisor digital metodológico" vs "app de finanças") é
  decisão semi-irreversível em 12-18 meses. Esta ADR fixa a categoria.
- **Pricing tier base R$ 99-149** (decidido em 4.C separadamente, fora desta
  ADR) é coerente com o posicionamento aqui. Free tier seria incoerente com
  P2/P4 — sinaliza "ferramenta", não "advisor".

## Sequência operacional pós-merge

| Ordem | Owner | Entregável | Gate de saída |
|---|---|---|---|
| **PR-A (esta ADR)** | orquestrador `senior-cto` | `docs/adr/183-landing-positioning-pillars-2026.md` Proposto | merge em `main`, status `Proposto` |
| **PR-B** | `product-manager` | Track skeleton `docs/sprint/<X>/tracks/gtm-landing-copy-rewrite.md` referenciando esta ADR | track materializado em `status: ready`; sprint placement decidido em SPRINT_CURRENT |
| **PR-C** | `product-designer` | Rascunho de copy literal contra os 4 pilares + ICP card + anti-personas — paralelo a PR-B | copy revisada com `gtm-strategist` (auditoria sigilo §13.3) + CEO sign-off |
| **PR-D** | CEO + `product-designer` | Publicação da landing reescrita; hook `sigilo-terms` expandido para `docs/_marketing/**` se materializado | landing live; analytics configurado; baseline de leading indicators capturado |
| **PR-E** | orquestrador | Flip ADR-183 de `Proposto` para `Decidido (Sprint XX.Y)` quando 4.B publica | data de flip + Sprint registrada no frontmatter |

**Coordenação com lane em voo `A11.w5 Frontend + Methodology`:** o owner
dessa lane está reescrevendo terminologia user-facing em paralelo. PR-C
**precisa coordenar com A11.w5** para não introduzir vocabulário paralelo
divergente. Recomendação: reviewer A11.w5 valida vocabulário canônico de
§"Decisão" desta ADR antes de PR-C ir para review.

**Refresh trigger:** revisitar pilares se concorrente lançar (a) feature de
cônjuge/sucessão, (b) free tier brasileiro estruturado em wealth advisory,
ou (c) parceria com banco gestor de patrimônio premium. Refresh = nova ADR
ou supersedure desta.

## Critério de aceite (gate `Proposto` → `Decidido`)

- [ ] PR-A mergeado em `main` (esta ADR como `Proposto`).
- [ ] PR-B mergeado: track `gtm-landing-copy-rewrite.md` materializado pelo
      `product-manager` com sprint placement.
- [ ] PR-C mergeado: copy literal rascunhada por `product-designer` passa
      em `dev/check_sigilo_terms.py` (zero hits) E vocabulário canônico
      desta ADR é respeitado.
- [ ] PR-D mergeado: landing live em `mathoms.ai`; analytics capturando os
      6 leading indicators desta ADR.
- [ ] 30-60 dias pós-launch: ≥ 4 dos 6 leading indicators em sinal
      positivo. Se < 4: refresh com `product-designer` antes de promover a
      `Decidido`.
- [ ] Coordenação com A11.w5 documentada: vocabulário público desta ADR
      alinhado com cleanup de terminologia em curso.

Promoção a `Decidido (Sprint XX.Y)` ocorre no PR-E quando os critérios
acima estão verdes E a landing está live ≥ 30 dias com sinais positivos.
