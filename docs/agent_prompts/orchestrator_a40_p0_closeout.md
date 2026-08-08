# Orquestrador — Sprint A40 "Report trust": fechamento das 3 P0 pegáveis

> **Escopo:** [[A40.l2]] (restante) + [[A40.l20]] (restante) + [[A40.l22]].
> **Estado em 2026-08-08: resta a Frente C.** A **A** foi consumida pelo #1276
> (`b3b8a74b`) e a **B** pelo #1278 (`039c1b6d`); as duas §§ ficam como registro
> datado, com os vereditos in-loco. Da [[A40.l2]] seguem abertos 3c1 · 3c2 · 3d
> (destravado) · 3e.
> **Criado:** 2026-08-07, contra `main @ 2571f203`. Os números de linha citados
> abaixo foram **reverificados** nesse commit — se `main` andou, reverifique-os
> antes de confiar (o mecanismo continua válido; o endereço, não necessariamente).
> **Uso:** cole o bloco inteiro no início da sessão, ou a §Frente que for pegar.
> Cada frente é **1 branch, 1 PR, 1 agente**. Nunca funda duas frentes num PR.

---

## 0. Comando de arranque (cole isto numa sessão nova)

Uma frente por sessão. Troque **`<FRENTE>`** por `A`, `B` ou `C`:

```
Leia docs/agent_prompts/orchestrator_a40_p0_closeout.md e execute a Frente <FRENTE>.

Regras: rode o §1 antes de qualquer edição — inclusive os 2 checks de pickup e a
reverificação dos números de linha citados (main anda várias vezes por dia).
O prompt é roteador; a lane em docs/sprint/A40/lanes/ é fonte de verdade, e onde
divergirem, a lane vence — me avise da divergência em 1 linha.
Se a §"medir antes de editar" da sua frente existir, o resultado da medição entra
no PR mesmo que confirme o esperado.
Não funda frentes: 1 branch, 1 PR. Pare e me pergunte se o escopo crescer para
fora da §Aceite da frente.
```

- ✅ **Frente A** = [[A40.l2]], restante do PR3b — **consumida** (#1276, `b3b8a74b`)
- ✅ **Frente B** = [[A40.l20]] PR2 — **consumida** (#1278, `039c1b6d`)
- ⬜ **Frente C** = [[A40.l22]] (frontend + PDF; bloqueador do beta) — **a única pegável**

As três rodam em paralelo em worktrees separados:

```bash
git worktree add ../mathoms-a40-l2 -b agent/a40-l2-3b/$(date +%Y%m%d-%H%M) origin/main
```

## 1. Antes de qualquer coisa

```bash
git fetch origin && git status && git worktree list
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' refs/remotes/origin/agent/ | head -15
```

Se `origin/agent/a40-l2-*`, `a40-l20-*` ou `a40-l22-*` tem commit <24h, **a frente
está tomada** — pegue outra. Crie a branch **antes da primeira edição**:
`agent/<slug>/<yyyyMMdd-HHmm>`.

Leia, nesta ordem, e **não confie neste prompt contra a lane**: a lane é fonte de
verdade, este arquivo é roteador + estado medido.

1. A lane da sua frente em `docs/sprint/A40/lanes/`.
2. `docs/sprint/A40/_README.md` §Gate de saída e §Predicado do campo `status`.
3. As ADRs citadas na frente.

---

## 2. Por que estas três, e por que agora

As três são **P0** e as únicas P0 pegáveis da A40. Estado em 2026-08-07:

- **[[A40.l18]] shipou** (PR1 `4620cc04`/#1242 + PR2 `b8460274`/#1258). Isso
  satisfez a dependência da [[A40.l20]] **hoje**.
- **O PR1 da [[A40.l20]]** mergeou em 06/08 (`0301f7a0`/#1250) — que é o gatilho
  declarado da [[A40.l22]] (*"Não espera o PR2"*, topo da lane).
- **A [[A40.l2]] dita o ritmo da sprint inteira:** pela cláusula de 06/08 do
  §Gate de saída, o contador de 2 re-runs consecutivos **só inicia quando a l2
  estiver terminal**. Nenhuma outra lane muda essa data.

> ✅ **Frontmatter corrigido em 2026-08-07** (PR docs-only): `A40.l18` → `shipped`,
> `A40.l22` → `open`. Durante ~1 dia as duas mentiram em sentidos opostos e as
> duas eram P0 — registro em `_README` §Predicado, Delta 2026-08-07. Se você
> encontrar divergência nova entre `status` e `origin/main`, é o mesmo defeito
> (flip manual sem gate), não um caso novo.

**Contexto de 2026-08-07, tarde:** [[A40.l30]], [[A40.l27]] e [[A40.l28]] shipparam
em sequência (#1260-#1270, com a [[ADR-368]] e a [[ADR-369]]). São **P1** e não
tocam nenhuma das três frentes abaixo — mas mudam a fila do nível 1: sobram
[[A40.l10]] PR3, [[A40.l32]] e [[A40.l25]]. E a [[A40.l8]], que a l30 gateava,
está liberada.

**Paralelismo:** as três tocam árvores disjuntas (E3/backend-ops · orquestrador ·
frontend+PDF). Rodam em paralelo sem merge-hell. **Ordem, se houver 1 slot só:**
l2 → l20 → l22.

> **Delta 2026-08-08.** O paralelismo se resolveu sem conflito: A e B mergearam no
> mesmo dia (`b3b8a74b`, `039c1b6d`) e o rebase da B sobre a A foi limpo. Resta a C.

---

## 3. Regras que valem nas três frentes

- **CLAUDE.md manda**, sempre. Branch `agent/*`, Conventional Commits, squash,
  sem `--no-verify`, sem push em `main`, sem `--admin`.
- **Commit antes de devolver o turno**, mesmo WIP. Este worktree já perdeu edits
  entre turnos.
- **Gate local antes do push** (não confie no CI):
  `pre-commit run --all-files` + `pytest backend/tests -q` + `pytest tests -q`
  (+ `cd frontend && npm test -- --run` se tocou frontend). A suíte backend roda
  **da raiz do repo** — `cd backend` dá falha falsa.
- **Prova por mutação, não por nome.** Todo critério de aceite abaixo pede um
  teste que **fica vermelho** quando o mecanismo é removido. Teste que nomeia o
  mecanismo sem exercitá-lo é falso-verde, e esta sprint já pagou por três.
- **A mutação tem de ser plausível** — a que um refactor faria (rename, inline,
  early return), não `raise Exception()` no topo da função.
- **Instrumento delega ao domínio.** Se `dev/*` recomputa o que
  `pipeline/domain/` já calcula, o instrumento prova a si mesmo. Direção da
  dependência é `dev/` → domínio, nunca a inversa.
- **Não peça código a especialista** — peça decisão. Co-design **antes** de
  codar, 1 rodada de objeção, `senior-cto` fecha se persistir.
- **ADR:** nunca reserve ID citando em prosa. Aloque na escrita (`ls docs/adr/ |
  tail`) e refetch se a sessão for longa.

---

## 4. Frente A — [[A40.l2]], restante do PR3b (o gate da pré-condição)

**Branch:** `agent/a40-l2-3b/<ts>` · **P0** · a mais longa das três.

> ✅ **CONSUMIDA em 2026-08-07** — PR [#1276](https://github.com/davidrobert/mathoms/pull/1276),
> commit-merge `b3b8a74b`, CI verde. **Não pegue esta frente.** O diagnóstico abaixo fica como
> registro do que foi medido; os 5 itens da lista estão **todos corrigidos**, e um agente que
> os tratar como pendentes vai procurar defeito que não existe mais. Estado corrente e
> followups: §Ordem de trabalho e §Guarda anti-regressão da [[A40.l2]], e §Emenda de
> 2026-08-07 da [[ADR-364]]. **Aberto em seguida:** 3c1 · 3c2 (brief pronto em
> `docs/sprint/A40/tracks/a40-l2-3c2-superficie-do-colapso.md`) · 3d (**destravado** — dependia
> do 3b) · 3e.

### Estado medido em `main @ 2571f203` (não re-derive)

| Sub-PR | Estado |
|---|---|
| 3a — a sombra | ✅ #1231 (`65464db6`) + follow-ups #1236, #1239 |
| 3b1 — fonte única do digest | ✅ #1251 (`077fb7e9`) — `_gate_digest_da_chave` chama `gate_key_digest`, nunca inline |
| 3b2 — `CollapseMeasurement` | ✅ #1256 (`4fdcf400`) — `corpus_gate_digests`, `corpus_row_hashes`, `survivor_hash` |
| **3b restante** | ✅ **#1276 (`b3b8a74b`)** — era "o seu PR" quando isto foi escrito |
| 3c1/3c2/3d/3e | ⬜ depois; **3d destravado** pelo merge do 3b |

**~~O que ainda está no arquivo~~ — os 5 estavam no arquivo em `2571f203` e foram
CORRIGIDOS no #1276.** Preservados porque são o diagnóstico que justificou o desenho, em
[`backend/app/services/internal_ops/collapse_precondition.py`](../../backend/app/services/internal_ops/collapse_precondition.py):

1. **`liberado` (linha 61) é `hits == 0 and sem_snapshot == 0`** — o predicado que
   o painel julgou **inalcançável por construção**: `gate_digest` é
   `(data, cents, moeda, descricao_norm)`, as duas pernas o compartilham **por
   definição de candidato**, e re-ancorar não muda nenhum dos quatro ⇒ o override
   segue hit para sempre.
2. **`_alvos` (linha 128) é fail-open** — `getattr(c, "collapsible", False)` /
   `getattr(c, "gate_digest", "")`: qualquer rename ⇒ `alvos = ∅` ⇒
   `liberado=True` **em silêncio**.
3. **`evaluate()` (linha 151) tem `corpus_digests=frozenset()` por default** —
   chamador que esquece o argumento certifica vivacidade vazia.
4. **`tx_data_nao_iso` é medido e não impede nada** — override com
   `tx_data="30/03/2026"` conta em `com_snapshot`, nunca casa nada, e sai
   `liberado`.
5. **Não existe chamador de produção.** `rg -n collapse_precondition --glob '*.py'`
   devolve **só testes**. A "chamada no composition root do stage" do escopo do 3b
   não foi feita.

**Como cada um foi fechado no #1276** (para quem chegar aqui pelo histórico):
1 e 4 → predicado cumulativo de 5 cláusulas (`medido` · `hits` · `sem_snapshot` ·
`tx_data_nao_iso` · vivacidade **universal**), derivado de `clausulas_reprovadas()` como fonte
única, com a adjudicação por `survivor_hash` que torna o gate alcançável · 2 → acesso por
atributo, `AttributeError` alto · 3 → `corpus_digests` obrigatório · 5 → chamada em
`main_with_store`, relatório em `pipeline_stage_logs.output_summary`. **9 provas de mutação**,
todas vermelhas. **Ainda não medido, e agora pagando em produção:** custo do gate por run
(ver [[A40.l2]] §"predicado FECHADO no PR3b; sobra o custo").

### O que o 3b entrega

- **Adjudicação por hash** (descoberta continua por digest — as duas razões do
  docstring seguem válidas; o digest é invariante sob re-ancoragem, o hash não).
  `survivor_hash` e `corpus_row_hashes` já existem no produtor desde o 3b2.
- **Predicado corrigido**, cumulativo: `medido is True` · `hits == 0` ·
  `sem_snapshot == 0` · `tx_data_nao_iso == 0` · **vivacidade UNIVERSAL**
  (`snapshot_casa_corpus == com_snapshot`, nunca `> 0`).
- **`_alvos` fail-loud** — acesso por atributo, `AttributeError` alto (precedente
  [[ADR-359]]).
- **`evaluate()` sem default** em `corpus_digests`.
- **Chamada no composition root do stage** + relatório em
  `pipeline_stage_logs.output_summary`. **Não** em `AuditRecord`: `append_audit`
  é `db.add` **sem commit** e o loop do `pipeline_task` faz rollback em
  `not result.success` ⇒ a série nasceria com os vermelhos apagados.
  `internal_ops_audit` recebe **uma** row quando o operador flippa a flag.
- Comentário stale de `_targets` · **emenda datada** na [[ADR-364]] e na §D1 da
  lane (emenda exige `amended_at` no frontmatter + blockquote de sinal, senão o
  gate dá verde falso).

### Aceite — e os três falsos-verdes a evitar

- **A escapatória (`natural_key_hash == survivor_hash ⇒ seguro`) é exercitada por
  ZERO overrides no dogfood.** Medido em 06/08: 5 overrides ativos, 4
  `casou_corpus_fora_de_candidato`, 1 `casou_nada`, **0** em candidato. As travas
  1 e 2 do predicado têm de vir de **fixture sintética**, e o PR tem de **dizer
  isso** — senão alguém lê "verde no dogfood" como prova da escapatória.
- **A vivacidade universal reprova hoje (4 ≠ 5), e essa é a polaridade certa.**
  O 1 que não casa nada é exatamente o override que o gate não sabe julgar.
- **`test_collapse_precondition.py` constrói o `gate_digest` da fixture chamando
  `gate_key_digest`** — produtor == consumidor sob teste. O teste de derivação
  tem de ser alimentado pelos **dois produtores reais**
  (`test_gate_digest_paired_derivation.py` é o precedente).
- **Re-rode `dev/probe_collapse_adjudication.py`** antes de fechar o desenho —
  "vazio" é propriedade do corpus **e do tempo**. O probe recusa emitir veredito
  com corpus ou overrides vazios (`INDETERMINADO`, exit 2); **não contorne o
  guard**: a primeira execução dele imprimiu "adjudicação MORTA" com `corpus=0` e
  teria matado um desenho correto.
- **Não afrouxe `liberado` sob pressão de entrega.** É a trave movida
  retroativamente, e é o incentivo nomeado na própria lane.

### Guardas que **não** podem ser deletadas

`test_collapse_shadow.py::test_stage_de_producao_nunca_liga_o_enforce` (AST no
call-site) e `test_collapse_layer.py::test_instrumento_delega_ao_shadow_counts_do_dominio`.
O 3e **estreita** a primeira; **deletá-la é o atalho que o PR do flip tem
incentivo a tomar**.

### Fim da frente A

3b é **100% read-only** e vem primeiro porque o 3d consome a classificação que
ele define. Ao mergear, **abra o brief do 3c2 junto** — ele é o long pole real
(frontend + snapshot + brief), não o 3d.

---

## 5. Frente B — [[A40.l20]] PR2 (wire-up no orquestrador)

**Branch:** `agent/a40-l20-pr2/<ts>` · **P0** · a menor das três.

> ✅ **CONSUMIDA em 2026-08-07** — PR [#1278](https://github.com/davidrobert/mathoms/pull/1278),
> commit-merge `039c1b6d`, checks required verdes. **Não pegue esta frente.** O diagnóstico
> abaixo fica como registro do que foi medido **antes** da execução — e a execução **refutou
> duas linhas dele**, marcadas in-loco. Estado corrente: §Estado — PR2 entregue da
> [[A40.l20]] (`shipped`), [[ADR-366]] e [[ADR-357]] `Decidido` com emenda datada.
> **Os endereços de linha desta seção morreram** (o próprio PR moveu a função): re-derive
> com `rg -n`, nunca confie no número.

### ~~🔴 são **4+ portas, não 3**~~ — medido: **3 portas reais, e só UMA barrava**

> **Corrigido pela execução (2026-08-07).** O heading e o parágrafo abaixo estavam errados
> em duas frentes, e é o tipo de erro que esta sprint persegue: a lane apontava a função
> errada, e este prompt somou uma porta que não existe. **Preservados porque foram o
> diagnóstico que justificou o desenho**, com o veredito ao lado de cada linha.

A lane mediu em 06/08 *"são 3 guards independentes, não 1"* e nomeou os 3 dentro
de `_should_persist_planner_review`. **Medi hoje e há pelo menos mais uma, acima
delas** — e ela é a que o PR2 tem de abrir primeiro, senão o diff fica verde e o
runtime morto (a mesma classe de defeito que a lane já nomeia, uma camada acima):

| # | Porta | Veredito da execução |
|---|---|---|
| 0a | `if outcome.delivered:` — o **call site** só chama o persist quando o stage entregou. Stage **degradado** ⇒ `delivered=False` ⇒ persist **nunca chamado** | ✅ **certa, e era a ÚNICA barreira real.** Todo o corpo de `_should_persist_planner_review` era dead code neste caminho |
| 0b | O ramo `needs_review` desvia para `_record_stage_needs_review`, que **não chama o persist** | ❌ **REFUTADA — não está no caminho.** A guarda é `if result.success and _has_validation_errors(...)`; o `and` curto-circuita em `success=False`, e o stage do parecer **nunca emite bloco `validation`**. Varridos resume / redelivery / retry / `from_stage` / cancel / exceção: nenhuma rota chega lá |
| 1 | `not result.success` | ⚠️ contrafactual — barraria **se** a 0a fosse aberta sozinha. Deletada |
| 2 | `detail["skipped"] or detail["status"] == "needs_review"` | ⚠️ idem, **na metade `needs_review`**. A metade `skipped` **fica** (é ausência: free / sem chave / flag off / sem E5) |
| 3 | `"persona_hash" in result.detail` | ❌ **REFUTADA — já não barrava.** O PR1 pôs `_audit_detail` no retorno do retido. Fica, mas o que ela fecha é a **rota de exceção**, cujo detail não tem auditoria alguma |

**Sinal de que o PR1 já preparou o andar de baixo:** `planner_review_persistence`
tem `_derive_outcome` com `ParecerOutcome.retido` e a guarda
`detail.get("status") != "needs_review" or bool(detail.get("retention_reason"))`.
Ou seja, a persistência **já aceita** needs_review-com-motivo; quem não a alcança
é o orquestrador. ✅ Confirmado — e por isso o filtro do orquestrador **não**
duplica essa regra: quem decide indisponibilidade é o domínio.

### ~~Passo 1 — medir antes de editar~~ ✅ **CUMPRIDA — o resultado está no PR**

O desfecho retido chega **só por `degraded`**, nunca por `needs_review`: os cinco
produtores de `_needs_review` convergem num retorno com `success: False`, e o
registry declara o parecer `degradable`. A dúvida original ("por um, por outro, ou
pelos dois?") tinha resposta única.

### ~~Aceite~~ ✅ cumprido — o que a execução acrescentou

- ✅ Row de `PlannerReview` com `outcome` de retenção pelo caminho real do run.
- ✅ **7 mutações executadas, não argumentadas.** "Cada porta" = as 3 reais; a 0b
  não ganha teste porque não tem código. **A guarda `skipped` sobreviveu à 1ª
  rodada** — era mascarada por `persona_hash`, logo indistinguível de código
  morto — e o teste foi reescrito até matá-la.
- ✅ `retention_reason` segue argumento do construtor; nenhuma resposta de
  `/planner-review` vaza `error_detail` cru.
- ✅ **Flip da [[ADR-366]]**, mais o da [[ADR-357]] (decisão do dono: estava
  `Proposto` com a condição já cumprida pelo writer da [[A40.l18]]).
- ➕ **Escopo ampliado por decisão do dono**, porque o flip deixaria a ADR
  descrevendo código inexistente: `generation_unavailable` (§D6, discriminado pelo
  **artifact** — o produtor o grava mesmo nos ramos de indisponibilidade) e o
  **gate de paridade** dos 4 vocabulários (`test_parecer_vocabulary_parity.py`).
  Duas correções ao texto da ADR, na emenda: o §D6 omitia `parecer_artifact_missing`,
  que o router já produzia; e copiar o gate da [[A40.l18]] tal-e-qual dá
  verde-falso (o extrator dele usa `[a-z_]+`, que não casa o ponto de
  `parecer.sigilo`).

### Não é escopo (nomeado, não corrigido)

`check_orphan_planner_artifacts` é falso-verde (casa `stage == "E6-parecer"` sem
`stage_aliases`) · `output_summary` de `stage_logs` expõe prosa crua por outro
endpoint · `riscos_truncados` é 4ª subtração silenciosa (cap ≤12) · free tier cai
na mesma copy que mente → **destino [[A40.l22]]**.

➕ **Follow-up NOVO criado por este PR** — a **copy da UI para
`generation_unavailable`**. O servidor discrimina e o hook `usePlannerReview`
**transporta** o código (o estado `not_generated` ganhou `code:
PlannerReviewAbsenceCode`, 4 valores); escolher a palavra por código é
**[[A40.l22]]**, junto com o caso free tier, que é a outra metade da mesma mentira.

---

## 6. Frente C — [[A40.l22]] (superfície de degradação, inclusive PDF)

**Branch:** `agent/a40-l22-superficie-degradacao/<ts>` · **P0** ·
**bloqueador de fato do beta** (6ª classe do §Gate de saída).

### ~~Primeira ação: flipe o `status`~~ — já feito; flipe para `in_progress` no pickup

~~A lane está `blocked`~~ — **corrigido em 2026-08-07 pelo #1272**: está `open`, e
a dependência ficou **terminal** em 07/08 com o merge do PR2 da [[A40.l20]]
(#1278), então o `open` deixou de se apoiar na 2ª cláusula do §Predicado. No
pickup, flipe para `in_progress`.

### O que a Frente C herdou das outras duas (medido, não suposto)

- ➕ **A copy por código de ausência.** O 404 do parecer agora discrimina 4
  códigos (`report_not_found` · `not_generated_yet` · `generation_unavailable` ·
  `parecer_artifact_missing`), tipados no OpenAPI, e o `usePlannerReview`
  **transporta** o `code` no estado `not_generated` — sem escolher palavra. Escolher
  é seu, junto com o caso **free tier**, que é a outra metade da mesma mentira.
- ➕ **O estado `retained` e os contadores** já existem desde o PR1 da l20; o PR2
  deu **produtor** ao `outcome == "retido"`, então a seção passa a receber o
  estado de runs reais, não só de fixture.
- ⚠️ **Gate de paridade novo:** `backend/tests/test_parecer_vocabulary_parity.py`
  lê `frontend/src/lib/api/planner-review.ts` como texto. Membro novo em qualquer
  vocabulário (incl. `PlannerReviewAbsenceCode`) sem as outras cópias fica
  vermelho — atenção ao mexer nos tipos do cliente.

### Decisões já cravadas (não reabrir)

- **Sinal proporcional à invisibilidade, não à gravidade.** "Retido inteiro" é
  auto-evidente e **não** ganha linha no banner; "parcial" é indetectável e ganha.
- **Zero banner novo.** Existem 4 (`ReportDataQualityBanner`,
  `DefasagemWarningBanner`, `AcumuladoresBanner`, `MonthClosedBanner`); reusar o
  `ReportDataQualityBanner` (A28.l9) é a decisão, e o argumento é a **enumeração**,
  não um ordinal.
- **Título do banner: "precisão" → "leitura"** — item retido afeta completude, não
  precisão, e "leitura" é palavra que o próprio componente já usa.
- **Caption do parcial** estende o idioma de `ParecerRisksTable`, mantendo os dois
  contadores **semanticamente separados**: retido = qualidade → reprocessar;
  gated = comercial → comprar.
- **O PDF é a superfície de maior valor** — é a única que sai do produto e chega a
  terceiros que não podem perguntar. Nota em **texto no DOM**, `<details>` forçado
  `[open]` (padrão de `SParecer.print.css`). Nunca `title=`/hover: falha 1.4.13 e
  some no PDF.

### Aceite

- Os 2 estados novos renderizam; **nenhum** contém `error_detail` cru, `risco[N]`,
  `number_in_prose`, `whitelist_miss`, `stage`, `E5` ou `E6`.
- Sinal assertado em **4 superfícies**: seção · banner · `/pipeline` · **PDF via
  `pdftotext`**.
- `S_parecer` nos estados novos entra em `STRATEGIC_SECTIONS` do
  `a11y.@critical.spec.ts`; axe-core 0 critical/serious, **light e dark**.
- `<md`: nota vira linha própria; caption com 3 contadores não estoura.
- **Rebaseline explícito** dos snapshots visuais (light+dark × estados novos) — o
  job visual não é bloqueante, então **não pode ficar para o próximo agente**.
  > **Medido em 2026-08-07/08 e vale para 2 critérios seus:** o job
  > `Frontend E2E (Playwright + backend real)` também **não gateia** — é opt-in
  > pelo label `e2e` (`ci.yml`, job `frontend-e2e`) **e não entra** no
  > `All checks green`. Ou seja, o PDF via `pdftotext` e o `a11y.@critical` só
  > rodam se você puser o label, e mesmo vermelhos não seguram o merge. Adicionar
  > o label **não re-dispara** o run — precisa de push novo. O smoke do parecer,
  > que se auto-pulava, foi consertado no #1281; o job continuar não-bloqueante
  > **não** foi corrigido e não tem dono.
  View-model novo ⇒ `MATHOMS_UPDATE_SNAPSHOT=1` no snapshot do view-model.
- **Teste com humano (n=1):** o dono abre um relatório parcial **sem** ter visto o
  `/pipeline` e diz em 1 frase o que falta e o que fazer; e lê o PDF do estado
  retido **sem** concluir que os números das outras seções são suspeitos.

### Herdado da [[A40.l10]] — supressor não-declarado no frontend

`dedupeBySemanticKey` em
`frontend/src/components/report/utils/curadoriaDestaques.ts` colapsa itens por
chave semântica derivada de **regex sobre texto**, *first-wins*: o sobrevivente
depende da **ordem de chegada** e o descartado some sem rastro. Duas
consequências: (a) a contagem que a l10 declarou no `s10` ([[ADR-365]]) **pode
divergir** do que o card renderiza; (b) **asserção sobre payload não prova o
renderizado** — teste no nível de render, sempre.

### Cuidado de UI

Wrappers `base-ui`: `Select.Value` sem `items` mostra o value cru; variant custom
do shadcn faz ponte por `data-attr` — CSS vivo não prova comportamento. Popup é
async: teste que só falha em máquina rápida é teste que precisa de `await`, não
de `sleep`.

---

## 7. Definition of done (as três)

Uma frente **só está concluída** quando o PR está **mergeado em `main` via
squash** com CI verde (`gh pr view <N> --json mergeCommit,mergedAt`). PR aberto
aguardando CI é `in_progress`, não `completed`.

No merge, **no mesmo PR ou num docs-only imediatamente depois**:

- `status` da lane → `shipped`.
- ADR citada → `Decidido` (l20: ✅ [[ADR-366]] **e** [[ADR-357]], ambas no #1278 com
  emenda datada; l2: ✅ emenda datada na [[ADR-364]]).
- Se a frente destravou outra lane, **flipe o `blocked` dela** — é a manutenção
  que o §Predicado exige e que ninguém fez duas vezes nesta sprint.
  > Verificado no fecho da B (2026-08-07): **nenhum alvo**. A única dependente da
  > [[A40.l20]] é a [[A40.l22]], que já estava `open` desde #1272 — o gatilho dela
  > era o PR1. Registrar a verificação é parte da manutenção: "não havia o que
  > flipar" e "esqueci de flipar" são indistinguíveis sem esta linha.

**Gates de doc antes de commitar doc:**

```bash
python3 dev/validate_frontmatter.py && python3 dev/check_doc_links.py && \
python3 dev/check_adr_anchors.py && python3 dev/check_adr_amendment_signal.py && \
python3 dev/build_doc_index.py --check
```

---

## 8. O que NÃO fazer

- **Não funda frentes.** Três lanes, três PRs. A l2 sozinha já é multi-PR.
- **Não pine número como alvo** (`593`, `411`, `261`). O alvo é a **regra**;
  pinar o número é Goodhart, e esta lane já acumula três instâncias de identidade
  que fecha por construção e esconde o defeito.
- **Não trate "medido" como "corrigido".** A KR-B é reportada **não atingida**
  enquanto o flip do enforce não mergear — está escrito no §Estado dos KRs.
- **Não ligue o enforce** (3e) nesta passada. Ele exige os 9 eixos do §Critério
  de saída, incluindo **ensaio de rollback medido** — undo nunca executado é
  premissa, não propriedade.
- **Não deixe o working tree sujo** ao devolver o turno.

---

## 9. Referências

- Lanes: [[A40.l2]] · [[A40.l20]] ✅ `shipped` (#1278) · [[A40.l22]] ⬜ `open`
- Sprint: [`docs/sprint/A40/_README.md`](../sprint/A40/_README.md) §Gate de saída ·
  §Predicado do campo `status`
- Plano: [[PLAN-report-trust]] §Gate de saída do dogfood
- ADRs: [[ADR-354]] · [[ADR-357]] (`Decidido`) · [[ADR-359]] · [[ADR-364]] ·
  [[ADR-365]] · [[ADR-366]] (`Decidido`)
- Instrumento: `dev/probe_collapse_adjudication.py` · `dev/ledger_collapse_layer.py` ·
  `dev/certify_ledger_local.py` · `backend/tests/test_parecer_vocabulary_parity.py`
  (paridade dos 4 vocabulários do parecer nas 3 cópias — lê o `.ts` do cliente;
  membro novo em qualquer uma sem as outras fica vermelho)
