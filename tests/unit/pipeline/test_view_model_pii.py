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
    TIPOS_COBERTOS,
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


# ─────────────── [[A40.l115]] — cobertura declarada = cobertura medida ──────────
#
# A lane nasceu de uma docstring que afirmava "CPF/CNPJ redigidos" e valeu como
# justificativa para não existir gate. O antídoto não é prosa mais cuidadosa: é
# uma testemunha por tipo, atravessando o detector E o redator de verdade. Um
# teste que comparasse `TIPOS_COBERTOS` consigo mesmo sobreviveria à mutação da
# própria constante — seria o mesmo modo de falha, num arquivo diferente.
_TESTEMUNHAS = {
    "IDENTIFICADOR": "ADQUIRIDO DE FULANO CPF 123.456.789-09",
    "CPF_PARCIAL": "Falta a declaração de CPF ***.***.***-09 no ano-base",
    "CONTA": "Conta Corrente - Ag 1234 Conta 1234567-8",
    "MATRICULA": "IMOVEL MATR. 999999 DO CARTORIO",
    "ENDERECO": "CASA NA R. Exemplo, 100",
    "CEP": "Bairro Exemplo, CEP 00000-000",
}


def test_cobertura_declarada_igual_a_medida() -> None:
    """Igualdade de conjunto nas DUAS direções — nenhum tipo declarado sem
    testemunha, nenhuma testemunha fora do vocabulário declarado."""
    medido = {t for texto in _TESTEMUNHAS.values() for t in cartorial_pii_tipos(texto)}
    assert medido == set(TIPOS_COBERTOS)
    assert set(_TESTEMUNHAS) == set(TIPOS_COBERTOS)


@pytest.mark.parametrize("tipo", TIPOS_COBERTOS)
def test_cada_tipo_declarado_tem_testemunha_que_o_dispara(tipo: str) -> None:
    assert tipo in cartorial_pii_tipos(_TESTEMUNHAS[tipo])


@pytest.mark.parametrize("tipo", TIPOS_COBERTOS)
def test_cada_tipo_declarado_e_de_fato_redigido(tipo: str) -> None:
    """Detectar sem redigir é o falso-verde do gate: o scanner acusa, o gêmeo de
    escrita não limpa, e o payload servido continua com a PII."""
    redigido = redact_cartorial(_TESTEMUNHAS[tipo])
    assert tipo not in cartorial_pii_tipos(redigido)
    assert redact_cartorial(redigido) == redigido


def test_docstring_do_modulo_declara_exatamente_os_tipos_cobertos() -> None:
    """A linha "Tipos cobertos:" da docstring é contrato, não prosa: se alguém
    adicionar tipo sem anunciá-lo (ou anunciar sem implementar), isto falha."""
    linha = next(
        ln for ln in (view_model_pii.__doc__ or "").splitlines() if ln.startswith("Tipos cobertos:")
    )
    anunciados = {t.strip() for t in linha.split(":", 1)[1].split("·")}
    assert anunciados == set(TIPOS_COBERTOS)


# ─────────────── [[A40.l115]] — os dois vazamentos medidos no U5 ────────────────


@pytest.mark.parametrize(
    "rotulo",
    [
        "Conta Corrente - Ag 1234 Conta 1234567-8",
        "RDB/CDB - Ag 1234 Conta 1234567-8",
        "Depósito em conta pagamento - PicPay IP - Ag 1 Conta 123456-7",
        "CDB - Conta 1234-123456789012",
    ],
)
def test_as_quatro_linhas_de_posicao_31_12_que_publicavam_conta(rotulo: str) -> None:
    """Formas reais do `posicao_31_12` do U5 — o gate dava zero hit sobre elas."""
    assert "CONTA" in cartorial_pii_tipos(rotulo)
    redigido = redact_cartorial(rotulo)
    assert "CONTA" not in cartorial_pii_tipos(redigido)
    assert "1234567" not in redigido and "123456789012" not in redigido


@pytest.mark.parametrize(
    "mascara",
    ["***.***.***-09", "***.***.789-00", "***.456.789-**"],
)
def test_as_tres_mascaras_de_cpf_que_o_produto_emite(mascara: str) -> None:
    """E1.6 (`***.***.***-XX`), [[ADR-259]] §4 e [[ADR-231]] emitem formas
    diferentes; o gate media só a crua e deixava as três passarem."""
    assert "CPF_PARCIAL" in cartorial_pii_tipos(f"declaração de CPF {mascara} ausente")


def test_cpf_cru_nao_vira_cpf_parcial() -> None:
    """`_CPF_PARCIAL` exige `*` no PRÓPRIO token — senão duplicaria IDENTIFICADOR."""
    assert cartorial_pii_tipos("CPF 123.456.789-09") == ("IDENTIFICADOR",)


def test_agencia_sai_inteira_e_conta_preserva_a_cauda() -> None:
    # Publica-se o que desambigua, oculta-se o que credencia: agência não
    # desambigua (contas do mesmo banco a compartilham) e é a metade transacional.
    # A agência da testemunha tem DV de propósito: com 4 dígitos exatos, zerar a
    # agência e preservar cauda-4 produzem a MESMA string, e a fixture deixa de
    # discriminar `_AG_CAUDA` (a mutação M4 sobrevivia).
    assert redact_cartorial("Ag 1234-5 Conta 1234567-8") == "Ag ••••-• Conta ••••567-8"
    assert redact_cartorial("Ag 1234 Conta 1234567-8") == "Ag •••• Conta ••••567-8"


# Prosa é outra distribuição estatística que rótulo de linha, e o gate passou a
# rodar sobre a prosa do parecer. `conta` é palavra hiperfrequente em pt-BR: a
# primeira versão redigia `conta: R$ 1.500` como `R$ •.500`. Corromper valor
# monetário ([[ADR-090]]) é pior que o vazamento que o gate evita.
@pytest.mark.parametrize(
    "prosa",
    [
        "saldo em conta: R$ 1.500 no fim do mes",
        "manter em conta corrente 3.000 de reserva",
        "levar em conta 2026 como ano-base",
        "deixe 6.000 em conta para emergencia",
        "a poupança rendeu 1.200 no ano",
        "conta corrente com saldo de 12.345,67",
    ],
)
def test_prosa_do_parecer_nao_e_redigida_como_conta(prosa: str) -> None:
    assert "CONTA" not in cartorial_pii_tipos(prosa)
    assert redact_cartorial(prosa) == prosa


@pytest.mark.parametrize(
    ("regex", "tipo"),
    [("_CPF_PARCIAL", "CPF_PARCIAL"), ("_CONTA", "CONTA")],
)
def test_regex_nova_e_load_bearing(regex: str, tipo: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralizar a regex some com o tipo — nenhuma das duas é decorativa."""
    import re

    monkeypatch.setattr(view_model_pii, regex, re.compile(r"(?!x)x"))
    assert tipo not in cartorial_pii_tipos(_TESTEMUNHAS[tipo])
