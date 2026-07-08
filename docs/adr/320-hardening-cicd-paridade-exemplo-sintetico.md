---
id: ADR-320
type: adr
title: "Hardening de CI/CD e contrato de paridade estrutural do EXEMPLO sintético"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[A34.l13]]", "[[A34.l14]]", "[[A34.l15]]", "[[A34.l8]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/ci
  - area/seguranca
---

# ADR-320 — Hardening de CI/CD e contrato de paridade estrutural do EXEMPLO sintético

**Status:** Proposto · **Data:** 2026-07-08 · Uma das 8 ADRs do gate G0 de
[[PLAN-public-release]]. Diferente das ADRs 313–318 (owner-gated), esta
agrupa **duas decisões técnicas não-owner-gated** — a política é fechada
pela síntese do co-design, não pelo owner.

## Contexto

Tornar `davidrobert/mathoms` público in-place cria duas superfícies novas
que não existem em repo privado, e ambas são resolvíveis **no HEAD**, sem
tocar histórico git:

**(A) Superfície de execução de CI/CD.** Em repo público, workflows do
GitHub Actions rodam sob permissões que, no privado, eram inócuas por
ausência de tráfego externo. Hoje só o job `changes` declara `permissions`
explícito; os demais herdam o token com escopo amplo. Quatro actions de
terceiros são referenciadas por **tag flutuante** (`@v...`), o que permite
que o mantenedor da action reescreva a tag e injete código na nossa
pipeline sem PR nosso — precedente concreto em **CVE-2025-30066**
(`tj-actions/changed-files`, tag reescrita retroativamente). A mais
perigosa é `chinthakagodawita/autoupdate-action`, que roda com
`contents:write` e push em `main`: comprometê-la é escrita direta no
repositório. As outras três (`amannn/action-semantic-pull-request`,
`actions/labeler`, `CodelyTV/pr-size-labeler`) têm blast-radius menor mas
o mesmo vetor. O CI hoje também injeta uma **Fernet key dummy inline**
(TODO em `ci.yml:82`) — aceitável em privado, ruído de secret-scanner em
público. GHAS (secret scanning + push protection + code scanning) é
**gratuito em repositório público** e hoje está off.

**(B) Contrato do `EXEMPLO_DE_RELATORIO.html`.** O arquivo contém um
relatório real e será regenerado com dados sintéticos PII-zero em
[[A34.l8]]. A auditoria confirmou que **nenhum golden ou teste carrega o
`.html` em runtime** — a única referência viva é uma docstring em
`tests/unit/pipeline/test_financial_score_calculator.py:402` que cita linhas
físicas do HTML (`L1809-1811`) como nota humana de paridade, sem assert que
leia o arquivo. O risco não é quebra de teste;
é **perda silenciosa da referência de review humano** do renderer premium
([[PLAN-report-premium]]): o EXEMPLO é o artefato que designers/PM usam
para julgar paridade visual do relatório. Se a regeneração "sintetizar"
dados removendo seções/cards/charts, a referência degrada sem nenhum gate
avisar.

Co-design 2026-07-08 (`sre-devops` + `senior-cto`, síntese de fechamento).
A decisão (B) exige coordenação com o dono do [[PLAN-report-premium]] —
registrada como não-decisão de escopo abaixo.

## Decisão

**(A) Hardening de superfície de repo público:**

1. **`permissions: read-all` como default de workflow**, elevação
   **por-job** ao mínimo necessário (padrão least-privilege do GitHub
   hardening guide). O job de autoupdate declara `contents: write`
   explícito e isolado; nenhum outro job herda escrita.
2. **SHA-pin das 4 actions de terceiros** por commit SHA imutável
   (`uses: owner/action@<sha40>  # v1.2.3`), nunca por tag flutuante.
   Dependabot passa a propor bumps de SHA (revisáveis via PR), preservando
   atualização sem reabrir o vetor de tag reescrita.
3. **Habilitar GHAS**: secret scanning + push protection (barra segredo
   *antes* do push) + code scanning com upload SARIF. Gratuito em público.
4. **Require approval para first-time contributors** — workflows de fork
   de contribuidor novo só rodam após aprovação manual, fechando o vetor
   de PR malicioso que exfiltra secrets via CI.
5. **Fernet dummy do CI migrado para secret** (key inline em `ci.yml:87`,
   TODO em `:82`) — remove a key inline; o valor dummy passa a
   `secrets.MATHOMS_FERNET_KEY`, silenciando o scanner e removendo a TODO.
6. **CODEOWNERS cobrindo `.github/workflows/**`** — mudança em pipeline
   exige review do owner, defesa em profundidade contra PR que afrouxa o
   hardening.

**(B) Contrato de paridade estrutural do EXEMPLO sintético:**

7. Invariante de regeneração ([[A34.l8]]): **zero seção, card ou chart
   removido; só os dados são trocados por sintéticos PII-zero.** A
   regeneração reusa a fixture dogfood existente
   (`tests/fixtures/pipeline_golden/dogfood/`, já PII-zero) como fonte de
   dados, garantindo que o shape estrutural do relatório é o mesmo do
   pipeline real.
8. **Cobertura estrutural** substitui a onda de re-paridade que seria
   custosa e desnecessária: um assert sobre a presença de todas as
   seções/cards/charts/IDs do layout (fonte: `config/report_layout.yaml`)
   no HTML regenerado. Isso protege a referência de review sem carregar o
   `.html` em golden de valor — que nunca existiu.
9. A docstring em `tests/unit/pipeline/test_financial_score_calculator.py:402`
   é atualizada no mesmo PR: o próprio line-ref e a citação de linhas do HTML
   (`L1809-1811`); preferível de-acoplar da linha física (citar `id` de âncora).

## Alternativas consideradas

- **(A) Manter tags flutuantes + Dependabot só para bump de versão**:
  Dependabot vê a tag, não o SHA; não protege contra reescrita retroativa
  da tag — que é exatamente o vetor do CVE-2025-30066. Rejeitada.
- **(A) `permissions` mínimo declarado só nos jobs que escrevem, resto
  herda default**: o default do repo ainda seria permissivo; um job novo
  adicionado sem `permissions` reintroduz a superfície silenciosamente.
  `read-all` no topo torna a elevação **explícita e revisável**.
- **(B) Onda de re-paridade do EXEMPLO** (regenerar golden de valor,
  comparar pixel/estrutura contra baseline): custo alto para um artefato
  que **nenhum teste carrega** — seria criar acoplamento novo só para
  proteger a regeneração. Cobertura estrutural entrega o sinal (referência
  íntegra) sem o custo.
- **(B) Deletar o EXEMPLO** (nenhum teste depende): descarta a referência
  de review humano do REPORT_PREMIUM, que tem valor real para
  designer/PM. Rejeitada — o EXEMPLO fica, só troca os dados.

## Consequências

- **Superfície de CI/CD fecha antes do flip** (gate G5), independente do
  rewrite de histórico (W3) — a config vive no HEAD. Bumps de action
  passam a exigir PR de SHA, custo marginal absorvido por Dependabot.
- **First-time approval adiciona 1 clique** por contribuidor novo — custo
  aceito: o repo público terá contribuição externa esparsa, e o vetor de
  exfiltração via fork é real.
- **O EXEMPLO regenerado permanece a referência de review** do relatório
  premium, com garantia mecânica de completude estrutural. A ausência de
  golden de valor é intencional e documentada — não é dívida.
- **Coordenação com o dono do [[PLAN-report-premium]]** é pré-condição de
  [[A34.l8]]: o invariante de "zero seção removida" precisa do aval de
  quem mantém o layout canônico, para o assert estrutural refletir o
  contrato de paridade visual vigente.
- Migrar o Fernet dummy para secret **não altera segurança real** (o valor
  é público-inócuo por ser dummy); o ganho é higiene de scanner e remoção
  da TODO.

## Não-decisões

- **Licença, escopo público, rewrite de histórico, aceite de metadados,
  mailmap e fronteira de idioma** são owner-gated e vivem em
  [[ADR-313]]–[[ADR-318]]. Esta ADR não os toca.
- **Contrato negativo dos gates de PII/sigilo** (lint/sigilo/forbidden-paths/gitleaks
  como enforcement permanente) é escopo de [[ADR-319]] — complementar, não
  sobreposto: 319 protege *conteúdo*, 320 protege *execução*.
- **Regras de negócio do relatório** (quais seções existem, o que cada card
  mostra) permanecem em `config/report_layout.yaml` + [[PLAN-report-premium]];
  esta ADR só exige que a regeneração as preserve integralmente.
