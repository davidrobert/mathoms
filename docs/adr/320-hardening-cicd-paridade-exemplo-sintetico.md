---
id: ADR-320
type: adr
title: "Hardening de CI/CD e contrato de paridade estrutural do EXEMPLO sintético"
status: Decidido
phase: A34
date: "2026-07-08"
amended_at: ["2026-08-03"]
relates_to: ["[[PLAN-public-release]]", "[[A34.l13]]", "[[A34.l14]]", "[[A34.l15]]", "[[A34.l8]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/decidido
  - area/ci
  - area/seguranca
---

# ADR-320 — Hardening de CI/CD e contrato de paridade estrutural do EXEMPLO sintético

> **Emenda (2026-08-03) — o SHA-pin da decisão 2 tem um limite que não estava
> escrito:** ele pina o *código* da action, não a **imagem base** que uma action
> Docker builda em runtime. Uma das 4 actions pinadas (`CodelyTV/pr-size-labeler`)
> fazia `FROM alpine:3.15` sem digest e derrubou um required check por
> indisponibilidade do Docker Hub. A emenda no fim desta nota fecha a regra:
> action de terceiro em job *required* não pode ser `runs.using: docker`. Leia a
> decisão 2 como "fecha reescrita de tag", não como "fecha dependência externa".

**Status:** Decidido (A34) · **Data:** 2026-07-08 · Uma das 8 ADRs do gate G0 de
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

## Emenda 2026-08-03 — SHA-pin não cobre a base da imagem de Docker action

**O que a decisão 2 não garantia.** O pin por SHA fecha o vetor de reescrita de
tag (CVE-2025-30066). Não fecha o que a action **resolve em runtime**: uma action
`runs.using: docker` tem `Dockerfile` próprio, e o `FROM` dela é uma dependência
externa que o nosso pin não alcança. Das 4 actions pinadas em [[A34.l14]],
`CodelyTV/pr-size-labeler` fazia `FROM alpine:3.15` — sem digest, resolvido no
Docker Hub a cada run.

**Incidente medido (2026-08-03, PR #1157, run 30816509828 attempt 1, job
91695493843).** `dial tcp …:443: i/o timeout` ao resolver
`docker.io/library/alpine:3.15`, com retry que também falhou. O job era
`Title (Conventional Commits)`, *required check* do ruleset `main-protection`
(id 15884038): merge de **todo** PR do repo ficou bloqueado por um label
cosmético de tamanho.

**O mecanismo, que é o que importa para não repetir.** O runner builda a imagem
de uma Docker action num **passo sintetizado, antes dos passos declarados** no
workflow. Steps observados: `2 Build CodelyTV/pr-size-labeler → failure`,
`4 Validate PR title → skipped`. Como esse passo não é declarado, ele **não
carrega `continue-on-error`** — logo `continue-on-error: true` no passo que
referencia a action **não** protege o check. A correção que fecha o buraco é
remover Docker do caminho, não tolerar a falha dele.

**Regra (emenda à decisão 2).** Action de terceiro em job que seja *required
status check* deve ser `node20`/`composite`. `runs.using: docker` é vedado nesse
caminho — o build da imagem é dependência externa não-pinável de fora, no gate de
merge. Fora de job required (nightly, security, jobs informativos), Docker action
segue aceitável. Antes de adotar action de terceiro em job required, ler
`runs.using` no `action.yml` dela no SHA pinado.

**Por que não há gate automático.** O hook `docker-sha-pin` ([[ADR-249]])
escaneia `Dockerfile`/`compose` via `git ls-files` e por construção **não**
alcança o `Dockerfile` de action de terceiro — ele vive no repo dela e é buscado
em runtime. Verificar `runs.using` exigiria rede no pre-commit (buscar o
`action.yml` remoto), o que se recusa por princípio. A regra fica editorial,
sustentada por esta ADR + comentário no cabeçalho do workflow.

**Aplicado.** `76b32d3a` (#1161) removeu `CodelyTV/pr-size-labeler` e reimplementou
o size-label como script `gh` inline no próprio job, com thresholds e ignore-list
em paridade; `continue-on-error: true` entrou nos dois passos de label como defesa
em profundidade (label cosmética nunca gateia merge). As 3 actions restantes de
[[A34.l14]] são `node20` — nenhuma outra Docker action está em caminho de merge.
Registro operacional da sprint em [[MOC-sprint-a40]] §Infra de CI tocada durante
a sprint.
