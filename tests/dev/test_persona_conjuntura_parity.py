"""A persona só convida leitura de ciclo de juros se o exec context traz taxa (ADR-341 §Emenda 2026-10-09)."""

# Bicondicional, como o gate de capacidade da A40.l117: (1) enquanto o manifest não
# projeta taxa de mercado, a persona não convida o modelo a ler ciclo de juros — a taxa
# viria do treino, desatualizada; (2) se o manifest passar a projetar taxa, a R23
# ("o produto não tem taxa de mercado viva") fica falsa e este teste cobra a revisão.
# O E5 já guarda `real_estate.benchmarks` (seed estático, ADR-221 Proposto): projetá-lo
# é mudança plausível, e é ela que a perna reversa pega.
#
# Limite declarado: fecha os CONVITES literais, não a classe. Prosa equivalente ("escolha
# o indexador pelo momento da Selic") passa. Juro de dívida (`taxa_juros_aa`) não é taxa
# de mercado e fica fora do regex de path de propósito.

from __future__ import annotations

import re
from pathlib import Path

from backend.app.services.parecer_manifest import load_persona

_MANIFEST = Path(__file__).resolve().parents[2] / "config" / "prompts" / "parecer_planejador.yaml"
_PATH_RE = re.compile(r'path:\s*"(\$[^"]+)"')
_TAXA_DE_MERCADO_RE = re.compile(r"selic|cdi|curva|benchmark", re.IGNORECASE)
_CONVITE_RE = re.compile(
    r"contrac[ií]clic|ciclo de juros|curva de juros|travar prefixad", re.IGNORECASE
)
_R23 = "**R23.**"


def _paths_de_taxa(manifest_text: str) -> list[str]:
    return [p for p in _PATH_RE.findall(manifest_text) if _TAXA_DE_MERCADO_RE.search(p)]


def _convites_fora_da_r23(persona: str) -> list[str]:
    paragrafos = (p for p in persona.split("\n\n") if not p.lstrip().startswith(_R23))
    return [m.group(0) for p in paragrafos for m in _CONVITE_RE.finditer(p)]


def _violacoes(persona: str, manifest_text: str) -> list[str]:
    taxas = _paths_de_taxa(manifest_text)
    if taxas and _R23 in persona:
        return [f"manifest projeta taxa {taxas}, mas a R23 afirma que não há — revise a R23"]
    if not taxas:
        return [
            f"persona convida leitura de juros sem taxa no contexto: {c!r}"
            for c in _convites_fora_da_r23(persona)
        ]
    return []


def test_persona_e_manifest_concordam_sobre_taxa_de_mercado() -> None:
    assert _violacoes(load_persona()[0], _MANIFEST.read_text(encoding="utf-8")) == []


def test_perna_direta_pega_convite_reintroduzido() -> None:
    persona = (
        load_persona()[0]
        + "\n\n- Se a sugestão envolve travar prefixado no atual ciclo de juros → `auvp`.\n"
    )
    assert _violacoes(persona, _MANIFEST.read_text(encoding="utf-8"))


def test_perna_reversa_pega_taxa_projetada() -> None:
    manifest = (
        _MANIFEST.read_text(encoding="utf-8")
        + '\n- {path: "$.real_estate.benchmarks.cdi_liquido_pct"}\n'
    )
    assert _violacoes(load_persona()[0], manifest)


def test_isencao_da_r23_carrega_peso() -> None:
    # A proibição nomeia o que proíbe; sem a isenção, a perna direta acusaria a R23.
    persona = load_persona()[0]
    r23 = next(p for p in persona.split("\n\n") if p.lstrip().startswith(_R23))
    assert _CONVITE_RE.search(r23)
    assert _convites_fora_da_r23(persona) == []
