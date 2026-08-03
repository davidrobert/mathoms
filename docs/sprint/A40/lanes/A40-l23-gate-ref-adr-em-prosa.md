---
id: A40.l23
type: lane
title: "Gate: ADR citada em prosa tem de resolver para arquivo — reserva de ID é invisível"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l23-gate-ref-adr-em-prosa
adrs:
  - "[[ADR-345]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/docs
---

# A40.l23 — `gate-ref-adr-em-prosa`

> Onda 4 da A40. Fecha a **classe** que a [[ADR-345]] expôs — ela conserta a
> instância.

## Problema

A A39 reservou o ID "ADR-345" citando-o **6× em prosa**
(`docs/sprint/A39/_README.md` ×5 + `docs/_MOC/SPRINTS-active.md` ×1) e nunca
escreveu o arquivo. Como as menções eram **texto puro, não wikilink**,
`dev/check_doc_links.py` não as via.

Consequência: o ID era **roubável**. O alocador de ID é `ls docs/adr/ | tail` — o
próximo agente pega o teto e nunca descobre a reserva. Quando o trabalho fosse
feito, ou colidia, ou nascia com ID diferente e as 6 referências apontavam para o
nada.

A instância foi fechada pela [[ADR-345]] (nota `Roadmap` ocupando o ID + menções
convertidas em wikilink). **A classe continua aberta:** nada impede a próxima
reserva-em-prosa.

## Decisão

Gate que exige que `ADR-\d{3}` citado em **prosa** resolva para arquivo existente
em `docs/adr/`.

Escopo e cuidados que o `senior-cto` e o `information-architect` nomearam:

- **Fora do gate:** ocorrências dentro de wikilink `[[ADR-NNN]]` (já cobertas por
  `check_doc_links.py`) e dentro de code fence / inline code.
- **Whitelist obrigatória:** o shim `docs/DECISIONS.md` (preserva âncoras
  históricas de PRs antigos por design) e `docs/archive/**` (arqueologia — cita
  ADRs de planos substituídos).
- Toca `dev/` + `.pre-commit-config.yaml`, por isso **não foi empacotado** no PR
  da [[ADR-345]].

Regra que o gate enforça, já escrita no CLAUDE.md §ADRs: **nunca reserve ID de
ADR; reserve o trabalho** — deferimento datado com dono no plano, que é
wikilink-ável e visível aos gates. Precedente de forma: [[ADR-356]].

## Critério de aceite

- Fixture com `ADR-999` em prosa de doc não-whitelisted ⇒ EXIT≠0 com mensagem
  que aponta arquivo + linha.
- Fixture com `[[ADR-999]]` ⇒ o gate **não** dispara (é escopo do
  `check_doc_links.py`).
- Fixture com `ADR-999` dentro de code fence ⇒ não dispara.
- `docs/DECISIONS.md` e `docs/archive/**` não disparam.
- `pre-commit run --all-files` verde sobre o vault atual **sem** exceção nova além
  da whitelist declarada — se precisar de mais exceções, são reservas-em-prosa
  ainda vivas e devem ser fechadas, não whitelisted.
