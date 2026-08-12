"""PerfilFamiliaNarrator — seção ``perfil_familia`` (A6d.3.2).

Extraído de ``scripts/generate_narratives.build_narrativas`` (linhas 787-822
do legado). Narra a apresentação da família em ``left`` — prosa sobre as
pessoas, com HTML simples (``<p>`` apenas — validator rejeita <ul>, <li>,
<table>).

Função pura sobre ``metrics`` + ``family`` + ``NarrativasContext``.

``right`` foi removida (emenda ADR-356, 2026-08-11). Este narrador não
publica valor monetário nem juízo qualitativo: o card é prosa sobre pessoas.
Quem quiser o número tem a superfície que o possui — hero, S1, S7. Ver
``E5NarrativasBuilder`` para a composição das outras seções.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any, Mapping

from pipeline.domain.services.narrativas.context import NarrativasContext
from pipeline.domain.services.narrativas.format_helpers import clause, pluralize

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


# A40.l4 (C32 · ADR-319): o card de perfil publicava ``nome_completo`` de
# adultos E de menor. O relatório é o artefato que a família guarda e mostra a
# terceiros (contador) — nome completo identifica; primeiro nome e papel
# servem ao leitor sem identificar. Guarda: tests/test_e5n_pii_guard.py.
def _membro_paragrafo(nome_curto: str, idade: str, descricao: str) -> str:
    """``<p>`` de um adulto — primeiro nome (nunca ``nome_completo``) + idade."""
    cabeca = f"{nome_curto}, {idade} anos" if nome_curto else f"{idade} anos"
    return f"<p>{cabeca}" + (f", {descricao}" if descricao else ".") + "</p>\n"


def _filho_paragrafo(filho: Mapping[str, Any], cidadanias: str) -> str:
    """``<p>`` do filho — papel, nunca nome: menor é a PII mais sensível."""
    if not filho:
        return ""
    cabeca = "Primeiro filho do casal"
    if cidadanias:
        cabeca += f", com dupla cidadania {cidadanias}"
    return f"<p>{cabeca} — peça central no planejamento sucessório da família.</p>\n"


class PerfilFamiliaNarrator:
    """Narra ``perfil_familia.left`` — apresentação das pessoas da família."""

    def __init__(self, ctx: NarrativasContext):
        self._ctx = ctx

    # ``today`` é a data de referência do run (``data_analise`` do E5), não o
    # relógio de parede: idade impressa tem de ser a idade **no período do
    # relatório**, senão re-renderizar um relatório antigo muda o número.
    def narrate(
        self,
        metrics: dict[str, Any],
        family: dict[str, Any],
        *,
        today: _date | None = None,
    ) -> dict[str, str]:
        """Retorna ``{"left": str}`` — um ``<p>`` por pessoa, mais os pets."""
        today = today or _date.today()
        ctx = self._ctx

        fm = family.get("membros", {}) or {}
        _tit = fm.get(ctx.titular_key, {}) or {}
        _conj = fm.get(ctx.conjuge_key, {}) or {}
        _filho_key = next(
            (k for k, v in fm.items() if isinstance(v, dict) and v.get("papel") == "filho"),
            "",
        )
        _filho = fm.get(_filho_key, {}) or {}
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
        # A40.l4 (ADR-319): endereço é PII dura e o relatório é artefato que a
        # família mostra a terceiros — a residência não é citada por localização.
        _pets_clause = (
            f"<p>A família conta com {len(_pets)} {pluralize(len(_pets), 'gato', 'gatos')}"
            + (f" — {_pets_str}" if _pets_str else "")
            + ".</p>"
            if _pets
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
        # O salário-base do cônjuge saiu com a emenda ADR-356: é valor monetário
        # (regra do narrador) e é PII de renda individual num artefato que a
        # família mostra ao contador — mesma classe do endereço cortado na l4.
        # A renda do casal vive na S2 (fluxo), agregada.
        _perfil_int_clause = clause("", _mar_perfil_int)

        _tit_desc = f"{_prof_clause}{_empresas_clause}{_formacao_clause}{_regime_clause}".rstrip()
        _conj_desc = f"{_conj_prof_clause}{_esp_clause}{_perfil_int_clause}".rstrip()
        _p_tit = _membro_paragrafo(ctx.titular_nome, _titular_age, _tit_desc) if _tit else ""
        _p_conj = _membro_paragrafo(ctx.conjuge_nome, _conjuge_age, _conj_desc) if _conj else ""
        _p_filho = _filho_paragrafo(_filho, _cidadanias_str)

        return {"left": f"{_p_tit}{_p_conj}{_p_filho}{_pets_clause}"}
