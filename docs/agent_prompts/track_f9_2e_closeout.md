# Track F9.2e — Closeout F9.2 (audit final + docs + destrava F9.3)

> **Lane ID:** F9.2e
> **Branch prefix:** `agent/f9-stage-rename/2e-closeout/*`
> **Depende de:** F9.2a, F9.2b, F9.2c, F9.2d ✅ (todas mergeadas em main)
> **Bloqueia:** F9.3 (Alembic) — F9.3 começa após esta lane fechar
> **Onda:** F9 (sub-fatia 3e/7)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093)

> **Objetivo:** validar que toda string legada residual é intencional (compat
> reverso ou docstring), regenerar auditoria, atualizar BACKLOG/CHANGELOG/ADR-093/
> CLAUDE.md marcando F9.2 ✅ e destravando F9.3.

---

## Pré-condições

Confirme que estão mergeadas em `origin/main`:
- F9.2 T1 (commits `332c51e`, `9758e59`, `ffca1b9`) ✅
- F9.2a (pipeline core) ✅
- F9.2b (scripts) ✅
- F9.2c (e_reset CLI deprecation) ✅
- F9.2d (backend residual + tests) ✅

```bash
git fetch origin
git log origin/main --oneline | grep -E "F9.2[abcd]" | head -20
```

## Passos

### 1. Re-rodar auditoria F9.0

```bash
source ../../../.venv/bin/activate
python dev/audit_stage_references.py --skip-db --output-dir _scratch/
```

Compare com baseline `docs/audits/f9_audit_20260424.md`. Esperado:
- `code_string` reduziu drasticamente (~1353 → ≤300)
- Categoria `doc_string` mantém número alto (intencional — `docs/**` histórico
  preserva legacy para contexto)
- `test_string` reduzido (~602 → ≤200)
- `alembic` permanece (~30 — F9.3 endereça)
- `filename` permanece (~16 — F9.4 endereça)

### 2. Validar que strings residuais em produção são intencionais

```bash
grep -rn '"E[0-9]' pipeline/ backend/app/ scripts/ \
  | grep -v -E "STAGE_RENAME_MAP|LEGACY_|legacy|deprecated|compat|_archive|test"
```

Cada hit precisa cair em uma das categorias:
- (a) `STAGE_RENAME_MAP` ou derivados (`LEGACY_TO_DESCRIPTIVE`, `DESCRIPTIVE_TO_LEGACY`)
- (b) `LEGACY_FROM_ALIASES` (`"E0"`, `"E2"`, `"E7"` sem sufixo)
- (c) Docstring/comentário com nota explícita explicando legacy
- (d) Alias compat em `e_reset.py` (intencional até F9.6)

Se sobrar algo fora dessas categorias, **adicione fix em commit separado**
ou abra issue/lane específica.

### 3. Atualizar `docs/audits/f9_audit_<YYYYMMDD>.md`

Crie novo arquivo `docs/audits/f9_audit_pos_f9_2_<YYYYMMDD>.md` com:
- Tabela de redução por categoria (baseline vs pós-F9.2)
- Lista de hits residuais classificados por (a)/(b)/(c)/(d)
- Confirmação "F9.2 fechada — F9.3 destravada"

### 4. Atualizar `docs/BACKLOG.md`

Linha "F9 stage rename em bloco" — marcar:
```
F9.0/.1/.2 ✅ — strings descritivas em produção 2026-MM-DD,
~N commits através de 6 sub-fatias (T1+2a+2b+2c+2d+2e); F9.3 destravada.
```

### 5. Atualizar `docs/CHANGELOG.md`

Entrada nova no topo:
```markdown
### 2026-MM-DD — F9.2 fechada: strings descritivas em produção (ADR-093)

- Sub-fatias mergeadas: T1 (stage_spec), 2a (pipeline core), 2b (scripts),
  2c (e_reset CLI deprecation), 2d (backend + tests não-golden), 2e (closeout).
- `STAGE_REGISTRY`/`FULL_ORDER`/`DETERMINISTIC_ORDER` em descritivo.
- `STAGE_RENAME_MAP` mantido como compat reverso + helpers
  `resolve_stage_name`/`to_legacy_stage_name`.
- CLI `scripts/e_reset.py --from E3` aceita legado com warning de deprecação
  (remoção em F9.6).
- DB `pipeline_artifacts.stage` **inalterado** — F9.3 (Alembic) endereça em
  fatia separada. Janela: app lê rows legadas via `resolve_stage_name`.
- Audit pós-F9.2: `docs/audits/f9_audit_pos_f9_2_<date>.md`.
- Goldens: <regenerados se aplicável> | intactos.
```

### 6. Atualizar `docs/DECISIONS.md` ADR-093

Adicionar nota datada no início ou no final do ADR:
```
**F9.2 fechada 2026-MM-DD.** Código de produção usa nomes descritivos.
`STAGE_RENAME_MAP` é compat reverso. F9.3 (Alembic migration de
`pipeline_artifacts.stage`) destravada.
```

### 7. Atualizar `CLAUDE.md`

Procure §"Stage identifiers — F9.2+ usa nomes descritivos (ADR-093)" (já
existe? confirme em `git grep -n "Stage identifiers" CLAUDE.md`). Substitua
texto antigo por:

```markdown
### Stage identifiers — F9.2+ usa nomes descritivos (ADR-093)

**F9.2 fechada YYYY-MM-DD.** `STAGE_REGISTRY`/`FULL_ORDER`/`DETERMINISTIC_ORDER`
em `pipeline/stage_spec.py` agora usam keys descritivas
(`"reconcile_transactions"`, `"analyze_finances"`, `"extract_statements"`…).
Em **código novo**, prefira o nome descritivo.

Para input externo (HTTP body, CLI arg, DB row durante janela →F9.3),
use `resolve_stage_name(name)` — aceita legacy (`"E3"`) ou descritivo,
retorna sempre descritivo. Inverso em `to_legacy_stage_name()` para
adapters que ainda gravam DB legado.

`STAGE_RENAME_MAP` permanece como compat reverso. DB
`pipeline_artifacts.stage` continua em formato legado até F9.3
(Alembic). Janela de compat termina em F9.6.
```

### 8. Atualizar `docs/agent_prompts/README.md`

Marcar inline na tabela que F9.2 está fechada (ou nada — README não rastreia
status; apenas confirme que F9.3 está listada e referenciável).

## Gate

Doc-only — pule pytest, **mas rode pre-commit**:
```bash
pre-commit run --all-files
```

## Commit + push

```bash
git add docs/audits/ docs/BACKLOG.md docs/CHANGELOG.md docs/DECISIONS.md \
        CLAUDE.md docs/agent_prompts/README.md

git commit -m "$(cat <<'EOF'
docs(f9): F9.2 fechada — strings descritivas em produção (ADR-093)

Closeout das sub-fatias T1+2a+2b+2c+2d. STAGE_REGISTRY usa nomes
descritivos; STAGE_RENAME_MAP é compat reverso. DB rows ainda legadas
(F9.3 endereça). CLI e_reset.py emite deprecação em --from <legacy>.

Audit pós: docs/audits/f9_audit_pos_f9_2_<date>.md
EOF
)"

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main
git push origin HEAD:main
```

## Critérios de aceite

- [ ] Audit re-rodado e arquivado em `docs/audits/`.
- [ ] Strings residuais em `pipeline/`/`backend/app/`/`scripts/` todas justificadas.
- [ ] BACKLOG marca F9.2 ✅ + F9.3 destravada.
- [ ] CHANGELOG tem entrada datada.
- [ ] ADR-093 ganha nota datada.
- [ ] CLAUDE.md atualizado.
- [ ] `pre-commit run --all-files` verde.
- [ ] Mergeado em `origin/main`.

## Anti-padrões

- ❌ Tocar código fora de docs/audits — esta fatia é doc-only.
- ❌ Marcar F9.2 fechada antes de TODAS as sub-fatias 2a-2d em main.
- ❌ Reescrever histórico (CHANGELOG entries antigas).

## Referências

- [F9.2 master](track_f9_2_string_literals.md)
- [F9.2a-d sub-fatias](README.md)
- [F9.3 alembic — destravada após esta lane](track_f9_3_alembic_migration.md)
