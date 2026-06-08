#!/usr/bin/env python3
"""Diff valor-a-valor de dois goldens JSON — rede de regressão number-level (A23.l2). Classifica cada campo entre ``unchanged | moved | value_delta | new | removed``; delta monetário em cents int (ADR-090, nunca float); puro/stateless (ADR-111). Monetário-por-default: campo numérico é monetário salvo allowlist não-monetária — campo novo falha alto, nunca passa silencioso. Todo ``value_delta`` monetário exige entrada no manifesto de rebaseline (exit≠0 se não-justificado ou manifesto stale). Uso: ``python dev/golden_diff.py OLD NEW [--manifest M.yaml] [--golden-id ID]``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

# Chaves-folha numéricas que NÃO são monetárias (percentuais, contagens, idades,
# anos, ratios, score). Tudo o mais numérico é tratado como monetário (default).
_NON_MONETARY_EXACT = frozenset(
    {
        "pct",
        "peso",
        "nota",
        "max",
        "n",
        "sigma_usado",
        "fator_reduzido",
        "aliquota_marginal",
        "data",
        "idade_david",
        "idade_meta_usada",
        "ano_if",
        "anos_if",
        "if_pct",
        "if_trs",
        "meta_pct",
        "folga_pct",
        "n_imoveis_total",
        "janela_n_meses",
        "transacoes_total",
        "transacoes_duplicadas_removidas",
        "acumuladores_pct_gerador",
        "percentual_patrimonio",
        "prob_if_ate_idade_meta",
        "taxa_poupanca_recorrente",
        "taxa_poupanca_total",
    }
)
_NON_MONETARY_SUFFIXES = (
    "_pct",
    "_meses",
    "_anos",
    "_idade",
    "_idade_if",
    "_ano_if",
    "idade_if",
    "_aa",
)
_NON_MONETARY_PREFIXES = ("idade_", "anos_", "ano_", "nivel_", "prazo_", "prazos_")

ClassifyFn = Callable[[str], bool]


def is_monetary(path: str) -> bool:
    """``True`` se o campo (dot-path) é monetário — monetário-por-default."""
    leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
    if leaf in _NON_MONETARY_EXACT:
        return False
    if leaf.endswith(_NON_MONETARY_SUFFIXES):
        return False
    if leaf.startswith(_NON_MONETARY_PREFIXES):
        return False
    return True


def to_cents(value: Any) -> int:
    """Converte valor monetário para cents int (ADR-090: via ``Decimal(str(v))``)."""
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"valor não-monetário em campo monetário: {value!r}") from exc


@dataclass(frozen=True)
class FieldDiff:
    path: str
    kind: str  # unchanged | moved | value_delta | new | removed
    old: Any = None
    new: Any = None
    delta_cents: int | None = None  # só para value_delta monetário

    def is_monetary_value_delta(self) -> bool:
        return self.kind == "value_delta" and self.delta_cents is not None


_NATURAL_KEYS = ("categoria", "property_id", "codigo_rfb", "code", "id", "nome", "key")


def _natural_key(item: Any) -> Any | None:
    if not isinstance(item, dict):
        return None
    for key in _NATURAL_KEYS:
        if key in item:
            return (key, item[key])
    return None


def _is_scalar(value: Any) -> bool:
    return not isinstance(value, (dict, list))


def _scalar_diff(path: str, old: Any, new: Any, classify: ClassifyFn) -> list[FieldDiff]:
    if old == new:
        return [FieldDiff(path, "unchanged", old, new)]
    if isinstance(old, bool) or isinstance(new, bool):
        return [FieldDiff(path, "value_delta", old, new)]
    if classify(path) and isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return [FieldDiff(path, "value_delta", old, new, to_cents(new) - to_cents(old))]
    return [FieldDiff(path, "value_delta", old, new)]


def _diff_list(path: str, old: list, new: list, classify: ClassifyFn) -> list[FieldDiff]:
    old_keyed = {_natural_key(it): it for it in old if _natural_key(it) is not None}
    new_keyed = {_natural_key(it): it for it in new if _natural_key(it) is not None}
    if len(old_keyed) == len(old) and len(new_keyed) == len(new) and old:
        return _diff_keyed_list(path, old_keyed, new_keyed, classify)
    return _diff_positional(path, old, new, classify)


def _diff_keyed_list(path, old_keyed, new_keyed, classify) -> list[FieldDiff]:
    out: list[FieldDiff] = []
    for key, item in old_keyed.items():
        sub = f"{path}[{key[1]}]"
        if key in new_keyed:
            out.extend(_walk(sub, item, new_keyed[key], classify))
        else:
            out.append(FieldDiff(sub, "removed", old=item))
    for key, item in new_keyed.items():
        if key not in old_keyed:
            out.append(FieldDiff(f"{path}[{key[1]}]", "new", new=item))
    return out


def _positional_item(sub: str, i: int, old: list, new: list, classify) -> list[FieldDiff]:
    if i >= len(old):
        return [FieldDiff(sub, "new", new=new[i])]
    if i >= len(new):
        return [FieldDiff(sub, "removed", old=old[i])]
    return _walk(sub, old[i], new[i], classify)


def _diff_positional(path, old: list, new: list, classify) -> list[FieldDiff]:
    out: list[FieldDiff] = []
    for i in range(max(len(old), len(new))):
        out.extend(_positional_item(f"{path}[{i}]", i, old, new, classify))
    return out


def _dict_key(sub: str, key: str, old: dict, new: dict, classify) -> list[FieldDiff]:
    if key not in new:
        return [FieldDiff(sub, "removed", old=old[key])]
    if key not in old:
        return [FieldDiff(sub, "new", new=new[key])]
    return _walk(sub, old[key], new[key], classify)


def _diff_dict(path: str, old: dict, new: dict, classify: ClassifyFn) -> list[FieldDiff]:
    out: list[FieldDiff] = []
    for key in sorted(set(old) | set(new)):
        sub = f"{path}.{key}" if path else key
        out.extend(_dict_key(sub, key, old, new, classify))
    return out


def _walk(path: str, old: Any, new: Any, classify: ClassifyFn) -> list[FieldDiff]:
    if isinstance(old, dict) and isinstance(new, dict):
        return _diff_dict(path, old, new, classify)
    if isinstance(old, list) and isinstance(new, list):
        return _diff_list(path, old, new, classify)
    if _is_scalar(old) and _is_scalar(new):
        return _scalar_diff(path, old, new, classify)
    return [FieldDiff(path, "value_delta", old, new)]


def _find_move(
    removed: FieldDiff, candidates: list[FieldDiff], taken: set[str]
) -> FieldDiff | None:
    for n in candidates:
        same = _leaf(removed.path) == _leaf(n.path) and _move_value(removed.old) == _move_value(
            n.new
        )
        if n.path not in taken and same:
            return n
    return None


def _reclassify_moves(diffs: list[FieldDiff]) -> list[FieldDiff]:
    """Pareia removed+new com mesma chave-folha e mesmo valor monetário ≠ 0 → moved."""
    removed = [d for d in diffs if d.kind == "removed" and _move_value(d.old) not in (None, 0)]
    new = [d for d in diffs if d.kind == "new" and _move_value(d.new) not in (None, 0)]
    moved_paths: set[str] = set()
    moves: list[FieldDiff] = []
    for r in removed:
        target = _find_move(r, new, moved_paths)
        if target is not None:
            moves.append(FieldDiff(target.path, "moved", old=r.old, new=target.new))
            moved_paths.update({r.path, target.path})
    if not moved_paths:
        return diffs
    return [d for d in diffs if d.path not in moved_paths] + moves


def _leaf(path: str) -> str:
    return path.rsplit(".", 1)[-1].split("[", 1)[0]


def _move_value(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return to_cents(value)


def diff_golden(old: dict, new: dict, *, classify: ClassifyFn = is_monetary) -> list[FieldDiff]:
    """Diff puro de dois goldens JSON. Sorted por path; ``moved`` reconciliado."""
    diffs = _reclassify_moves(_walk("", old, new, classify))
    return sorted(diffs, key=lambda d: (d.path, d.kind))


# ──────────────────────────────── manifesto ────────────────────────────────


@dataclass(frozen=True)
class ManifestEntry:
    golden: str
    path: str
    old_cents: int
    new_cents: int


def load_manifest(path: Path) -> list[ManifestEntry]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [
        ManifestEntry(e["golden"], e["path"], int(e["old_cents"]), int(e["new_cents"])) for e in raw
    ]


def check_manifest(
    diffs: list[FieldDiff], manifest: list[ManifestEntry], golden_id: str
) -> tuple[list[FieldDiff], list[ManifestEntry]]:
    """Retorna ``(value_deltas monetários não-cobertos, entradas órfãs/stale)``."""
    relevant = [m for m in manifest if m.golden == golden_id]
    covered: set[int] = set()
    uncovered: list[FieldDiff] = []
    for d in diffs:
        if not d.is_monetary_value_delta():
            continue
        match = _match_entry(d, relevant)
        if match is None:
            uncovered.append(d)
        else:
            covered.add(id(match))
    orphans = [m for m in relevant if id(m) not in covered]
    return uncovered, orphans


def _match_entry(diff: FieldDiff, entries: list[ManifestEntry]) -> ManifestEntry | None:
    for e in entries:
        if (
            e.path == diff.path
            and e.old_cents == to_cents(diff.old)
            and e.new_cents == to_cents(diff.new)
        ):
            return e
    return None


# ─────────────────────────────── PR comment ────────────────────────────────

_KIND_ICON = {
    "value_delta": "🔴",
    "moved": "🔵",
    "new": "🟢",
    "removed": "⚪",
}


def render_markdown(diffs: list[FieldDiff], golden_id: str) -> str:
    changed = [d for d in diffs if d.kind != "unchanged"]
    if not changed:
        return f"### golden_diff `{golden_id}`\n\n✅ Nenhuma mudança.\n"
    lines = [
        f"### golden_diff `{golden_id}`\n",
        "| | campo | de | para | Δ cents |",
        "|---|---|---|---|---|",
    ]
    for d in changed:
        icon = _KIND_ICON.get(d.kind, "•")
        delta = "" if d.delta_cents is None else f"`{d.delta_cents:+d}`"
        lines.append(f"| {icon} | `{d.path}` | `{_fmt(d.old)}` | `{_fmt(d.new)}` | {delta} |")
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    text = json.dumps(value, ensure_ascii=False) if not _is_scalar(value) else str(value)
    return text if len(text) <= 60 else text[:57] + "…"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _report_violations(uncovered: list[FieldDiff], orphans: list[ManifestEntry]) -> None:
    for d in uncovered:
        print(
            f"::error:: value_delta monetário não-justificado: {d.path} "
            f"({d.delta_cents:+d} cents) — adicione ao manifesto de rebaseline",
            file=sys.stderr,
        )
    for m in orphans:
        print(
            f"::error:: entrada de manifesto órfã/stale: {m.golden} {m.path} "
            f"({m.old_cents}→{m.new_cents}) não casa nenhum value_delta atual",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--golden-id", default=None, help="id no manifesto (default: nome do new)")
    args = parser.parse_args(argv)

    golden_id = args.golden_id or args.new.name
    diffs = diff_golden(_load_json(args.old), _load_json(args.new))
    print(render_markdown(diffs, golden_id))

    manifest = load_manifest(args.manifest) if args.manifest else []
    uncovered, orphans = check_manifest(diffs, manifest, golden_id)
    _report_violations(uncovered, orphans)
    return 1 if (uncovered or orphans) else 0


if __name__ == "__main__":
    raise SystemExit(main())
