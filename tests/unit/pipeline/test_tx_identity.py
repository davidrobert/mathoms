"""Tests — ``_tx_identity`` (ADR-255 Camada A)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services._tx_identity import (  # noqa: E402
    _hash_v1,
    cents_int,
    normalize_banco,
    normalize_descricao,
    normalize_tipo_conta,
    normalize_titular,
)


class TestNormalizeBanco:
    def test_collapses_spacing_and_casing(self):
        assert normalize_banco("C6Bank") == normalize_banco("C6 Bank")
        assert normalize_banco("C6Bank") == normalize_banco("c6bank")

    def test_strips_accent(self):
        assert normalize_banco("Itaú") == normalize_banco("Itau")

    def test_empty_and_none(self):
        assert normalize_banco("") == ""
        assert normalize_banco(None) == ""


class TestNormalizeDescricao:
    def test_preserves_accent_and_digits(self):
        # Crítico para distinguir "FAÇA" vs "FACA" e tokens N/M legítimos.
        assert "ç" in normalize_descricao("FAÇA O X")
        assert "3/12" in normalize_descricao("PARC 3/12 LOJA")

    def test_collapses_whitespace_and_casing(self):
        assert normalize_descricao("  pix  recebido  arvo  ") == "pix recebido arvo"

    def test_empty_and_none(self):
        assert normalize_descricao("") == ""
        assert normalize_descricao(None) == ""

    def test_strips_routing_suffix_salarios_pj(self):
        # ADR-255 it. 2 — sufixo final ` — Salários PJ` removido antes do hash.
        assert normalize_descricao(
            "Pix recebido de ARVO SAUDE LTDA — Salários PJ"
        ) == normalize_descricao("Pix recebido de ARVO SAUDE LTDA")

    def test_strips_routing_suffix_only_at_end(self):
        # GUARD: sufixo em meio da descrição NÃO é stripado (só no final).
        # Cenário hipotético: bug futuro de parser que insere o tag no meio.
        # Acento preservado por normalize_descricao (vs normalize_banco).
        assert "salários pj" in normalize_descricao(
            "Pix recebido — Salários PJ de ARVO SAUDE LTDA — pagamento mensal"
        )

    def test_strips_routing_suffix_case_insensitive(self):
        assert (
            normalize_descricao("Pix recebido de X — TRANSF ENVIADA PIX")
            == normalize_descricao("pix recebido de x — transf enviada pix")
            == normalize_descricao("Pix recebido de X")
        )

    def test_preserves_legitimate_em_dash_segment(self):
        # GUARD: "— Aluguel apto 12" não é sufixo whitelisted; preservado.
        assert "aluguel apto 12" in normalize_descricao("Pix de João — Aluguel apto 12")


class TestCentsInt:
    def test_avoids_float_drift(self):
        # 47208.77 * 100 em float = 4720876.999... — int(round(...)) salva.
        assert cents_int(47208.77) == 4720877

    def test_negative(self):
        assert cents_int(-100.5) == -10050


class TestHashV1:
    def _base(self) -> dict:
        return dict(
            data="2026-03-30",
            banco="C6Bank",
            titular="david",
            tipo_conta="extratoconta",
            valor=47208.77,
            descricao="Pix recebido de ARVO SAUDE LTDA",
        )

    def test_deterministic_across_bank_casing_drift(self):
        h1 = _hash_v1(**{**self._base(), "banco": "C6Bank"})
        h2 = _hash_v1(**{**self._base(), "banco": "C6 Bank"})
        h3 = _hash_v1(**{**self._base(), "banco": "c6bank"})
        assert h1 == h2 == h3

    def test_changes_with_data(self):
        h1 = _hash_v1(**self._base())
        h2 = _hash_v1(**{**self._base(), "data": "2026-03-31"})
        assert h1 != h2

    def test_changes_with_titular(self):
        # K4: titular separa casal mesmo banco.
        h1 = _hash_v1(**self._base())
        h2 = _hash_v1(**{**self._base(), "titular": "mariana"})
        assert h1 != h2

    def test_changes_with_tipo_conta(self):
        # K4: tipo_conta separa CC vs poupança do mesmo titular.
        h1 = _hash_v1(**self._base())
        h2 = _hash_v1(**{**self._base(), "tipo_conta": "extratopoupanca"})
        assert h1 != h2

    def test_changes_with_valor(self):
        h1 = _hash_v1(**self._base())
        h2 = _hash_v1(**{**self._base(), "valor": 47208.78})
        assert h1 != h2

    def test_changes_with_genuinely_different_descricao(self):
        # Conteúdo de negócio diferente — diferentes remetentes — produz hashes
        # distintos. Critério: descricao_norm preserva remetente/destinatário.
        h1 = _hash_v1(**self._base())
        h2 = _hash_v1(**{**self._base(), "descricao": "Pix recebido de OUTRA EMPRESA LTDA"})
        assert h1 != h2

    def test_collapses_routing_suffix_salarios_pj(self):
        # ADR-255 it. 2 / critério #12 — C6 emite a MESMA transação em PDFs
        # diferentes ora com `" — Salários PJ"`, ora sem. Hash deve colapsar.
        h_with = _hash_v1(
            **{**self._base(), "descricao": "Pix recebido de ARVO SAUDE LTDA — Salários PJ"}
        )
        h_without = _hash_v1(**{**self._base(), "descricao": "Pix recebido de ARVO SAUDE LTDA"})
        assert h_with == h_without

    def test_collapses_routing_suffix_13_salario(self):
        # Décimo terceiro: mesmo PIX em 2 extratos com sufixo " — 13 Salário"
        # ora presente, ora omitido.
        h_with = _hash_v1(
            **{**self._base(), "descricao": "Pix recebido de ARVO SAUDE LTDA — 13 Salário"}
        )
        h_without = _hash_v1(**{**self._base(), "descricao": "Pix recebido de ARVO SAUDE LTDA"})
        assert h_with == h_without

    def test_collapses_routing_suffix_transf_pix(self):
        # Despesa: `" — TRANSF ENVIADA PIX"` é tag de roteamento C6, mesmo
        # PIX outbound em PDFs diferentes ora tem, ora não.
        h_with = _hash_v1(
            **{**self._base(), "descricao": "Pix enviado para X — TRANSF ENVIADA PIX"}
        )
        h_without = _hash_v1(**{**self._base(), "descricao": "Pix enviado para X"})
        assert h_with == h_without

    def test_collapses_routing_suffix_nf_numerada(self):
        # NFS 25 / NF 26 são tags emitidos pelo banco quando o PIX traz NF.
        h_nfs = _hash_v1(
            **{**self._base(), "descricao": "Pix recebido de CNRY MANAGEMENT LTDA — NFS 25"}
        )
        h_nf = _hash_v1(
            **{**self._base(), "descricao": "Pix recebido de CNRY MANAGEMENT LTDA — NF 26"}
        )
        h_plain = _hash_v1(**{**self._base(), "descricao": "Pix recebido de CNRY MANAGEMENT LTDA"})
        assert h_nfs == h_nf == h_plain

    def test_collapses_routing_suffix_boleto(self):
        h_with = _hash_v1(**{**self._base(), "descricao": "Belt Academy — Boleto"})
        h_without = _hash_v1(**{**self._base(), "descricao": "Belt Academy"})
        assert h_with == h_without

    def test_collapses_routing_suffix_darf_simples_nacional(self):
        # DARF detalhada — anexa "SIMPLES NACIONAL" sem em-dash.
        h_detail = _hash_v1(
            **{**self._base(), "descricao": "TRIBUTOS FEDERAIS DARF NUMERADO SIMPLES NACIONAL"}
        )
        h_plain = _hash_v1(**{**self._base(), "descricao": "TRIBUTOS FEDERAIS DARF NUMERADO"})
        assert h_detail == h_plain

    def test_collapses_routing_suffix_cpf_remetente_ted(self):
        # ADR-255 it.3 — TED inbound: alguns extratos C6 anexam CPF+nome do
        # remetente, outros não. Mesmo TED, descrição diferente.
        h_with_cpf = _hash_v1(
            **{**self._base(), "descricao": "RECEBIMENTO DE TED — 12345678901-FULANO DE TAL"}
        )
        h_plain = _hash_v1(**{**self._base(), "descricao": "RECEBIMENTO DE TED"})
        assert h_with_cpf == h_plain

    def test_collapses_routing_suffix_cnpj_remetente_ted(self):
        # ADR-255 it.3 — TED inbound de empresa: CNPJ 14 dígitos + nome PJ.
        h_with_cnpj = _hash_v1(
            **{
                **self._base(),
                "descricao": "RECEBIMENTO DE TED — 12345678000100-EMPRESA EXEMPLO SA",
            }
        )
        h_plain = _hash_v1(**{**self._base(), "descricao": "RECEBIMENTO DE TED"})
        assert h_with_cnpj == h_plain

    def test_collapses_routing_suffix_placa_local_c6tag(self):
        # ADR-255 it.3 — C6TAG ESTACIONAMENTO: alguns extratos anexam
        # placa do veículo + local, outros omitem.
        h_with_placa = _hash_v1(
            **{
                **self._base(),
                "descricao": "C6TAG ESTACIONAMENTO — GDK6A27-AEROPORTO DE GUARULHOS GRU ROD",
            }
        )
        h_plain = _hash_v1(**{**self._base(), "descricao": "C6TAG ESTACIONAMENTO"})
        assert h_with_placa == h_plain

    def test_does_not_strip_short_alphanum_after_dash(self):
        # GUARD: NÃO casar ` — A1` ou ` — AB12` (curto demais para placa/CPF).
        # Aluguel apto 12 vs 13 já tem guard separado; este protege casos curtos.
        h_a = _hash_v1(**{**self._base(), "descricao": "X — A1"})
        h_b = _hash_v1(**{**self._base(), "descricao": "X — A2"})
        # Sufixos curtos demais NÃO casam whitelist — preservados como conteúdo.
        assert h_a != h_b

    def test_does_not_strip_legitimate_em_dash_content(self):
        # GUARD: `"— Aluguel apto 12"` vs `"— Aluguel apto 13"` são receitas
        # legítimas de aluguéis distintos. Strip cego juntaria; whitelist NÃO
        # casa porque o conteúdo após em-dash não está na lista.
        h12 = _hash_v1(**{**self._base(), "descricao": "Pix de João — Aluguel apto 12"})
        h13 = _hash_v1(**{**self._base(), "descricao": "Pix de João — Aluguel apto 13"})
        assert h12 != h13

    def test_preserves_distinct_parcelas(self):
        # PARC 3/12 vs PARC 4/12 — mesmo dia, mesmo valor, mas diferentes
        # lançamentos contábeis. Hash deve separar.
        h_p3 = _hash_v1(
            data="2026-01-15",
            banco="Santander",
            titular="david",
            tipo_conta="faturaunique",
            valor=199.90,
            descricao="LOJA X PARC 3/12",
        )
        h_p4 = _hash_v1(
            data="2026-01-15",
            banco="Santander",
            titular="david",
            tipo_conta="faturaunique",
            valor=199.90,
            descricao="LOJA X PARC 4/12",
        )
        assert h_p3 != h_p4

    def test_abs_value_collapses_sign(self):
        # Hash usa abs() para robustez se caller passar valor com sinal.
        kw = dict(data="2026-01-01", banco="X", titular="y", tipo_conta="z", descricao="abc")
        h_pos = _hash_v1(valor=100.0, **kw)
        h_neg = _hash_v1(valor=-100.0, **kw)
        assert h_pos == h_neg

    def test_hash_is_16_lowercase_hex(self):
        h = _hash_v1(**self._base())
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


class TestNormalizeTitular:
    def test_handles_strip_and_accent(self):
        assert normalize_titular(" David ") == normalize_titular("david")
        assert normalize_titular("Davíd") == normalize_titular("david")


class TestNormalizeTipoConta:
    def test_collapses_spaces(self):
        assert normalize_tipo_conta("Conta Corrente") == "contacorrente"

    def test_none(self):
        assert normalize_tipo_conta(None) == ""
