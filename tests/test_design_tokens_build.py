#!/usr/bin/env python3
"""Tests for design-tokens/build.py — ADR-076.

Validates that the tokens.json → CSS generation is deterministic, complete,
and produces syntactically valid CSS for both the Next.js site and the
frontend-ops console.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_BUILD_PY = ROOT / "design-tokens" / "build.py"

# The folder has a hyphen, so load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location("design_tokens_build", _BUILD_PY)
assert _spec and _spec.loader
design_tokens_build = importlib.util.module_from_spec(_spec)
sys.modules["design_tokens_build"] = design_tokens_build
_spec.loader.exec_module(design_tokens_build)

FRONTEND_OUTPUT = design_tokens_build.FRONTEND_OUTPUT
FRONTEND_OPS_OUTPUT = design_tokens_build.FRONTEND_OPS_OUTPUT
TOKENS_PATH = design_tokens_build.TOKENS_PATH
build = design_tokens_build.build
load_tokens = design_tokens_build.load_tokens
render_css = design_tokens_build.render_css


@pytest.fixture(scope="module")
def tokens() -> dict:
    return load_tokens()


class TestTokensJson:
    def test_tokens_file_exists(self):
        assert TOKENS_PATH.exists()

    def test_tokens_valid_json(self, tokens):
        assert isinstance(tokens, dict)

    def test_required_top_level_keys(self, tokens):
        required = {"meta", "typography", "spacing", "radius", "shadow", "modes", "card_variants"}
        assert required.issubset(tokens.keys())

    def test_both_modes_present(self, tokens):
        assert "light" in tokens["modes"]
        assert "dark" in tokens["modes"]

    def test_modes_have_parity(self, tokens):
        """Light and dark must define the same semantic keys."""
        light = tokens["modes"]["light"]
        dark = tokens["modes"]["dark"]
        for category in ("brand", "surface", "semantic", "sidebar"):
            assert set(light[category].keys()) == set(
                dark[category].keys()
            ), f"mode parity broken in category: {category}"

    def test_chart_palette_has_12_colors(self, tokens):
        assert len(tokens["modes"]["light"]["chart"]) == 12
        assert len(tokens["modes"]["dark"]["chart"]) == 12

    def test_all_hex_colors_valid(self, tokens):
        """Every color value must be a valid hex or start with var()/color-mix."""
        import re

        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for mode_name, mode in tokens["modes"].items():
            for cat in ("brand", "surface", "semantic", "sidebar"):
                for k, v in mode[cat].items():
                    assert hex_re.match(v), f"invalid hex in {mode_name}.{cat}.{k}: {v}"
            for v in mode["chart"]:
                assert hex_re.match(v), f"invalid hex in chart: {v}"

    def test_brand_primary_is_navy(self, tokens):
        """DNA check: light-mode primary must be the navy institucional."""
        assert tokens["modes"]["light"]["brand"]["primary"] == "#1A3A5C"

    def test_brand_accent_is_green(self, tokens):
        assert tokens["modes"]["light"]["brand"]["accent"] == "#15803D"


class TestBuild:
    def test_build_produces_two_outputs(self):
        frontend_css, ops_css = build()
        assert frontend_css
        assert ops_css

    def test_frontend_has_theme_inline(self):
        frontend_css, _ = build()
        assert (
            "@theme inline" in frontend_css
        ), "frontend CSS must include Tailwind v4 @theme inline block"

    def test_ops_has_no_theme_inline(self):
        _, ops_css = build()
        assert (
            "@theme inline" not in ops_css
        ), "frontend-ops CSS must NOT include Tailwind-specific block"

    def test_both_outputs_have_light_and_dark(self):
        frontend_css, ops_css = build()
        for name, css in [("frontend", frontend_css), ("ops", ops_css)]:
            assert ":root {" in css, f"{name} missing :root"
            assert ".dark," in css, f"{name} missing .dark block"
            assert "[data-theme='dark']" in css, f"{name} missing [data-theme='dark'] block"

    def test_outputs_reference_no_hardcoded_colors_outside_root(self):
        """Card variants and theme block should use var(), not hex literals."""
        frontend_css, ops_css = build()
        for css in (frontend_css, ops_css):
            idx = css.index("Card variants")
            rest = css[idx:]
            import re

            hex_matches = re.findall(r"#[0-9A-Fa-f]{6}", rest)
            assert not hex_matches, f"hex literal found in utility section: {hex_matches}"

    def test_frontend_does_not_emit_font_families(self):
        """Frontend delega --font-display/body/mono para next/font/google.

        Emitir literais aqui quebraria as otimizações do Next (subsetting,
        self-hosting, font-display:swap). Só --font-size-* e --font-weight-*
        podem vir daqui.
        """
        frontend_css, _ = build()
        # Extrai apenas o bloco :root (antes do .dark)
        root_block = frontend_css.split(".dark,")[0]
        for family in ("display", "body", "mono"):
            forbidden = f"--font-{family}: '"
            assert forbidden not in root_block, (
                f"frontend CSS não deve definir --font-{family} como literal — "
                f"essa var vem do next/font em runtime"
            )

    def test_ops_emits_font_families(self):
        """frontend-ops precisa das famílias (não tem next/font)."""
        _, ops_css = build()
        root_block = ops_css.split(".dark,")[0]
        assert "--font-display: 'Plus Jakarta Sans'" in root_block
        assert "--font-body: 'Inter'" in root_block
        assert "--font-mono: 'JetBrains Mono'" in root_block

    def test_card_variants_all_emitted(self, tokens):
        frontend_css, _ = build()
        for variant in tokens["card_variants"]:
            assert (
                f".card-variant-{variant}" in frontend_css
            ), f"missing utility for variant: {variant}"

    def test_render_is_deterministic(self):
        """Same input → byte-identical output."""
        a, _ = build()
        b, _ = build()
        assert a == b


class TestGeneratedFilesOnDisk:
    def test_frontend_file_exists_and_in_sync(self):
        assert FRONTEND_OUTPUT.exists(), (
            f"{FRONTEND_OUTPUT.relative_to(ROOT)} not generated — run "
            "`python3 design-tokens/build.py`"
        )
        expected, _ = build()
        actual = FRONTEND_OUTPUT.read_text(encoding="utf-8")
        assert (
            actual == expected
        ), "frontend tokens.css out of sync — run `python3 design-tokens/build.py`"

    def test_ops_file_exists_and_in_sync(self):
        assert FRONTEND_OPS_OUTPUT.exists()
        _, expected = build()
        actual = FRONTEND_OPS_OUTPUT.read_text(encoding="utf-8")
        assert (
            actual == expected
        ), "frontend-ops/src/styles/tokens.css out of sync — run `python3 design-tokens/build.py`"
