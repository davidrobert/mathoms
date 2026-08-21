"""O gate de emenda datada enxerga ênfase, não só heading (ADR-027).

Regressão de classe: por 3 meses `AMENDMENT_HEADING_RE` casava apenas
`^#{2,4}`, então emenda anunciada em negrito ficava invisível e o gate passava
em silêncio. Três ADRs usavam essa forma — a de 2026-05-22 na ADR-157 mudou
comportamento de pipeline (anti-PII de `error` para `warning`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.check_adr_amendment_signal import check_file

_FM = '---\nid: ADR-999\ntype: adr\ntitle: "Teste"\nstatus: Decidido\ndate: "2026-01-01"\n{extra}---\n\n'


def _adr(tmp_path: Path, corpo: str, *, amended: str | None = None) -> Path:
    extra = f'amended_at: ["{amended}"]\n' if amended else ""
    p = tmp_path / "999-teste.md"
    p.write_text(_FM.format(extra=extra) + corpo, encoding="utf-8")
    return p


@pytest.mark.parametrize(
    "linha",
    [
        "**Errata 2026-05-22 — D5 reclassificado**",
        "**Emenda de implementação 2026-08-14:** o resolver mudou",
        "- **Emenda (A24.l3, 2026-06-10):** `tipo_lancamento` saiu do contrato",
        "*Correção 2026-05-22* — a fórmula tinha um termo a mais",
    ],
)
def test_enfase_datada_exige_sinal(tmp_path: Path, linha: str) -> None:
    """A forma que o regex de heading não via agora acusa."""
    erros = check_file(_adr(tmp_path, linha))

    assert erros, f"gate cego a: {linha}"
    assert "amended_at" in erros[0]


def test_enfase_com_sinal_passa(tmp_path: Path) -> None:
    assert not check_file(_adr(tmp_path, "**Errata 2026-05-22 — D5**", amended="2026-05-22"))


def test_heading_continua_valendo(tmp_path: Path) -> None:
    """Não regride a forma que já era coberta."""
    assert check_file(_adr(tmp_path, "## Emenda 2026-05-22 — D5 reclassificado"))


def test_enfase_sem_data_nao_dispara(tmp_path: Path) -> None:
    """Sem data na mesma linha não há emenda datada — herdar da linha seguinte
    transformaria menção em prosa em falso positivo."""
    corpo = "**Emenda** — este parágrafo só cita o conceito.\n\nOutro texto de 2026-05-22.\n"

    assert not check_file(_adr(tmp_path, corpo))
