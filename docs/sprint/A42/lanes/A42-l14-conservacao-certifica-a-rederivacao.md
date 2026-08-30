---
id: A42.l14
type: lane
title: "Os vereditos de conservação certificam a re-derivação, não o artefato entregue"
sprint: A42
status: in_progress
priority: P0
branch_slug: a42-l14-conservacao-certifica-a-rederivacao
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-302]]"
  - "[[ADR-347]]"
  - "[[ADR-421]]"
tags:
  - type/lane
  - sprint/a42
  - status/in-progress
  - priority/p0
  - area/dados
---

# A42.l14 — `conservacao-certifica-a-rederivacao`

> **Origem:** `LC6-01` da rodada unificada **U2** ([[LEDGER-CERTIFY-active]] §r6,
> merge `47970706`). Levantado pela lente do razão e **verificado no código** pelo loop
> principal — a descoberta invalidou um cross-check que a própria rodada havia publicado.

## O defeito

`dev/ledger_certify_core.py:247` chama `_conservation(e2_payloads, fresh_e3, e4, result)` —
o E3 é a **re-derivação**. O docstring de `build_report` (`:307`) declara *"a partir das
peças re-derivadas"*. O `persisted_e3` entra em `build_report` e é consumido **só** em
`_drift` (`:322`).

Logo `e3_groups` (`:318`), `e4_buckets`, `investment_collisions` e `natural_key` (`:229`)
**também** descrevem a re-derivação, não o que o run publicou. O `--entregue` cobre **uma**
linha: o numerador da KR-B.

**Agravante não medido:** `_persisted_e3_by_key` é **workspace-latest, não run-scoped** —
existe `_e3_of_run` ao lado e não é usado ali. Os "31 só-no-persistido" podem ser sobra de
runs anteriores; responder isso é parte da lane.

## Por que é P0

No mesmo run o drift é ≠ 0 (4 grupos com count divergente, 31 só-no-persistido). A skill
inteira vinha sendo citada como propriedade do artefato entregue — inclusive por esta
rodada, que se retratou.

## Já refutado — não re-litigue

- *"`coberto-sem-verificação-de-valor` é o único veredito possível, independentemente da
  qualidade do dado"* é **falso**: com `dups == 0` o índice 0 de `_e2e3_checks` emite
  perda-silenciosa; com `count_out > count_in` o índice 2 emite. O veredito é constante
  **enquanto** `count_out < count_in and dups > 0` — estado do **corpus**, não do instrumento.
- A **ordem** dos checks em `dev/ledger_conservation.py:163-180` é **decisão documentada**
  (docstring: *"A ORDEM importa… sub-declaração ⇒ não perda (LC-07)"*). Não é defeito, e a
  rodada vendeu uma como a outra antes de se corrigir.

## Rota sugerida (não é ordem)

`certify` recebe o par (fresco, entregue) e emite **duas** colunas; ou o entregue vira o
default e o fresco vira o drift. Decida e justifique.

**Onde o fix não mora:** `pipeline/**`. Isto é instrumento de review, em `dev/`.

## Critério de aceite

- Toda linha do relatório da skill declara **sobre qual substrato** foi computada.
- O modo entregue cobre conservação, não só o numerador da KR-B.
- Os "31 só-no-persistido" ganham veredito: deste run ou sobra.

---

## Pré-trabalho de 2026-08-29 — as três perguntas do §Critério de aceite estão respondidas

> Ataque do `LC6-01`. A lane vira `in_progress` neste mesmo PR; a **A42 segue
> `candidate`** e a ativação da sprint é decisão do dono — o que este PR entrega é a
> medição e a **ADR `Proposto` que a política exige antes do PR de implementação**.
> Direção decidida em [[ADR-421]] (`Proposto`). Registro durável no
> [[LEDGER-CERTIFY-active]] §r6 §`LC6-01`. Evidência reprodutível off-git em
> `storage/<uuid>/reviews/U2-2026-08-29/lc6-01/` (script + saída). O §O defeito acima
> **não é editado** — é a redação de origem.

**1. "Os 31 só-no-persistido: deste run ou sobra?" — SOBRA, 31/31.** Vêm de **7 outros
runs**, `created_at` 2026-05-29 → 2026-07-31; o run pinado (2026-08-29) escreveu **zero**
deles, e `run − ws_latest = 0`. Consequência que a linha do §r6 não previa: a glosa
impressa em `ledger_certify_core.py:391` — *"keying antigo não reproduzido"* — é
**atribuição falsa de causa**. Nada na re-chaveação está implicado.

**2. O agravante é maior do que "não medido" sugeria.** Dos **61 runs `completed` com E3,
60** teriam **todas** as próprias keys comparadas contra artefato de outro run.
`require_pinned_run` só exige `--run` não-vazio; só o run mais novo escapa, por
coincidência de recência. E o docstring de `dev/ledger_certify_entregue.py` afirma
*"Workspace-latest é proibido"* — a proibição vale para a **seleção do run**, e o
substrato entra pela porta dos fundos.

**3. A rota está decidida, e não é nenhuma das duas sugeridas.** Nem duas colunas nem
flip cego: **sujeito único = artefato entregue, com auto-rotulagem por linha**, e a
sombra rebaixada a bloco diagnóstico **normativo**. Duas colunas foram rejeitadas porque
o registro durável keya por `(dimensão, âncora, regra)` **sem eixo de braço** — obrigar
todo citador a carregar um qualificador que a chave não guarda é a causa-raiz deste
próprio achado. Seis decisões em [[ADR-421]] §Decisão.

### Armadilha medida — o braço entregue está amputado

`_rederive_entregue` semeia **só E3**. Investimentos vêm de artefatos **E2**
(`e4_categorizer_adapter.py::load_investment_positions`) e `patrimonio` do baseline.
Medido in-process, os dois braços do mesmo run:

| | baldes | `investimentos` | `classified` | `transferencias` |
|---|---|---|---|---|
| sombra | 7 | 18 | 6928 | 1363 |
| entregue | **6** (falta `patrimonio`) | **0** | 6241 | 1246 |

Logo `investment_double_count` devolve 0 sobre **zero posições** — falso-negativo do
detector da [[ADR-271]], **indistinguível na saída** de um 0 verdadeiro. **Promover
`e4_e` à rubrica sem corrigir isso troca um defeito por outro.** O E4 **persistido** do
run carrega o sinal inteiro (7 baldes, `investimentos`=18): ler o publicado é mais fiel
e mais barato que re-derivar ([[ADR-421]] D4).

### Dois bounds que impedem exagero, e um que impede regressão

- **A KR-B da [[A40]] não está contaminada.** O numerador lê só os baldes transacionais
  (`_tx_rows`) e `transferencias_count`; não lê `investimentos`/`patrimonio`.
- **O substrato E2 não é defeito.** A [[ADR-241]] decidiu que E2 é workspace-scoped — é
  o read-path de produção — e neste run **0 de 170** rows E2 nasceram depois do fim dele.
  **Run-escopar o E2 seria regressão**, reintroduzindo o universo subdimensionado da
  §Contexto daquela ADR. O escopo certo é assimétrico: E2 pela política do run,
  **E3/E4 run-scoped**.
- **Separar o predicado de certificar do de pontuar KR-B é obrigatório.**
  `evidence_from_retention` exige `removals_publicadas > 0`, e só **10 dos 61** runs têm
  essa evidência: sem a separação, tornar o entregue o default **recusaria 51**.

### O que a [[ADR-241]] já decidiu contra este código

A §Alternativas (a) rejeitou "mais-recente-por-key" para E3 porque *"congelaria dedup
parcial entre runs — bug silencioso difícil de detectar"*. `_persisted_e3_by_key` **é**
essa alternativa, dentro do instrumento; os 31 fantasmas são esse bug, medido. O lado de
escopo do fix é **conformidade a ADR Decidida**, não decisão nova — o que a [[ADR-421]]
decide é só o **sujeito**.

### Por que sobreviveu quatro rodadas — a fixture é a causa

`tests/dev/test_ledger_certify_core.py:201` passa `persisted_e3=fresh_e3`, o **mesmo
objeto**. Nenhum teste sobre `build_report` consegue discriminar os dois universos.
Provado por mutação no núcleo puro: universo entregue grosseiramente outro ⇒ os **oito**
campos de rubrica e sumário saem idênticos, só `drift` reage.

### Emenda ao §Critério de aceite — quatro bullets que discriminam proveniência

Os três acima continuam valendo. Estes entram porque **critério de mutação por ausência
não pega esta classe**: aqui o input está presente e o check roda; errado é de onde ele veio.

- **Teste de troca de sujeitos** sobre `format_report`: dois sujeitos que rendem
  vereditos **opostos** em todos os eixos; trocá-los troca os blocos integralmente. Eixo
  que ignore o argumento quebra a simetria — e eixo **novo** adicionado depois sem wiring
  cai no mesmo teste. Falha hoje por ausência do bloco.
- **Fixture de dois runs** em SQLite real: mesma `artifact_key`, runs distintos, a do
  outro run mais recente ⇒ certificar o run A reporta os grupos de **A**. Tem de ser DB —
  o defeito mora na cláusula `WHERE`, e sessão fake seria o mock/prod drift que a §Testes
  do CLAUDE.md proíbe. **Duas mutações escritas antes do gate:** reintroduzir
  workspace-latest **reprova**; remover o corte temporal **reprova**.
- **Anti-amputação:** `investimentos` do sujeito entregue tem `len(dados) > 0` e
  `patrimonio` presente. Sem isto, "consertei o sujeito" passa verde sobre o `e4_e`
  amputado.
- **Drift honesto exercitado onde ele mente:** rodar em **≥3 runs não mais recentes** —
  é o cenário dos 60/61. Certificar qualquer um não produz `persisted_only` de outro run.

**Aresta:** a [[A42.l3]] reescreve o mesmo arquivo (itens 1–9). **Esta lane precede os
itens 1–5 dela** — rationale na §Aresta declarada de lá.

- **Não-regressão da sombra:** golden do texto do bloco sombra **idêntico ao HEAD**. Este
  critério existia só na [[ADR-421]] §Critério de aceite e faltava aqui — a §Emenda era
  cópia *lossy*, e quem trabalhasse pela lane não veria o critério que enforça a D1.
  **Ordem obrigatória:** o golden se captura contra `origin/main` **antes** do primeiro
  commit de código. "HEAD" é referência móvel: capturado depois, ele congela a saída já
  mudada e passa verde provando nada.

## Rota de PRs (2026-08-30)

A [[ADR-421]] citava *"o PR1 desta rota"* sem enumerar rota nenhuma. Ela vive aqui — plano
de entrega envelhece, e ADR não é o lugar dele.

**PR-A — `dev/**` + `tests/dev/**`**, nesta ordem de commits:

1. golden do bloco sombra contra `origin/main` (janela única — ver acima);
2. split de `dev/ledger_certify_core.py` (472 linhas) e `dev/certify_ledger_local.py`
   (455) — folga de 28 e 44 contra o teto de 500. Render sai para
   `dev/ledger_certify_render.py`; leitura de DB para `dev/ledger_certify_db.py`.
   **Re-exportar por binding** (`from … import _x  # noqa: F401`), nunca por chamada
   qualificada: três testes fazem `monkeypatch.setattr(mod, "_row_counts" / …)` e viram
   inertes em silêncio se o nome deixar de morar no módulo;
3. ratchet de ordem estendido a `certify_entregue` + o fix do `counts_after` (§Achado
   adjacente, abaixo);
4. call-site run-scoped — `certify` passa a usar `_e3_of_run`, **que já existe e não é
   chamado ali** (`certify_ledger_local.py:352` vs `:115`). É o menor PR de código com
   valor: ataca direto o 60-de-61;
5. corte temporal no E2 + censo de proveniência (`do run` / `herdado` / `pós-run`);
6. baldes E4 e `investment_double_count` sobre o E4 **persistido** (D4 + anti-amputação);
7. `_e4_verdicts` itera o conjunto **esperado** de baldes, não `sorted(e4)` — hoje balde
   ausente não gera linha nenhuma, que é o modo de falha por **omissão** que a D6 nomeia;
8. rótulo `[entregue]`/`[sombra]` por linha (D2);
9. `evidence_from_retention` fora do caminho de `certify` (D5);
10. a glosa falsa de `ledger_certify_core.py:391` corrigida.

**PR-B — docs-only:** flip da [[ADR-421]] para `Decidido` + `phase: A42.l14`, nota de
cabeçalho no [[LEDGER-CERTIFY-active]] prevista na §Consequências da ADR, `LC6-01`
fechado, e o flip desta lane com `ship_pr`/`ship_date` + `#N` citado na tabela do
`_README` da sprint (`check_lane_transition` exige os três no mesmo commit, e a A42 **não
tem `_HISTORY.md`** — o `#N` só é encontrável no `_README`).

## Achado adjacente — o zero-write do modo que pontua a KR-B

`certify_ledger_local.py` sobrescreve `report.counts_after` em `certify_entregue`
**depois** de `certify` já ter rodado `_blast_radius_or_empty`, cujo ramo degradado faz
`rollback`. Como `zero_write_ok` é `counts_before == counts_after`, o **único modo que
pontua a KR-B** pode declarar zero-write com escrita tendo existido. O comentário em
`certify` diz literalmente *"ORDEM É A PROVA"*, e o ratchet
`test_contagem_final_vem_antes_do_blast_radius_que_faz_rollback` cobre **só** `certify`.
Não está na [[ADR-421]] — foi achado ao mapear o arquivo que ela reescreve. Entregue no
commit 3 do PR-A, com o ratchet estendido **antes** do fix.

## Ressalvas declaradas (a lane fecha com elas escritas, nunca em silêncio)

- **D3 §"compor o `DBArtifactStore` real"** não é testado por nenhum dos seis bullets —
  dá para fechar verde violando-a, porque `_latest_by_canonical` **admite no docstring**
  ser réplica. **§Deferimento datado 2026-08-30**, retomada nomeada: [[A42.l6]], que já é
  dona da política de escopo do store pela emenda à [[ADR-291]].
- **Execução em ≥3 runs não mais recentes** exige o DB de dogfood. Se não for exercitada,
  a lane fecha declarando *"mecanismo provado por fixture; rota sobre os 61 runs não
  exercitada"*.
- **Tensão interna da ADR:** a D2 manda rotular toda linha, e o §Critério exige o golden
  da sombra **idêntico**. Leitura adotada: "bloco sombra" = o bloco
  `## Duplicação cross-grupo`, que **já** se auto-rotula (`_SOMBRA_LABEL`) e fica intacto.
  Registrado aqui para o implementador não decidir isso calado.
- **`LC6-02`…`LC6-07` do §r6 seguem `procede-aberto`.** Fechar esta lane não fecha o §r6.
