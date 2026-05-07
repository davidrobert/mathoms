---
id: TRACK-f9-2-string-literals
type: track
title: "Track F9.2 — Substituir strings literais `\"E*\"` em código de produção"
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

# Track F9.2 — Substituir strings literais `"E*"` em código de produção

> **Lane ID:** F9.2
> **Branch prefix:** `agent/f9-stage-rename/2-strings/*`
> **Depende de:** F9.1 ✅ (filenames `pipeline/stages/` renomeados)
> **Paralelo com:** nenhum (sequencial; bloqueia 9.3)
> **Conflita com:** qualquer commit em `pipeline/`, `backend/app/`, `scripts/`, `tests/` (escopo enorme — não há janela paralela viável)
> **Onda:** F9 (sub-fatia 3/7) — **a maior das 7**
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a) · [`STAGE_RENAME_MAP`](../../pipeline/stage_spec.py#L129)

> **Objetivo:** trocar todas as strings literais `"E0-audit"`, `"E1.5c"`,
> `"E2-faturas"`, `"E3"`, `"E5"`, `"E5.N"`, `"E7-apply"`… (16 keys do
> `STAGE_RENAME_MAP`) por seus equivalentes descritivos em **código de
> produção**, atualizando `STAGE_REGISTRY`/`FULL_ORDER`/`DETERMINISTIC_ORDER`,
> mantendo `STAGE_RENAME_MAP` apenas como referência histórica + alias
> compat para queries legadas durante 1 release.

---

## Por que este slice é o mais delicado

Strings literais `"E3"` aparecem em:
- `pipeline/stage_spec.py` (registry — fonte de verdade)
- `pipeline/orchestrator.py` (FROM_MAP, switches)
- `backend/app/services/pipeline_service.py` (run dispatch)
- `backend/app/repositories/artifact_repository.py` (queries)
- `backend/app/api/routers/pipeline.py` (params)
- `scripts/e_reset.py` (CLI `--from E3`)
- 30+ tests
- Logs estruturados (`logger.info("stage=%s", "E3")`)
- Frontend types gerados via OpenAPI snapshot

A auditoria de F9.0 produz a **lista exata**. Trabalhe arquivo-por-arquivo,
`pytest` entre cada — diff cumulativo de 100+ linhas sem teste é convite
para regressão silenciosa.

---

## Regras inegociáveis

1. **`STAGE_RENAME_MAP` é referência, não fonte de verdade após esta fatia.**
   Em F9.2, `STAGE_REGISTRY` passa a usar keys descritivas; `STAGE_RENAME_MAP`
   permanece como dicionário de **compat reverso** (`{"E3": "reconcile_transactions"}`)
   por 1 release para CLI alias (F9.4) e queries legadas.
2. **Alias bidirecional para CLI.** `e_reset.py --from E3` continua funcionando
   via lookup em `STAGE_RENAME_MAP` (será deprecado em F9.6). Mensagem de
   warning ao detectar uso legado: `[deprecated] use --from reconcile_transactions; "E3" será removido em F9.6`.
3. **Logs e `pipeline_artifacts.stage` (DB) NÃO mudam aqui.** Logs estruturados
   passam a emitir nome descritivo (mudança automática quando `STAGE_REGISTRY`
   muda). DB rows são F9.3 (Alembic). Durante a janela entre F9.2 deploy e
   F9.3 alembic upgrade, o app **lê** rows legadas via `STAGE_RENAME_MAP`
   reverso.
4. **Goldens são o gate principal.** Qualquer string `"E3"` em arquivo `*_golden.py`
   ou `*_parity.py` é dado de fixture imutável — não mude. Goldens são
   responsabilidade do produtor (`STAGE_REGISTRY`); se o produtor agora gera
   `"reconcile_transactions"`, o golden tem que ser regenerado **e** isso é
   uma mudança intencional documentada no commit.
5. **OpenAPI snapshot:** após mudar enum/Literal de stage em DTOs, rode
   `make update-openapi-snapshot` e comite o diff (CLAUDE.md §Endpoint JSON).

---

## Ordem de ataque (de mais isolado para mais conectado)

### Tier 1 — fonte de verdade (1 commit)

`pipeline/stage_spec.py`: trocar keys de `STAGE_REGISTRY`, `FULL_ORDER`,
`DETERMINISTIC_ORDER`, `VIRTUAL_ARTIFACT_STAGES`. Manter `STAGE_RENAME_MAP`
**inalterado** (vira o dicionário reverso compat).

```python
# Adicionar:
LEGACY_TO_DESCRIPTIVE = STAGE_RENAME_MAP  # alias para clarear intenção
DESCRIPTIVE_TO_LEGACY = {v: k for k, v in STAGE_RENAME_MAP.items()}

def resolve_stage_name(name: str) -> str:
    """Aceita legado ou descritivo, retorna sempre descritivo."""
    return STAGE_RENAME_MAP.get(name, name)
```

**Gate:** `pytest tests/unit/pipeline -q` verde.

**Commit 1:** `refactor(pipeline): STAGE_REGISTRY usa nomes descritivos (F9.2 — T1)`

### Tier 2 — orquestrador + serviços backend (1-3 commits)

- `pipeline/orchestrator.py` (FROM_MAP, switches)
- `backend/app/services/pipeline_service.py`
- `backend/app/repositories/artifact_repository.py`
- `backend/app/repositories/pipeline_artifact_repository.py`

Para cada arquivo: substituir strings, adicionar `resolve_stage_name()` em
qualquer ponto que recebe input externo (HTTP body, CLI arg). `pytest backend/tests -q` entre commits.

**Gate:** `pytest backend/tests -q` verde + smoke local de pipeline run.

**Commit 2-4:** `refactor(<scope>): strings stage descritivas (F9.2 — T2)`

### Tier 3 — routers HTTP + DTOs (1 commit)

- `backend/app/api/routers/pipeline.py`
- `backend/app/api/dto/*.py` (Literal[stage] em DTOs)

OpenAPI muda — rode `make update-openapi-snapshot`, commite o diff.

**Gate:** `pytest backend/tests/test_openapi_*.py -q` verde + frontend codegen
sem warning.

**Commit 5:** `refactor(api): pipeline DTOs com nomes descritivos + alias legado (F9.2 — T3)`

### Tier 4 — tests (não-golden) (1-3 commits)

Strings `"E3"`/`"E5"` em testes que **não** são goldens. Auditoria F9.0
classifica isso. Manter goldens intocados; se um test não-golden quebra
porque o produtor mudou, é teste **errado** que estava acoplado ao formato
legado — atualize.

**Gate:** `pytest tests -q` + `pytest backend/tests -q` verde.

**Commit 6-8:** `test: stage strings descritivas em <scope> (F9.2 — T4)`

### Tier 5 — config + docs (1 commit)

- `config/pipeline.json` (se houver referências por nome)
- `config/report_layout.yaml` (idem)
- Inline docs em código (docstrings, comentários `# E3 reads from E2`).

Nota: docs em `docs/**` (BACKLOG, CHANGELOG, ADRs antigos) **não** mudam — são
referência histórica. ADR-093 e ARCHITECTURE.md ganham nota datada
"F9.2 ativa: nomes descritivos em código; legado disponível via
`resolve_stage_name`".

**Gate:** `pre-commit run --all-files`.

**Commit 9:** `chore(config): nomes descritivos em pipeline.json/report_layout (F9.2 — T5)`

---

## Sequência de execução

```bash
git fetch origin && git status
git checkout -b agent/f9-stage-rename/2-strings/$(date +%Y%m%d-%H%M)

# Baseline
pytest tests -q 2>&1 | tail -3
pytest backend/tests -q 2>&1 | tail -3

# Para cada Tier (T1 → T5), commit + pytest entre
# Total: ~9 commits

# Gate final
pre-commit run --all-files
pytest tests -q                          # goldens passam (produtor agora emite descritivo; goldens regenerados se intencional)
pytest backend/tests -q
make update-openapi-snapshot && git diff backend/openapi.json
cd frontend && npm test -- --run; cd -

# Drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `STAGE_REGISTRY` keys são todas descritivas (`"reconcile_transactions"` etc).
- [ ] `STAGE_RENAME_MAP` mantém forma `legacy → descriptive` (compat reverso).
- [ ] `resolve_stage_name(legacy_or_descriptive)` retorna sempre descritivo.
- [ ] CLI `e_reset.py --from E3` ainda funciona com warning de deprecação.
- [ ] OpenAPI snapshot regenerado e commitado.
- [ ] Goldens regenerados (se intencional) — diff revisado.
- [ ] `grep -rn '"E[0-9]' pipeline/ backend/app/ scripts/` retorna apenas:
  (a) `STAGE_RENAME_MAP` em `stage_spec.py`,
  (b) testes de compat,
  (c) docstrings/comentários explicitando legado.
- [ ] `pytest tests -q` + `pytest backend/tests -q` verdes.
- [ ] Frontend `npm test -- --run` verde.
- [ ] BACKLOG + CHANGELOG atualizados.

---

## Rollback criteria — ABORTE se

- Smoke run de pipeline (E0→E5.N) trava em algum stage com `KeyError` por
  nome não resolvido.
- OpenAPI diff explode (>500 linhas) — sinal de que mudou enum em DTO sem
  migration de cliente; revise plano.
- Frontend tests quebram em massa por type mismatch — provavelmente faltou
  regenerar codegen.
- Mais de 3 goldens regeneram diff não-trivial sem você entender o que mudou.

---

## Atualizar documentação (obrigatório, último passo)

1. **`docs/BACKLOG.md`** — lane F9 status: `🚧 F9.0/.1 ✅ · F9.2 ✅ — strings descritivas em produção YYYY-MM-DD, ~N commits; F9.3 destravada (Alembic migration)`.
2. **`docs/CHANGELOG.md`** — entrada detalhada:
   ```markdown
   ### 2026-MM-DD — F9.2 strings descritivas em produção (ADR-093)

   - `STAGE_REGISTRY`/`FULL_ORDER`/`DETERMINISTIC_ORDER` em
     `pipeline/stage_spec.py` agora usam nomes descritivos como keys.
   - `STAGE_RENAME_MAP` mantido como compat reverso (legacy → descriptive)
     + helper `resolve_stage_name(name)` para inputs externos.
   - CLI `scripts/e_reset.py --from E3` aceita legado com warning de
     deprecação (remoção em F9.6).
   - OpenAPI snapshot regenerado: `<diff_summary>` (DTOs de pipeline).
   - DB `pipeline_artifacts.stage` **inalterado** — F9.3 (Alembic) endereça.
     Janela: app lê rows legadas via `resolve_stage_name`.
   ```
3. **`docs/reference/ARCHITECTURE.md` §7 e §10** — atualizar tabelas/refs de stages.
4. **`docs/DECISIONS.md`** ADR-093 — nota datada "F9.2 fechada YYYY-MM-DD".
5. **`CLAUDE.md` §Regras críticas › "Stage identifiers — use nomes legados até F9 (ADR-093)"** — atualizar para refletir nova realidade: "Em F9.2+ código de produção usa nomes descritivos; `resolve_stage_name(name)` aceita ambos durante janela de compat até F9.6".
6. Commit docs separado: `docs(f9): F9.2 strings descritivas, F9.3 destravada (ADR-093)`.

---

## O que esta fatia NÃO entrega

- **DB rows ainda legadas.** `pipeline_artifacts.stage = "E3"` permanece até F9.3.
- **Filenames `scripts/e*.py`.** F9.4.
- **Hard-fail no `test_no_legacy_stage_names.py`.** F9.5.
- **Remoção de `STAGE_RENAME_MAP` + alias compat.** F9.6.

---

## Referências

- F9.1 (prereq): [track_f9_1_pipeline_stages_rename.md](track_f9_1_pipeline_stages_rename.md)
- F9.3 (próximo): [track_f9_3_alembic_migration.md](track_f9_3_alembic_migration.md)
- ADR-093: `docs/DECISIONS.md:2228`
- Auditoria F9.0: `docs/archive/audits/f9_audit_<date>.md` (lista exata de strings).
