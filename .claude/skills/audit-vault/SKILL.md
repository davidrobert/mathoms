---
name: audit-vault
description: >-
  Auditar o vault de documentação (MD/HTML/YAML/JSON/TOML/TXT) quanto a
  completude, corretude, consistência e precisão. Use quando o dono pedir para
  "auditar a documentação/o vault/os planos/ADRs/prompts", revisar saúde de
  docs, ou ao fechar um plano canônico grande (drift recém-criado). Orquestra
  gates determinísticos → julgamento delegado aos especialistas → síntese que
  se pluga em docs/_MOC/AUDITS-active.md. Canônica: ADR-302.
---

# audit-vault

Procedimento do **loop principal** para auditoria recorrente do vault. Não é um
agente — orquestra os gates de `dev/` e delega julgamento aos especialistas do
**§Subagentes do CLAUDE.md**. Regra canônica: [[ADR-302]]. Detalhamento de
critérios, roteamento, severidade e armadilhas: [`references/checklist.md`](references/checklist.md).

## Parâmetros

- `--scope` = `all` (default) · `reference` · `adr` · `plan` · `claude` ·
  `prompt` · `sprint` · `root`.
- `--mode` = `comprehensive` (default: todos os buckets vivos, 5 dimensões) ·
  `focused` (só o `--scope` dado, dimensão dominante).
- `--full` = sweep 100% do universo do `--scope` (repassa `--full` ao coletor).
  **Modo de evento** — baseline inicial, pós-refactor estrutural, gate
  dogfood→beta ([[ADR-302]] §Gatilho) — nunca cadência recorrente. Custo ≈17k
  tokens de julgamento/arquivo (empírico r5); rode **1 bucket por sessão/PR**
  (`--scope reference --full` primeiro) para a triagem caber em <30min por fase.

`archive/` e sprint fechada ficam **sempre fora** do julgamento (gates ainda
rodam via pre-commit) — auditar histórico congelado gera falso-drift.

## Procedimento (5 camadas)

### Camada 0 — Contexto (obrigatória, antes de tudo)

1. Ler [`docs/_MOC/_generated/CONTEXT_INDEX.md`](../../../docs/_MOC/_generated/CONTEXT_INDEX.md)
   e escolher os buckets do escopo. **Nunca** `rg --no-ignore`.
2. Ler a **última seção** de [`docs/_MOC/AUDITS-active.md`](../../../docs/_MOC/AUDITS-active.md):
   todo `procede-aberto` que persiste é re-priorizado ou rebaixado a
   `aceito-wontfix` (cadência anti-zumbi §4). Sem zumbis silenciosos.

### Camada 1 — Gates determinísticos (fail-fast, 100% dos arquivos)

Rode e capture:

```bash
python3 dev/validate_frontmatter.py
python3 dev/check_doc_links.py
python3 dev/check_adr_anchors.py
python3 dev/check_doc_filename_id.py
python3 dev/validate_adr_format.py
python3 dev/build_doc_index.py --check
```

Cada gate falho vira finding automático `corretude` **sem gastar token LLM**.
O julgamento (camada 3) **nunca** re-verifica o que um gate cobre
(ver coluna "coberto por gate" no checklist).

### Camada 2 — Coleta determinística

```bash
python3 .claude/skills/audit-vault/references/collect_candidates.py \
  --scope all --since origin/main --run <N> --out _scratch/audit-candidates.json
```

`<N>` = número deste run (o `rN` da seção que este run criará no
AUDITS-active = última seção + 1). Candidatos = `gate-fail ∪ git-diff ∪ amostra
rotativa`: cada arquivo tem classe permanente `sha1(path) % stride` e o `--run`
rotaciona a classe-alvo — 100% do bucket é julgado a cada `stride` runs
(reference/plan/sprint/root: 5 · adr/claude/prompt: 20). Sem `--run`, a amostra
repete a classe 0 (o bug F17/r5). Reproduzível: `--self-test` prova que o mesmo
`--run` dá o mesmo conjunto E que a rotação cobre o universo. Para sweep 100%,
repasse `--full` (ver §Parâmetros); o JSON de saída traz `buckets` com
`universe/sampled/stride` — cite essa cobertura no relatório.

### Camada 3 — Julgamento delegado (só nos candidatos)

Para cada candidato, roteie por **`type:` do frontmatter** (não por path) ao
especialista, conforme o mapa em [`references/checklist.md`](references/checklist.md) §2.
**Múltiplos buckets → invoque os especialistas em paralelo** (1 mensagem, N
`Agent` calls), como manda o §Protocolo de delegação. Ataque só os 4 gaps que
gate não pega: precisão factual (doc↔código), consistência semântica cross-doc,
supersedure de sentido, completude editorial. Brief mínimo: "reporte findings,
não conserte".

A maioria dos `DOC-BLOCK` (doc contradiz código) o **loop principal** resolve
sozinho por diff textual — não precisa de especialista.

### Camada 4 — Verify (só severidade ≥ DOC-BLOCK)

Cada `DOC-BLOCK` passa por **1 verify barato**: cite o trecho exato do doc **e**
o da fonte-de-verdade (código/ADR/config) que se contradizem. **Sem citar
ambos → rebaixa para DOC-DRIFT/descarta.** Nunca auto-marque `refutado` sem
evidência empírica (lição SEC-03 do AUDITS-active).

### Camada 5 — Síntese (dois outputs)

1. **Bruto** → `_scratch/audit-vault-<YYYY-MM-DD>.md` (efêmero, todos os
   findings inclusive ruído).
2. **Curado** → patch de nova seção para
   [`docs/_MOC/AUDITS-active.md`](../../../docs/_MOC/AUDITS-active.md), na
   convenção existente: `## rN — vault-<YYYY-MM-DD>-rN`, tabela
   `Código | Severidade | Veredito | Disposição | Trilha`, **cobertura 100%**
   (todo finding com disposição; default `procede-aberto`).

Estrutura de finding e dedup por `(path, regra)`: checklist §4.

## Do finding à ação (triagem manual — nunca auto-lane)

- **DOC-BLOCK** → commit `docs(...)` imediato (docs-only, sem gate de CI) ou
  lane XS se toca código.
- **DOC-DRIFT** → **uma** lane P2 batch no BACKLOG (estilo W6-T04). A skill
  **propõe**; não cria `track_*.md` automático (furaria o pickup discipline).
- **DOC-POLISH** → lista no relatório; wontfix até pré-beta.

## Critério de aceite

- ≥1 `DOC-BLOCK` vira correção mergeada em `main`.
- Falso-positivo dos `DOC-BLOCK` ≤ 20% na triagem.
- Modo default não chama LLM em arquivo que passou gates e está inalterado.
- < 30% dos findings recriam o que o pre-commit já pega.
- Relatório triável em < 30min.

## Gatilho de reabertura (dogfood → beta)

Em dogfood, sem cron e sem KR. Ao cruzar para beta, reabrir: cadência agendada,
KR "% reference sem DOC-BLOCK", sweep amplo. Ver [[ADR-302]] §Gatilho.
