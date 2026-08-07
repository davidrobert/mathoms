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
from pipeline.domain.services.if_monte_carlo import (
    IFMonteCarloConfig,
    PrazoDeclarado,
    run_monte_carlo_if,
)

_MANIFEST = Path(__file__).resolve().parents[2] / "config" / "prompts" / "parecer_planejador.yaml"

# Escalares de DOMÍNIO: mudam a leitura do número, então nenhum pode ser cortado.
# `mc_version`/`seed_usado`/`n_simulacoes_usado`/`horizonte_simulado_anos` ficam de fora de
# propósito — são metadado de auditoria e vivem depois dos `caminho_*` (ADR-360).
_CAMPOS_DOMINIO = (
    "ano_if_cenario_favoravel",
    "ano_if_cenario_favoravel_censurado",
    "ano_if_cenario_central",
    "ano_if_cenario_central_censurado",
    "ano_if_cenario_adverso",
    "ano_if_cenario_adverso_censurado",
    "prob_if_ate_prazo_declarado",
    "prazo_declarado_anos",
    "ano_alvo_declarado",
    "declarado_em",
    "prazo_declarado_truncado",
    "motivo_sem_prazo_declarado",
    "prob_if_ate_horizonte_simulado",
    "sigma_usado",
    "exibir_cone",
    "aporte_mensal_usado",
    "motivo_sem_cone",
)

_VIGENTE = PrazoDeclarado(anos=25, ano_alvo=2051, declarado_em="2026-03-01")
_VENCIDO = PrazoDeclarado(anos=3, ano_alvo=2023, declarado_em="2020-05-01")

# (patrimônio, meta, aporte, prazo) — os estados observáveis do bloco.
_ESTADOS = [
    pytest.param("5000000", "10000000", "15000", _VIGENTE, id="cone-cheio"),
    pytest.param("2000000", "10000000", "5000", _VIGENTE, id="adverso-censurado"),
    pytest.param("1500000", "10000000", "0", _VIGENTE, id="central-e-favoravel-censurados"),
    pytest.param("400000", "10000000", "0", _VIGENTE, id="cone-suprimido"),
    pytest.param("11000000", "10000000", "0", _VIGENTE, id="meta-ja-atingida"),
    pytest.param("5000000", "10000000", "15000", None, id="prazo-nao-declarado"),
    # A40.l28 PR-B — o PIOR caso não é nenhum dos cinco acima isolado: é cone
    # suprimido COM prazo vencido, que põe `motivo_sem_cone` e
    # `motivo_sem_prazo_declarado` (as duas strings longas) no mesmo payload.
    # Medido: 613 sem o prazo vencido, 633 com ele. Sem este estado o gate
    # ficaria verde com `max_chars` calibrado 20 chars curto demais.
    pytest.param("400000", "10000000", "0", _VENCIDO, id="pior-caso-dois-motivos"),
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


def _render(pv: str, fv: str, pmt: str, prazo: PrazoDeclarado | None) -> str:
    cfg = IFMonteCarloConfig(
        patrimonio_investivel=Decimal(pv),
        meta_if=Decimal(fv),
        aporte_mensal=Decimal(pmt),
        ano_base=2026,
    )
    mc = run_monte_carlo_if(cfg, ano_base=2026, prazo_declarado=prazo)
    return render_block(dict(_bloco_manifest()), {"if_monte_carlo": monte_carlo_to_dict(mc)})


@pytest.mark.parametrize("pv,fv,pmt,prazo", _ESTADOS)
def test_dado_de_dominio_do_cone_sobrevive_ao_corte(pv, fv, pmt, prazo):
    """Nenhum campo que muda a leitura do número é truncado do exec context."""
    renderizado = _render(pv, fv, pmt, prazo)
    assert renderizado, "bloco do cone não renderizou"
    for campo in _CAMPOS_DOMINIO:
        assert campo in renderizado, (
            f"`{campo}` caiu fora do corte de max_chars — o LLM lê o cone sem ele. "
            f"Suba `max_chars` no bloco $.if_monte_carlo do manifest."
        )


@pytest.mark.parametrize("pv,fv,pmt,prazo", _ESTADOS)
def test_flag_de_censura_segue_o_ano_que_qualifica(pv, fv, pmt, prazo):
    """Intercalada, então não existe janela de ano sem qualificador no prefixo."""
    renderizado = _render(pv, fv, pmt, prazo)
    for cenario in ("favoravel", "central", "adverso"):
        pos_ano = renderizado.index(f'"ano_if_cenario_{cenario}"')
        pos_flag = renderizado.index(f'"ano_if_cenario_{cenario}_censurado"')
        assert pos_flag > pos_ano, f"{cenario}: flag deveria seguir o ano"
