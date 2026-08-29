"""Gate de conservação do E7 (A36.l3): violação de conservação pausa o run.

`validate_cross` passa a emitir `validation.valid` gatilhando num conjunto
EXPLÍCITO de checks de conservação ({CV1,CV2,CV3,CV6}), não em `severity=="error"`
genérico — porque CV9/CV10 (render) são `error` e falham em run incremental,
o que pausaria 100% dos runs (medição A36.l3). Estes testes travam: (a) o gate
dispara na conservação, (b) render não derruba o gate, (c) o bloco flui por
`main_with_store` até o `result["validation"]` que o loop de pipeline consome.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.stages import validate_cross as stage
from scripts.validate_cross import (
    _REQUIRED_CHARTS,
    CrossValidationResult,
    _conservation_validation,
)


def _r(check_id: str, passed: bool) -> CrossValidationResult:
    return CrossValidationResult(check_id, check_id, "warning", passed, "", [])


# ── unit puro sobre o helper (load-bearing: decouple render × conservação) ──


def test_conservacao_falha_pausa() -> None:
    v = _conservation_validation([_r("CV2", False), _r("CV9", True)])
    assert v["valid"] is False
    assert any("CV2" in e for e in v["errors"])


def test_render_falho_nao_pausa() -> None:
    """CV10 (render) reprovado NÃO derruba o gate — a lição da medição A36.l3."""
    v = _conservation_validation([_r("CV10", False), _r("CV4", False), _r("CV2", True)])
    assert v["valid"] is True
    assert v["errors"] == []


def test_conservacao_limpa_valida() -> None:
    v = _conservation_validation([_r(c, True) for c in ("CV1", "CV2", "CV3", "CV6")])
    assert v["valid"] is True


# ── stage-level: o bloco flui por main_with_store até result["validation"] ──


def _e5(*, bruto, comp_valor) -> dict:
    return {
        "narrativas": {
            "summaries": {f"s{i}": "x" for i in range(1, 11)},
            "charts": {c: {"context": "c", "conclusion": "f"} for c in _REQUIRED_CHARTS},
        },
        "score": {"valor": 0},
        "patrimonio": {"bruto": bruto, "composicao": [{"valor": comp_valor}]},
    }


def _ctx(tmp_path: Path, store: InMemoryArtifactStore) -> WorkspaceContext:
    (tmp_path / "config").mkdir(exist_ok=True)
    return WorkspaceContext(root=tmp_path, artifact_store=store)


def test_stage_pausa_em_conservacao_violada(tmp_path: Path) -> None:
    """CV2: composição 1200 vs bruto 1000 (20% > 5%) → validation.valid False."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _e5(bruto=1000.0, comp_valor=1200.0))
    result = stage.run(_ctx(tmp_path, store))
    assert result["success"] is True  # rodou sem crashar
    assert result["validation"]["valid"] is False
    assert any("CV2" in e for e in result["validation"]["errors"])


def test_stage_run_limpo_valido(tmp_path: Path) -> None:
    """Composição bate com bruto → conservação ok → validation.valid True."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _e5(bruto=1000.0, comp_valor=1000.0))
    result = stage.run(_ctx(tmp_path, store))
    assert result["validation"]["valid"] is True


# ── CV18 observado disparando: a evidência que o §r10 declarou fraca ──
#
# O PV10-01 leu o predicado no código e nunca o viu reprovar num run. Aqui ele é
# observado ATRAVESSANDO o stage: reprova, chega ao payload como `errors_count`,
# e — o que muda a leitura do PV10-03 — **não pausa**, porque CV18 está fora de
# `_CONSERVATION_CHECKS`. Um `severity="error"` que não gateia é exatamente o que
# a linha de resumo "17/17 OK" conflaciona com gate.


def _e5_cambial(*, tier: str, carteira_apurada: bool = False) -> dict:
    cobertura = "apurado" if carteira_apurada else "indeterminado"
    e5 = _e5(bruto=1000.0, comp_valor=1000.0)
    e5["exposicao_cambial"] = {
        "componentes": {
            "caixa_fx": {"valor_brl": 100.0, "cobertura": "apurado"},
            "carteira_lastro_estrangeiro": {"valor_brl": 0.0, "cobertura": cobertura},
        },
        "total_brl": 100.0,
        "tier": tier,
    }
    return e5


def test_stage_cv18_reprova_veredito_forte_demais(tmp_path: Path) -> None:
    """Banda afirmada sobre cobertura incompleta: CV18 falha `error` no run inteiro."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _e5_cambial(tier="verde"))
    result = stage.run(_ctx(tmp_path, store))

    cv18 = next(r for r in result["results"] if r["check_id"] == "CV18")
    assert cv18["passed"] is False
    assert cv18["severity"] == "error"
    assert result["errors_count"] == 1


def test_stage_cv18_reprovado_nao_pausa_o_run(tmp_path: Path) -> None:
    """CV18 é advisory: reprova e o run segue. Medido, não inferido do código."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _e5_cambial(tier="verde"))
    result = stage.run(_ctx(tmp_path, store))

    assert result["validation"]["valid"] is True
    assert result["validation"]["errors"] == []


def test_stage_cv18_passa_no_estado_sancionado_da_v1(tmp_path: Path) -> None:
    """Cobertura incompleta + veredito suprimido é o run de produção — verde."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _e5_cambial(tier="indeterminado"))
    result = stage.run(_ctx(tmp_path, store))

    cv18 = next(r for r in result["results"] if r["check_id"] == "CV18")
    assert cv18["passed"] is True
    assert result["errors_count"] == 0
