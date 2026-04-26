# Track F9.2c — `scripts/e_reset.py` deprecation warning + flip interno

> **Lane ID:** F9.2c
> **Branch prefix:** `agent/f9-stage-rename/2c-e-reset/*`
> **Depende de:** F9.2a ✅ (`resolve_stage_name` disponível)
> **Bloqueia:** F9.2e (closeout)
> **Paralelo com:** F9.2b, F9.2d (escopo isolado em 1 arquivo)
> **Onda:** F9 (sub-fatia 3c/7)
> **Fonte de verdade:** [ADR-093](../DECISIONS.md#adr-093)

> **Objetivo:** atualizar `scripts/e_reset.py` para (a) aceitar `--from <legacy>`
> com warning de deprecação, (b) trocar strings internas para descritivas,
> (c) manter compat até F9.6.

---

## Estado atual

`scripts/e_reset.py` é a maior concentração de strings legadas no repo (120 hits).
Boa parte está intencional (legacy alias map para CLI compat). Esta fatia:
1. Adiciona warning quando usuário passa `--from E3`.
2. Internamente usa nome descritivo após o normalize.
3. Mantém o mapeamento como compat até F9.6.

## Mudanças

### 1. Deprecation warning no parsing de `--from`

```python
import sys
from pipeline.stage_spec import STAGE_RENAME_MAP, resolve_stage_name

def _normalize_from_stage(value: str) -> str:
    """Aceita legacy ou descritivo; warn em legacy + retorna descritivo."""
    if value in STAGE_RENAME_MAP:
        descriptive = STAGE_RENAME_MAP[value]
        print(
            f'[deprecated] use --from {descriptive}; '
            f'"{value}" será removido em F9.6',
            file=sys.stderr,
        )
        return descriptive
    return resolve_stage_name(value)
```

Aplique no ponto que parseia `args.from_stage` (ou equivalente).

### 2. Flip de strings internas

Onde `e_reset.py` referencia stages diretamente (não como alias map), trocar
para descritivo. Strings dentro do dict de aliases legacy permanecem.

### 3. Help text

Atualize `--help` para mostrar exemplos com nomes descritivos primário e
mencionar que aliases legados ainda funcionam:

```
--from STAGE  Stage de início (ex.: reconcile_transactions, analyze_finances).
              Aliases legados (E3, E5) aceitos com aviso de deprecação até F9.6.
```

### 4. Teste de regressão

Adicione em `tests/test_e_reset.py` (ou novo arquivo se não existir):

```python
def test_legacy_from_emits_deprecation_warning(capsys, ...):
    # roda e_reset.py com --from E3; assert stderr contém "[deprecated]"
    # assert pipeline executa começando em reconcile_transactions
```

## Gate

```bash
source ../../../.venv/bin/activate
pytest tests -q -k "reset or e_reset"  # ou pytest tests -q se não for caro
```

## Commits sugeridos

1. `refactor(scripts): e_reset.py flip interno para descritivos (F9.2c — T1)`
2. `feat(scripts): e_reset.py warn deprecation em aliases legados (F9.2c — T2)`
3. `test(scripts): regressão deprecation warning em e_reset (F9.2c — T3)`

(Pode ser 1 commit único se o agente preferir.)

## Sequência

```bash
git fetch origin
git checkout -b agent/f9-stage-rename/2c-e-reset/$(date +%Y%m%d-%H%M)
source ../../../.venv/bin/activate

pytest tests -q 2>&1 | tail -3  # baseline

# implementação

pre-commit run --all-files
pytest tests -q

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest tests -q
git push origin HEAD:main
```

## Critérios de aceite

- [ ] `e_reset.py --from E3` continua funcionando + emite warning em stderr.
- [ ] `e_reset.py --from reconcile_transactions` funciona sem warning.
- [ ] `e_reset.py --help` mostra exemplos descritivos.
- [ ] Teste de regressão cobrindo o warning.
- [ ] `pytest tests -q` verde.
- [ ] Strings internas (não-alias) flipadas para descritivo.

## Anti-padrões

- ❌ Remover o alias map (vai em F9.6).
- ❌ Renomear o filename `e_reset.py` (não é stage; permanece).
- ❌ Mudar comportamento do `e_reset` além da string normalization.

## Referências

- [F9.2a pipeline core](track_f9_2a_pipeline_core_strings.md)
- [F9.2 master](track_f9_2_string_literals.md) §"CLI alias bidirecional"
- [F9.6 cleanup](track_f9_6_cleanup.md) — remoção do warning
