#!/usr/bin/env bash
# scripts/gen-secrets.sh — gera FIN_FERNET_KEY e FIN_SECRET_KEY para desenvolvimento local.
#
# Requer: Python 3.11+ com pacote `cryptography` (ex.: pip install -e backend ou backend/requirements.txt).
#
# Uso:
#   ./scripts/gen-secrets.sh              Imprime duas linhas (colar no .env)
#   ./scripts/gen-secrets.sh --init-env   cp .env.example → .env e preenche Fernet + JWT (falha se .env existir)
#   ./scripts/gen-secrets.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

print_generated_lines() {
  python3 <<'PY'
try:
    from cryptography.fernet import Fernet
except ImportError:
    raise SystemExit(
        "Erro: pacote 'cryptography' não encontrado. "
        "Ative o venv e instale dependências do backend: pip install -r backend/requirements.txt"
    )
import secrets

print("FIN_FERNET_KEY=" + Fernet.generate_key().decode())
print("FIN_SECRET_KEY=" + secrets.token_urlsafe(48))
PY
}

init_env() {
  if [[ -f .env ]]; then
    echo "Erro: .env já existe. Remova ou renomeie antes de usar --init-env." >&2
    exit 1
  fi
  if [[ ! -f .env.example ]]; then
    echo "Erro: .env.example não encontrado na raiz do repositório." >&2
    exit 1
  fi

  tmpfile="$(mktemp)"
  print_generated_lines >"$tmpfile"

  GEN_LINE_FERNET=""
  GEN_LINE_JWT=""
  while IFS= read -r line; do
    if [[ "$line" == FIN_FERNET_KEY=* ]]; then
      GEN_LINE_FERNET="$line"
    elif [[ "$line" == FIN_SECRET_KEY=* ]]; then
      GEN_LINE_JWT="$line"
    fi
  done <"$tmpfile"
  rm -f "$tmpfile"

  export GEN_LINE_FERNET GEN_LINE_JWT
  python3 <<'PY'
import os
from pathlib import Path

root = Path.cwd()
fernet = os.environ["GEN_LINE_FERNET"]
jwt = os.environ["GEN_LINE_JWT"]
text = (root / ".env.example").read_text(encoding="utf-8")
out_lines = []
for line in text.splitlines():
    if line.startswith("FIN_FERNET_KEY="):
        out_lines.append(fernet)
    elif line.startswith("FIN_SECRET_KEY="):
        out_lines.append(jwt)
    else:
        out_lines.append(line)
(root / ".env").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
print("Criado .env a partir de .env.example com FIN_FERNET_KEY e FIN_SECRET_KEY gerados.")
PY
}

case "${1:-}" in
  --init-env)
    init_env
    ;;
  -h|--help|"")
    if [[ "${1:-}" == "" ]]; then
      echo "# Cole no .env ou execute: $0 --init-env"
      print_generated_lines
    else
      cat <<EOF
Uso: $(basename "$0") [--init-env|--help]

Sem argumentos: imprime FIN_FERNET_KEY e FIN_SECRET_KEY novos.

  --init-env   Copia .env.example para .env e injeta chaves geradas (não sobrescreve .env existente).

Requer Python com cryptography instalado (dependência do backend).
EOF
    fi
    ;;
  *)
    echo "Opção desconhecida: $1 (use --help)" >&2
    exit 1
    ;;
esac
