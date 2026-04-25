# Track F9.0 — Auditoria de referências aos identificadores legados

> **Lane ID:** F9.0
> **Branch prefix:** `agent/f9-stage-rename/0-audit/*`
> **Depende de:** A6c ✅ (bridge removida) · A6d ✅ (Caminho B puro) · ADR-129 ✅ (E6 fora do mapa)
> **Paralelo com:** nenhum (gate inicial da Fase 9; depois desbloqueia 9.1)
> **Conflita com:** qualquer commit ativo em `pipeline/stage_spec.py`, `pipeline/stages/`, `scripts/e*.py`, `backend/alembic/versions/`
> **Onda:** F9 (sub-fatia 1/7)
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) · [`pipeline.stage_spec.STAGE_RENAME_MAP`](../../pipeline/stage_spec.py#L129)

> **Objetivo (1 frase):** produzir um inventário exaustivo das ocorrências dos
> identificadores legados (`E2`, `E3`, `E5`, `E5.N`, `E7-apply`…) em todo o
> repo, validar que `STAGE_RENAME_MAP` cobre 100% dos nomes em uso, e
> congelar o baseline antes do `git mv` em massa de 9.1+.

---

## Por que este slice agora

A Fase 9 é um rename em bloco que toca **filenames + strings literais + DB rows
+ logs + docs**. Sem auditoria prévia, o sweep das fatias 9.1-9.4 vai descobrir
"surpresas" tarde (string em test fixture, regex em CI, label de gráfico). O
output de 9.0 é a planilha de trabalho das fatias seguintes.

Bonus: artefatos parcialmente já existem — `STAGE_RENAME_MAP` pronto,
[`tests/unit/pipeline/test_no_legacy_stage_names.py`](../../tests/unit/pipeline/test_no_legacy_stage_names.py)
em soft-fail, [migration `q5r6s7t8u9v0_rename_stage_identifiers`](../../backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py)
scaffolded. 9.0 valida que esses stubs ainda batem com a realidade do código
em 2026-04-24 (pós-A6c, pós-ADR-129 — `E6`/`E6-final` saíram do mapa).

---

## Regras inegociáveis

- **Não renomeie nada** nesta fatia. 9.0 é só leitura + asserção. Qualquer
  edit fora de `_scratch/` ou `tests/unit/pipeline/test_stage_spec.py` é
  out-of-scope.
- **Mapa exaustivo é binário** — se um nome aparece em `pipeline_artifacts.stage`
  (ou em string literal de produção) e não está em `STAGE_RENAME_MAP`, a
  fatia falha e bloqueia 9.1.
- **Soft-fail no test_no_legacy é OK por enquanto.** Hard-fail é F9.5.

---

## Entregas

### 1. Script de auditoria — `dev/audit_stage_references.py`

**Ferramenta reutilizável** — mora em `dev/` junto com `audit_code_style.py`
(não `_scratch/`, que é gitignored). F9.1-F9.6 podem re-rodar para confirmar
redução de offenders ao longo das fatias.

Dump JSON com todas as ocorrências, classificadas por categoria. Sugestão de
estrutura:

```python
# Categorias:
#   "code_string"     — string literal "E2"/"E3"/etc em código de produção
#   "code_identifier" — token (var/func/class) que contém E2/E3/etc
#   "filename"        — arquivos com prefixo e<N>_*.py
#   "test_string"     — string literal em tests/ ou backend/tests/
#   "doc_string"      — ocorrência em docs/**, *.md, ADRs
#   "config"          — config/**.json, *.yaml
#   "db_value"        — DISTINCT stage em pipeline_artifacts/pipeline_stage_logs
#   "alembic"         — backend/alembic/versions/**
```

Interface sugerida: `python dev/audit_stage_references.py --format {json,md} --output-dir <path>`.
Default `--output-dir _scratch/` (output **é** ephemeral — o artefato durável
é o resumo em `docs/audits/`, não o dump bruto).

Output esperado em `<output-dir>/stage_audit_<YYYYMMDD>.{json,md}`:
- Total de ocorrências por categoria.
- Top 20 arquivos com mais ocorrências (alvos prioritários de 9.2).
- Lista de filenames `e*` em `scripts/` e `pipeline/stages/` (alvos 9.1/9.4).
- Tabela "stage encontrado" → "está em STAGE_RENAME_MAP?" — qualquer "Não" é
  blocker.

### 2. Teste de exhaustividade do mapa — em `tests/unit/pipeline/test_stage_spec.py`

```python
def test_rename_map_covers_all_legacy_names():
    """Garante STAGE_RENAME_MAP exaustivo para todos os stages em uso."""
    legacy_in_registry = set(STAGE_REGISTRY.keys()) | VIRTUAL_ARTIFACT_STAGES
    mapped = set(STAGE_RENAME_MAP.keys())
    missing = legacy_in_registry - mapped
    assert not missing, f"STAGE_RENAME_MAP missing: {missing}"


def test_rename_map_targets_are_unique():
    """Garante que dois legados não mapeiam para o mesmo nome descritivo."""
    targets = list(STAGE_RENAME_MAP.values())
    assert len(targets) == len(set(targets)), "duplicate targets"
```

(Adicionar a `tests/unit/pipeline/test_stage_spec.py` se já existe — não
criar arquivo novo se houver lugar natural.)

### 3. DB sanity check (apenas dev local)

```bash
python -c "
from backend.app.db import session_scope
with session_scope() as s:
    rows = s.execute('SELECT DISTINCT stage FROM pipeline_artifacts').all()
    print([r[0] for r in rows])
"
```

Comparar com `STAGE_RENAME_MAP.keys()`. Qualquer stage não mapeado é
investigação obrigatória **antes de prosseguir** — provavelmente débito de
ADR-129 (E6/E6-final residual) ou stage ad-hoc esquecido.

### 4. Relatório executivo — `docs/audits/f9_audit_<YYYYMMDD>.md`

**Artefato durável** (commitado, não em `_scratch/`). Resumo de 1 página:
contagens por categoria, lista de blockers (se houver), estimativa de
esforço por sub-fatia (9.1-9.6) com base nos números reais. F9.1-F9.6
consultam este arquivo; gitignored não serve.

---

## Sequência de execução

```bash
# Setup
git fetch origin
git worktree list
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/f9-stage-rename/ | head -10
git checkout -b agent/f9-stage-rename/0-audit/$(date +%Y%m%d-%H%M)

# 1. Escrever dev/audit_stage_references.py (ferramenta commitada)
# 2. Rodar `python dev/audit_stage_references.py --output-dir _scratch/`
#    e iterar até output cobrir todas categorias acima
# 3. Adicionar testes em tests/unit/pipeline/test_stage_spec.py
pytest tests/unit/pipeline/test_stage_spec.py -q

# 4. DB sanity check (se mathoms.db existir local)
# 5. Escrever docs/audits/f9_audit_<YYYYMMDD>.md (resumo durável)

# Gates
pre-commit run --all-files
pytest tests -q                          # zero regressão
pytest backend/tests -q                  # zero regressão

# Push
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q
git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] `dev/audit_stage_references.py` commitado em `main` e roda em <10s (`python dev/audit_stage_references.py --format md --output-dir _scratch/` produz output).
- [ ] `docs/audits/f9_audit_<YYYYMMDD>.md` commitado com resumo + contagens + blockers.
- [ ] `test_rename_map_covers_all_legacy_names` + `test_rename_map_targets_are_unique` passando em verde.
- [ ] Tabela "stage encontrado vs mapeado" no resumo tem 100% de cobertura — zero "Não".
- [ ] DB local: `SELECT DISTINCT stage FROM pipeline_artifacts` retorna apenas keys de `STAGE_RENAME_MAP` (ou DB vazio) — registrado no resumo.
- [ ] BACKLOG + CHANGELOG atualizados (§Atualizar documentação).

**Nota:** dumps brutos em `_scratch/stage_audit_<date>.{json,md}` são
gitignored (ephemeral) e **não** são gate — qualquer um re-gera rodando
o script. O gate é o resumo em `docs/audits/`.

---

## Rollback criteria — ABORTE se

- DB tem stage não mapeado **e** não consegue ser justificado (ex.: artifact stage
  virtual novo não declarado em `VIRTUAL_ARTIFACT_STAGES`). Investigue antes de mergear.
- Teste de exhaustividade falha — não bypasse com skip; corrija `STAGE_RENAME_MAP`
  primeiro (mesmo isso é uma decisão de ADR — abra discussão antes).

---

## Atualizar documentação (obrigatório, último passo)

Antes de push final, no **mesmo turno**:

1. **`docs/BACKLOG.md`** — na linha da lane "F9 stage rename em bloco" (§Lanes
   abertas agora), atualize status: `🚧 F9.0 ✅ — auditoria fechada YYYY-MM-DD,
   N ocorrências mapeadas, zero blockers; F9.1 destravada`. Inclua link para
   `docs/audits/f9_audit_<date>.md`.
2. **`docs/CHANGELOG.md`** — adicione entrada datada:
   ```markdown
   ### 2026-MM-DD — F9.0 audit ADR-093

   - `dev/audit_stage_references.py` (ferramenta reutilizável) +
     `docs/audits/f9_audit_<date>.md` (resumo):
     N ocorrências de identificadores legados mapeadas em K categorias.
   - `tests/unit/pipeline/test_stage_spec.py`: testes de exhaustividade e
     unicidade do `STAGE_RENAME_MAP`.
   - `STAGE_RENAME_MAP` validado contra DB + código + docs — zero blockers
     para F9.1.
   ```
3. **`docs/DECISIONS.md`** ADR-093 — adicionar nota datada na seção "Status"
   se relevante: "F9.0 fechada YYYY-MM-DD".
4. Commit docs separado do código:
   `docs(f9): audit fechado, N ocorrências, F9.1 destravada (ADR-093)`.

---

## O que esta fatia NÃO entrega

- **Nenhum rename de arquivo.** `git mv` é F9.1+.
- **Nenhuma substituição de string.** F9.2.
- **Nenhuma mudança em DB.** F9.3.
- **Switch hard-fail no `test_no_legacy_stage_names.py`.** F9.5.

---

## Referências

- ADR-093 (DECISIONS.md:2228) — plano completo das 7 sub-fatias.
- `pipeline/stage_spec.py:129` — `STAGE_RENAME_MAP` canônico.
- `tests/unit/pipeline/test_no_legacy_stage_names.py` — guardrail soft-fail.
- `backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py` — migration scaffolded.
- Próximo prompt: [track_f9_1_pipeline_stages_rename.md](track_f9_1_pipeline_stages_rename.md).
