"""Format helpers para narrativas E5.N (A6d.3.2).

Extraído de ``scripts/generate_narratives.py`` (fmt_currency, fmt_percent,
fmt_num, fmt_usd, validate_narrativas). Funções puras — não dependem
de globals.

Regras de formatação:
- BRL milhões: ``R$ 1,5M`` (vírgula como separador decimal)
- BRL milhares: ``R$ 50k`` ou ``R$ 1,5k``
- BRL sub-mil: ``R$ 1.234,56`` (formato brasileiro)
- Percentual: ``50%`` (inteiro) ou ``50,5%`` (vírgula)
- ``None`` → ``"N/D"``

Paridade 100% com legado.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


def fmt_currency(value) -> str:
    """Format BRL currency per spec.

    - Millions: R$ X,YM (comma as decimal separator)
    - Thousands: R$ XXk or R$ XX,Yk
    - Sub-thousand: R$ X.XXX,XX (Brazilian format)
    - Negative: preserva sinal, usa abs() para range detection
    - None: ``"N/D"``
    """
    if value is None:
        return "N/D"
    if not isinstance(value, (int, float)):
        return f"R$ {value}"
    sign = "-" if value < 0 else ""
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        millions = abs_val / 1_000_000
        formatted = f"{millions:.1f}".replace(".", ",")
        return f"R$ {sign}{formatted}M"
    elif abs_val >= 1_000:
        thousands = abs_val / 1_000
        if thousands == int(thousands):
            return f"R$ {sign}{int(thousands)}k"
        formatted = f"{thousands:.1f}".replace(".", ",")
        return f"R$ {sign}{formatted}k"
    else:
        formatted = f"{abs_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {sign}{formatted}"


def fmt_percent(value) -> str:
    """Format percentage value. Returns 'N/D' for None."""
    if value is None:
        return "N/D"
    if value == int(value):
        return f"{int(value)}%"
    return f"{value:.1f}%".replace(".", ",")


def fmt_num(value, decimals: int = 1) -> str:
    """Format numeric with Brazilian decimal separator. Returns 'N/D' for None."""
    if value is None:
        return "N/D"
    if not isinstance(value, (int, float)):
        return str(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.{decimals}f}".replace(".", ",")


def pluralize(n: int, singular: str, plural: str) -> str:
    """Retorna ``singular`` se ``n == 1``, ``plural`` caso contrário."""
    return singular if n == 1 else plural


def clause(prefixo: str, valor, sufixo: str = ". ") -> str:
    """'' quando ``valor`` é vazio/falsy; senão ``prefixo+valor+sufixo`` (guard anti-buraco PD-01/PD-02)."""
    if not valor:
        return ""
    return f"{prefixo}{valor}{sufixo}"


# A40.l4: ``diversificacao`` vinha de ``len([...]) or 5`` — zero categoria
# classificada virava "5 categorias". Zero é zero: sem categoria não se afirma
# contagem. Os três call sites (s3, perfil_familia, patrimonio_doughnut) passam
# a compartilhar estas duas frases.
SEM_CATEGORIA_CLASSIFICADA = "Composição da carteira ainda não classificada por categoria de ativo"


def carteira_diversificacao_frase(n) -> str:
    """Frase de diversificação da carteira; sem categoria, declara a ausência."""
    count = int(n or 0)
    if count <= 0:
        return f"{SEM_CATEGORIA_CLASSIFICADA}. "
    return f"Carteira diversificada entre {count} {pluralize(count, 'categoria', 'categorias')} de ativos. "


def categorias_ativos_sufixo(n) -> str:
    """`` entre N categorias de ativos`` — vazio quando não há categoria."""
    count = int(n or 0)
    if count <= 0:
        return ""
    return f" entre {count} {pluralize(count, 'categoria', 'categorias')} de ativos"


def ensure_period(s: str) -> str:
    """Termina ``s`` com '.' sem duplicar; '.!?' (após rstrip) ficam; vazio→vazio."""
    stripped = s.rstrip()
    if not stripped:
        return ""
    if stripped[-1] in ".!?":
        return stripped
    return stripped + "."


# A37.l2 (PD-01): rótulos das 4 keys do legado preservados byte-a-byte;
# key desconhecida cai no fallback genérico (acrônimo/dígito → UPPER).
_APORTE_INSTRUMENTO_LABELS: dict[str, str] = {
    "cofrinhos_itau": "Cofrinhos",
    "tesouro_ipca_plus": "IPCA+",
    "ivvb11": "IVVB11",
    "wise_usd": "Wise USD",
}

_INSTRUMENTO_ACRONYMS = frozenset(
    {"brl", "cdb", "cdi", "etf", "fii", "ipca", "lca", "lci", "pgbl", "usd", "vgbl"}
)

APORTE_SEM_DISTRIBUICAO = "a distribuir entre as classes sub-representadas"


def humanize_instrumento(key: str) -> str:
    """Rótulo humano para key técnica de instrumento (``cdb_liquidez`` → ``CDB Liquidez``)."""
    known = _APORTE_INSTRUMENTO_LABELS.get(key)
    if known:
        return known
    return " ".join(
        w.upper() if w in _INSTRUMENTO_ACRONYMS or any(c.isdigit() for c in w) else w.capitalize()
        for w in key.split("_")
        if w
    )


def fmt_aporte_distribuicao(dist) -> str:
    """Parcelas > 0 como ``'R$ 5k Cofrinhos, R$ 8k IPCA+'``; vazia/zerada → ``''``."""
    entries = [(k, v) for k, v in (dist or {}).items() if isinstance(v, (int, float)) and v > 0]
    return ", ".join(f"{fmt_currency(v)} {humanize_instrumento(k)}" for k, v in entries)


# A40.l10: teto de itens renderizados da fila de decisões. Espelha
# `pipeline_adapter._TOP5_DECISION_LIMIT` — se as duas superfícies da S10
# cortarem em pontos diferentes, uma afirma contagem que a outra não lista.
TOP_DECISOES_RENDER = 5


def strip_terminal_punct(s: str) -> str:
    """Remove '.', '!' ou '?' finais — item de lista separada por vírgula não os leva."""
    return s.rstrip().rstrip(".!?").rstrip()


# A40.l10 (RV4-02): até 2026-08-05 esta frase ocupava "Prioridade 1"
# incondicionalmente no `charts.top5_decisoes` e no `summaries.s10`, e a fila do
# dono era enumerada a partir de `decisoes[1:]` — a primeira decisão registrada
# não chegava ao leitor. Aporte é um `Goal` (APORTE_MENSAL), não uma `Decision`:
# numerá-lo na mesma fila funde duas categorias e, por ser a única linha que o
# motor sempre consegue calcular, tornava o item mais fácil de computar
# sistematicamente o mais importante — inversão de Cerbasi (quitar dívida
# onerosa antes de aportar) e de Perini (reserva antes de risco).
# Produtor único das duas superfícies: o comentário "mesma guard do
# charts.top5_decisoes" que ficava no `s10` descrevia uma segunda cópia.
def fmt_aporte_contexto(M: Mapping[str, Any]) -> str:
    """Meta vigente de aporte como enquadramento; zerada/ausente omite a frase."""
    if not M.get("meta_aporte_mensal"):
        return ""
    parcelas = fmt_aporte_distribuicao(M.get("aporte_distribuicao"))
    divisao = f"com divisão ({parcelas})" if parcelas else APORTE_SEM_DISTRIBUICAO
    return f"Meta vigente de aporte mensal: {fmt_currency(M['meta_aporte_mensal'])} {divisao}. "


def fmt_usd(value) -> str:
    """Format USD value: US$ X,Yk or US$ X. Returns 'N/D' for None."""
    if value is None:
        return "N/D"
    if not isinstance(value, (int, float)):
        return f"US$ {value}"
    if value >= 1000:
        thousands = value / 1000
        if thousands == int(thousands):
            return f"US$ {int(thousands)}k"
        formatted = f"{thousands:.1f}".replace(".", ",")
        return f"US$ {formatted}k"
    return f"US$ {int(value)}"


def _is_impostos_pj_pendente(chart: dict) -> bool:
    """ADR-236 §D5: card 'perfil tributário PJ pendente' tem conclusion vazia."""
    context = chart.get("context", "") or ""
    return "Perfil tributário PJ pendente" in context


def validate_narrativas(
    narrativas_obj: dict, cenarios_section_key: str = "cenarios_conjuge"
) -> tuple[bool, list[str]]:
    """Validate narrativas E5.N. ``cenarios_section_key`` default fixado por ADR-176; parâmetro mantido por compat reversa."""
    errors: list[str] = []

    if "perfil_familia" not in narrativas_obj:
        errors.append("Missing perfil_familia key")
    if "summaries" not in narrativas_obj:
        errors.append("Missing summaries key")
    if "charts" not in narrativas_obj:
        errors.append("Missing charts key")

    if "perfil_familia" in narrativas_obj:
        pf = narrativas_obj["perfil_familia"]
        if "left" not in pf or not pf["left"]:
            errors.append("perfil_familia.left is missing or empty")
        if "right" not in pf or not pf["right"]:
            errors.append("perfil_familia.right is missing or empty")

        for side in ["left", "right"]:
            if side in pf:
                if "<table" in pf[side].lower():
                    errors.append(f"perfil_familia.{side} contains <table>")
                if "<ul" in pf[side].lower() or "<li" in pf[side].lower():
                    errors.append(f"perfil_familia.{side} contains <ul> or <li>")

        _MAX = 300
        for side in ["left", "right"]:
            if side in pf:
                paragraphs = re.findall(r"<p>(.*?)</p>", pf[side], re.DOTALL)
                for idx, p_html in enumerate(paragraphs):
                    plain = re.sub(r"<[^>]+>", "", p_html).strip()
                    if len(plain) > _MAX:
                        errors.append(
                            f"perfil_familia.{side} P{idx+1}: {len(plain)} chars " f"(max {_MAX})"
                        )

    if "summaries" in narrativas_obj:
        summaries = narrativas_obj["summaries"]
        required_summaries = [f"s{i}" for i in range(1, 11)]
        for s_key in required_summaries:
            if s_key not in summaries:
                errors.append(f"Missing summaries.{s_key}")
            elif not summaries[s_key]:
                errors.append(f"summaries.{s_key} is empty")

    # ADR-168 cleanup (Sprint A10.1): `custos_f1f2` e `cenarios_cambiais`
    # removidos da required list — charts marcados como removidos no
    # report_spec.md desde A8.4 PR4, mas o validator continuava exigindo
    # presença, mantendo as narrativas órfãs vivas.
    required_charts = [
        "score_gauge",
        "patrimonio_doughnut",
        "alocacao_atual_vs_alvo",
        "fluxo_mensal",
        "receita_bar",
        "receita_despesa_mensal",
        "despesas_doughnut",
        "projecao_3cenarios",
        "waterfall_if",
        "renda_passiva",
        "top15_ativos",
        "impostos_pj",
        cenarios_section_key,
        "viagens",
        "bubble_riscos",
        "top5_decisoes",
    ]

    if "charts" in narrativas_obj:
        charts = narrativas_obj["charts"]
        for chart_key in required_charts:
            if chart_key not in charts:
                errors.append(f"Missing charts.{chart_key}")
            else:
                chart = charts[chart_key]
                if "context" not in chart or not chart["context"]:
                    errors.append(f"charts.{chart_key}.context is missing or empty")
                # ADR-236 §D5: impostos_pj em estado "perfil pendente" tem
                # conclusion vazia por contrato (card UI renderiza só context+CTA).
                if chart_key == "impostos_pj" and _is_impostos_pj_pendente(chart):
                    continue
                if "conclusion" not in chart or not chart["conclusion"]:
                    errors.append(f"charts.{chart_key}.conclusion is missing or empty")

    def check_monetary_format(text: str, field_name: str) -> None:
        if re.search(r"R\$\s*[\d.,]+\s*KM", text, re.IGNORECASE):
            errors.append(f"{field_name}: Invalid 'KM' suffix found (use either k or M, not KM)")
        if re.search(r"R\$\s*[\d.,]+\s+[kM]", text):
            errors.append(f"{field_name}: Invalid space between value and k/M suffix")
        if re.search(r"R\$\s*\d+\.\d+[kM]", text):
            errors.append(
                f"{field_name}: Possível ponto decimal em valor monetário " "(deveria usar vírgula)"
            )

    if "perfil_familia" in narrativas_obj:
        for side in ["left", "right"]:
            if side in narrativas_obj["perfil_familia"]:
                check_monetary_format(
                    narrativas_obj["perfil_familia"][side], f"perfil_familia.{side}"
                )

    if "summaries" in narrativas_obj:
        for s_key, text in narrativas_obj["summaries"].items():
            if text:
                check_monetary_format(text, f"summaries.{s_key}")

    if "charts" in narrativas_obj:
        for chart_key, chart in narrativas_obj["charts"].items():
            for field in ["context", "conclusion"]:
                if field in chart and chart[field]:
                    check_monetary_format(chart[field], f"charts.{chart_key}.{field}")

    return len(errors) == 0, errors
