"""Camada E3 do colapso cross-documento ([[ADR-354]] §Emenda) — instrumento da [[A40.l2]].

O detector da [[A40.l1]] (`ledger_cross_group`) varre os **baldes E4**; o colapsador
que corrige o defeito opera nos **statements E3**, pré-agrupamento. São populações
diferentes por construção, então "o numerador E4 caiu a 0" **não** certifica o que o
enforce fez em E3 — medido em 2026-08-05, 70 de 331 chaves colapsáveis ficam fora do
campo de visão do detector, carregando 58% dos cents.

Este módulo conta a camada E3 ao lado do numerador E4 e fecha a **paridade exata por
digest**: os dois instrumentos derivam a chave com
``sha256("|".join(str(p) for p in key))`` sobre tuplas de conteúdo idêntico, com
truncamentos diferentes — então comparar por prefixo é exato, não aproximado. O
comprimento é **derivado** do detector, nunca constante literal.

Os campos que produção também emite vêm de ``shadow_counts`` (domínio), **nunca**
recomputados aqui. A direção da dependência é essa e não a inversa: este instrumento existe
para PROVAR a telemetria de produção — se calculasse por conta própria, provaria a si mesmo.
Derivação paralela da mesma regra é o bug do ``keep_split``: duas cópias concordavam na
fixture, divergiam no corpus, e o measure declarava 453 enquanto a mutação removia 593.

PII-safe: só contagens, cents agregados e nomes de motivo. Puro, sem I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.domain.services.cross_document_collapse_types import shadow_counts


@dataclass(frozen=True)
class CollapseLayerSummary:
    """Camada E3 JÁ PARTICIONADA — não existe campo com "total sem partição"."""

    candidatos: int = 0
    colapsaveis: int = 0
    bloqueados_por_motivo: dict[str, int] = field(default_factory=dict)
    rows_removiveis: int = 0
    # Rows que o ALVO emitido resolve. Diverge de `rows_removiveis` quando o alvo pede
    # remoção parcial de um bucket — e é a divergência que o gate tem de ver, porque um
    # consumidor que apaga por conjunto de hash removeria a mais.
    rows_alcancadas: int = 0
    candidatos_com_alvo_ambiguo: int = 0
    cents_removiveis: int = 0
    cardinalidade: dict[int, int] = field(default_factory=dict)
    # Paridade exata contra o numerador do detector E4.
    em_ambos: int = 0
    so_no_detector: int = 0
    so_no_colapsador: int = 0
    orfas_rows: int = 0
    orfas_cents: int = 0
    digest_len: int = 0

    @property
    def bloqueados(self) -> int:
        return sum(self.bloqueados_por_motivo.values())

    @property
    def particao_fecha(self) -> bool:
        """Identidade 1 — **auto-consistente**: pega filtro ASSIMÉTRICO dentro do
        sumário, não cap sobre a lista de entrada (reduziria os dois lados)."""
        # Mesma classe da identidade interna da [[A40.l1]]: fecha com qualquer piso.
        # Quem trava cap na entrada é `test_summary_nao_capa_nem_filtra_a_entrada`,
        # que ancora as contagens FORA do sumário.
        return self.colapsaveis + self.bloqueados == self.candidatos

    @property
    def paridade_fecha(self) -> bool:
        """Identidade 2 — **externa**: cruza com os digests do detector, conjunto que
        este módulo não produz. É a que pega colisão de prefixo e undercount."""
        return self.em_ambos + self.so_no_colapsador == self.colapsaveis

    @property
    def cardinalidade_fecha(self) -> bool:
        """Identidade 3 — auto-consistente como a 1; pega cap no histograma."""
        return sum(self.cardinalidade.values()) == self.colapsaveis

    @property
    def alvo_enderecavel(self) -> bool:
        """Rows que o alvo resolve == rows declaradas. **Reportado, não gateado.**"""
        # Retirado de `layer_ok` em 2026-08-05 (critério do senior-cto). Não é uma
        # propriedade de LEGIBILIDADE do instrumento — é dano contrafactual de um
        # consumidor que apaga por CONJUNTO de hash. Fundir as duas naturezas deixava a
        # legibilidade refém de uma decisão de produto, que é a ADR-342 invertida.
        #
        # A retirada passou os 4 critérios do senior-cto; o registro completo, com a
        # evidência de cada um, está na §Critério de aceite da [[A40.l2]].
        return self.rows_alcancadas == self.rows_removiveis

    @property
    def sem_ponto_cego(self) -> bool:
        """Detector ⊆ colapsador. Falso ⇒ o colapsador NÃO cobre o que o gate mede."""
        return self.so_no_detector == 0

    @property
    def layer_ok(self) -> bool:
        """Token grepável — falso ⇒ os números desta camada não são legíveis."""
        return self.particao_fecha and self.paridade_fecha and self.cardinalidade_fecha


def _digest_len(digests: frozenset[str]) -> int:
    """Comprimento ÚNICO dos digests do detector; heterogêneo é erro, não warning."""
    lens = {len(d) for d in digests}
    if len(lens) > 1:
        raise ValueError(f"digests do detector com comprimentos distintos: {sorted(lens)}")
    return lens.pop() if lens else 0


def _parity(detector_digests: frozenset[str], colapsaveis: list, todos: list) -> dict:
    """Paridade por prefixo de digest — comprimento derivado, nunca literal."""
    n = _digest_len(detector_digests)
    if not n:
        return {"em_ambos": 0, "so_no_detector": 0, "so_no_colapsador": len(colapsaveis)}
    col_ok = {c.key_digest[:n] for c in colapsaveis}
    col_todos = {c.key_digest[:n] for c in todos}
    return {
        "em_ambos": len(detector_digests & col_ok),
        # Contra TODOS os candidatos: chave que o colapsador viu mas bloqueou não é
        # ponto cego de cobertura — é decisão de predicado.
        "so_no_detector": len(detector_digests - col_todos),
        "so_no_colapsador": len(col_ok - detector_digests),
    }


def _orfas(detector_digests: frozenset[str], colapsaveis: list, n: int) -> tuple[int, int]:
    """``(rows, cents)`` das chaves colapsáveis que o detector não vê."""
    if not n:
        return (
            sum(c.removable_rows for c in colapsaveis),
            sum(c.valor_cents * c.removable_rows for c in colapsaveis),
        )
    orfas = [c for c in colapsaveis if c.key_digest[:n] not in detector_digests]
    return (
        sum(c.removable_rows for c in orfas),
        sum(c.valor_cents * c.removable_rows for c in orfas),
    )


def _histograma(valores) -> dict:
    out: dict = {}
    for v in valores:
        out[v] = out.get(v, 0) + 1
    return out


def _motivos(todos: list) -> dict:
    return _histograma(c.blocked_reason or "sem_motivo" for c in todos if not c.collapsible)


def _proprios(colapsaveis: list, detector_digests: frozenset[str], n: int) -> dict:
    """Campos que só este instrumento produz — o resto vem de ``shadow_counts``."""
    orfas_rows, orfas_cents = _orfas(detector_digests, colapsaveis, n)
    return {
        "rows_alcancadas": sum(c.rows_alcancadas_por_hash for c in colapsaveis),
        "cardinalidade": _histograma(c.survivor_cardinality for c in colapsaveis),
        "orfas_rows": orfas_rows,
        "orfas_cents": orfas_cents,
        "digest_len": n,
    }


def collapse_layer_summary(candidates, detector_digests: frozenset[str]) -> CollapseLayerSummary:
    """Sumário da camada E3 + paridade contra o numerador do detector E4."""
    todos = list(candidates)
    colapsaveis = [c for c in todos if c.collapsible]
    base = shadow_counts(todos)
    n = _digest_len(detector_digests)
    return CollapseLayerSummary(
        candidatos=base["candidatos"],
        colapsaveis=base["colapsaveis"],
        bloqueados_por_motivo=_motivos(todos),
        rows_removiveis=base["rows_removiveis"],
        candidatos_com_alvo_ambiguo=base["alvo_ambiguo"],
        cents_removiveis=base["cents_removiveis"],
        **_proprios(colapsaveis, detector_digests, n),
        **_parity(detector_digests, colapsaveis, todos),
    )


def detector_digests(cross_group) -> frozenset[str]:
    """Digests do numerador do detector — o conjunto contra o qual a paridade fecha."""
    return frozenset(c.key_digest for c in getattr(cross_group, "numerador", ()))


def _fmt_motivos(summary: CollapseLayerSummary) -> list[str]:
    if not summary.bloqueados_por_motivo:
        return [
            "- bloqueio por motivo: nenhum — **as cláusulas protetivas do predicado"
            " não foram exercitadas por este corpus** (quem as valida é fixture + mutação)"
        ]
    ordenado = sorted(summary.bloqueados_por_motivo.items(), key=lambda kv: (-kv[1], kv[0]))
    return [f"- bloqueio `{motivo}`: {n}" for motivo, n in ordenado]


_TITULO = "## Camada E3 (colapso cross-documento)"


def _fmt_paridade(s: CollapseLayerSummary) -> list[str]:
    cego = "" if s.sem_ponto_cego else "  ⚠️ **PONTO CEGO**"
    return [
        f"- paridade vs detector E4 (digest[:{s.digest_len}]): "
        f"em ambos **{s.em_ambos}** · só no detector **{s.so_no_detector}**{cego} · "
        f"só no colapsador **{s.so_no_colapsador}**",
        f"- fora do campo de visão do detector: **{s.orfas_rows}** rows, "
        f"**{s.orfas_cents}** cents",
        f"- `layer_ok={str(s.layer_ok).lower()}` "
        f"(partição {s.particao_fecha} · paridade {s.paridade_fecha} · "
        f"cardinalidade {s.cardinalidade_fecha}) — `alvo_enderecavel="
        f"{str(s.alvo_enderecavel).lower()}` é REPORTADO, não gateia",
    ]


def _fmt_rows(s: CollapseLayerSummary) -> list[str]:
    excesso = s.rows_alcancadas - s.rows_removiveis
    aviso = (
        ""
        if s.alvo_enderecavel
        else f"  ⚠️ **ALVO NÃO ENDEREÇÁVEL** — o enforce removeria {excesso} rows a mais"
    )
    return [
        f"- rows removíveis: **{s.rows_removiveis}** · "
        f"cents removíveis: **{s.cents_removiveis}** (fórmula: cents × rows)",
        f"- rows que o ALVO resolve: **{s.rows_alcancadas}**{aviso}"
        f" · candidatos com alvo ambíguo: {s.candidatos_com_alvo_ambiguo}",
    ]


def fmt_collapse_layer(summary: CollapseLayerSummary) -> list[str]:
    """Bloco PII-safe da camada E3 (contagens, cents, nomes de motivo)."""
    if not summary.candidatos:
        return [_TITULO, "", "- nenhum candidato cross-proveniência."]
    return [
        _TITULO,
        "",
        f"- candidatos cross-proveniência: **{summary.candidatos}** "
        f"(colapsáveis **{summary.colapsaveis}**, bloqueados {summary.bloqueados})",
        *_fmt_rows(summary),
        f"- cardinalidade multiset: {dict(sorted(summary.cardinalidade.items()))}",
        *_fmt_motivos(summary),
        *_fmt_paridade(summary),
    ]
