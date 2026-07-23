---
name: parse-certify
description: >-
  Certifica a INGESTÃO (E0→E2) de UM workspace documento-a-documento —
  classificação → roteamento → parse → validação — caçando perda/corrupção
  silenciosa (artefato "ok" com dado parcial ou errado). Use SEMPRE que o dono
  pedir para "certificar/validar o parse dos documentos de um workspace", ver se
  a ingestão está perdendo dados, conferir se cada documento virou artefato
  correto, ou validar parse antes/depois de um fix de parser — mesmo sem a
  palavra "skill". NÃO roda o pipeline inteiro nem avalia o relatório final
  (isso é a skill pipeline-review). Recebe o workspace por email OU uuid.
---

# parse-certify

Procedimento do **loop principal** (não é um agente) para: rodar o caminho real
de ingestão E0→E2 sobre os documentos de um workspace, atribuir a **cada
documento** um veredito de completude, e produzir uma revisão priorizada
delegando aos especialistas do §Subagentes do CLAUDE.md, com verificação
adversarial.

É **análise, não implementação** — não altere parser nem abra PR de fix; o
entregável é diagnóstico + plano de ataque priorizado (candidatos a lane).
Envelopa o harness testado `dev/certify_parse_local.py`; deriva do processo que
certificou 3 corpora na Sprint A38.

**Fronteira vs [[pipeline-review]]:** aqui é a camada de **ingestão E0→E2,
documento-a-documento** (cada arquivo virou artefato correto?). O pipeline-review
roda o pipeline **inteiro** e critica o **relatório final E5→E7**. Perda de dado
no parse é aqui; número errado no relatório é lá.

Classe canônica (skill vs. subagente vs. prompt): [[ADR-302]] — 3ª instância da
classe, não exige ADR própria. Catálogo humano: `docs/reference/SKILLS.md`.
Rubrica de veredito por tipo: [`references/rubric.md`](references/rubric.md).

## Parâmetros

- **workspace** (obrigatório) — email (ex.: `5@5.com`) ou UUID.
- **grupo** (opcional, default `financial_statements`) — v1 certifica só
  `financial_statements`; os outros grupos de `data/` passam por outros stages
  (ver rubrica §Cobertura). Não force o harness sobre eles — mislabela.
- **baseline** (opcional) — snapshot para `--compare` (anti-regressão). Sem ele,
  o run é uma fotografia; com ele, um gate pass/fail.

## Ambiente

Rode do **checkout principal** (não um worktree) — os scripts importam `backend`
e leem `DATABASE_URL`/Fernet/`STORAGE_ROOT` do `.env`, e os documentos reais
vivem em `storage/<uuid>/data/` (gitignored). Precisa do venv do repo. **Não é
necessário worker Celery/Redis** — o harness roda E0→E2 síncrono e isolado, sem
disparar run.

**Pré-condição de cripto:** o harness lê os bytes de `storage/<uuid>/data/`. Se
os originais estiverem Fernet-encrypted em repouso, aponte-o para os originais
**destrancados** — senão o parse roda sobre lixo e produz falso-silêncio (rubrica
§Divergências).

## Procedimento

### Passo 1 — Resolver workspace + storage + inventário do DB

```bash
.venv/bin/python .claude/skills/parse-certify/scripts/resolve_workspace_dirs.py <workspace>
```

Retorna `workspace_id`, `groups` (grupo, `dir` absoluto, `n_files`, `in_scope_v1`)
e `db` (docs, needs_review, possible_duplicate, `doc_type_hist`). Guarde o
`workspace_id` e o `dir` do grupo alvo. `db` é o insumo do cross-check do Passo 3.

### Passo 2 — Rodar o harness por grupo (+ baseline/compare)

O harness é single-`--dir`; **itere** os grupos não-vazios no escopo. Para uma
fotografia:

```bash
python3 dev/certify_parse_local.py --dir <groups[*].dir>
```

Para congelar baseline (anti-regressão) ou comparar:

```bash
python3 dev/certify_parse_local.py --dir <dir> --baseline <baseline.json>
python3 dev/certify_parse_local.py --dir <dir> --compare  <baseline.json>
```

Saída = uma linha mascarada por doc: `type`, `inst`, `conf`, `parser`, `n_tx`,
`moeda`, `conserv`, `escala`, `status`. `--compare` retorna exit ≠ 0 em
regressão (`n_tx` menor, conservação passa→falha, parser perdido).

**Home do baseline:** `_scratch/` some entre sessões (efêmero) — para persistir
na máquina do dono use `storage/<uuid>/certify/` (durável, path proibido no git).

### Passo 3 — Cross-check harness ↔ DB (perda silenciosa vive aqui)

O harness diz o que **parsearia** isolado; o DB diz o que **persistiu** de fato.
A perda silenciosa mora na divergência. Reconcilie:

- **Por `content_hash`, nunca por contagem** — dedup faz o DB ter ≤ arquivos do
  dir (rubrica §Divergências).
- **Artefato vivo não-fallback** por `(ws, stage, artifact_key)` em
  `pipeline_artifacts` — stub (`requires_llm_fallback`, `transacoes:[]`) é
  `escalado-honesto`, não "vazio". Invariante: **≤1 vivo não-fallback por
  `(ws, stage, key)`** (um parcial de run anterior ressuscitado = falso-verde).

### Passo 4 — Atribuir veredito + delegar aos especialistas

Classifique cada doc em **um dos 5 vereditos** da [rubrica](references/rubric.md):
`completo` · `coberto-sem-verificação-de-soma` · `escalado-honesto` ·
`perda/corrupção silenciosa` · `não-coberto`. Regra de ouro: só sobe a
`completo` quem tem **checksum que prova o fechamento**; sem checksum, teto
`coberto-sem-verificação`.

Delegue o julgamento das lacunas (vereditos 2 e 4) em **paralelo** (1 mensagem, N
`Agent` calls), brief mínimo, pedindo **decisão/objeção com evidência**:

| Lacuna | Especialista |
|---|---|
| Contrato E2 (tipo/posicoes/transacoes/itens), checksum, conservação, needs_review, read-path | `data-engineer` |
| Materialidade de domínio (que dimensão do relatório o doc corrompe: fluxo, patrimônio, dolarização, renda) | `financial-planner` |
| Impasse de contrato/arquitetura (como um layout novo deve escalar) — decide e fecha | `senior-cto` |
| Lacuna no caminho E2-llm (só se cair no fallback LLM) | `prompt-engineer` |

### Passo 5 — Verificação adversarial

Cada candidato a `perda/corrupção silenciosa` passa por **1 verificador cético**
que tenta REFUTAR, re-derivando a evidência (re-rodar o harness, inspecionar o
artefato vivo, recomputar o checksum). Descarte os REFUTED. Este passo mata
"plausível mas errado" — foi ele que refutou hipóteses na certificação A38.

## Guardrails

- **Zero PII no entregável** — sem CPF, valores ou nomes reais. O harness já
  mascara; o baseline JSON **ainda pode vazar nome via filename** (`mask_text`
  não remove nome de pessoa) → nunca commite baseline; mantenha em `_scratch/`
  ou `storage/<uuid>/certify/` (ambos fora do git). Nome próprio como chave de
  dict é smell a **reportar, não reproduzir**.
- **Read-only** sobre o workspace — não reprocessa nem grava no DB. Não dispara
  run (isso é pipeline-review).
- **Evidência sempre** — `campo`/número/`arquivo:linha` mascarado. Hipótese não
  verificada não vira bug.

## Entregável

Salve em `_scratch/parse-certify-<slug>-<AAAA-MM-DD>.md` e resuma no chat.
Estrutura: **premissas → cobertura (grupos rodados, n docs) → TABELA DE VEREDITO
POR DOCUMENTO → achados priorizados → próximos passos**, com critério de aceite.

Tabela de veredito (mascarada), colunas:
`Doc (type+inst+período) · Classificado? · Parser · n_tx/n_itens/n_posições ·
Conservação/Checksum · Veredito · Lacuna`

Achados priorizados (silêncio primeiro), colunas:
`ID · Achado · Severidade · Prioridade (P0–P3) · Dificuldade (S/M/L) · Risco
regr. · Fix recomendado · Candidata a lane`

## Extensões do harness (candidatas a lane — o backlog que a skill produz)

O harness atual não emite tudo que o veredito de 5 estados exige; onde falta, a
skill degrada honestamente para `coberto-sem-verificação`. Cada gap é uma lane:

1. **Emitir por tipo:** `tipo`, `n_itens`, `n_posicoes`, `raw_rows_detected`,
   `escalation_reason.code`, `conservacao_verificavel` (hoje só `transacoes` e
   `conservacao` float).
2. **Checksum de fatura** Σ itens × `total_fatura` em `validate_fatura_result`
   (hoje só trata 0-lançamentos).
3. **Checksum de investimento** `_apply_cdb_checksum` em CDB XLSX/HTML-XLS Itaú
   (hoje só Santander CDB PDF).
4. **Conservação em cents** — reusar `conservation_gap_cents` (tol-zero) em vez
   do float `<0.011`, para o veredito bater com o gate de produção.
5. **`--compare` mais forte:** falhar em `escalated True→False` sem checksum-pass
   (silêncio reintroduzido — a pior regressão), checksum pass→fail, e queda do
   piso de cobertura determinística.
6. **Chave de baseline PII-safe** `doc_type|institution|period|sha256[:8]`
   (dropa o filename legível) + `--compare` que erra limpo sem baseline (hoje
   crasha exit 1 se o arquivo sumiu).

## Critério de aceite da skill

Grupo(s) no escopo rodados + todo doc com um dos 5 vereditos + `completo` só com
checksum que fecha (nunca "parseou e não escalou") + cross-check por
`content_hash` + zero PII vazada + candidatos a silêncio sobreviventes à
verificação adversarial.

## Armadilhas (aprendidas na certificação A38)

- **Falso-verde é o inimigo** — tratar `n_tx>0 & !escalated` como `completo`
  certifica parcial silencioso. Sem checksum, teto é `coberto-sem-verificação`.
- **Escalar não é falhar** — `requires_llm_fallback`/`needs_review` por 0 tx ou
  conservação quebrada é o comportamento **correto** (ADR-342). Não conte como bug.
- **Grupo errado** — rodar `income_tax_br`/`real_estate`/`vehicles` no harness E2
  os marca falso `não-coberto` (são cobertos por outros stages). Fique em
  `financial_statements` no v1.
- **Cripto em repouso** — parse sobre bytes encriptados = falso-silêncio.
  Confirme originais legíveis antes de concluir.
- **Checkout errado** — o DB default e o `STORAGE_ROOT` seguem o `_PROJECT_ROOT`
  do pacote `backend` de **onde o script roda** (sys.path). Rodar a cópia de um
  worktree resolve para o `mathoms.db`/`storage/` **vazios** do worktree (DB sem
  tabelas ou 0 files) — sintoma: `no such table` ou `n_files=0` em tudo. Rode do
  **checkout principal** (verificado: resolve `5@5.com` → 160 docs).
