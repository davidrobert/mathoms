"""Goldens dos checksums de posição RV (ADR-346 · A39.l9).

Invariantes anti-silêncio: checksum de contagem (Itaú custódia só-quantidade)
e checksum Σ-por-classe (Rico carteira valorada) ESCALAM em vez de perder
posição em silêncio; proventos/JCP ficam fora do PL.
"""

from scripts.e2.banks.rico import (
    _consume_rico_position_row,
    _fill_rico_positions,
    _rico_is_class_header,
    _rico_position,
)
from scripts.e2.validation import apply_rv_carteira_checksum, apply_rv_count_checksum


def _result(posicoes):
    return {"tipo": "investimentosposicao", "posicoes": list(posicoes), "notas": []}


# --- Itaú: checksum de contagem (só-quantidade) --------------------------------


def test_itau_count_ok_marca_checksum():
    r = _result([{"ticker": "BRKM5", "quantidade": 300}, {"ticker": "ITSA4", "quantidade": 778}])
    apply_rv_count_checksum(r, raw_detected=2)
    assert r.get("checksum_ok") is True
    assert not r.get("requires_llm_fallback")


def test_itau_count_mismatch_escala():
    # 3 linhas-candidatas observadas, só 2 viraram posição → perda → escala.
    r = _result([{"ticker": "BRKM5", "quantidade": 300}, {"ticker": "ITSA4", "quantidade": 778}])
    apply_rv_count_checksum(r, raw_detected=3)
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.investment_sum_mismatch"


def test_itau_zero_posicoes_escala():
    r = _result([])
    apply_rv_count_checksum(r, raw_detected=0)
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.empty_result"


def test_itau_posicao_sem_valor_nao_e_zero():
    # Custódia só-quantidade: valor_atual AUSENTE (não 0.0) → posicao_sem_marcacao no E4.
    r = _result([{"ticker": "BRKM5", "quantidade": 300}])
    apply_rv_count_checksum(r, raw_detected=1)
    assert "valor_atual" not in r["posicoes"][0]


# --- Rico: checksum Σ-por-classe (valorada) ------------------------------------


def test_rico_classes_fecham_marca_checksum():
    r = _result(
        [
            {"ticker": "PETR4", "valor_atual": 800.0, "classe": "Ações"},
            {"ticker": "ITSA4", "valor_atual": 300.0, "classe": "Ações"},
            {"nome": "Fundo X", "valor_atual": 500.0, "classe": "Fundos"},
        ]
    )
    apply_rv_carteira_checksum(r, {"Ações": 1100.0, "Fundos": 500.0})
    assert r.get("checksum_ok") is True
    assert not r.get("requires_llm_fallback")


def test_rico_classe_nao_fecha_escala():
    r = _result([{"ticker": "PETR4", "valor_atual": 800.0, "classe": "Ações"}])
    apply_rv_carteira_checksum(r, {"Ações": 1100.0})
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.investment_sum_mismatch"


def test_rico_sem_subtotal_pula_com_traco():
    r = _result([{"ticker": "PETR4", "valor_atual": 800.0, "classe": "Ações"}])
    apply_rv_carteira_checksum(r, {})
    assert r.get("checksum_skipped_no_total") is True
    assert not r.get("requires_llm_fallback")


# --- Rico: parsing de linha -----------------------------------------------------


def test_class_header_reconhecido():
    assert _rico_is_class_header(["Ações", "R$ 1.100,00"]) is True
    assert _rico_is_class_header(["PETR4", "R$ 800,00", "28,7%"]) is False  # posição, não header
    assert _rico_is_class_header(["PETR4", "R$ 800,00"]) is False  # ticker não é classe


def test_ticker_position_carrega_qtd():
    pos = _rico_position(["PETR4", "R$ 800,00", "28,7%", "-", "R$ 42,58", "1.700"], "Ações")
    assert pos["ticker"] == "PETR4"
    assert pos["quantidade"] == 1700
    assert pos["valor_atual"] == 800.0


def test_fund_position_sem_ticker_sem_qtd():
    pos = _rico_position(["Fundo Sintetico FIF", "R$ 500,00", "1,31%"], "Fundos")
    assert "ticker" not in pos
    assert "quantidade" not in pos
    assert pos["valor_atual"] == 500.0


def test_proventos_ficam_fora_do_pl():
    rows = [
        ["Ações", "R$ 1.100,00"],
        ["PETR4", "R$ 800,00", "28,7%", "-", "1.700"],
        ["ITSA4", "R$ 300,00", "4,26%", "-", "778"],
        ["Dividendos, proventos e outras distribuições"],
        ["Proventos"],
        ["PETR4", "1.700", "0,24%", "R$ 50,00"],  # JCP futuro — NÃO é posição de PL
    ]
    result = _result([])
    subtotais = _fill_rico_positions(result, rows)
    assert subtotais == {"Ações": 1100.0}
    assert [p["ticker"] for p in result["posicoes"]] == ["PETR4", "ITSA4"]
    assert any("proventos/JCP" in n for n in result.get("notas", []))
