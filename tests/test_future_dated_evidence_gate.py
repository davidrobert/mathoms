"""Campo de frontmatter que afirma passado não aceita data no futuro.

Regressão real (2026-08-28, A40.l80): 9 datas stampadas 1 e 2 dias à frente em
3 docs de uma sessão. `check_adr_amendment_signal` leu o mesmo `amended_at` e
ficou verde — ele exige que a data do heading **exista** no frontmatter, nunca
que ela seja possível.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.check_future_dated_evidence import datas_futuras

_TETO = "2026-08-28"


def test_amended_at_real_do_incidente_e_pego():
    """O `amended_at` como estava na ADR-412 em `origin/main` — dado real, não sintético."""
    fm = 'id: ADR-412\ndate: "2026-08-21"\namended_at: ["2026-08-25", "2026-08-28", "2026-08-29", "2026-08-30"]\n'
    assert datas_futuras(fm, _TETO) == [("amended_at", "2026-08-29"), ("amended_at", "2026-08-30")]


def test_ship_date_futura_e_pega():
    """`ship_date` afirma que a lane shipou; no futuro é impossível."""
    assert datas_futuras('ship_date: "2026-09-10"\n', _TETO) == [("ship_date", "2026-09-10")]


def test_date_no_teto_passa():
    """Hoje é passado o bastante — o teto é inclusivo, senão o commit do dia reprova."""
    assert datas_futuras(f'date: "{_TETO}"\n', _TETO) == []


def test_date_target_futura_nao_e_evidencia():
    """A A40 mira 2026-09-05: alvo é plano, não afirmação de fato ocorrido."""
    assert datas_futuras('date_target: "2026-09-05"\n', _TETO) == []


def test_bloco_yaml_de_lista_tambem_e_lido():
    """`amended_at` em bloco `- item` é a mesma evidência que a forma inline."""
    fm = 'amended_at:\n  - "2026-08-20"\n  - "2026-09-01"\n'
    assert datas_futuras(fm, _TETO) == [("amended_at", "2026-09-01")]
