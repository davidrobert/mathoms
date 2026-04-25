# Track F9.5 — Guardrail hard-fail contra identificadores legados

> **Lane ID:** F9.5
> **Branch prefix:** `agent/f9-stage-rename/5-guardrail/*`
> **Depende de:** F9.4 ✅ (scripts renomeados, wrappers compat ativos)
> **Paralelo com:** nenhum
> **Conflita com:** commits em `tests/unit/pipeline/test_no_legacy_stage_names.py`, `pyproject.toml`, `.pre-commit-config.yaml`
> **Onda:** F9 (sub-fatia 6/7)
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) · [test_no_legacy_stage_names.py soft-fail atual](../../tests/unit/pipeline/test_no_legacy_stage_names.py)

> **Objetivo:** transformar [`tests/unit/pipeline/test_no_legacy_stage_names.py`](../../tests/unit/pipeline/test_no_legacy_stage_names.py)
> de soft-fail (warn) para **hard-fail** (default em CI). Strings legadas
> (`"E2"`, `"E3"`, `"E5.N"`…) só sobrevivem em ilhas explicitamente
> permitidas (compat dicts, runbook docs históricos, ADR-093).

---

## Por que este slice agora

F9.0-F9.4 fecharam código + DB + scripts. Sem hard-fail, novo código continua
podendo introduzir `"E3"` literal sem quebrar CI — drift volta. Esta fatia é
o **lock**.

A infra já existe em soft-fail mode com env var `MATHOMS_ENFORCE_STAGE_RENAME=1`
disparando hard-fail. Aqui flipamos o default.

---

## Regras inegociáveis

1. **Default = hard-fail.** Sem env var, teste falha em qualquer string legada
   fora da ALLOWLIST.
2. **ALLOWLIST mínima e justificada.** Lista vai em comentário inline no teste
   ou em arquivo separado `tests/unit/pipeline/_legacy_allowlist.txt`. Cada
   entrada com motivo de 1 linha (compat dict, runbook histórico, ADR
   referência).
3. **Não adicione hack para passar.** Se um arquivo legítimo tem `"E3"`
   sobrevivente, ou (a) é compat real e entra na ALLOWLIST com nota, ou
   (b) é dívida que deveria ter sido limpa em F9.2 — abra issue/commit
   separado, não enfie ALLOWLIST como atalho.
4. **Pre-commit hook.** Adicione check leve em `.pre-commit-config.yaml`
   (grep simples) para feedback local antes do CI.

---

## Entregas

### 1. Atualizar [`test_no_legacy_stage_names.py`](../../tests/unit/pipeline/test_no_legacy_stage_names.py)

Mudanças:
- Inverter default: `ENFORCE = os.getenv("MATHOMS_ENFORCE_STAGE_RENAME", "1") != "0"` (em vez de `== "1"`).
- Atualizar docstring: hard-fail é o novo default; soft-fail só com env var explícita (uso temporário em rebase com main pendente).
- Garantir cobertura de **todas** as keys de `STAGE_RENAME_MAP` como tokens proibidos.
- Permitir ALLOWLIST por path (não por linha — granular demais é frágil).

### 2. Pre-commit hook

Em `.pre-commit-config.yaml`:

```yaml
- id: no-legacy-stage-names
  name: no legacy stage names ("E3", "E5.N"...) outside ALLOWLIST
  entry: python dev/check_no_legacy_stage_names.py
  language: system
  files: ^(pipeline|backend/app|scripts|tests)/.*\.py$
  exclude: ^(tests/unit/pipeline/_legacy_allowlist|.*test_no_legacy_stage_names).*
```

Implementar `dev/check_no_legacy_stage_names.py` (hook leve — pega offsetters comuns; o teste pytest é o gate canônico).

### 3. Atualizar ALLOWLIST justificada

Tipicamente sobrevivem:
- `pipeline/stage_spec.py` — `STAGE_RENAME_MAP`, `LEGACY_TO_DESCRIPTIVE`, `resolve_stage_name`. Compat real.
- `backend/alembic/versions/q5r6s7t8u9v0_*.py` — migration de rename.
- `tests/unit/pipeline/test_stage_spec.py` — teste do mapa.
- `tests/unit/pipeline/test_no_legacy_stage_names.py` — auto-referência.
- `scripts/e_reset.py` — alias CLI emite warning para `--from E3`.

Wrappers compat em `scripts/e*.py` (F9.4) **não** entram aqui: o conteúdo
deles é só `warnings.warn(...)` + `from … import *`; não contém `"E3"`
literal.

### 4. Migrar audit baseline

Se `dev/audit_code_style.py` ou `dev/code_style_baseline.json` tem categoria
`stage_legacy_strings`, regenerar pós-fix para refletir contagem nova
(idealmente 0 fora da ALLOWLIST).

---

## Sequência de execução

```bash
git fetch origin && git status
git checkout -b agent/f9-stage-rename/5-guardrail/$(date +%Y%m%d-%H%M)

# 1. Inverter default em test_no_legacy_stage_names.py
pytest tests/unit/pipeline/test_no_legacy_stage_names.py -q
# Se falhar: investigar offenders. Cada um:
#   - é compat real? → ALLOWLIST com nota
#   - é dívida F9.2? → fix em commit separado, não ALLOWLIST

# 2. Implementar dev/check_no_legacy_stage_names.py + adicionar ao pre-commit

# 3. Regenerar baseline de audit (se aplicável)
python dev/audit_code_style.py --format json --output-dir _scratch/

# Gate
pre-commit run --all-files
pytest tests -q                          # zero regressão; novo teste hard-fail passa
pytest backend/tests -q

# Drift
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `MATHOMS_ENFORCE_STAGE_RENAME` env var **não** precisa ser setada — default hard-fail.
- [ ] `MATHOMS_ENFORCE_STAGE_RENAME=0` força soft-fail (escape hatch para rebase em situações temporárias).
- [ ] ALLOWLIST contém ≤6 entradas, cada com justificativa de 1 linha.
- [ ] Pre-commit hook `no-legacy-stage-names` ativo e bloqueia adição de `"E3"` literal em arquivo novo (test: criar arquivo dummy com `"E3"`, `git commit` → bloqueado).
- [ ] CI verde com novo default.
- [ ] BACKLOG + CHANGELOG atualizados.

---

## Rollback criteria — ABORTE se

- Hard-fail revela dezenas de offenders sobreviventes — F9.2 ficou incompleta.
  Volte e feche em commit separado antes de mergear F9.5.
- Pre-commit hook tem falsos positivos frequentes (ex.: `"E3"` em comentário
  benigno) — ajuste regex (apenas string entre aspas, fora de comentário).

---

## Atualizar documentação (obrigatório, último passo)

1. **`docs/BACKLOG.md`** — lane F9 status: `🚧 F9.0-.4 ✅ · F9.5 ✅ — guardrail hard-fail YYYY-MM-DD; F9.6 destravada (cleanup final)`.
2. **`docs/CHANGELOG.md`** — entrada datada:
   ```markdown
   ### 2026-MM-DD — F9.5 guardrail hard-fail (ADR-093)

   - `tests/unit/pipeline/test_no_legacy_stage_names.py`: default agora é
     hard-fail. `MATHOMS_ENFORCE_STAGE_RENAME=0` força soft-fail (escape).
   - Pre-commit hook `no-legacy-stage-names` (`dev/check_no_legacy_stage_names.py`)
     bloqueia inclusão de string `"E3"`/`"E5.N"`/etc fora da ALLOWLIST.
   - ALLOWLIST: 5-6 paths justificados (compat dict, migration, ADR).
   - Audit baseline regenerado: stage_legacy_strings = 0 fora da ALLOWLIST.
   ```
3. **`CLAUDE.md` §Regras críticas › "Stage identifiers"** — finalizar: "Pós-F9.5, código de produção usa exclusivamente nomes descritivos. Strings legadas só em ALLOWLIST justificada."
4. **`docs/DECISIONS.md`** ADR-093 — nota "F9.5 fechada YYYY-MM-DD".
5. Commit docs separado: `docs(f9): F9.5 hard-fail ativo, F9.6 destravada (ADR-093)`.

---

## O que esta fatia NÃO entrega

- **Remoção dos wrappers compat** — F9.6.
- **Cleanup de `_init_config()` global** — F9.6.
- **Remoção dos aliases legacy** (`STAGE_RENAME_MAP` etc) — F9.6.

---

## Referências

- F9.4 (prereq): [track_f9_4_scripts_rename.md](track_f9_4_scripts_rename.md)
- F9.6 (próximo): [track_f9_6_cleanup.md](track_f9_6_cleanup.md)
- ADR-093: `docs/DECISIONS.md:2228`
- Soft-fail atual: `tests/unit/pipeline/test_no_legacy_stage_names.py`
