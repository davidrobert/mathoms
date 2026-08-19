"""Projeção da fonte documental de seguro no bundle (A40.l73 · ADR-395 §D2/§D6)."""

from __future__ import annotations

from pipeline.domain.services.documentary_coverage import documentary_coverage_from_payload


def _payload(**overrides) -> dict:
    base = {
        "apolices_vigentes": [
            {
                "apolice_numero": "AP-1",
                "seguradora": "seguradora_alfa",
                "seguradora_nome": "Seguradora Alfa",
                "vigencia_inicio": "2026-01-01",
                "vigencia_fim": "2027-03-31",
            }
        ],
        "escopo_cobertura": {"categorias_somente_no_documento": ["vida"]},
    }
    base.update(overrides)
    return base


def test_payload_ausente_nao_projeta_fonte_documental():
    assert documentary_coverage_from_payload(None) is None
    assert documentary_coverage_from_payload({}) is None


def test_conta_apolices_vigentes_e_nomeia_seguradoras():
    projecao = documentary_coverage_from_payload(_payload())
    assert projecao is not None
    assert projecao["active_policies_count"] == 1
    assert projecao["insurers"] == ["Seguradora Alfa"]
    assert projecao["earliest_coverage_end"] == "2027-03-31"


def test_categoria_documental_vira_categoria_do_bundle():
    projecao = documentary_coverage_from_payload(_payload())
    assert projecao is not None
    assert projecao["unconfirmed_categories"] == ["vida"]


def test_categoria_documental_sem_par_no_bundle_nao_retem_nada():
    """`saude` existe no vocabulário documental e não é categoria do bundle."""
    projecao = documentary_coverage_from_payload(
        _payload(escopo_cobertura={"categorias_somente_no_documento": ["saude"]})
    )
    assert projecao is not None
    assert projecao["unconfirmed_categories"] == []
    assert projecao["active_policies_count"] == 1


def test_apolice_de_bem_sem_categoria_pessoal_ainda_conta_como_fonte():
    """Auto/residencial não retém gap, mas desmente "sem riscos cadastrados"."""
    projecao = documentary_coverage_from_payload(
        _payload(escopo_cobertura={"categorias_somente_no_documento": []})
    )
    assert projecao is not None
    assert projecao["unconfirmed_categories"] == []
    assert projecao["active_policies_count"] == 1


def test_seguradora_sem_nome_de_catalogo_cai_no_code():
    projecao = documentary_coverage_from_payload(
        _payload(
            apolices_vigentes=[
                {"seguradora": "seguradora_beta", "vigencia_fim": "2026-12-31"},
                {"seguradora": "seguradora_beta", "vigencia_fim": "2027-01-31"},
            ]
        )
    )
    assert projecao is not None
    assert projecao["insurers"] == ["seguradora_beta"]
    assert projecao["earliest_coverage_end"] == "2026-12-31"


def test_vigencia_vazia_nao_vira_data_fabricada():
    projecao = documentary_coverage_from_payload(
        _payload(apolices_vigentes=[{"seguradora": "seguradora_beta", "vigencia_fim": ""}])
    )
    assert projecao is not None
    assert projecao["earliest_coverage_end"] is None
