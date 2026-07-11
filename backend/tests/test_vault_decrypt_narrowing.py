"""Regressão QUAL-01 (A36.l5): VaultService.decrypt só engole InvalidToken.

`except (InvalidToken, Exception)` mascarava bug real (tipo errado/encoding)
atrás de um `None` silencioso. Narrow para `InvalidToken`; `None`-in→`None`-out
preservado (callers passam Optional). Qualquer outra exceção propaga.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from backend.app.services.security.vault import VaultService


def _vault() -> VaultService:
    return VaultService(key=Fernet.generate_key().decode())


def test_round_trip() -> None:
    v = _vault()
    assert v.decrypt(v.encrypt("segredo")) == "segredo"


def test_token_de_outra_chave_retorna_none() -> None:
    """Miss de rotação (InvalidToken) → None, comportamento esperado."""
    alheio = _vault().encrypt("x")
    assert _vault().decrypt(alheio) is None


def test_lixo_base64_retorna_none() -> None:
    """Base64/token malformado → InvalidToken → None (coberto pelo Fernet)."""
    assert _vault().decrypt("not-a-fernet-token") is None


def test_none_in_none_out() -> None:
    v = _vault()
    assert v.decrypt(None) is None
    assert v.needs_rotation(None) is False


def test_erro_nao_invalidtoken_propaga() -> None:
    """Narrowing: tipo errado levanta em vez de virar None silencioso (era engolido)."""
    with pytest.raises(AttributeError):
        _vault().decrypt(123)  # type: ignore[arg-type]


def test_needs_rotation_token_primario_false() -> None:
    v = _vault()
    assert v.needs_rotation(v.encrypt("x")) is False
