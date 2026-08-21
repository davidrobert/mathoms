"""Gate de PII no view-model — ADR-337 critério 4 · A40.l6."""

from __future__ import annotations

from pipeline.observability.view_model_pii import (
    redact_cartorial,
    scan_view_model_pii,
)

# Placeholders canônicos (ADR-319): o gate ainda casa o shape; o lint não.
_CARTORIAL = "Apartamento matrícula 999.999, Rua Exemplo, 100, CEP 00000-000, CPF 123.456.789-09"


def _payload(descricao: str) -> dict:
    return {
        "real_estate": {"imoveis": [{"descricao": descricao}]},
        "endividamento": {"dividas": [{"descricao": "Financiamento imobiliário (titular)"}]},
    }


def test_gate_bloqueia_descricao_cartorial_e_cita_o_path() -> None:
    hits = scan_view_model_pii(_payload(_CARTORIAL))
    paths = {h.path for h in hits}
    tipos = {h.tipo for h in hits}
    assert "real_estate.imoveis[0].descricao" in paths
    assert {"MATRICULA", "ENDERECO", "CEP", "IDENTIFICADOR"} <= tipos
    assert all("123.456" not in h.format() for h in hits)


def test_remover_as_keys_faz_a_fixture_passar() -> None:
    """Prova de mutação: sem keys o PII atravessa — o teste testa o gate."""
    assert scan_view_model_pii(_payload(_CARTORIAL), keys=frozenset()) == ()


def test_corpus_limpo_nao_dispara() -> None:
    hits = scan_view_model_pii(_payload("Imóvel locado"))
    assert hits == ()


def test_redact_cartorial_remove_os_quatro_tipos() -> None:
    redacted = redact_cartorial(_CARTORIAL)
    assert scan_view_model_pii(_payload(redacted)) == ()
    assert "999.999" not in redacted
    assert "00000-000" not in redacted
    assert "Rua Exemplo" not in redacted
