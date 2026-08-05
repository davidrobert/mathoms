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

## Escopo adotado — 3 gates de integridade de grafo de lane (2026-08-05)

Roteados para cá porque esta lane **já é** a dona de gate de referência de doc e já
era candidata a absorver o gate da §Pendência de decisão nº 12. Origem: avaliação da
fusão [[A42]] → [[A40]] (recusada), que mediu os três como **blind spots provados**,
não hipóteses. São ortogonais ao gate de ADR-em-prosa acima e podem ir em PR próprio.

1. **Autorreferência e aresta órfã em `depends_on`/`parallel_with`.** É a §Pendência
   nº 12 da [[A40]]: a l27 entrou em `main` declarando `depends_on: [[A40.l27]]` —
   find-replace de renumeração trocou os wikilinks pelo próprio id e **nenhum gate
   pegou** (`check_doc_links` só pergunta se o alvo resolve, e resolve: é a própria
   nota). Efeito pior que link quebrado: **reescreve o grafo de dependências em
   silêncio**. ~10 linhas em `dev/validate_frontmatter.py` (266 linhas, tem folga;
   `check_doc_links.py` está em 498/500 e estouraria o P2 de tamanho). Não há caso
   legítimo de nota depender de si mesma.
2. **Coerência `path ↔ sprint`.** Lane com `sprint: AXX` tem de viver em
   `docs/sprint/AXX/lanes/`. Hoje **nada verifica**: medido em cópia isolada da vault,
   mover as 12 lanes da A42 para `docs/sprint/A40/lanes/` trocando só o campo `sprint`
   passa nos **cinco** gates de doc (`validate_frontmatter`,
   `check_doc_filename_id` — que é path-independent —, `check_doc_links`,
   `check_adr_anchors`, `build_doc_index --check`), deixando o id mentir sobre o dono.
   ~8 linhas em `dev/check_doc_filename_id.py`. É o gate que torna qualquer
   reorganização de sprint **detectável a meio caminho**.
3. **`former_ids` no schema de lane.** Renumeração é hoje **não-auditável por
   construção**: `docs/_schemas/note-lane.schema.json` não tem campo para id anterior,
   então o único registro do `A41.l1 → A40.l24` é blockquote em prosa, e o
   `l25 → l26 → l27` desta sprint não deixou registro nenhum. Patch aditivo
   (`additionalProperties: true` ⇒ não-breaking, zero migração), com retroaplicação no
   mesmo PR: `former_ids: ["A41.l1"]` na [[A40.l24]] e `["A40.l25","A40.l26"]` na
   [[A40.l27]].

**Achado de método que motivou os três:** o critério de agrupamento por arquivo que as
sprints declaram **não alcança** dependência cross-sprint nem renumeração — foi assim
que a aresta [[A42.l3]] → [[A40.l2]] (uma lane reescrevendo o instrumento que produz a
prova de outra) ficou invisível às duas sprints até 2026-08-05.

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

### Dos 3 gates de grafo de lane (§Escopo adotado)

- **Prova por mutação nos três, senão o gate é vácuo** (regra 3 da [[A42]]): fixture com
  `depends_on: ["[[self]]"]` ⇒ EXIT≠0 · lane com `sprint: A40` sob `docs/sprint/A42/lanes/`
  ⇒ EXIT≠0 · `former_ids` com id fora do pattern ⇒ EXIT≠0.
- `former_ids` retroaplicado em [[A40.l24]] e [[A40.l27]] no mesmo PR — sem isso o campo
  nasce sem os dois únicos casos que existem.
- `pre-commit run --all-files` verde sobre as 31 lanes da A40 + 12 da A42 **sem
  exceção**: se alguma lane viva falhar o gate de coerência `path ↔ sprint`, é defeito
  real e sai no mesmo PR.
- `python3 dev/build_doc_index.py --check` verde (o campo novo não entra em índice).
