#!/usr/bin/env python3
"""Remove metadados embutidos (Info + XMP) de um PDF.

Não redige texto nem imagens — use só **depois** de redação visual manual do corpo
do extrato. Ver `tests/fixtures/e2_real_pdf_anon/README.md`.

Uso:
  python dev/strip_pdf_metadata.py entrada.pdf saida.pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="PDF de entrada")
    parser.add_argument("output", type=Path, help="PDF de saída (pode ser igual com backup prévio)")
    args = parser.parse_args()

    try:
        import pikepdf
    except ImportError:
        print("ERRO: instale pikepdf (dependência do projeto).", file=sys.stderr)
        return 1

    if not args.input.is_file():
        print(f"ERRO: não encontrado: {args.input}", file=sys.stderr)
        return 1

    with pikepdf.Pdf.open(args.input) as pdf:
        if hasattr(pdf, "open_metadata"):
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta.clear()
        if pdf.Root.get("/Metadata") is not None:
            del pdf.Root["/Metadata"]
        pdf.save(args.output)

    print(f"OK: metadados removidos → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
