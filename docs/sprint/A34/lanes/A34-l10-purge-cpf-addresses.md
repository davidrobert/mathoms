---
id: A34.l10
type: lane
title: "Purgar CPFs + neutralizar endereço residencial"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: purge-cpf-addresses
adrs: []
depends_on: ["[[A34.l4]]"]
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/seguranca
---

# A34.l10 — `purge-cpf-addresses` (W1 · Saneamento)

## Problema

Dois vazamentos de PII direta sobrevivem no HEAD tracked, ambos recuperáveis por
`git grep` num clone anônimo pós-flip:

- **CPFs reais do casal fundador** em docs de archive (auditoria §1.7): dois CPFs
  com dígito verificador válido, transcritos em texto corrido — ironicamente no
  doc que celebra a remoção de CPFs. Paths: `docs/archive/BACKLOG-pre-shim-2026-05-07.md`
  e `docs/sprint/_archive_pre_a6/_README.md`.
- **Endereço residencial real** (rua + número) espalhado em ~27 arquivos que
  cruzam **código, testes e docs** (auditoria §1.3). Não é só documentação — o
  endereço aparece como exemplo pedagógico em prompt LLM, comentário de service,
  fixture de teste de API e ADRs de domínio. Amostra dos hotspots:
  - **Código:** `pipeline/llm/prompts/apolice.py` (exemplo no prompt),
    `pipeline/domain/services/endereco_canonicalizer.py` (comentário).
  - **Testes:** `backend/tests/test_property_api.py`, testes de identidade de
    imóvel, fixtures frontend correlatas.
  - **Docs:** `docs/adr/215-*.md`, `docs/adr/239-*.md`, `docs/adr/143-*.md`,
    `docs/plan/RESIDENCIA_E_USO/_README.md`, lanes/tracks de A18.

Como a lane toca **código e testes**, é a única do W1 com risco de regressão
funcional — daí depender de [[A34.l4]] (gate `lint_no_real_pii` estendido a
`docs/` + domínio já vermelho no HEAD) rodando antes de qualquer edição.

## Escopo

1. **CPFs → placeholder canônico.** Substituir os dois CPFs reais nos dois docs
   de archive por `123.456.789-09` (CPF de exemplo com DV válido, já adotado pelo
   plano). Preservar a estrutura da frase; só o valor muda.
2. **Endereço → `Rua Exemplo, 100`.** Neutralizar rua + número em todos os ~27
   arquivos. Onde o endereço é dado pedagógico (prompt `apolice.py`, comentário
   do `endereco_canonicalizer.py`, fixtures de teste), o placeholder deve
   **preservar a mecânica** — a canonicalização de endereço, o parsing da apólice
   e as asserções de `test_property_api.py` continuam exercitando o mesmo caminho,
   só com um endereço sintético.
3. **Não tocar** `id`/filename/`aliases`/`supersedes`/`superseded_by` das ADRs
   editadas — anonimização é **in-body apenas** (invariante `filename ≡ id ≡
   wikilink`). Idem para os docs de archive: só o corpo muda.
4. **Ajustar asserções que casam o valor literal.** Se um teste faz assert sobre
   a string do endereço/CPF real, atualizar para o placeholder no **mesmo commit**
   — senão a suíte quebra e mascara o saneamento.

> **Lane toca código + testes → CI obrigatório** (não é docs-only). Rodar a suíte
> completa localmente antes do push (`pytest backend/tests -q`, `pytest tests -q`,
> `cd frontend && npm test -- --run` se tocou fixtures frontend).

## Critério de aceite

- `git grep` no HEAD retorna **zero** para o CPF real (ambos os valores) e para
  o endereço residencial real (rua + número, com e sem acento/abreviação).
- `git grep "123.456.789-09"` resolve nos dois docs de archive; `git grep "Rua
  Exemplo, 100"` resolve nos arquivos neutralizados (prova de substituição, não
  de deleção).
- Gate [[A34.l4]] (`lint_no_real_pii` estendido) passa **VERDE** neste HEAD para
  os padrões CPF + endereço (era vermelho por causa desta contaminação).
- Suíte completa **verde** — `test_property_api.py`, testes de identidade de
  imóvel e fixtures frontend passam com o endereço sintético; parsing de apólice
  e `endereco_canonicalizer` inalterados no comportamento.
- `dev/check_doc_links.py` + `dev/check_adr_anchors.py` verdes (nenhum id/anchor
  de ADR movido).

## Rollback

Lane toca código: em regressão detectada pós-merge, `git revert` do PR restaura
os valores originais. **Porém** revert reintroduz a PII no HEAD — só aceitável
**antes** de W3 (rewrite de histórico) e do flip (W8). Sequência segura de
recuperação: revert → corrigir a asserção/parsing quebrado → re-aplicar o
saneamento em novo PR, tudo dentro da janela pré-FREEZE. O placeholder é
determinístico, então re-aplicar é idempotente.

## Referências

- Plano canônico: [[PLAN-public-release]] (Onda W1 · Saneamento do HEAD).
- Anexo de auditoria (achados mascarados): [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md)
  §1.3 (endereço em ~27 arquivos) · §1.7 (CPF em archive).
- Depende de: [[A34.l4]] (gate `lint_no_real_pii` estendido a `docs/` + domínio).
- Par de saneamento W1: [[A34.l9]] (anonimização in-body de ADRs/docs) —
  coordenar edições sobrepostas em `docs/adr/246-*.md` e docs de A18.
- Contrato de gate anti-regressão permanente: [[ADR-319]].
