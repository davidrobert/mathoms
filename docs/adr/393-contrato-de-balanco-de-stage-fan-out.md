---
id: ADR-393
type: adr
title: "Contrato de balanço de stage fan-out: queued ≡ processed + errors + skipped(motivo)"
status: Proposto
phase: A40.l68
date: "2026-08-18"
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
  - status/proposto
  - area/pipeline
  - phase/a40-l68
---

# ADR-393 — Contrato de balanço de stage fan-out

**Status:** Proposto • **Data:** 2026-08-18 • É a **ADR-B** do
[[PLAN-deterministic-authority]] (§ADRs a abrir), aberta pela [[A40.l68]].

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

`extract()` permanece como wrapper `-> str` por compat: **cinco** stages o
consomem (`extract_baseline`, `extract_with_llm`, `extract_informes_anuais`,
`extract_comprovantes_bens`, `extract_irpf_full`) e só o segundo entra no escopo
da [[A40.l68]]. Os outros quatro herdam a mesma cegueira e **não** são
consertados aqui — fica declarado, não silencioso.

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

## Consequências

- `extract_with_llm` passa a devolver `skipped: list[...]`; leitores do bloco
  precisam tolerar a chave nova (aditiva).
- `success=true` com balanço aberto passa a ser impossível por construção.
- Os quatro stages fora do escopo seguem cegos até lane própria.
- O `.xls` do dogfood passa a aparecer como `needs_review` nomeado em vez de
  sumir — o corpus não muda, a **visibilidade** dele muda.
