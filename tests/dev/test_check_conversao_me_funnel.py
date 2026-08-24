"""Prova por mutação do gate ADR-390 D4.

A bateria abaixo nasceu do §Ataque da A40.l63 (2026-08-24), que mediu o gate
original pegando **3 de 10** formas plausíveis de reintroduzir a multiplicação.
Cada caso aqui é um idioma que existe neste repositório — não uma variação
sintética. Mutação que só o gate original pegava não prova nada sobre a classe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))

from check_conversao_me_funnel import main, offenders  # noqa: E402

# (id, corpo do produtor novo). Todos devem ser ofensores.
MUTACOES = [
    ("name_historico", "def f(saldo, cambio_usd):\n    return saldo * cambio_usd\n"),
    ("invertido", "def f(saldo, cambio_usd):\n    return cambio_usd * saldo\n"),
    ("attr_rate", "def f(saldo, quote):\n    return saldo * quote.rate\n"),
    # O atributo que o adapter de fato carrega — a lista original vinha do
    # nome do *parâmetro* de __init__, sem o underscore.
    ("attr_privado", "def f(self, saldo):\n    return saldo * self._cambio_usd_brl\n"),
    ("attr_taxa_do_carimbo", "def f(saldo, conv):\n    return saldo * conv.taxa\n"),
    ("subscript", "def f(self, saldo):\n    return saldo * self._taxas['cambio_usd_brl']\n"),
    # A linha 905 pré-390, apenas inline em vez de ligada a um local.
    (
        "call_get_com_chave",
        "def f(self, saldo):\n"
        "    return saldo * safe_float(self._taxas.get('cambio_usd_brl', 5.80))\n",
    ),
    ("call_cast", "def f(saldo, cambio_usd):\n    return saldo * float(cambio_usd)\n"),
    # `+=`/`*=` é o idioma dominante da própria função que o gate protege.
    ("aug_assign", "def f(saldo, cambio_usd):\n    v = saldo\n    v *= cambio_usd\n    return v\n"),
    ("renomeado_par", "def f(saldo, usd_brl):\n    return saldo * usd_brl\n"),
]


def _root_with(tmp_path: Path, body: str, name: str = "fake_caixa.py") -> Path:
    producer = tmp_path / "pipeline" / "domain" / "services" / name
    producer.parent.mkdir(parents=True, exist_ok=True)
    producer.write_text(body)
    return tmp_path / "pipeline"


@pytest.mark.parametrize("caso,body", MUTACOES, ids=[c for c, _ in MUTACOES])
def test_mutacao_derruba_o_gate(tmp_path: Path, caso: str, body: str) -> None:
    root = _root_with(tmp_path, body)
    assert main(["--root", str(root)]) == 1, f"{caso} passou pelo gate"
    assert any("fake_caixa.py" in item for item in offenders((root,)))


def test_codigo_sem_conversao_nao_e_ofensor(tmp_path: Path) -> None:
    """Controle de polaridade: o gate precisa saber ficar quieto."""
    root = _root_with(
        tmp_path,
        "def f(a, b, meses):\n"
        "    total = a * b\n"
        "    renda = total * 12\n"
        "    return renda / meses\n",
    )
    assert main(["--root", str(root)]) == 0


def test_sink_e_o_path_canonico_nao_o_basename(tmp_path: Path) -> None:
    """Um `conversao_me.py` em qualquer pasta ficava isento (A40.l63 §Ataque §2)."""
    root = _root_with(
        tmp_path,
        "def convert(amount, quote):\n    return amount * quote.rate\n",
        name="conversao_me.py",
    )
    assert main(["--root", str(root)]) == 1


def test_conversor_canonico_do_repo_e_isento() -> None:
    """O sink real multiplica por `quote.rate` e não pode ser ofensor."""
    assert main([]) == 0
