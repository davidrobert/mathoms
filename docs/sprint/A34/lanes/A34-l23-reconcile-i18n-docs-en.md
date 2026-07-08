---
id: A34.l23
type: lane
title: "Docs EN de apresentação + cross-link PLAN-i18n"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P2
branch_slug: reconcile-i18n-docs-en
adrs: ["[[ADR-318]]", "[[ADR-130]]"]
depends_on: ["[[A34.l16]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p2
  - area/docs
---

# A34.l23 — `reconcile-i18n-docs-en` (W7 · i18n docs (should))

## Problema

Um repo público de referência é lido por audiência-de-repo (contribuidores,
recrutadores, avaliadores técnicos) para a qual o inglês é o idioma esperado.
Hoje a **camada de apresentação** do repo (`README.md`, `.github/CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md` se existir, `SECURITY.md`) está em PT-BR — coerente com a
audiência interna de agentes, mas fricção para a audiência-de-repo externa.

Ao mesmo tempo, o vault (`docs/adr/`, `docs/plan/`, `docs/sprint/`,
`docs/reference/`) é PT-BR por decisão explícita e **não deve** ser traduzido:
é arqueologia de decisão, densa, e a tradução multiplicaria custo de manutenção
e drift entre idiomas sem servir a nenhuma audiência real. A regra
[[PLAN-i18n]] §2 (vault permanece PT-BR) fica **intacta**.

O risco de não separar as duas camadas é duplo: (a) traduzir o vault inteiro
por reflexo "internacional"; (b) sinalizar erroneamente que o **produto** entrou
em fase de i18n (produto-i18n está `paused` com gate de demanda — [[ADR-130]]),
quando esta lane ativa apenas a cláusula já escrita de docs-EN para open-source.
A fronteira é formalizada em [[ADR-318]].

Esta é uma lane **should, pós-flip** (W7): não bloqueia o marco de segurança do
flip. Depende de [[A34.l16]] (LICENSE + README EN com disclaimer já criado no
caminho crítico) — esta lane completa a camada de apresentação em EN a partir
daquela base.

## Escopo

1. Traduzir para EN a camada de apresentação pública:
   - `README.md` (raiz) — partindo do README EN mínimo já entregue em [[A34.l16]],
     completar seções de apresentação (o disclaimer de dogfood e a fronteira de
     idioma já vêm de l16; preservá-los).
   - `.github/CONTRIBUTING.md`.
   - `CODE_OF_CONDUCT.md` (se presente; caso ausente, fica com [[A34.l17]] polish).
   - `SECURITY.md` — traduzir mantendo os SLAs e a referência de disclosure LGPD.
2. **NÃO traduzir o vault:** `docs/adr/`, `docs/plan/`, `docs/sprint/`,
   `docs/reference/` permanecem PT-BR. Regra [[PLAN-i18n]] §2 intacta.
3. Cross-link **bidirecional**: da camada de apresentação para [[PLAN-i18n]]
   (fronteira EN/PT-BR) e do PLAN-i18n de volta para esta lane.
4. Nota editorial de gatilho open-source em [[PLAN-i18n]] §10 — registrar que a
   cláusula de docs-EN foi ativada pelo flip público, **sem nova ADR** e **sem
   reabrir** as fases F12.* de produto-i18n.
5. Fora de escopo: pt-PT (descartado, decisão unânime do co-design); produto-i18n
   (`paused`, não reabrir); tradução de qualquer arquivo dentro de `docs/**`.

## Critério de aceite (verificável)

- `README.md`, `.github/CONTRIBUTING.md`, `SECURITY.md` (e `CODE_OF_CONDUCT.md`
  se presente) com corpo em EN; disclaimer de dogfood + fronteira de idioma
  herdados de [[A34.l16]] preservados.
- `docs/adr/`, `docs/plan/`, `docs/sprint/`, `docs/reference/` **inalterados
  em idioma** — `git diff` desta lane não toca corpo desses diretórios.
- Cross-link bidirecional presente: link EN→[[PLAN-i18n]] na apresentação e
  link [[PLAN-i18n]]→[[A34.l23]] no §10 do plano.
- [[PLAN-i18n]] permanece `status: paused` (produto-i18n intacto); a nota §10 é
  editorial, sem emenda de ADR e sem tocar frontmatter do plano além do link.
- Gates de doc verdes: `check_doc_links` e `check_adr_anchors` operam sobre
  frontmatter + wikilinks e são **independentes do idioma do corpo**; o README
  raiz não tem frontmatter, então nenhum gate de doc é acionado por ele.
  `check_sigilo_terms` (estendido em [[A34.l5]]) verde sobre os arquivos EN.
- pt-PT ausente; nenhum diretório de produto-i18n (F12.*) criado ou modificado.

## Rollback

Docs-only e não-destrutiva. Reverter é `git revert` do PR — a camada de
apresentação volta ao PT-BR e a nota §10 do PLAN-i18n sai. Nenhum artefato
de runtime, migration ou histórico git afetado.

**Mergeia sem CI** (exceção docs-only do CLAUDE.md): o diff é exclusivamente
`README.md` + `.github/*.md` + `SECURITY.md` + `CODE_OF_CONDUCT.md` +
`docs/plan/I18N/_README.md` (nota §10). `pre-commit run --all-files`
(PII/sigilo/paths/commit-msg) continua obrigatório.

## Referências

- Plano canônico: [[PLAN-public-release]] (§Ondas W7 · G7).
- Fronteira de idioma: [[ADR-318]] (ativa cláusula §11 de [[ADR-130]] sem emenda).
- Produto-i18n pausado: [[PLAN-i18n]] ([[ADR-130]]).
- Base da apresentação EN: [[A34.l16]] (LICENSE + README EN + disclaimer).
- Polish complementar (P2, pós-flip): [[A34.l17]].
