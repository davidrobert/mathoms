"""Núcleo compartilhado do gate de valor do dogfood ([[ADR-442]]): forma, tier e HMAC."""

# Nestes módulos a regra do CLAUDE.md de "mensagem com o valor ofensor" se INVERTE:
# nenhuma saída, exceção ou repr carrega o número — log de hook é colado em PR e chat.

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DIR_ENV = "MATHOMS_DOGFOOD_DIR"
DENYLIST_NAME = "dogfood_denylist.v1"
KEY_NAME = "dogfood_denylist.key"
MANIFEST_NAME = "dogfood_denylist.manifest.json"
MANIFEST_MAX_AGE_DAYS = 14
TIER_A_MIN_CENTS = 1_000_000
TIER_A_MIN_SIG_DIGITS = 6

_BR = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})(?![\d,])")
_ISO = re.compile(r"(?<![\d.,_])(\d{1,3}(?:[,_]\d{3})+|\d+)\.(\d{1,2})(?![\d._])")
_REAIS_INTEIROS = re.compile(r"(?:R\$|US\$|U\$)\s?(\d{1,3}(?:\.\d{3})+|\d{4,})(?![\d,.])")
_PY_AGRUPADO = re.compile(r"(?<![\d.,_])(\d{1,3}(?:_\d{3})+)(?![\d._])")


class DenylistIndisponivel(RuntimeError):
    """Diretório existe mas a lista, a chave ou o manifesto falta ou está corrompido."""


@dataclass(frozen=True)
class Denylist:
    """Digests HMAC dos valores do dogfood e a chave que os produziu."""

    chave: bytes
    digests: frozenset[str]
    gerada_em: datetime

    def contem(self, cents: int) -> bool:
        return digest(self.chave, cents) in self.digests

    def idade_dias(self, agora: datetime) -> float:
        return (agora - self.gerada_em).total_seconds() / 86_400


def digest(chave: bytes, cents: int) -> str:
    """HMAC-SHA256 do valor absoluto em centavos inteiros."""
    return hmac.new(chave, str(abs(cents)).encode(), hashlib.sha256).hexdigest()


def digitos_significativos(cents: int) -> int:
    return len(str(abs(cents)).rstrip("0"))


def e_tier_a(cents: int) -> bool:
    """≥ R$ 10.000,00 com ≥ 6 dígitos significativos: onde coincidência é desprezível."""
    return abs(cents) >= TIER_A_MIN_CENTS and digitos_significativos(cents) >= TIER_A_MIN_SIG_DIGITS


def centavos_da_linha(linha: str) -> Iterator[int]:
    """Cada forma monetária da linha, normalizada para centavos inteiros."""
    for m in _BR.finditer(linha):
        yield int(m.group(1).replace(".", "")) * 100 + int(m.group(2))
    for m in _ISO.finditer(linha):
        yield int(re.sub(r"[,_]", "", m.group(1))) * 100 + int(m.group(2).ljust(2, "0"))
    for m in _REAIS_INTEIROS.finditer(linha):
        yield int(m.group(1).replace(".", "")) * 100
    for m in _PY_AGRUPADO.finditer(linha):
        yield int(m.group(1).replace("_", "")) * 100


def diretorio_da_denylist() -> Path:
    return Path(os.environ.get(DIR_ENV) or Path.home() / ".config" / "mathoms")


def carregar_denylist(diretorio: Path) -> Denylist:
    """Lê chave, digests e manifesto; qualquer ausência ou corrupção é fail-closed."""
    try:
        chave = bytes.fromhex((diretorio / KEY_NAME).read_text().strip())
        linhas = (diretorio / DENYLIST_NAME).read_text().split()
        manifesto = json.loads((diretorio / MANIFEST_NAME).read_text())
        gerada_em = datetime.fromisoformat(manifesto["generated_at"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DenylistIndisponivel(type(exc).__name__) from None
    if len(chave) < 32 or not linhas or not all(_e_hex64(d) for d in linhas):
        raise DenylistIndisponivel("conteúdo fora do formato")
    return Denylist(chave=chave, digests=frozenset(linhas), gerada_em=_com_fuso(gerada_em))


def _e_hex64(texto: str) -> bool:
    return len(texto) == 64 and all(c in "0123456789abcdef" for c in texto)


def _com_fuso(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)
