---
id: A34.l9
type: lane
title: "Anonimizar ~15 ADRs + docs de sprint (in-body apenas)"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: anonymize-adrs-sprint-docs
adrs: []
depends_on: ["[[A34.l4]]"]
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/docs
---

# A34.l9 — `anonymize-adrs-sprint-docs` (W1 · Saneamento)

## Problema

Cerca de 15 ADRs e docs de sprint carregam PII real **no corpo do texto** —
resíduo de quando o vault documentava decisões contra o dogfood do próprio
owner. Enquanto o repo era privado isso era aceitável; no repo público vira
vazamento direto de dado de terceiro. Inventário mascarado em
[audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md) §1.3,
§1.4 e §1.6. Padrões contaminantes:

- **Placas de veículo reais** (com marca/modelo/ano) — §1.4.
- **Endereço residencial real** (rua, condomínio, matrícula de imóvel) — §1.3.
- **Número de contrato de crédito imobiliário** + parcela real — §1.6.
- **Patrimônio por nome** (nome do titular/cônjuge + valores exatos por ano) — §1.6.
- **Transações PJ com clientes nomeados** (Pix de empregador identificado, CDB
  com valor exato, decomposição de renda por fonte) — §1.6.

A anonimização é **in-body apenas**: o valor real some, mas a **mecânica** que a
ADR/lane documenta (o que o código faz, por que a regra existe) é preservada com
placeholders sintéticos (`Titular`/`Cônjuge`, `123.456.789-09`, `Rua Exemplo, 100`,
`R$ X`, placa `ABC1D23`, matrícula `999.999`).

## Escopo

**Anonimizar (corpo):**

- ADRs `docs/adr/215-*.md`, `225-*.md`, `239-*.md`, `244-*.md`, `245-*.md`,
  `246-*.md`, `255-*.md`, `261-*.md`, `265-*.md`, `267-*.md`.
- **Revisar** (achado incerto — só editar se o padrão realmente aparecer no
  corpo): `073-*.md`, `136-*.md`, `168-*.md`, `241-*.md`, `266-*.md`.
- Lanes `docs/sprint/A17/lanes/A17-l6-*.md`, `docs/sprint/A18/lanes/A18-l1-crlv.md`,
  `docs/sprint/A18/lanes/A18-l2-apolice.md`, `docs/sprint/A28/lanes/A28-l5*.md`.
- Changelog `docs/sprint/A12/changelog/CHG-2026-05-12*.md`.
- Runbook `docs/agent_prompts/orchestrator_a17_a18_a19.md`.

**Regra pedagógica:** onde a PII é *exemplo* que ilustra a regra (ADR-246 dedup de
imóvel em comunhão; ADR-255 strip de sufixo PIX; ADR-267 identidade de membro por
CPF; ADR-271 dedup cross-declarante), reescrever com `Titular`/`Cônjuge` sintéticos
**preservando a mecânica** — o exemplo continua ensinando a mesma coisa, só sem o
dado real. Não remover o exemplo; substituir o dado.

**NUNCA tocar** (invariante `filename ≡ id ≡ wikilink-target`): `id`, filename,
`aliases`, `supersedes`, `superseded_by`, `relates_to`, ou qualquer campo de
frontmatter. ADRs 246/255/267/271 são `adrs_canonical` de [[PLAN-launch-trust]] —
quebrar o `id` desconecta o grafo. `size_lines` é regenerado por `build_doc_index`;
**não editar à mão**.

## Critério de aceite (verificável)

- `git grep -in` no HEAD para cada padrão (placa real, matrícula real, nº de
  contrato real, nome de terceiro, patrimônio nominal, empregador nomeado) =
  **zero ocorrências no corpo** dos arquivos em escopo.
- `python3 dev/check_doc_links.py` verde — nenhum wikilink quebrado pela edição.
- `python3 dev/check_adr_anchors.py` verde — âncoras históricas preservadas em
  cada ADR editada.
- `python3 dev/validate_frontmatter.py` verde — `id`/filename/`supersedes`/
  `superseded_by`/`relates_to` idênticos ao pré-edição (diff só no corpo).
- `python3 dev/build_doc_index.py` regenera `_generated/` sem drift de `id`; o
  único delta esperado por ADR é `size_lines`.
- Gate [[A34.l4]] (`lint_no_real_pii` estendido a `docs/`) roda **verde** sobre
  os arquivos saneados — prova que a detecção que rodou vermelho no HEAD
  contaminado agora passa.
- Exemplos pedagógicos preservam a mecânica: ADR-246 ainda ilustra dedup em
  comunhão, ADR-255 ainda ilustra o sufixo PIX, apenas com dados sintéticos.

## Rollback

Docs-only, não-destrutiva de código — **mergeia sem CI** (política docs-only do
CLAUDE.md). `pre-commit run --all-files` continua obrigatório (PII, paths,
commit msg). Rollback = `git revert` do commit de anonimização; como nenhum
`id`/wikilink muda, reverter não produz link rot. Sem migração de dados, sem
efeito em runtime.

## Notas

- **Depende de [[A34.l4]]** — o gate PII estendido a `docs/` precisa existir e
  rodar vermelho no HEAD contaminado antes desta lane (ordem W2→W1: gate-first).
- Par de saneamento W1 com [[A34.l7]] (delete `_archive/`), [[A34.l10]]
  (purgar CPFs+endereço em código/testes) e [[A34.l12]] (redigir IP competitivo).
- Rodar `check_doc_links` + `check_adr_anchors` **por ADR** durante a edição —
  não deixar acumular para o fim.

## Referências

- Plano: [[PLAN-public-release]] — Onda W1.
- Anexo: [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md)
  §1.3 (endereço), §1.4 (placas), §1.6 (valores/transações).
- Gate de detecção: [[A34.l4]].
- Grafo a preservar: [[PLAN-launch-trust]] ([[ADR-246]] · [[ADR-255]] ·
  [[ADR-267]] · [[ADR-271]]).
