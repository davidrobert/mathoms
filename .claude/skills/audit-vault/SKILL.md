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
  `prompt` · `sprint` · `root` · `moc`.
- `moc` (emenda 2026-08-21 da [[ADR-302]]) cobre os MOCs em **dois grãos**: os
  4 registros com máquina de estado de skills pares ([[ADR-343]] —
  PIPELINE-REVIEWS/REPORT-REVIEWS/LEDGER-CERTIFY/PARSE-CERTIFY) entram como
  **linha de seção viva** (o coletor resolve `status:`/`ship_pr:` da lane
  citada localmente; quem decide "é zumbi" é a camada 3); OWNER-GATED, PLANS e
  00-INDEX entram no grão-arquivo normal. `AUDITS-active` fica **fora do
  universo julgado** (a camada 5 escreve nele todo run — auto-referência
  sujaria o hot set para sempre; a camada 0 continua lendo a última seção) e
  `SPRINTS-active` também (sobrepõe o bucket `sprint` e a camada 2 da
  lane-closeout). O **detector primário** da linha-zumbi é a `lane-closeout`
  no merge (`citers_of` inclui `docs/_MOC/*-active.md`); este bucket é a rede
  de segurança, com latência de rotação. Receitas e limites: checklist §6.
- `--mode` = `comprehensive` (default: todos os buckets vivos, 5 dimensões) ·
  `focused` (só o `--scope` dado, dimensão dominante).
- `--full` = sweep 100% do universo do `--scope` (repassa `--full` ao coletor).
  **Modo de evento** — baseline inicial, pós-refactor estrutural, gate
  dogfood→beta ([[ADR-302]] §Gatilho) — nunca cadência recorrente. Custo ≈17k
  tokens de julgamento/arquivo (empírico r5); rode **1 bucket por sessão/PR**
  (`--scope reference --full` primeiro) para a triagem caber em <30min por fase.
  Sequência completa das 3 fases + gates de decisão:
  [`docs/reference/runbooks/vault_full_audit.md`](../../../docs/reference/runbooks/vault_full_audit.md).
- `--scope all --full` = **sweep one-shot** (um comando audita TUDO — ~409
  arquivos, ~7M tokens). Contrato de execução obrigatório: **fasear
  internamente na mesma sessão** — Fase 1 `reference` → Fase 2
  `plan`+`sprint`+`claude`+`prompt`+`root`+`moc` → Fase 3 `adr` em 4-5 sub-lotes
  (`Proposto`/`Roadmap` primeiro) — fechando **1 PR docs-only + 1 subseção rN
  no AUDITS-active por fase ANTES de iniciar a seguinte**. Isso preserva
  triagem <30min/pacote e dá checkpoint (interrupção retoma da fase seguinte,
  não do zero). O gate de custo pré-Fase 3 do runbook vira **informativo**
  (invocar one-shot = owner já decidiu pagar o sweep inteiro): registre a taxa
  de findings das fases 1-2 na subseção da Fase 3 em vez de parar. **Nunca**
  consolide tudo num relatório/PR único.
- `--fix` = após a triagem de cada fase/run, **executa** o batch de DOC-DRIFT
  em vez de só propor a lane P2 (precedente: batch r4, ordem do owner
  2026-07-02). Três garantias invioláveis: (a) **item que exige decisão do
  owner nunca é auto-resolvido** — status estagnado dependente de evento
  externo, priorização/escopo de produto, arquivamento com cascade de links →
  fica `procede-aberto` com a pergunta explícita na tabela rN; (b) todo DRIFT
  só é editado com **citação dupla** (trecho do doc + trecho da
  fonte-de-verdade), o mesmo verify que a camada 4 exige de DOC-BLOCK —
  sem ambos, não edita; (c) DOC-POLISH continua wontfix (não entra no `--fix`);
  (d) correção que refuta/supersede **prescrição viva em linha de registro**
  edita **a própria célula** — forma canônica no checklist §6; nota datada
  abaixo da tabela sozinha não vale (quem lê a tabela antes da nota executa a
  prescrição morta); (e) flip de ADR `Proposto`→`Decidido` executado pela
  auditoria é **atestação**, não housekeeping: a citação dupla de (b) vira
  "trecho da ADR + trecho do diff do **SHA que implementa**" — se a ADR
  precisa de edição além do `status:`, não é flip, é `procede-aberto` com o
  SHA nomeado; (f) o `--fix` **nunca muda disposição** de linha de registro:
  em registro de skill par ([[ADR-343]]), reporta "trilha aponta lane
  `shipped` — reconciliar" e o flip fica com a cadência da skill dona; no
  próprio `AUDITS-active`, mudança de disposição é da cadência anti-zumbi
  (camadas 0/5), nunca do batch. Cada batch sai em **PR docs-only próprio**,
  separado do PR de síntese da fase, para manter o diff revisável.

`archive/` e sprint fechada ficam **sempre fora** do julgamento (gates ainda
rodam via pre-commit) — auditar histórico congelado gera falso-drift.

## Procedimento (6 camadas)

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
python3 dev/check_adr_amendment_signal.py
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
rotativa ∪ linhas de registro`: cada arquivo tem classe permanente
`sha1(path) % stride` e o `--run` rotaciona a classe-alvo — 100% do bucket é
julgado a cada `stride` runs. Fonte única dos strides:
`SAMPLE_STRIDE_BY_BUCKET` no próprio coletor (denso onde o sentido muda toda
sprint; não reenumere em prosa). As linhas de registro (`moc-linhas` no JSON)
saem **todo run**, fora da rotação — são compactas e o estado muda por evento
externo ao arquivo. Sem `--run`, a amostra repete a classe 0 (o bug F17/r5).
Reproduzível: `--self-test` prova que o mesmo `--run` dá o mesmo conjunto, que
a rotação cobre o universo E que o parser de linha extrai o esperado de uma
fixture sintética. Para sweep 100%, repasse `--full` (ver §Parâmetros; para
linhas de registro, `--full` significa "todas as linhas de seção **viva**" —
seção congelada nunca entra); o JSON de saída traz `buckets` com
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

Candidatos `moc-linhas` julgam **o registro, nunca o mérito do achado**
(fronteira [[ADR-343]]): estado da linha vs. `lanes`/`prs` já resolvidos pelo
coletor, forma da célula, integridade do ponteiro. "O achado de fato fechou?"
é da cadência da skill dona. Receitas: checklist §6.

### Camada 4 — Verify (só severidade ≥ DOC-BLOCK)

Cada `DOC-BLOCK` passa por **1 verify barato**: cite o trecho exato do doc **e**
o da fonte-de-verdade (código/ADR/config) que se contradizem. **Sem citar
ambos → rebaixa para DOC-DRIFT/descarta.** Nunca auto-marque `refutado` sem
evidência empírica (lição SEC-03 do AUDITS-active).

### Camada 4b — Auditoria dos mortos (o verify do verify)

A camada 4 **mata** achados. Ninguém checa a morte, e a assimetria é silenciosa:
o achado que sobrevive ganha escrutínio de graça — você age sobre ele, e agir
revela erro. O achado morto não ganha nenhum. Refutação errada apaga defeito real
e o resultado fica **idêntico** a sucesso.

**Audite os mortos, não os sobreviventes.** O conjunto é pequeno e limitado por
construção (na rodada de origem: 4 mortos contra 45 vivos), então a camada custa
quase nada. A pergunta é **invertida** — não "o achado procede?", mas **"esta
refutação é boa?"** —, e o refutador da camada 4 é quem está no banco dos réus.

**Testemunha mecânica ou nada.** `morte-correta`/`morte-errada` exigem um comando
reproduzível (`grep`/`git`/`pytest`) cujo output decide, colado com o output.
Sem isso o veredito é `indeterminado`, que é resposta legítima e melhor que
prosa: prosa-contra-prosa é exatamente o que já falhou uma camada antes.

**O que NÃO fazer: a camada simétrica.** Não acrescente "refute a refutação" como
terceira passada sobre os achados vivos. O refutador empurra sempre **contra** a
afirmação corrente, sem saber qual direção é segura — quando o default seguro é
*não agir* (não flipar uma ADR, não reescrever evidência datada), ele empurra
para o lado inseguro. E erro de LLM lendo texto é correlacionado entre camadas:
não se cancela por empilhamento. Orçamento marginal rende mais em **lente nova**
(outro artefato-alvo) que em profundidade.

> **Caso de origem (2026-08-30, closeout da `A40.l94`).** Dois céticos deram
> veredito **oposto** sobre a mesma substância: um confirmou, outro refutou. Agi
> sobre o confirmado e **risquei uma frase verdadeira** — "uma aplicação, dois
> pontos", que era literalmente correta sobre o separador que nomeava
> (`transfer_categories` aplicado em `fluxo_caixa_enricher.py:510`, ausente em
> `_collect_candidates`). O risco falso foi para `main` num PR de closeout cujo
> objetivo era justamente consertar afirmações falsas.

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
  Exceção: com `--fix` (ver §Parâmetros), o batch é executado no próprio run,
  com as 3 garantias de lá (decisão-do-owner fica aberta; citação dupla
  obrigatória; POLISH fora).
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
