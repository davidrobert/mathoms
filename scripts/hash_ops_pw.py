#!/usr/bin/env python3
"""Gera um hash bcrypt para o `config/internal_operators.yaml` (ADR-116).

Uso:
    python3 scripts/hash_ops_pw.py

Pede a senha duas vezes (sem echo), imprime o hash. Cole no campo
`hashed_password` do yaml. A senha em claro nunca é persistida nem logada.
"""

from __future__ import annotations

import getpass
import sys

import bcrypt


def main() -> int:
    try:
        pw1 = getpass.getpass("Senha do operador: ")
        pw2 = getpass.getpass("Confirme: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.", file=sys.stderr)
        return 130

    if pw1 != pw2:
        print("As senhas não conferem.", file=sys.stderr)
        return 1
    if len(pw1) < 12:
        print("Senha curta: use pelo menos 12 caracteres.", file=sys.stderr)
        return 2

    hashed = bcrypt.hashpw(pw1.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    print(hashed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
