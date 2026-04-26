#!/usr/bin/env bash
# dev/gen-secrets.sh — gera secrets para .env.prod.local (lane 7A-dev / dev.mathoms.ai).
#
# Imprime no STDOUT três linhas KEY=value prontas para colar/redirecionar:
#   - MATHOMS_FERNET_KEY    (Fernet 32 bytes url-safe base64)
#   - MATHOMS_SECRET_KEY    (64 hex chars para JWT HS256)
#   - POSTGRES_PASSWORD     (32 chars URL-safe sem /+=)
#
# Uso:
#   ./dev/gen-secrets.sh                       # imprime no terminal
#   ./dev/gen-secrets.sh >> .env.prod.local    # acrescenta no env de prod (gitignored)
#
# Idempotente no formato — valores são novos a cada execução (entropia fresca).
#
# Nota: para dev local (.env), continue usando scripts/gen-secrets.sh que tem
# integração com .env.example. Este script é específico para deploy 7A-dev.

set -euo pipefail

# --- 1. FERNET_KEY (cryptography.fernet) ---
python3 -c "from cryptography.fernet import Fernet; print('MATHOMS_FERNET_KEY=' + Fernet.generate_key().decode())"

# --- 2. JWT/SECRET_KEY (64 hex chars = 32 bytes de entropia) ---
echo "MATHOMS_SECRET_KEY=$(openssl rand -hex 32)"

# --- 3. POSTGRES_PASSWORD (32 chars URL-safe sem caracteres problemáticos em URLs) ---
echo "POSTGRES_PASSWORD=$(openssl rand -base64 48 | tr -d '/+=' | head -c 32)"
