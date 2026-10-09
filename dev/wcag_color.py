"""Aritmética de cor dos gates de contraste: luminância WCAG, composição e oklch.

Separado de `check_tint_contrast.py` quando a paleta oklch do shadcn/ui entrou
na medição (ADR-372 §Emenda 2026-10-09): antes ela ficava fora por nome porque
não havia hex a medir.
"""

from __future__ import annotations

import math
import re

# `--x: oklch(L C H)` opaco. A forma com alpha (`oklch(1 0 0 / 10%)`) não casa
# de propósito: cor translúcida não tem hex próprio, e utility que apontar para
# ela fica sem hex e derruba o gate em vez de ser medida errada.
OKLCH_DECL_RE = re.compile(r"--([\w-]+):\s*oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)(?:deg)?\s*\)")


def channels(hex_value: str) -> tuple[int, int, int]:
    h = hex_value.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def relative_luminance(hex_value: str) -> float:
    def lin(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = channels(hex_value)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = relative_luminance(fg), relative_luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def composite(color: str, over: str, pct: int) -> str:
    f, b = channels(color), channels(over)
    a = pct / 100
    return "#" + "".join(f"{round(v * a + b[i] * (1 - a)):02X}" for i, v in enumerate(f))


def _linear_srgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """OKLCH → sRGB linear (matrizes de Björn Ottosson, as da CSS Color 4)."""
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )


def _encode(linear: float) -> int:
    v = min(max(linear, 0.0), 1.0)
    v = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return round(v * 255)


# Fora do gamut sRGB o canal é recortado, não mapeado por croma: é o que dá o
# hex que o Tailwind publica para a própria paleta (`red-600` → #E7000B).
def oklch_hex(lightness: str, chroma: str, hue: str) -> str:
    """`oklch(L C H)` como hex sRGB; `L` aceita `0.577` ou `57.7%`."""
    lum = float(lightness[:-1]) / 100 if lightness.endswith("%") else float(lightness)
    return "#" + "".join(f"{_encode(v):02X}" for v in _linear_srgb(lum, float(chroma), float(hue)))
