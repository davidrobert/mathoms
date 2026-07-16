"""PerfilFamiliaNarrator — seção ``perfil_familia`` (A6d.3.2).

Extraído de ``scripts/generate_narratives.build_narrativas`` (linhas 787-822
do legado). Narra a apresentação da família em 2 colunas (left/right)
com HTML simples (<p> apenas — validator rejeita <ul>, <li>, <table>).

Função pura sobre ``metrics`` + ``family`` + ``NarrativasContext``.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import (
    clause,
    fmt_currency,
    fmt_num,
    fmt_percent,
    pluralize,
)

# Max chars per <p> — enforçado pelo validator E5.N (V_PERFIL_MAX_CHARS).
PERFIL_MAX_CHARS = 300


def _age(dob_str: str | None, today: _date) -> str:
    if not dob_str:
        return "?"
    try:
        parts = dob_str.split("-")
        dob = _date(int(parts[0]), int(parts[1]), int(parts[2]))
        return str(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
    except (ValueError, IndexError, TypeError) as e:
        from pipeline.observability import get_logger

        # dob é PII — loga só a classe do erro, nunca a data crua.
        get_logger("narrativas.perfil_familia").warning(
            "idade nao calculada",
            extra={"error": str(e)},
        )
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
            (k for k, v in fm.items() if isinstance(v, dict) and v.get("papel") == "filho"),
            "",
        )
        _filho = fm.get(_filho_key, {}) or {}
        _endereco = family.get("endereco", {}) or {}
        _pets = family.get("pets", []) or []

        _titular_age = _age(_tit.get("data_nascimento"), today)
        _conjuge_age = _age(_conj.get("data_nascimento"), today)
        _pets_str = (
            ", ".join(_pets[:-1]) + " e " + _pets[-1] if len(_pets) > 1 else ", ".join(_pets)
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

        # `1 imóvel (R$ X residência + R$ Y investimento)` é semanticamente
        # contraditório — soa como "2 papéis num único imóvel". Quando há
        # ≥2 imóveis, a divisão informa; n=1 omitimos o breakdown.
        # (Ressalva financial-planner review do bundle de followups.)
        _imoveis_breakdown = (
            f" ({fmt_currency(M['residencia'])} residência + {fmt_currency(M['imoveis_investimento'])} investimento)"
            if M["n_imoveis"] >= 2
            else ""
        )

        # PD-01: cláusulas condicionais — campo vazio omite a cláusula inteira
        # (evita buracos de template: "é ()", "0 gatos", "residência na , ,").
        _prof_tit = _tit.get("profissao", "")
        _desc_emp = _tit.get("descricao_empresa", "")
        _prof_clause = (
            f"é {_prof_tit} ({_desc_emp}). "
            if _prof_tit and _desc_emp
            else f"é {_prof_tit}. "
            if _prof_tit
            else ""
        )
        _empresas_clause = (
            f"Mais de {_anos_exp} anos em tecnologia, com passagens por {_empresas_str}. "
            if _empresas_str and _anos_exp
            else ""
        )
        _endereco_partes = [
            p
            for p in (
                _endereco.get("rua", ""),
                _endereco.get("bairro", ""),
                _endereco.get("cidade", ""),
            )
            if p
        ]
        _pets_clause = (
            f"<p>A família conta com {len(_pets)} {pluralize(len(_pets), 'gato', 'gatos')}"
            + (f" — {_pets_str}" if _pets_str else "")
            + (f" — na residência em {', '.join(_endereco_partes)}" if _endereco_partes else "")
            + ".</p>"
            if _pets or _endereco_partes
            else ""
        )

        # PD-01: cada fragmento vira cláusula condicional — campo vazio omite a
        # cláusula (sem "Formado em .", "é  desde .", "Especialista em , mestre em .").
        _formacao_clause = clause("Formado em ", _tit.get("formacao", ""))
        _regime_clause = clause("Opera como ", _tit.get("regime", ""))
        _cprof = _conj.get("profissao", "")
        _cinicio = _conj.get("emprego_inicio", "")
        _conj_prof_clause = (
            f"é {_cprof} desde {_cinicio}. " if _cprof and _cinicio else clause("é ", _cprof)
        )
        _esp_clause = (
            f"Especialista em {_mar_esp}, mestre em {_mar_mestrado}. "
            if _mar_esp and _mar_mestrado
            else clause("Especialista em ", _mar_esp) or clause("Mestre em ", _mar_mestrado)
        )
        _sal_conj = M.get(ctx.key_sal_conjuge, 0)
        _sal_clause = (
            clause("CLT com salário-base de ", f"{fmt_currency(_sal_conj)}/mês")
            if _sal_conj
            else ""
        )
        _perfil_int_clause = clause("", _mar_perfil_int)

        _tit_desc = f"{_prof_clause}{_empresas_clause}{_formacao_clause}{_regime_clause}".rstrip()
        _conj_desc = f"{_conj_prof_clause}{_esp_clause}{_sal_clause}{_perfil_int_clause}".rstrip()
        _p_tit = (
            f"<p>{_tit.get('nome_completo', '')}, {_titular_age} anos"
            + (f", {_tit_desc}" if _tit_desc else ".")
            + "</p>\n"
        )
        _p_conj = (
            f"<p>{_conj.get('nome_completo', '')}, {_conjuge_age} anos"
            + (f", {_conj_desc}" if _conj_desc else ".")
            + "</p>\n"
        )
        _filho_nome = _filho.get("nome_completo", "")
        _filho_local = _filho.get("local_nascimento", "")
        _p_filho = ""
        if _filho_nome:
            _head = _filho_nome
            if _filho_local:
                _head += f" nasceu em {_filho_local}"
            if _cidadanias_str:
                _head += f" e possui dupla cidadania {_cidadanias_str}"
            _p_filho = (
                f"<p>{_head}. Primeiro filho do casal, é peça central "
                "no planejamento internacional da família.</p>\n"
            )

        left = f"{_p_tit}{_p_conj}{_p_filho}{_pets_clause}"

        # ADR-168 cleanup (Sprint A10.1): primeiro parágrafo reescrito sem
        # EUA. Antes citava plano de mudança via visto F1/F2 + custo da
        # fase USA — chaves dead-data do Modo USA removido em A8.4 PR4.
        # Refoca em IF (já era o segundo parágrafo) e amplia panorama.
        right = (
            f"<p>Meta de independência financeira de {fmt_currency(M['if_meta'])} (TRS {fmt_num(M['if_trs_pct'], 0)}%, "
            f"renda passiva de {fmt_currency(M['if_renda_passiva_meta'])}/mês). "
            f"Patrimônio investível atual de {fmt_currency(M['patrimonio_investivel'])} ({fmt_percent(M['progresso_if'])} da meta). "
            f"Com aportes de {fmt_currency(M['meta_aporte_mensal'])}/mês e retorno real de {fmt_num(M['if_retorno_real_pct'], 0)}% a.a., "
            f"prazo realista de {M['anos_para_if_calculo']} anos ({ctx.titular_nome} {M[ctx.key_idade_titular_if]} anos, {M['if_ano']}).</p>\n"
            f"<p>Patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])}: "
            f"{M['n_imoveis']} {pluralize(M['n_imoveis'], 'imóvel', 'imóveis')}{_imoveis_breakdown}, "
            f"carteiras {ctx.titular_nome} ({fmt_currency(M[ctx.key_inv_titular])}) e {ctx.conjuge_nome} ({fmt_currency(M[ctx.key_inv_conjuge])}). "
            f"Endividamento de {fmt_percent(M['taxa_endividamento'])} — saudável.</p>\n"
            f"<p>Carteira diversificada entre {M['diversificacao']} categorias de ativos. "
            f"Score financeiro de {fmt_num(M['score'])}/10 ({M['score_label']}), com taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])} "
            f"e cobertura de {fmt_num(M['cobertura_meses'])} meses de despesas — base sólida para o plano IF.</p>"
        )

        return {"left": left, "right": right}
