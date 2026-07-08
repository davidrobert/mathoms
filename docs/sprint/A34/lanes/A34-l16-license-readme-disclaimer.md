---
id: A34.l16
type: lane
title: "LICENSE + README EN com disclaimer e fronteira de idioma"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: license-readme-disclaimer
adrs: ["[[ADR-313]]", "[[ADR-318]]", "[[ADR-183]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/docs
  - area/gtm
---

# A34.l16 — `license-readme-disclaimer` (W6 · Apresentação)

## Problema

Um repositório público **sem `LICENSE`** é, por default legal, *all-rights-reserved*:
qualquer visitante que clone o código não tem direito de uso, estudo ou contribuição.
Para um projeto que se apresenta como aberto, a ausência de licença é hostil e
sinaliza descuido — dano de percepção ativo no momento do flip. Hoje não há `LICENSE`
na raiz.

Além disso, o flip expõe duas expectativas falsas se nada for dito:

1. **Certificação/aconselhamento financeiro.** O Mathoms é dogfood de relatório e
   planejamento patrimonial, **não** software financeiro certificado nem
   aconselhamento profissional. Sem disclaimer explícito, um leitor pode assumir
   garantia que o projeto não oferece.
2. **Idioma da superfície pública.** O vault (`docs/adr`, `docs/plan`, `docs/sprint`,
   `docs/reference`) é PT-BR por decisão de vault; a superfície de apresentação
   (README/CONTRIBUTING/LICENSE/SECURITY) deve ser EN — língua franca de open-source,
   e o ICP nômade-BR lê EN. Sem uma fronteira formalizada ([[ADR-318]]), a mistura
   confunde o contribuidor externo e reabre por engano o debate de produto-i18n.

Esta lane é a **apresentação mínima** de W6 (G6-min): só o que, ausente, causa dano
legal (LICENSE) ou expectativa falsa (disclaimer). Polish de percepção é [[A34.l17]]
(P2, pós-flip).

## Escopo

1. **`LICENSE` na raiz** com o texto exato da licença decidida em [[ADR-313]]
   (leading: BSL 1.1, Change License Apache-2.0, janela de 4 anos). O arquivo deve
   ser o texto canônico da licença, sem edição — GitHub só reconhece o badge de
   licença com o texto íntegro.
2. **`README.md` raiz reescrito em EN** contendo:
   - **(a) Status / disclaimer**: seção explícita "dogfood, not certified financial
     software / not financial advice".
   - **(b) Fronteira de idioma** ([[ADR-318]]): nota de que a superfície de
     apresentação (README/CONTRIBUTING/LICENSE/SECURITY) é EN e o vault
     (`docs/adr`, `docs/plan`, `docs/sprint`, `docs/reference`) permanece PT-BR —
     por design, não por omissão.
   - **(c) Narrativa de categoria** com o vocabulário canônico de [[ADR-183]]
     ("metodologia consagrada de planejamento patrimonial brasileiro"), **sem
     atribuição nominal** a Perini/Cerbasi/AUVP/Raul Sena.
   - **(d) Transparência de escopo público**: nota do que é/não é público caso os
     prompts de produto sejam split ([[A34.l12]] / [[ADR-314]]) — evitar que o
     leitor conclua "o repo é o produto inteiro".
3. **Sem reabrir produto-i18n.** Esta lane ativa apenas a cláusula de apresentação
   de [[ADR-318]]; [[PLAN-i18n]] permanece `paused`. A reconciliação ampla de
   docs-EN é [[A34.l23]] (W7, should).

## Critério de aceite (verificável)

- `test -f LICENSE` na raiz; conteúdo é o texto canônico da licença de [[ADR-313]]
  (GitHub reconhece o SPDX no badge de licença).
- `README.md` raiz em EN, contendo: seção de disclaimer de dogfood; nota de fronteira
  EN/PT-BR; narrativa de categoria sem atribuição nominal.
- **Gate de sigilo estendido ([[A34.l5]] / [[ADR-319]]) verde no README**:
  `grep -iE '(perini|cerbasi|auvp|raul sena|viver de renda)'` no README = vazio.
- `check_doc_links` verde (wikilinks e links relativos do README resolvem).
- Nenhum campo `id`/filename de ADR ou plano alterado — esta lane só adiciona
  arquivos de apresentação, não toca o grafo do vault.

## Rollback

Baixo blast-radius (dois arquivos novos na raiz, sem código de runtime). Rollback =
`git revert` do PR. Não há migração, estado nem dependência downstream que precise
de compensação. A escolha de licença é substantiva — trocar de licença pós-flip é
possível mas politicamente custoso; por isso é gate-first em [[ADR-313]] (G0), não
decisão desta lane.

## Notas de execução

- **Depende de G0**, não de outra lane (`depends_on: []`): [[ADR-313]] (licença) e
  [[ADR-318]] (fronteira) precisam estar **decididas** antes de escrever o texto —
  senão o `LICENSE` fica com placeholder e o README afirma uma fronteira não ratificada.
- **CI obrigatório**: embora o conteúdo seja docs/apresentação, o gate de sigilo
  estendido roda em pre-commit/CI sobre o README (superset público de [[A34.l5]]).
  Não mergeia sem o gate de sigilo verde.
- Reusar o `SECURITY.md` e `.github/CONTRIBUTING.md` existentes como âncoras de
  tom/idioma; a tradução/adaptação deles para EN é [[A34.l23]] (W7, should), não
  esta lane.

## Referências

- Plano: [[PLAN-public-release]] §W6 (Apresentação, G6-min).
- ADRs: [[ADR-313]] (licença) · [[ADR-318]] (fronteira EN-apresentação vs PT-BR-vault) ·
  [[ADR-183]] (vocabulário canônico de categoria, sem atribuição nominal).
- Par de onda: [[A34.l17]] (polish, P2, pós-flip).
- Gate consumido: [[A34.l5]] (sigilo estendido) / [[ADR-319]].
- Reconciliação: [[PLAN-i18n]] ([[ADR-130]]) — permanece `paused`; docs-EN amplo em [[A34.l23]].
