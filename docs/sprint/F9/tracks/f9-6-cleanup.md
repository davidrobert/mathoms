---
id: TRACK-f9-6-cleanup
type: track
title: "Track F9.6 — Cleanup final: remover wrappers compat, aliases e globals legados"
sprint: F9
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/f9
  - status/consumed
---

# Track F9.6 — Cleanup final: remover wrappers compat, aliases e globals legados

> **Lane ID:** F9.6
> **Branch prefix:** `agent/f9-stage-rename/6-cleanup/*`
> **Depende de:** F9.5 ✅ (hard-fail ativo, ALLOWLIST mínima)
> **Paralelo com:** nenhum (último step da Fase 9)
> **Conflita com:** commits em `pipeline/stage_spec.py`, `scripts/e*.py` (wrappers), `pipeline/`
> **Onda:** F9 (sub-fatia 7/7) — **fechamento**
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) §9.6 + ADR-100 (housekeeping `_init_config`)

> **Objetivo:** remover toda a infra de compat introduzida em F9.2-F9.4
> (wrappers `scripts/e*.py`, alias `STAGE_RENAME_MAP` reverso,
> `resolve_stage_name`, alias CLI `--from E3`) + housekeeping órfão da
> Fase 9 (helpers `_init_config()` global se ainda existirem em
> `pipeline/stages/` legado).

---

## Por que este slice agora

Após 1 release com hard-fail (F9.5) ativo e descritivos consolidados, qualquer
consumidor externo que ainda usava nome legado já reagiu (warning forçou).
Compat agora é dívida pura — pesa em código, em entendimento, em diff de
PR futuro. F9.6 limpa.

**Cuidado especial:** este é o slice mais "destrutivo" — remove código que
era compat. Audite consumidores externos antes (Grafana, scripts ad-hoc,
notebooks no `_archive/`).

---

## Regras inegociáveis

1. **Confirme janela mínima de 1 release** entre F9.5 merge e F9.6 start.
   Em dev (sem prod ainda), "1 release" = 7-14 dias de estabilidade observada.
2. **Audit consumidores antes de deletar.** `grep -rn "STAGE_RENAME_MAP\|resolve_stage_name\|from scripts.e3_reconcile\|--from E3"`
   no repo inteiro. Se houver call-site que **não** é compat real, esse call-site precisa migrar **antes** de F9.6.
3. **Não delete `STAGE_RENAME_MAP` se algo de runtime ainda lê.** A intenção
   é deletar; mas se F9.5 ALLOWLIST tem entradas de runtime real (não
   docs/migration), volte a F9.2 e feche.
4. **`_init_config()` global** — A6d.1 fechou em 2026-04-24 (commit `e694f42`)
   com AST guard `tests/unit/pipeline/test_no_init_config_at_toplevel.py`.
   Se F9.0 audit revelar regressão (alguém top-leveou de novo), F9.6 limpa.
   Em condição normal, este passo é no-op verificado.

---

## Entregas

### 1. Remover wrappers compat de `scripts/e*.py`

```bash
git rm scripts/e0_audit.py scripts/e0_route.py scripts/e0_unlock.py \
       scripts/e15_consolidate.py scripts/e2_extract.py \
       scripts/e3_reconcile.py scripts/e4_categorize.py \
       scripts/e5_analyze.py scripts/e5n_narrativas.py \
       scripts/e7_review.py
```

(Exato set vem de F9.4 — confirme via `ls scripts/e[0-9]*.py` antes.)

### 2. Remover alias bidirecional do `pipeline/stage_spec.py`

- `LEGACY_TO_DESCRIPTIVE` alias → deletar.
- `DESCRIPTIVE_TO_LEGACY` reverso → deletar.
- `resolve_stage_name(name)` → deletar (todos os call-sites já usam
  descritivo direto pós-F9.2 + warnings extintos pós-F9.4).
- `STAGE_RENAME_MAP` → **manter como referência histórica** (read-only,
  exportado para a migration F9.3 que continua viva no histórico Alembic).
  Comentário: `# Manter como referência histórica para a migration de rename (F9.3) e ADR-093.`

### 3. Remover alias CLI em `scripts/e_reset.py`

- `--from E3` deixa de ser aceito; help text só lista descritivos.
- Se alguém invocar com legacy, `argparse` rejeita naturalmente — mensagem
  de erro inclui dica: "stage não reconhecido; use descritivo (ex.: `reconcile_transactions`)".

### 4. Verificar `_init_config()` global (esperado: no-op)

A6d.1 fechou em 2026-04-24 com AST guard
[`tests/unit/pipeline/test_no_init_config_at_toplevel.py`](../../tests/unit/pipeline/test_no_init_config_at_toplevel.py)
parametrizado por todos os scripts/stages. Verifique:

```bash
pytest tests/unit/pipeline/test_no_init_config_at_toplevel.py -q
```

Se verde: passo é no-op verificado, siga adiante.
Se vermelho: alguém regrediu — reabra como issue separada e bloqueie F9.6
até o fix.

### 5. Remover ALLOWLIST entries que viraram redundantes

Em F9.5 a ALLOWLIST tinha 5-6 entradas. Após F9.6:
- `pipeline/stage_spec.py` — fica (STAGE_RENAME_MAP histórico).
- `backend/alembic/versions/q5r6s7t8u9v0_*` — fica.
- `tests/unit/pipeline/test_stage_spec.py` — fica.
- `tests/unit/pipeline/test_no_legacy_stage_names.py` — fica.
- `scripts/e_reset.py` — **remove** (alias CLI deletado).
- Wrappers `scripts/e*.py` — **remove** (arquivos não existem).

ALLOWLIST final ≤4 entradas, todas docs/test/migration.

---

## Sequência de commits

Um commit por entrega:

```bash
# 1. Remove scripts/ wrappers
git rm scripts/e[0-9]*.py
pytest tests -q && pytest backend/tests -q
git commit -m "refactor(scripts): remove wrappers legados e* (F9.6)"

# 2. Remove aliases stage_spec
# editar pipeline/stage_spec.py
git commit -m "refactor(pipeline): remove resolve_stage_name + alias bidirecional (F9.6)"

# 3. Remove alias CLI e_reset
git commit -m "refactor(scripts): remove --from E3 alias em e_reset (F9.6)"

# 4. Cleanup _init_config (se necessário)
git commit -m "refactor(pipeline): elimina _init_config global (A6d.1 + F9.6)"

# 5. Atualiza ALLOWLIST guardrail
git commit -m "test: ALLOWLIST guardrail enxuta pós-F9.6"
```

---

## Sequência de execução

```bash
git fetch origin && git status
git checkout -b agent/f9-stage-rename/6-cleanup/$(date +%Y%m%d-%H%M)

# 0. Audit consumidores
grep -rn "resolve_stage_name\|STAGE_RENAME_MAP\|from scripts.e[0-9]\|--from E[0-9]" \
  --include="*.py" --include="*.md" --include="*.yaml" --include="*.json" \
  | grep -v "_archive/\|docs/audits/\|backend/alembic/" | tee _scratch/f9_6_audit.txt

# Inspecionar — qualquer match em runtime fora das ilhas previstas é blocker

# 1-5: commits sequenciais (ver acima)

# Gate final
pre-commit run --all-files
pytest tests -q
pytest backend/tests -q
cd frontend && npm test -- --run; cd -

# Smoke run pipeline (E0 → E5.N) com workspace de teste
python -m scripts.audit_documents --workspace-id <test-id>  # nome descritivo direto
python scripts/e_reset.py --from E3 2>&1 | grep -i "não reconhecido"  # legado rejeitado

# Drift
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `ls scripts/e[0-9]*.py` retorna **vazio**.
- [ ] `grep -rn "resolve_stage_name" pipeline/ backend/app/ scripts/` retorna 0.
- [ ] `grep -rn "from scripts.e3_reconcile\|from scripts.e5_analyze" backend/ pipeline/ tests/` retorna 0 (todos consumidores usam descritivo).
- [ ] `python scripts/e_reset.py --from E3` falha com mensagem clara.
- [ ] `python -m scripts.reconcile_transactions --help` funciona.
- [ ] Smoke run E0→E5.N completo verde.
- [ ] Pytest 100% verde (tests + backend/tests).
- [ ] Frontend `npm test -- --run` verde.
- [ ] ALLOWLIST guardrail tem ≤4 entradas.
- [ ] BACKLOG marca lane F9 como ✅ fechada · CHANGELOG entrada final.

---

## Rollback criteria — ABORTE se

- Audit (passo 0) revela call-site runtime usando `resolve_stage_name` ou import legado **fora** das ilhas previstas. Migre call-site primeiro, depois retome F9.6.
- Smoke run E0→E5.N quebra com `KeyError` — algum lugar ainda assumia compat reverso. Reabra investigação.
- Frontend tests quebram em type — provavelmente algum codegen referenciando alias removido; regenere.

---

## Atualizar documentação (obrigatório, último passo)

1. **`docs/BACKLOG.md`** — lane F9 status: `✅ **fechada YYYY-MM-DD** — F9.0-F9.6 mergeadas; nomes descritivos em todo o repo; compat dict/scripts removidos; guardrail hard-fail ativo.`
2. **`docs/CHANGELOG.md`** — entrada final com escopo:
   ```markdown
   ### 2026-MM-DD — F9.6 cleanup final (ADR-093) — Fase 9 fechada

   - Removidos 10 wrappers `scripts/e*.py` (aliases compat de F9.4).
   - Removidos `resolve_stage_name`, `LEGACY_TO_DESCRIPTIVE`,
     `DESCRIPTIVE_TO_LEGACY` em `pipeline/stage_spec.py`.
     `STAGE_RENAME_MAP` mantido como referência histórica (alembic + ADR-093).
   - `scripts/e_reset.py --from E3` removido; help text só descritivos.
   - `_init_config()` global eliminado (A6d.1 ☐ → ✅).
   - ALLOWLIST guardrail enxuta para ≤4 entradas (docs/test/migration).
   - **Fase 9 fechada** — todos os identificadores em código de produção,
     DB, logs e CLI agora são descritivos (ADR-093 implementada em bloco).
   ```
3. **`docs/DECISIONS.md`** ADR-093 — atualizar Status: `Implementado (Fase 9.6 fechada YYYY-MM-DD)`.
4. **`CLAUDE.md` §Regras críticas › "Stage identifiers"** — reescrever:
   "Identificadores de stage são descritivos (`reconcile_transactions`,
   `analyze_finances`…). Nomes legados (`E3`, `E5`…) só sobrevivem em ADRs
   históricas e na migration `q5r6s7t8u9v0`. `STAGE_RENAME_MAP` é apenas
   referência."
5. **`docs/ARCHITECTURE.md` §7 e §10** — checar e atualizar se ainda menciona compat.
6. **`docs/RUNBOOK.md`** — comandos com nomes descritivos.
7. **`docs/agent_prompts/README.md`** — opcional: marcar lane F9 como concluída.
8. Commit docs final: `docs(f9): Fase 9 fechada — ADR-093 implementada`.

---

## O que esta fatia entrega (resumo)

✅ Repo 100% em nomes descritivos.
✅ Compat dict/scripts/CLI removidos.
✅ Hard-fail mantido (de F9.5).
✅ `STAGE_RENAME_MAP` preservado como referência histórica.
✅ Lane F9 fechada no BACKLOG.

---

## Referências

- F9.5 (prereq): [track_f9_5_guardrail_hardfail.md](track_f9_5_guardrail_hardfail.md)
- ADR-093: `docs/DECISIONS.md:2228`
- ADR-100: housekeeping `_init_config()` global (referência para A6d.1).
- Migration histórica: `backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py`.
