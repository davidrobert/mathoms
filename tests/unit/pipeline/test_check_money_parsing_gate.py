"""O gate de parse monetário pega as reintroduções plausíveis — medido por sonda."""

# A 1ª versão do gate coletava por CADEIA e pegava 1 de 4 formas (medido na review
# `data-engineer` do PR #1417). A versão por corpo-de-função + constantes de módulo pega
# 3 de 4. A 4ª (`float(v)` cru em campo monetário) é classe distinta: não há idioma para
# casar — `float(v)` é legítimo em quase todo lugar. Documentada como limite conhecido.

import importlib.util
from pathlib import Path

import pytest

_GATE = Path(__file__).resolve().parents[3] / "dev" / "check_money_parsing.py"


def _gate():
    spec = importlib.util.spec_from_file_location("check_money_parsing", _GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PEGA = [
    (
        "encadeado",
        'def f(v):\n    return float(v.replace(".", "").replace(",", "."))\n',
    ),
    (
        "dois statements",
        'def f(v):\n    s = v.replace(".", "")\n    s = s.replace(",", ".")\n    return float(s)\n',
    ),
    (
        "separador em constante de módulo",
        '_MILHAR = "."\n_DEC = ","\n\n\ndef f(v):\n'
        '    s = v.replace(_MILHAR, "")\n    return float(s.replace(_DEC, "."))\n',
    ),
    (
        "escopo de módulo (sem função)",
        'RAW = "1.234,56"\nVAL = float(RAW.replace(".", "").replace(",", "."))\n',
    ),
]

PASSA = [
    # Strip de pontuação em documento — não é parse monetário (apolice.py:124).
    ("cpf/cnpj", 'def f(v):\n    return v.replace(".", "").replace("-", "").replace("/", "")\n'),
    # Formatação de SAÍDA: o inverso (ponto → vírgula).
    ("formatação pt-BR", 'def f(n):\n    return f"{n:.2f}".replace(".", ",")\n'),
    # Limite conhecido: classe diferente, sem idioma para casar.
    ("float cru", "def f(v):\n    return float(v)\n"),
]


@pytest.mark.parametrize("nome,src", PEGA, ids=[n for n, _ in PEGA])
def test_gate_pega_reintroducao(nome, src):
    assert _gate().violacoes(src, "pipeline/_sonda.py"), f"gate cego para: {nome}"


@pytest.mark.parametrize("nome,src", PASSA, ids=[n for n, _ in PASSA])
def test_gate_nao_tem_falso_positivo(nome, src):
    assert not _gate().violacoes(src, "pipeline/_sonda.py"), f"falso-positivo em: {nome}"


def test_repo_esta_limpo():
    """O gate roda no pre-commit e no CI — tem de estar verde em `main`."""
    assert _gate().main([]) == 0
