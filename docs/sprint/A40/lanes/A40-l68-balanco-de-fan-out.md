---
id: A40.l68
type: lane
title: "Balanço de stage fan-out: documento que some não pode sair como sucesso"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P1
branch_slug: a40-l68-balanco-de-fan-out
owner: data-engineer
adrs:
  - "[[ADR-081]]"
  - "[[ADR-393]]"
  - "[[ADR-272]]"
  - "[[ADR-357]]"
depends_on: []
parallel_with:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
---

# A40.l68 — `a40-l68-balanco-de-fan-out`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (Onda 2,
> itens 2a e 2b). **Paralela desde o dia 0** — não depende do seam da
> [[A40.l66]] e não compete pela mesma janela de rebaseline. Nasce `planned`
> apenas porque a Onda 0 abriu uma lane `open` de cada vez; o pickup pode
> promovê-la sem esperar ninguém.

## Problema

`extract_with_llm` faz fan-out sobre N documentos e devolve `success` sem provar
que os N foram contabilizados. Documento que entra na fila e não sai — porque o
leitor do formato não existe — desaparece **sem deixar rastro**: o run fica
verde e o relatório é publicado sobre corpus incompleto.

A causa medida no r6 é um resultado não-tipado na extração de texto:
`text_extractor.py` **lava a exceção do leitor** e devolve string vazia. O `.xls`
observado não é "texto vazio" — é **leitor ausente**, e as duas condições são
indistinguíveis para o chamador.

## Escopo

**2a — invariante de balanço.** `queued ≡ processed + errors + skipped(motivo)`
no `extract_with_llm`, com **resultado tipado** na extração de texto
(`texto | falha_de_leitor(motivo)`). Regras:

- `skip` → `review_reason` **nomeando o documento** ([[ADR-272]]);
- `success` exige balanço fechado;
- formato sem extrator falha **no E0**, não no meio do fan-out;
- o invariante mora no **contrato de retorno do stage** (stage log /
  `validation`), **não** em JSON Schema: com `processed = 0` não existe payload
  para o hook pós-write validar;
- denominador **enumerado** — lista declarada de stages fan-out, não descoberta
  por reflexão.

**2b — ladder [[ADR-081]] no E1.5.** `confidence < 0,7` → `review_reason` +
`degraded`, WARN-first com budget medido.

## Enforcement

WARN-first ([[ADR-357]]): `skipped(motivo)` + `needs_review`; `success=false`
**só** com balanço aberto. Budget medido sobre r5+r6 antes do flip; kill-switch
por env var. Estado terminal de documento não processado é `degraded` +
`needs_review`, nunca run abortado.

> **Marcador 2026-08-24 (§Ataque D/E).** O kill-switch **não existe** e o
> produtor **retém** o run em vez de segui-lo — a [[ADR-393]] §Emenda 2026-08-19
> declara **D4 parcial**. O texto acima fica como registro do co-design.

## Critério de aceite

- **Prova por mutação:** remover o leitor de um formato ⇒ motivo "leitor
  ausente" + documento em `needs_review` + balanço fecha. Sem a mutação, o teste
  nomeia o mecanismo sem exercitá-lo.
- Fixture com formato sem extrator falha **no E0** e não chega ao fan-out.
  → **não entregue** ([[ADR-393]] §Estado: **D5** e **D3** sem dono nomeado).
- `success=true` com `queued != processed + errors + skipped` é impossível —
  teste que constrói o desbalanço à mão.
  → entregue **e vácuo**: o desbalanço só existe à mão. Ver §Ataque A.
- Cada `skipped` carrega motivo e identificador do documento no
  `review_reason`; taxa medida sobre r5+r6 e escrita na ADR-B.
- ADR-B aberta `Proposto` antes do PR de implementação. **Nenhuma emenda à
  [[ADR-342]]** — escopo distinto, decisão do co-design.

## Fora de escopo

- Ampliar [[A42.l4]] (dona de `validate_cross`): ela **preserva a disjunção
  declarada**, ganha citação da ADR-B e re-prioridade P1 no frontmatter, e nada
  além disso.
- `llm_call_log` e telemetria por tentativa → [[A42.l7]].
- Cache/pin de extração → depois da Onda 1 (§Anti-decisões do plano).

## Liberada e em execução — 2026-08-18

Promovida `planned` → `open` por decisão do dono. A **ADR-B** do plano é a
[[ADR-393]], aberta `Proposto` antes do PR de implementação.

Medido ao abrir a ADR, e é mais forte que o registro §r6 sozinho: r5 e r6 têm
`total_documents` **idêntico (171)** e `llm_calls` **7 vs 6**, ambos
`completed`. O limite da medição está declarado na ADR — `llm_calls` agrega mais
de um stage, então o delta é consistente com o skip do RV6-10 sem isolá-lo.

Descoberto ao mapear o terreno: são **dois** call-sites que devolvem
`(None, None)` — imagem vazia além do texto vazio — e **cinco** stages consomem
o `DocumentTextExtractor`. Só o `extract_with_llm` entra no escopo desta lane;
os outros **seis** herdam a mesma cegueira e ficam declarados na [[ADR-393]] §D2,
não consertados em silêncio.

> **Marcador 2026-08-24 (§Ataque D).** "cinco" foi corrigido para **sete** na
> [[ADR-393]] §D2 (a medição original truncou em `head -10`), e a correção
> também truncou: há um 7º consumidor fora de `pipeline/stages/` —
> `family_member_pii_service.py:70`.

## 2a entregue — 2026-08-18 (#1526 · `4b3bff08`)

Leitor tipado (`extract_result` → `TextExtraction`), balanço
`queued ≡ processed + errors + skipped` com `success` exigindo o fechamento, e
`extract.reader_missing` WARN-first fora de `BLOCKING_CODES`. Quatro mutações
provadas, incluindo a que a lane pede (remover o leitor de um formato ⇒ motivo
nomeado + `needs_review` + balanço fecha), como teste permanente.

Três achados de execução que o planejamento não tinha:

1. **Dois** call-sites mudos, não um — imagem vazia além do texto vazio.
2. A chave `skipped` já existia como **booleano** nos early-returns do stage;
   minha lista teria criado a mesma chave com dois tipos. Renomeada
   `skipped_docs`.
3. Deslocar o seam **silenciou 18 dublês** que fazem `patch` em `extract`.
   Atualizados só os do E2-llm.

O `.xls` do RV6-10 ficou provado por execução: `openpyxl does not support the
old .xls file format`.

## §Pendência datada — 2b (ladder [[ADR-081]] no E1.5) · 2026-08-18

**Não entregue**, e não por falta de tempo: ao ler o terreno,
`extract_baseline.py:161` agrega confiança como
`min(confidences) if confidences else **0.0**`. Um ladder `< 0,7` cru dispararia
para **todo** run sem metadado de confiança, porque o `0.0` ali é **sentinela de
ausência**, não medição — é o mesmo "zero ≠ não medido" que este plano combate,
e um gate que dispara sempre ensina o operador a ignorá-lo.

Condição de retomada: `confidence` ausente modelado como estado próprio
(distinto de confiança baixa), com a taxa de disparo medida sobre r5+r6 **antes**
do WARN, na forma da [[ADR-393]] §D4. Dono: `data-engineer`. Enquanto isso a lane
fica `open` — 2a mergeado não fecha a lane.

> **Entregue em 2026-08-24 — e o bloqueio declarado acima estava errado.**
> Medido: `confidence == 0.0` aparece em **0/172** agregados; o sentinela nunca
> dispara. Quem dispararia 100% é o `min()` do agregado (172/172 abaixo de 0,7).
> No grão do **arquivo** o piso discrimina — `< 0,7` ⟺ mediana de **0** itens
> extraídos, contra **9** acima —, e a taxa é **4 por run**. O ladder shipou
> ali, com `extract.low_confidence` (que existia no enum desde a [[ADR-272]] e
> nunca teve emissor). Ver [[ADR-393]] §Emenda 2026-08-24 (b).

## §Ataque — 2026-08-24

Ataque medido ao 2a já mergeado (#1526 · `4b3bff08`), com a suíte da lane verde
(15/15) e `origin/main` em `47c0988e`. Tudo abaixo é **execução**, não leitura.

### A — `success=true` sobre documento perdido: o predicado do título não shipou

O título da lane é "documento que some não pode sair como sucesso". Medido, com
o stage real rodando sobre um `.xls` de internet banking (tabela HTML, sintético):

```
success            : True
balanco            : {queued: 1, processed: 0, errors: 0, skipped: 1, fecha: True}
artefatos gravados : 0
validation.valid   : False   ← quem retém o run
```

**O balanço fecha *porque* a perda é um termo do lado direito.**
`queued ≡ processed + errors + skipped` é uma identidade de conservação, não um
predicado de saúde: ela é satisfeita por qualquer distribuição, inclusive
`processed = 0`. Logo `success = errors == 0 and fecha` **não pode ser `False`
por documento perdido** — só por exceção não capturada.

Quem de fato retém o run é `validation.valid=False`, lido por
`pipeline_task.py:1489 _has_validation_errors` — o canal da A28.l8, que a lane
estendeu. Ou seja: **D1 (balanço) contribui zero detecção**; D2 (leitor tipado) e
D4 (`review_reason` nomeando o documento) fazem todo o trabalho. O `success=True`
não é falso-verde — ele é justamente o token que roteia para o `needs_review`
(`if result.success and _has_validation_errors(result)`). O defeito é a ADR-393
§D1 afirmar que "`success` passa a exigir o balanço fechado, não só
`errors == []`": a exigência existe e é vácua.

**Nenhum dos 15 testes asserta `run()["success"]`.** Todos chamam
`_fan_out_balance` / `_e2llm_validation_block` direto, com listas montadas à mão
— inclusive `test_nao_fecha_com_documento_sem_destino`, que constrói o desbalanço
que o stage não consegue produzir. A `TestProvaPorMutacao` asserta
`balanco["fecha"] is True` para o documento perdido, o que **codifica a vacuidade
como critério de aceite**. O balanço vale como guarda de regressão do caminho de
drop que o próprio #1526 deletou; não vale como detector.

### B — `documento_vazio` é a porta que ficou aberta

Dos quatro motivos, um reproduz o comportamento pré-fix **inteiro**. Medido:

| motivo | `success` | `valid` | `review_reasons` | artefato | run |
|---|---|---|---|---|---|
| `leitura_falhou` / `leitor_ausente` / `leitor_indisponivel` | True | **False** | 1 | 0 | pausa p/ review |
| `documento_vazio` | True | **True** | **0** | 0 | **segue verde** |

`imagem sem bytes` cai em `documento_vazio` — upload truncado classificado como
fato legítimo. E PDF escaneado sem camada de texto é `""` do pdfplumber, que é
limitação de leitor, não documento vazio: a mesma conflação que a lane matou, um
andar abaixo.

**Incidência hoje: zero.** 305/305 PDFs reais e 290/290 CSVs saem `ok`. É buraco
latente, não regressão viva — a taxa está declarada para não virar P0 fantasma.

### C — o único defeito medido no corpus é `.xls`, e o leitor já está no repo

Outcome real de `extract_result` sobre as 3 pastas de fan-out de `storage/`:

| sufixo | n | `ok` | defeito |
|---|---|---|---|
| `.pdf` (reais) | 305 | 305 | 0 |
| `.csv` | 290 | 290 | 0 |
| `.xlsx` | 10 | 10 | 0 |
| **`.xls`** | **168** | **0** | **168 `leitura_falhou`** |

168/168, motivo idêntico: `openpyxl does not support the old .xls file format`.
E **`xlrd` 2.0.2 está instalado e abre 168/168** — é a lib que
`route_documents.py:399`, `e2/banks/itau.py:98` e `santander.py` já usam. O
`_reader_for` manda `.xls` para openpyxl e é o único lugar do repo que faz isso.

O RV6-10 está `fechado com ressalva` por "o skip ser nomeado". O sintoma de
origem — *documento financeiro permanentemente ausente do corpus* — segue
intacto: o documento continua inextraível, agora com aviso. **Nenhuma lane e
nenhuma ADR assumem o roteamento.** O enum também não tem estado para "roteado
para a lib errada": 168 documentos legíveis saem rotulados `leitura_falhou`, que
lê como "o documento está quebrado".

**Limite da medição:** só chega ao fan-out o `.xls` cujo parser determinístico
não gravou artefato. Não consegui contar essa população hoje — dos workspaces com
corpus em disco, só 1 tem chaves de `pipeline_artifacts` que casam com os stems.
O n=3 do RV6-10 prova que ao menos um chega.

### D — a correção da truncagem do §D2 está truncada do mesmo jeito

O blockquote "Correção 2026-08-18" conserta cinco→sete re-medindo com
`grep -rln DocumentTextExtractor pipeline/stages/` — **escopado a
`pipeline/stages/`**. Há um 7º consumidor de `.extract()` fora dali:
`backend/app/services/family_member_pii_service.py:70` (backend, não stage). `DocumentTextExtractor.extract_multiple` também roteia pelo
`extract()` cego. A §D2 existe para declarar quem herda o resíduo; a lista segue
incompleta pela mesma classe de erro que ela corrigiu, um diretório acima.

### E — a lane não carrega as correções que a ADR carrega

A [[ADR-393]] declara **D3** e **D5 não entregues** e **D4 parcial** (kill-switch
inexistente; o produtor retém em vez de seguir). A lane não: o §Critério de aceite
segue pedindo "Fixture com formato sem extrator falha **no E0**" (D5) e o
§Enforcement segue prometendo "kill-switch por env var" (D4), sem marcador, e o
§2a entregue não sinaliza a lacuna. Quem faz pickup lê a lane. Precedente:
closeout da [[A40.l66]].

### Nota de método — a primeira medição estava contaminada

Medir `.pdf` sobre `storage/` inteiro deu 598/903 `leitura_falhou`
(`No /Root object!`). São **1 byte de resíduo de teste** (`write_text("x")`), um
por workspace sintético — 598 workspaces com 1 arquivo cada. A população real é
305 PDFs em 8 workspaces, e sai 305/305 `ok`. Filtro que salvou o achado: magic
bytes `%PDF`, não sufixo.

### Sobre o 2b

A §Pendência datada segue válida: `min(confidences) if confidences else 0.0`
continua vivo — hoje em `extract_baseline.py:169`, não `:161`.

## §Deferimento datado — roteamento do `.xls` · 2026-08-24

**Dono: `data-engineer`** (owner da lane). Aberto pelo §Ataque C; sem lane, sem
ADR e sem disposição de review até aqui — o RV6-10 fechou "com ressalva" por
nomear o skip, e o sintoma de origem (documento financeiro permanentemente
ausente do corpus) ficou sem rota.

`_reader_for` manda `.xls` para openpyxl e é o **único** lugar do repo que faz
isso: `route_documents.py:399`, `e2/banks/itau.py:98` e `santander.py` já usam
`xlrd`. Medido no corpus de fan-out: **168/168 falham com openpyxl, 168/168
abrem com `xlrd` 2.0.2** (já instalado).

Condição de retomada — três decisões que não são do closeout:

1. Rotear `.xls` para `xlrd` é fix de duas linhas, mas parte dos `.xls` de
   internet banking é **tabela HTML** (`e2/banks/itau.py:429`) — a forma certa é
   reusar o roteamento que os parsers determinísticos já têm, não duplicar.
2. O enum de `ReaderOutcome` não tem estado para "roteado para a lib errada":
   168 documentos legíveis saem rotulados `leitura_falhou`, que lê como
   "documento quebrado". Decidir se vira motivo próprio ou fica no `detalhe`.
3. Medir antes do flip quantos `.xls` **chegam** ao fan-out — só chega o que o
   parser determinístico não gravou. Não foi possível contar em 2026-08-24: dos
   workspaces com corpus em disco, só 1 tem chaves de `pipeline_artifacts` que
   casam com os stems, e não há stub `requires_llm_fallback` vivo no DB. O
   `n=3` do RV6-10 prova que ao menos um chega.

Enquanto isso a lane fica `open` — junto com o 2b da §Pendência datada.
