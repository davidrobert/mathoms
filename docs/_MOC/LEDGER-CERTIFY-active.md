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

> **Revisado em r3 (abaixo).** r2·LC01 (dedup membro-vazio) **holds** — 0 colisões
> em r3 (r3·LC09). r2·LC02 (E2→E3 remoções): **count fecha**, mas a dimensão-**valor**
> do dedup segue não-declarada → r3·LC06 (aberto até ADR-347 PR2). r2·LC03 (E3→E4
> info_fiscal): pipeline resolvido (#1065), mas o **harness** ainda emite o falso P0
> → r3·LC02 (lado-skill, novo). r2·LC04/LC05 (natural_key/membro) mantidos →
> r3·LC07 (cobertura 11,8%→12,1%).

---

## r3 — ws-1b9f2cf5-2026-07-27

> Skill ledger-certify ([[ADR-302]]) · run 5c030f1f. Re-derivação in-process E3+E4
> sobre E2 persistido — **zero write no DB provado** (`pipeline_artifacts`
> 11457→11457, `transaction_overrides` 12→12). Grupos E3: **91/105 `conservado`**
> (ledger de contagem declarado fecha tol-0, [[ADR-347]]), 14 `coberto` (0-tx).
> Baldes E4: 3/7 `conservado` (`despesas` 3544 tx, `receitas` 776 tx, `investimentos`
> 18 pos **0 colisões**), 4 fora-do-grão. Transferências netadas: 1239. natural_key:
> **12,1%** (754/6255). Drift vs persistido: 105 casados, **0 divergente** (a
> re-derivação bate 1:1 com o run mais recente). **Julgamento:** data-engineer +
> financial-planner em paralelo + verificação adversarial (**1/1 candidato a P0
> refutado** — o único `perda` é falso-positivo do harness). Cru + instância (PII)
> em `storage/<uuid>/ledger_certify/` (off-git).
>
> **DB vivo sob a cert:** um run novo aterrissou no meio da execução
> (`pipeline_artifacts` 11039→11457, workspace em dogfood ativo); todos os números
> vêm do snapshot r3 consistente, re-rodado após o novo run.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC01 — **[skill]** conservação de **VALOR** E3→E4 nunca é provada: `_e3e4_verdict` (`dev/ledger_conservation.py:163`) faz `val_in == val_out == despesas.total_geral + receitas.total_geral` (auto-referente) ⇒ uma queda de valor E3→E4 passaria em silêncio — o falso-verde que a skill existe pra pegar | conservação (skill) | Alto | P1 | procede | procede-aberto | harness-hardening: `val_in`=Σ cents E3 reconciliados (menos transferência+info_fiscal), `val_out`=Σ baldes E4 |
| LC02 — **[skill]** check de count E3→E4 emite falso `perda/dupla-contagem-silenciosa` (P0) no canal `info_fiscal_anual` ([[ADR-242]]): gap=1, **residual=0** (verificado), = 1 linha pulada em `transaction_classifier.py:312` (grupo `c6bank_investment_report_BRL_202503_202503`). Pipeline resolvido r2·LC03/#1065; harness nunca endurecido | conservação (skill) | Médio | P2 | procede | procede-aberto | harness-hardening: declarar o canal com o **mesmo predicado** `is_info_fiscal_anual` + termo explícito no `ConservationResult` (não hard-code −1) |
| LC03 — **[produto]** `receita_investimento` é balde catch-all **fora** de `_DEFAULT_ONE_TIME_CATEGORIES` (`fluxo_caixa_enricher.py:47`) ⇒ tratado como recorrente; 304 tx (39% das receitas) em perfil CDB-pesado funde retorno-de-principal/round-trip de corretora com rendimento → renda-fantasma recorrente (direção otimista) | categorização | Alto | P1 | procede | procede-aberto | camada-B: split por VALOR (juros vs principal vs ganho); corrompe fluxo + taxa de poupança (não TRS/IF — IRPF/goals-sourced) |
| LC04 — **[produto]** balde `aporte_investimento` efetivamente morto (1 tx / 3544 despesas) ⇒ mecanismo [[ADR-333]] (`despesa_consumo = despesa_total − aporte`) inerte ⇒ taxa de poupança não-confiável; ligado a LC03 por assimetria de round-trip de corretora | categorização | Alto | P1 | procede | procede-aberto | camada-B: witness entrada-recorrente↔saída-aporte/transferência por instituição de investimento (count+valor) |
| LC05 — **[produto]** `nao_identificado` = 460 despesas (13% por contagem) — materialidade por valor desconhecida; conta como consumo (deprime poupança) e pode esconder transferência/aporte | categorização/consistência | Médio | P2 (condicional a valor) | procede | procede-aberto | recomputar como **% de VALOR**; >~10% valor bloqueia seções fluxo/comportamental; <~5% degrada c/ disclaimer |
| LC06 — **[produto]** E2→E3 valor de dedup não-declarado (Δvalor não-provável, `coberto-sem-verificação`): dups declaradas por count, valor removido ausente do artefato. Continuação de r2·LC02 (count fechou; **valor** aberto) | conservação | Alto | P1 | procede | procede-aberto | [[ADR-347]] PR2 (artefato carrega `remocoes[canal].{count,valor_cents}` §Dec-2/4/6); bloqueia beta fechado (auditabilidade); harness re-derivar valor é interim |
| LC07 — **[produto]** natural_key cobertura 12,1% (754/6255) → ancoragem de override frágil (customer-facing) + lineage por membro; **não** quebra conservação (member_hashes all-or-nothing, [[ADR-287]]). Continuação de r2·LC04/LC05 | consistência | Médio | P1 se beta expõe override sticky / P2 read-only | procede | procede-aberto | [[PLAN-data-lineage]] Onda 7 (#1074) + ADR-321 (wiring titular) + **reancorar overrides antes** de abrir a feature; KR `k4_coverage_pct` c/ piso ≥90% |
| LC08 — **[skill]** harness não pondera por **VALOR** nem tem witness de assimetria de round-trip por instituição ⇒ LC03/LC04 não são quantificáveis por materialidade | conservação (skill) | Médio | P2 | procede | procede-aberto | harness-hardening: breakdown por valor + witness de assimetria entrada↔saída por instituição de investimento |
| LC09 — **[confirmação]** dupla-contagem de investimento **não ocorre** (0 colisões) — LC-02/#1073 ([[ADR-346]] §4b, membro-vazio) + detector/#1063 seguram | dedup/transferência | — | — | procede | procede-fechado | confirmação positiva de r2·LC01 |
| LC10 — **[refutado]** `receita_resgate` (18) como receita é benigno — **está** em `_DEFAULT_ONE_TIME_CATEGORIES`, excluído da renda recorrente; a fronteira "resgate como recorrente" já é mitigada por construção (sobre-leitura minha) | categorização | Baixo | P3 | refutado | refutado | auditar que resgate/venda/restituição não vaze p/ o balde recorrente |

> **Nota transversal (r3).** LC01/LC02/LC06/LC07 são instâncias do anti-silêncio da
> [[ADR-347]]: *toda transformação que remove/altera contagem ou valor declara o delta
> estruturalmente*. LC02 = canal E3→E4 faltando no harness; LC06 = dimensão-valor do
> canal E2→E3; LC01 = dimensão-valor E3→E4 **nunca instrumentada**; LC07 = discriminante
> de identidade que torna o delta atribuível por membro. **3 achados de skill**
> (LC01/LC02/LC08) recomendam uma lane de hardening do harness antes da próxima cert
> run — falso-positivo em ferramenta de certificação gateia beta e gera fadiga de
> alarme. **Insulação (financial-planner):** TRS/renda-passiva e projeção-IF são
> IRPF/goals-sourced, não E4-receita-sourced → LC03/LC04/LC05 corrompem só fluxo +
> taxa de poupança, não patrimônio/TRS/IF.

---

## r4 — ws-1b9f2cf5-2026-08-04

> Skill ledger-certify ([[ADR-302]]) · run 604f8816. Re-derivação in-process E3+E4
> sobre E2 persistido — **zero write no DB provado** (`pipeline_artifacts`
> 13626→13626, `transaction_overrides` 12→12). Grupos E3: **90/105 `conservado`**
> ([[ADR-347]], tol-0), 15 `coberto` (**todos** 0-tx). Baldes E4: `despesas` (21 cat,
> 3540 tx) + `receitas` (9 cat, 773 tx) + `investimentos` (18 pos, **0 colisões**)
> `conservado`; E3→E4 conserva count **e** valor (Δ=0). Drift vs persistido: 105
> casados, **0 divergente**. natural_key: **12,1%** (754/6247) — patamar de r3.
> **Julgamento:** data-engineer (2 rodadas, a 2ª revogando a 1ª) + financial-planner
> em paralelo + verificação adversarial (**1/1 candidato a P0 CONFIRMADO**, 5
> refutações mortas) + **`senior-cto` decidindo e fechando** (§Anti-loop) após 3
> rodadas convergirem em desenhos que a medição eliminou. Cru + instância (PII) em
> `storage/<uuid>/ledger_certify/` (off-git).
>
> **Camada A limpa; o P0 é de identidade e não é novo** — as 261 ocorrências
> cross-grupo são o **baseline já congelado** pela [[A40.l1]]; r4 reproduz byte-a-byte
> ⇒ **zero drift, zero progresso**. O valor de r4 é (a) materialidade, (b) causa-raiz,
> (c) eliminar 4 dos 5 desenhos de fix por medição.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC01 — **[produto]** duplicação cross-documento de sobreposição: mesma conta com múltiplos documentos-fonte de período sobreposto (um parseado nativamente, outro escalado ao LLM) rende 261 eventos 2× no E4 entregue = **~19% da receita** e **~8% da despesa**. Sum-preserving ⇒ passa por toda conservação. E5 consome E4 verbatim (`fluxo_caixa_enricher.py:283`, acumuladores `+=`) ⇒ **infla 1:1**, sem dedup a jusante | identidade/dedup | Alto | **P0** | procede (CONFIRMADO) | procede-aberto | [[A40.l2]] — **colapsador cross-documento por TRANSAÇÃO** (domain service puro, injetado com `default None` no `E3ReconcilerAdapter`, após `reconcile_with_report` e **antes** do agrupamento), chave provenance-free day-exact; sobrevivente = perna nativa |
| LC02 — **[produto]** a chave de agrupamento de artefato do E3 carrega o **período do documento** (`e3_serialization.py:136`) ⇒ duas pernas da mesma conta **nunca se encontram** no dedup, independente de identidade de transação. O E3 tem duas noções concorrentes de "mesma conta": `AccountGrouper.key()` é **period-free** ([[ADR-310]]) e o agrupamento de artefato é **period-bearing** — o repo tem a definição certa e agrupa pela errada | contrato de agrupamento | Alto | P1 | procede | procede-aberto | corolário novo da emenda [[ADR-354]]; regrouping period-free + balance selection por `max(period_end)` é lane própria (fecha a classe latente native↔native) · [[A42.l5]] |
| LC03 — **[produto]** o dedup existente exige descrição **bruta byte-idêntica** (`reconciliation_service.py:152`, sem `normalize_descricao`, ±3 dias) ⇒ teto de colapso **~48%** (126/261). Torna o desenho "fundir os grupos" um fix parcial que **fecha verde** pagando o preço máximo | dedup | Alto | P1 | procede | procede-aberto | não reusar `is_duplicate` no colapsador; usar a chave normalizada que já roda dentro do `_hash_v2` de produção |
| LC04 — **[produto]** colisão literal↔sentinela destrói informação: o token residual do contrato LLM (`e2_llm_extract.py:94`) é **byte-idêntico** ao default de "desconhecido" do código (`e3_serialization.py:99`,`:137`; `document.py:186`) ⇒ a jusante é **indecidível** se o dado disse ou o código defaultou (11 de 17 artefatos vêm do contrato, 6 do default). É defeito de **contrato**, não alucinação — o LLM cumpriu a instrução | contrato de identidade | Médio | P1 | procede | procede-aberto | [[A40.l2]] PR-B: sentinela reservado fora de `TIPO_CANONICAL` nos 3 sítios + `Literal[...]` em `document_type` validado no boundary |
| LC05 — **[skill]** `_non_ledger_verdict` (`dev/ledger_certify_core.py:161`) é catch-all com **default `coberto`**: conta containers que esses baldes não usam (`patrimonio` usa `itens`=67, não `dados`; `fluxo_mensal_detalhado` usa `meses_ordenados`=44) ⇒ imprime "0 itens · coberto" com o payload completo em mãos, e a glosa "fora do grão transacional" é **factualmente falsa** para `fluxo_mensal_detalhado` (sai de `result.cash_flow`, mesma população classificada). Carimba `coberto` sobre a dimensão de **62,5% do peso do score** | conservação (skill) | Alto | P1 | procede | procede-aberto | registry `{balde → checker \| não-verificável(motivo)}` com default **`não-verificável`**; + estender o drift (hoje só E3) para contagem por balde E4 — **guard que fecha a classe**, não a instância · [[A42.l3]] |
| LC06 — **[skill]** a rubrica declara a P0 nº 1 (dedup patrimonial [[ADR-271]]/[[ADR-246]]) coberta, mas o check que roda (`investment_double_count`) varre o balde E4 `investimentos` (18 pos, origem E2) — **população e vetor diferentes** de `investimentos_consolidados` do E1.5c (49 entradas, eixos cross-year/cross-declarante). P0 nº 1 **nunca exercitada** em r1–r4 | conservação (skill) | Alto | P1 | procede | procede-aberto | invariantes de **saída** (não reimportar os módulos de dedup — seria tautologia): PAT-1 (contribuição = `valores_31_12[max(ano)]`, nunca Σ anos, fechando contra o agregado publicado), IMO-1/2, INV-1/2, MEM-1 — **com partição de julgabilidade** e prova por mutação · [[A42.l3]] |
| LC07 — **[produto]** misclassificação E0 a montante **amplifica** (não causa) o carrier: doc de conta corrente classificado como outro tipo foi escalado ao LLM e rendeu 72 tx de conta corrente. Com E0 perfeito a classe **permanece** (banco emite mensal + consolidado anual da mesma conta) | ingestão (E0) | Médio | P1 | procede | procede-aberto | escopo da skill `parse-certify` ([[parse-certify-registry]]), lane separada; não bloqueia a l2. Ganho colateral: E0 correto manda o doc ao parser nativo ⇒ perna LLM deixa de existir · [[A42.l10]] |
| LC08 — **[produto]** `list_keys` (workspace-wide, `db_artifact_store.py:379`) e `read` (run-scoped, 3 degraus) **discordam de política de escopo** — a assimetria que [[ADR-291]] §Contexto documenta como causa-raiz e consertou só do lado do `read`. Efeitos: `_e3_validate_outputs` reporta 137 grupos escritos quando o run escreveu 105; e órfão de **keying** nunca recebe `retention_until` (retenção é key-scoped) ⇒ imortal | contrato de store / retenção | Médio | P1 (contrato) + P2 (GC) | procede | procede-aberto | paridade de política (mesma regra de 3 degraus) + guard reescrito **por expectativa**; escopar `list_keys` ingenuamente torna o guard de [[ADR-291]] D5 dead code e devolve o E4-vazio-silencioso. **GC depois do PR-D** — os órfãos são a pré-imagem da re-ancoragem · [[A42.l6]] |
| LC09 — **[produto]** o `artifact_key` rotula período que **subrepresenta o span real** (key de 1 mês transportando 13) porque o `periodo` do artefato LLM vem de um único `YYYYMM` expandido, enquanto `transacoes` carrega o PDF inteiro | ingestão (E2) | Médio | P2 | procede | procede-aberto | derivar `periodo` do span real das tx (`extract_with_llm.py:438`); ordem 5 da trilha decidida · [[A42.l6]] |
| LC10 — **[produto]** natural_key 12,1% — 88% dos ajustes manuais sem âncora estável. Continuação de r3·LC07 (sem mudança) | consistência | Médio | P1 | procede | procede-aberto | **não abrir lane**: mesma causa do LC01/LC04 e [[A40.l2]] PR3 é o vetor. Gate de beta correto **não é cobertura ≥X%** e sim **nenhum override ativo sem âncora** (recusar a promoção no ato > aceitar e perder em silêncio) |
| LC11 — **[refutado]** acreção de E3 stale (137 grupos latest-per-key de 9 runs) **não** causa dupla-contagem em produção: E3 não está em `_WORKSPACE_SCOPED_STAGES` ([[ADR-241]] rejeitou explicitamente) ⇒ órfão de run anterior retorna `None` nos 3 degraus do `read` e é descartado. As sobreposições que eu medi vinham do próprio `_persisted_e3_by_key` do harness (workspace-latest **por desenho**, para o drift) | contrato de store | Baixo | P3 | refutado | refutado | sobre-leitura minha; o defeito real virou LC08 |
| LC12 — **[refutado]** "skip silencioso do E2-LLM" **não é a causa** desta duplicação — aquele defeito é o **inverso** (doc escalado morria sem LLM) e já foi corrigido (`extract_with_llm.py:76-81`, [[ADR-342]]). **Nenhum documento foi extraído duas vezes**: o nativo emitiu stub e o LLM pegou o doc **uma** vez | ingestão | — | — | refutado | refutado | o invariante ausente não é "um extrator por documento" e sim "**um razão canônico por conta, idempotente sob cobertura redundante**" |
| LC13 — **[confirmação]** o eixo **patrimônio não se move** neste defeito: a perna LLM não tem campo de saldo ⇒ `saldo_final_unknown=True` ⇒ `e5_analyzer_adapter.py:896` **já a pula**. Hoje o caixa **não** é duplicado; a contaminação é **só do eixo de fluxo** | conservação | — | — | procede | procede-fechado | é o que desacopla a instrumentação de patrimônio do caminho crítico da l2 — **e** o argumento decisivo contra fundir (fundir insere statement sem saldo; por `stmts[-1]` posicional, apagaria a conta inteira) |

> **Nota transversal (r4).** O eixo novo desta rodada é **identidade sob cobertura
> redundante**, não conservação: LC01/LC02/LC03/LC04 são quatro camadas do mesmo
> defeito — dois documentos legítimos da mesma conta, um escalado ao LLM, que o razão
> trata como duas contas porque a chave de grupo carrega período **e** um sentinela de
> ausência. **Quatro dos cinco desenhos de fix foram eliminados por medição** (alias-map
> e fail-closed pela [[A40.l1]]/r4; fail-closed em `account_type` e fundir por medição
> desta rodada) — a cobertura de contraparte é **50,88%**, então quarentenar vocabulário
> desconhecido apagaria ~252 rows de fonte única/órfãs, e fundir colapsaria só ~48%.
> **Anti-Goodhart:** o critério de aceite da l2 usa **banda** `[259,261]`, não ponto
> fixo, porque o instrumento é estimador com piso irrefutável 126 (descrição bruta) —
> e adiciona **conservação de população** como ratchet para o desenho fail-closed não
> voltar por acidente. **2 achados de skill** (LC05/LC06) são falso-verde de escopo
> **para dentro**: a skill carimbou `coberto` na dimensão de 62,5% do peso do score e
> nunca exercitou a P0 nº 1 da própria rubrica em 4 rodadas — precedente direto do
> "critério derivado de contador exige ler o código". **Insulação (financial-planner),
> revista:** TRS/renda-passiva/projeção-IF seguem IRPF/goals-sourced ⇒ insulados de
> LC01; mas **todos expostos ao patrimônio** ⇒ a insulação **transfere** o risco, não o
> reduz. E as duas pernas de LC01 **não se cancelam**: na taxa de poupança o viés é
> otimista sempre que a família gasta >25% da receita; na folga mensal as pernas
> **somam** (a parte pontual do débito duplicado se cancela dentro do parêntese e não
> reduz a folga); na reserva o cancelamento é estruturalmente impossível. Sintoma de
> produto: o relatório afirma folga confortável **e** reserva insuficiente ao mesmo
> tempo — incoerência interna visível ao usuário.
