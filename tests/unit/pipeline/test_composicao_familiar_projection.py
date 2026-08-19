"""Projeção civil da família no E5 (PE-3 · r7) — PII garantida no produtor.

O bloco existe para dar ao parecer o lado CIVIL do domicílio, que faltava: com
só a contagem fiscal (``$.irpf_kpis.dependentes``) o modelo emitia os dois lados
da mesma família com confianças incompatíveis. A garantia de PII é estrutural —
o produtor deriva faixa etária e nunca emite idade nem data de nascimento.
"""

from __future__ import annotations

import json
import re
from datetime import date

import pytest

from pipeline.domain.services.composicao_familiar import (
    FAIXAS_ETARIAS,
    PAPEIS,
    build_composicao_familiar,
)
from pipeline.domain.services.e5_analyzer_adapter import _faixa_ref_fiscal
from pipeline.domain.services.protecao_analyzer import FamilyMemberSnapshot

FAIXA_REF = "2024-12-31"
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _snap(parentesco: str, idade: int | None) -> FamilyMemberSnapshot:
    return FamilyMemberSnapshot(parentesco=parentesco, idade=idade)


def _build(*snaps: FamilyMemberSnapshot) -> dict:
    out = build_composicao_familiar(snaps, faixa_ref=FAIXA_REF)
    assert out is not None
    return out


class TestPIIZero:
    def test_nenhuma_data_iso_fora_de_faixa_ref(self):
        """G2: a única data no bloco é ``faixa_ref``. DOB nunca sai do produtor."""
        out = _build(_snap("titular", 41), _snap("filho", 8))
        serialized = json.dumps(out["membros"], ensure_ascii=False)
        assert _ISO_DATE.search(serialized) is None
        assert _ISO_DATE.fullmatch(out["faixa_ref"])

    def test_membro_nao_carrega_idade_nem_nascimento(self):
        out = _build(_snap("titular", 41))
        assert set(out["membros"][0]) == {"papel", "faixa_etaria"}

    def test_chaves_do_bloco_sao_fechadas(self):
        assert set(_build(_snap("titular", 41))) == {"faixa_ref", "fonte", "membros"}


class TestEnumFaixaEtaria:
    @pytest.mark.parametrize(
        "idade,esperado",
        [
            (0, "0-17"),
            (17, "0-17"),
            (18, "18-21"),
            (21, "18-21"),
            (22, "22-24"),
            (24, "22-24"),
            (25, "25-59"),
            (59, "25-59"),
            (60, "60+"),
            (95, "60+"),
        ],
    )
    def test_fronteiras_de_decisao(self, idade, esperado):
        """Cortes em 18/22/25/60 (Lei 9.250/95 art. 35; RIR/2018 art. 71 §1º)."""
        assert _build(_snap("filho", idade))["membros"][0]["faixa_etaria"] == esperado

    def test_idade_ausente_vira_desconhecida_e_nao_some(self):
        """``_idade_em`` devolve None sem data de nascimento; omitir o membro o
        tornaria invisível ao parecer."""
        out = _build(_snap("filho", None))
        assert out["membros"][0]["faixa_etaria"] == "desconhecida"
        assert len(out["membros"]) == 1

    def test_todas_as_faixas_emitidas_estao_no_enum(self):
        out = _build(*(_snap("filho", i) for i in (None, 0, 19, 23, 40, 70)))
        assert {m["faixa_etaria"] for m in out["membros"]} <= set(FAIXAS_ETARIAS)


class TestEnumPapel:
    def test_papel_desconhecido_vira_outro_dependente(self):
        """``family_members`` é editável pelo dono e tem texto livre na natureza:
        pass-through do parentesco vazaria PII para o exec context."""
        assert _build(_snap("sobrinha-neta do titular", 9))["membros"][0]["papel"] == (
            "outro_dependente"
        )

    def test_default_legado_dependente_outro_normaliza(self):
        """``_snapshot_membro`` emite ``dependente_outro`` quando não há papel."""
        assert _build(_snap("dependente_outro", 9))["membros"][0]["papel"] == "outro_dependente"

    def test_papeis_reconhecidos_sao_preservados(self):
        snaps = [_snap(p, 30) for p in PAPEIS]
        assert [m["papel"] for m in _build(*snaps)["membros"]] == list(PAPEIS)

    def test_papel_normaliza_caixa_e_espaco(self):
        assert _build(_snap("  Conjuge ", 40))["membros"][0]["papel"] == "conjuge"

    def test_todos_os_papeis_emitidos_estao_no_enum(self):
        out = _build(_snap("titular", 41), _snap("primo", 30), _snap("", None))
        assert {m["papel"] for m in out["membros"]} <= set(PAPEIS)


class TestOrdemEBlocoAusente:
    def test_ordem_estavel_titular_conjuge_demais(self):
        out = _build(_snap("filho", 8), _snap("conjuge", 40), _snap("titular", 41))
        assert [m["papel"] for m in out["membros"]] == ["titular", "conjuge", "filho"]

    def test_ordem_de_entrada_preservada_dentro_do_mesmo_papel(self):
        out = _build(_snap("filho", 8), _snap("filho", 19))
        assert [m["faixa_etaria"] for m in out["membros"]] == ["0-17", "18-21"]

    def test_sem_membros_devolve_none(self):
        """``on_null: skip`` no manifest — bloco ausente em vez de vazio."""
        assert build_composicao_familiar((), faixa_ref=FAIXA_REF) is None

    def test_faixa_ref_e_ecoada_no_bloco(self):
        assert _build(_snap("titular", 41))["faixa_ref"] == FAIXA_REF


class TestFaixaRefFiscal:
    """A data de corte é regra de domínio, não conveniência (ADR-397 D3). Tem
    teste próprio porque o snapshot do view-model mascara ``faixa_ref``: sem
    IRPF ela deriva de ``date.today()`` e viraria na passagem de ano."""

    def _irpf(self, anos: dict[int, tuple]):
        class _FakeIRPF:
            def estados_completude(self, today=None):
                return anos

        return _FakeIRPF()

    def test_usa_31_12_do_ano_base_do_irpf(self):
        from pipeline.domain.services.irpf_completude import CompletudeAno

        irpf = self._irpf({2024: (CompletudeAno.completo, None)})
        assert _faixa_ref_fiscal(irpf, date(2026, 8, 19)) == date(2024, 12, 31)

    def test_sem_irpf_cai_no_ultimo_ano_calendario_fechado(self):
        """Relógio no passado: subestimar idade é a direção conservadora — nunca
        envelhece um membro para além do que o ano declarado sustentaria."""
        assert _faixa_ref_fiscal(None, date(2026, 8, 19)) == date(2025, 12, 31)

    def test_irpf_sem_ano_base_resolvivel_cai_no_fallback(self):
        assert _faixa_ref_fiscal(self._irpf({}), date(2026, 3, 1)) == date(2025, 12, 31)

    def test_nao_usa_a_data_do_run(self):
        """Recortar em ``today`` produz falso positivo para quem completou 22 (ou
        25) entre 1º de janeiro e o dia do run."""
        from pipeline.domain.services.irpf_completude import CompletudeAno

        irpf = self._irpf({2024: (CompletudeAno.completo, None)})
        ref = _faixa_ref_fiscal(irpf, date(2026, 8, 19))
        assert ref.year != 2026 and (ref.month, ref.day) == (12, 31)
