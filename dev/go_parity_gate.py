#!/usr/bin/env python3
"""Gate de paridade de artefatos Go↔Python (F2 do PLAN-go-shell, [[ADR-150]] §7): compara os artefatos de dois runs (`pipeline_run_id`) e falha se o executor Go divergir do Python além do piso de ruído medido por um run de controle Python↔Python. Critério, normalização e composição nos comentários abaixo."""

# O shell Go executa cada stage por subprocess do MESMO Python; logo divergência
# de artefato NUNCA vem de cálculo (código idêntico) — só de o shell corromper
# args/env/I/O.
#
# Critério (co-design 2026-07-08, tracks/f2-cutover.md):
# - Tier-1 (determinístico): run com skip_llm (DETERMINISTIC_ORDER) + fixture sem
#   fallback LLM no E2 → payload E0→E5 100% determinístico → paridade value-exact
#   de payload completo (Go↔Py = 0; controle Py↔Py = 0, guarda anti-mascaramento).
# - Tier-2 (full): divergência(Go,Py) ⊆ divergência(Py,Py) por campo — um campo
#   só tem direito de divergir se dois runs Python já divergem nele.
#
# Normalização por IDENTIDADE (run_id, timestamps, prefixo de path), nunca por
# valor — ver _normalize. Lê o payload DECRIPTADO via read_artifact_content
# (nunca a linha crua: com ENCRYPT_PIPELINE_ARTIFACTS o ciphertext tem nonce
# por-escrita → divergência espúria de 100%). Compõe dev/golden_diff.py como lib
# (sem o manifesto de rebaseline: paridade Go não tem escape — delta = bug).
#
# Uso (o operador dispara os runs via `make go-on`; este gate consome run_ids):
#   python dev/go_parity_gate.py --python-run RUN_PY --go-run RUN_GO \
#       [--control-run RUN_PY2] [--tier tier1|tier2] \
#       [--ws-root /path] [--storage-root /path] [--json-out report.json]

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.golden_diff import FieldDiff, diff_golden  # noqa: E402

# ─────────────────────────── normalização (identidade) ───────────────────────────

_IDENTITY_KEYS = frozenset({"run_id", "pipeline_run_id", "workspace_id", "trace_id"})
_TIMESTAMP_KEYS = frozenset({"timestamp", "created_at", "updated_at", "generated_at"})
_RUN_SENTINEL = "<RUN_ID>"
_TS_SENTINEL = "<TS>"
_PATH_SENTINEL = "<WS>"

# artifact_key da E3 carrega o filename lógico determinístico (generate_legacy_filename)
# — NUNCA normalizar por path; só prefixos de path ABSOLUTO real em valores string.


def _is_timestamp_key(key: str) -> bool:
    return key in _TIMESTAMP_KEYS or key.endswith("_at")


def _normalize_str(value: str, path_prefixes: tuple[str, ...]) -> str:
    for prefix in path_prefixes:
        if prefix and value.startswith(prefix):
            return _PATH_SENTINEL + value[len(prefix) :]
    return value


def _normalize(value: Any, path_prefixes: tuple[str, ...]) -> Any:
    """Blanka campos não-determinísticos por IDENTIDADE; nunca reordena listas
    nem toca valores de domínio."""
    if isinstance(value, dict):
        return {k: _normalize_field(k, v, path_prefixes) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(item, path_prefixes) for item in value]
    if isinstance(value, str):
        return _normalize_str(value, path_prefixes)
    return value


def _normalize_field(key: str, value: Any, path_prefixes: tuple[str, ...]) -> Any:
    if key in _IDENTITY_KEYS:
        return _RUN_SENTINEL
    if _is_timestamp_key(key):
        return _TS_SENTINEL
    return _normalize(value, path_prefixes)


# ──────────────────────────────── comparação ────────────────────────────────

ArtifactSet = dict[tuple[str, str], dict]


def compare_payloads(
    old: dict, new: dict, *, path_prefixes: tuple[str, ...] = ()
) -> list[FieldDiff]:
    """Diffs não-`unchanged` entre dois payloads, após normalização por identidade."""
    diffs = diff_golden(_normalize(old, path_prefixes), _normalize(new, path_prefixes))
    return [d for d in diffs if d.kind != "unchanged"]


@dataclass(frozen=True)
class RunComparison:
    """Resultado de parear dois runs por ``(stage, artifact_key)``."""

    diffs_by_artifact: dict[tuple[str, str], list[FieldDiff]] = field(default_factory=dict)
    only_in_old: list[tuple[str, str]] = field(default_factory=list)
    only_in_new: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.diffs_by_artifact and not self.only_in_old and not self.only_in_new

    def divergent_paths(self) -> set[str]:
        """Conjunto de campos (``stage/key::dot.path``) + artefatos ausentes/extras."""
        paths = {
            f"{stage}/{key}::{d.path}"
            for (stage, key), diffs in self.diffs_by_artifact.items()
            for d in diffs
        }
        paths |= {f"{s}/{k}::<MISSING>" for s, k in self.only_in_old}
        paths |= {f"{s}/{k}::<EXTRA>" for s, k in self.only_in_new}
        return paths


def compare_artifact_sets(
    old: ArtifactSet, new: ArtifactSet, *, path_prefixes: tuple[str, ...] = ()
) -> RunComparison:
    """Pareia por ``(stage, artifact_key)``; artefato só de um lado é divergência."""
    old_keys, new_keys = set(old), set(new)
    diffs_by_artifact: dict[tuple[str, str], list[FieldDiff]] = {}
    for artifact_id in sorted(old_keys & new_keys):
        diffs = compare_payloads(old[artifact_id], new[artifact_id], path_prefixes=path_prefixes)
        if diffs:
            diffs_by_artifact[artifact_id] = diffs
    return RunComparison(
        diffs_by_artifact=diffs_by_artifact,
        only_in_old=sorted(old_keys - new_keys),
        only_in_new=sorted(new_keys - old_keys),
    )


def tier1_verdict(main: RunComparison, control: RunComparison | None) -> tuple[bool, str]:
    """Value-exact: Go↔Py limpo E (se houver controle) Py↔Py limpo."""
    if not main.is_clean:
        return False, "Go↔Python divergiu (Tier-1 exige value-exact)"
    if control is not None and not control.is_clean:
        return (
            False,
            "controle Py↔Py não-zero — normalização incompleta ou não-determinismo fora da allowlist; gate não está pronto",
        )
    return True, "value-exact E0→E5"


def tier2_verdict(main: RunComparison, control: RunComparison | None) -> tuple[bool, str]:
    """Diferencial: divergência(Go,Py) ⊆ divergência(Py,Py) por campo."""
    if control is None:
        return False, "Tier-2 exige --control-run (piso de ruído Py↔Py)"
    leaked = main.divergent_paths() - control.divergent_paths()
    if leaked:
        return (
            False,
            f"{len(leaked)} campo(s) divergem Go↔Py fora do piso Py↔Py: {sorted(leaked)[:5]}",
        )
    return True, "divergências Go↔Py ⊆ ruído Py↔Py"


# ────────────────────────────────── report ──────────────────────────────────


def render_report(cmp: RunComparison, *, label: str) -> str:
    if cmp.is_clean:
        return f"### paridade `{label}`\n\n✅ 0 divergências.\n"
    lines = [f"### paridade `{label}`\n"]
    for stage, key in cmp.only_in_old:
        lines.append(f"- ⚪ artefato só no lado A: `{stage}/{key}`")
    for stage, key in cmp.only_in_new:
        lines.append(f"- 🟢 artefato só no lado B: `{stage}/{key}`")
    for (stage, key), diffs in sorted(cmp.diffs_by_artifact.items()):
        lines.append(f"- 🔴 `{stage}/{key}` — {len(diffs)} campo(s):")
        lines.extend(f"    - `{d.path}`: `{d.old!r}` → `{d.new!r}`" for d in diffs[:20])
    return "\n".join(lines) + "\n"


# ─────────────────────────── coleta (DB, lazy import) ───────────────────────────


def collect_run_artifacts(pipeline_run_id: str) -> ArtifactSet:
    """Lê os artefatos decriptados de uma run, keyed por ``(stage_descritivo, key)``."""
    # Import lazy do backend: read_artifact_content puxa o vault Fernet no load do
    # módulo — importar cedo quebraria --help sem MATHOMS_FERNET_KEY.
    from backend.app.core.database import SyncSessionLocal
    from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository
    from backend.app.services.security.crypto import read_artifact_content
    from pipeline.stage_spec import resolve_stage_name

    out: ArtifactSet = {}
    with SyncSessionLocal() as db:
        for art in PipelineArtifactRepository(db).list_for_run(pipeline_run_id):
            payload = read_artifact_content(art.content_json)
            out[(resolve_stage_name(art.stage), art.artifact_key)] = payload
    return out


# ──────────────────────────────────── CLI ────────────────────────────────────

_VERDICT = {"tier1": tier1_verdict, "tier2": tier2_verdict}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Gate de paridade de artefatos Go↔Python (F2 GO_SHELL)."
    )
    p.add_argument("--python-run", required=True, help="pipeline_run_id do executor Python")
    p.add_argument("--go-run", required=True, help="pipeline_run_id do executor Go")
    p.add_argument("--control-run", default=None, help="2º run Python (piso de ruído Py↔Py)")
    p.add_argument("--tier", choices=("tier1", "tier2"), default="tier1")
    p.add_argument("--ws-root", default=None, help="prefixo de path absoluto do workspace → <WS>")
    p.add_argument(
        "--storage-root", default=None, help="prefixo de path absoluto do storage → <WS>"
    )
    p.add_argument("--json-out", default=None, help="grava o resultado estruturado em JSON")
    return p.parse_args(argv)


def _path_prefixes(args: argparse.Namespace) -> tuple[str, ...]:
    return tuple(p for p in (args.ws_root, args.storage_root) if p)


def _write_json(path: str, main: RunComparison, ok: bool, reason: str) -> None:
    data = {
        "ok": ok,
        "reason": reason,
        "divergent_paths": sorted(main.divergent_paths()),
        "only_in_python": [f"{s}/{k}" for s, k in main.only_in_old],
        "only_in_go": [f"{s}/{k}" for s, k in main.only_in_new],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _run_comparisons(
    args: argparse.Namespace, prefixes: tuple[str, ...]
) -> tuple[RunComparison, RunComparison | None]:
    """Coleta os runs, compara Go↔Py (+ controle Py↔Py se pedido) e imprime os reports."""
    python_set = collect_run_artifacts(args.python_run)
    main_cmp = compare_artifact_sets(
        python_set, collect_run_artifacts(args.go_run), path_prefixes=prefixes
    )
    print(render_report(main_cmp, label="Go↔Python"))
    if not args.control_run:
        return main_cmp, None
    control_set = collect_run_artifacts(args.control_run)
    control_cmp = compare_artifact_sets(python_set, control_set, path_prefixes=prefixes)
    print(render_report(control_cmp, label="controle Python↔Python"))
    return main_cmp, control_cmp


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    prefixes = _path_prefixes(args)
    main_cmp, control_cmp = _run_comparisons(args, prefixes)

    ok, reason = _VERDICT[args.tier](main_cmp, control_cmp)
    if args.json_out:
        _write_json(args.json_out, main_cmp, ok, reason)
    if not ok:
        print(f"::error:: {args.tier} FALHOU — {reason}", file=sys.stderr)
    else:
        print(f"✓ {args.tier} PASSOU — {reason}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
