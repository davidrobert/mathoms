"""X7 — o teto de iteracoes de tool conta a MESMA populacao que o emissor."""

# `LC9-10` (`U5`): o run publicou `tool_iterations: 19` contra
# `max_tool_iterations: 6` — estourado 3,2x, sem alarme e sem contradicao. Nao ha
# defeito no run: emissor e teto contam coisas DIFERENTES.
#
#   emissor  `PlannerDrillDown.iterations_count` = TODA invocacao de tool na
#            instancia, inclusive cache hit e o estampamento pos-LLM de ancoras e
#            metricas (ADR-296 / ADR-399). Cresce com o tamanho do parecer.
#   teto     `max_tool_iterations` do manifesto = round-trips LLM->tool->LLM,
#            que e o que a [[ADR-203]] §D2 dimensionou.
#
# A semantica canonica ja estava decidida (OBS-1 · A37.l1 · [[ADR-341]]: "telemetria,
# NAO o cap"); quem nao a acompanhou foi o schema do artefato, que anotava
# `maximum: 6` no campo do EMISSOR. Este check mede as duas populacoes e da o
# veredito sobre a que o teto governa — hoje VAZIA, porque o modelo nao recebe
# tools (`LLMService.call` nao tem parametro `tools`; `PV9-25`/`RV4-43`).

from __future__ import annotations

import inspect
import json

from dev._unified_xchecks.base import veredito


def _modelo_tem_tools() -> bool | None:
    """O caminho de LLM do parecer pode receber tools? ``None`` ≡ ilegivel.

    Oraculo por ASSINATURA, nao por leitura de docstring: o `RV4-43` nasceu de
    inferir afordance de comentario. Se alguem ligar tools, isto vira `True`
    sozinho e o teto passa a governar populacao nao-vazia.
    """
    try:
        from pipeline.llm.litellm_client import LLMService

        return "tools" in inspect.signature(LLMService.call).parameters
    except Exception:
        return None


def _fases(trace: list) -> dict[str, int]:
    """Reparticao do trace por fase declarada pelo emissor.

    O trace de hoje NAO carrega marca de fase — `ToolTraceEntry` tem
    `iter/tool/input/result_summary/latency_ms/cache_hit` e mais nada. Enquanto
    o modelo nao tem tools, `pos_llm` e a fase de todas por deducao estrutural
    (nao ha outro emissor possivel). No dia em que tools existirem, a atribuicao
    post-hoc deixa de ser derivavel e o check tem de DIZER isso — nao chutar.
    """
    return {
        "total": len(trace),
        "cache_hit": sum(1 for e in trace if (e or {}).get("cache_hit")),
        "com_marca_de_fase": sum(1 for e in trace if (e or {}).get("fase")),
    }


def _teto_do_manifesto() -> int | None:
    try:
        from backend.app.services.parecer_manifest import load_manifest

        return int(load_manifest().max_tool_iterations)
    except Exception:
        return None


def _indeterminado(motivo: str, n_esperado: int) -> None:
    print(f"  INDETERMINADO: {motivo}")
    veredito("X7", 0, n_esperado, 0, n_falsificavel=0, nota=motivo)


def x7(ws: str, run: str, parecer_path: str) -> None:
    """Teto de iteracoes de tool contra a populacao que o emissor de fato conta."""
    meta = (json.load(open(parecer_path)) or {}).get("_meta") or {}
    emitido = int(meta.get("tool_iterations") or 0)
    trace = meta.get("tool_trace") or []
    fases, teto, tem_tools = _fases(trace), _teto_do_manifesto(), _modelo_tem_tools()
    print("## X7 — teto de iteracoes de tool vs populacao do emissor")
    print(f"emissor `tool_iterations`: {emitido} · entries no trace: {fases['total']}")
    print(f"  cache_hit: {fases['cache_hit']} · com marca de fase: {fases['com_marca_de_fase']}")
    print(f"teto `max_tool_iterations` (manifesto): {teto} · modelo recebe tools: {tem_tools}")
    if teto is None or tem_tools is None:
        _indeterminado("manifesto ou cliente LLM ilegivel — teto nao verificavel", emitido)
        return
    if tem_tools:
        _indeterminado(
            "o modelo passou a receber tools e o trace nao marca fase: round-trip "
            "deixou de ser derivavel post-hoc. Emitir `fase` antes de voltar a medir",
            emitido,
        )
        return
    print(
        f"round-trips iniciados pelo modelo: 0 (estrutural — `LLMService.call` nao "
        f"aceita `tools`) · as {emitido} sao estampagem pos-LLM"
    )
    veredito(
        "X7",
        emitido,
        emitido,
        0,
        n_falsificavel=0,
        nota=(
            f"o teto {teto} governa round-trips; o emissor conta invocacoes. Populacao "
            "do teto VAZIA ⇒ nenhum valor de `tool_iterations` pode viola-lo, e "
            "`19 > 6` nao e achado. Isto e resultado, nao ausencia de medicao"
        ),
    )
