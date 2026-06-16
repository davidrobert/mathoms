# Orquestrador — Sprint A26 "Data Lineage: consolidação"

> Prompt self-contained para atacar a A26 em **nova sessão**. Sprint `current` desde
> 2026-06-16. Plano dono: [[PLAN-data-lineage]] (`docs/plan/DATA_LINEAGE/_README.md`, §Onda 5).
> Pré-revisado em co-design 2026-06-16: `product-manager` + `information-architect` +
> `data-engineer` + `prompt-engineer` + `sre-devops`.
>
> **Quando arquivar:** sprint A26 `done` (l1+l2 shipped no mínimo; l3/l4/l5 conforme
> gates de tráfego fecharem ou cortadas para A27).

## 0. Antes de qualquer coisa (protocolo de início)

```bash
git fetch origin && git status && git log --oneline origin/main..HEAD -10
git log --oneline -5 -- CLAUDE.md
git worktree list && git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' refs/remotes/origin/agent/ | head -15
```
Leia `CLAUDE.md` (regras timeless), `docs/sprint/A26/_README.md` (MOC desta sprint) e a
lane que for atacar. Crie branch `agent/a26-<slug>/<yyyyMMdd-HHmm>` ANTES de editar
(worktree `.claude/worktrees/` reverte edits uncommitted entre turnos).

## 1. Tese da sprint (por que ela existe)

A frente Data Lineage (A23 contrato aditivo → A24 de-leak + skeleton → A25 reverso +
produto + debug LLM, todas `done`) introduziu cada mudança de identidade **com uma rede
de segurança**: o shim v1 vivo ao lado do v2 (rollback = flag off) e o `evidencia_path`
do Parecer (E6) em modo `warn` (observa, não bloqueia). A **A26 desliga as redes** —
liga o `strict`, deleta os shims v1 — **somente** quando o uso real prova que é seguro.
Custo de antecipar é assimétrico (drops irreversíveis; bloqueio de parecer em massa) →
cada lane destrutiva tem **gate verificável**, não prazo.

## 2. Estado atual (2026-06-16)

- **Único lane atacável já:** [[A26.l1]] (`open`, sem gate). As demais (`blocked`) esperam
  **dados de tráfego** que não existem pré-launch.
- **Insumos para destravar l2–l5** (provê o owner):
  1. `ANTHROPIC_API_KEY` no ambiente backend — **ausente hoje**; sem ela nenhum parecer
     real é gerado e a telemetria do `evidencia_path` não cresce além das 3 gerações atuais.
  2. **~20 gerações de parecer** (dogfood: processar documentos → pipeline até E6, dados variados).
  3. **Exercício do override v2** por ≥1 sprint (aplicar/editar overrides via UI + reprocessar E4).
  4. **Confirmar PITR** do Postgres (Coolify) — `RUNBOOK §5` trata DR como pendente.
- **Já satisfeito:** G1 da l5 (`count(natural_key_hash IS NULL AND orphaned_at IS NULL)==0`,
  backfill da [[A25.l1]]). `dedup_natural_key_v2_enabled=True` (default, #648).
- **Ainda OFF:** `override_natural_key_v2_enabled=False` (a [[A26.l4]] flipa).

## 3. As 5 lanes — ordem de risco crescente

| Lane | Status | O quê | Gate de desbloqueio |
|---|---|---|---|
| [[A26.l1]] | `open` | fix de citação do `evidencia_path` (catálogo de paths) + eval golden | **nenhum** — atacar já |
| [[A26.l2]] | `blocked` | flip `evidencia_verification_mode: warn→strict` | l1 + **per-parecer <5% sobre ≥20 ger** (ou eval holdout) |
| [[A26.l3]] | `blocked` | M2-A: drop `compute_transaction_hash` (`_tx_identity.py`, dedup) — reversível | dedup v2 100% + counter zerado ≥1 sprint |
| [[A26.l4]] | `blocked` | flip `override_natural_key_v2_enabled`→True + `v2_match_count` + query agendada | habilitador (código + observação) |
| [[A26.l5]] | `blocked` | M2-B: drop coluna `transaction_hash` + `generate_transaction_hash` (`transaction_service.py`) — IRREVERSÍVEL | l4 + G1/G2/G3 + PITR + **owner go/no-go** |

**Precedência de corte:** Must = l1 + l2. Should = l3 + l4. Could/cortável p/ A27 = l5
(maior risco — nunca forçar sob gate apertado). **l1→l2** (flip precisa do prompt
corrigido); **l3 antes de l5** (reversível "canário" antes de irreversível); **l4
habilita o gate de l5**. l3/l4/l5 independentes de l1/l2.

## 4. POR ONDE COMEÇAR — [[A26.l1]] (não depende de nada)

Ler `docs/sprint/A26/lanes/A26-l1-evidencia-prompt-catalogo.md` (escopo completo). Resumo:

**Problema (telemetria A25.l7):** modo `warn`, taxa de violação de citação ~89% (n=3
dogfood). **72% das falhas são conformidade de citação** — `resolve_null` (38%, cita
campo nulo) + `whitelist_miss` (34%, path fora da `section_whitelist` ou sintaxe inválida).
Só 19% é `value_mismatch` (alucinação de valor). **Causa-raiz (prompt-engineer):** o LLM
**não vê** os paths citáveis — adivinha (`$.reserva.total` vs. real
`$.reserva_emergencia.total_liquida`). Expandir whitelist NÃO ajuda.

**Plano de ataque (4 passos, nesta ordem):**
1. **Diagnóstico ANTES de corrigir:** dump dos paths citados nas 3 gerações dogfood
   (`pipeline_stage_logs.output_summary.evidencia_verification` no DB, stage
   `review_finances_holistic`); classificar cada `whitelist_miss` em root-fora /
   sintaxe-inválida / leaf-errado. Registrar no PR. **Não pule** — decide whitelist vs catálogo.
2. **Catálogo de citação (maior alavanca, ~70%):** injetar no exec context do manifest
   (`config/prompts/parecer_planejador.yaml`) um bloco `evidencia_paths_disponiveis` com
   os leafs monetários **presentes e não-nulos** do E5 do cliente. Bump `version` do
   manifest (invalida cache Redis). Co-design `information-architect` se mexer na **forma**
   da DSL do manifest.
3. **Prompt:** reforçar a regra de citação ("cite EXCLUSIVAMENTE paths de
   `evidencia_paths_disponiveis`; campo ausente → não cite valor, use
   `campos_faltantes_pediria_se_iterasse[]`") + 2-3 few-shot. Bump `PROMPT_VERSION`
   (`pipeline/llm/prompts/parecer_planejador.py`) 1.5.0→1.6.0; atualizar `_PROMPT_BASELINE_CHARS`.
4. **Eval golden do LLM** (`tests/test_parecer_evidencia_llm_eval.py`, `@pytest.mark.llm_eval`,
   FORA do PR gate por custo/flakiness): 25 fixtures E5 PII-zero (happy, sem-previdência,
   sem-imóvel, leaf-nulo, período `999999`, casal vs solteiro), **15 tuning / 10 holdout**.
   LLM real + verificador real, **3 runs/fixture**, agrega **% pareceres com ≥1 violação**
   com banda. Anti-overfit: meça o gate no holdout nunca-visto no tuning.

**Critério de aceite l1:** conformidade ≥95%; eval holdout <5% (% pareceres c/ ≥1
violação); `tests/test_parecer_evidencia_path.py` verde (não-regressão do verificador);
`PROMPT_VERSION`+`version` bumpados; PII grep zero nas fixtures.

## 5. Decisões cravadas no co-design (NÃO reabrir)

- **Gate do flip é PER-PARECER** (% pareceres com ≥1 violação <5%), NÃO per-citação — em
  `strict` uma falha rejeita o parecer inteiro → `needs_review` (fallback graceful
  [[ADR-081]], sem retry/degradação). Ajustar a query SQL da [[A25.l7]] com
  `count(*) WHERE evidencia_failed > 0`.
- **M2-A (l3) e M2-B (l5) são lanes SEPARADAS**, M2-A primeiro (reversível, código).
  ⚠️ `compute_transaction_hash` (dedup) ∈ `_tx_identity.py`; `generate_transaction_hash`
  (override) ∈ `backend/app/services/transaction_service.py` — **funções/módulos
  distintos**. Não confundir.
- **Gate não pode ser vácuo:** "zero fallback por inatividade" não conta. Exige
  `v1_fallback==0` **E** `v2_match>=1` (uso real exercitado) — a [[A26.l4]] cria o
  `v2_match_count` e a query agendada (hoje o counter é só `logger.info`).
- **Migration destrutiva (l5):** `downgrade`→`raise RuntimeError` explicando
  irreversibilidade + caminho PITR; `upgrade` com hard-assert de G1 embutido; sem
  `IF EXISTS`. Backup `pg_dump` + sha256 + retenção 30d. **Go/no-go do owner**, não do agente.
- **Sem ADR nova:** [[ADR-279]] §E (evidencia) e [[ADR-287]] §Cutover (dedup) cobrem;
  **[[ADR-282]] flippa `Proposto→Decidido (A26)`** no merge da M2-B (l5).

## 6. KRs da janela (readiness/saúde, não "conclusão")

- **KR1** — conformidade de citação do `evidencia_path` **≥95%** (baseline ~28%). Via l1, hoje.
- **KR2** — `dualread.v1_fallback==0` por ≥1 sprint **com `v2_match>=1`** (uso real). Via l4.
- **KR3** — consolidações destrutivas (l2/l3/l5) executadas **com gate fechado verificado
  ANTES do PR** — não incentiva deletar cedo.
- **Gate de saúde pré-flip:** baseline de `needs_review` por geração instrumentado antes
  do flip (transparency backfire — flip só procede se taxa per-parecer genuinamente <5%).

## 7. Convenções do repo (CLAUDE.md — não violar)

- Concluído = PR mergeado em `main` (squash) com CI verde. Docs-only não espera CI, mas
  `pre-commit run --all-files` é obrigatório.
- Co-design > review: invoque o especialista ao **planejar** (gatilhos: prompt LLM/eval →
  `prompt-engineer`; migration/contrato → `data-engineer`; runbook/PITR → `sre-devops`;
  forma de doc → `information-architect`; priorização → `product-manager`).
- Dinheiro nunca é `float` ([[ADR-090]]). Pipeline não importa framework. Stateless
  rigoroso ([[ADR-111]]). Sem dados sensíveis (CPF/valores reais) em commits/fixtures/logs.
- Testes: `pytest tests -q`, `pytest backend/tests -q`. Função nova → teste; bug → teste
  de regressão antes do fix. Goldens de execução com schema validation.
- Branch `agent/<slug>/<ts>`; commit a cada marco; nunca termine turno com working tree sujo.

## 8. Gates de doc (rodar antes de commitar doc)

```bash
python3 dev/validate_frontmatter.py && python3 dev/check_doc_filename_id.py \
  && python3 dev/check_doc_links.py && python3 dev/check_adr_anchors.py \
  && python3 dev/build_doc_index.py --inline && python3 dev/build_doc_index.py --check
```

## 9. Referências

- Sprint MOC: `docs/sprint/A26/_README.md` · lanes em `docs/sprint/A26/lanes/`.
- Plano: `docs/plan/DATA_LINEAGE/_README.md` (§Onda 5, §KRs, §Blockers F2).
- Carry-overs de origem: [[A25.l7]] (decisão evidencia_path) · [[A25.l1]] §5 (gate M2
  override) · [[ADR-287]] §Cutover (M2 dedup).
- Verificador evidencia: `backend/app/services/parecer_evidencia.py` (4 camadas).
- Telemetria: `pipeline_stage_logs.output_summary.evidencia_verification` (PII-free).
