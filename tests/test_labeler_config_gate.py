"""Gates de glob: negativo sob `any-glob-to-*` casa em todo PR; `**` colado não cruza `/`."""

from __future__ import annotations

import yaml

from dev.check_labeler_config import (
    DEFAULT_CONFIG,
    WORKFLOW_DIR,
    iter_globs,
    iter_workflow_globs,
    load_workflow_filters,
    scan_config,
    scan_globstars,
    suggest_globstar,
)

BROKEN = """\
'area:docs':
  - changed-files:
      - any-glob-to-any-file:
          - 'docs/**'
          - '!**/CHANGELOG.md'
"""

CORRECT = """\
'area:docs':
  - changed-files:
      - any-glob-to-any-file:
          - 'docs/**'
      - all-globs-to-all-files:
          - '!**/CHANGELOG.md'
"""

GLUED = """\
'area:go':
  - changed-files:
      - any-glob-to-any-file:
          - '**.go'
          - 'config/**.yaml'
'area:x':
  - changed-files:
      - all-globs-to-all-files:
          - '!**.md'
"""

CLEAN_GLOBSTAR = """\
'area:go':
  - changed-files:
      - any-glob-to-any-file:
          - '**/*.go'
          - 'config/**/*.yaml'
          - 'docs/**'
          - '**'
          - '*.md'
"""


def test_detecta_negativo_sob_any() -> None:
    violations = scan_config(yaml.safe_load(BROKEN))
    assert [(v.label, v.glob) for v in violations] == [("area:docs", "!**/CHANGELOG.md")]


def test_aceita_negativo_sob_all_globs_to_all_files() -> None:
    assert scan_config(yaml.safe_load(CORRECT)) == []


def test_detecta_globstar_colado_em_qualquer_chave() -> None:
    """Glob errado é errado sob `any-*` e sob `all-*`; negativo inclusive."""
    found = scan_globstars(iter_globs(yaml.safe_load(GLUED)))
    assert [v.glob for v in found] == ["**.go", "config/**.yaml", "!**.md"]


def test_globstar_como_segmento_inteiro_passa() -> None:
    assert scan_globstars(iter_globs(yaml.safe_load(CLEAN_GLOBSTAR))) == []


def test_sugestao_insere_barra_no_globstar_prefixo() -> None:
    assert suggest_globstar("**.go") == "**/*.go"
    assert suggest_globstar("config/**.yaml") == "config/**/*.yaml"
    assert suggest_globstar("!**.md") == "!**/*.md"


def test_sugestao_ausente_quando_globstar_nao_inicia_segmento() -> None:
    """`a**b` não tem reescrita óbvia — melhor não sugerir do que sugerir errado."""
    assert suggest_globstar("src/a**b.ts") is None
    assert suggest_globstar("**/*.go") is None


def test_area_adr_cobre_o_vault_atomizado() -> None:
    """Regressão: pós-[[ADR-182]] F2 a label casava só docs/DECISIONS.md (shim)."""
    parsed = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    globs = [glob for label, _, glob in iter_globs(parsed) if label == "area:adr"]
    assert "docs/adr/**" in globs, globs


def test_config_real_esta_limpa() -> None:
    parsed = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    findings = [*scan_config(parsed), *scan_globstars(iter_globs(parsed))]
    assert findings == [], [f.format() for f in findings]


def test_matrizes_files_yaml_dos_workflows_estao_limpas() -> None:
    """Os globs de ci.yml/security.yml são declarados alinhados com o labeler."""
    scanned = 0
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        filters = load_workflow_filters(path)
        if not filters:
            continue
        scanned += 1
        findings = scan_globstars(iter_workflow_globs(filters))
        assert findings == [], [f"{path.name}: {f.format()}" for f in findings]
    assert scanned >= 2, f"esperava ci.yml + security.yml, varreu {scanned}"
