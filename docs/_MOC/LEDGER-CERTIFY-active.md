---
type: moc
title: LEDGER-CERTIFY-active — Rastreamento de certificações de razão (E3/E4)
aliases: ["LEDGER-CERTIFY", "LEDGER-CERTIFY-active", "ledger-tracking", "ledger-certify-registry"]
---

# LEDGER-CERTIFY-active — Rastreamento de certificações de razão

> **Editorial.** Curado manualmente — **não é gerado**. Registro durável dos
> achados **sistêmicos/defeito** da skill `ledger-certify` ([[ADR-343]] para a
> disciplina de estado durável; [[ADR-302]] para a classe). Certifica E3
> (reconciliação) + E4 (categorização) no grão transação/posição. Uma seção por
> run; seções de runs 100% fechados viram histórico aqui mesmo.

## O que entra aqui (e o que NÃO entra) — [[ADR-343]]

Achados da `ledger-certify` são de duas naturezas; **só uma** aterrissa aqui:

- ✅ **Sistêmico / defeito** — afirmação sobre o **pipeline** (reconciliador,
  categorizador, contrato de stage, dedup, detector de transferência,
  natural_key). Recorre entre runs e é **PII-free por construção**. Ex.: "dedup de
  investimento não colapsa chave `tipo|instituicao|descricao_norm` cross-ano
  (ADR-271)". **Entra aqui**, keyed por `(dimensão, evidência-âncora, regra)` —
  âncora = `stage:key`/`campo.dot.path`/`arquivo:linha`, **nunca** um valor.
- ❌ **Instância / dado** — afirmação sobre as transações/posições **deste
  workspace neste run** (carrega contraparte/nome; não recorre). **Fica off-git**
  em `storage/<uuid>/ledger_certify/<ts>-<run8>/` junto com a síntese crua.

**Commit-safe:** zero literal monetário, zero nome próprio. O título do achado tem
de ser um **defeito**, não um dado. Discriminador de workspace na seção =
`ws-<uuid8>` (nunca slug derivado de email). O hook de PII do pre-commit é
backstop, não garantia primária.

## Convenção de rastreamento (timeless)

Para que nenhum achado-defeito se perca entre runs:

1. **Cobertura 100%.** Cada run gera uma seção cobrindo **todos** os achados
   sistêmicos — inclusive refutados e não-acionáveis. Triagem só é completa quando
   todo item tem disposição.
2. **ADR/lane para o que tem peso de decisão.** Item que procede e altera
   decisão/invariante/contrato entra em ADR de veredito ou lane do BACKLOG.
   Refutado/não-acionável basta neste índice com 1-2 linhas de rationale + link à
   evidência. **Não** se exige "1 ADR por item".
3. **Aberto exige gatilho.** Item `procede-aberto` **deve** ter prioridade
   (P0-P3) + owner + link para lane ou ADR `Proposto`.
4. **Cadência.** Ao abrir run novo, revise a seção do anterior: todo
   `procede-aberto` que persiste é re-priorizado ou rebaixado a `aceito-wontfix`
   com rationale. Sem zumbis silenciosos.

**Severidade** (própria da skill): `Crítico` · `Alto` · `Médio` · `Baixo`,
cruzada com **Prioridade** `P0`–`P3`. **Taxonomia de disposição** (reusada do
`AUDITS-active`/`PIPELINE-REVIEWS-active`): `procede-fechado` · `procede-aberto` ·
`refutado` · `não-acionável` · `aceito-wontfix`.

**Formato de seção** (por run):

```
## rN — ws-<uuid8>-<AAAA-MM-DD>

> Skill ledger-certify ([[ADR-302]]) · run <run8>. Re-derivação in-process E3+E4
> sobre E2 persistido (zero write DB). Grupos E3: <ok>/<total>; baldes E4:
> <ok>/7. natural_key cobertura: <pct>%. Julgamento: data-engineer +
> financial-planner em paralelo + verificação adversarial (<X>/<Y> confirmados).
> Cru em storage/<uuid>/ledger_certify/ (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC01 — <defeito, com stage:key ou campo.dot.path> | dedup/transferência | Crítico | P0 | procede | procede-aberto | <lane/ADR/commit> |
```

Colunas: **Dimensão** ∈ reconciliação · categorização · conservação ·
dedup/transferência · consistência · saúde-execução. **Trilha** = lane do
BACKLOG, ADR de veredito, ou commit que fechou.

---

_Nenhum run registrado ainda. A primeira seção `## r1 — …` é adicionada pela
primeira execução real da skill (Passo do entregável)._
