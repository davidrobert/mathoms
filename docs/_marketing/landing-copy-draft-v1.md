---
id: MARKETING-landing-copy-draft-v1
type: marketing-draft
title: "Landing copy draft v1 — pilares ADR-183 (Fase 4.B COMPETITIVE_PIERRE)"
status: draft
date: "2026-05-09"
relates_to:
  - "[[ADR-183]]"
  - "[[PLAN-competitive-pierre]]"
aliases: ["Landing copy v1"]
tags:
  - type/marketing-draft
  - status/draft
  - area/marketing
  - phase/a11
---

> **Estado:** rascunho v1, gerado em PR-C da Fase 4.B do plano
> [[PLAN-competitive-pierre]]. **Não é landing publicada.** A propagação
> para `mathoms.ai` ocorre em PR-D, com decisão de stack/CMS, analytics e
> baseline dos 6 leading indicators de [[ADR-183]] §"Leading indicators".
>
> **Validação obrigatória antes de qualquer commit:**
> `python3 dev/check_sigilo_terms.py docs/_marketing/landing-copy-draft-v1.md` →
> exit 0. O hook cobre este path desde 2026-05-09.
>
> **Vocabulário canônico:** [COPY_GUIDELINES §13.2](../reference/COPY_GUIDELINES.md)
> + [[ADR-183]] §"Decisão" (tabela de substituições). Atribuição direta a
> autor é bloqueada — usar `metodologia consagrada de planejamento
> patrimonial brasileiro`, `regras estruturadas que planejadores CFP
> aplicam`, `alocação contracíclica`, etc.

---

## 0. Como ler este draft

Cada seção entrega: **headline · subheadline · body · CTA · visual brief**.
Para o hero (P1) há duas variantes A/B. As demais seções têm uma versão
única — variantes adicionais entram em iteração v2 se os leading
indicators de [[ADR-183]] vierem fracos.

Visual brief é descrição do mood, não escolha de imagem específica
(escopo de PR-D em colaboração com ilustração/foto).

Faixas de credibilidade aparecem **entre** P1↔P2 e P3↔P4 — atalhos
explicados na §6. Footer de rejeição de ICP fecha a página e mapeia as
quatro anti-personas de [[ADR-183]] §"Anti-personas".

---

## 1. Hero — Pilar P1 (patrimônio do casal, decidido a quatro mãos)

### Variante A — foco em "casal"

**Headline (8 palavras)**

> Patrimônio do casal, decidido a quatro mãos.

**Subheadline (16 palavras)**

> Mathoms consolida contas, investimentos e IRPF dos dois em um plano
> único, revisado mês a mês.

**Body de apoio (35 palavras, opcional sob hero)**

> Cada decisão patrimonial sai do palpite e entra no plano. Você e o
> cônjuge enxergam o mesmo número, a mesma meta de independência
> financeira e o mesmo próximo passo. Sem planilha duplicada, sem
> conversa adiada.

**CTA primário (2 palavras)**

> Pedir convite

**CTA secundário (4 palavras)**

> Ver como funciona

**Visual brief**

> Painel patrimonial em vista desktop com duas colunas paralelas
> (titular e cônjuge) convergindo numa terceira coluna ("família"). Tom
> sóbrio, tipografia densa, paleta neutra do design system. Sem
> ilustração humana — produto fala por si.

### Variante B — foco em "decisão / método"

**Headline (8 palavras)**

> Patrimônio do casal, decisões sem palpite.

**Subheadline (19 palavras)**

> Mathoms aplica regras estruturadas de planejamento patrimonial sobre
> seus extratos, investimentos e IRPF — para você e o cônjuge no mesmo
> plano.

**Body de apoio (32 palavras)**

> Não é app de orçamento. Não é planilha. É um painel que consolida o
> patrimônio do casal e propõe próximos passos com base em método —
> não em humor de mercado.

**CTA primário (2 palavras)**

> Pedir convite

**CTA secundário (4 palavras)**

> Ver como funciona

**Visual brief**

> Mesma vista de painel da variante A, mas com sobreposição sutil de
> diagramas de regra (alíquota efetiva, gap de independência, alocação
> alvo) em primeiro plano. Sinaliza "estrutura visível", não "demo
> interativa".

### Decisão entre A e B

A roda primeiro em launch. B vai a teste se dwell time no hero ficar
abaixo de 40 segundos médios em 30 dias ([[ADR-183]] §"Leading
indicators"), ou se as entrevistas da Fase 4.A indicarem que "casal"
soa exclusivo demais para o ICP.

---

## 2. Faixa de credibilidade entre P1 e P2

**Frase única (24 palavras)**

> Construído sobre regras consagradas de planejamento patrimonial
> brasileiro, validadas com planejadores CFP independentes e cobertas
> por dezenas de decisões de arquitetura documentadas.

**Visual brief**

> Linha-fina em fundo neutro. Sem logos de "as seen on", sem badge
> de prêmio. Discreto.

---

## 3. Seção P2 — Método estruturado, não palpite

**Headline (5 palavras)**

> Método Estruturado, Não Palpite

**Body (78 palavras)**

> Cada cálculo do Mathoms vem de uma regra explicitada — taxa de
> poupança, score financeiro, gap de independência financeira,
> alíquota efetiva, alocação contracíclica de renda fixa. Nada é
> "geral", nada é "intuição do app". Você vê a fórmula, a premissa, o
> intervalo de incerteza. Quando o cenário muda, a conclusão muda —
> não a opinião.
>
> O resultado é um painel que aguenta revisão de planejador
> profissional. Você apresenta o relatório a um CFP ou contador e a
> conversa começa pelo próximo passo, não pelo número.

**CTA inline (3 palavras)**

> Conhecer o método

**Visual brief**

> Detalhe ampliado de um card do relatório com: KPI principal, fórmula
> condensada em linha-fina, intervalo de incerteza explícito,
> referência "ver §X" para a metodologia interna. Mostra densidade,
> não esconde a régua.

---

## 4. Seção P3 — Patrimônio inteiro, fiscal incluso

**Headline (5 palavras)**

> Patrimônio Inteiro, Fiscal Incluso

**Body (84 palavras)**

> A maioria dos painéis financeiros para de funcionar onde o
> patrimônio fica complexo. O Mathoms começa exatamente aí.
>
> Imóvel próprio e de investimento, fundo exclusivo, fundo imobiliário
> com distribuição parcial, conta no exterior, holding patrimonial,
> previdência PGBL e VGBL, ações em book de longa duração — tudo
> entra. A declaração de IRPF é lida em cima do mesmo dado, então
> alíquota efetiva, carnê-leão e PGBL deixam de ser contas separadas.
>
> Patrimônio do casal não cabe num app que cobre só "extrato e
> fatura". O Mathoms cobre o resto.

**CTA inline (4 palavras)**

> Ver cobertura completa

**Visual brief**

> Mosaico de classes de ativo cobertas — renda fixa, renda variável,
> imóveis, FII, REIT, PGBL, conta no exterior, holding —, com
> indicador discreto "incluído na consolidação". Sem stock photo de
> moeda ou cofre. Tipografia carrega o peso.

---

## 5. Faixa de credibilidade entre P3 e P4

**Frase única (21 palavras)**

> Cada decisão patrimonial fica registrada como evento — você consulta
> hoje o porquê de uma escolha tomada há doze meses.

**Visual brief**

> Mesma linha-fina da §2, com micro-timeline horizontal mostrando 4-5
> decisões em sequência. Reforça o pilar P4 antes da seção dele.

---

## 6. Seção P4 — Plano de ação que evolui, não relatório que envelhece

**Headline (8 palavras)**

> Plano de Ação Que Evolui, Não Envelhece

**Body (92 palavras)**

> Relatório financeiro tradicional fica obsoleto no dia em que sai do
> PDF. O Mathoms guarda cada decisão patrimonial como evento — quando
> foi tomada, com base em qual cenário, com qual premissa — e
> reconstrói o plano sempre que a realidade muda.
>
> Você adicionou um aporte fora do programado, vendeu um ativo, mudou
> de meta de independência financeira, recebeu uma herança? O plano
> recalcula, marca a decisão antiga como superada e mostra a próxima
> ação concreta. O histórico fica auditável; a recomendação fica
> atual.
>
> Sem reescrever a planilha. Sem perder o porquê.

**CTA inline (3 palavras)**

> Ver plano vivo

**Visual brief**

> Pequeno fragmento de timeline de plano de ação, com marcador "ação
> superada" cruzando uma decisão antiga e setinha apontando para a
> próxima. Sem confete, sem badge "concluído". Sério como prontuário
> médico.

---

## 7. Footer — quem o Mathoms não atende

**Frase de transparência (parágrafo único, 78 palavras)**

> O Mathoms é construído para casais e famílias com patrimônio em
> formação ou consolidado, que querem decisão estruturada sobre o
> longo prazo. Não é a ferramenta certa se você busca sair do
> vermelho neste mês, se faz negociação intradiária em renda
> variável, se já tem family office humano dedicado, ou se quer
> conversar com agente de IA novelty sobre suas finanças. Para esses
> cenários, há outras opções melhores — e dizemos isso porque
> contratar a ferramenta errada custa caro.

**Visual brief**

> Bloco em fundo neutro, contraste mais baixo que o resto da página.
> Sinaliza honestidade editorial, não rejeição agressiva.

---

## 8. Out of scope (não entra nesta v1)

Itens explicitamente fora do rascunho — nenhum deles deve aparecer
quando esta copy materializa em landing real (PR-D):

1. **Pricing literal.** Tier, valor, free/trial/paywall — escopo da
   Fase 4.C ([[PLAN-competitive-pierre]] §3 Fase 4.C). Esta v1 fala
   "pedir convite", coerente com beta fechado de [PRODUCT.md
   §5](../reference/PRODUCT.md). Quando 4.C decidir, a CTA muda.
2. **Comparativo direto com concorrente.** Escopo da Fase 4.E, gated
   por Fase 2 (MCP) live ([[ADR-183]] §"Dependências de gate"). Não
   citar nome do concorrente, não referenciar "alternativa a X".
3. **Narrativa "advisor conversacional" / chat hero.** Gated por Fase 3
   (chat) beta. Quando o chat for visível, entra como P5 ou refresh do
   P4 — não substitui o pilar P1 hero.
4. **Templates de e-mail transacional.** Surface diferente; quando
   `backend/app/services/email/` for materializado, o draft entra como
   `docs/_marketing/email-templates-v1.md` (mesma régua §13).
5. **SEO long-tail / blog editorial.** Escopo da Fase 4.D; vocabulário
   canônico desta v1 deve ser respeitado quando aquele conteúdo nascer.
6. **Programa de embaixadores e parcerias CFP.** Escopo da Fase 4.F.
7. **Página de demo / sandbox público.** Decisão separada — beta
   fechado vigente; demo entra apenas em GA.

---

## 9. Métricas de aceitação desta v1

Antes do PR-D propagar a copy, validar:

- [ ] `python3 dev/check_sigilo_terms.py docs/_marketing/landing-copy-draft-v1.md`
      → exit 0 (zero hits §13.1).
- [ ] Vocabulário canônico de [[ADR-183]] §"Decisão" respeitado em todas as seções.
- [ ] Tom de voz aderente a [§1 do COPY_GUIDELINES](../reference/COPY_GUIDELINES.md)
      — sério, segunda pessoa "você", sem promessa de retorno, sem
      gamificação, sem inglês cru.
- [ ] Capitalização §3 — Title Case em headlines/CTAs, sentence case em body.
- [ ] Anti-padrões §9 — sem emoji em label, sem exclamação, sem "clique aqui",
      sem caps lock.
- [ ] Coordenação com lane [A11.w5 Frontend + Methodology](../sprint/A11/lanes/A11-w5-frontend-methodology.md)
      — vocabulário não diverge do cleanup user-facing em curso (acordo
      registrado em [[ADR-183]] §"Sequência operacional pós-merge"
      coordenação A11.w5).
- [ ] CEO sign-off em PR-C antes de PR-D.

---

## 10. Histórico

- **2026-05-09 · v1 (este draft):** estrutura inicial dos 4 pilares,
  variantes A/B do hero, faixas de credibilidade, footer de rejeição
  de ICP, out of scope explícito. Ancorado em [[ADR-183]]; gate
  `sigilo-terms` cobre este arquivo.
