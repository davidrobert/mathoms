"""Orçamento do bloco ``$.if_monte_carlo`` no exec context do parecer (ADR-361).
O distiller renderiza o bloco raw e corta em ``max_chars`` de forma prefixal. Os
campos de censura tornaram o prefixo escalar maior que o cap default de 300, então
sem o knob a correção de honestidade entraria derrubando dado de domínio do
contexto do LLM — regressão silenciosa, do tipo que a ADR-360 evitou.
"""

from __future__ import annotations

import functools
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from app.services.parecer_distiller import render_block

from pipeline.domain.services.e5_serialization import monte_carlo_to_dict
from pipeline.domain.services.if_monte_carlo import IFMonteCarloConfig, run_monte_carlo_if

_MANIFEST = Path(__file__).resolve().parents[2] / "config" / "prompts" / "parecer_planejador.yaml"

# Escalares de DOMÍNIO: mudam a leitura do número, então nenhum pode ser cortado.
# `mc_version`/`seed_usado`/`n_simulacoes_usado`/`horizonte_anos` ficam de fora de
# propósito — são metadado de auditoria e vivem depois dos `caminho_*` (ADR-360).
_CAMPOS_DOMINIO = (
    "p10_ano_if",
    "p10_censurado",
    "p50_ano_if",
    "p50_censurado",
    "p90_ano_if",
    "p90_censurado",
    "prob_if_ate_idade_meta",
    "prob_if_ate_horizonte",
    "idade_meta_usada",
    "sigma_usado",
    "exibir_cone",
    "aporte_mensal_usado",
    "motivo_sem_cone",
)

# (patrimônio, meta, aporte) — os cinco estados observáveis do bloco.
_ESTADOS = [
    pytest.param("5000000", "10000000", "15000", id="cone-cheio"),
    pytest.param("2000000", "10000000", "5000", id="p90-censurado"),
    pytest.param("1500000", "10000000", "0", id="p50-e-p10-censurados"),
    pytest.param("400000", "10000000", "0", id="cone-suprimido"),
    pytest.param("11000000", "10000000", "0", id="meta-ja-atingida"),
]


@functools.lru_cache(maxsize=1)
def _bloco_manifest() -> tuple[tuple[str, object], ...]:
    """Bloco do manifest como itens hasheáveis (lru_cache: parse de YAML é caro)."""
    manifest = yaml.safe_load(_MANIFEST.read_text(encoding="utf-8"))
    blocos = [
        b
        for s in manifest["context_sections"]
        for b in s.get("blocks", [])
        if b.get("path") == "$.if_monte_carlo"
    ]
    assert blocos, "bloco $.if_monte_carlo ausente do manifest do parecer"
    return tuple(blocos[0].items())


def _render(pv: str, fv: str, pmt: str) -> str:
    cfg = IFMonteCarloConfig(
        patrimonio_investivel=Decimal(pv),
        meta_if=Decimal(fv),
        aporte_mensal=Decimal(pmt),
        ano_base=2026,
    )
    mc = run_monte_carlo_if(cfg, ano_base=2026, idade_titular_atual=40, idade_meta_if=65)
    return render_block(dict(_bloco_manifest()), {"if_monte_carlo": monte_carlo_to_dict(mc)})


@pytest.mark.parametrize("pv,fv,pmt", _ESTADOS)
def test_dado_de_dominio_do_cone_sobrevive_ao_corte(pv: str, fv: str, pmt: str):
    """Nenhum campo que muda a leitura do número é truncado do exec context."""
    renderizado = _render(pv, fv, pmt)
    assert renderizado, "bloco do cone não renderizou"
    for campo in _CAMPOS_DOMINIO:
        assert campo in renderizado, (
            f"`{campo}` caiu fora do corte de max_chars — o LLM lê o cone sem ele. "
            f"Suba `max_chars` no bloco $.if_monte_carlo do manifest."
        )


@pytest.mark.parametrize("pv,fv,pmt", _ESTADOS)
def test_flag_de_censura_segue_o_ano_que_qualifica(pv: str, fv: str, pmt: str):
    """Intercalada, então não existe janela de ano sem qualificador no prefixo."""
    renderizado = _render(pv, fv, pmt)
    for percentil in ("p10", "p50", "p90"):
        pos_ano = renderizado.index(f'"{percentil}_ano_if"')
        pos_flag = renderizado.index(f'"{percentil}_censurado"')
        assert pos_flag > pos_ano, f"{percentil}: flag deveria seguir o ano"
