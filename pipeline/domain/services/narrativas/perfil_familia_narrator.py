"""PerfilFamiliaNarrator — seção ``perfil_familia`` (A6d.3.2).

Extraído de ``scripts/e5n_narrativas.build_narrativas`` (linhas 787-822
do legado). Narra a apresentação da família em 2 colunas (left/right)
com HTML simples (<p> apenas — validator rejeita <ul>, <li>, <table>).

Função pura sobre ``metrics`` + ``family`` + ``NarrativasContext``.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
)


# Max chars per <p> — enforçado pelo validator E5.N (V_PERFIL_MAX_CHARS).
PERFIL_MAX_CHARS = 300


def _age(dob_str: str | None, today: _date) -> str:
    if not dob_str:
        return "?"
    try:
        parts = dob_str.split("-")
        dob = _date(int(parts[0]), int(parts[1]), int(parts[2]))
        return str(
            today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        )
    except (ValueError, IndexError, TypeError) as e:
        print(f"  [WARN] Erro ao calcular idade de '{dob_str}': {e}")
        return "?"


class PerfilFamiliaNarrator:
    """Narra ``perfil_familia.left`` e ``.right`` — apresentação familiar."""

    def __init__(self, ctx: NarrativasContext):
        self._ctx = ctx

    def narrate(
        self,
        metrics: dict[str, Any],
        family: dict[str, Any],
        *,
        today: _date | None = None,
    ) -> dict[str, str]:
        """Retorna ``{"left": str, "right": str}`` com HTML de 4 parágrafos cada."""
        today = today or _date.today()
        ctx = self._ctx
        M = metrics

        fm = family.get("membros", {}) or {}
        _tit = fm.get(ctx.titular_key, {}) or {}
        _conj = fm.get(ctx.conjuge_key, {}) or {}
        _filho_key = next(
            (
                k
                for k, v in fm.items()
                if isinstance(v, dict) and v.get("papel") == "filho"
            ),
            "",
        )
        _filho = fm.get(_filho_key, {}) or {}
        _endereco = family.get("endereco", {}) or {}
        _pets = family.get("pets", []) or []

        _titular_age = _age(_tit.get("data_nascimento"), today)
        _conjuge_age = _age(_conj.get("data_nascimento"), today)
        _pets_str = (
            ", ".join(_pets[:-1]) + " e " + _pets[-1]
            if len(_pets) > 1
            else ", ".join(_pets)
        )

        _carreira_inicio = _tit.get("carreira_inicio")
        _anos_exp = (today.year - _carreira_inicio) if _carreira_inicio else 0
        _empresas = _tit.get("empresas_destaque", [])
        _empresas_str = ", ".join(_empresas) if _empresas else ""

        _mar_esp = _conj.get("especializacao", "")
        _mar_mestrado = _conj.get("mestrado", "")
        _mar_perfil_int = _conj.get("perfil_internacional", "")

        _cidadanias = _filho.get("cidadania", []) or []
        _cidadanias_str = " e ".join(_cidadanias) if _cidadanias else ""

        left = (
            f"<p>{_tit.get('nome_completo', '')}, {_titular_age} anos, "
            f"é {_tit.get('profissao', '')} ({_tit.get('descricao_empresa', '')}). "
            f"Mais de {_anos_exp} anos em tecnologia, com passagens por {_empresas_str}. "
            f"Formado em {_tit.get('formacao', '')}. "
            f"Opera como {_tit.get('regime', '')}.</p>\n"
            f"<p>{_conj.get('nome_completo', '')}, {_conjuge_age} anos, "
            f"é {_conj.get('profissao', '')} desde {_conj.get('emprego_inicio', '')}. "
            f"Especialista em {_mar_esp}, mestre em {_mar_mestrado}. "
            f"CLT com salário-base de {fmt_currency(M[ctx.key_sal_conjuge])}/mês. "
            f"{_mar_perfil_int}.</p>\n"
            f"<p>{_filho.get('nome_completo', '')} nasceu em "
            f"{_filho.get('local_nascimento', '')} e possui dupla cidadania {_cidadanias_str}. "
            "Primeiro filho do casal, é peça central no planejamento internacional da família.</p>\n"
            f"<p>A família conta com {len(_pets)} gatos — {_pets_str} — na residência da "
            f"{_endereco.get('rua', '')}, {_endereco.get('bairro', '')}, "
            f"{_endereco.get('cidade', '')}.</p>"
        )

        right = (
            f"<p>Plano de vida centrado na mudança para os EUA via visto {M['f1f2_visto']} "
            f"({M['f1f2_universidade']}), seguido de Green Card por {M['f1f2_green_card_via']}. "
            f"{M[ctx.key_f1f2_titular]}; {M[ctx.key_f1f2_conjuge]}. "
            f"Custo projetado: {fmt_currency(M['custo_fase_f1f2'])}/mês, com sobra de "
            f"{fmt_currency(M['sobra_mensal_f1f2'])}/mês.</p>\n"
            f"<p>Meta IF: {fmt_currency(M['if_meta'])} (TRS {fmt_num(M['if_trs_pct'], 0)}%, renda passiva de {fmt_currency(M['if_renda_passiva_meta'])}/mês). "
            f"Patrimônio investível atual de {fmt_currency(M['patrimonio_investivel'])} ({fmt_percent(M['progresso_if'])} da meta). "
            f"Com aportes de {fmt_currency(M['meta_aporte_mensal'])}/mês e retorno real de {fmt_num(M['if_retorno_real_pct'], 0)}% a.a., "
            f"prazo de {M['anos_para_if_calculo']} anos ({ctx.titular_nome} {M[ctx.key_idade_titular_if]} anos, {M['if_ano']}).</p>\n"
            f"<p>Patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])}: "
            f"{M['n_imoveis']} imóveis ({fmt_currency(M['residencia'])} residência + {fmt_currency(M['imoveis_investimento'])} investimento), "
            f"carteiras {ctx.titular_nome} ({fmt_currency(M[ctx.key_inv_titular])}) e {ctx.conjuge_nome} ({fmt_currency(M[ctx.key_inv_conjuge])}). "
            f"Endividamento de {fmt_percent(M['taxa_endividamento'])} — saudável.</p>"
        )

        return {"left": left, "right": right}
