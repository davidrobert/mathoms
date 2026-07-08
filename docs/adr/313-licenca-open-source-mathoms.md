---
id: ADR-313
type: adr
title: "Licença open-source do Mathoms — BSL 1.1 vs AGPL-3.0 vs Apache-2.0/MIT"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[ADR-183]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/gtm
  - area/legal
---

# ADR-313 — Licença open-source do Mathoms

**Status:** Proposto · **Data:** 2026-07-08 · Gate **G0** de
[[PLAN-public-release]] (owner-gated). Bloqueia W6 ([[A34.l16]] LICENSE +
README) e o flip ([[A34.l22]]).

## Contexto

Tornar `davidrobert/mathoms` público exige uma licença explícita: repo
público **sem** `LICENSE` é *all-rights-reserved* de fato — hostil ao
público, sem permissão de uso, clone ou fork, e sinaliza descuido em vez
de abertura. A escolha é **semi-irreversível** (revogar permissões já
concedidas a quem clonou é impraticável) e de **alto risco competitivo**.

O ativo em jogo não é código genérico: é o **motor fiscal-BR** (cascata
IRPF/PGBL/lucro presumido, ADR-135/236) e o **rules-as-code metodológico**
([[ADR-183]] — metodologia consagrada de planejamento patrimonial
brasileiro, codificada como docstring+enforcer por ADR-143). Esse é o
diferencial que um concorrente não replica em semanas. O contexto
competitivo é concreto: [[PLAN-public-release]] nasce adjacente à resposta
a um player de mercado (plano `COMPETITIVE_PIERRE`/CloudWalk). A licença
define, na prática, **se o moat vira commodity**.

A licença interage com as demais decisões do gate: o escopo público
([[ADR-314]]) já retira do repositório os prompts de produto e o playbook
competitivo. A licença cobre o **restante publicado** — o motor, o
pipeline, o design system, os schemas — que continua sendo IP substantivo
mesmo sem os prompts.

## Decisão

**Adotar Business Source License 1.1 (BSL 1.1), source-available**, com os
parâmetros:

- **Licensor:** o owner (identidade legal confirmada em [[ADR-317]]).
- **Additional Use Grant:** uso não-comercial, desenvolvimento, avaliação,
  educação e **self-host individual** liberados sem restrição. O único uso
  vedado é o comercial concorrente — operar o Mathoms (ou derivado
  substancial) **como serviço a terceiros**.
- **Change License:** **Apache-2.0**.
- **Change Date:** **4 anos** após a data de publicação de cada versão
  (cada release "abre" em Apache-2.0 na sua própria janela de 4 anos).

Rationale: a BSL preserva **credibilidade de engenharia** (código legível,
auditável, clonável — o que serve os objetivos legítimos de transparência
e recrutamento discutidos em [[PLAN-public-release]] §Objeções) e mantém
**GitHub Advanced Security grátis** (GHAS é gratuito para repositórios
públicos, e a Onda 5 depende disso — [[A34.l15]]), enquanto bloqueia
**exatamente o único uso que dói**: um competidor rodar Mathoms-as-a-service
sobre o nosso motor. É o menor recorte que protege o moat sem fechar a porta
que se quer abrir.

## Alternativas consideradas

- **AGPL-3.0 (copyleft de rede).** Protege contra SaaS-wrapping ao exigir
  que quem opera o software em rede libere as modificações. **Rejeitada
  como leading** porque (a) **assusta parceiros** CFP/white-label e
  integradores — copyleft de rede contamina o produto do parceiro; (b)
  **pesa em due diligence** de investidores, que tratam AGPL como risco
  jurídico de contaminação; (c) **não impede** um concorrente de operar um
  SaaS que *respeite* o copyleft (basta ele publicar o próprio fork) — ou
  seja, é fraca justamente no cenário competitivo que motiva a decisão. É a
  alternativa a promover **se** o owner priorizar pureza open-source
  reconhecida (OSI-aprovada) sobre proteção de parceria/investimento.

- **Apache-2.0 / MIT (permissiva).** Maximiza adoção, contribuição externa e
  aceitação por parceiros/investidores; zero fricção. **Rejeitada** porque
  **doa o diferencial [[ADR-183]] de graça** — qualquer concorrente
  incorpora o motor fiscal-BR e o rules-as-code sem contrapartida, no exato
  momento em que estamos respondendo a um concorrente. Racional apenas se a
  tese "ser referência open-source" for validada como alavanca de negócio
  dominante (objeção 2 de [[PLAN-public-release]]), o que hoje **não está**.

- **Sem LICENSE (all-rights-reserved).** Não é opção — é o default
  destrutivo. Repo público sem licença nega qualquer uso legal e sinaliza
  amadorismo. É o estado que esta ADR **existe para evitar**.

## Consequências

- **Bloqueia W6 e o flip.** [[A34.l16]] materializa o `LICENSE` e o README
  a partir desta decisão; [[A34.l22]] não flippa sem `LICENSE` coerente. Até
  o owner decidir, ambas ficam paradas.
- **BSL não é OSI-aprovada.** O README **não pode** afirmar "open source
  (OSI)" — deve dizer "source-available (BSL 1.1)". A narrativa de
  apresentação ([[A34.l16]]) precisa ser honesta quanto a isso; caso
  contrário, gera atrito reputacional com a comunidade OSS.
- **Contribuições externas** exigem CLA/DCO leve (contribuidor concede
  direito sobre o patch para permitir a Change License futura). Detalhe
  operacional fica em `CONTRIBUTING`, fora do escopo desta ADR.
- **Change Date rolante** significa que releases antigos abrem em Apache-2.0
  progressivamente — a proteção é sempre sobre a versão recente, não
  perpétua. Aceito: 4 anos cobre o horizonte competitivo relevante.
- Se o owner escolher **AGPL** ou **Apache/MIT**, o README, o disclaimer e o
  gate de sigilo ([[ADR-319]]) não mudam de forma — só o texto de `LICENSE` e
  a linha de posicionamento. Baixo custo de troca **antes** do flip; alto
  **depois**.

## Decisão do owner

Esta ADR é **owner-gated** e permanece `Proposto` até a marcação abaixo.
Escalar para **`gtm-strategist`** (impacto em posicionamento/moat) +
**revisão jurídica** (validade da Additional Use Grant e do CLA/DCO)
antes de fechar.

- [ ] **Opção A (leading) — BSL 1.1** source-available; Additional Use Grant
  (não-comercial + dev + self-host individual); Change License Apache-2.0;
  Change Date 4 anos. Preserva o moat competitivo.
- [ ] **Opção B — AGPL-3.0.** Copyleft de rede OSI-aprovado. Aceita fricção
  com parceiros/investidores em troca de pureza open-source.
- [ ] **Opção C — Apache-2.0 ou MIT.** Permissiva, máxima adoção. Aceita
  doar o diferencial [[ADR-183]]. (Owner escolhe qual das duas.)

Ao decidir, o owner registra a escolha aqui (linha datada) e flippa o
status para `Decidido (A34.W0)`; [[A34.l16]] então implementa `LICENSE` +
README coerentes com a opção marcada.
