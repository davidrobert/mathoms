---
type: moc
title: PARSE-CERTIFY-active — Rastreamento de certificações de ingestão (E0/E2)
aliases: ["PARSE-CERTIFY", "PARSE-CERTIFY-active", "parse-tracking", "parse-certify-registry"]
---

# PARSE-CERTIFY-active — Rastreamento de certificações de ingestão

> **Editorial.** Curado manualmente — **não é gerado**. Registro durável dos
> achados **sistêmicos/defeito** da skill `parse-certify` ([[ADR-343]] para a
> disciplina de estado durável; [[ADR-302]] para a classe). Certifica a ingestão
> E0→E2 (classificação → roteamento → parse → validação) no grão documento. Uma
> seção por run; seções de runs 100% fechados viram histórico aqui mesmo.

## O que entra aqui (e o que NÃO entra) — [[ADR-343]]

Achados da `parse-certify` são de duas naturezas; **só uma** aterrissa aqui:

- ✅ **Sistêmico / defeito** — afirmação sobre o **pipeline de ingestão**
  (classificador, roteador, parser de banco, validador/checksum, harness da
  própria skill). Recorre entre runs e é **PII-free por construção**. Ex.:
  "checksum de fatura fecha sobre escopo parcial e passa falso-verde
  (ADR-342)". **Entra aqui**, keyed por `(dimensão, evidência-âncora, regra)` —
  âncora = `arquivo:linha`/`campo`/`escalation_code`, **nunca** um valor.
- ❌ **Instância / dado** — afirmação sobre os documentos **deste workspace
  neste run** (nome via filename, valores do extrato/fatura; não recorre).
  **Fica off-git** em `storage/<uuid>/parse_certify/<ts>/` junto com a síntese
  crua e o baseline.

**Commit-safe:** zero literal monetário, zero nome próprio. O título do achado
tem de ser um **defeito**, não um dado. Discriminador de workspace na seção =
`ws-<uuid8>` (nunca slug derivado de email). O baseline JSON do harness pode
vazar nome via filename (`mask_text` não remove nome de pessoa) → nunca commite
baseline; o hook de PII do pre-commit é backstop, não garantia primária.

## Convenção de rastreamento (timeless)

Para que nenhum achado-defeito se perca entre runs:

1. **Cobertura 100%.** Cada run gera uma seção cobrindo **todos** os achados
   sistêmicos — inclusive refutados e não-acionáveis. Triagem só é completa
   quando todo item tem disposição.
2. **ADR/lane para o que tem peso de decisão.** Item que procede e altera
   decisão/invariante/contrato entra em ADR de veredito ou lane do BACKLOG.
   Refutado/não-acionável basta neste índice com 1-2 linhas de rationale + link à
   evidência. **Não** se exige "1 ADR por item".
3. **Aberto exige gatilho.** Item `procede-aberto` **deve** ter prioridade
   (P0-P3) + owner + link para lane ou ADR `Proposto`. `procede-aberto` sem
   gatilho é bug deste índice.
4. **Cadência.** Ao abrir run novo, revise a seção do anterior: todo
   `procede-aberto` que persiste é re-priorizado ou rebaixado a `aceito-wontfix`
   com rationale. Sem zumbis silenciosos.

**Severidade** (própria da skill): `Crítico` · `Alto` · `Médio` · `Baixo`,
cruzada com **Prioridade** `P0`–`P3`. **Taxonomia de disposição** (reusada do
`AUDITS-active`/`LEDGER-CERTIFY-active`/`PIPELINE-REVIEWS-active`):
`procede-fechado` · `procede-aberto` · `refutado` · `não-acionável` ·
`aceito-wontfix`. As três colunas de finding (severidade × prioridade ×
disposição) são **comuns** aos MOCs de skill de certificação; só o eixo
**Dimensão** varia por skill (aqui, a superfície da ingestão E0→E2).

**Formato de seção** (por run):

```
## rN — ws-<uuid8>-<AAAA-MM-DD>

> Skill parse-certify ([[ADR-302]]) · harness E0→E2 síncrono (sem Celery/LLM).
> Grupo <financial_statements>: <n> docs. Vereditos:
> <completo>/<coberto-sem-verificação>/<escalado-honesto>/<perda>/<não-coberto>.
> Cross-check harness↔DB por content_hash: <ingested>/<deduped>/<not_ingested>.
> Julgamento: data-engineer + financial-planner em paralelo + verificação
> adversarial (<X>/<Y> confirmados). Cru + baseline em
> storage/<uuid>/parse_certify/ (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| PC01 — <defeito, com arquivo:linha ou escalation_code> | validação/checksum | Alto | P1 | procede | procede-aberto | <lane/ADR/commit> |
```

Colunas: **Dimensão** ∈ classificação · roteamento · parse · validação/checksum ·
cobertura · consistência · saúde-harness. **Trilha** = lane do BACKLOG, ADR de
veredito, ou commit que fechou.

---

## r1 — ws-1b9f2cf5-2026-07-27

> Skill parse-certify ([[ADR-302]]) · harness E0→E2 síncrono `dev/certify_parse_local.py`
> (sem Celery/LLM). **Seção reconstruída da trilha de commits** — os relatórios
> efêmeros dos runs de 2026-07-23 (cert) e 2026-07-27 (re-cert) do grupo
> `financial_statements` não foram preservados em `_scratch/` (precedente [[ADR-302]]:
> relatório efêmero perdido, reconstruído da trilha). Cada linha abaixo é ancorada
> num **commit real** que fechou o defeito; os achados de instância/dado ficaram
> off-git. A re-cert 2026-07-27 saiu **APROVADA** (0 silêncio; candidatos a perda
> refutados na verificação adversarial) após os fixes desta seção.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| PC01 — checksum de completude de fatura ausente: `Σ transações` vs `total_compras` não verificado → artefato "ok" com viés otimista (falso-verde de completude) | validação/checksum | Alto | P1 | procede | procede-fechado | #1036 (WARN-first, emenda [[ADR-342]]) + #1080 (invariante de escopo) |
| PC02 — falso-verde de **escopo** em fatura multi-escopo: checksum fechava sobre escopo parcial (subconjunto de lançamentos) e passava | validação/checksum | Alto | P1 | procede | procede-fechado | #1080 (`4b15d0a4` — invariante de cobertura de escopo) |
| PC03 — double-count no parser `picpay`: mesma transação contada 2× no artefato E2 | parse | Alto | P1 | procede | procede-fechado | #1080 (`4b15d0a4` — hardening picpay/santander_xls) |
| PC04 — harness da skill não expunha o **traço** do pass de checksum de fatura → sucesso silencioso (indistinguível "checou e passou" de "não checou") | saúde-harness | Médio | P2 | procede | procede-fechado | #1080 (traço `fatura_checksum`) |
| PC05 — checksum de investimento ausente (CDB XLSX Santander "Valor Total" / HTML-XLS Itaú `saldo_bruto_final`, escopo bruto) | validação/checksum | Médio | P2 | procede | procede-fechado | #1036 (`a63ec80f` — `apply_cdb_checksum`) |
| PC06 — `--compare` sem ratchet de completude por-documento: regressão de silêncio (`escalated True→False` com conservação quebrada) reintroduzível sem falhar o gate | saúde-harness | Médio | P2 | procede | procede-fechado | #1083 (`6dd27f34` — ratchet de completude W0) |
| PC07 — cross-source: fatura ↔ pagamento correspondente no extrato não reconciliado → mesma saída contável 2× entre documentos (fatura + débito no extrato) | consistência | Médio | P2 | procede | procede-aberto | [[ADR-350]] `Proposto` · PR1 measure-only #1087 (`82c04f0f`); falta enforce |

**Notas de re-triagem:** primeira seção do índice — sem `procede-aberto`
anterior. **1 aberto** (PC07): o enforce do checksum cross-source de fatura
depende da conclusão da [[ADR-350]] (hoje `Proposto`, PR1 só mede). Os demais
6 fecharam antes desta seção existir — daí a natureza reconstruída. **3 achados
de harness/skill** (PC04/PC06 + o traço de PC01) motivaram o hardening do harness
antes das cert runs seguintes: falso-verde numa ferramenta de certificação gateia
beta e gera fadiga de alarme.
