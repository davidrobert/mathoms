"""FP-2 D1-A — sob base de comparação alterada o changelog recolhe o juízo.

O produtor do payload é quem corrige: a V0 já neutraliza a CÉLULA
(`VariacaoSection.tsx`), mas o `changelog[]` continuava publicando
`delta_signal="down"` sobre um par cujas pontas foram consolidadas por métodos
diferentes. Gate visual não vê texto, e o payload é o que outra camada lê.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.schemas.snapshot_changelog import (
    ChangelogEntryRead,
    neutralize_changelog_base_changed,
)


def _entry(signal: str = "down", pct: Decimal | None = Decimal("12.5")) -> ChangelogEntryRead:
    return ChangelogEntryRead(
        section_id="M_PL",
        summary="Patrimônio líquido recuou R$ 1.000,00 desde o relatório anterior (−12,5%)",
        delta_signal=signal,
        delta_pct=pct,
    )


class TestNeutralizeChangelogBaseAlterada:
    def test_delta_signal_vira_nao_comparavel(self):
        (out,) = neutralize_changelog_base_changed([_entry()])
        assert out.delta_signal == "nao_comparavel"

    def test_marca_comparabilidade_base_alterada(self):
        (out,) = neutralize_changelog_base_changed([_entry()])
        assert out.comparabilidade == "base_alterada"

    def test_delta_pct_continua_publicado(self):
        """Some o juízo, não o número — o delta segue auditável."""
        (out,) = neutralize_changelog_base_changed([_entry()])
        assert out.delta_pct == pytest.approx(12.5)

    def test_summary_carrega_a_ressalva(self):
        """Sem isso a prosa afirma 'recuou … desde o relatório anterior' dentro de
        um objeto que declara `nao_comparavel` — as duas metades se contradizem."""
        (out,) = neutralize_changelog_base_changed([_entry()])
        assert "base de comparação alterada" in out.summary

    def test_default_do_dto_e_comparavel(self):
        """Payload sem base alterada não ganha marcador — o campo é diferença."""
        assert _entry().comparabilidade == "comparavel"

    def test_lista_vazia_nao_explode(self):
        assert neutralize_changelog_base_changed([]) == []


# ─── Call-site: o endpoint aplica a regra (regra certa em função não chamada é inerte) ───


_PREV_BASE_A = {
    "periodo_dados": "202601-202603",
    "patrimonio": {"liquido": 1_000_000.0, "bruto": 1_200_000.0},
    "ratios": {"taxa_poupanca_recorrente_pct": 20.0},
    "fluxo_caixa": {"consolidacao_cross_documento": False},
}
_CURR_BASE_B = {
    "periodo_dados": "202602-202604",
    "patrimonio": {"liquido": 1_400_000.0, "bruto": 1_600_000.0},
    "ratios": {"taxa_poupanca_recorrente_pct": 31.0},
    "fluxo_caixa": {"consolidacao_cross_documento": True},
}
_CURR_MESMA_BASE = {**_CURR_BASE_B, "fluxo_caixa": {"consolidacao_cross_documento": False}}


async def _changelog_do_par(auth_client, tmp_path, db, curr: dict) -> list[dict]:
    from backend.tests.test_reports import _seed_report

    await _seed_report(auth_client, analysis_payload=_PREV_BASE_A, tmp_path=tmp_path, db=db)
    rid = await _seed_report(auth_client, analysis_payload=curr, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["changelog"], "par sem entrada de changelog não mede nada"
    return body["changelog"]


@pytest.mark.asyncio
async def test_endpoint_neutraliza_changelog_sob_base_alterada(auth_client, tmp_path, db):
    entries = await _changelog_do_par(auth_client, tmp_path, db, _CURR_BASE_B)
    assert {e["delta_signal"] for e in entries} == {"nao_comparavel"}
    assert {e["comparabilidade"] for e in entries} == {"base_alterada"}
    assert all(e["delta_pct"] is not None for e in entries)


@pytest.mark.asyncio
async def test_endpoint_preserva_juizo_quando_a_base_nao_muda(auth_client, tmp_path, db):
    """Polaridade: sem base alterada o sinal continua sendo emitido."""
    entries = await _changelog_do_par(auth_client, tmp_path, db, _CURR_MESMA_BASE)
    assert "nao_comparavel" not in {e["delta_signal"] for e in entries}
    assert {e["comparabilidade"] for e in entries} == {"comparavel"}
