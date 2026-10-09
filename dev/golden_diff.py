#!/usr/bin/env python3
"""Diff valor-a-valor de dois goldens JSON — rede de regressão number-level (A23.l2). Classifica cada campo entre ``unchanged | moved | value_delta | new | removed``; delta monetário em cents int (ADR-090, nunca float); puro/stateless (ADR-111). Monetário-por-default: campo numérico é monetário salvo allowlist não-monetária — campo novo falha alto, nunca passa silencioso. Todo ``value_delta`` monetário exige entrada no manifesto de rebaseline (exit≠0 se não-justificado ou manifesto stale). Uso: ``python dev/golden_diff.py OLD NEW [--manifest M.yaml] [--golden-id ID]``."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

# Irmão carregado por caminho: o módulo é importado DENTRO do pacote `dev` e também
# FORA dele (`spec_from_file_location`, no snapshot do view-model e em dois testes).
_DEV_DIR = str(Path(__file__).resolve().parent)
if _DEV_DIR not in sys.path:
    sys.path.append(_DEV_DIR)

from golden_diff_allowlist import (  # noqa: E402
    MARCADORES_MONETARIOS,
    NON_MONETARY_EXACT,
    NON_MONETARY_NAMESPACES,
    NON_MONETARY_PREFIXES,
    NON_MONETARY_SUFFIXES,
    NON_MONETARY_UNIT_TOKENS,
)

ClassifyFn = Callable[[str], bool]


def _bloco_nao_monetario(path: str) -> bool:
    leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
    if leaf.endswith(MARCADORES_MONETARIOS):
        return False
    return re.sub(r"\[[^\]]*\]", "", path).startswith(NON_MONETARY_NAMESPACES)


def is_monetary(path: str) -> bool:
    """``True`` se o campo (dot-path) é monetário — monetário-por-default."""
    leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
    if _bloco_nao_monetario(path):
        return False
    if leaf in NON_MONETARY_EXACT:
        return False
    if leaf.endswith(NON_MONETARY_SUFFIXES):
        return False
    if leaf.startswith(NON_MONETARY_PREFIXES):
        return False
    if set(leaf.split("_")) & NON_MONETARY_UNIT_TOKENS:
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
    # Campo monetário que passou de número a `null` ou de `null` a número. Não há
    # `delta_cents` a calcular, e era exatamente por isso que a supressão de um balde
    # rebaselinava sem waiver ([[ADR-439]] · co-design `data-engineer`).
    anulacao: bool = False

    def is_monetary_value_delta(self) -> bool:
        return self.kind == "value_delta" and self.delta_cents is not None

    def exige_manifesto(self) -> bool:
        """Delta monetário OU anulação monetária — os dois movem o número publicado."""
        return self.is_monetary_value_delta() or self.anulacao


_NATURAL_KEYS = (
    "categoria",
    "fonte",
    "natureza",
    "property_id",
    "codigo_rfb",
    "code",
    "id",
    "nome",
    "key",
)


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
    if classify(path) and _numero_contra_nulo(old, new):
        return [FieldDiff(path, "value_delta", old, new, anulacao=True)]
    return [FieldDiff(path, "value_delta", old, new)]


def _numero_contra_nulo(old: Any, new: Any) -> bool:
    """Exatamente um lado é `null` e o outro é número (bool não é número aqui)."""
    lados = [v for v in (old, new) if v is not None]
    return len(lados) == 1 and isinstance(lados[0], (int, float)) and not isinstance(lados[0], bool)


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

_ADR_RE = r"^ADR-\d+$"
_REF_RE = r"^\S+:\d+$"


@dataclass(frozen=True)
class ManifestEntry:
    golden: str
    path: str
    old_cents: int | None  # `None` = o lado era `null` (anulação, [[ADR-439]])
    new_cents: int | None
    adr: str  # justificativa obrigatória (F2-DB6); fora da chave de match
    rationale: str
    ref: str  # file:line da mudança de produção (G-c)


def _validated_entry(e: dict) -> ManifestEntry:
    import re

    required = ("golden", "path", "old_cents", "new_cents", "adr", "rationale", "ref")
    missing = [
        k for k in required if k not in e or (isinstance(e.get(k), str) and not e[k].strip())
    ]
    if missing:
        raise ValueError(f"entrada de manifesto sem campo(s) obrigatório(s) {missing}: {e!r}")
    if not re.match(_ADR_RE, str(e["adr"])):
        raise ValueError(
            f"manifesto: adr deve casar {_ADR_RE!r}, got {e['adr']!r} em {e['path']!r}"
        )
    if not re.match(_REF_RE, str(e["ref"])):
        raise ValueError(
            f"manifesto: ref deve ser file:line ({_REF_RE!r}), got {e['ref']!r} em {e['path']!r}"
        )
    return ManifestEntry(
        e["golden"],
        e["path"],
        _cents_declarado(e["old_cents"]),
        _cents_declarado(e["new_cents"]),
        str(e["adr"]),
        str(e["rationale"]),
        str(e["ref"]),
    )


def _cents_declarado(valor: Any) -> int | None:
    return None if valor is None else int(valor)


def _cents_ou_nulo(valor: Any) -> int | None:
    return None if valor is None else to_cents(valor)


def load_manifest(path: Path) -> list[ManifestEntry]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [_validated_entry(e) for e in raw]


def check_manifest(
    diffs: list[FieldDiff], manifest: list[ManifestEntry], golden_id: str
) -> tuple[list[FieldDiff], list[ManifestEntry]]:
    """Retorna ``(value_deltas monetários não-cobertos, entradas órfãs/stale)``."""
    relevant = [m for m in manifest if m.golden == golden_id]
    covered: set[int] = set()
    uncovered: list[FieldDiff] = []
    for d in diffs:
        if not d.exige_manifesto():
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
            and e.old_cents == _cents_ou_nulo(diff.old)
            and e.new_cents == _cents_ou_nulo(diff.new)
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


MANIFESTO_PADRAO = "tests/fixtures/pipeline_golden/rebaseline_manifest.yaml"


# Anulação não tem `delta_cents`: formatá-lo com `:+d` derrubava o gate em `TypeError`
# — falha de leitura no lugar da reprovação que ele existe para dar (A40.l113).
def _descrever_delta(d: FieldDiff) -> str:
    if d.anulacao:
        lados = ("null" if v is None else _fmt(v) for v in (d.old, d.new))
        return " → ".join(lados) + ", anulação"
    return f"{d.delta_cents:+d} cents"


def _report_violations(uncovered: list[FieldDiff], orphans: list[ManifestEntry]) -> None:
    for d in uncovered:
        print(
            f"::error:: value_delta monetário não-justificado: {d.path} "
            f"({_descrever_delta(d)}) — adicione ao manifesto de rebaseline",
            file=sys.stderr,
        )
    # A mensagem nomeia o REMÉDIO porque quem lê esta falha quase nunca é quem criou a
    # entrada: o waiver é do PR do rebaseline e morre no merge dele, mas a falha cai no
    # PRÓXIMO PR a tocar aquele golden — que não tem contexto nenhum. Aconteceu duas
    # vezes em 2026-08-31 (A40.l95: #1911 e o fecho), e nas duas o diagnóstico custou mais
    # que o conserto.
    for m in orphans:
        print(
            f"::error:: entrada de manifesto órfã/stale: {m.golden} {m.path} "
            f"({m.old_cents}→{m.new_cents}) não casa nenhum value_delta atual. "
            "Waiver de rebaseline é TRANSITÓRIO: se o rebaseline dela já mergeou, "
            "esvazie o manifesto (`[]`) — não é dívida deste PR. Ver o cabeçalho de "
            f"{Path(MANIFESTO_PADRAO).name}.",
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
