"""Gate de PII no view-model — ADR-337 critério 4 · A40.l6.

O gate varre TODA string do payload. O teste que ele substituiu varria uma
allowlist de chave e por isso ficava verde com a PII em `endereco_canonical`
(§Ataque A1); a prova de mutação antiga trocava o argumento do chamador, não o
gate (§Ataque A7).
"""

from __future__ import annotations

import pytest

import pipeline.domain.services.real_estate_metrics  # noqa: F401  (ordem do ciclo de import)
from pipeline.domain.services.real_estate_metrics_payload import endereco_exibivel
from pipeline.observability import view_model_pii
from pipeline.observability.view_model_pii import (
    cartorial_pii_tipos,
    redact_cartorial,
    scan_view_model_pii,
)

# Placeholders canônicos (ADR-319): o gate casa o shape; o lint não acusa.
_CARTORIAL = "Apartamento matrícula 999.999, Rua Exemplo, 100, CEP 00000-000, CPF 123.456.789-09"


def _payload(descricao: str) -> dict:
    return {
        "real_estate": {"imoveis": [{"descricao": descricao}]},
        "endividamento": {"dividas": [{"descricao": "Financiamento imobiliário (titular)"}]},
    }


def test_gate_bloqueia_descricao_cartorial_e_cita_o_path() -> None:
    hits = scan_view_model_pii(_payload(_CARTORIAL))
    assert "real_estate.imoveis[0].descricao" in {h.path for h in hits}
    assert {"MATRICULA", "ENDERECO", "CEP", "IDENTIFICADOR"} <= {h.tipo for h in hits}
    assert all("123.456" not in h.format() for h in hits)


def test_gate_acusa_em_qualquer_chave_nao_so_descricao() -> None:
    """§Ataque A1: o allowlist de chave era o ponto cego — o predicado é o VALOR."""
    for chave in ("endereco_canonical", "endereco_display", "rotulo", "nome"):
        hits = scan_view_model_pii({"real_estate": {"imoveis": [{chave: _CARTORIAL}]}})
        assert hits, f"chave {chave} atravessou o gate"
        assert hits[0].path == f"real_estate.imoveis[0].{chave}"


def test_corpus_limpo_nao_dispara() -> None:
    assert scan_view_model_pii(_payload("Imóvel locado")) == ()
    assert scan_view_model_pii(_payload("exemplo 100")) == ()


@pytest.mark.parametrize(
    ("texto", "tipo"),
    [
        ("TERRENO — INSCRICAO MUNICIPAL (IPTU): 999.999.9999", "MATRICULA"),
        ("IMOVEL MATR. 999999 DO CARTORIO", "MATRICULA"),
        ("CASA NA R. Exemplo, 100", "ENDERECO"),
        ("ADQUIRIDO DE FULANO CPF 12345678909", "IDENTIFICADOR"),
    ],
)
def test_regressao_das_quatro_grafias_que_vazavam(texto: str, tipo: str) -> None:
    """§Ataque A6: o gate fechava a grafia da fixture, não a classe."""
    assert tipo in cartorial_pii_tipos(texto)


def test_neutralizar_o_detector_faz_a_fixture_passar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prova de mutação: o alvo é o GATE, não o argumento do chamador."""
    monkeypatch.setattr(view_model_pii, "cartorial_pii_tipos", lambda _text: ())
    assert scan_view_model_pii(_payload(_CARTORIAL)) == ()


@pytest.mark.parametrize(
    ("regex", "tipo"),
    [("_CONTRATO", "MATRICULA"), ("_ENDERECO", "ENDERECO"), ("_CEP", "CEP")],
)
def test_cada_regex_e_load_bearing(regex: str, tipo: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralizar UMA regex some com exatamente UM tipo — nenhuma é decorativa."""
    import re

    monkeypatch.setattr(view_model_pii, regex, re.compile(r"(?!x)x"))
    assert tipo not in cartorial_pii_tipos(_CARTORIAL)


def test_redact_cartorial_remove_os_quatro_tipos() -> None:
    redacted = redact_cartorial(_CARTORIAL)
    assert cartorial_pii_tipos(redacted) == ()
    assert "999.999" not in redacted
    assert "00000-000" not in redacted
    assert "Rua Exemplo" not in redacted


def test_redact_cartorial_e_idempotente() -> None:
    once = redact_cartorial(_CARTORIAL)
    assert redact_cartorial(once) == once


@pytest.mark.parametrize(
    ("canonical", "esperado"),
    [
        ("exemplo 100", "exemplo 100"),
        ("  acacias 1234  ", "acacias 1234"),
        ("mat:999999", None),
        ("iptu:9999999999", None),
        ("qa:894064293", None),
        ("Rua Exemplo, 100, CEP 00000-000", None),
        (None, None),
        ("   ", None),
    ],
)
def test_endereco_exibivel_publica_so_o_que_passa_no_gate(
    canonical: str | None, esperado: str | None
) -> None:
    """§Ataque A1/A2: matrícula e IPTU chegavam à tela como 'rótulo curto'."""
    assert endereco_exibivel(canonical) == esperado
