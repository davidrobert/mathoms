#!/usr/bin/env python3
"""dev/migrate_milhas_to_workspace_storage.py — A7.6 ADR-147 migrator one-shot.

Copia ``docs/methodology/milhas.md`` (ou ``_archive/methodology/milhas.md`` se
já arquivado) para ``<workspace>/notes/milhas.md`` (gitignored, workspace-scoped).

**Idempotente:** skip silencioso se path destino já existe (não sobrescreve;
operador valida visualmente antes de re-rodar com ``--force``).

CLI:

    python dev/migrate_milhas_to_workspace_storage.py --workspace-id <id>
    python dev/migrate_milhas_to_workspace_storage.py --workspace-id <id> --force
    python dev/migrate_milhas_to_workspace_storage.py --workspace-root /path/to/ws

A7.5 (cleanup) removerá o bridge de leitura legado em scripts/analyze_finances.py.
A8.1 (MileageProgram DB aggregate) torna esse arquivo obsoleto — migrar
para DB rows e descontinuar markdown workspace-scoped.

Saída: 0 = sucesso ou skip silencioso (idempotência); 1 = erro.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_workspace_root(args: argparse.Namespace) -> Path:
    """Resolve workspace root from --workspace-id ou --workspace-root."""
    if args.workspace_root:
        return Path(args.workspace_root).resolve()
    if args.workspace_id:
        return _REPO_ROOT / "storage" / args.workspace_id
    raise SystemExit("erro: forneça --workspace-id OU --workspace-root")


def _resolve_source(args: argparse.Namespace) -> Path:
    """Resolve fonte legada (docs/methodology/milhas.md prioritário)."""
    if args.source:
        return Path(args.source).resolve()
    candidates = [
        _REPO_ROOT / "docs" / "methodology" / "milhas.md",
        _REPO_ROOT / "_archive" / "methodology" / "milhas.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "erro: fonte legada não encontrada (tentado docs/methodology/milhas.md "
        "e _archive/methodology/milhas.md). Use --source para apontar manualmente."
    )


def migrate(source: Path, workspace_root: Path, force: bool = False) -> int:
    """Copia ``source`` → ``<workspace_root>/notes/milhas.md``. Idempotente."""
    if not source.exists():
        print(f"erro: fonte {source} não existe", file=sys.stderr)
        return 1

    dest_dir = workspace_root / "notes"
    dest = dest_dir / "milhas.md"

    if dest.exists() and not force:
        print(f"skip — destino já existe: {dest} (use --force para sobrescrever)")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    print(f"✓ milhas migrado: {source} → {dest}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", help="ID do workspace.")
    parser.add_argument("--workspace-root", help="Path absoluto do workspace.")
    parser.add_argument("--source", help="Path do arquivo fonte legado.")
    parser.add_argument("--force", action="store_true", help="Sobrescreve destino.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        ws_root = _resolve_workspace_root(args)
        source = _resolve_source(args)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return migrate(source, ws_root, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
