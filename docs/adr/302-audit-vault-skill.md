---
id: ADR-302
type: adr
title: "Skill audit-vault — auditoria recorrente de vault como procedimento do loop principal"
status: Decidido
phase: A26
date: "2026-07-01"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-182]]"
  - "[[ADR-247]]"
  - "[[ADR-343]]"
amended_at:
  - "2026-07-03"
  - "2026-08-21"
supersedes: []
superseded_by: []
aliases:
  - "ADR 302"
  - "audit-vault skill"
  - "auditoria de vault"
tags:
  - type/adr
  - status/decidido
  - area/docs
  - area/tooling
  - phase/a26
size_lines: 245
---

> ADR >150 linhas: procedimento de 5 camadas + 2 emendas datadas (amostra
> rotativa 2026-07-03; bucket `moc` 2026-08-21) — 1 conceito, densidade
> legítima; split produziria peças órfãs.

> **Emenda (2026-07-03, achado F17 do run r5):** amostra estratificada da
> camada 2 passou a ser rotativa (`--run N`) — ver blockquote na camada 2 de §Decisão.

> **Emenda (2026-08-21):** o universo ganha o bucket `moc` — registros com
> máquina de estado ([[ADR-343]]) no grão de **linha viva**, navegacionais no
> grão-arquivo; `AUDITS-active` e `SPRINTS-active` ficam fora do universo
> julgado. Dedup de linha de registro estende a chave para
> `(path, regra, âncora)`. Ver §Emenda 2026-08-21.

## Contexto

Auditar o vault de documentação (MD/HTML/YAML/JSON/TOML/TXT) quanto a
**completude, corretude, consistência e precisão** é tarefa recorrente do dono
do repo. Hoje é feita ad-hoc: cada auditoria reinventa formato de finding,
escopo e roteamento. Precedentes provam o valor e o custo da falta de
convenção — a revisão multi-agente de 2026-04-24 ([PHASES §DOCS-REVIEW](../reference/PHASES.md))
e a `repo-audit-...-r2` (cujo relatório efêmero **se perdeu** e teve de ser
reconstruído da trilha, ver [AUDITS-active](../_MOC/AUDITS-active.md)).

Já existe infra parcial que uma auditoria nova **deve reusar em vez de duplicar**:

- **7 gates determinísticos** em `dev/` (`validate_frontmatter`,
  `check_doc_links`, `check_adr_anchors`, `check_doc_filename_id`,
  `validate_adr_format`, `build_doc_index --check`,
  `check_doc_markdown_links`) rodando em pre-commit — cobrem o **mecânico**.
- **`docs/_MOC/AUDITS-active.md`** — registro editorial com taxonomia de
  disposição (`procede-fechado`/`procede-aberto`/`refutado`/`não-acionável`/
  `aceito-wontfix`), cadência anti-zumbi e cobertura 100%.
- **`docs/archive/audits/`** — padrão de arquivamento de auditoria fechada.

O gap: não há **procedimento reutilizável** que orquestre gates → julgamento
LLM → síntese, plugando no registro existente. A pergunta "isso é skill, prompt
ou agente?" precisa de resposta canônica para não recorrer.

## Decisão

Auditoria de vault é **procedimento do loop principal** implementado como
**Skill** (`.claude/skills/audit-vault/`), não como agente novo nem prompt
solto.

**Rationale da forma:** um agente `vault-auditor` duplicaria os 5 especialistas
que já têm o domínio (`information-architect` julga forma, `senior-cto` ADR
técnica, `financial-planner` regra de domínio, `product-manager` plano
canônico, `prompt-engineer` prompt YAML). O valor é o **procedimento de
orquestração + roteamento + taxonomia de output** — não uma nova cabeça de
julgamento. No modelo deste repo, quem delega é o loop principal (§Subagentes
do CLAUDE.md); auditar **é** orquestração ⇒ é trabalho de skill.

Arquitetura em camadas (fronteiras sem sobreposição):

1. **Gates determinísticos primeiro** (fail-fast, 100% dos arquivos). Gate
   falho vira finding automático `corretude` **sem gastar token LLM**.
2. **Coleta determinística** (`references/collect_candidates.py`): candidatos a
   julgamento = `gate-fail ∪ git-diff ∪ amostra estratificada`. Não manda os
   ~956 markdown ao LLM; só o residual.

   > **Emenda 2026-07-03 (achado F17 do run r5):** a amostra original
   > (`clean[::20]`, offset fixo) fazia r3/r4/r5 julgarem os **mesmos** 24
   > arquivos — 97% do universo nunca entrava na camada 3. A amostra agora é
   > **rotativa**: classe permanente `sha1(path) % stride` + `--run N` (o rN do
   > AUDITS-active) rotacionando a classe-alvo — 100% do bucket coberto a cada
   > `stride` runs, imune a inserções no vault. Stride por bucket
   > (reference/plan/sprint/root: 5 · adr/claude/prompt: 20) pondera risco de
   > rot. `--full`/`--stride 1` habilita sweep 100% como **modo de evento**
   > (baseline, pós-refactor, gate dogfood→beta — nunca recorrente). O contrato
   > de determinismo passa a ser "mesmo `--run` → mesmo conjunto"; o
   > `--self-test` também prova a cobertura completa da rotação.
3. **Julgamento LLM** só nos candidatos, roteado por **`type:` do frontmatter**
   (não por path) ao especialista do §Subagentes. Ataca só os 4 gaps que gate
   não pega: precisão factual (doc↔código), consistência semântica cross-doc,
   supersedure de sentido, completude editorial.
4. **Verify barato** só em findings de severidade alta: exige citar o trecho do
   doc **e** da fonte-de-verdade que se contradizem; sem ambos, rebaixa.
5. **Síntese** com dois outputs: relatório bruto em `_scratch/` (efêmero) +
   **patch de seção para `docs/_MOC/AUDITS-active.md`** (curado, disposição).

**Severidade ancorada em consequência** (não herda P0/P1/P2 de runtime):
`DOC-BLOCK` (doc contradiz código/ADR vigente ⇒ agente decidiria errado — fix
agora), `DOC-DRIFT` (desatualizado mas não indutor de erro — batch em lane P2),
`DOC-POLISH` (cosmético — wontfix/batch). Só `DOC-BLOCK` interrompe.

**Baseline = o AUDITS-active.md.** Em estágio dogfood, a disposição triada no
registro editorial **é** o baseline; dedup entre runs por chave semântica
`(path, regra)` cruzada contra o `procede-aberto` da seção anterior. Um baseline
JSON separado fica **deferido** (gatilho de crescimento: quando o cross-ref
manual doer).

> **Emenda 2026-08-21:** para finding sobre **linha de registro**, a chave é
> `(path, regra, âncora)` com `âncora = <seção rN>/<código>` — código sozinho
> não é identidade (`F01` reinicia a cada run). Ver §Emenda 2026-08-21.

## Alternativas consideradas

### Opção A — Agente novo `vault-auditor`

**Rejeitada.** Duplica os 5 especialistas existentes; viola a filosofia de
"especialista estreito". Auditoria não é domínio novo, é orquestração.

### Opção B — Prompt/`track_*.md` copiável

**Rejeitada.** `track_*` é para 1 lane / 1 agente / 1 branch ligado ao BACKLOG.
Auditoria é recorrente e transversal, não lane. Prompt solto não é discoverable
via `/` e apodrece.

### Opção C — "Workflow salvo" como artefato de orquestração separado

**Rejeitada.** Criaria segundo orquestrador que **duplica** a tabela de
gatilhos do §Subagentes — diverge em poucas sprints. O que sobrevive dela é a
**coleta determinística** (`collect_candidates.py`), que não roteia agentes.

## Consequências

### Positivas

- Procedimento reutilizável via `/audit-vault`, versionado e descoberto.
- Zero duplicação de roteamento: a skill **referencia** o §Subagentes.
- Custo controlado: LLM só no residual, não nos 956 arquivos.
- Recorrência reproduzível: 2 runs sem mudança → mesmo conjunto de candidatos.
- Findings aterrissam no registro canônico existente, com dedup semântico.

### Negativas

- Introduz nova classe de artefato (`.claude/skills/`) — primeiro do repo.
- Manter o roteamento por `type:` alinhado aos schemas em `docs/_schemas/`.
- Triagem de disposição continua manual (custo humano, como os goldens).

## Validação

Critério de aceite da skill (prova de valor, não teatro):

- ≥1 `DOC-BLOCK` vira correção mergeada em `main` (docs-only).
- Taxa de falso-positivo dos `DOC-BLOCK` ≤ 20% na triagem.
- Determinismo: 2 runs sem mudança → diff de candidatos vazio
  (`collect_candidates.py --self-test`).
- Modo default não chama LLM em arquivo que passou gates e está inalterado.
- < 30% dos findings recriam o que o pre-commit já pega.

**Evidência do flip (2026-07-03):** critérios satisfeitos pelas execuções
`vault-2026-07-01-r3` (18 findings triados, DOC-BLOCKs com 0 falso-positivo,
correções mergeadas em `main`) e `vault-2026-07-02-r4` (gates 100% verdes,
3/3 DOC-BLOCKs reverificados, zero regressão r3→r4) registradas em
[AUDITS-active](../_MOC/AUDITS-active.md).

## Migração

1. `references/checklist.md` (4 critérios × tipo de arquivo + coluna "coberto
   por gate").
2. `references/collect_candidates.py` + `--self-test`.
3. `SKILL.md` (procedimento das 5 camadas, parâmetros `--scope`/`--mode`,
   armadilhas, referência ao §Subagentes).
4. Primeira execução real; nova seção em `AUDITS-active.md`.

## Riscos

- **LLM inventa contradição** — mitigado pela camada 4 (verify obrigatório em
  DOC-BLOCK) e pela lição SEC-03 (nunca auto-marcar `refutado` sem evidência
  empírica).
- **Escopo puxa histórico congelado** — `archive/` e sprint fechada ficam fora
  do julgamento (gates só); auditar precisão de snapshot gera falso-drift.

## Emenda 2026-08-21 — bucket `moc`: registros com máquina de estado

**Origem:** revisão de método da `lane-closeout` (2026-08-21, IA+PM+CTO). Os 2
`CLOSE-BLOCK` reais do closeout da Onda A moravam em linha de achado de
`docs/_MOC/PIPELINE-REVIEWS-active.md` — fora do universo de **ambas** as
skills. Verde-falso por construção: o escopo era escolhido pelo autor e o
registro certo ficava fora dele. As unidades com máquina de estado são três:
lane (`status:`), linha de achado em MOC `*-active.md` (`Disposição` +
trilha), fase de plano — e a segunda não tinha detector.

**Decisão (co-design `senior-cto` + `information-architect`):**

1. **Bucket `moc` em dois grãos.** Os 4 registros de skills pares
   ([[ADR-343]]: PIPELINE-REVIEWS, REPORT-REVIEWS, LEDGER-CERTIFY,
   PARSE-CERTIFY) entram como **linha de seção viva** — emissor puro de fatos
   locais (`disposicao`, `viva`, status/`ship_pr` da lane citada, lidos do
   frontmatter **sem rede**); seção com 0 linhas vivas é histórico congelado,
   fora até de `--full`. Navegacionais/fila (00-INDEX, PLANS-active,
   OWNER-GATED) entram no grão-arquivo (stride em
   `SAMPLE_STRIDE_BY_BUCKET`, que passa a ser a **fonte única** dos strides —
   esta ADR deixa de reenumerá-los).
2. **Exclusões com motivo.** `AUDITS-active` fica fora do universo julgado: a
   camada 5 escreve nele todo run e o hot set é `gate-fail ∪ changed` —
   auto-referência tornaria o critério "2 runs sem mudança → diff vazio"
   insatisfazível por construção. `SPRINTS-active` fora: sobrepõe o bucket
   `sprint` e a camada 2 da `lane-closeout` (finding duplicado cross-skill sem
   chave de dedup comum). `.claude/skills/` entra no bucket `claude` — a
   skill que audita registros fora do mapa estava, ela própria, fora do mapa.
3. **Fronteira com [[ADR-343]].** A auditoria julga **o registro** (estado da
   linha, forma da célula, integridade do ponteiro), **nunca o mérito do
   achado** — mérito é da cadência da skill dona, e o `--fix` não muda
   disposição de registro alheio (reporta "reconciliar"). O **detector
   primário** da linha-zumbi é a `lane-closeout` no merge (`citers_of`
   alargado para `docs/_MOC/*-active.md`); este bucket é rede de segurança
   com latência de rotação.
4. **Atestação, não housekeeping.** Flip `Proposto`→`Decidido` executado pela
   auditoria exige citação dupla "trecho da ADR + trecho do diff do SHA que
   implementa" (o escritor canônico do `status:` é o PR de implementação).

## Gatilho de reabertura

Estágio **dogfood** justifica cortar KR e cron. Ao cruzar para **beta** (docs
viram superfície para usuários), reabrir: cadência agendada, KR "% reference sem
DOC-BLOCK" e sweep amplo dos 5 agentes passam a ter ROI.

## Referências

- [[ADR-182]] — vault atômico (frontmatter + schemas).
- [[ADR-247]] — MD canônico, HTML derivado.
- [[ADR-081]] — padrão regex→LLM→needs_review (mesma filosofia de camadas).
- [AUDITS-active](../_MOC/AUDITS-active.md) — registro canônico de auditorias.
