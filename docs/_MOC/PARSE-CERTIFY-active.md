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

---

## r2 — ws-1b9f2cf5-2026-08-04

> Skill parse-certify ([[ADR-302]]) · harness E0→E2 síncrono (sem Celery/LLM).
> Grupo `financial_statements`: **128 docs** (os outros 4 grupos ficaram fora do
> escopo v1 — cobertos por outros stages ou vazios). Vereditos:
> **30 completo / 80 coberto-sem-verificação / 16 escalado-honesto / 0 perda /
> 2 não-coberto**. Cross-check harness↔DB por `content_hash`: **128 ingested /
> 2 deduped / 0 not_ingested**, 0 violação do invariante de artefato vivo.
> **`--compare` vs baseline 2026-07-24: 7 regressões** — o ratchet de completude
> (PC06/r1) pegou o que foi introduzido depois dela. Julgamento: `data-engineer` +
> `financial-planner` em paralelo (ambos objetaram a premissas do orquestrador;
> objeções aceitas) + verificação adversarial (**1 candidato a perda refutado,
> 1 achado de teste vácuo confirmado por mutação**). Veredito: **APROVADO COM
> RESSALVA** — zero perda silenciosa, mas o corpus regrediu em *capacidade de
> provar* que o dado está certo. Cru + baseline + anexo de instância em
> `storage/<uuid>/parse_certify/2026-08-04/` (off-git).

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| PC09 — parser line-oriented sem âncora de fidelidade: 3 parsers CSV (29% do corpus) nunca setam `raw_rows_detected`, e com o gate de PC08 suprimido o fail-safe da emenda A38.l14 não tem por onde disparar → zero sinal de completude. Três `continue` silenciosos vivos (`scripts/e2/banks/c6bank.py:257`, `:271`, `:784`); risco declarado em prosa e nunca gateado em `scripts/e2/banks/santander.py:625` | parse | Crítico | P1 | procede | procede-aberto | lane a abrir · emenda [[ADR-342]] |
| PC08 — gate de conservação suprimido por **conclusão do parser**: `_c6_csv_apply_conservation_flags` (`scripts/e2/banks/c6bank.py:108-126`) retira `conservacao_verificavel` quando a cadeia de âncoras diárias quebra, sem checar o fechamento **independente** dos endpoints → gap≠0 chega ao E3 sem sinal. Regressão de **forma** vs [[ADR-342]] §Emenda A38.l14, que rejeitou nominalmente a flag-conclusão (`conta_dormant`), sem emendar a ADR | validação/checksum | Alto | P1 | procede | procede-aberto | lane a abrir · emenda [[ADR-342]] |
| PC10 — o golden que justifica o mecanismo não o exercita: a fixture stale de `tests/test_e2_c6_csv_verificabilidade.py` tem gap==0, logo a asserção comportamental de não-escalação sobrevive à remoção integral da supressão (provado por mutação em runtime); nenhuma fixture cobre `gap≠0 ∧ breaks≥2`, que é a combinação do corpus real | saúde-harness | Alto | P1 | procede | procede-aberto | lane a abrir (junto de PC08/PC09) |
| PC11 — escalação honesta não é segura no tier sem LLM: período cuja extração determinística dá 0 tx escala corretamente, mas em modo 0-LLM (default do Free) entra na janela como "mês documentado com zero movimento" — viola [[ADR-306]] de fato sem violar de forma. Pior dos estados: ausente sem aviso, fantasiado de observação | cobertura | Alto | P1 | procede | procede-aberto | lane a abrir · interação [[ADR-306]] |
| PC12 — vocabulário de checksum de fatura conflacia dívida com teto: `faltando` cobre tanto "parser não fez opt-in" (acionável) quanto "a fonte não declara total independente" (teto estrutural, 31 de 41 docs) → a condição de flip HARD é inalcançável por construção, travando o rollout e não o gate. Precedente do split na própria [[ADR-342]] §Emenda A39.l6 (`checksum_ok` vs `checksum_skipped_no_total`) | validação/checksum | Médio | P2 | procede | procede-aberto | lane a abrir (com PC09) |
| PC13 — harness cego a traço de checksum já emitido: `checksum_ok`/`checksum_skipped_no_total` são declarados em `config/schemas/e2_extract.schema.json` e escritos por `apply_cdb_checksum`, mas `_quality_metrics` (`dev/certify_parse_local.py`) não os lê → 11 docs de investimento presos em `coberto-sem-verificação` por observabilidade, e `checksum_ok: True → ausente` é des-certificação invisível ao ratchet | saúde-harness | Médio | P2 | procede | procede-aberto | lane a abrir |
| PC14 — export sem linha datada não escala por **acidente de limiar** (`MIN_CSV_BYTES`, `scripts/e2/common.py:105`), não por decisão → artefato vivo vazio sem sinal. Armadilha do fix óbvio: tratar 0 candidatas como dormência converte acidente em silêncio **justificado**; dormência exige o par (0 candidatas **e** saldo presente, [[ADR-342]] §A38.l14) | validação/checksum | Médio | P2 | procede | procede-aberto | lane a abrir (com PC09) |
| PC15 — `parse_c6bank` (PDF) deixa candidatas datadas não convertidas com **delta constante** em 3 docs de tamanhos muito diferentes (assinatura sistemática, não ruído); `count_candidate_rows` já exclui linhas de saldo. Escala honesto (conservação quebra junto), logo não é silêncio — custa LLM recorrente e expõe os docs ao modo 0-LLM de PC11 | parse | Médio | P2 | procede | procede-aberto | lane a abrir (baixa) |
| PC16 — classificador que alimenta gate compara **float** com tolerância monetária de centavos (`scripts/e2/banks/c6bank.py:81`) — contraria [[ADR-090]] e a tolerância-zero adotada em [[ADR-342]] | validação/checksum | Baixo | P3 | procede | procede-aberto | polish (com PC08) |
| PC17 — hipótese de perda silenciosa de linha em parser CSV | parse | — | — | **refutado** | refutado | Contagem de linhas datadas fora do parser casa `n_tx` em 6/6 docs → parser fiel ao arquivo; a premissa de "âncora stale, não perda" fica corroborada. Refutada também a sub-hipótese de que gap **redondo** indica lançamento ausente: âncora terminal defasada por transação de valor redondo produz assinatura idêntica |
| PC18 — 2 docs sem classificação no harness (`status=sem_classificacao_regex`) | classificação | Baixo | P3 | **não-acionável** | não-acionável | Divergência regex-only↔LLM prevista na rubrica: ambos classificados em produção com `needs_review=0`. Efeito real é ponto cego do harness (2 docs sem veredito nesta cert), não defeito de produto |

**Notas de re-triagem (r1 → r2):** **PC07 re-priorizado ↑ (P2→P1)**, segue
`procede-aberto` — [[ADR-350]] continua `Proposto` e só o PR1 measure-only (#1087)
existe; nenhum commit novo no cross-checker. A subida é por convergência
independente: o `financial-planner` chegou à mesma testemunha cross-source como
**resposta para os 31 docs de PC12**, e apontou que o sub-produto é achado de
**domínio**, não de QA (pagamento menor que a soma da fatura indica
rotativo/parcelamento — hoje invisível). PC01–PC06 seguem `procede-fechado`; PC04
e PC06 foram o que **permitiu este run** detectar as 7 regressões — a instrumentação
do harness pagou a si mesma em um run.

**Forma recomendada para o pacote de fix:** **emenda datada à [[ADR-342]]**, não ADR
nova — mesma decisão com o eixo refinado (separar "fidelidade do parser" de
"completude da fonte", que `breaks≥2` hoje conflaciona); precedente exato é a emenda
2026-07-27, também nascida desta skill. Campos novos aditivos em
`e2_extract.schema.json` + `ReviewReasonCode`; sem migration, sem bump.
**Gatilho a registrar na [[ADR-345]]** (`Roadmap`, adoção deferida): a condição de
retomada da nota é *"quando um achado de revisão demonstrar número de origem
degradada chegando ao usuário sem sinal"* — **PC08 é esse achado**. Registrar o
gatilho na nota, sem implementar (promover a `Proposto` exige design, per [[ADR-358]]).
