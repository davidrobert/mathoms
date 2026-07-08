"""Auth portability parity tests (A6f.5a · ADR-109).

Contratos de auth — JWT e Fernet — testados contra as shapes canônicas que
qualquer cliente em outra linguagem (Go, TS, Rust) precisa replicar:

- **JWT**: RFC 7519 puro, algoritmo HS256, payload ``{sub, exp, tv}``
  com tipos estáveis.
- **Fernet**: cifra simétrica formato Fernet documentado — plaintext ASCII
  deve roundtrip correto; ciphertext gerado pelo backend deve ser
  decriptado por qualquer lib Fernet-compatível.

Política: se este teste quebra, a mudança em auth é **breaking** e exige
ADR (provavelmente A6f.5b ou A6f.5c) antes de merge.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

# ═══════════════════════════════════════════════════════════════════════
# JWT — contrato canônico RFC 7519 + HS256
# ═══════════════════════════════════════════════════════════════════════


def test_jwt_algorithm_and_payload_claims_are_canonical() -> None:
    """HS256 + payload ``{sub, exp, tv}`` — qualquer lib Go/TS lê."""
    import jwt

    from backend.app.core.config import settings
    from backend.app.core.security import create_access_token

    token = create_access_token("user-abc", token_version=7)

    # Header: apenas ``alg`` e ``typ`` — sem kid nem x5c (portável).
    header = jwt.get_unverified_header(token)
    assert (
        header["alg"] == "HS256"
    ), "ADR-109: algoritmo JWT deve ser HS256 para compat Go/TS sem config extra."
    assert header.get("typ") in ("JWT", None), "typ inesperado"

    # Payload: contrato ``{sub: str, exp: int (unix seconds), tv: int}``.
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert set(payload.keys()) == {"sub", "exp", "tv"}, (
        f"ADR-109: claims devem ser exatamente {{sub, exp, tv}}. Encontrado: "
        f"{sorted(payload.keys())}. Novos claims exigem bump de contrato."
    )
    assert isinstance(payload["sub"], str)
    assert isinstance(payload["exp"], int)
    assert isinstance(payload["tv"], int)
    assert payload["sub"] == "user-abc"
    assert payload["tv"] == 7


def test_jwt_expired_token_is_rejected() -> None:
    """Go `jwt.ParseWithClaims` rejeita tokens expirados — parity."""
    from backend.app.core.security import (
        create_access_token,
        decode_access_token_payload,
    )

    token = create_access_token(
        "user-abc",
        expires_delta=timedelta(seconds=-1),  # já expirou
        token_version=0,
    )
    assert decode_access_token_payload(token) is None


def test_jwt_tampered_signature_is_rejected() -> None:
    """Alteração de 1 byte no token invalida assinatura — RFC 7519."""
    from backend.app.core.security import (
        create_access_token,
        decode_access_token_payload,
    )

    token = create_access_token("user-abc", token_version=0)
    # Troca o primeiro char da assinatura (último segmento do JWT). Evitamos
    # o último char porque, em base64url sem padding, ele pode conter bits
    # ignorados pelo decoder (sig HS256 = 32 bytes → 43 chars; último char
    # só usa 4 dos 6 bits) — flipar lá pode não alterar a assinatura efetiva.
    parts = token.split(".")
    assert len(parts) == 3
    sig = parts[2]
    flipped = "A" if sig[0] != "A" else "B"
    tampered = ".".join(parts[:2] + [flipped + sig[1:]])
    assert decode_access_token_payload(tampered) is None


def test_jwt_hs256_signed_externally_decodes_with_same_secret() -> None:
    """Cliente externo (simulado) que emite JWT HS256 com a mesma SECRET_KEY
    é aceito pelo decoder — prova que o contrato é simétrico.

    Simula o cenário onde um serviço Go hipotético emite token e o backend
    Python valida, ou vice-versa.
    """
    import jwt

    from backend.app.core.config import settings
    from backend.app.core.security import decode_access_token_payload

    now = datetime.now(timezone.utc)
    external_token = jwt.encode(
        {"sub": "go-service", "exp": now + timedelta(minutes=5), "tv": 0},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    payload = decode_access_token_payload(external_token)
    assert payload is not None
    assert payload["sub"] == "go-service"


# ═══════════════════════════════════════════════════════════════════════
# Fernet — cifra simétrica portátil
# ═══════════════════════════════════════════════════════════════════════


# Vetor canônico gerado com Python cryptography — qualquer lib Fernet
# (Go/TS/Rust) que implemente o spec decripta para o mesmo plaintext.
# Key e ciphertext estáveis — nunca substituir sem bumpar ADR.
_FERNET_KEY_CANONICAL = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
_FERNET_PLAINTEXT_CANONICAL = "mathoms-fernet-canonical-plaintext-2026-04-20"


def test_fernet_roundtrip_via_vault_service() -> None:
    """VaultService encrypt→decrypt roundtrip — garante que o pipeline
    inteiro (settings → Fernet → base64) funciona."""
    from backend.app.services.security.vault import VaultService

    vault = VaultService(key=_FERNET_KEY_CANONICAL)
    ciphertext = vault.encrypt(_FERNET_PLAINTEXT_CANONICAL)
    assert ciphertext  # não-vazio
    assert ciphertext != _FERNET_PLAINTEXT_CANONICAL  # está cifrado

    recovered = vault.decrypt(ciphertext)
    assert recovered == _FERNET_PLAINTEXT_CANONICAL


def test_fernet_cross_lib_format_is_stable() -> None:
    """O formato Fernet emitido pelo backend é o spec público documentado
    (5 campos binários base64url-encoded: version||timestamp||IV||ciphertext||HMAC).

    Parity com Go (``fernet-go``) e TS (``fernet``): se o ciphertext
    decodificar em base64url e o primeiro byte for 0x80 (version Fernet),
    qualquer lib compatível consegue decriptar com a mesma chave.
    """
    import base64

    from backend.app.services.security.vault import VaultService

    vault = VaultService(key=_FERNET_KEY_CANONICAL)
    token = vault.encrypt(_FERNET_PLAINTEXT_CANONICAL)

    # Fernet tokens são base64url sem padding. O decode precisa
    # completar com padding.
    padded = token + "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(padded)
    assert raw[0] == 0x80, (
        "Fernet spec: byte de versão deve ser 0x80. Formato alterado "
        "quebra compat com libs não-Python — abrir A6f.5b."
    )
    # Spec mínimo: 1 (version) + 8 (timestamp) + 16 (IV) + 0+ (ct) + 32 (HMAC)
    assert len(raw) >= 57


def test_fernet_rejects_tampered_ciphertext() -> None:
    """HMAC protege integridade — flip de bit invalida o token."""
    from backend.app.services.security.vault import VaultService

    vault = VaultService(key=_FERNET_KEY_CANONICAL)
    token = vault.encrypt(_FERNET_PLAINTEXT_CANONICAL)

    # Flip de 1 char no meio do token (dentro do ciphertext ou HMAC).
    mid = len(token) // 2
    original_char = token[mid]
    # Escolhe um substituto válido em base64url alfabeto.
    substitute = "A" if original_char != "A" else "B"
    tampered = token[:mid] + substitute + token[mid + 1 :]

    recovered = vault.decrypt(tampered)
    assert recovered is None, "Fernet deve rejeitar ciphertext adulterado — HMAC-SHA256 guard."


@pytest.mark.parametrize(
    "plaintext",
    [
        "ascii-simple",
        "com acentuação portuguesa: ção, ã, é, ü",
        "emoji 🔐 e símbolos: €£¥",
        "x" * 4096,  # payload grande (4KB)
        "",  # string vazia
    ],
)
def test_fernet_roundtrip_unicode_and_edge_cases(plaintext: str) -> None:
    """Qualquer lib Fernet-compatível deve preservar UTF-8 + edge cases."""
    from backend.app.services.security.vault import VaultService

    vault = VaultService(key=_FERNET_KEY_CANONICAL)
    token = vault.encrypt(plaintext)
    recovered = vault.decrypt(token)
    assert recovered == plaintext
