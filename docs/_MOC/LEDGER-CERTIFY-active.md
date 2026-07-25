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

## r1 — ws-1b9f2cf5-2026-07-24

> Skill ledger-certify ([[ADR-302]]) · run 57cd4618. Primeira re-derivação
> in-process E3+E4 sobre E2 persistido via `dev/certify_ledger_local.py` — **zero
> write no DB provado** (rows `pipeline_artifacts`/`transaction_overrides`
> inalteradas antes/depois). Grupos E3: 82/109 `conservado`, 27
> `coberto-sem-verificação` (0-tx ou dedup declarado). Baldes E4: 2/7 `conservado`
> (`despesas`, `receitas`), 1 `perda` (`investimentos`), 4 `coberto` (fora do grão
> transacional). natural_key cobertura: **11,8%**. Substrato E2 = workspace-latest;
> drift vs persistido: 109 grupos casados (mesmo count), 0 count-divergente, 20
> só-persistido com keying legado. Julgamento de materialidade (data-engineer +
> financial-planner) + verificação adversarial ficam para a próxima **invocação de
> certificação** — esta seção é o baseline mecânico do harness. Cru + instância em
> `storage/<uuid>/ledger_certify/` (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC01 — dedup de investimento não colapsa a chave `tipo\|instituicao\|descricao_norm` no balde `investimentos` (6 chaves vivas 2×) | dedup/transferência | Crítico | P0 | procede | procede-aberto | [[ADR-271]] (fuzzy/CNPJ é follow-up conhecido) |
| LC02 — E2→E3: `Σ n_tx(E2)` excede `Σ [transacoes_total + dups]` no workspace (gap de count); `statements_reconciled=122`, `skipped_inputs=4` declarados | conservação/reconciliação | Alto | P1 | needs-verification | procede-aberto | atribuir as tx dos 4 statements skipped antes de concluir perda silenciosa |
| LC03 — E3→E4: `Σ transacoes_total(E3)` excede `tx_total(_lineage)` de `despesas` em 1 (1 tx classificada a menos) | categorização/conservação | Médio | P2 | needs-verification | procede-aberto | localizar o drop entre `TransactionClassifier` e `CashFlowBuilder` |
| LC04 — natural_key ausente em ~88% das tx classificadas (cobertura 11,8%) — join sticky-override degradado | consistência | Médio | P2 | procede | procede-aberto | [[ADR-287]] (gate classe-c, titular ausente) |
| LC05 — 20 grupos E3 persistidos com keying legado não reproduzido (banco-prefixo vazio `_extrato_*`, períodos sentinela `189912`/`210001`) | saúde-execução | Baixo | P3 | não-acionável | não-acionável | drift benigno — a re-derivação atual não reproduz o keying antigo (já corrigido) |

> **Revisado em r2 (abaixo).** r1 era o baseline mecânico do harness; r2 completa o
> julgamento diferido (data-engineer + financial-planner + verificação adversarial):
> **r1·LC01 refinado** (5 das 6 "colisões" eram falso-positivo do detector; o
> defeito real é membro-vazio, não a chave `tipo\|inst\|desc`) → r2·LC01+LC06.
> **r1·LC02 mecanismo resolvido** (o gap NÃO são os 4 skipped — carregam 0 tx — e
> sim 2 canais de remoção não-declarados) → r2·LC02. **r1·LC03/LC04 mantidos e
> re-escopados** → r2·LC03/LC04. **r1·LC05 confirmado não-acionável** → r2·LC08.

---

## r2 — ws-1b9f2cf5-2026-07-24

> Skill ledger-certify ([[ADR-302]]) · run 57cd4618. Re-derivação in-process E3+E4
> sobre E2 persistido — **zero write no DB provado** (`pipeline_artifacts`
> 10870→10870, `transaction_overrides` 12→12). Grupos E3: 82/109 `conservado`, 27
> `coberto-sem-verificação`. Baldes E4: 2/7 `conservado` (`despesas` 3586 tx,
> `receitas` 766 tx, ambos fecham cents tol-0), `investimentos` flag,
> 4 fora-do-grão. Transferências internas netadas: 791 (sem vazamento p/
> receita/despesa). natural_key: **11,8%** (677/5723). **Julgamento:** data-engineer
> + financial-planner em paralelo + verificação adversarial (**1/6 colisões de
> investimento confirmadas; 5 refutadas** como falso-positivo do detector). Esta
> seção **completa o julgamento que r1 diferiu**. Cru + instância (PII) em
> `storage/<uuid>/ledger_certify/` (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC01 — dedup de investimento escapa por **membro-vazio**: a chave de produção `(inst, membro)` (`investments_consolidator.py:241`) trata `membro=""` e `membro=<resolvido>` da mesma instituição como chaves distintas → snapshot stale cross-período soma ao `total_geral` (inflação de patrimônio). [[ADR-346]] (Proposto) só fecha inst-vazia; vetor simétrico membro-vazio ABERTO (invariante 3 exige mesmo `(inst,membro)` → nem pega) | dedup/transferência | Alto | P1 | procede | procede-fechado | **fechado** [#1073](https://github.com/davidrobert/mathoms/pull/1073): `_collapse_empty_member` + emenda [[ADR-346]] §4b + invariante 11 (guard de unicidade 0/≥2→needs_review; colapsa no único irmão resolvido) |
| LC02 — E2→E3: **214 de 356 remoções de tx não-declaradas** por 2 canais silenciosos — dedup intra-statement (`reconciliation_service.py:127`,`:145-155`; count reportado em lugar nenhum) + merge cross-file (`e3_serialization.py:115`; só declara com `len(stmts)>1`). Sem ledger de conservação de contagem no workspace → conservação **não-provável a partir do artefato** (gap NÃO são os 4 skipped: 0 tx) | conservação/reconciliação | Alto | P1 | procede | procede-fechado (measure) | **measure em `main`** ([[ADR-347]]): PR1a [#1065](https://github.com/davidrobert/mathoms/pull/1065) + PR1b [#1068](https://github.com/davidrobert/mathoms/pull/1068) + PR2 [#1070](https://github.com/davidrobert/mathoms/pull/1070) declaram `tx_carregadas`+`remocoes`+`exclusions`; [#1071](https://github.com/davidrobert/mathoms/pull/1071) a skill consome/prova. **Resta** PR2b (`needs_review` measure-then-emit) + PR3 (flip HARD) — soak WARN no dogfood |
| LC03 — E3→E4: 1 tx dropada (`Σtransacoes_total`=5724 vs `tx_total(_lineage)`=5723) sem declaração | categorização/conservação | Baixo | P3 | procede | procede-fechado | **resolvido** [#1065](https://github.com/davidrobert/mathoms/pull/1065): é o skip **intencional** info-fiscal-anual ([[ADR-242]]) no `TransactionClassifier`, não perda; regressão em `test_e4_intake_info_fiscal_skip.py` |
| LC04 — natural_key ausente em ~88% (cobertura 11,8%) → join sticky-override degradado | consistência | Médio | P2 (Learning Loop OFF no beta) | procede | procede-aberto | **onda aberta** — [[PLAN-data-lineage]] Onda 7 ([#1074](https://github.com/davidrobert/mathoms/pull/1074)), `pendente-agenda`; gate do flag Learning Loop ≥90%; fix titular no E3 ([[ADR-287]], nunca CPF no hash) |
| LC05 — `membro` é slug de **nome pessoal** usado como componente de identidade/dedup de investimento (e vazio quando o parse não atribui → causa raiz de LC01) | consistência | Médio | P2 | procede | procede-aberto | **onda aberta** — [[PLAN-data-lineage]] Onda 7 ([#1074](https://github.com/davidrobert/mathoms/pull/1074)); identidade por id estável ([[ADR-287]]); PR disjunto (não toca overrides) |
| LC06 — **[skill]** detector `investment_double_count` usa chave `(tipo\|inst\|descricao_norm)`; com descrição vazia agrupa produtos distintos do mesmo tipo/instituição → falso-positivo (5/6 colisões neste run) | consistência (skill) | Médio | P3 | procede | procede-fechado | **fechado** [#1063](https://github.com/davidrobert/mathoms/pull/1063) (`943682f2`): 2 vetores de identidade real — duplicata literal + snapshot stale cross-período (mesma identidade em ≥2 `data_referencia`), **membro fora da identidade**; lê `nome`/`ticker_norm`+`vencimento` (não `descricao`, ausente no E4); 8 testes |
| LC07 — **[skill]** verdict E2→E3 rotula sub-declaração de dedup como `perda-silenciosa` (P0) em vez de `coberto-sem-verificação`: o check `count_out<count_in` precede o cover-de-dedup; denominador inclui tx de `investment_report` não-reconciliável (10) | saúde-execução (skill) | Médio | P1 | procede | procede-fechado | **fechado** [#1063](https://github.com/davidrobert/mathoms/pull/1063) (`943682f2`): reordenado (queda de count com `dups>0` ⇒ coberto; só perda sem dedup declarado) + denominador exclui não-reconciliáveis (`should_skip` + doc-type `investment_report`/`informe_rendimentos`); 8 testes |
| LC08 — drift: 20 grupos só-persistidos com keying banco-vazio (`_extrato_*`) — a re-derivação re-chaveia com o guard empty-institution (A28.l8) | saúde-execução | Baixo | P3 | não-acionável | não-acionável | drift benigno (código melhorou); confirma r1·LC05 |

> **Atualização 2026-07-24** — LC06 e LC07 (hardening do núcleo puro da skill,
> não do pipeline) **fechados** em [#1063](https://github.com/davidrobert/mathoms/pull/1063)
> (`943682f2`): detector de dupla-contagem passa a exigir identidade real (mata o
> falso-positivo de descrição vazia) e o verdict E2→E3 rebaixa sub-declaração de
> dedup para `coberto-sem-verificação`.

> **Atualização 2026-07-24 (execução)** — achados de produto: **LC01 fechado** (#1073,
> [[ADR-346]] §4b) · **LC02 measure fechado** ([[ADR-347]]: #1065/#1068/#1070/#1071; resta
> PR2b/PR3 gated por soak) · **LC03 resolvido** (#1065, skip intencional [[ADR-242]]) ·
> **LC04/LC05** roteados e **onda aberta** ([[PLAN-data-lineage]] Onda 7, #1074,
> `pendente-agenda` P2). Fonte: plano [[PLAN-ledger-integrity]] §Estado.
