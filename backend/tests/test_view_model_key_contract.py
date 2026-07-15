"""Contrato de shape do view-model (ADR-338 · cluster CTO-02).

O view-model NÃO pode carregar o nome do membro em CHAVES de dict — só em VALORES.
Chaves derivadas do nome (``investimentos_<nome>``, ``idade_<nome>_if``,
``salario_<nome>_clt_brl``) produzem: (1) shape não-determinístico (key-set varia
por workspace → golden frágil, TS não-tipável); (2) PII estrutural que scrubbers de
VALOR não pegam (nome legal na chave). Este teste é a alavanca red-before-green do
CTO-02 e vira regressão permanente contra qualquer campo por-nome futuro.

Estratégia: roda o view-model com DOIS conjuntos de nomes distintos e afirma
key-set idêntico (determinismo de shape) — qualquer nome-em-chave quebra a
igualdade. Reforça com walk anti-token e presença das role-keys."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
for _p in (str(_REPO), str(_REPO / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pipeline_golden_substrate import (  # noqa: E402
    load_fixture,
    run_dogfood_pipeline,
    write_e5_config,
)

_DOGFOOD = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"

_FAMILY_A = {
    "titular": "alex",
    "membros": {
        "alex": {"nome_curto": "Alex", "data_nascimento": "1985-03-10"},
        "bia": {"nome_curto": "Bia", "data_nascimento": "1987-07-22"},
    },
}
# Nomes deliberadamente distintos (tokens improváveis como substring de chave legítima).
_FAMILY_B = {
    "titular": "quirino",
    "membros": {
        "quirino": {"nome_curto": "Quirino", "data_nascimento": "1985-03-10"},
        "placida": {"nome_curto": "Plácida", "data_nascimento": "1987-07-22"},
    },
}
_NAME_TOKENS = ("alex", "bia", "quirino", "placida")


def _run(tmp_path: Path, family: dict) -> dict:
    write_e5_config(
        tmp_path,
        family=family,
        income_keywords={"lucros_distribuidos": ["PIX"]},
        expense_keywords={"alimentacao": ["MERCADO"]},
    )
    return run_dogfood_pipeline(
        tmp_path,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "fict_a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "fict_b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )


def _key_paths(obj: Any, path: str = "") -> set[str]:
    """Todos os caminhos de CHAVE de dict, com índices de lista normalizados p/ ``[]``
    (shape independente de ordem/nome de valor)."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            out.add(p)
            out |= _key_paths(v, p)
    elif isinstance(obj, list):
        for v in obj:
            out |= _key_paths(v, f"{path}[]")
    return out


def _all_keys(obj: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k))
            out |= _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _all_keys(v)
    return out


def test_key_set_independe_dos_nomes(tmp_path: Path):
    """Shape determinístico: trocar os nomes NÃO pode mudar o conjunto de chaves."""
    a = _key_paths(_run(tmp_path / "a", _FAMILY_A))
    b = _key_paths(_run(tmp_path / "b", _FAMILY_B))
    diff = a.symmetric_difference(b)
    assert not diff, f"chaves dependentes de nome (shape não-determinístico): {sorted(diff)[:20]}"


def _segments(key: str) -> set[str]:
    """Segmentos ``_``-delimitados do nome da chave (evita falso-positivo de
    substring, ex.: 'bia' em 'cambial')."""
    return set(key.lower().split("_"))


def test_nenhuma_chave_contem_token_de_nome(tmp_path: Path):
    """Gate estrutural de PII: nome de membro nunca em CHAVE de dict."""
    keys = _all_keys(_run(tmp_path, _FAMILY_B))
    tokens = set(_NAME_TOKENS)
    offenders = sorted(k for k in keys if _segments(k) & tokens)
    assert not offenders, f"chaves com token de nome (PII estrutural): {offenders}"


def test_role_keys_obrigatorias_presentes(tmp_path: Path):
    """As role-keys canônicas existem (contrato estável para TS + goldens)."""
    e5 = _run(tmp_path, _FAMILY_A)
    pat = e5.get("patrimonio", {})
    assert "investimentos_titular" in pat
    assert "investimentos_conjuge" in pat
    goals = e5.get("goals", {})
    assert "idade_titular_if" in goals
