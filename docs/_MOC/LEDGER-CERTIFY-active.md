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
| LC01 — **[produto]** duplicação cross-documento de sobreposição: mesma conta com múltiplos documentos-fonte de período sobreposto (um parseado nativamente, outro escalado ao LLM) rende 261 eventos 2× no E4 entregue = **~19% da receita** e **~8% da despesa**. Sum-preserving ⇒ passa por toda conservação. E5 consome E4 verbatim (`fluxo_caixa_enricher.py:283`, acumuladores `+=`) ⇒ **infla 1:1**, sem dedup a jusante | identidade/dedup | Alto | **P0** | procede (CONFIRMADO) | procede-parcial-fechado (2026-08-14) | [[A40.l2]] **shipped** #1368 — enforce no E3 persistido (453 rows cortadas). Residual da própria l2: o instrumento sombra re-deriva E3 do E2 e **ainda reporta 261**. Números da abertura são fotografia 2026-08-04 |
| LC02 — **[produto]** a chave de agrupamento de artefato do E3 carrega o **período do documento** (`e3_serialization.py:139-144`, conferido 2026-08-14; a âncora `:136` driftou) ⇒ duas pernas da mesma conta **nunca se encontram** no dedup, independente de identidade de transação. O E3 tem duas noções concorrentes de "mesma conta": `AccountGrouper.key()` é **period-free** ([[ADR-310]]) e o agrupamento de artefato é **period-bearing** — o repo tem a definição certa e agrupa pela errada | contrato de agrupamento | Alto | P1 | procede | procede-aberto | [[ADR-354]] agora `Decidido`; regrouping period-free + balance selection por `max(period_end)` · [[A42.l5]] (dep [[A40.l2]] quitada #1368) |
| LC03 — **[produto]** o dedup existente exige descrição **bruta byte-idêntica** (`reconciliation_service.py:152`, sem `normalize_descricao`, ±3 dias) ⇒ teto de colapso **~48%** (126/261). Torna o desenho "fundir os grupos" um fix parcial que **fecha verde** pagando o preço máximo | dedup | Alto | P1 | procede | procede-aberto | não reusar `is_duplicate` no colapsador; usar a chave normalizada que já roda dentro do `_hash_v2` de produção · [[A42.l5]] (contexto de desenho do colapsador) |
| LC04 — **[produto]** colisão literal↔sentinela destrói informação: o token residual do contrato LLM (`e2_llm_extract.py:94`) é **byte-idêntico** ao default de "desconhecido" do código (`e3_serialization.py:99`,`:137`; `document.py:186`) ⇒ a jusante é **indecidível** se o dado disse ou o código defaultou (11 de 17 artefatos vêm do contrato, 6 do default). É defeito de **contrato**, não alucinação — o LLM cumpriu a instrução | contrato de identidade | Médio | P1 | procede | procede-aberto · **âncoras stale (2026-08-14)** | path `e2_llm_extract.py` não resolve; default de `account_type` em `e3_serialization.py:137` agora é `"extrato"`, não `"desconhecido"`. KR-C da [[A42]] ainda mede o achado; **re-medir o mecanismo na abertura** antes de implementar · [[A42.l5]] |
| LC05 — **[skill]** `_non_ledger_verdict` (`dev/ledger_certify_core.py:170`, era `:161`) é catch-all com **default `coberto`**: conta containers que esses baldes não usam (`patrimonio` usa `itens`=67, não `dados`; `fluxo_mensal_detalhado` usa `meses_ordenados`=44) ⇒ imprime "0 itens · coberto" com o payload completo em mãos, e a glosa "fora do grão transacional" é **factualmente falsa** para `fluxo_mensal_detalhado` (sai de `result.cash_flow`, mesma população classificada). Carimba `coberto` sobre a dimensão de **62,5% do peso do score** | conservação (skill) | Alto | P1 | procede | procede-aberto | registry `{balde → checker \| não-verificável(motivo)}` com default **`não-verificável`**; + estender o drift (hoje só E3) para contagem por balde E4 — **guard que fecha a classe**, não a instância · [[A42.l3]] (dep [[A40.l2]] quitada #1368) |
| LC06 — **[skill]** a rubrica declara a P0 nº 1 (dedup patrimonial [[ADR-271]]/[[ADR-246]]) coberta, mas o check que roda (`investment_double_count`) varre o balde E4 `investimentos` (18 pos, origem E2) — **população e vetor diferentes** de `investimentos_consolidados` do E1.5c (49 entradas, eixos cross-year/cross-declarante). P0 nº 1 **nunca exercitada** em r1–r4 | conservação (skill) | Alto | P1 | procede | procede-aberto | invariantes de **saída** (não reimportar os módulos de dedup — seria tautologia): PAT-1 (contribuição = `valores_31_12[max(ano)]`, nunca Σ anos, fechando contra o agregado publicado), IMO-1/2, INV-1/2, MEM-1 — **com partição de julgabilidade** e prova por mutação · [[A42.l3]] |
| LC07 — **[produto]** misclassificação E0 a montante **amplifica** (não causa) o carrier: doc de conta corrente classificado como outro tipo foi escalado ao LLM e rendeu 72 tx de conta corrente. Com E0 perfeito a classe **permanece** (banco emite mensal + consolidado anual da mesma conta) | ingestão (E0) | Médio | P1 | procede | procede-aberto | escopo da skill `parse-certify` ([[parse-certify-registry]]), lane separada; não bloqueia a l2. Ganho colateral: E0 correto manda o doc ao parser nativo ⇒ perna LLM deixa de existir · [[A42.l10]] |
| LC08 — **[produto]** `list_keys` (workspace-wide, `db_artifact_store.py:379`) e `read` (run-scoped, 3 degraus) **discordam de política de escopo** — a assimetria que [[ADR-291]] §Contexto documenta como causa-raiz e consertou só do lado do `read`. Efeitos: `_e3_validate_outputs` reporta 137 grupos escritos quando o run escreveu 105; e órfão de **keying** nunca recebe `retention_until` (retenção é key-scoped) ⇒ imortal | contrato de store / retenção | Médio | P1 (contrato) + P2 (GC) | procede | procede-aberto | paridade de política (mesma regra de 3 degraus) + guard reescrito **por expectativa**; escopar `list_keys` ingenuamente torna o guard de [[ADR-291]] D5 dead code e devolve o E4-vazio-silencioso. **GC depois do PR-D** — os órfãos são a pré-imagem da re-ancoragem · [[A42.l6]] |
| LC09 — **[produto]** o `artifact_key` rotula período que **subrepresenta o span real** (key de 1 mês transportando 13) porque o `periodo` do artefato LLM vem de um único `YYYYMM` expandido, enquanto `transacoes` carrega o PDF inteiro | ingestão (E2) | Médio | P2 | procede | procede-aberto | derivar `periodo` do span real das tx (`extract_with_llm.py:438`); ordem 5 da trilha decidida · [[A42.l5]] |
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
>
> ⚠️ **Anotação 2026-08-30 — a nota acima fica como está (é medição do r4, 2026-08-04),
> mas o mecanismo que ela descreve deixou de existir.** "A parte pontual se cancela
> dentro do parêntese" fala do parêntese da fórmula antiga da folga —
> `receita_rec_mensal − (despesa_mensal_media − pontuais_janela/n)` —, onde a perna
> pontual do débito duplicado entrava nos dois termos. A [[ADR-422]] D1 (#1828,
> 2026-08-29) eliminou o parêntese: `folga_mensal = receita_recorrente_mensal −
> despesa_consumo_mensal`, sem termo de pontuais. **O dimensionamento de LC01 sobre a
> folga precisa ser refeito** contra a fórmula nova antes de ser citado de novo — as
> pernas podem não somar mais da mesma forma. As outras duas (taxa de poupança,
> reserva) não dependem do parêntese e seguem valendo.

---

## r5 — ws-1b9f2cf5-2026-08-26

> Rodada unificada **U1** ([[ADR-416]]) · [[PIPELINE-REVIEWS-active]] §r9 · [[REPORT-REVIEWS-active]] §r5.
> Run `c97b97c2` `completed` 18/18 · executor `1eb6a8bf` · modo **entregue** (`--entregue --run`)
> sobre o E3 persistido do run pinado, com a sombra no mesmo processo.
> Zero-write provado (artefatos e overrides idênticos antes/depois).
> Cru + síntese com valores: `storage/<uuid>/reviews/U1-2026-08-26/` (off-git).
> Cobertura: matriz dimensão × registro — 2 células declaradas N/A sem motivo escrito
> (§Débito de método do [runbook](../reference/runbooks/unified_certify_review.md)).

**Manchete: o enforce da [[A40.l2]] funciona no artefato entregue, e a KR-B não fecha por
um motivo que o próprio harness imprime.** Primeira medição com sombra e entregue no mesmo
run: numerador cross-grupo **317 → 7** (−97,8%), com `cobertura=OK` nos dois. O carrier
`tipo_conta` fechou por inteiro. O critério da KR-B exige `entregue=0`; o residual é **uma
classe única** e o bloco de paridade da camada já o nomeia — `só no detector 7 ⚠️ PONTO CEGO`.

**A causa-raiz mudou o alvo do fix.** O colapsador e o detector derivam `direction` de
funções diferentes: o detector usa o balde E4; o colapsador chama `derive_direction` com
`tipo=None`, inferindo do sinal — exatamente o que o contrato da função proíbe por escrito
("não derivar do sinal cru: fatura inverte"). O docstring do colapsador afirma chave
idêntica à do detector; é falsa no 4º componente. **O residual não está bloqueado por falta
de entrada de whitelist — está bloqueado porque o remediador não enxerga a classe.**

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC5-01 — colapsador e detector derivam `direction` de funções distintas (`ledger_cross_group.py:21` usa o balde E4; `cross_document_collapser.py:125-129` passa `tipo=None` a `derive_direction`, contra o contrato em `_tx_identity.py:139`); o residual do numerador KR-B é 100% ponto cego do remediador | correção | Crítico | P0 | procede (causa-raiz fechada; reclassifica LC-01 do §r4) | procede-aberto | paridade de chave, **não** whitelist: `_collapse_key` honra `tipo`, ou o detector deriva pela mesma função. Teste de paridade sobre corpus com estorno de fatura · **dona [[A42.l5]]** |
| LC5-02 — `layer_ok` sai verde com PONTO CEGO impresso a duas linhas: `paridade_fecha` é auto-identidade (partição do próprio conjunto do colapsador), e `sem_ponto_cego` existe **fora** do predicado agregado (`ledger_collapse_layer.py:68-70`, `:90-99`) | contrato | Alto | P0 | procede (novo) | procede-aberto | `layer_ok` inclui `sem_ponto_cego`; se o ponto cego for tolerado, o token verde muda de nome e o gate lê o específico · **dona [[A42.l3]]** |
| LC5-03 — o checksum por grupo prova auto-consistência do produtor, não conservação E2→E3: `_ledger_verdict` lê três campos escritos pelo mesmo produtor e `carregadas` nunca é confrontado com o input E2. 97/97 grupos saem `conservado` ao lado de "E2→E3: count não fecha" | contrato | Alto | P0 | procede (novo) | procede-aberto | ancorar `carregadas` fora do artefato; sem reconciliar, teto do grupo é `coberto-sem-verificação` · **dona [[A42.l3]]** |
| LC5-04 — o veredito E2→E3 afirma "resíduo = perda" sem computá-lo, e o sinal está invertido: as exclusões declaradas **excedem** o gap em 13 rows, e há 23 rows entre "semeado" e "conservação" sem linha que as declare | contrato | Alto | P1 | procede (novo) | procede-aberto | imprimir a cadeia inteira com resíduo **assinado** e falha dura em resíduo ≠ 0; `dups` sai da linha do gap |
| LC5-05 — o artefato E3 carrega dois contadores de dedup que discordam: o campo escalar soma 543 e está populado em 3 grupos; `Σ remocoes[].count` soma 1153 e está populado amplamente | contrato | Alto | P1 | procede (novo) | procede-aberto | um só contador no contrato (`remocoes{}` tem motivo); deprecar o escalar com invariante durante a janela |
| LC5-06 — o catch-all `_non_ledger_verdict` carimba `coberto` em balde que não sabe ler: procura três containers e o payload de `patrimonio` e de `fluxo_mensal_detalhado` não tem nenhum ⇒ "0 itens · coberto" com o payload completo em mãos | conservação | Alto | P1 | procede (LC05 do §r4 reproduzido no U1) | procede-aberto | dona [[A42.l3]] · registry `{balde → checker \| não-verificável(motivo)}` com default `não-verificável`. Override aplicado nesta rodada em 2 baldes; `seguros` e `pontos_milhas` **não** se rebaixam · **dona [[A42.l3]]** |
| LC5-07 — o eixo E3 rotula `n_tx` um número que é `total + dups` (`ledger_certify_core.py:197-202`); o bloco de drift compara inflado contra inflado | clareza-ux | Médio | P2 | procede (novo) | procede-aberto | imprimir os dois, ou renomear. Nome que promete contagem de transação entrega contagem de transação |
| LC5-08 — o comparador vetorial mede janela **cortada** contra razão **cru** e emite divergência falsa: o enricher reatribui as séries ao resultado do corte de provisionado antes de janelar (`fluxo_caixa_enricher.py:341-346` → `:376`), e o razão soma o artefato E4 pré-corte | contrato | Alto | P1 | procede (mecanismo fechado; **refuta** a leitura inicial de defeito de produto) | procede-aberto | o comparador aplica `split_provisionado` ao razão antes de somar e declara a data de corte; delta residual pós-corte vira falha dura |
| LC5-09 — 31 grupos só no persistido carregam **prefixo de banco vazio** na `artifact_key`, e os 4 grupos com drift de contagem concentram exatamente a massa do colapso da camada | consistência | Médio | P2 | procede (novo) | procede-aberto | invariante no adapter: o write do E3 nunca persiste `banco` vazio quando o E2 o traz |
| LC-02 (§r4) — cobertura de `natural_key` | consistência | — | — | **rebaixado a sintoma** | fecha como achado próprio | a elegibilidade é computada **uma vez por artefato**: artefato com `banco` ou `titular` vazio perde 100% das chaves. A queda medida não é regressão gradual — é um punhado de artefatos virando o bit, e é LC5-01/LC5-09 medidos de outro ângulo |

**Atribuição fechada por medição — 2026-08-26, mesmo run.** O `LC5-01` deixa de ser mecanismo
nomeado e passa a ser **atribuição integral**, e o escopo é maior do que o numerador sugeria.

- **As 7 do numerador: 7/7, 14/14 rows.** Para cada ocorrência, o `direction` do detector
  (`debit`, vindo do balde `despesas`) contra `derive_direction(tipo=None, valor, tipo_conta)`
  do colapsador (`credit`). **Zero coincidências, zero indeterminadas.** Todas com a mesma
  assinatura: conta não-`fatura`, valor guardado positivo — `_infer_tipo` devolve `credito`
  porque o balde E4 carrega **magnitude**, e o `abs` da despesa destrói o sinal que a
  inferência precisa. O comentário em `ledger_cross_group.py:18` nomeia essa exata razão para
  o detector **não** derivar do item; o colapsador deriva.
- **A divergência é sistemática, não confinada:** **1.591 de 4.296** rows transacionais do run
  (**37,0%**) são mis-chaveadas, todas no sentido `debit`→`credit`. Por `tipo_conta`:
  `extratoconta` 1.353 · `extrato` 201 · variantes USD/EUR/global 35 · `investment_report` 2.
  As 754 rows de receita **coincidem** — não há divergência no sentido inverso.

**O que isso muda.** As 7 são a ponta visível: o subconjunto do mis-chaveamento que também é
colisão cross-proveniência. O fix não destrava 7 ocorrências — **corrige a chave de mais de um
terço do corpus transacional**, e é o que explica a assimetria nos dois sentidos que o bloco
de paridade reporta (`só no detector 7` · `só no colapsador 84` · `154 rows fora do campo de
visão do detector`).

**Sinal adjacente, não perseguido:** dentro de `despesas`, 1.951 rows **coincidem** — ou seja,
o balde carrega valores com convenção de sinal mista. Registrado para quem pegar o fix; não é
o defeito desta linha.

**Re-medir com:** `dev/certify_ledger_local.py <ws> --entregue --run <id>` para o numerador, e o
join `direction do balde × derive_direction(tipo=None, …)` sobre `X._tx_rows(baldes)` para a
população. Ambos read-only.

**Refutados / reenquadrados nesta rodada.** A divergência de receita entre janela e razão
**não** era defeito de produto (LC5-08). O mês futuro na série do razão é E3/E4 **correto por
desenho** — o provisionado é fato e fica no ledger; o E5 já corta — logo reportá-lo como
defeito sugeriria a correção errada (truncar o ledger).

**Positivos verificados.** Zero-write do harness provado por contagem antes/depois ·
determinismo do categorizador sobre o E3 do próprio run **fecha ao centavo** nos dois baldes
transacionais, com o pin de overrides estável ⇒ sem confundidor de drift de regra aprendida ·
E3→E4 conserva count e valor.

## r6 — ws-1b9f2cf5-2026-08-29

> Rodada unificada **U2** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r6 (este) · [[PIPELINE-REVIEWS-active]] §r10 · [[REPORT-REVIEWS-active]] §r6.
> Run `79a61e33` `completed` 18/18 · 25,5 min · executor `887579734428` · report `c011c40c` · preflight: 4 WARN declarados.
> Modo **entregue** (`--entregue --run`) sobre o E3 persistido do run pinado, sombra no mesmo processo. Zero-write provado.
> Cru + síntese com valores: `storage/<uuid>/reviews/U2-2026-08-29/` (off-git).
> Cobertura: matriz 7×3 — **3 células declaradas SEM COBERTURA com motivo escrito** (`LEDGER × clareza-ux`, `LEDGER × qualidade-llm`, `PIPELINE × clareza-ux`) + 1 declarada N/A por roteamento.
> Céticos: 3 lotes · **2 REFUTADO / 14 PARCIAL / 2 CONFIRMADO** — nenhum dos 18 sobreviveu na forma escrita.

**Manchete: o veredito de conservação desta skill nunca descreveu o artefato entregue, e
descobrir isso invalidou a própria F3.a da rodada.** `ledger_certify_core.py:247` chama
`_conservation(e2_payloads, **fresh_e3**, …)` e o docstring do montador declara *"a partir
das peças **re-derivadas**"*. O `persisted_e3` entra em `build_report` e é consumido **só**
em `_drift` — logo `e3_groups`, `e4_buckets`, `investment_collisions` e `natural_key`
**também** descrevem a re-derivação. O `--entregue` cobre **uma** linha (o numerador KR-B).
No mesmo relatório o drift é ≠ 0: 4 grupos com count divergente e 31 só-no-persistido.

**A régua que reprova é decisão registrada, não defeito — e a rodada quase vendeu uma
como a outra.** A F3.a publicou que `coberto-sem-verificação-de-valor` é o único veredito
emissível *"independentemente da qualidade do dado"*. **Falso:** com `dups == 0` o índice 0
emite `perda-silenciosa`; com `count_out > count_in` o índice 2 emite. O veredito é
constante **enquanto** `count_out < count_in and dups > 0` — estado do corpus, não
propriedade do instrumento. E o docstring de `_e2e3_verdict` declara essa ordem como
**decisão** (`"A ORDEM importa… sub-declaração ⇒ não perda (LC-07)"`).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC6-01 — os vereditos de conservação, os grupos E3, os baldes E4, a colisão de investimento e a cobertura de `natural_key` são computados sobre a **re-derivação**, não sobre o artefato que o run publicou; `persisted_e3` só alimenta `_drift`, e `_persisted_e3_by_key` é **workspace-latest, não run-scoped** (existe `_e3_of_run` ao lado, não usado) | correção | Crítico | P0 | procede (novo) · verificado no código | procede-aberto | `certify` recebe o par (fresco, entregue) e emite **duas** colunas, ou o entregue vira o default e o fresco vira o drift. Enquanto não, nenhuma linha desta skill pode ser citada como propriedade do artefato entregue — inclusive os 31 "só-no-persistido", que podem ser sobra de outro run · **gatilho: [[ADR-421]] `Proposto`** — a incógnita fechou (são sobra; 31/31), ver §`LC6-01` abaixo |
| LC6-02 — `investment_id` é `sha256(tipo, instituicao, descricao)[:16]` sobre campos que o extrator LLM reescreve, e nenhum dos três passa pelo `institution_catalog` que já existe no DB; entre dois runs do mesmo documento a identidade tem **23,5% de estabilidade** | correção | Alto | P0 | PARCIAL (a [[ADR-271]] já declara "não estável a rename"; **a classe é nova** — ela previu instabilidade entre ANOS, não entre dois runs do mesmo documento) | procede-aberto | canonicalizar `instituicao` contra o [[ADR-137]] **antes** do hash — única das 3 entradas com catálogo, e **não** reabre o resolver persistido que a [[ADR-271]] §140 rejeitou. **Dano vivo não é estado persistido** (`rg investment_id backend/app/models/ alembic/` → zero): é `compare_reviews.py` ([[ADR-406]] D7), cujas 2 pernas HARD cross-run disparam com exatamente esta churn ⇒ **gate de migração patrimonial disparando com ruído de extrator** |
| LC6-03 — cobertura de `natural_key` em **7,0%** (482/6928) é **regressão de wiring**, não design: a [[ADR-287]] **retratou por emenda datada** a premissa "classe-c por design PII-zero", e a [[ADR-321]] nomeia *"regressão desde A7/[[ADR-134]]"* — e está **`Proposto`, nunca implementada** | correção | Alto | P1 | PARCIAL (não é degradação nova: 8,2% em jul → 7,0% agora) · **eleva a severidade que a lente havia rebaixado** | procede-aberto | impacto que a [[ADR-321]] §Contexto nomeia: dedup v2 sem discriminação por membro ⇒ **casal no mesmo banco colapsa tx idênticas**, e overrides ancorados em hash com titular vazio. A premissa "~92% é o esperado" **não pode voltar a ser usada** — ela já foi retratada |
| LC6-04 — dois dos cinco canais de remoção emitem `valor_cents` **literal 0**, e o produtor descarta o dado antes: `anachronic_guard` faz `dropped.append(tx_date)` — guarda **só a data**. O schema `$defs/remocao` declara o campo `required` ⇒ **obriga-o a existir e não pode obrigá-lo a ser verdadeiro** | contrato | Médio | P2 | CONFIRMADO · rebaixado de Crítico (o gate é **fail-closed**: degrada para `coberto`, nunca vira `conservado` falso) | procede-aberto | measure-then-emit no guard. **Resíduo que vale mais:** o docstring difere a captura "ao PR2b", e o `PR2b` do plano canônico tem **escopo outro** ⇒ deferimento sem §Deferimento datado, sem dono, invisível aos gates, com a lane de origem `shipped` |
| LC6-05 — a base de consumo pontual inclui **aporte e transferência interna**, e o parecer emite risco de "gastos pontuais elevados" sobre uma base que contém o próprio aporte — pedindo que a família contenha o comportamento pelo qual é elogiada duas seções antes | correção | Alto | P1 | procede (MEDIÇÃO-DE-CONHECIDO de `PV9-11`/`PV9-12`; o **consumidor** é novo) | procede-aberto | o separador de transferência patrimonial **existe** e é aplicado à janela 12m; não é aplicado à janela que produz `total_pontuais`. Uma aplicação, dois pontos. ⚠️ **Retificação 2026-08-30:** esta frase estava riscada aqui pelo #1840 e **a retirada do risco é o conserto** — ela é verdadeira sobre o separador que nomeia (`transfer_categories` é aplicado em `fluxo_caixa_enricher.py:510` e ausente em `_collect_candidates`). O que se acrescenta é outro contável, não uma correção dela: são TRÊS **produtores de "gasto pontual"** com filtros disjuntos — enricher (`{aporte_investimento}`), a **lista** do card (`consumo_pontuais.py::_is_pontual`, que aplica `InternalTransferDetector`) e o **KPI** (`_collect_candidates`, que não aplica nenhum dos dois). Portar só `transfer_categories` não remove transferência interna nem `nao_identificado` (57,5% da janela no dogfood). Dono: [[A40.l98]] |
| LC6-06 — aporte e amortização entram em `despesa_total` na janela cheia, e daí sai uma **terceira** taxa de poupança publicada na mesma peça, menor que as outras duas porque conta o dinheiro poupado como gasto | consistência | Médio | P2 | procede (MEDIÇÃO-DE-CONHECIDO de `PV9-11`) | procede-aberto | aporte é transferência patrimonial; da parcela de financiamento só os juros são despesa |
| LC6-07 — a lista de gastos pontuais publica ~~**dois pares duplicados** (mesma data, mesma categoria, mesmo valor,~~ **UM par** (datas D e D+1, mesma categoria e valor, descrição diferindo por prefixo verbal) sob o cabeçalho que afirma *"contamos cada um uma vez só"* | correção | Alto | **P2** | procede · **re-enunciado 2026-08-30** | procede-aberto · dono [[A40.l102]] | é a lista mais escrutinável do relatório pelo cliente, e alimenta o contador de pontuais e o "equivalente em meses de aporte" |
| LC5-01 · LC5-02 · LC5-03 · LC5-06 · LC5-09 (§r5) | — | — | — | **reproduzidos neste run, sem alteração** | procede-aberto | numerador KR-B **7**, `carrier-shaped 7/7`, classe única `banco=<instituição>\|tipo_conta=extrato\|titular=parcial` · `layer_ok=true` **com PONTO CEGO impresso** · 31 grupos com prefixo de banco vazio · 4 baldes rebaixados por override LC05 |
| LC5-04 · LC5-05 · LC5-07 · LC5-08 (§r5) | — | — | — | **procede-aberto (não re-medidos)** | registrado para não decaírem em silêncio | — |

**Re-enunciado do `LC6-07` — 2026-08-30.** As duas metades do enunciado original são
falsas, medido nos itens do report `c011c40c`:

- **Não é "mesma data".** O par difere em 1 dia — `2025-10-26` em `C6Bank (extratoconta)`
  e `2025-10-27` em `c6bank (extrato)`: mesmo banco, **documentos-fonte distintos**, mesmo
  valor, mesmo beneficiário. É assinatura de D+1 entre dois documentos, não dois lançamentos
  idênticos.
- **Não são "dois pares".** Por `(data, categoria, valor)` dá **0** grupos; por
  `(mês, categoria, valor)` dá **1**; por `(mês, valor)` dá 2, mas o segundo é falso —
  beneficiários distintos. E o grupo verdadeiro carrega um **terceiro** item legítimo
  (`PDV*BARA CLINICA`, outro documento): chave por mês+valor colapsaria os três.

⚠️ **A primeira análise mediu CÓDIGO MORTO** — `transaction_signature`/
`deduplicate_transactions`, cujo único chamador `reconcile_account` não tinha chamador
nenhum, e cujo teste próprio (`tests/test_e3_dedup.py`) as mantinha verdes. Ela concluiu
"só a data separa"; no caminho vivo o par falha em **cinco** cláusulas, em dois mecanismos
com cegueiras complementares (`is_duplicate` tolera ±3 dias mas exige descrição idêntica;
o colapsador normaliza a descrição mas é day-exact). O cluster morto foi deletado.

**Severidade rebaixada de Alto/P1 para P2** e a promessa verificada: `_le_consolidacao` só
emite `consolidacao_cross_documento` com `count > 0`, e com enforce desligado a chave é
omitida — a nota *"contamos cada um uma vez só"* **não aparece**. Não há P0 de copy. É 1 par
em 89 itens (0,76% da janela) contra 63,2% de base não classificada — duas ordens de
grandeza menor, e o único item do lote que **destrói dado** se consertado de forma errada.

**Roteamento de 2026-08-30.** Das sete linhas `procede-aberto` do §r6, **quatro** (`LC6-04` a
`LC6-07`) estavam sem dono e sem link — a regra deste arquivo exige gatilho. `LC6-01`/`LC6-02` já
tinham rota para a A42 e `LC6-03` já tinha gatilho na [[ADR-321]]. Sem reescrever a
tabela (é evidência datada, [[ADR-343]]):

| linha | dono | nota |
| --- | --- | --- |
| `LC6-03` | [[ADR-321]] (`Proposto`) | já tinha gatilho; **não** entra no lote |
| `LC6-04` | **[[PLAN-ledger-integrity]]** §Deferimento datado 2026-08-30 (dono `data-engineer`) | o `PR2b` recolhia DOIS trabalhos e só um estava nomeado; agora o plano exige as duas pernas antes do `done` |
| `LC6-05` | **[[A40.l98]]** (aberta 2026-08-30) | re-enunciada acima: são três produtores, não dois |
| `LC6-06` | **[[A40.l98]]** | mesma família de base (aporte/amortização no denominador) |
| `LC6-07` | **[[A40.l102]]** | re-enunciado acima: é **um** par, D e D+1. Measure-first, sem enforce |

`LC6-01`/`LC6-02` já estavam roteadas para a A42 ([[A42.l14]], [[A42.l3]], [[A42.l15]]).

**Positivos verificados.** Zero-write provado (artefatos e overrides idênticos antes/depois) ·
**determinismo do categorizador fecha ao centavo sobre o E3 persistido do próprio run**:
2.289 células em `(balde, categoria, mês)`, **zero divergentes**, com pin de
`transaction_overrides` estável ⇒ sem confundidor de regra aprendida · E3→E4 conserva
count e valor · a consolidação declarada no E4 bate com a executada no E3 (907 == 907).

**Refutados nesta rodada.** As convenções de sinal dos 4 canais de remoção **são
coerentes** (cents assinados, mesma convenção declarada; o negativo do cross-file é
composição líquida de débitos, não sinal trocado) — resíduo real é haver **duas
implementações** do mesmo primitivo sem teste que amarre a igualdade · o `StageSpec.writes`
falso **não é load-bearing**: mutação com `writes=()` e com `writes=("xpto_inexistente",)`
passa em `validate_full_order` nos dois casos · o fallback de auto-leitura do
`consolidate_baseline` é **inalcançável na config corrente**, e a omissão da auto-leitura
em `reads` **não é negligência** (incluí-la quebra o import).

### `LC6-01` — ataque de 2026-08-29: a incógnita fechou, e a direção do fix está decidida

> Sessão de ataque dedicada ([[ADR-421]] `Proposto`). **A tabela acima não é
> reeditada** — snapshot datado é evidência ([[ADR-343]]). Este bloco registra o que
> se mediu depois dela. Evidência reprodutível off-git em
> `storage/<uuid>/reviews/U2-2026-08-29/lc6-01/` (script + saída).

**A afirmação central, agora provada por mutação.** Trocando `persisted_e3` por um
universo grosseiramente diferente no núcleo puro, os **oito** campos de rubrica e
sumário (`conservation`, `e3_groups`, `e4_buckets`, `investment_collisions`,
`natural_key`, `cross_group`, `e2_seeded`, `e2_tx`) saem **idênticos**; só `drift`
reage. O artefato entregue pode ser qualquer coisa.

**Por que sobreviveu quatro rodadas — a fixture é a causa.**
`tests/dev/test_ledger_certify_core.py:201` passa `persisted_e3=fresh_e3`, o **mesmo
objeto**. Nenhum teste sobre `build_report` consegue discriminar os dois universos.

**A incógnita registrada está fechada.** Os 31 "só no persistido" são **31/31 sobra de
7 outros runs** (`created_at` 2026-05-29 → 2026-07-31); o run pinado escreveu **zero**
deles, e `run − ws_latest = 0`. A glosa impressa em `ledger_certify_core.py:391` —
*"keying antigo não reproduzido"* — é **atribuição falsa de causa**: nada na
re-chaveação está implicado; o universo de comparação é que é maior que o run.

**O agravante é maior do que a linha dizia.** Dos **61 runs `completed` com E3, 60**
teriam todas as próprias keys comparadas contra artefato de outro run —
`require_pinned_run` só exige `--run` não-vazio. Só o pinado escapa, e apenas por ser o
mais novo. O docstring de `dev/ledger_certify_entregue.py` afirma *"Workspace-latest é
proibido"*: a proibição vale para a **seleção do run**, e o substrato entra pela porta
dos fundos.

**Achado novo desta sessão — o braço entregue está amputado.** `_rederive_entregue`
semeia **só E3**; investimentos vêm de artefatos E2 e `patrimonio` do baseline. Medido
in-process: sombra 7 baldes / `investimentos`=18 · entregue **6 baldes** (falta
`patrimonio`) / `investimentos`=**0**. Logo `investment_double_count` devolve 0 sobre
**zero posições** — falso-negativo do detector da [[ADR-271]], indistinguível na saída
de um 0 verdadeiro. **Promover `e4_e` à rubrica sem corrigir isso trocaria um defeito
por outro.** O E4 **persistido** do run carrega o sinal inteiro (7 baldes,
`investimentos`=18) — ler o publicado é mais fiel e mais barato que re-derivar.

**Dois bounds que impedem exagero na leitura desta linha:**

- **A KR-B da [[A40]] não está contaminada.** O numerador lê só os baldes
  transacionais (`_tx_rows`) e `transferencias_count`; não lê
  `investimentos`/`patrimonio`. A amputação não o alcança.
- **O substrato E2 não é defeito.** A [[ADR-241]] decidiu que E2 é workspace-scoped
  (é o read-path de produção); neste run **0 de 170** rows E2 foram criadas depois do
  fim do run. Run-escopar o E2 seria **regressão** — reintroduziria o universo
  subdimensionado da §Contexto daquela ADR. O escopo certo é assimétrico: E2 pela
  política do run, **E3/E4 run-scoped**.

**O que a [[ADR-241]] já decidiu contra este código.** A §Alternativas (a) rejeitou
"mais-recente-por-key" para E3 porque *"congelaria dedup parcial entre runs — bug
silencioso difícil de detectar"*. `_persisted_e3_by_key` **é** essa alternativa,
dentro do instrumento de review; os 31 fantasmas são esse bug, medido. O lado de
escopo do fix é portanto **conformidade**, não decisão nova.

**Também medido:** separar o predicado de *certificar* do de *pontuar KR-B* é
obrigatório — `evidence_from_retention` exige `removals_publicadas > 0`, e só **10 dos
61** runs têm essa evidência. Sem a separação, tornar o entregue o default recusaria 51.

**Classe, não instância.** A [[ADR-343]] §Emenda 2026-08-05 item 2 já registra o mesmo
defeito no instrumento irmão (*"O parecer não era run-scoped: `ORDER BY id DESC LIMIT
1` por workspace"*). Duas ocorrências, dois instrumentos, mesma causa. **Não
generaliza** para os outros leitores de `dev/`: `dump_artifact.py` e
`measure_if_base.py` filtram por `pipeline_run_id` — `certify_ledger_local` é o outlier.

**Disposição:** segue `procede-aberto`. Direção decidida em [[ADR-421]] (`Proposto`,
seis decisões + critério de aceite com prova por mutação). Execução é da [[A42.l14]],
criada pelo dono em #1821 no mesmo dia — as três perguntas abertas no
§Critério de aceite dela estão respondidas acima. **Ordem:** a l14 precede os itens 1–5
da [[A42.l3]], que reescreve o mesmo arquivo. Aresta com a [[A42.l6]] declarada na ADR.

> ### Retificação datada do `LC6-02` — 2026-08-29, no ataque da lane
>
> O snapshot acima **não se reescreve**; três afirmações dele foram medidas e caíram, e a
> [[A42.l15]] carrega a evidência. Quem citar o `LC6-02` cite também isto:
>
> - ❌ *"as duas pernas HARD disparam com esta churn"*. Executadas sobre os snapshots reais:
>   **U1→U2** dispara só `_reclassificacao_regression`; `_identidade_regression` **não**
>   (instituições **subiram** 18→24). **r8→U1** é o inverso. A contagem oscila **24 → 18 →
>   24** com o corpus parado ⇒ dispara em todo par consecutivo, **por perna diferente a cada
>   vez**, e `_identidade_regression` é unidirecional (cega em metade do ciclo).
> - ❌ *"canonicalizar `instituicao` … resolve os dois exemplos medidos"*. O teto de qualquer
>   canonicalização é **29,9%** (de 23,5%), e com o resolver que existe no repo o ganho é
>   **~0pp** — `BANCO C6`→`bancoc6` e `C6 BANK`→`c6bank` são codes diferentes. A rota também
>   é vetada em substância pela [[ADR-400]] §1. O driver dominante é **`descricao` (56%)**.
> - ⚠️ *"Alto e não Crítico porque nenhum estado persistido é corrompido"*. O inventário
>   estava incompleto: `investment_id` é **publicado** como `nao_classificado_itens[].locator`
>   no artefato E5 (`e5_analysis.schema.json:2137`, [[ADR-406]] D5) e congelado em
>   `tests/fixtures/dedup/policy_parity_snapshot.json`.
>
> Efeito no relatório, mesmo corpus: `Internacional` R$ 34.857,23 → **R$ 423,56**,
> `nao_classificado_pct` 3,93% → **6,51%**, com **totais publicados idênticos ao centavo** —
> redistribuição com Σ preservado, a classe cega aos invariantes de conservação.

## r7 — ws-1b9f2cf5-2026-08-30

> Rodada unificada **U3** ([[ADR-416]]) · [[LEDGER-CERTIFY-active]] §r7 · [[PIPELINE-REVIEWS-active]] §r11 · [[REPORT-REVIEWS-active]] §r7.
> Run `3a5b9c7d` `completed` 18/18 · 25,7 min · executor `f0ac69a2` · report `939ee69c` · preflight: 4 WARN.
> Cru + síntese com valores: storage/<uuid>/reviews/U3-2026-08-30/SINTESE.md (off-git).
> Escrituração: [[A40.l100]] · [[A40.l101]] · [[A42.l17]] alocadas nesta rodada.
> Cobertura: matriz 7×3 — **`REPORT × solidez-financeira` NULA** (100% dos blocos de doutrina em `sem-veredito` ⇒ a resposta legítima era `BLOQUEADA`) · `PIPELINE × qualidade-llm` fraca.
> Céticos: **3 CONFIRMADO / ~10 PARCIAL / 2 REFUTADO**.

**Manchete: a rodada mediu que os dois consertos seguram, e descobriu que o instrumento que
pontua a KR-B mudou entre os dois runs sem ninguém olhar.** A regra §10 nº 5 — escrita no
fecho do `U2` — manda derivar a lista de fechados do `git log` entre executores, e o
pathspec que ela fixa é `pipeline backend scripts config frontend/src`. O instrumento vive
em `dev/` e em `storage/`, e **nenhum dos dois está no pathspec**.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| LC7-01 — um parser de banco chama o SDK LLM **sem `temperature`**, sem seed, sem contrato tipado e **sem escrever na telemetria** que é fonte única, e a descrição livre que ele devolve alimenta a **chave natural** da transação | correção | Alto | P0 | PARCIAL (Crítico → Alto: blast radius vivo é zero) · NOVO | **procede-parcial-fechado** (#1846, 2026-08-30) | mesmo documento, 4 runs: **2/1/4** de 8 chaves mudaram. No corpus inteiro (136 unidades, 7.991 tx) as 4 que mudaram no último intervalo estão **todas nesta unidade** · **dona [[A42.l17]]** (`shipped`). **Fechado:** `temperature` declarada no call-site cru + gate que torna visível a classe do bypass (o anterior era cego em 3 eixos). **Aberto:** telemetria/budget/cache seguem fora — dependem da **Fase 2 da [[ADR-349]]** (bloco `document` no `LLMService`), e o texto livre do LLM continua alimentando a chave natural. **Eixo novo medido:** rotear pelo choke-point **não** compra determinismo (`use_cache` é `False` por default e `extract_with_llm` não o passa) |
| LC7-02 — a população consolidada publicada mede **churn do extrator**, não descoberta: contas reais **55 → 60 → 58** contra contagem publicada **61 → 60 → 63**; uma linha do IRPF produziu **4 descrições** em 3 runs ⇒ 4 identidades | consistência | Alto | P1 | PARCIAL (MEDIÇÃO-DE-CONHECIDO de `LC6-02`; o mecanismo **não** é novo, a decomposição é) | procede-aberto · dona [[A42.l15]] | **refutação embutida: não há dupla contagem monetária** — a soma fecha ao centavo nos 3 runs, porque o consumidor lê a fatia do ano corrente |
| LC6-01 · LC6-02 · LC6-03 · LC6-05 · LC6-07 (§r6) | — | — | — | **reproduzidos sem alteração** | procede-aberto | KR-B **7** `carrier-shaped` · E2→E3 `coberto-sem-verificação` · `natural_key` 7,0% · lanes `in_progress` |

**Positivos verificados.** E3→E4 `conservado` · X2 determinístico (2.289 células, 0
divergentes, pin de overrides estável) · X3b fecha · zero-write provado.

**⚠️ Ressalva de instrumento, e é minha.** O modo que pontua a KR-B foi **reescrito** entre
os dois runs (para fechar um falso-verde de zero-write). Publiquei "KR-B idêntico" atravessando
essa mudança sem declará-la. E ao "propagar o instrumento corrigido" eu **sobrescrevi o
`xchecks.py` do diretório do `U2`**, que é o baseline congelado do `--compare` — os
números do §r6 já não são reproduzíveis com o instrumento que os produziu. Mesma patologia
que o `LC6-01` declara.
