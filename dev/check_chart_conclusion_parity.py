#!/usr/bin/env python3
"""Paridade YAML ↔ TS dos chart conclusions (ADR-117 · ADR-122).

`config/prompts/chart_conclusions.yaml` é declarado source-of-truth, mas o
consumidor real é `frontend/src/components/report/utils/conclusionUtils.ts`,
que duplica a lógica inline (BUILDERS + FALLBACKS) — sem carregar o YAML em
runtime. Sem gate, o YAML deriva do que o TS de fato produz (audit-vault r3:
F09/F10/F11/F18). Este check trava a divergência estrutural.

Escopo pragmático (regex, sem parser TS completo):

  1. Toda key de FALLBACKS do TS existe no YAML, e toda key de BUILDERS do TS
     existe no YAML — o TS não pode referenciar chart que o YAML desconhece
     (essa é a direção que sinaliza drift real).
     NÃO exigimos o inverso (todo chart do YAML ter FALLBACKS): o TS omite
     fallback de propósito para alguns charts (deriveChartConclusion retorna
     null → box oculto). Charts do YAML sem builder e sem fallback no TS são
     efetivamente inativos no runtime atual, mas o YAML os mantém como catálogo.
  2. Todo chart do YAML com `required_keys` OU placeholders `{...}`
     não-triviais que NÃO tem builder deve estar marcado `# fallback-only`
     na linha da key — senão dá falsa impressão de interpolação ativa.
  3. Chart marcado `# fallback-only` não pode estar em BUILDERS (contradição).
  4. Todo id literal passado a `deriveChartConclusion(...)`/`getConclusion(...)`
     em frontend/src/components/report/sections/*.tsx existe em
     BUILDERS ∪ FALLBACKS — call site com id desconhecido renderiza o chart
     sem conclusão em runtime, silenciosamente (audit-vault r4: S2 usava
     `receita_fonte`/`despesas_categoria` em vez de
     `receita_bar`/`despesas_doughnut`).
  5. Em sections/*.tsx, o bag `narrativas` só pode ser acessado via `.charts`
     (A40.l4 · ADR-355). Mesma classe da regra 4, um nível acima: leitura no
     TOPO de `narrativas` — `narrativas?.["S1"]`, `narrativas?.score_gauge` —
     renderiza vazio em runtime porque nenhum produtor emite ali. O parágrafo
     de seção vem de `<SectionSummary data={data}>` (precedência em
     `utils/sectionSummarySource.ts`); a conclusão de chart vem de
     `narrativas.charts[id]` via `utils/chartNarrative.ts`.

Uso:
    python3 dev/check_chart_conclusion_parity.py
    python3 dev/check_chart_conclusion_parity.py --verbose

Exit 0 = paridade OK, 1 = divergência.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_YAML_PATH = _REPO_ROOT / "config" / "prompts" / "chart_conclusions.yaml"
_TS_PATH = (
    _REPO_ROOT / "frontend" / "src" / "components" / "report" / "utils" / "conclusionUtils.ts"
)
_SECTIONS_DIR = _REPO_ROOT / "frontend" / "src" / "components" / "report" / "sections"

# Placeholder {campo|fmt} — só conta como "interpolação ativa" se referenciar
# um campo real. Vazio ou puramente decorativo não conta.
_PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][\w.]*(?:\|[a-z]+)?\}")

_FALLBACK_ONLY_MARKER = "fallback-only"


def _load_yaml_charts() -> dict[str, dict]:
    data = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))
    templates = (data or {}).get("templates") or {}
    if not isinstance(templates, dict):
        raise ValueError("chart_conclusions.yaml: `templates` não é um mapping")
    return templates


_YAML_KEY_LINE_RE = re.compile(r"^  ([a-zA-Z_]\w*):\s*(#.*)?$")
_TS_KEY_RE = re.compile(r"^([a-zA-Z_]\w*)\s*:")


def _fallback_only_keys() -> set[str]:
    """Keys cuja linha `<key>:` traz o comentário `# fallback-only` (PyYAML descarta comentários)."""
    lines = _YAML_PATH.read_text(encoding="utf-8").splitlines()
    matches = (_YAML_KEY_LINE_RE.match(line) for line in lines)
    return {m.group(1) for m in matches if m and _FALLBACK_ONLY_MARKER in (m.group(2) or "")}


def _extract_ts_block(src: str, decl: str) -> str:
    """Extrai o corpo `{...}` de `const NAME ... = {`, balanceando chaves aninhadas."""
    brace = src.index("{", src.index(decl))
    depth = 0
    for i in range(brace, len(src)):
        depth += 1 if src[i] == "{" else -1 if src[i] == "}" else 0
        if depth == 0:
            return src[brace : i + 1]
    raise ValueError(f"bloco não balanceado a partir de `{decl}`")


def _ts_top_level_keys(block: str) -> set[str]:
    """Keys de primeiro nível de um objeto TS (ignora aninhados)."""
    out: set[str] = set()
    depth = 0
    for line in block.splitlines():
        m = _TS_KEY_RE.match(line.strip())
        if depth == 1 and m:
            out.add(m.group(1))
        depth += line.count("{") - line.count("}")
    return out


def _load_ts_keys() -> tuple[set[str], set[str]]:
    src = _TS_PATH.read_text(encoding="utf-8")
    builders_block = _extract_ts_block(src, "const BUILDERS")
    fallbacks_block = _extract_ts_block(src, "const FALLBACKS")
    return _ts_top_level_keys(builders_block), _ts_top_level_keys(fallbacks_block)


def _has_active_interpolation(spec: dict) -> bool:
    if spec.get("required_keys"):
        return True
    template = spec.get("template") or ""
    return bool(_PLACEHOLDER_RE.search(template))


def _ts_refs_unknown_chart(
    yaml_ids: set[str], builders: set[str], fallbacks: set[str]
) -> list[str]:
    """Regra 1 — TS não referencia chart desconhecido do YAML (drift real)."""
    return [
        f"chart `{cid}` em {label} do TS sem template no YAML ({_YAML_PATH.name})"
        for label, keys in (("FALLBACKS", fallbacks), ("BUILDERS", builders))
        for cid in sorted(keys - yaml_ids)
    ]


def _interpolation_without_builder(
    charts: dict[str, dict], builders: set[str], fallback_only: set[str]
) -> list[str]:
    """Regra 2 — interpolação declarada exige builder OU marca fallback-only."""
    orphans = [
        cid
        for cid in sorted(charts)
        if _has_active_interpolation(charts[cid])
        and cid not in builders
        and cid not in fallback_only
    ]
    return [
        f"chart `{cid}` tem required_keys/placeholders mas não tem builder no TS "
        f"nem está marcado `# {_FALLBACK_ONLY_MARKER}` no YAML "
        f"(cai sempre no fallback — placeholders não interpolam)"
        for cid in orphans
    ]


# Só ids literais — id via variável/expressão fica fora do escopo do gate
# (não há caso hoje; se surgir, o autor promove o literal ou estende o regex).
_CALL_SITE_RE = re.compile(r'\b(?:deriveChartConclusion|getConclusion)\(\s*"([^"]+)"')


_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
# `(?<!:)` preserva `https://` — comentário de linha em TS/TSX nunca vem após `:`.
_LINE_COMMENT_RE = re.compile(r"(?<!:)//[^\n]*")


# Sem strip de comentário, um comentário que documenta a REMOÇÃO de um padrão
# proibido (`// antes lia narrativas["S8"]`) dispara a própria regra.
def _tsx_code(path: Path) -> str:
    """Fonte sem comentários — o gate mede código, não prosa sobre o código."""
    src = path.read_text(encoding="utf-8")
    return _LINE_COMMENT_RE.sub("", _BLOCK_COMMENT_RE.sub("", src))


def _section_call_sites() -> dict[str, set[str]]:
    """Ids literais por arquivo em sections/*.tsx (regra 4)."""
    out: dict[str, set[str]] = {}
    for tsx in sorted(_SECTIONS_DIR.glob("*.tsx")):
        ids = set(_CALL_SITE_RE.findall(_tsx_code(tsx)))
        if ids:
            out[tsx.name] = ids
    return out


def _call_site_unknown_id(builders: set[str], fallbacks: set[str]) -> list[str]:
    """Regra 4 — call site em sections/*.tsx só usa id de BUILDERS ∪ FALLBACKS."""
    known = builders | fallbacks
    return [
        f"chart `{cid}` chamado em sections/{fname} não existe em BUILDERS nem "
        f"FALLBACKS de {_TS_PATH.name} (conclusão renderiza vazia em runtime)"
        for fname, ids in _section_call_sites().items()
        for cid in sorted(ids - known)
    ]


# Acesso ao bag `narrativas`: `.charts` / `?.charts` / `["charts"]`. Qualquer
# outro acessor é leitura no topo do bag. Casts (`data.narrativas as X`) e props
# JSX (`narrativas={...}`) não casam — não há `.`/`[` depois do identificador.
_NARRATIVAS_ACCESS_RE = re.compile(
    r"narrativas\s*\??\.\s*([A-Za-z_]\w*)" r"|narrativas\s*\??\.?\s*\[\s*([^\]\n]+?)\s*\]"
)
_ALLOWED_NARRATIVAS_ACCESS = frozenset({"charts", '"charts"', "'charts'"})


def _forbidden_accessors(tsx: Path) -> list[str]:
    """Acessores de `narrativas` fora da allowlist, num arquivo."""
    matches = _NARRATIVAS_ACCESS_RE.finditer(_tsx_code(tsx))
    accessors = (m.group(1) or m.group(2) or "" for m in matches)
    return [a for a in accessors if a not in _ALLOWED_NARRATIVAS_ACCESS]


def _narrativas_top_level_access() -> list[str]:
    """Regra 5 — em sections/*.tsx, `narrativas` só via `.charts`."""
    return [
        f"leitura `narrativas[{accessor}]` em sections/{tsx.name} — o bag "
        "só tem `charts`, `summaries` e `perfil_familia`; leitura no topo "
        "renderiza vazio em runtime. Parágrafo de seção: "
        "<SectionSummary data={data}>; conclusão de chart: "
        "readNarrativeConclusion(narrativas.charts, id)"
        for tsx in sorted(_SECTIONS_DIR.glob("*.tsx"))
        for accessor in _forbidden_accessors(tsx)
    ]


def _fallback_only_with_builder(fallback_only: set[str], builders: set[str]) -> list[str]:
    """Regra 3 — fallback-only não pode ter builder (contradição)."""
    return [
        f"chart `{cid}` marcado `# {_FALLBACK_ONLY_MARKER}` mas TEM builder no TS "
        f"— remova a marca ou o builder"
        for cid in sorted(fallback_only & builders)
    ]


def collect_violations() -> list[str]:
    charts = _load_yaml_charts()
    yaml_ids = set(charts)
    fallback_only = _fallback_only_keys()
    builders, fallbacks = _load_ts_keys()
    return [
        *_ts_refs_unknown_chart(yaml_ids, builders, fallbacks),
        *_interpolation_without_builder(charts, builders, fallback_only),
        *_fallback_only_with_builder(fallback_only, builders),
        *_call_site_unknown_id(builders, fallbacks),
        *_narrativas_top_level_access(),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors = collect_violations()
    if args.verbose and not errors:
        print("OK: chart conclusions YAML ↔ TS em paridade", file=sys.stderr)
    for line in errors:
        print(f"chart-conclusion-parity: {line}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
