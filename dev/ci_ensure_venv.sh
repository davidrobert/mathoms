#!/usr/bin/env bash
# Garante um .venv utilizável e sincronizado com requirements.lock (ADR-254).
#
# Por que existe: o `.venv` é derivado de DOIS inputs — o lock e o interpretador
# — e a key do cache só codificava o lock. `uv venv` grava `.venv/bin/python3`
# como symlink ABSOLUTO; quando o runner troca de patch do Python (3.13.14 →
# 3.13.15), o symlink dangla, `[ -d .venv ]` segue verdadeiro, o step de install
# é pulado por `cache-hit == 'true'` e o job morre em "Failed to inspect Python
# interpreter". Incidentes: PR #658 (2026-06-18) e PR #1379 (2026-08-11).
#
# O predicado é EXECUTAR o interpretador, não testar presença: `-x` pegaria o
# symlink dangling, mas execução também pega tar truncado, stdlib faltando e
# venv de outro glibc.
#
# Uso:  bash dev/ci_ensure_venv.sh [extra-dep ...]
#       bash dev/ci_ensure_venv.sh --self-test

set -euo pipefail

VENV="${VENV_PATH:-.venv}"

venv_usable() {
  "$1/bin/python3" -c "import sys" >/dev/null 2>&1
}

rebuild_if_broken() {
  local venv="$1"
  if venv_usable "$venv"; then
    return 0
  fi
  if [ -e "$venv" ]; then
    echo "::warning::venv cache inutilizável em ${venv} (interpretador não executa) — rebuild"
  fi
  rm -rf "$venv"
  uv venv "$venv"
}

install_deps() {
  local venv="$1"
  shift
  # Ordem lock → extras decide quem VENCE, e hoje vencem os extras — medido:
  # "schemathesis<4" rebaixa starlette 1.3.1 (lock) → 0.52.1 a cada run
  # (ADR-254 §Emenda 2026-08-12). Não inverta sem requirements-test.lock:
  # o lock re-subiria starlette acima do que schemathesis declara suportar.
  # `uv pip install` não faz prune (isso é `uv pip sync`), então rodar o
  # lock sempre não desinstala os extras.
  uv pip install --python "${venv}/bin/python3" --require-hashes -r requirements.lock
  if [ "$#" -gt 0 ]; then
    uv pip install --python "${venv}/bin/python3" "$@"
  fi
}

# Cobre a CLASSE (venv restaurado inutilizável), não só a instância medida.
self_test() {
  local tmp failures=0
  tmp="$(mktemp -d)"
  # Expandido AGORA de propósito: `tmp` é local e estaria unbound no EXIT
  # (com `set -u`, a trap falharia e mascararia o resultado do self-test).
  # shellcheck disable=SC2064
  trap "rm -rf '${tmp}'" EXIT

  for mode in dangling_symlink missing_binary empty_dir; do
    local venv="${tmp}/${mode}"
    uv venv "${venv}" >/dev/null 2>&1
    case "${mode}" in
      dangling_symlink) ln -sf /nonexistent/python3 "${venv}/bin/python3" ;;
      missing_binary) rm -f "${venv}/bin/python3" ;;
      empty_dir) rm -rf "${venv}" && mkdir -p "${venv}/bin" ;;
    esac

    if venv_usable "${venv}"; then
      echo "FALHA [${mode}]: predicado considerou utilizável um venv corrompido"
      failures=$((failures + 1))
      continue
    fi
    rebuild_if_broken "${venv}" >/dev/null 2>&1 || true
    if venv_usable "${venv}"; then
      echo "ok [${mode}]: detectado e reconstruído"
    else
      echo "FALHA [${mode}]: rebuild não produziu venv utilizável"
      failures=$((failures + 1))
    fi
  done

  if [ "${failures}" -ne 0 ]; then
    echo "self-test: ${failures} caso(s) falharam"
    return 1
  fi
  echo "self-test: 3/3 casos detectados e curados"
}

main() {
  if [ "${1:-}" = "--self-test" ]; then
    self_test
    return
  fi
  rebuild_if_broken "${VENV}"
  install_deps "${VENV}" "$@"
}

main "$@"
