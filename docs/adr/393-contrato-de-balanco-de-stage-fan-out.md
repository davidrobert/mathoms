---
id: ADR-393
type: adr
title: "Contrato de balanço de stage fan-out: queued ≡ processed + errors + skipped(motivo)"
status: Decidido
phase: A40.l68
date: "2026-08-18"
amended_at: ["2026-08-19", "2026-08-24"]
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-097]]"
  - "[[ADR-272]]"
  - "[[ADR-342]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 393"
  - "balanco de fan-out"
  - "ADR-B do PLAN-deterministic-authority"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - phase/a40-l68
---

# ADR-393 — Contrato de balanço de stage fan-out

**Status:** Decidido • **Data:** 2026-08-18 • É a **ADR-B** do
[[PLAN-deterministic-authority]] (§ADRs a abrir), aberta pela [[A40.l68]].

> **Emendada em 2026-08-24 (§D1 é conservação, não detecção):** o §D1 declara
> que "`success` passa a exigir o balanço fechado, não só `errors == []`". A
> exigência existe e é **vácua** — medido por execução. A decisão D1 sobrevive
> como guarda de regressão; o que cai é a afirmação de que ela detecta.
> Ver §Emenda 2026-08-24.

> **Emendada em 2026-08-19 (correção do §Estado, não da decisão):** o §Estado
> declarava **D4 entregue** e a §D4 prometia um **kill-switch de 1 env var
> "provado por teste"**. Medido: o kill-switch **não existe** em lugar nenhum, e
> o produtor de `extract.reader_missing` **retém o run** — o oposto do que o
> texto promete. A decisão D4 sobrevive; o que cai é a afirmação de cobertura.
> Ver §Emenda 2026-08-19.

## Contexto

`extract_with_llm` faz fan-out sobre N documentos e devolve `success` sem provar
que os N foram contabilizados:

```python
out = {
    "success": len(errors) == 0,
    "processed": processed,
    "errors": errors,
    "queued": {"total": len(docs), ...},
}
```

`queued.total` é `len(docs)`, mas nada exige `len(processed) + len(errors) ==
len(docs)`. Documento que entra na fila e não sai de nenhum dos dois lados
**desaparece sem rastro**, e o run fica verde.

Há **dois** call-sites que produzem esse desaparecimento, ambos devolvendo
`(None, None, empty_summary)` — nem `processed`, nem `errors`:

- imagem cujo `extract_image_bytes` volta vazio;
- documento cujo `extractor.extract(doc)` volta `""` (`extract_with_llm.py:231`).

### A causa é um resultado não-tipado no leitor

`DocumentTextExtractor.extract()` devolve `str` e usa `""` para **cinco**
situações que o chamador não consegue distinguir:

| Situação | Linha | O que o chamador vê |
|---|---|---|
| sufixo sem leitor | `text_extractor.py:66` | `""` |
| exceção de qualquer leitor | `:68` | `""` |
| `pdfplumber` ausente | `:76` | `""` |
| `openpyxl` ausente | `:113` | `""` |
| documento genuinamente vazio | — | `""` |

O caso medido é `.xls`: o `elif suffix in (".xlsx", ".xls")` roteia para
`openpyxl`, que **não lê o formato legado** — levanta, a exceção é lavada em
`:68`, e o documento vira "texto vazio". "Leitor ausente" e "documento vazio"
são o mesmo valor, e só o primeiro é um defeito.

### Medição

Registro §r6 (RV6-10, CONFIRMED n=3): o **mesmo** `.xls` pulado por "texto
vazio" em 3 runs consecutivos — skip determinístico, documento financeiro
permanentemente ausente do corpus.

Re-medido nesta lane sobre os snapshots de r5 e r6 (`review_snapshot.json ›
run_health`):

| Run | `total_documents` | `llm_calls` | `status` |
|---|---|---|---|
| r5 `0a040a22` | 171 | **7** | completed |
| r6 `7b64b6c7` | 171 | **6** | completed |

Corpus idêntico, uma chamada a menos, ambos `completed`. **Limite honesto da
medição:** `llm_calls` agrega mais de um stage, então o delta de 1 é
*consistente* com o skip do RV6-10 mas não o isola — isolar exigiria o stage log,
que vive no DB do workspace de dogfood. O default desta ADR é WARN, então nenhum
flip depende desse número.

## Decisão

### D1 — O balanço é contrato de retorno do stage

Todo stage de fan-out devolve `queued ≡ processed + errors + skipped`, com
`skipped` carregando **motivo tipado + identificador do documento**. `success`
passa a exigir o balanço fechado, não só `errors == []`.

O invariante mora no **contrato de retorno** (stage log / bloco `validation`),
**não** em JSON Schema: com `processed == 0` não existe payload gravado para o
hook pós-write validar, e é exatamente o caso que mais importa.

### D2 — O leitor devolve resultado tipado

`DocumentTextExtractor` ganha `extract_result()` devolvendo
`texto | falha_de_leitor(motivo)`. Motivos são fechados em enum:
`leitor_ausente`, `leitor_indisponivel`, `leitura_falhou`, `documento_vazio` —
os três primeiros são defeito, o quarto é fato legítimo.

`extract()` permanece como wrapper `-> str` por compat: **sete** stages o
consomem — `extract_baseline`, `extract_comprovantes_bens`,
`extract_informe_aluguel`, `extract_informes_anuais`, `extract_irpf_full`,
`extract_members` e `extract_with_llm`. Só o último entra no escopo da
[[A40.l68]]; os outros **seis** herdam a mesma cegueira e **não** são
consertados aqui — fica declarado, não silencioso.

> **Correção 2026-08-18 (closeout).** Esta linha dizia "cinco" e nomeava cinco.
> A medição original terminava em `| head -10` e a saída foi **truncada** —
> `extract_informe_aluguel` e `extract_members` ficaram de fora da lista de
> quem herda o resíduo, que é justamente o que a §D2 existe para declarar.
> Re-medido: `grep -rln DocumentTextExtractor pipeline/stages/` → 7 arquivos,
> e 6 chamam `.extract(`.

### D3 — Denominador enumerado, não descoberto

A lista de stages fan-out é **declarada** em constante. Descobrir por reflexão
faria o gate crescer sozinho e falhar aberto no stage novo — a direção errada do
erro, mesma razão do §dev_tools do `ci.yml`.

### D4 — WARN-first, não aborta

Code novo `extract.reader_missing` ([[ADR-272]]), **fora** de `BLOCKING_CODES`.
Default: declara + `needs_review` nomeando o documento; o run segue. Estado
terminal de documento não processado é `degraded` + `needs_review`, nunca run
vermelho ([[ADR-357]]). Kill-switch de 1 env var, provado por teste.

### D5 — Formato sem extrator falha no E0

Documento cujo formato não tem leitor é rejeitado na **entrada**, não no meio do
fan-out. Descobrir isso na extração é tarde: o documento já foi aceito, contado
e prometido ao usuário.

### D6 — Nenhuma emenda à [[ADR-342]]

Escopo distinto — a 342 é checksum de escopo **dentro** do documento; esta é
contabilidade de documentos **entre** unidades de fan-out. Decisão do co-design
do plano, registrada em §Anti-decisões ("NÃO ampliar [[A42.l4]] nem emendar
[[ADR-342]]").

## Estado de implementação (2026-08-18)

`Decidido` refere-se à **decisão**, não à cobertura. Entregue na [[A40.l68]] 2a
(#1526 · `4b3bff08`): **D1** (balanço), **D2** (leitor tipado), **D4**
(WARN-first). **Não** entregues: **D3** (denominador enumerado de stages
fan-out) e **D5** (formato sem extrator falha no E0) — sem dono nomeado, ficam
como resíduo da lane.

> **Corrigido em 2026-08-19 (§Emenda):** **D4** é **parcial**, não entregue — o
> produtor retém o run via `validation.valid`, e o kill-switch prometido nunca
> existiu. O snapshot acima fica como registro do que se acreditava em 18/08.

## Emenda 2026-08-19 — o §Estado afirmava cobertura que a medição refuta

Achado **CTO-2** do §r7. Duas afirmações desta ADR não se sustentam.

**(a) O kill-switch não existe.** A §D4 promete "kill-switch de 1 env var,
provado por teste". `rg 'getenv|environ' pipeline/stages/extract_with_llm.py`
devolve **uma** ocorrência, `MATHOMS_E2_LLM_CONCURRENCY`, que é paralelismo.
Nenhuma env var governa `extract.reader_missing`, e nenhum teste a prova.

**(b) "O run segue" é falso — o produtor retém.** A §D4 diz que o default
"declara + `needs_review` nomeando o documento; o run segue", e o teste que
guarda a promessa (`test_reader_missing_e_warn_first`) afirma **pertinência em
conjunto** — `code not in BLOCKING_CODES` — com a docstring "não retém o run".
O caminho real não passa por `BLOCKING_CODES`:

- `_e2llm_validation_block` publica `valid = not flagged and not defeitos`, e um
  skip com `motivo != "documento_vazio"` é defeito ⇒ `valid=False`;
- o orquestrador retém lendo **`validation.valid`**
  (`pipeline_task.py::_has_validation_errors`, consumido no loop de stages);
- `BLOCKING_CODES` só escolhe **rótulo de severidade** na projeção para
  `ValidationIssue`.

Evidência independente no próprio §r7: o run `33514dc4` **pausou 1× em
`extract_with_llm`** e precisou de `resume_pipeline_run`. A pausa é o
comportamento que a ADR declara não existir.

**O que muda.** A decisão D4 — *documento não processado é declarado, nomeado, e
não pinta o run de vermelho* — sobrevive inteira e está entregue nessa parte:
o code existe, fica fora de `BLOCKING_CODES`, e o desfecho não é `failed`. Cai a
afirmação de que **não retém**, e cai o kill-switch.

**O kill-switch fica redundante, não pendente.** Ele existia para desligar a
retenção em emergência. Sob a tabela de política **total** que o RV7-03/DE-3 vai
introduzir — predicado de pausa passa a ser `any(code ∈ BLOCKING_CODES)`, e cada
membro do enum declara sua política — desligar a retenção de um code é editar a
tabela, não uma env var. Env var de emergência sobre um predicado que já é
declarativo é um segundo lugar para a verdade morar.

**§Estado corrigido:** entregues **D1** (balanço) e **D2** (leitor tipado); **D4
parcial** (code declarado e fora de `BLOCKING_CODES`; retenção **não** desligada,
kill-switch inexistente e retirado do escopo); **não** entregues **D3** e **D5**.

## Consequências

- `extract_with_llm` passa a devolver `skipped: list[...]`; leitores do bloco
  precisam tolerar a chave nova (aditiva).
- `success=true` com balanço aberto passa a ser impossível por construção.
- Os **seis** stages fora do escopo seguem cegos até lane própria.
- O `.xls` do dogfood passa a aparecer como `needs_review` nomeado em vez de
  sumir — o corpus não muda, a **visibilidade** dele muda.

## Emenda 2026-08-24 — D1 é identidade de conservação, não predicado de saúde

Medido no [[A40.l68]] §Ataque, com o stage real sobre um formato que o leitor
não abre:

```
success  : True    balanco : {queued:1, processed:0, errors:0, skipped:1, fecha:True}
artefatos: 0       validation.valid : False   ← quem retém o run
```

`queued ≡ processed + errors + skipped` é **identidade de conservação**: fechada
sob realocação entre as parcelas, satisfeita por qualquer distribuição —
inclusive `processed = 0`. O balanço fecha **porque a perda é termo do lado
direito**. As cinco saídas de `_process_one_e2_llm_document` devolvem exatamente
um não-`None` cada, então `fecha` é tautologia em todo estado alcançável, e
`success = errors == 0 and fecha` **não pode ser `False` por documento perdido**
— só por exceção não capturada.

**O que muda.** O §D1 segue valendo como **guarda de regressão** do caminho de
drop que o #1526 deletou (`return None, None, summary`). O que cai é a
afirmação de que `success` mudou de significado: quem retém o run é
`validation.valid=False` (`pipeline_task.py:1489`), o canal da A28.l8 que a D4
estendeu — e o `success=True` é justamente o token que roteia para lá
(`if result.success and _has_validation_errors(result)`). **D1 contribui zero
detecção; D2 e D4 fazem o trabalho.**

**Regra que sai daqui, para o denominador enumerado da D3:** identidade de
conservação nunca é gate de saúde. Gate de saúde precisa de predicado sobre a
**distribuição** (`processed > 0`, ou `skipped/queued` sob teto), não sobre a
soma. Nenhum dos 15 testes da lane asserta `run()["success"]` — todos chamam
`_fan_out_balance` com listas montadas à mão, e a `TestProvaPorMutacao` asserta
`balanco["fecha"] is True` para o documento perdido, codificando a vacuidade
como critério de aceite.

**Fora desta emenda, com dono:** o `.xls` do RV6-10 segue inextraível — 168/168
falham com openpyxl e 168/168 abrem com `xlrd` 2.0.2, já instalado e já usado
por `route_documents.py:399`, `e2/banks/itau.py:98` e `santander.py`. Ver
[[A40.l68]] §Deferimento.
