"""Honestidade do cone de IF: cone não-citável + procedência do sigma (A40.l25)."""
# Duas faces da mesma classe — número que afirma precisão ou procedência que
# não tem. Residual nomeado por ADR-360 §Deferimento 1 e ADR-361 §Deferimento 5.

from __future__ import annotations

from decimal import Decimal

import pytest
from app.services.parecer_citation_catalog import build_citation_catalog

from pipeline.domain.services.if_monte_carlo import (
    IFMonteCarloConfig,
    run_monte_carlo_if,
)
from pipeline.domain.services.if_monte_carlo_payload import monte_carlo_to_dict

CONE_KEYS = ("caminho_p10", "caminho_p50", "caminho_p90")


def _payload_com_cone() -> dict:
    return {
        "if_monte_carlo": {
            "caminho_p10": [[2026, 11037269.90], [2027, 11500000.0]],
            "caminho_p50": [[2026, 12000000.0]],
            "caminho_p90": [[2026, 14000000.0]],
            "valor_final_p50": 12000000.0,
        }
    }


@pytest.mark.parametrize("whitelist", [frozenset({"S7"}), frozenset({"if_monte_carlo"})])
def test_cone_nao_produz_ancora_de_citacao(whitelist: frozenset[str]) -> None:
    """O parecer não pode citar valor de cone: ±1,2% de dispersão amostral."""
    catalog = build_citation_catalog(_payload_com_cone(), section_whitelist=whitelist)
    assert [e.path for e in catalog if "caminho_p" in e.path] == []


def test_exclusao_e_decisao_nao_acidente() -> None:
    """Se a folha virar citável por mudança no predicado, o gate ainda barra."""
    # Mutação plausível: alguém faz `_is_money_leaf` casar lista de pares. Este
    # teste força o caminho de exclusão explícito em vez de depender do acidente.
    from app.services import parecer_citation_catalog as cat

    assert set(CONE_KEYS) <= cat._NAO_CITAVEL_ESTIMATIVA
    paths = list(cat._leaf_paths_for("caminho_p50", [[2026, 12000000.0]], "$.if_monte_carlo"))
    assert paths == [], "cone virou citável — precisão inventada sobre projeção"


def _run(**kwargs) -> object:
    config = IFMonteCarloConfig(
        patrimonio_investivel=Decimal("1000000"),
        meta_if=Decimal("3000000"),
        aporte_mensal=Decimal("10000"),
        **kwargs,
    )
    return run_monte_carlo_if(config, ano_base=2026)


def test_sigma_declara_procedencia_de_fallback() -> None:
    """Sem premissa vigente o payload DECLARA a constante em vez de insinuar auditoria."""
    payload = monte_carlo_to_dict(_run())
    assert payload["sigma_usado"] == 0.11
    assert payload["sigma_procedencia"] == "fallback_codigo"


def test_procedencia_acompanha_quem_passa_a_premissa() -> None:
    """Quem passar sigma de premissa vigente carimba a origem — o campo não é constante."""
    payload = monte_carlo_to_dict(_run(sigma_anual=0.09, sigma_procedencia="workspace_override"))
    assert (payload["sigma_usado"], payload["sigma_procedencia"]) == (0.09, "workspace_override")


def test_sigma_por_perfil_nao_existe_mais() -> None:
    """Dead code que parece configuração é pior que ausência (critério da lane)."""
    from pipeline.domain.services import if_monte_carlo

    assert not hasattr(if_monte_carlo, "_SIGMA_POR_PERFIL")
